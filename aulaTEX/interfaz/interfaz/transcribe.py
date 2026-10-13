from __future__ import annotations

import asyncio
import base64
import errno
import gc
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import quote

import azure.cognitiveservices.speech as speechsdk
from openai import AsyncOpenAI

from .config import Settings, load_settings


_REALTIME_TRANSIENT_ERROR_MARKERS = (
    "keepalive ping timeout",
    "no close frame received",
    "sent 1011",
    "connectionclosed",
    "connection closed",
    "websocket",
    "timed out",
    "timeout",
)
REALTIME_PCM_SAMPLE_RATE = 24_000
REALTIME_PCM_BYTES_PER_SAMPLE = 2
REALTIME_PCM_BYTES_PER_SECOND = REALTIME_PCM_SAMPLE_RATE * REALTIME_PCM_BYTES_PER_SAMPLE
REALTIME_MAX_AUDIO_SECONDS = 10 * 60
REALTIME_SEGMENT_SECONDS = 90
REALTIME_SEGMENT_BYTES = REALTIME_PCM_BYTES_PER_SECOND * REALTIME_SEGMENT_SECONDS
REALTIME_STREAM_CHUNK_BYTES = 4_800  # 100 ms a 24 kHz, PCM16 mono.
REALTIME_TRAILING_SILENCE_BYTES = REALTIME_PCM_BYTES_PER_SECOND


def _require_existing_audio_and_ffmpeg(source_path: str) -> tuple[Path, str]:
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"No existe el audio: {source_path}")

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError("No se encontró `ffmpeg` en PATH. Instálalo para convertir audios de Telegram.")

    return source, ffmpeg_path


def _convert_audio_to_wav(source_path: str) -> str:
    source, ffmpeg_path = _require_existing_audio_and_ffmpeg(source_path)

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    temp_file.close()

    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(source),
        "-ac",
        "1",
        "-ar",
        "16000",
        temp_file.name,
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        Path(temp_file.name).unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg no pudo convertir el audio: {result.stderr.strip()}")

    return temp_file.name


def _convert_audio_to_realtime_pcm16(source_path: str) -> str:
    source, ffmpeg_path = _require_existing_audio_and_ffmpeg(source_path)

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pcm")
    temp_file.close()

    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(source),
        "-ac",
        "1",
        "-ar",
        str(REALTIME_PCM_SAMPLE_RATE),
        "-f",
        "s16le",
        temp_file.name,
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        Path(temp_file.name).unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg no pudo convertir el audio para GPT Realtime: {result.stderr.strip()}")

    return temp_file.name


def _split_realtime_pcm_segments(audio_data: bytes) -> list[bytes]:
    if not audio_data:
        raise RuntimeError("Audio PCM vacio para GPT Realtime.")
    max_bytes = REALTIME_MAX_AUDIO_SECONDS * REALTIME_PCM_BYTES_PER_SECOND
    if len(audio_data) > max_bytes:
        raise RuntimeError("El audio excede el maximo soportado de 10 minutos.")
    return [
        audio_data[offset : offset + REALTIME_SEGMENT_BYTES]
        for offset in range(0, len(audio_data), REALTIME_SEGMENT_BYTES)
    ]


def _delete_file_with_retries(file_path: str, retries: int = 8, delay_seconds: float = 0.25) -> None:
    path = Path(file_path)
    last_error: PermissionError | None = None

    for attempt in range(retries):
        try:
            path.unlink(missing_ok=True)
            return
        except PermissionError as exc:
            winerror = getattr(exc, "winerror", None)
            err_no = getattr(exc, "errno", None)
            is_file_locked = winerror == 32 or err_no in {32, errno.EACCES}
            if not is_file_locked:
                raise
            last_error = exc
            if attempt == retries - 1:
                break
            gc.collect()
            time.sleep(delay_seconds)

    if last_error is not None:
        raise last_error


def transcribe_audio_with_speech(audio_path: str, settings: Settings | None = None) -> str:
    settings = settings or load_settings()
    wav_path = _convert_audio_to_wav(audio_path)

    recognizer = None
    audio_config = None
    speech_config = None

    try:
        speech_config = speechsdk.SpeechConfig(
            subscription=settings.azure_speech_key,
            region=settings.azure_speech_region,
        )
        speech_config.speech_recognition_language = settings.azure_speech_language

        audio_config = speechsdk.audio.AudioConfig(filename=wav_path)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config,
        )

        transcript_parts: list[str] = []
        done = threading.Event()
        error_holder: list[str] = []

        def on_recognized(evt: object) -> None:
            result = getattr(evt, "result", None)
            if result is None:
                return
            if getattr(result, "reason", None) == speechsdk.ResultReason.RecognizedSpeech:
                text = (getattr(result, "text", "") or "").strip()
                if text:
                    transcript_parts.append(text)

        def on_canceled(evt: object) -> None:
            result = getattr(evt, "result", None)
            cancellation = getattr(result, "cancellation_details", None)
            cancellation_reason = getattr(cancellation, "reason", None)
            if cancellation_reason == speechsdk.CancellationReason.EndOfStream:
                done.set()
                return
            if cancellation is not None:
                error_details = getattr(cancellation, "error_details", "") or ""
                error_holder.append(f"{cancellation.reason}: {error_details}".rstrip())
            else:
                error_holder.append("Transcripción cancelada por Azure Speech.")
            done.set()

        def on_session_stopped(_: object) -> None:
            done.set()

        recognizer.recognized.connect(on_recognized)
        recognizer.canceled.connect(on_canceled)
        recognizer.session_stopped.connect(on_session_stopped)

        recognizer.start_continuous_recognition_async().get()
        if not done.wait(timeout=300):
            recognizer.stop_continuous_recognition_async().get()
            raise RuntimeError("La transcripción excedió el tiempo máximo permitido.")
        recognizer.stop_continuous_recognition_async().get()

        if error_holder:
            raise RuntimeError(error_holder[0])

        transcript = " ".join(part.strip() for part in transcript_parts if part.strip()).strip()
        if not transcript:
            raise RuntimeError("Azure Speech no devolvió texto reconocible para el audio recibido.")
        return transcript
    finally:
        recognizer = None
        audio_config = None
        speech_config = None
        gc.collect()
        _delete_file_with_retries(wav_path)


def _build_realtime_ws_url(settings: Settings) -> str:
    endpoint = settings.azure_openai_realtime_endpoint.rstrip("/")
    if endpoint.endswith("/openai/v1"):
        base = endpoint
    else:
        base = f"{endpoint}/openai/v1"

    if base.startswith("https://"):
        base = "wss://" + base[len("https://") :]
    elif base.startswith("http://"):
        base = "ws://" + base[len("http://") :]

    deployment = quote(settings.azure_openai_realtime_deployment_name, safe="")
    return f"{base}/realtime?model={deployment}"


def _build_realtime_session_update(settings: Settings) -> dict:
    return {
        "type": "session.update",
        "session": {
            "type": "realtime",
            "instructions": (
                "Transcribe literalmente el audio del usuario en español. "
                "Devuelve únicamente la transcripción, sin comentarios, sin traducción y sin formato adicional."
            ),
            "output_modalities": ["text"],
            "audio": {
                "input": {
                    "format": {
                        "type": "audio/pcm",
                        "rate": 24000,
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500,
                        "create_response": False,
                        "interrupt_response": False,
                    },
                },
            },
        },
    }


def _is_realtime_transient_error(exc: Exception) -> bool:
    message = str(exc).casefold()
    return any(marker in message for marker in _REALTIME_TRANSIENT_ERROR_MARKERS)


def _build_realtime_websocket_base_url(settings: Settings) -> str:
    endpoint = settings.azure_openai_realtime_endpoint.rstrip("/")
    if endpoint.endswith("/openai/v1"):
        return endpoint.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
    return endpoint.replace("https://", "wss://", 1).replace("http://", "ws://", 1) + "/openai/v1"


async def _recv_realtime_event(connection, deadline: float, timeout_seconds: float = 15.0):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("Tiempo agotado esperando evento de GPT Realtime.")
    return await asyncio.wait_for(connection.recv(), timeout=min(timeout_seconds, remaining))


async def _transcribe_realtime_segment(
    client: AsyncOpenAI,
    settings: Settings,
    segment: bytes,
    segment_index: int,
    total_segments: int,
) -> str:
    transcript_parts: list[str] = []
    async with client.realtime.connect(
        model=settings.azure_openai_realtime_deployment_name,
        websocket_connection_options={
            "ping_interval": None,
            "ping_timeout": None,
            "close_timeout": 30,
            "max_size": 32 * 1024 * 1024,
        },
    ) as connection:
        session_payload = _build_realtime_session_update(settings)["session"]
        await connection.session.update(session=session_payload)

        session_ready = False
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            event = await _recv_realtime_event(connection, deadline)
            event_type = str(getattr(event, "type", ""))
            if event_type == "session.updated":
                session_ready = True
                break
            if event_type == "error":
                error = getattr(event, "error", event)
                raise RuntimeError(f"GPT Realtime devolvió error: {error}")

        if not session_ready:
            raise RuntimeError("GPT Realtime no confirmó la configuración de sesión.")

        audio_data = segment + (b"\x00" * REALTIME_TRAILING_SILENCE_BYTES)
        appended_bytes = 0
        for offset in range(0, len(audio_data), REALTIME_STREAM_CHUNK_BYTES):
            chunk = audio_data[offset : offset + REALTIME_STREAM_CHUNK_BYTES]
            appended_bytes += len(chunk)
            await connection.input_audio_buffer.append(audio=base64.b64encode(chunk).decode("ascii"))
            await asyncio.sleep(0.01)

        if appended_bytes < REALTIME_STREAM_CHUNK_BYTES:
            raise RuntimeError(f"Audio PCM demasiado corto para GPT Realtime: {appended_bytes} bytes.")

        committed = False
        response_requested = False
        while time.monotonic() < deadline:
            try:
                event = await _recv_realtime_event(connection, deadline)
            except TimeoutError:
                break
            event_type = str(getattr(event, "type", ""))

            if event_type == "input_audio_buffer.committed":
                committed = True

            if committed and not response_requested and event_type == "conversation.item.done":
                response_requested = True
                await connection.response.create(
                    response={
                        "instructions": (
                            f"El mensaje anterior del usuario contiene audio. Transcribe literalmente el segmento "
                            f"{segment_index} de {total_segments}. No respondas al contenido, no expliques, no anticipes. "
                            "Devuelve solamente las palabras pronunciadas en el audio."
                        ),
                    }
                )

            if event_type in {"response.text.delta", "response.output_text.delta"}:
                delta = str(getattr(event, "delta", "") or "")
                if delta:
                    transcript_parts.append(delta)

            if event_type in {"response.text.done", "response.output_text.done"}:
                text = str(getattr(event, "text", "") or "").strip()
                if text:
                    transcript_parts = [text]

            if event_type == "response.done":
                break

            if event_type == "error":
                error = getattr(event, "error", event)
                raise RuntimeError(f"GPT Realtime devolvió error: {error}")

        if not committed:
            raise RuntimeError("GPT Realtime no confirmó el buffer de audio.")

    transcript_text = "".join(part for part in transcript_parts if part).strip()
    if not transcript_text:
        raise RuntimeError("GPT Realtime no devolvió una transcripción reconocible para el audio recibido.")
    return transcript_text


async def _transcribe_audio_with_realtime_async(audio_path: str, settings: Settings) -> str:
    pcm_path = _convert_audio_to_realtime_pcm16(audio_path)
    try:
        audio_data = Path(pcm_path).read_bytes()
        segments = _split_realtime_pcm_segments(audio_data)
        client = AsyncOpenAI(
            api_key=settings.azure_openai_realtime_api_key,
            websocket_base_url=_build_realtime_websocket_base_url(settings),
            default_headers={"api-key": settings.azure_openai_realtime_api_key},
        )
        transcript_segments: list[str] = []
        total_segments = len(segments)
        for index, segment in enumerate(segments, start=1):
            transcript_segments.append(await _transcribe_realtime_segment(client, settings, segment, index, total_segments))
        transcript_text = " ".join(part.strip() for part in transcript_segments if part.strip()).strip()
        if not transcript_text:
            raise RuntimeError("GPT Realtime no devolvió una transcripción reconocible para el audio recibido.")
        return transcript_text
    finally:
        _delete_file_with_retries(pcm_path)


def transcribe_audio_with_realtime(audio_path: str, settings: Settings | None = None) -> str:
    settings = settings or load_settings()
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            return asyncio.run(_transcribe_audio_with_realtime_async(audio_path, settings))
        except Exception as exc:
            last_error = exc
            if attempt == 1 or not _is_realtime_transient_error(exc):
                break
            time.sleep(1.5)
    assert last_error is not None
    raise last_error


def transcribe_audio(audio_path: str, settings: Settings | None = None) -> str:
    settings = settings or load_settings()
    provider = settings.transcription_provider

    if provider == "realtime":
        return transcribe_audio_with_realtime(audio_path, settings)

    if provider == "auto":
        try:
            return transcribe_audio_with_realtime(audio_path, settings)
        except Exception:
            return transcribe_audio_with_speech(audio_path, settings)

    return transcribe_audio_with_speech(audio_path, settings)
