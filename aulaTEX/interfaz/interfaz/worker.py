from __future__ import annotations

import logging
import time
from pathlib import Path

from .analyze import analyze_text
from .queue import dequeue_job, mark_done, ensure_dirs
from .config import load_settings
from .transcribe import transcribe_audio
from .notes import save_note

LOG = logging.getLogger("notas.worker")


def run_once(settings=None) -> int:
    settings = settings or load_settings()
    ensure_dirs()
    job = dequeue_job()
    if job is None:
        LOG.debug("No hay trabajos pendientes")
        return 0

    processing_path, payload = job
    try:
        audio_path = payload["audio_path"]
        LOG.info(f"Procesando job {payload['id']} -> {audio_path}")
        text = transcribe_audio(audio_path, settings)
        analysis = analyze_text(
            text,
            source_audio=audio_path,
            settings=settings,
            source_type=f"queue_{payload.get('media_type', 'audio')}",
        )
        saved = save_note(settings.notes_dir, analysis)
        LOG.info(f"Nota guardada: {saved.note_path}")
        Path(audio_path).unlink(missing_ok=True)
    except Exception as exc:
        LOG.exception("Error procesando job %s: %s", payload.get("id"), exc)
    finally:
        try:
            mark_done(processing_path)
        except Exception:
            LOG.exception("No pude mover job a done %s", processing_path)
    return 1


def run_loop(settings=None, interval: float = 1.0) -> None:
    settings = settings or load_settings()
    ensure_dirs()
    try:
        while True:
            processed = run_once(settings)
            if processed == 0:
                time.sleep(interval)
    except KeyboardInterrupt:
        LOG.info("Worker detenido por KeyboardInterrupt")
