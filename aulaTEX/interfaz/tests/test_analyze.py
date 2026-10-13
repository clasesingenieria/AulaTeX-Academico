from __future__ import annotations

import pytest

from interfaz.analyze import _build_analysis_request, _build_json_repair_request, _detect_text_type, _extract_json, analyze_text
from interfaz.azure_openai_client import build_pdf_input_message, build_responses_payload, extract_response_text, invoke_chat, uses_openai_v1_endpoint
from interfaz.config import Settings


class DummyResponse:
    def __init__(self, status_code=200, body=None, text=""):
        self.status_code = status_code
        self._body = body or {}
        self.text = text

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._body


class DummyOpenAI:
    last_instance = None

    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key
        self.base_url = base_url
        self.calls = []
        self.responses = self
        DummyOpenAI.last_instance = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "output_text": (
                '{"title":"Nota","corrected_text":"Texto limpio.",'
                '"concepts":[],"related_terms":[]}'
            )
        }


def make_settings(tmp_path):
    return Settings(
        telegram_bot_token="token",
        notes_dir=tmp_path / "notes",
        audio_storage_dir=tmp_path / "audio",
        bot_mode="polling",
        azure_speech_key="speech-key",
        azure_speech_region="eastus",
        azure_speech_language="es-MX",
        azure_openai_endpoint="https://example.openai.azure.com/",
        azure_openai_api_key="openai-key",
        azure_openai_chat_deployment="gpt-test",
        azure_openai_api_version="2024-10-21",
    )


def test_extract_json_accepts_fenced_json() -> None:
    assert _extract_json('```json\n{"title": "Hola"}\n```') == {"title": "Hola"}


def test_extract_json_accepts_unescaped_line_breaks_in_strings() -> None:
    data = _extract_json(
        '{"title":"Roma","corrected_text":"Linea uno\nLinea dos","concepts":[],"related_terms":[]}'
    )

    assert data["corrected_text"] == "Linea uno\nLinea dos"


def test_analyze_text_calls_azure_openai_and_normalizes(monkeypatch, tmp_path) -> None:
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return DummyResponse(
            body={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"title":"Cambio climatico","corrected_text":"Texto limpio.",'
                                '"concepts":[{"term":"Clima","definition":"Tema central."}],'
                                '"related_terms":["ambiente"]}'
                            )
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("requests.post", fake_post)

    analysis = analyze_text("texto crudo", "audio.ogg", make_settings(tmp_path), "telegram_voice")

    assert captured["url"] == (
        "https://example.openai.azure.com/openai/deployments/gpt-test/chat/completions"
        "?api-version=2024-10-21"
    )
    assert captured["headers"]["api-key"] == "openai-key"
    assert captured["json"]["response_format"] == {"type": "json_object"}
    assert captured["timeout"] == 120
    assert analysis["title"] == "Cambio climatico"
    assert analysis["text_type"] == "nota_libre"
    assert analysis["corrected_text"] == "Texto limpio."
    assert analysis["concepts"] == [{"term": "Clima", "definition": "Tema central."}]
    assert analysis["related_terms"] == ["ambiente"]
    assert analysis["raw_transcript"] == "texto crudo"
    assert analysis["source_audio"] == "audio.ogg"
    assert analysis["source_type"] == "telegram_voice"


def test_analyze_text_supports_openai_v1_endpoint(monkeypatch, tmp_path) -> None:
    settings = make_settings(tmp_path)
    object.__setattr__(settings, "azure_openai_endpoint", "https://example.services.ai.azure.com/openai/v1/")
    object.__setattr__(settings, "azure_openai_chat_deployment", "model-router")

    monkeypatch.setattr("interfaz.azure_openai_client.OpenAI", DummyOpenAI)

    analyze_text("texto crudo", settings=settings)

    assert uses_openai_v1_endpoint(settings.azure_openai_endpoint)
    assert str(DummyOpenAI.last_instance.base_url) == "https://example.services.ai.azure.com/openai/v1/"
    assert DummyOpenAI.last_instance.api_key == "openai-key"
    assert DummyOpenAI.last_instance.calls[0]["model"] == "model-router"
    assert "instructions" in DummyOpenAI.last_instance.calls[0]
    assert "input" in DummyOpenAI.last_instance.calls[0]
    assert DummyOpenAI.last_instance.calls[0]["text"]["format"] == {"type": "json_object"}


def test_analyze_text_supports_responses_endpoint(monkeypatch, tmp_path) -> None:
    settings = make_settings(tmp_path)
    object.__setattr__(
        settings,
        "azure_openai_endpoint",
        "https://example.services.ai.azure.com/api/projects/p/openai/v1/responses",
    )
    object.__setattr__(settings, "azure_openai_chat_deployment", "gpt-test")

    monkeypatch.setattr("interfaz.azure_openai_client.OpenAI", DummyOpenAI)

    analysis = analyze_text("texto crudo", settings=settings)

    assert str(DummyOpenAI.last_instance.base_url) == "https://example.services.ai.azure.com/api/projects/p/openai/v1/"
    assert DummyOpenAI.last_instance.calls[0]["model"] == "gpt-test"
    assert "response_format" not in DummyOpenAI.last_instance.calls[0]
    assert analysis["title"] == "Nota"


def test_extract_response_content_reads_responses_output_items() -> None:
    body = {
        "output": [
            {
                "content": [
                    {
                        "type": "output_text",
                        "text": '{"title":"Nota","corrected_text":"Texto","concepts":[],"related_terms":[]}',
                    }
                ]
            }
        ]
    }

    assert extract_response_text(body).startswith('{"title":"Nota"')


def test_analyze_text_requires_selected_llm_provider(tmp_path) -> None:
    settings = make_settings(tmp_path)
    object.__setattr__(settings, "azure_openai_api_key", "")

    with pytest.raises(RuntimeError, match="proveedor LLM seleccionado"):
        analyze_text("hola", settings=settings)


def test_build_analysis_request_summarizes_documents() -> None:
    request = _build_analysis_request("contenido largo", "telegram_document")

    assert "nota-resumen" in request
    assert "3 minutos de lectura" in request
    assert "DOCUMENTO:" in request
    assert "Tipo textual probable: informativo" in request


def test_build_analysis_request_preserves_questionnaires() -> None:
    request = _build_analysis_request(
        "¿Pregunta uno?\n◯ a. Opcion A\n◯ b. Opcion B\n\n¿Cuestion dos?\n◯ a. Opcion C\n◯ b. Opcion D",
        "telegram_text",
    )

    assert "conservar la estructura original del cuestionario" in request
    assert "No respondas el cuestionario" in request
    assert "no lo conviertas en prosa" in request
    assert "Tipo textual probable: cuestionario" in request


def test_detect_text_type_covers_common_catalog_entries() -> None:
    assert _detect_text_type("Problema 4. Calcula el area de un circulo de radio 3.", "telegram_text") == "problema_enunciado"
    assert _detect_text_type("Paso 1: abre la aplicacion.\nPaso 2: inicia sesion.\nPaso 3: exporta el reporte.", "telegram_text") == "procedimental"
    assert _detect_text_type("Estimado profesor:\nSolicito una prorroga para entregar el informe.\nAtentamente,\nAna", "telegram_text") == "formal"
    assert _detect_text_type("La noche respira\ncomo un vidrio lento\ny la lluvia cae\nsobre mi memoria", "telegram_text") == "lirico"


def test_build_analysis_request_mentions_probable_text_type_for_procedure() -> None:
    request = _build_analysis_request(
        "Paso 1: abre la consola.\nPaso 2: ejecuta el comando.\nPaso 3: valida el resultado.",
        "telegram_text",
    )

    assert "Tipo textual probable: procedimental" in request
    assert "Clasifica la entrada en el campo text_type" in request


def test_build_pdf_input_message_embeds_pdf_as_data_url(tmp_path) -> None:
    pdf_path = tmp_path / "archivo.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    message = build_pdf_input_message(pdf_path, "Resume este PDF")

    assert message[0]["content"][0]["type"] == "input_file"
    assert message[0]["content"][0]["filename"] == "archivo.pdf"
    assert message[0]["content"][0]["file_data"].startswith("data:application/pdf;base64,")
    assert message[0]["content"][1]["text"] == "Resume este PDF"


def test_build_responses_payload_uses_input_override() -> None:
    payload = build_responses_payload(
        [{"role": "system", "content": "Sistema"}, {"role": "user", "content": "Usuario"}],
        max_tokens=100,
        temperature=0.2,
        input_override=[{"role": "user", "content": [{"type": "input_text", "text": "Hola"}]}],
    )

    assert payload["instructions"] == "Sistema"
    assert isinstance(payload["input"], list)
    assert payload["input"][0]["content"][0]["text"] == "Hola"


def test_build_responses_payload_sets_json_format_when_requested() -> None:
    payload = build_responses_payload(
        [{"role": "system", "content": "Sistema"}, {"role": "user", "content": "Usuario"}],
        max_tokens=100,
        temperature=0.2,
        response_format_json=True,
    )

    assert payload["text"]["format"] == {"type": "json_object"}


def test_build_json_repair_request_mentions_invalid_response() -> None:
    request = _build_json_repair_request("contenido largo", "telegram_document", "{mal}")

    assert "RESPUESTA_PREVIA_INVALIDA" in request
    assert "DOCUMENTO_FUENTE" in request


def test_analyze_text_retries_when_first_response_is_invalid_json(monkeypatch, tmp_path) -> None:
    settings = make_settings(tmp_path)
    calls = []
    responses = iter(
        [
            '{"title":"Nota","corrected_text":"Texto roto","concepts" [}',
            '{"title":"Nota reparada","corrected_text":"Texto limpio.","concepts":[],"related_terms":["pdf"]}',
        ]
    )

    def fake_invoke_chat(current_settings, messages, max_tokens=2048, temperature=0.7, response_format_json=False):
        calls.append(
            {
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "response_format_json": response_format_json,
            }
        )
        return next(responses)

    monkeypatch.setattr("interfaz.analyze.invoke_chat", fake_invoke_chat)

    analysis = analyze_text("contenido pdf", "archivo.pdf", settings, "telegram_document")

    assert analysis["title"] == "Nota reparada"
    assert analysis["related_terms"] == ["pdf"]
    assert len(calls) == 2
    assert calls[0]["temperature"] == 0.2
    assert calls[1]["temperature"] == 0
    assert calls[1]["response_format_json"] is True
    assert "RESPUESTA_PREVIA_INVALIDA" in calls[1]["messages"][1]["content"]


def test_analyze_text_tries_direct_pdf_input_on_v1_before_text_fallback(monkeypatch, tmp_path) -> None:
    settings = make_settings(tmp_path)
    object.__setattr__(settings, "azure_openai_endpoint", "https://example.services.ai.azure.com/openai/v1/")
    pdf_path = tmp_path / "entrada.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    calls = []

    def fake_invoke_chat(current_settings, messages, max_tokens=2048, temperature=0.7, response_format_json=False, input_override=None):
        calls.append({"messages": messages, "input_override": input_override})
        if input_override is not None:
            raise RuntimeError("input_file temporalmente no disponible")
        return '{"title":"Fallback","corrected_text":"Texto limpio","concepts":[],"related_terms":[]}'

    monkeypatch.setattr("interfaz.analyze.invoke_chat", fake_invoke_chat)

    analysis = analyze_text("texto extraido", str(pdf_path), settings, "telegram_document")

    assert analysis["title"] == "Fallback"
    assert len(calls) == 2
    assert calls[0]["input_override"] is not None
    assert calls[1]["input_override"] is None


def test_analyze_text_preserves_questionnaire_when_model_over_summarizes(monkeypatch, tmp_path) -> None:
    settings = make_settings(tmp_path)
    questionnaire = (
        "¿Que herramienta facilita la comunicacion instantanea entre equipos dispersos geograficamente?\n"
        "◯ a. Redes Sociales Corporativas\n"
        "◯ b. Herramientas de Gestion de Proyectos\n"
        "◯ c. Comunicacion Virtual\n"
        "◯ d. Intranet Corporativa\n\n"
        "¿Cual es un beneficio de una comunicacion organizacional efectiva en la toma de decisiones?\n"
        "◯ a. Reduce la necesidad de feedback\n"
        "◯ b. Facilita la coordinacion y colaboracion\n"
        "◯ c. Aumenta el numero de reuniones\n"
        "◯ d. Aumenta los conflictos"
    )

    def fake_invoke_chat(current_settings, messages, max_tokens=2048, temperature=0.7, response_format_json=False):
        return (
            '{"title":"Principios de comunicacion organizacional efectiva",'
            '"corrected_text":"La comunicacion organizacional efectiva mejora la coordinacion y la colaboracion.",'
            '"concepts":[{"term":"Comunicacion virtual","definition":"Permite conectar equipos."}],'
            '"related_terms":["liderazgo inclusivo"]}'
        )

    monkeypatch.setattr("interfaz.analyze.invoke_chat", fake_invoke_chat)

    analysis = analyze_text(questionnaire, settings=settings, source_type="telegram_text")

    assert analysis["text_type"] == "cuestionario"
    assert analysis["corrected_text"] == questionnaire
    assert analysis["concepts"] == [{"term": "Comunicacion virtual", "definition": "Permite conectar equipos."}]


def test_invoke_chat_retries_v1_incomplete_response_without_text(monkeypatch, tmp_path) -> None:
    settings = make_settings(tmp_path)
    object.__setattr__(settings, "azure_openai_endpoint", "https://example.services.ai.azure.com/openai/v1/")
    calls = []

    class IncompleteResponse:
        status = "incomplete"
        incomplete_details = {"reason": "max_output_tokens"}
        output_text = None
        output = []

    class CompleteResponse:
        status = "completed"
        incomplete_details = None
        output_text = '{"title":"Nota","corrected_text":"Texto","concepts":[],"related_terms":[]}'
        output = []

    class IncompleteThenCompleteOpenAI:
        def __init__(self, api_key=None, base_url=None):
            self.responses = self

        def create(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return IncompleteResponse()
            return CompleteResponse()

    monkeypatch.setattr("interfaz.azure_openai_client.OpenAI", IncompleteThenCompleteOpenAI)

    content = invoke_chat(
        settings,
        [{"role": "system", "content": "Sistema"}, {"role": "user", "content": "Usuario"}],
        max_tokens=settings.azure_openai_max_output_tokens,
        temperature=0.2,
        response_format_json=True,
    )

    assert content.startswith('{"title":"Nota"')
    assert len(calls) == 2
    assert calls[0]["text"]["format"] == {"type": "json_object"}
    assert calls[1]["max_output_tokens"] == settings.azure_openai_max_output_tokens
