from __future__ import annotations

import json
import pytest

from interfaz.openai_client import analyze_text_with_openai


class DummyResp:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data or {"id": "test", "choices": []}
        self.text = text

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._json


def test_analyze_text_with_openai_success(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        assert "Authorization" in headers
        assert json is not None and "messages" in json
        return DummyResp(200, {"id": "ok", "choices": [{"message": {"content": "Resp"}}]})

    monkeypatch.setattr("requests.post", fake_post)
    res = analyze_text_with_openai("hola", api_key="fake-key")
    assert res["id"] == "ok"


def test_analyze_text_with_openai_no_key():
    # Ensure error when no key provided and not in env
    with pytest.raises(RuntimeError):
        analyze_text_with_openai("hola", api_key=None)
