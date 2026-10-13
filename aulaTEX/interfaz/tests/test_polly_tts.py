from __future__ import annotations

from pathlib import Path

from interfaz.config import Settings
from interfaz.polly_tts import synthesize_text_to_mp3_files


class DummyAudioStream:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self.payload


class DummyPollyClient:
    def __init__(self):
        self.calls: list[str] = []

    def synthesize_speech(self, **kwargs):
        text = kwargs["Text"]
        self.calls.append(text)
        return {"AudioStream": DummyAudioStream((text[:1] or "x").encode("utf-8") * 256)}


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        telegram_bot_token="token",
        notes_dir=tmp_path / "notes",
        audio_storage_dir=tmp_path / "audio",
        bot_mode="polling",
        azure_speech_key="speech-key",
        azure_speech_region="eastus",
        azure_speech_language="es-MX",
        telegram_reply_audio_enabled=True,
        aws_access_key_id="aws-key",
        aws_secret_access_key="aws-secret",
        polly_max_chars=8,
        polly_tts_workers=12,
    )


def test_synthesize_text_to_mp3_files_uses_workers_and_preserves_chunk_order(tmp_path: Path, monkeypatch) -> None:
    settings = make_settings(tmp_path)
    client = DummyPollyClient()
    monkeypatch.setattr("interfaz.polly_tts._build_polly_client", lambda current_settings: client)

    files = synthesize_text_to_mp3_files(settings, "uno. dos. tres. cuatro.", "reply")

    assert len(files) == 4
    assert [path.name[-6:-4] for path in files] == ["01", "02", "03", "04"]
    assert client.calls == ["uno.", "dos.", "tres.", "cuatro."]
    assert all(path.exists() and path.stat().st_size == 256 for path in files)
