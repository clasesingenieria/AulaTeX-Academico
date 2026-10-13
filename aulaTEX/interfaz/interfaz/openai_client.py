from __future__ import annotations

import os
import requests
from typing import Any, Dict


OPENAI_API_URL = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")


def analyze_text_with_openai(text: str, api_key: str | None = None, model: str = "gpt-3.5-turbo") -> Dict[str, Any]:
    """Send a minimal Chat Completions request to OpenAI and return the JSON response.

    This function is intentionally small and suitable for unit testing (we'll mock requests.post).
    It expects an API key in the environment variable OPENAI_API_KEY or as api_key parameter.
    """
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": text},
        ],
        "max_tokens": 256,
    }

    resp = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=10)
    try:
        resp.raise_for_status()
    except Exception as exc:
        # Surface useful error
        raise RuntimeError(f"OpenAI request failed: {exc} - body: {resp.text}") from exc

    return resp.json()
