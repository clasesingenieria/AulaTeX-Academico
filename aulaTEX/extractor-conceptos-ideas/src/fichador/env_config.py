from __future__ import annotations

import os
from pathlib import Path


def load_env() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return
    project_root = Path(__file__).resolve().parents[2]
    primary_env = project_root / "extractor.ev"
    primary_local = project_root / "extractor.ev.local"
    legacy_env = project_root / ".env"
    legacy_local = project_root / ".env.local"
    if primary_env.exists():
        load_dotenv(primary_env, override=False)
    elif legacy_env.exists():
        load_dotenv(legacy_env, override=False)
    if primary_local.exists():
        load_dotenv(primary_local, override=True)
    elif legacy_local.exists():
        load_dotenv(legacy_local, override=True)


def env_str(name: str, default: str | None = None) -> str | None:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    return val.strip()


def env_int(name: str, default: int) -> int:
    val = env_str(name)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def env_float(name: str, default: float | None) -> float | None:
    val = env_str(name)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        return default


def env_bool(name: str, default: bool = False) -> bool:
    val = env_str(name)
    if val is None:
        return default
    return val.lower() in {"1", "true", "sí", "si", "yes", "y", "on"}


def ensure_relative(path_value: str | None) -> str | None:
    if not path_value:
        return None
    return str(Path(path_value))
