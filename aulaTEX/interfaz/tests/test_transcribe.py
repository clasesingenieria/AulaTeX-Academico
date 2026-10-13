from __future__ import annotations

import errno
from pathlib import Path
from types import SimpleNamespace

import azure.cognitiveservices.speech as speechsdk
import pytest

from interfaz.config import Settings
from interfaz.transcribe import (
    REALTIME_MAX_AUDIO_SECONDS,
    REALTIME_PCM_BYTES_PER_SECOND,
    REALTIME_SEGMENT_BYTES,
    _build_realtime_session_update,
    _build_realtime_ws_url,
    _convert_audio_to_wav,
    _delete_file_with_retries,
    _split_realtime_pcm_segments,
    transcribe_audio,
)


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return Settings(
        telegram_bot_token="token",
        notes_dir=tmp_path / "notes",
        audio_storage_dir=tmp_path / "audio",
        bot_mode="polling",
        azure_speech_key="speech-key",
        azure_speech_region="eastus",
        azure_speech_language="es-MX",
    )


def test_convert_audio_to_wav_requires_existing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.ogg"

    with pytest.raises(FileNotFoundError):
        _convert_audio_to_wav(str(missing))


def test_delete_file_with_retries_retries_on_winerror_32(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    file_path = tmp_path / "temp.wav"
    file_path.write_text("x", encoding="utf-8")

    attempts = {"count": 0}
    original_unlink = Path.unlink

    def fake_unlink(self: Path, missing_ok: bool = False) -> None:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise PermissionError(32, "locked", str(self))
        return original_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", fake_unlink)

    _delete_file_with_retries(str(file_path), retries=2, delay_seconds=0)

    assert attempts["count"] == 2
    assert not file_path.exists()


def test_delete_file_with_retries_raises_other_permission_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    file_path = tmp_path / "temp.wav"
    file_path.write_text("x", encoding="utf-8")

    def fake_unlink(self: Path, missing_ok: bool = False) -> None:
        raise PermissionError(errno.EPERM, "denied", str(self))

    monkeypatch.setattr(Path, "unlink", fake_unlink)

    with pytest.raises(PermissionError):
        _delete_file_with_retries(str(file_path), retries=2, delay_seconds=0)


def test_end_of_stream_cancellation_is_ignored() -> None:
    cancellation = SimpleNamespace(
        reason=speechsdk.CancellationReason.EndOfStream,
        error_details="",
    )

    assert cancellation.reason == speechsdk.CancellationReason.EndOfStream
    assert not cancellation.error_details


def test_build_realtime_ws_url(settings: Settings) -> None:
    object.__setattr__(settings, "azure_openai_realtime_endpoint", "https://example.services.ai.azure.com/openai/v1/")
    object.__setattr__(settings, "azure_openai_realtime_deployment_name", "gpt realtime")

    assert _build_realtime_ws_url(settings) == (
        "wss://example.services.ai.azure.com/openai/v1/realtime?model=gpt%20realtime"
    )


def test_build_realtime_session_update_includes_required_session_type(settings: Settings) -> None:
    object.__setattr__(settings, "azure_openai_realtime_transcription_model", "gpt-4o-mini-transcribe")

    payload = _build_realtime_session_update(settings)
    input_audio = payload["session"]["audio"]["input"]

    assert payload["type"] == "session.update"
    assert payload["session"]["type"] == "realtime"
    assert "modalities" not in payload["session"]
    assert "input_audio_format" not in payload["session"]
    assert "input_audio_transcription" not in payload["session"]
    assert input_audio["format"] == {"type": "audio/pcm", "rate": 24000}
    assert "transcription" not in input_audio
    assert payload["session"]["output_modalities"] == ["text"]
    assert input_audio["turn_detection"]["type"] == "server_vad"
    assert input_audio["turn_detection"]["create_response"] is False


def test_transcribe_audio_uses_realtime_provider(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    object.__setattr__(settings, "transcription_provider", "realtime")
    monkeypatch.setattr("interfaz.transcribe.transcribe_audio_with_realtime", lambda audio_path, settings: "texto realtime")

    assert transcribe_audio("audio.ogg", settings) == "texto realtime"


def test_transcribe_audio_auto_falls_back_to_speech(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    object.__setattr__(settings, "transcription_provider", "auto")

    def fail_realtime(audio_path: str, settings: Settings) -> str:
        raise RuntimeError("sin realtime")

    monkeypatch.setattr("interfaz.transcribe.transcribe_audio_with_realtime", fail_realtime)
    monkeypatch.setattr("interfaz.transcribe.transcribe_audio_with_speech", lambda audio_path, settings: "texto speech")

    assert transcribe_audio("audio.ogg", settings) == "texto speech"


def test_transcribe_audio_realtime_does_not_fall_back_to_speech(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    object.__setattr__(settings, "transcription_provider", "realtime")

    def fail_realtime(audio_path: str, settings: Settings) -> str:
        raise RuntimeError("sent 1011 (internal error) keepalive ping timeout; no close frame received")

    monkeypatch.setattr("interfaz.transcribe.transcribe_audio_with_realtime", fail_realtime)
    monkeypatch.setattr("interfaz.transcribe.transcribe_audio_with_speech", lambda audio_path, settings: "texto speech")

    with pytest.raises(RuntimeError, match="keepalive ping timeout"):
        transcribe_audio("audio.ogg", settings)


def test_split_realtime_pcm_segments_splits_long_audio() -> None:
    audio = b"x" * (REALTIME_SEGMENT_BYTES * 2 + 123)

    segments = _split_realtime_pcm_segments(audio)

    assert len(segments) == 3
    assert len(segments[0]) == REALTIME_SEGMENT_BYTES
    assert len(segments[1]) == REALTIME_SEGMENT_BYTES
    assert len(segments[2]) == 123


def test_split_realtime_pcm_segments_rejects_over_10_minutes() -> None:
    audio = b"x" * (REALTIME_MAX_AUDIO_SECONDS * REALTIME_PCM_BYTES_PER_SECOND + 1)

    with pytest.raises(RuntimeError, match="10 minutos"):
        _split_realtime_pcm_segments(audio)

