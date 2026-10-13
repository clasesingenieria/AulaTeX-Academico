"""Generación de imágenes y video conceptuales a partir de una nota.

Filosofía: las notas son personales y temáticas. La imagen/video debe ilustrar
el CONCEPTO o TEMA central de la nota — no trivialidades ni texto literal. Por
eso, primero un LLM destila un prompt visual conceptual, y con él se genera:

  - Imagen: gpt-image-2 (rápida) vía /openai/v1/images/generations
  - Video:  sora-2 (asíncrono). Sora produce clips cortos; se acota la duración
            a un máximo seguro (AZURE_OPENAI_VIDEO_MAX_SECONDS, def. 8s) y se
            genera UN clip conceptual único (no multi-frame), evitando el límite
            de ~18s por generación.

Reutiliza el recurso Azure y las credenciales cifradas ya presentes en el .env.
"""

from __future__ import annotations

import base64
import time
from pathlib import Path
from uuid import uuid4

import requests

from .config import Settings, load_settings
from .note_intelligence import smart_invoke


# ------------------------------------------------------------ prompt conceptual
_VISUAL_PROMPT_SYSTEM = (
    "Eres un director de arte. A partir de una nota personal, redacta UN prompt "
    "visual en inglés para un generador de imágenes/vídeo. El prompt debe captar "
    "el CONCEPTO o TEMA central de la nota de forma evocadora y estética "
    "(metáfora visual, atmósfera, composición), NO ilustrar trivialidades, listas "
    "ni texto literal. Nada de palabras dentro de la imagen. Si la nota es trivial "
    "o sin tema ilustrable, responde exactamente 'SKIP'. Devuelve solo el prompt."
)


def build_visual_prompt(note_text: str, settings: Settings | None = None, kind: str = "image") -> str:
    """Destila un prompt visual conceptual de la nota. Devuelve '' si la nota
    no da para una imagen temática (respuesta SKIP del modelo)."""
    settings = settings or load_settings()
    text = (note_text or "").strip()
    if len(text) < 20:
        return ""
    extra = ""
    if kind == "video":
        extra = (
            " Para VÍDEO: describe una escena breve con movimiento sutil y "
            "continuo (una sola toma conceptual, sin cortes)."
        )
    out = smart_invoke(
        "summarize",  # tarea ágil; destilar prompt no requiere razonamiento profundo
        messages=[
            {"role": "system", "content": _VISUAL_PROMPT_SYSTEM + extra},
            {"role": "user", "content": text[:6000]},
        ],
        settings=settings,
        max_tokens=300,
        temperature=0.6,
    )
    prompt = (out or "").strip().strip('"')
    if not prompt or prompt.upper().startswith("SKIP"):
        return ""
    return prompt


# ------------------------------------------------------------ helpers de recurso
def _image_host(settings: Settings) -> str:
    from .azure_openai_client import normalize_openai_v1_base_url
    ep = settings.azure_openai_images_endpoint or settings.azure_openai_endpoint
    return normalize_openai_v1_base_url(ep)


def _video_base(settings: Settings) -> str:
    from .azure_openai_client import normalize_openai_v1_base_url
    ep = settings.azure_openai_video_endpoint or settings.azure_openai_endpoint
    return normalize_openai_v1_base_url(ep)


def image_enabled(settings: Settings) -> bool:
    return bool((settings.azure_openai_image_api_key or settings.azure_openai_api_key)
                and (settings.azure_openai_images_endpoint or settings.azure_openai_endpoint)
                and settings.azure_openai_image_deployment)


def video_enabled(settings: Settings) -> bool:
    return bool((settings.azure_openai_video_api_key or settings.azure_openai_api_key)
                and (settings.azure_openai_video_endpoint or settings.azure_openai_endpoint)
                and settings.azure_openai_video_deployment)


# ------------------------------------------------------------ generación imagen
def generate_image(settings: Settings, prompt: str, *, size: str = "1024x1024",
                   output_dir: Path | None = None) -> Path:
    if not prompt.strip():
        raise RuntimeError("Prompt de imagen vacío.")
    if not image_enabled(settings):
        raise RuntimeError("Generación de imágenes no configurada.")
    from openai import OpenAI

    api_key = settings.azure_openai_image_api_key or settings.azure_openai_api_key
    client = OpenAI(api_key=api_key, base_url=_image_host(settings))
    try:
        resp = client.images.generate(
            model=settings.azure_openai_image_deployment,
            prompt=prompt.strip(), n=1, size=size,
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Fallo al generar imagen: {exc}") from exc

    item = resp.data[0]
    if getattr(item, "b64_json", None):
        data = base64.b64decode(item.b64_json)
    elif getattr(item, "url", None):
        import urllib.request
        with urllib.request.urlopen(item.url, timeout=60) as r:
            data = r.read()
    else:
        raise RuntimeError("La API no devolvió imagen.")

    out_dir = output_dir or (Path(settings.audio_storage_dir).parent / "images")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"nota_{uuid4().hex}.png"
    path.write_bytes(data)
    return path


# ------------------------------------------------------------ generación video
_POLL_INTERVAL = 5
_MAX_WAIT = 600


def generate_video(settings: Settings, prompt: str, *, seconds: int | None = None,
                   size: str = "1280x720", output_dir: Path | None = None) -> Path:
    """Genera un clip corto con Sora. Acota la duración al máximo seguro para no
    exceder el límite de generación por clip."""
    if not prompt.strip():
        raise RuntimeError("Prompt de video vacío.")
    if not video_enabled(settings):
        raise RuntimeError("Generación de video no configurada.")

    # Sora limita la duración por clip; se recorta al máximo seguro configurado.
    max_s = max(1, int(settings.azure_openai_video_max_seconds or 8))
    secs = min(max_s, seconds or max_s)

    base = _video_base(settings)
    api_key = settings.azure_openai_video_api_key or settings.azure_openai_api_key
    headers = {"Content-Type": "application/json", "api-key": api_key}
    payload = {
        "model": settings.azure_openai_video_deployment,
        "prompt": prompt.strip(),
        "seconds": str(secs),
        "size": size,
    }
    try:
        resp = requests.post(base + "videos", headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"No se pudo crear el job de video: {exc}") from exc

    job = resp.json()
    job_id = job.get("id")
    if not job_id:
        raise RuntimeError(f"Respuesta inesperada al crear video: {job}")

    deadline = time.monotonic() + _MAX_WAIT
    status = job.get("status", "")
    while status not in {"completed", "succeeded", "failed", "cancelled"}:
        if time.monotonic() > deadline:
            raise RuntimeError("Tiempo de espera agotado esperando el video.")
        time.sleep(_POLL_INTERVAL)
        try:
            poll = requests.get(base + f"videos/{job_id}", headers=headers, timeout=30)
            poll.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Error consultando el video: {exc}") from exc
        job = poll.json()
        status = job.get("status", "")

    if status not in {"completed", "succeeded"}:
        raise RuntimeError(f"El video no se generó (status={status}).")

    try:
        content = requests.get(base + f"videos/{job_id}/content", headers=headers, timeout=120)
        content.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"No se pudo descargar el video: {exc}") from exc

    out_dir = output_dir or (Path(settings.audio_storage_dir).parent / "videos")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"nota_{uuid4().hex}.mp4"
    path.write_bytes(content.content)
    return path


# ------------------------------------------------------------ orquestación
def visual_from_note(note_text: str, kind: str = "image", settings: Settings | None = None) -> dict:
    """Genera imagen o video conceptual a partir de la nota.

    Devuelve dict {ok, path, prompt, reason}. Si la nota es trivial (SKIP),
    devuelve ok=False con reason explicativo.
    """
    settings = settings or load_settings()
    prompt = build_visual_prompt(note_text, settings=settings, kind=kind)
    if not prompt:
        return {"ok": False, "path": None, "prompt": "",
                "reason": "La nota no tiene un tema conceptual ilustrable."}
    try:
        if kind == "video":
            path = generate_video(settings, prompt)
        else:
            path = generate_image(settings, prompt)
    except Exception as exc:
        return {"ok": False, "path": None, "prompt": prompt, "reason": str(exc)}
    return {"ok": True, "path": str(path), "prompt": prompt, "reason": ""}


__all__ = [
    "build_visual_prompt", "generate_image", "generate_video",
    "visual_from_note", "image_enabled", "video_enabled",
]
