"""Generación de imágenes y video conceptuales para el motor inteligente.

Permite al motor inteligente de AulaTeX ilustrar actividades, conceptos o
reportes con una imagen (gpt-image-2) o un clip corto (sora-2), a partir del
TEMA/CONCEPTO — no de trivialidades. Un LLM (vía llm_bridge) destila primero un
prompt visual conceptual y con él se genera el recurso.

Usa las credenciales de ``aulaTEX/aulatex.env`` (AZURE_OPENAI_IMAGE_*/VIDEO_*),
descifradas de forma autónoma por config.load_aulatex_env.
"""

from __future__ import annotations

import base64
import os
import time
from pathlib import Path
from uuid import uuid4

from .config import load_aulatex_env
from .llm_bridge import AulaTeXLLMClient


_VISUAL_PROMPT_SYSTEM = (
    "Eres un director de arte académico. A partir de un tema o concepto de una "
    "actividad educativa, redacta UN prompt visual en inglés para un generador "
    "de imágenes/vídeo. Debe captar el CONCEPTO central de forma evocadora y "
    "profesional (metáfora visual, composición clara, estética didáctica), sin "
    "texto dentro de la imagen y sin trivialidades. Si el tema no es ilustrable, "
    "responde exactamente 'SKIP'. Devuelve solo el prompt."
)


def _ensure_env() -> None:
    load_aulatex_env()


def build_visual_prompt(concept_text: str, *, kind: str = "image") -> str:
    """Destila un prompt visual conceptual del tema. '' si no es ilustrable."""
    _ensure_env()
    text = (concept_text or "").strip()
    if len(text) < 15:
        return ""
    extra = ""
    if kind == "video":
        extra = " Para VÍDEO: una sola toma conceptual con movimiento sutil y continuo."
    client = AulaTeXLLMClient()
    result = client.call_with_safety_net(
        f"{_VISUAL_PROMPT_SYSTEM}{extra}\n\nTEMA/CONCEPTO:\n{text[:6000]}",
        task="rapido",
        max_tokens=400,
    )
    if not result.ok:
        return ""
    prompt = (result.text or "").strip().strip('"')
    if not prompt or prompt.upper().startswith("SKIP"):
        return ""
    return prompt


def image_enabled() -> bool:
    _ensure_env()
    return bool(os.getenv("AZURE_OPENAI_IMAGE_API_KEY") and os.getenv("AZURE_OPENAI_IMAGES_ENDPOINT"))


def video_enabled() -> bool:
    _ensure_env()
    return bool(os.getenv("AZURE_OPENAI_VIDEO_API_KEY") and os.getenv("AZURE_OPENAI_VIDEO_ENDPOINT"))


def _images_base_url() -> str:
    ep = (os.getenv("AZURE_OPENAI_IMAGES_ENDPOINT") or "").strip().rstrip("/")
    marker = "/openai/v1"
    if marker in ep:
        return ep[: ep.index(marker) + len(marker)] + "/"
    return ep + "/openai/v1/"


def generate_image(prompt: str, *, size: str = "1024x1024", output_dir: Path | None = None) -> Path:
    _ensure_env()
    if not prompt.strip():
        raise RuntimeError("Prompt de imagen vacío.")
    if not image_enabled():
        raise RuntimeError("Generación de imágenes no configurada (faltan claves AZURE_OPENAI_IMAGE_*).")

    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("AZURE_OPENAI_IMAGE_API_KEY"), base_url=_images_base_url())
    resp = client.images.generate(
        model=os.getenv("AZURE_OPENAI_IMAGE_DEPLOYMENT", "gpt-image-2"),
        prompt=prompt.strip(), n=1, size=size,
    )
    item = resp.data[0]
    if getattr(item, "b64_json", None):
        data = base64.b64decode(item.b64_json)
    elif getattr(item, "url", None):
        import urllib.request
        with urllib.request.urlopen(item.url, timeout=60) as r:
            data = r.read()
    else:
        raise RuntimeError("La API no devolvió imagen.")

    out_dir = output_dir or (Path.cwd() / ".aulatex-temp" / "visuals")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"concepto_{uuid4().hex}.png"
    path.write_bytes(data)
    return path


def generate_video(prompt: str, *, seconds: int | None = None, size: str = "1280x720",
                   output_dir: Path | None = None) -> Path:
    _ensure_env()
    if not prompt.strip():
        raise RuntimeError("Prompt de video vacío.")
    if not video_enabled():
        raise RuntimeError("Generación de video no configurada (faltan claves AZURE_OPENAI_VIDEO_*).")

    import requests

    ep = (os.getenv("AZURE_OPENAI_VIDEO_ENDPOINT") or "").strip().rstrip("/")
    marker = "/openai/v1"
    base = (ep[: ep.index(marker) + len(marker)] + "/") if marker in ep else (ep + "/openai/v1/")
    api_key = os.getenv("AZURE_OPENAI_VIDEO_API_KEY")
    headers = {"Content-Type": "application/json", "api-key": api_key}
    max_s = max(1, int(os.getenv("AZURE_OPENAI_VIDEO_MAX_SECONDS", "8") or "8"))
    secs = min(max_s, seconds or max_s)
    payload = {
        "model": os.getenv("AZURE_OPENAI_VIDEO_DEPLOYMENT", "sora-2"),
        "prompt": prompt.strip(), "seconds": str(secs), "size": size,
    }
    resp = requests.post(base + "videos", headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    job = resp.json()
    job_id = job.get("id")
    if not job_id:
        raise RuntimeError(f"Respuesta inesperada al crear video: {job}")

    deadline = time.monotonic() + 600
    status = job.get("status", "")
    while status not in {"completed", "succeeded", "failed", "cancelled"}:
        if time.monotonic() > deadline:
            raise RuntimeError("Tiempo de espera agotado esperando el video.")
        time.sleep(5)
        poll = requests.get(base + f"videos/{job_id}", headers=headers, timeout=30)
        poll.raise_for_status()
        job = poll.json()
        status = job.get("status", "")
    if status not in {"completed", "succeeded"}:
        raise RuntimeError(f"El video no se generó (status={status}).")

    content = requests.get(base + f"videos/{job_id}/content", headers=headers, timeout=120)
    content.raise_for_status()
    out_dir = output_dir or (Path.cwd() / ".aulatex-temp" / "visuals")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"concepto_{uuid4().hex}.mp4"
    path.write_bytes(content.content)
    return path


def visual_from_concept(concept_text: str, *, kind: str = "image", output_dir: Path | None = None) -> dict:
    """Genera imagen/video conceptual de un tema. Devuelve
    {ok, path, prompt, reason}. Si el tema es trivial (SKIP), ok=False."""
    prompt = build_visual_prompt(concept_text, kind=kind)
    if not prompt:
        return {"ok": False, "path": None, "prompt": "",
                "reason": "El tema no tiene un concepto ilustrable."}
    try:
        path = generate_video(prompt, output_dir=output_dir) if kind == "video" else generate_image(prompt, output_dir=output_dir)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "path": None, "prompt": prompt, "reason": str(exc)}
    return {"ok": True, "path": str(path), "prompt": prompt, "reason": ""}


__all__ = [
    "build_visual_prompt", "generate_image", "generate_video",
    "visual_from_concept", "image_enabled", "video_enabled",
]
