from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

QUEUE_DIR = Path("data/queue")
PENDING_DIR = QUEUE_DIR / "pending"
PROCESSING_DIR = QUEUE_DIR / "processing"
DONE_DIR = QUEUE_DIR / "done"


def ensure_dirs() -> None:
    for d in (PENDING_DIR, PROCESSING_DIR, DONE_DIR):
        d.mkdir(parents=True, exist_ok=True)


def enqueue_audio(audio_path: str, chat_id: int, message_id: int, media_type: str, original_name: str | None = None) -> Path:
    """Create a job file in the queue pending directory.

    Returns the path to the created job file.
    """
    ensure_dirs()
    job_id = uuid.uuid4().hex
    now = datetime.utcnow().isoformat()
    payload = {
        "id": job_id,
        "created_at": now,
        "audio_path": str(audio_path),
        "chat_id": chat_id,
        "message_id": message_id,
        "media_type": media_type,
        "original_name": original_name,
    }
    job_path = PENDING_DIR / f"{job_id}.json"
    job_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return job_path


def dequeue_job() -> tuple[Path, dict] | None:
    """Atomically move one job from pending to processing and return (path, payload).

    Returns None if no pending job exists.
    """
    ensure_dirs()
    for job_file in sorted(PENDING_DIR.iterdir()):
        if not job_file.is_file() or job_file.suffix.lower() != ".json":
            continue
        dest = PROCESSING_DIR / job_file.name
        try:
            job_file.replace(dest)
        except Exception:
            continue
        content = dest.read_text(encoding="utf-8")
        payload = json.loads(content)
        return dest, payload
    return None


def mark_done(processing_path: Path) -> None:
    ensure_dirs()
    dest = DONE_DIR / processing_path.name
    processing_path.replace(dest)
