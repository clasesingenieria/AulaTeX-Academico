"""Hub de Capacidades — servicios especializados para el motor de AulaTeX.

Complementa los otros puentes del proyecto para ofrecer TODAS las capacidades
del recurso Azure compartido, más allá del chat de LLMs:

  - llm_bridge.py     -> Razonamiento (10+ LLMs, routing por tarea, red opus)
  - visual_bridge.py  -> Expresión visual (imagen gpt-image, video sora)
  - hub_bridge.py     -> Percepción (OCR) + Lenguaje (traductor) + Voz (TTS)

Todas las credenciales provienen de ``aulaTEX/aulatex.env`` (cifradas, con
descifrado autónomo vía config.load_aulatex_env).
"""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from .config import load_aulatex_env


def _ensure_env() -> None:
    load_aulatex_env()


def _shared_key() -> str:
    return (os.getenv("AZURE_OPENAI_IMAGE_API_KEY")
            or os.getenv("AZURE_AI_API_KEY")
            or os.getenv("CODEX_API_KEY") or "")


def _shared_host() -> str:
    return (os.getenv("AZURE_AI_HOST")
            or "https://carlosmauriciocarvajalcoronado-4.services.ai.azure.com").rstrip("/")


# ============================================================
#  Percepción — OCR vía visión (LLM multimodal desplegado)
# ------------------------------------------------------------
#  El modelo dedicado mistral-ocr-4-0 no está desplegado en el recurso, pero
#  los LLMs con visión (gpt-5.4-pro, gpt-5.6-sol) SÍ leen texto de imágenes vía
#  el endpoint Responses. Se usa esa vía, que funciona y da OCR de alta calidad.
# ============================================================
import json as _json
import urllib.request as _urlreq
import urllib.error as _urlerr

# Modelo de visión para OCR (Responses API). Configurable por env.
_OCR_VISION_MODEL = "gpt-5.4-pro"


def ocr_enabled() -> bool:
    _ensure_env()
    return bool(_shared_key())


def _extract_responses_text(payload: dict) -> str:
    """Extrae el texto de una respuesta del Responses API (ignora items de
    tipo 'reasoning' y toma el 'message'/'output_text')."""
    if isinstance(payload.get("output_text"), str) and payload["output_text"]:
        return payload["output_text"]
    parts = []
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for c in item.get("content", []) or []:
            if isinstance(c, dict) and c.get("type") in ("output_text", "text"):
                parts.append(str(c.get("text", "")))
    return "\n".join(p for p in parts if p).strip()


def _ocr_dedicated_available() -> bool:
    """True si hay un deployment OCR dedicado configurado (p. ej. tras
    desplegar mistral-ocr en Azure). Se comprueba solo la config; el uso real
    valida contra el endpoint."""
    _ensure_env()
    return bool(os.getenv("AZURE_OPENAI_OCR_DEPLOYMENT") and os.getenv("AZURE_OPENAI_OCR_ENDPOINT"))


def _ocr_via_dedicated(path: Path) -> str:
    """OCR con el modelo dedicado mistral-ocr vía su endpoint propio.

    El endpoint correcto es /providers/mistral/azure/ocr y exige la imagen como
    data URL base64 inline con autenticacion Bearer. Se puede sobrescribir con
    AZURE_OPENAI_OCR_ENDPOINT_MISTRAL."""
    key = _shared_key()
    endpoint = (
        os.getenv("AZURE_OPENAI_OCR_ENDPOINT_MISTRAL", "").rstrip("/")
        or f"{_shared_host()}/providers/mistral/azure/ocr"
    )
    model = os.getenv("AZURE_OPENAI_OCR_DEPLOYMENT", "mistral-ocr-4-0")
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    suffix = path.suffix.lower().lstrip(".")
    is_pdf = suffix == "pdf"
    doc = {
        "type": "document_url" if is_pdf else "image_url",
        ("document_url" if is_pdf else "image_url"):
            f"data:{'application/pdf' if is_pdf else 'image/'+(suffix or 'png')};base64,{data}",
    }
    body = {"model": model, "document": doc}
    req = _urlreq.Request(endpoint, data=_json.dumps(body).encode("utf-8"), method="POST",
                          headers={"Content-Type": "application/json",
                                   "Authorization": f"Bearer {key}"})
    with _urlreq.urlopen(req, timeout=120) as resp:
        payload = _json.load(resp)
    # Formato de respuesta de mistral-ocr: {pages:[{markdown/text}]}
    pages = payload.get("pages") or []
    if pages:
        return "\n\n".join(p.get("markdown") or p.get("text") or "" for p in pages).strip()
    return str(payload.get("text") or payload.get("content") or "").strip()


def _ocr_via_vision(path: Path, model: str | None = None) -> str:
    """OCR con un LLM de visión (gpt-5.4-pro) vía Responses. Siempre disponible."""
    key = _shared_key()
    host = _shared_host()
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    suffix = path.suffix.lower().lstrip(".") or "png"
    mime = "png" if suffix == "png" else ("jpeg" if suffix in ("jpg", "jpeg") else suffix)
    url = host + "/openai/v1/responses"
    body = {
        "model": model or os.getenv("AZURE_OPENAI_OCR_VISION_MODEL", _OCR_VISION_MODEL),
        "input": [{
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Transcribe EXACTAMENTE todo el texto de esta imagen, conservando la estructura y los saltos de línea. Devuelve solo el texto, sin comentarios."},
                {"type": "input_image", "image_url": f"data:image/{mime};base64,{data}"},
            ],
        }],
        "max_output_tokens": 8000,
    }
    req = _urlreq.Request(url, data=_json.dumps(body).encode("utf-8"), method="POST",
                          headers={"Content-Type": "application/json", "api-key": key})
    with _urlreq.urlopen(req, timeout=90) as resp:
        payload = _json.load(resp)
    return _extract_responses_text(payload)


def ocr_image(image_path: str | Path, *, model: str | None = None) -> str:
    """Extrae texto de una imagen/PDF.

    Estrategia dual (lista para tu deployment de Azure):
      1. Si hay un modelo OCR DEDICADO desplegado (AZURE_OPENAI_OCR_ENDPOINT),
         lo usa (mistral-ocr, etc.).
      2. Si no, o si falla, cae a OCR por VISIÓN de LLM (gpt-5.4-pro), que
         siempre está disponible.
    """
    _ensure_env()
    path = Path(image_path)
    if not path.exists():
        raise RuntimeError(f"No existe la imagen: {path}")
    if not ocr_enabled():
        raise RuntimeError("OCR no configurado (falta clave del recurso).")

    # 1) OCR dedicado si está desplegado.
    if _ocr_dedicated_available():
        try:
            texto = _ocr_via_dedicated(path)
            if texto:
                return texto
        except Exception:
            pass  # cae a visión

    # 2) Fallback: OCR por visión (siempre funciona).
    return _ocr_via_vision(path, model=model)


# ============================================================
#  Lenguaje — Traductor (Azure Translator)
# ============================================================
def translator_enabled() -> bool:
    # Siempre disponible: Azure Translator real si existe, o LLM como fallback.
    _ensure_env()
    return bool(_shared_key() or os.getenv("AZURE_TRANSLATOR_KEY"))


def _translator_configured() -> bool:
    """True solo si hay un recurso Azure Translator REAL (no placeholder)."""
    _ensure_env()
    ep = os.getenv("AZURE_TRANSLATOR_ENDPOINT", "")
    return bool(os.getenv("AZURE_TRANSLATOR_KEY") and ep and "tu-traductor" not in ep)


def translate(text: str, *, to_lang: str = "en", from_lang: str | None = None) -> str:
    """Traduce texto. Usa Azure Translator si hay un recurso real; si no
    (endpoint placeholder), cae a traducción por LLM, que SÍ está desplegado y
    da resultados de alta calidad."""
    _ensure_env()
    if not text.strip():
        return ""

    # 1) Azure Translator real, si está desplegado.
    if _translator_configured():
        import requests
        endpoint = os.getenv("AZURE_TRANSLATOR_ENDPOINT", "").rstrip("/")
        key = os.getenv("AZURE_TRANSLATOR_KEY", "")
        region = os.getenv("AZURE_TRANSLATOR_REGION", "eastus")
        params = {"api-version": "3.0", "to": to_lang}
        if from_lang:
            params["from"] = from_lang
        headers = {
            "Ocp-Apim-Subscription-Key": key,
            "Ocp-Apim-Subscription-Region": region,
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(f"{endpoint}/translate", params=params, headers=headers,
                                 json=[{"text": text}], timeout=30)
            resp.raise_for_status()
            return resp.json()[0]["translations"][0]["text"]
        except Exception:
            pass  # cae al LLM

    # 2) Fallback: traducción por LLM (siempre disponible).
    return translate_with_llm(text, to_lang=to_lang, from_lang=from_lang)


_LANG_NAMES = {
    "en": "inglés", "es": "español", "fr": "francés", "de": "alemán",
    "it": "italiano", "pt": "portugués", "zh": "chino", "ja": "japonés",
}


def translate_with_llm(text: str, *, to_lang: str = "en", from_lang: str | None = None) -> str:
    """Traduce con un LLM del recurso (alta calidad, siempre disponible)."""
    from .llm_bridge import AulaTeXLLMClient

    target = _LANG_NAMES.get(to_lang, to_lang)
    prompt = (
        f"Traduce el siguiente texto al {target}. Devuelve SOLO la traducción, "
        f"sin comentarios ni notas.\n\nTEXTO:\n{text}"
    )
    client = AulaTeXLLMClient()
    result = client.call_with_safety_net(prompt, task="rapido", max_tokens=4000)
    if not result.ok:
        raise RuntimeError(f"Traducción por LLM falló: {result.error}")
    return result.text.strip()


# ============================================================
#  Voz — TTS (Azure Speech)
# ============================================================
def tts_enabled() -> bool:
    _ensure_env()
    return bool(os.getenv("AZURE_SPEECH_KEY") and os.getenv("AZURE_SPEECH_REGION"))


def synthesize_speech(text: str, *, output_dir: Path | None = None,
                      voice: str | None = None) -> Path:
    """Sintetiza voz con Azure Speech y devuelve la ruta del MP3."""
    _ensure_env()
    if not text.strip():
        raise RuntimeError("Texto vacío para TTS.")
    if not tts_enabled():
        raise RuntimeError("TTS no configurado (falta AZURE_SPEECH_KEY/REGION).")

    import requests

    region = os.getenv("AZURE_SPEECH_REGION", "eastus")
    key = os.getenv("AZURE_SPEECH_KEY", "")
    voice_name = voice or os.getenv("AZURE_SPEECH_VOICE", "es-MX-JorgeNeural")
    lang = os.getenv("AZURE_SPEECH_LANGUAGE", "es-MX")
    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    ssml = (
        f'<speak version="1.0" xml:lang="{lang}">'
        f'<voice name="{voice_name}">{text}</voice></speak>'
    )
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3",
    }
    resp = requests.post(url, headers=headers, data=ssml.encode("utf-8"), timeout=60)
    resp.raise_for_status()
    out_dir = output_dir or (Path.cwd() / ".aulatex-temp" / "audio")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"tts_{uuid4().hex}.mp3"
    path.write_bytes(resp.content)
    return path


# ============================================================
#  Inventario del Hub
# ============================================================
def hub_capabilities() -> dict[str, Any]:
    """Reporta el estado de todas las capacidades del Hub disponibles."""
    _ensure_env()
    from .config import credential_status
    from . import visual_bridge

    llms = [s.engine for s in credential_status() if s.ok]
    return {
        "razonamiento": llms,
        "percepcion": {
            "ocr": ocr_enabled(),
            "ocr_model": os.getenv("AZURE_OPENAI_OCR_DEPLOYMENT", ""),
        },
        "expresion": {
            "imagen": visual_bridge.image_enabled(),
            "video": visual_bridge.video_enabled(),
            "voz_tts": tts_enabled(),
        },
        "lenguaje": {
            "traductor": translator_enabled(),
        },
        "total_llms": len(llms),
    }


__all__ = [
    "ocr_enabled", "ocr_image", "translator_enabled", "translate",
    "tts_enabled", "synthesize_speech", "hub_capabilities",
]
