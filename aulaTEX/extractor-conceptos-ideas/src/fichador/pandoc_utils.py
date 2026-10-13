from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
import subprocess
from shutil import which


@lru_cache(maxsize=1)
def get_pandoc_path() -> str | None:
    configured = os.getenv("PANDOC_PATH", "").strip()
    if configured:
        path = Path(configured)
        if path.exists():
            return str(path)
    return which("pandoc")


def pandoc_available() -> bool:
    return get_pandoc_path() is not None


def pandoc_enabled() -> bool:
    value = os.getenv("PANDOC_ENABLED", "true").strip().lower()
    return value not in {"0", "false", "no", "off"}


def pdf_pandoc_normalization_enabled() -> bool:
    value = os.getenv("PDF_NORMALIZE_WITH_PANDOC", "true").strip().lower()
    return value not in {"0", "false", "no", "off"}


def normalize_text_with_pandoc(
    text: str,
    *,
    from_format: str = "markdown",
    to_format: str = "plain",
    timeout_seconds: int | None = None,
) -> str:
    if not text.strip():
        return text
    if not pandoc_enabled() or not pandoc_available():
        return text

    timeout = timeout_seconds or int(os.getenv("PANDOC_TIMEOUT_SECONDS", "20"))
    pandoc_path = get_pandoc_path()
    if not pandoc_path:
        return text

    command = [
        pandoc_path,
        "--from",
        from_format,
        "--to",
        to_format,
        "--wrap=preserve",
    ]

    try:
        result = subprocess.run(
            command,
            input=text,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(1, timeout),
            check=False,
        )
    except Exception:
        return text

    if result.returncode != 0:
        return text

    normalized = result.stdout.replace("\r\n", "\n").strip()
    return normalized or text
