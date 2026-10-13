from __future__ import annotations

import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from .config import Settings


FFMPEG_MERGE_TIMEOUT_SECONDS = 120


# boto3 is imported lazily inside _build_polly_client to avoid requiring it
# at import time for environments (like unit tests) that don't have boto3 installed.


def polly_audio_enabled(settings: Settings) -> bool:
    return (
        settings.telegram_reply_audio_enabled
        and bool(settings.aws_access_key_id)
        and bool(settings.aws_secret_access_key)
    )


def _normalize_text_for_tts(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    compact = "\n".join(line for line in lines if line)
    return compact.strip()


def _split_text_for_polly(text: str, max_chars: int) -> list[str]:
    normalized = _normalize_text_for_tts(text)
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]

    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        piece = sentence.strip()
        if not piece:
            continue
        if len(piece) > max_chars:
            parts = [piece[index : index + max_chars] for index in range(0, len(piece), max_chars)]
        else:
            parts = [piece]
        for part in parts:
            candidate = f"{current} {part}".strip() if current else part
            if len(candidate) <= max_chars:
                current = candidate
                continue
            if current:
                chunks.append(current)
            current = part
    if current:
        chunks.append(current)
    return chunks


def _build_polly_client(settings: Settings):
    import boto3
    from botocore.config import Config as BotoConfig

    return boto3.client(
        "polly",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        config=BotoConfig(
            retries={"max_attempts": 2, "mode": "standard"},
            max_pool_connections=max(12, settings.polly_tts_workers),
            connect_timeout=15,
            read_timeout=120,
        ),
    )


def synthesize_text_to_mp3_files(
    settings: Settings,
    text: str,
    prefix: str = "respuesta",
) -> list[Path]:
    if not polly_audio_enabled(settings):
        return []

    chunks = _split_text_for_polly(text, settings.polly_max_chars)
    if not chunks:
        return []

    output_dir = settings.audio_storage_dir / "tts"
    output_dir.mkdir(parents=True, exist_ok=True)
    client = _build_polly_client(settings)
    created_files: list[Path] = []

    def synthesize_chunk(index_and_chunk: tuple[int, str]) -> Path:
        index, chunk = index_and_chunk
        response = client.synthesize_speech(
            Engine=settings.aws_polly_engine,
            VoiceId=settings.aws_polly_voice_id,
            LanguageCode=settings.aws_polly_language_code,
            OutputFormat="mp3",
            SampleRate=settings.aws_polly_sample_rate,
            Text=chunk,
            TextType="text",
        )
        with response["AudioStream"] as stream:
            audio_bytes = stream.read()
        if len(audio_bytes) < 128:
            raise RuntimeError("AWS Polly devolvio audio vacio o demasiado pequeno.")
        audio_path = output_dir / f"{prefix}_{uuid4().hex}_{index:02d}.mp3"
        audio_path.write_bytes(audio_bytes)
        return audio_path

    try:
        indexed_chunks = list(enumerate(chunks, start=1))
        max_workers = min(max(1, settings.polly_tts_workers), len(indexed_chunks))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            created_files = list(executor.map(synthesize_chunk, indexed_chunks))
        return created_files
    except Exception:
        for path in created_files:
            path.unlink(missing_ok=True)
        raise


def merge_mp3_files(files: list[Path], output_path: Path) -> Path:
    if not files:
        raise RuntimeError("No hay archivos MP3 para unir.")
    if len(files) == 1:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(files[0].read_bytes())
        return output_path

    concat_file = output_path.with_suffix(".txt")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    def ffmpeg_concat_path(path: Path) -> str:
        normalized = path.resolve().as_posix().replace("'", r"'\\''")
        return f"file '{normalized}'"

    concat_file.write_text("\n".join(ffmpeg_concat_path(path) for path in files), encoding="utf-8")

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c",
        "copy",
        str(output_path),
    ]
    try:
        result = subprocess.run(cmd, text=True, capture_output=True, timeout=FFMPEG_MERGE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        result = None
    concat_file.unlink(missing_ok=True)

    if result is None or result.returncode != 0:
        # fallback simple si ffmpeg no logra concat demuxer
        with output_path.open("wb") as merged:
            for file_path in files:
                merged.write(file_path.read_bytes())

    if not output_path.exists() or output_path.stat().st_size < 128:
        raise RuntimeError("No se pudo generar audio unificado.")
    return output_path


def synthesize_text_to_single_mp3(
    settings: Settings,
    text: str,
    prefix: str = "respuesta",
) -> Path | None:
    files = synthesize_text_to_mp3_files(settings, text, prefix)
    if not files:
        return None
    output_dir = settings.audio_storage_dir / "tts"
    merged_path = output_dir / f"{prefix}_{uuid4().hex}_merged.mp3"
    try:
        merge_mp3_files(files, merged_path)
        return merged_path
    finally:
        for file_path in files:
            file_path.unlink(missing_ok=True)
