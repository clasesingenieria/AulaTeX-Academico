from __future__ import annotations

import asyncio
from pathlib import Path

from src import bot
from interfaz.bot import _build_audio_filename, _build_document_filename, _resolve_audio_attachment, _resolve_document_attachment
from interfaz.config import Settings


class DummySentMessage:
    def __init__(self, parent, index, text):
        self._parent = parent
        self._index = index
        self.text = text

    async def edit_text(self, new_text):
        self.text = new_text
        self._parent.replies[self._index] = new_text

    async def edit_reply_markup(self, reply_markup=None, **kwargs):
        self._parent.reply_markup_edits.append(reply_markup)


class DummyMessage:
    def __init__(self, voice=None, audio=None, document=None):
        self.voice = voice
        self.audio = audio
        self.document = document
        self.replies = []
        self.reply_kwargs = []
        self.voice_replies = []
        self.audio_replies = []
        self.document_replies = []
        self.reply_markup_edits = []

    async def reply_text(self, text, **kwargs):
        index = len(self.replies)
        self.replies.append(text)
        self.reply_kwargs.append(kwargs)
        return DummySentMessage(self, index, text)

    async def edit_reply_markup(self, reply_markup=None, **kwargs):
        self.reply_markup_edits.append(reply_markup)

    async def reply_voice(self, voice=None, audio=None, **kwargs):
        payload = voice if voice is not None else audio
        self.voice_replies.append({"voice": payload, "kwargs": kwargs})

    async def reply_audio(self, audio=None, **kwargs):
        self.audio_replies.append({"audio": audio, "kwargs": kwargs})

    async def reply_document(self, document=None, **kwargs):
        self.document_replies.append({"document": document, "kwargs": kwargs})
        return DummySentMessage(self, len(self.replies), kwargs.get("caption", ""))


class DummyUpdate:
    def __init__(self, message=None, callback_query=None):
        self.message = message
        self.callback_query = callback_query


class DummyContext:
    def __init__(self, args=None):
        self.user_data = {}
        self.args = args or []


class DummyCallbackQuery:
    def __init__(self, data, message=None):
        self.data = data
        self.message = message
        self.answers = []

    async def answer(self, text=None):
        self.answers.append(text)


class DummyVoice:
    file_unique_id = "voice-123"

    async def get_file(self):
        return DummyTelegramFile()


class DummyAudio:
    file_unique_id = "audio-456"
    file_name = "clip.mp3"

    async def get_file(self):
        return DummyTelegramFile()


class DummyDocument:
    def __init__(self, file_name="archivo.pdf", file_unique_id="document-789"):
        self.file_name = file_name
        self.file_unique_id = file_unique_id

    async def get_file(self):
        return DummyTelegramFile()


class DummyTelegramFile:
    async def download_to_drive(self, destination):
        Path(destination).write_bytes(b"audio")


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        telegram_bot_token="token",
        notes_dir=tmp_path / "notes",
        audio_storage_dir=tmp_path / "audio",
        bot_mode="polling",
        azure_speech_key="speech-key",
        azure_speech_region="eastus",
        azure_speech_language="es-MX",
    )


def reset_bot_runtime() -> None:
    bot._NOTE_CONTEXT_REGISTRY.clear()
    bot._DERIVATIVE_JOB_QUEUE = None
    bot._DERIVATIVE_PROCESSOR_TASK = None
    bot._DERIVATIVE_PROCESSOR_LOOP = None
    bot._TELEGRAM_SEND_LOCK = None
    bot._DERIVATIVE_SAVE_LOCK = None
    bot._FOREGROUND_NOTE_EVENT = None
    bot._FOREGROUND_NOTE_COUNT = 0
    bot._TELEGRAM_SEND_LOOP = None


def run_async(coro, wait_background: bool = False):
    async def runner():
        result = await coro
        if wait_background:
            await bot._wait_for_background_jobs()
        return result

    return asyncio.run(runner())


def test_resolve_audio_attachment_prefers_voice() -> None:
    voice = DummyVoice()
    audio = DummyAudio()
    update = DummyUpdate(DummyMessage(voice=voice, audio=audio))

    attachment = _resolve_audio_attachment(update)

    assert attachment == (voice, "voice")


def test_resolve_audio_attachment_uses_audio() -> None:
    audio = DummyAudio()
    update = DummyUpdate(DummyMessage(audio=audio))

    attachment = _resolve_audio_attachment(update)

    assert attachment == (audio, "audio")


def test_resolve_document_attachment_uses_document() -> None:
    document = DummyDocument()
    update = DummyUpdate(DummyMessage(document=document))

    attachment = _resolve_document_attachment(update)

    assert attachment is document


def test_build_audio_filename_uses_voice_default_extension() -> None:
    assert _build_audio_filename("abc123", "voice") == "abc123.ogg"


def test_build_audio_filename_keeps_original_extension() -> None:
    assert _build_audio_filename("abc123", "audio", "nota.mp3") == "abc123.mp3"


def test_build_document_filename_keeps_original_extension() -> None:
    assert _build_document_filename("doc123", "nota.PDF") == "doc123.pdf"


def test_handle_audio_transcribes_and_saves_note(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    monkeypatch.setattr(bot, "_copy_clean_note_to_clipboard", lambda analysis: True)
    monkeypatch.setattr(bot, "invoke_chat", lambda *args, **kwargs: "Derivado listo.")

    def fake_transcribe(audio_path: str, transcribe_settings: Settings) -> str:
        assert transcribe_settings is settings
        assert Path(audio_path).exists()
        return "hola desde audio"

    monkeypatch.setattr(bot, "transcribe_audio", fake_transcribe)
    monkeypatch.setattr(
        bot,
        "analyze_text",
        lambda text, source_audio, analysis_settings, source_type: {
            "title": "Audio de prueba",
            "corrected_text": "Hola desde audio.",
            "concepts": [{"term": "Audio", "definition": "Contenido enviado por voz."}],
            "related_terms": ["telegram"],
            "raw_transcript": text,
            "source_audio": source_audio,
            "source_type": source_type,
        },
    )

    message = DummyMessage(voice=DummyVoice())
    update = DummyUpdate(message)
    context = DummyContext()

    run_async(bot.handle_audio(update, context), wait_background=True)

    assert message.replies[0] == "Audio recibido. Transcribiendo, analizando y guardando nota..."
    assert "Audio de prueba" in message.replies[1]
    assert "Hola desde audio." in message.replies[1]
    assert "Audio: Contenido enviado por voz." in message.replies[1]
    assert "Guardada en:" not in message.replies[1]
    assert str(settings.notes_dir) not in message.replies[1]
    assert message.reply_kwargs[1]["reply_markup"] is not None
    assert len(message.document_replies) == 1
    assert len(context.user_data["notes"]) == 1
    notes = [path for path in settings.notes_dir.rglob("*.md") if path.name != "index.md" and "." not in path.stem]
    assert len(notes) == 1
    assert not any(settings.audio_storage_dir.glob("voice-123*"))


def test_handle_audio_reports_transcription_error_without_note(tmp_path: Path, monkeypatch) -> None:
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)

    def fake_transcribe(audio_path: str, transcribe_settings: Settings) -> str:
        raise RuntimeError("azure no respondio")

    monkeypatch.setattr(bot, "transcribe_audio", fake_transcribe)

    message = DummyMessage(voice=DummyVoice())
    update = DummyUpdate(message)

    asyncio.run(bot.handle_audio(update, None))

    assert message.replies[-1] == "No pude procesar el audio: azure no respondio"
    assert not list(settings.notes_dir.rglob("*.md"))


def test_handle_document_reads_and_saves_note(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    monkeypatch.setattr(bot, "_copy_clean_note_to_clipboard", lambda analysis: True)
    monkeypatch.setattr(bot, "invoke_chat", lambda *args, **kwargs: "Derivado listo.")
    captured = {}

    def fake_read_document_text(file_path: str) -> str:
        path = Path(file_path)
        captured["path"] = path
        assert path.suffix == ".pdf"
        assert path.exists()
        return "contenido del documento"

    monkeypatch.setattr(bot, "read_document_text", fake_read_document_text)
    monkeypatch.setattr(
        bot,
        "analyze_text",
        lambda text, source_audio, analysis_settings, source_type: {
            "title": "Resumen documental",
            "corrected_text": "SÃ­ntesis clara del documento.",
            "concepts": [{"term": "Documento", "definition": "Contenido procesado desde archivo."}],
            "related_terms": ["resumen"],
            "raw_transcript": text,
            "source_audio": source_audio,
            "source_type": source_type,
        },
    )

    message = DummyMessage(document=DummyDocument(file_name="archivo.pdf"))
    update = DummyUpdate(message)
    context = DummyContext()

    run_async(bot.handle_document(update, context), wait_background=True)

    assert message.replies[0] == "Documento recibido. Leyendo, sintetizando y guardando nota..."
    assert "Resumen documental" in message.replies[1]
    assert "SÃ­ntesis clara del documento." in message.replies[1]
    assert message.reply_kwargs[1]["reply_markup"] is not None
    assert len(message.document_replies) == 1
    assert len(context.user_data["notes"]) == 1
    assert captured["path"].suffix == ".pdf"
    assert not captured["path"].exists()
    notes = [path for path in settings.notes_dir.rglob("*.md") if path.name != "index.md" and "." not in path.stem]
    assert len(notes) == 1


def test_handle_document_rejects_unsupported_extension(tmp_path: Path, monkeypatch) -> None:
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)

    message = DummyMessage(document=DummyDocument(file_name="archivo.xlsx"))
    update = DummyUpdate(message)

    asyncio.run(bot.handle_document(update, None))

    assert message.replies == ["Formato de documento no soportado. Usa PDF, TXT, MD o DOCX."]
    assert not list(settings.notes_dir.rglob("*.md"))


def test_handle_document_reports_reply_delivery_errors(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    monkeypatch.setattr(bot, "_copy_clean_note_to_clipboard", lambda analysis: True)
    monkeypatch.setattr(bot, "invoke_chat", lambda *args, **kwargs: "Derivado listo.")
    monkeypatch.setattr(bot, "read_document_text", lambda path: "contenido del documento")
    monkeypatch.setattr(
        bot,
        "analyze_text",
        lambda text, source_audio, analysis_settings, source_type: {
            "title": "Nota de documento",
            "corrected_text": "Texto corregido.",
            "concepts": [],
            "related_terms": [],
            "raw_transcript": text,
            "source_audio": source_audio,
            "source_type": source_type,
        },
    )

    async def fail_reply(*args, **kwargs):
        raise RuntimeError("telegram caido")

    monkeypatch.setattr(bot, "_reply_with_note_actions", fail_reply)

    message = DummyMessage(document=DummyDocument(file_name="nota.txt"))

    asyncio.run(bot.handle_document(DummyUpdate(message), DummyContext()))

    assert message.replies == [
        "Documento recibido. Leyendo, sintetizando y guardando nota...",
        "No pude procesar el documento: telegram caido",
    ]


def test_handle_text_analyzes_and_saves_note(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    monkeypatch.setattr(bot, "_copy_clean_note_to_clipboard", lambda analysis: True)
    monkeypatch.setattr(bot, "invoke_chat", lambda *args, **kwargs: "Derivado listo.")
    monkeypatch.setattr(
        bot,
        "analyze_text",
        lambda text, source_audio, analysis_settings, source_type: {
            "title": "Nota textual",
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
            "raw_transcript": text,
            "source_audio": source_audio,
            "source_type": source_type,
        },
    )

    message = DummyMessage()
    message.text = "texto crudo"
    update = DummyUpdate(message)
    context = DummyContext()

    run_async(bot.handle_text(update, context), wait_background=True)

    assert message.replies[0] == "Texto recibido. Analizando y guardando nota..."
    assert "Nota textual" in message.replies[1]
    assert "Guardada en:" not in message.replies[1]
    assert str(settings.notes_dir) not in message.replies[1]
    assert message.reply_kwargs[1]["reply_markup"] is not None
    assert len(message.document_replies) == 1
    assert len(context.user_data["notes"]) == 1
    notes = [path for path in settings.notes_dir.rglob("*.md") if path.name != "index.md" and "." not in path.stem]
    assert len(notes) == 1
    assert ".dialectic.md" in notes[0].read_text(encoding="utf-8")


def test_handle_text_reports_reply_delivery_errors(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    monkeypatch.setattr(bot, "_copy_clean_note_to_clipboard", lambda analysis: True)
    monkeypatch.setattr(bot, "invoke_chat", lambda *args, **kwargs: "Derivado listo.")
    monkeypatch.setattr(
        bot,
        "analyze_text",
        lambda text, source_audio, analysis_settings, source_type: {
            "title": "Nota textual",
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
            "raw_transcript": text,
            "source_audio": source_audio,
            "source_type": source_type,
        },
    )

    async def fail_reply(*args, **kwargs):
        raise RuntimeError("telegram caido")

    monkeypatch.setattr(bot, "_reply_with_note_actions", fail_reply)

    message = DummyMessage()
    message.text = "texto crudo"

    run_async(bot.handle_text(DummyUpdate(message), DummyContext()), wait_background=True)

    assert message.replies == [
        "Texto recibido. Analizando y guardando nota...",
        "No pude procesar la nota: telegram caido",
    ]


def test_handle_text_routes_motor_prefix(tmp_path: Path, monkeypatch) -> None:
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    captured = {}

    async def fake_handle(message, instruction, context):
        captured["instruction"] = instruction
        captured["context"] = context
        await message.reply_text("Motor OK")

    monkeypatch.setattr(bot, "_handle_intelligent_instruction", fake_handle)

    message = DummyMessage()
    message.text = "motor: planifica UCNL actividad 1"
    context = DummyContext()

    asyncio.run(bot.handle_text(DummyUpdate(message), context))

    assert captured["instruction"] == "planifica UCNL actividad 1"
    assert captured["context"] is context
    assert message.replies == ["Motor OK"]


def test_handle_intelligent_command_uses_context_args(tmp_path: Path, monkeypatch) -> None:
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    captured = {}

    async def fake_handle(message, instruction, context):
        captured["instruction"] = instruction
        captured["context"] = context
        await message.reply_text("Motor OK")

    monkeypatch.setattr(bot, "_handle_intelligent_instruction", fake_handle)

    message = DummyMessage()
    context = DummyContext(args=["planifica", "UCNL", "actividad", "1"])

    asyncio.run(bot.handle_intelligent_command(DummyUpdate(message), context))

    assert captured["instruction"] == "planifica UCNL actividad 1"
    assert captured["context"] is context
    assert message.replies == ["Motor OK"]


def test_note_clean_outputs_are_sent_before_derivatives(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    monkeypatch.setattr(bot, "polly_audio_enabled", lambda settings: True)
    monkeypatch.setattr(bot, "_copy_clean_note_to_clipboard", lambda analysis: True)
    order: list[str] = []

    monkeypatch.setattr(
        bot,
        "analyze_text",
        lambda text, source_audio, analysis_settings, source_type: {
            "title": "Nota textual",
            "corrected_text": "Texto corregido.",
            "concepts": [],
            "related_terms": [],
            "raw_transcript": text,
            "source_audio": source_audio,
            "source_type": source_type,
        },
    )

    original_reply_text = DummyMessage.reply_text
    original_reply_document = DummyMessage.reply_document

    async def tracked_reply_text(self, text, **kwargs):
        if text != "Texto recibido. Analizando y guardando nota...":
            order.append("text")
        return await original_reply_text(self, text, **kwargs)

    async def tracked_reply_document(self, document=None, **kwargs):
        order.append("markdown")
        return await original_reply_document(self, document=document, **kwargs)

    async def tracked_reply_audio_copy(message, text, prefix):
        order.append("audio")
        return True

    async def tracked_enqueue_default_derivatives(note_id):
        note_context = bot._get_note_context(note_id)
        assert note_context is not None
        assert note_context.get("auto_play_after_derivatives") is None
        order.append("derivatives")

    monkeypatch.setattr(DummyMessage, "reply_text", tracked_reply_text)
    monkeypatch.setattr(DummyMessage, "reply_document", tracked_reply_document)
    monkeypatch.setattr(bot, "_reply_audio_copy", tracked_reply_audio_copy)
    monkeypatch.setattr(bot, "_enqueue_default_derivatives", tracked_enqueue_default_derivatives)

    message = DummyMessage()
    message.text = "texto crudo"

    asyncio.run(bot.handle_text(DummyUpdate(message), DummyContext()))

    assert order == ["text", "markdown", "audio", "derivatives"]


def test_long_questionnaire_note_is_sent_as_text_chunks_before_markdown(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    monkeypatch.setattr(bot, "polly_audio_enabled", lambda settings: False)
    monkeypatch.setattr(bot, "_copy_clean_note_to_clipboard", lambda analysis: True)

    async def fake_enqueue_default_derivatives(note_id):
        return None

    monkeypatch.setattr(bot, "_enqueue_default_derivatives", fake_enqueue_default_derivatives)

    questionnaire = "\n".join(
        f"Â¿Pregunta {index}?\na. Opcion A\nb. Opcion B\nc. Opcion C\nd. Opcion D"
        for index in range(1, 90)
    )
    monkeypatch.setattr(
        bot,
        "analyze_text",
        lambda text, source_audio, analysis_settings, source_type: {
            "title": "Cuestionario extenso",
            "text_type": "cuestionario",
            "corrected_text": questionnaire,
            "concepts": [],
            "related_terms": [],
            "raw_transcript": text,
            "source_audio": source_audio,
            "source_type": source_type,
        },
    )

    message = DummyMessage()
    message.text = questionnaire

    asyncio.run(bot.handle_text(DummyUpdate(message), DummyContext()))

    visible_replies = [reply for reply in message.replies if not reply.startswith("Texto recibido.")]
    assert len(visible_replies) > 1
    assert "Â¿Pregunta 1?\na. Opcion A\nb. Opcion B" in "\n".join(visible_replies)
    assert message.reply_kwargs[-1]["reply_markup"] is not None
    assert len(message.document_replies) == 1
    assert message.document_replies[0]["kwargs"]["filename"].endswith("cuestionario_extenso.md")


def test_derivatives_finish_without_auto_play_and_enable_proposal(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    saved = bot.save_note(
        settings.notes_dir,
        {
            "title": "Nota textual",
            "corrected_text": "Texto corregido.",
            "concepts": [],
            "related_terms": [],
        },
    )
    note_id = bot._note_id_from_saved(saved)
    message = DummyMessage()
    bot._NOTE_CONTEXT_REGISTRY[note_id] = {
        "title": saved.title,
        "note_path": str(saved.note_path),
        "corrected_text": "Texto corregido.",
        "concepts": [],
        "related_terms": [],
        "status_message": message,
        "derivative_statuses": {},
        "derivative_texts": {},
        "play_active": False,
        "play_jobs_pending": 0,
    }
    enqueued: list[tuple[str, str, str]] = []
    derivative_batches: list[list[str]] = []

    async def fake_run_derive_jobs_for_note_ordered(note_id_arg, payloads):
        derivative_batches.append([action for _, _, action, _ in payloads])
        for _, payload_note_id, action, _ in payloads:
            enqueued.append(("derive", payload_note_id, action))
            bot._NOTE_CONTEXT_REGISTRY[payload_note_id].setdefault("derivative_statuses", {})[action] = "completed"
        return True

    async def fake_run_derivative_job(job_kind, note_id_arg, action, message_arg):
        enqueued.append((job_kind, note_id_arg, action))

    monkeypatch.setattr(bot, "_run_derive_jobs_for_note_ordered", fake_run_derive_jobs_for_note_ordered)
    monkeypatch.setattr(bot, "_run_derivative_job", fake_run_derivative_job)

    async def scenario():
        await bot._enqueue_default_derivatives(note_id)
        await bot._wait_for_background_jobs()

    asyncio.run(scenario())

    assert derivative_batches == [bot.PLAY_SEQUENCE]
    assert [item[0] for item in enqueued] == ["derive", "derive", "derive", "derive"]
    assert bot._NOTE_CONTEXT_REGISTRY[note_id]["play_active"] is False
    assert bot._NOTE_CONTEXT_REGISTRY[note_id]["play_jobs_pending"] == 0
    assert bot._base_editorial_actions_completed(bot._NOTE_CONTEXT_REGISTRY[note_id]) is True



def test_handle_note_action_enqueues_explanation_and_then_serves_markdown(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    captured = {}
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    saved = bot.save_note(
        settings.notes_dir,
        {
            "title": "Nota textual",
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
        },
    )
    note_id = bot._note_id_from_saved(saved)

    def fake_invoke_chat(settings, messages, max_tokens, temperature, response_format_json):
        captured["messages"] = messages
        captured["max_tokens"] = max_tokens
        captured["temperature"] = temperature
        captured["response_format_json"] = response_format_json
        return "Respuesta generada."

    monkeypatch.setattr(bot, "invoke_chat", fake_invoke_chat)
    monkeypatch.setattr(bot, "polly_audio_enabled", lambda settings: False)
    monkeypatch.setattr(bot, "_copy_text_to_clipboard", lambda text: captured.setdefault("clipboard", text) or True)

    message = DummyMessage()
    context = DummyContext()
    context.user_data["notes"] = {
        note_id: {
            "title": saved.title,
            "note_path": str(saved.note_path),
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
        }
    }

    async def scenario():
        query = DummyCallbackQuery(f"note_action:explain:{note_id}", message)
        await bot.handle_note_action(DummyUpdate(callback_query=query), context)
        assert query.answers == ["Procesando..."]
        assert message.replies == ["Explicar: pendiente. Se esta generando en segundo plano."]
        await bot._wait_for_background_jobs()

        followup_message = DummyMessage()
        followup_query = DummyCallbackQuery(f"note_action:explain:{note_id}", followup_message)
        await bot.handle_note_action(DummyUpdate(callback_query=followup_query), context)
        return followup_message

    followup_message = asyncio.run(scenario())

    assert len(message.reply_markup_edits) >= 2
    assert message.reply_markup_edits[0].inline_keyboard[1][0].text == "â³ Explicar..."
    assert message.reply_markup_edits[-1].inline_keyboard[1][0].text == "âœ… Explicar"
    assert followup_message.document_replies == []
    assert followup_message.replies == ["Explicar: copiado al portapapeles."]
    derivative_file = saved.note_path.with_name(f"{saved.note_path.stem}.explain.md")
    assert derivative_file.exists()
    assert captured["max_tokens"] == settings.azure_openai_max_output_tokens
    assert captured["temperature"] == 0.4
    assert captured["response_format_json"] is False
    assert "Explica la idea" in captured["messages"][1]["content"]
    assert "Texto corregido." in captured["messages"][1]["content"]
    assert "Contenido:" in captured["messages"][1]["content"]
    assert "Nota limpia:" not in captured["messages"][1]["content"]


def test_handle_note_action_persists_markdown_derivative(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    saved = bot.save_note(
        settings.notes_dir,
        {
            "title": "Nota persistible",
            "corrected_text": "Texto persistible.",
            "concepts": [],
            "related_terms": [],
        },
    )
    note_id = bot._note_id_from_saved(saved)

    monkeypatch.setattr(bot, "invoke_chat", lambda *args, **kwargs: "Respuesta guardada.")
    monkeypatch.setattr(bot, "polly_audio_enabled", lambda settings: False)
    monkeypatch.setattr(bot, "_copy_text_to_clipboard", lambda text: True)

    message = DummyMessage()
    context = DummyContext()
    context.user_data["notes"] = {
        note_id: {
            "title": saved.title,
            "note_path": str(saved.note_path),
            "corrected_text": "Texto persistible.",
            "concepts": [],
            "related_terms": [],
        }
    }

    async def scenario():
        await bot.handle_note_action(DummyUpdate(callback_query=DummyCallbackQuery(f"note_action:explain:{note_id}", message)), context)
        await bot._wait_for_background_jobs()

    asyncio.run(scenario())

    derivative_path = saved.note_path.with_name(f"{saved.note_path.stem}.explain.md")
    assert derivative_path.exists()
    assert "Respuesta guardada." in derivative_path.read_text(encoding="utf-8")
    assert derivative_path.name in saved.note_path.read_text(encoding="utf-8")


def test_proposal_action_is_locked_until_base_derivatives_complete(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    saved = bot.save_note(settings.notes_dir, {"title": "Nota", "corrected_text": "x", "concepts": [], "related_terms": []})
    note_id = bot._note_id_from_saved(saved)
    message = DummyMessage()
    context = DummyContext()
    context.user_data["notes"] = {
        note_id: {
            "title": saved.title,
            "note_path": str(saved.note_path),
            "corrected_text": "x",
            "concepts": [],
            "related_terms": [],
            "derivative_statuses": {"explain": "completed"},
            "derivative_texts": {},
        }
    }

    asyncio.run(bot.handle_note_action(DummyUpdate(callback_query=DummyCallbackQuery(f"note_action:proposal:{note_id}", message)), context))

    assert message.replies == ["Propuesta: disponible cuando terminen Explicar, Sugerencias, Investigar y Dialectica."]
    assert not saved.note_path.with_name(f"{saved.note_path.stem}.proposal.md").exists()


def test_proposal_action_persists_editorial_instruction(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    saved = bot.save_note(settings.notes_dir, {"title": "Nota", "corrected_text": "x", "concepts": [], "related_terms": []})
    note_id = bot._note_id_from_saved(saved)
    message = DummyMessage()
    context = DummyContext()
    context.user_data["notes"] = {
        note_id: {
            "title": saved.title,
            "note_path": str(saved.note_path),
            "corrected_text": "x",
            "concepts": [],
            "related_terms": [],
            "derivative_statuses": {action: "completed" for action in bot.PLAY_SEQUENCE},
            "derivative_texts": {},
        }
    }

    class DummyProposal:
        instruction = "planifica . con backend langgraph maximo 1 objetivo"
        backend = "langgraph"
        target_hint = "."
        sections = {
            "Nucleo": "Objetivo editorial.",
            "Desarrollo": "CampaÃ±a sobre repositorio.",
            "Accionables": "Ejecutar propuesta.",
            "Evidencias y supuestos": "Depende del inventario.",
            "Sintesis breve": "Realizar lote inicial.",
        }

    monkeypatch.setattr(bot, "build_editorial_proposal", lambda *args, **kwargs: DummyProposal())
    monkeypatch.setattr(bot, "polly_audio_enabled", lambda settings: False)

    async def scenario():
        await bot.handle_note_action(DummyUpdate(callback_query=DummyCallbackQuery(f"note_action:proposal:{note_id}", message)), context)
        await bot._wait_for_background_jobs()

    asyncio.run(scenario())

    proposal_file = saved.note_path.with_name(f"{saved.note_path.stem}.proposal.md")
    assert proposal_file.exists()
    proposal_payload = bot._parse_derivative_markdown(proposal_file.read_text(encoding="utf-8"))
    assert proposal_payload["metadata"]["editorial_instruction"] == "planifica . con backend langgraph maximo 1 objetivo"
    assert bot._proposal_ready(note_id, context.user_data["notes"][note_id]) is True


def test_realize_action_uses_persisted_proposal_instruction(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    saved = bot.save_note(settings.notes_dir, {"title": "Nota", "corrected_text": "x", "concepts": [], "related_terms": []})
    note_id = bot._note_id_from_saved(saved)
    bot.save_note_derivative(
        saved.note_path,
        "proposal",
        "## Nucleo\n\nPropuesta.",
        saved.title,
        extra_metadata={"editorial_instruction": "planifica UCNL actividad 1"},
    )
    message = DummyMessage()
    context = DummyContext()
    context.user_data["notes"] = {
        note_id: {
            "title": saved.title,
            "note_path": str(saved.note_path),
            "corrected_text": "x",
            "concepts": [],
            "related_terms": [],
            "derivative_statuses": {**{action: "completed" for action in bot.PLAY_SEQUENCE}, "proposal": "completed"},
            "derivative_texts": {},
        }
    }
    captured = {}

    class DummyDispatchResult:
        run_dir = tmp_path
        manifest_path = tmp_path / "manifest.json"
        report_path = tmp_path / "report.md"

    class DummyDispatch:
        result = DummyDispatchResult()

    DummyDispatchResult.report_path.write_text("# Reporte\n", encoding="utf-8")

    def fake_dispatch(instruction, settings_arg, **kwargs):
        captured["instruction"] = instruction
        captured["execution_mode"] = kwargs.get("execution_mode")
        return DummyDispatch()

    monkeypatch.setattr(bot, "run_intelligent_dispatch", fake_dispatch)
    monkeypatch.setattr(bot, "format_dispatch_summary", lambda dispatch: "Motor inteligente ejecutado.")
    monkeypatch.setattr(bot, "polly_audio_enabled", lambda settings: False)

    asyncio.run(bot.handle_note_action(DummyUpdate(callback_query=DummyCallbackQuery(f"note_action:realize:{note_id}", message)), context))

    assert captured["instruction"] == "planifica UCNL actividad 1"
    assert "Realizar: ejecutando propuesta" in message.replies[0]
    assert "Motor inteligente ejecutado." in message.replies[1]
    assert message.document_replies


def test_build_channel_text_keeps_derivative_complete_for_telegram() -> None:
    repeated = " ".join([f"bloque-{index}" for index in range(220)])
    payload = {
        "title": "Explicar",
        "source_title": "20:10 - Excedente y explotaciÃ³n en sociedades complejas",
        "sections": {
            "Nucleo": f"Inicio\n{repeated}\ncierre-nucleo-completo",
            "Desarrollo": "Desarrollo completo\ncon cierre-desarrollo-completo",
            "Accionables": "Paso 1.\nPaso 2.\ncierre-accionables-completo",
            "Evidencias y supuestos": "Base y limites cierre-evidencias-completo",
            "Sintesis breve": "Resumen final cierre-sintesis-completo",
        },
    }

    telegram_text = bot._build_channel_text(payload, "telegram")
    clipboard_text = bot._build_channel_text(payload, "clipboard")

    assert telegram_text.startswith("Excedente y explotaciÃ³n en sociedades complejas - ExplicaciÃ³n\n\nInicio\n")
    assert "20:10 -" not in telegram_text
    assert "Inicio\n" in telegram_text
    assert "Desarrollo completo\ncon cierre-desarrollo-completo" in telegram_text
    assert "Paso 1.\nPaso 2.\ncierre-accionables-completo" in telegram_text
    assert "cierre-nucleo-completo" in telegram_text
    assert "cierre-desarrollo-completo" in telegram_text
    assert "cierre-accionables-completo" in telegram_text
    assert "cierre-sintesis-completo" in telegram_text
    assert "cierre-evidencias-completo" not in telegram_text
    assert clipboard_text.startswith("Excedente y explotaciÃ³n en sociedades complejas - ExplicaciÃ³n\n\n")


def test_build_channel_text_formats_clipboard_with_note_title_and_line_breaks() -> None:
    markdown = """# Explicar

Nota origen: [20:10 - Excedente y explotaciÃ³n en sociedades complejas](nota.md)

## Metadata

{}

## Sintesis breve

Linea uno
Linea dos

## Nucleo

- punto A
- punto B

## Accionables

1. Paso uno
2. Paso dos
"""

    payload = bot._parse_derivative_markdown(markdown)

    clipboard_text = bot._build_channel_text(payload, "clipboard")

    assert clipboard_text.startswith("Excedente y explotaciÃ³n en sociedades complejas - ExplicaciÃ³n\n\n")
    assert "20:10 -" not in clipboard_text
    assert "Linea uno\nLinea dos" in clipboard_text
    assert "- punto A\n- punto B" in clipboard_text
    assert "1. Paso uno\n2. Paso dos" in clipboard_text


def test_handle_note_action_play_sends_only_audio(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    calls: list[dict] = []
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    saved = bot.save_note(
        settings.notes_dir,
        {
            "title": "Nota textual",
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
        },
    )
    note_id = bot._note_id_from_saved(saved)

    def fake_invoke_chat(settings, messages, max_tokens, temperature, response_format_json):
        user_content = messages[1]["content"]
        if "Explica la idea" in user_content:
            return "Salida explicar"
        if "Genera sugerencias practicas" in user_content:
            return "Salida sugerencias"
        if "Investiga y sintetiza" in user_content:
            return "Salida investigar"
        if "Analiza la idea con metodo dialectico" in user_content:
            return "Salida dialectica"
        return "Salida"

    async def fake_send_or_resume_play_audio(message, note_id_arg, action, text, prefix):
        calls.append({"text": text, "prefix": prefix})
        return True

    monkeypatch.setattr(bot, "invoke_chat", fake_invoke_chat)
    monkeypatch.setattr(bot, "_send_or_resume_play_audio", fake_send_or_resume_play_audio)
    monkeypatch.setattr(bot, "polly_audio_enabled", lambda settings: True)

    message = DummyMessage()
    query = DummyCallbackQuery(f"note_action:play:{note_id}", message)
    update = DummyUpdate(callback_query=query)
    context = DummyContext()
    context.user_data["notes"] = {
        note_id: {
            "title": saved.title,
            "note_path": str(saved.note_path),
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
            "status_message": message,
        }
    }

    run_async(bot.handle_note_action(update, context), wait_background=True)

    assert query.answers == ["Procesando..."]
    assert message.replies == []
    assert message.reply_markup_edits[0].inline_keyboard[0][0].text == "â³ Play..."
    assert message.reply_markup_edits[-1].inline_keyboard[0][0].text == "Play"
    assert len(calls) == 4
    assert calls[0]["text"].startswith("Explicacion.")
    assert calls[1]["text"].startswith("Sugerencias.")
    assert calls[2]["text"].startswith("Investigacion.")
    assert calls[3]["text"].startswith("Dialectica.")
    assert calls[0]["prefix"].endswith("_play")


def test_handle_note_action_play_recovers_after_audio_failure(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    saved = bot.save_note(
        settings.notes_dir,
        {
            "title": "Nota textual",
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
        },
    )
    note_id = bot._note_id_from_saved(saved)

    def fake_invoke_chat(settings, messages, max_tokens, temperature, response_format_json):
        user_content = messages[1]["content"]
        if "Explica la idea" in user_content:
            return "Salida explicar"
        if "Genera sugerencias practicas" in user_content:
            return "Salida sugerencias"
        if "Investiga y sintetiza" in user_content:
            return "Salida investigar"
        if "Analiza la idea con metodo dialectico" in user_content:
            return "Salida dialectica"
        return "Salida"

    calls: list[str] = []

    async def flaky_send_or_resume_play_audio(message, note_id_arg, action, text, prefix):
        calls.append(prefix)
        if len(calls) == 1:
            raise RuntimeError("telegram audio failed")
        return True

    monkeypatch.setattr(bot, "invoke_chat", fake_invoke_chat)
    monkeypatch.setattr(bot, "_send_or_resume_play_audio", flaky_send_or_resume_play_audio)
    monkeypatch.setattr(bot, "polly_audio_enabled", lambda settings: True)

    message = DummyMessage()
    query = DummyCallbackQuery(f"note_action:play:{note_id}", message)
    update = DummyUpdate(callback_query=query)
    context = DummyContext()
    context.user_data["notes"] = {
        note_id: {
            "title": saved.title,
            "note_path": str(saved.note_path),
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
            "status_message": message,
        }
    }

    run_async(bot.handle_note_action(update, context), wait_background=True)

    assert query.answers == ["Procesando..."]
    assert calls == [
        f"action_explain_{note_id}_play",
        f"action_suggest_{note_id}_play",
        f"action_research_{note_id}_play",
        f"action_dialectic_{note_id}_play",
    ]
    assert context.user_data["notes"][note_id]["play_active"] is False
    assert context.user_data["notes"][note_id]["play_jobs_pending"] == 0
    assert message.reply_markup_edits[-1].inline_keyboard[0][0].text == "Play"


def test_handle_note_action_play_retries_final_keyboard_refresh(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    saved = bot.save_note(
        settings.notes_dir,
        {
            "title": "Nota textual",
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
        },
    )
    note_id = bot._note_id_from_saved(saved)

    def fake_invoke_chat(settings, messages, max_tokens, temperature, response_format_json):
        user_content = messages[1]["content"]
        if "Explica la idea" in user_content:
            return "Salida explicar"
        if "Genera sugerencias practicas" in user_content:
            return "Salida sugerencias"
        if "Investiga y sintetiza" in user_content:
            return "Salida investigar"
        if "Analiza la idea con metodo dialectico" in user_content:
            return "Salida dialectica"
        return "Salida"

    async def fake_reply_audio_copy(message, text, prefix):
        return True

    class FlakyKeyboardMessage(DummyMessage):
        def __init__(self):
            super().__init__()
            self._failed_play_reset = False

        async def edit_reply_markup(self, reply_markup=None, **kwargs):
            label = reply_markup.inline_keyboard[0][0].text if reply_markup else ""
            if label == "Play" and not self._failed_play_reset:
                self._failed_play_reset = True
                raise RuntimeError("temporary telegram edit failure")
            await super().edit_reply_markup(reply_markup=reply_markup, **kwargs)

    monkeypatch.setattr(bot, "invoke_chat", fake_invoke_chat)
    monkeypatch.setattr(bot, "_reply_audio_copy", fake_reply_audio_copy)
    monkeypatch.setattr(bot, "polly_audio_enabled", lambda settings: True)

    message = FlakyKeyboardMessage()
    query = DummyCallbackQuery(f"note_action:play:{note_id}", message)
    update = DummyUpdate(callback_query=query)
    context = DummyContext()
    context.user_data["notes"] = {
        note_id: {
            "title": saved.title,
            "note_path": str(saved.note_path),
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
            "status_message": message,
        }
    }

    run_async(bot.handle_note_action(update, context), wait_background=True)

    assert query.answers == ["Procesando..."]
    assert context.user_data["notes"][note_id]["play_active"] is False
    assert context.user_data["notes"][note_id]["play_jobs_pending"] == 0
    assert message._failed_play_reset is True
    assert message.reply_markup_edits[-1].inline_keyboard[0][0].text == "Play"


def test_handle_note_action_play_keeps_retrying_until_clock_is_cleared(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    saved = bot.save_note(
        settings.notes_dir,
        {
            "title": "Nota textual",
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
        },
    )
    note_id = bot._note_id_from_saved(saved)

    def fake_invoke_chat(settings, messages, max_tokens, temperature, response_format_json):
        user_content = messages[1]["content"]
        if "Explica la idea" in user_content:
            return "Salida explicar"
        if "Genera sugerencias practicas" in user_content:
            return "Salida sugerencias"
        if "Investiga y sintetiza" in user_content:
            return "Salida investigar"
        if "Analiza la idea con metodo dialectico" in user_content:
            return "Salida dialectica"
        return "Salida"

    async def fake_reply_audio_copy(message, text, prefix):
        return True

    class VeryFlakyKeyboardMessage(DummyMessage):
        def __init__(self):
            super().__init__()
            self.play_reset_failures = 0

        async def edit_reply_markup(self, reply_markup=None, **kwargs):
            label = reply_markup.inline_keyboard[0][0].text if reply_markup else ""
            if label == "Play" and self.play_reset_failures < 3:
                self.play_reset_failures += 1
                raise RuntimeError("telegram still rejects final play reset")
            await super().edit_reply_markup(reply_markup=reply_markup, **kwargs)

    monkeypatch.setattr(bot, "invoke_chat", fake_invoke_chat)
    monkeypatch.setattr(bot, "_reply_audio_copy", fake_reply_audio_copy)
    monkeypatch.setattr(bot, "polly_audio_enabled", lambda settings: True)

    message = VeryFlakyKeyboardMessage()
    query = DummyCallbackQuery(f"note_action:play:{note_id}", message)
    update = DummyUpdate(callback_query=query)
    context = DummyContext()
    context.user_data["notes"] = {
        note_id: {
            "title": saved.title,
            "note_path": str(saved.note_path),
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
            "status_message": message,
        }
    }

    run_async(bot.handle_note_action(update, context), wait_background=True)

    assert query.answers == ["Procesando..."]
    assert context.user_data["notes"][note_id]["play_active"] is False
    assert context.user_data["notes"][note_id]["play_jobs_pending"] == 0
    assert message.play_reset_failures == 3
    assert message.reply_markup_edits[-1].inline_keyboard[0][0].text == "Play"


def test_play_reuses_persisted_audio_without_regenerating(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    settings.audio_storage_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    monkeypatch.setattr(bot, "polly_audio_enabled", lambda current: True)

    saved = bot.save_note(
        settings.notes_dir,
        {
            "title": "Nota textual",
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
        },
    )
    note_id = bot._note_id_from_saved(saved)
    derivative_file = saved.note_path.with_name(f"{saved.note_path.stem}.explain.md")
    derivative_file.write_text(
        "# Explicar\n\nNota origen: [nota](nota.md)\n\n## Metadata\n\n{}\n\n## Nucleo\n\nSalida explicar\n",
        encoding="utf-8",
    )
    persisted_audio = bot._play_audio_path(note_id, "explain")
    persisted_audio.parent.mkdir(parents=True, exist_ok=True)
    persisted_audio.write_bytes(b"x" * 256)

    def fail_if_regenerated(current, text, prefix):
        raise AssertionError("no deberia regenerar audio si ya existe")

    monkeypatch.setattr(bot, "synthesize_text_to_single_mp3", fail_if_regenerated)

    message = DummyMessage()
    bot._NOTE_CONTEXT_REGISTRY[note_id] = {
        "title": saved.title,
        "note_path": str(saved.note_path),
        "corrected_text": "Texto corregido.",
        "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
        "related_terms": [],
        "derivative_statuses": {"explain": "completed"},
        "derivative_texts": {"explain": "Salida explicar"},
        "status_message": message,
        "play_active": True,
        "play_jobs_pending": 1,
        "play_sent_actions": [],
    }

    asyncio.run(bot._run_derivative_job("play", note_id, "explain", message))

    assert len(message.audio_replies) == 1
    assert message.audio_replies[0]["kwargs"]["filename"] == derivative_file.with_suffix(".mp3").name
    assert bot._play_state_path(note_id).exists()
    assert "explain" in bot._read_play_state(note_id)["sent_actions"]


def test_handle_note_action_play_resumes_only_missing_actions_after_restart(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    calls: list[str] = []
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    saved = bot.save_note(
        settings.notes_dir,
        {
            "title": "Nota textual",
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
        },
    )
    note_id = bot._note_id_from_saved(saved)

    def fake_invoke_chat(settings, messages, max_tokens, temperature, response_format_json):
        user_content = messages[1]["content"]
        if "Investiga y sintetiza" in user_content:
            return "Salida investigar"
        if "Analiza la idea con metodo dialectico" in user_content:
            return "Salida dialectica"
        raise AssertionError("solo deberian generarse las acciones faltantes")

    async def fake_send_or_resume_play_audio(message, note_id_arg, action, text, prefix):
        calls.append(action)
        audio_path = bot._play_audio_path(note_id_arg, action)
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(b"x" * 256)
        await asyncio.to_thread(bot._mark_play_action_sent, note_id_arg, action, bot._get_note_context(note_id_arg))
        return True

    monkeypatch.setattr(bot, "invoke_chat", fake_invoke_chat)
    monkeypatch.setattr(bot, "_send_or_resume_play_audio", fake_send_or_resume_play_audio)
    monkeypatch.setattr(bot, "polly_audio_enabled", lambda settings: True)

    bot._write_play_state(note_id, ["explain", "suggest"])
    bot._play_audio_path(note_id, "explain").parent.mkdir(parents=True, exist_ok=True)
    bot._play_audio_path(note_id, "explain").write_bytes(b"x" * 256)
    bot._play_audio_path(note_id, "suggest").write_bytes(b"x" * 256)

    message = DummyMessage()
    query = DummyCallbackQuery(f"note_action:play:{note_id}", message)
    update = DummyUpdate(callback_query=query)
    context = DummyContext()

    run_async(bot.handle_note_action(update, context), wait_background=True)

    assert query.answers == ["Procesando..."]
    assert calls == ["research", "dialectic"]
    assert message.reply_markup_edits[-1].inline_keyboard[0][0].text == "Play"
    assert not bot._play_audio_path(note_id, "explain").exists()
    assert not bot._play_audio_path(note_id, "suggest").exists()
    assert not bot._play_audio_path(note_id, "research").exists()
    assert not bot._play_audio_path(note_id, "dialectic").exists()
    assert not bot._play_state_path(note_id).exists()


def test_handle_note_action_queues_non_play_action_while_play_is_active(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    notifications: list[str] = []
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    saved = bot.save_note(
        settings.notes_dir,
        {
            "title": "Nota textual",
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
        },
    )
    note_id = bot._note_id_from_saved(saved)

    async def fake_send_text_with_optional_audio(message, text, prefix):
        notifications.append(text)
        return None

    monkeypatch.setattr(bot, "_send_text_with_optional_audio", fake_send_text_with_optional_audio)

    message = DummyMessage()
    query = DummyCallbackQuery(f"note_action:research:{note_id}", message)
    update = DummyUpdate(callback_query=query)
    context = DummyContext()
    context.user_data["notes"] = {
        note_id: {
            "title": saved.title,
            "note_path": str(saved.note_path),
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
            "status_message": message,
            "play_active": True,
            "play_jobs_pending": 2,
            "queued_actions_after_play": [],
        }
    }

    run_async(bot.handle_note_action(update, context))

    assert query.answers == ["Procesando..."]
    assert notifications == ["Investigar: se agrego a la cola para despues de Play."]
    assert context.user_data["notes"][note_id]["queued_actions_after_play"] == ["research"]
    assert message.reply_markup_edits == []


def test_play_drains_queued_actions_after_finishing(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    enqueued_jobs: list[tuple[str, str, str]] = []
    notifications: list[str] = []
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    saved = bot.save_note(
        settings.notes_dir,
        {
            "title": "Nota textual",
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
        },
    )
    note_id = bot._note_id_from_saved(saved)

    derivative_file = saved.note_path.with_name(f"{saved.note_path.stem}.explain.md")
    derivative_file.write_text(
        "# Explicar\n\nNota origen: [nota](nota.md)\n\n## Metadata\n\n{}\n\n## Nucleo\n\nSalida explicar\n",
        encoding="utf-8",
    )

    async def fake_send_or_resume_play_audio(message, note_id_arg, action, text, prefix):
        audio_path = bot._play_audio_path(note_id_arg, action)
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(b"x" * 256)
        await asyncio.to_thread(bot._mark_play_action_sent, note_id_arg, action, bot._get_note_context(note_id_arg))
        return True

    async def fake_enqueue_derivative_job(job_kind, note_id_arg, action, message=None):
        enqueued_jobs.append((job_kind, note_id_arg, action))

    async def fake_send_text_with_optional_audio(message, text, prefix):
        notifications.append(text)
        return None

    monkeypatch.setattr(bot, "_send_or_resume_play_audio", fake_send_or_resume_play_audio)
    monkeypatch.setattr(bot, "_enqueue_derivative_job", fake_enqueue_derivative_job)
    monkeypatch.setattr(bot, "_send_text_with_optional_audio", fake_send_text_with_optional_audio)

    message = DummyMessage()
    bot._NOTE_CONTEXT_REGISTRY[note_id] = bot._register_note_context(
        note_id,
        {
            "title": saved.title,
            "note_path": str(saved.note_path),
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
            "derivative_statuses": {"research": "pending"},
            "derivative_texts": {"explain": "Salida explicar"},
            "status_message": message,
            "play_active": True,
            "play_jobs_pending": 1,
            "play_sent_actions": ["suggest", "research", "dialectic"],
            "queued_actions_after_play": ["research"],
        },
    )

    run_async(bot._run_derivative_job("play", note_id, "explain", message))

    assert enqueued_jobs == [("derive", note_id, "research")]
    assert notifications == ["Investigar: pendiente. Se esta generando en segundo plano."]
    assert bot._get_note_context(note_id)["queued_actions_after_play"] == []


def test_background_derivative_auto_sends_markdown(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)

    saved = bot.save_note(
        settings.notes_dir,
        {
            "title": "Nota textual",
            "corrected_text": "Texto corregido.",
            "concepts": [],
            "related_terms": [],
        },
    )
    note_id = bot._note_id_from_saved(saved)

    derivative_file = saved.note_path.with_name(f"{saved.note_path.stem}.suggest.md")
    derivative_file.write_text(
        "# Sugerencias\n\nNota origen: [nota](nota.md)\n\n## Metadata\n\n{}\n\n## Nucleo\n\nSalida sugerencias\n",
        encoding="utf-8",
    )

    message = DummyMessage()
    bot._NOTE_CONTEXT_REGISTRY[note_id] = bot._register_note_context(
        note_id,
        {
            "title": saved.title,
            "note_path": str(saved.note_path),
            "status_message": message,
        },
    )

    asyncio.run(bot._run_derivative_job("derive", note_id, "suggest", message))

    assert len(message.document_replies) == 1
    assert message.document_replies[0]["kwargs"]["filename"].endswith(".suggest.md")


def test_derivative_actions_use_best_provider_mapping(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    captured_providers: list[str] = []

    saved = bot.save_note(
        settings.notes_dir,
        {
            "title": "Nota textual",
            "corrected_text": "Texto corregido.",
            "concepts": [],
            "related_terms": [],
        },
    )
    note_id = bot._note_id_from_saved(saved)
    bot._NOTE_CONTEXT_REGISTRY[note_id] = bot._register_note_context(
        note_id,
        {
            "title": saved.title,
            "note_path": str(saved.note_path),
            "corrected_text": "Texto corregido.",
            "concepts": [],
            "related_terms": [],
        },
    )

    def fake_settings_for_provider(base_settings, provider):
        captured_providers.append(provider)
        return base_settings

    def fake_invoke_chat(settings_arg, messages, max_tokens, temperature, response_format_json):
        return "Respuesta generada."

    monkeypatch.setattr(bot, "settings_for_llm_provider", fake_settings_for_provider)
    monkeypatch.setattr(bot, "invoke_chat", fake_invoke_chat)

    async def scenario():
        for action in bot.PLAY_SEQUENCE:
            await bot._ensure_derivative_markdown(note_id, action)

    asyncio.run(scenario())

    assert captured_providers == ["claude-foundry", "gpt-pro", "codex", "model-router"]


def test_parallel_default_derivatives_send_markdown_in_action_order(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    send_order: list[str] = []
    start_order: list[str] = []
    release: dict[str, asyncio.Event] = {}

    saved = bot.save_note(
        settings.notes_dir,
        {
            "title": "Nota textual",
            "corrected_text": "Texto corregido.",
            "concepts": [],
            "related_terms": [],
        },
    )
    note_id = bot._note_id_from_saved(saved)
    message = DummyMessage()
    bot._NOTE_CONTEXT_REGISTRY[note_id] = bot._register_note_context(
        note_id,
        {
            "title": saved.title,
            "note_path": str(saved.note_path),
            "corrected_text": "Texto corregido.",
            "concepts": [],
            "related_terms": [],
            "status_message": message,
        },
    )

    async def fake_ensure_derivative_markdown(note_id_arg, action):
        start_order.append(action)
        await release[action].wait()
        path = saved.note_path.with_name(f"{saved.note_path.stem}.{action}.md")
        path.write_text(f"# {action}\n\n## Metadata\n\n{{}}\n\n## Nucleo\n\nSalida {action}\n", encoding="utf-8")
        return path, f"Salida {action}"

    async def fake_reply_markdown_file(message_arg, path, filename):
        send_order.append(Path(filename).suffixes[-2].lstrip("."))

    async def scenario():
        for action in bot.PLAY_SEQUENCE:
            release[action] = asyncio.Event()
        task = asyncio.create_task(
            bot._run_derive_jobs_for_note_ordered(
                note_id,
                [("derive", note_id, action, None) for action in bot.PLAY_SEQUENCE],
            )
        )
        await asyncio.sleep(0)
        for action in reversed(bot.PLAY_SEQUENCE):
            release[action].set()
        return await task

    monkeypatch.setattr(bot, "_ensure_derivative_markdown", fake_ensure_derivative_markdown)
    monkeypatch.setattr(bot, "_reply_markdown_file", fake_reply_markdown_file)

    completed = asyncio.run(scenario())

    assert completed is True
    assert set(start_order) == set(bot.PLAY_SEQUENCE)
    assert send_order == bot.PLAY_SEQUENCE


def test_background_derivative_auto_sends_markdown_using_stored_message(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)

    saved = bot.save_note(settings.notes_dir, {"title": "Nota", "corrected_text": "x", "concepts": [], "related_terms": []})
    note_id = bot._note_id_from_saved(saved)

    derivative_file = saved.note_path.with_name(f"{saved.note_path.stem}.explain.md")
    derivative_file.write_text("# Explicar\n\n## Metadata\n\n{}\n\n## Nucleo\n\nSalida\n", encoding="utf-8")

    message = DummyMessage()
    bot._NOTE_CONTEXT_REGISTRY[note_id] = bot._register_note_context(note_id, {"note_path": str(saved.note_path), "status_message": message})

    asyncio.run(bot._run_derivative_job("derive", note_id, "explain", None))

    assert len(message.document_replies) == 1


def test_queued_suggestions_after_play_clear_clock_and_reply(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    saved = bot.save_note(
        settings.notes_dir,
        {
            "title": "Nota textual",
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
        },
    )
    note_id = bot._note_id_from_saved(saved)

    for action, text in (("explain", "Salida explicar"), ("suggest", "Salida sugerencias")):
        derivative_file = saved.note_path.with_name(f"{saved.note_path.stem}.{action}.md")
        derivative_file.write_text(
            f"# {bot.NOTE_ACTIONS[action]}\n\nNota origen: [nota](nota.md)\n\n## Metadata\n\n{{}}\n\n## Nucleo\n\n{text}\n",
            encoding="utf-8",
        )

    async def fake_send_or_resume_play_audio(message, note_id_arg, action, text, prefix):
        audio_path = bot._play_audio_path(note_id_arg, action)
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(b"x" * 256)
        await asyncio.to_thread(bot._mark_play_action_sent, note_id_arg, action, bot._get_note_context(note_id_arg))
        return True

    monkeypatch.setattr(bot, "_send_or_resume_play_audio", fake_send_or_resume_play_audio)
    monkeypatch.setattr(bot, "_copy_text_to_clipboard", lambda text: True)

    message = DummyMessage()
    bot._NOTE_CONTEXT_REGISTRY[note_id] = bot._register_note_context(
        note_id,
        {
            "title": saved.title,
            "note_path": str(saved.note_path),
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
            "derivative_statuses": {"explain": "completed", "suggest": "completed"},
            "derivative_texts": {"explain": "Salida explicar", "suggest": "Salida sugerencias"},
            "status_message": message,
            "play_active": True,
            "play_jobs_pending": 1,
            "play_sent_actions": ["suggest", "research", "dialectic"],
            "queued_actions_after_play": ["suggest"],
        },
    )

    run_async(bot._run_derivative_job("play", note_id, "explain", message))

    note_context = bot._get_note_context(note_id)
    assert note_context["play_active"] is False
    assert note_context["play_jobs_pending"] == 0
    assert note_context["queued_actions_after_play"] == []
    assert message.reply_markup_edits[-1].inline_keyboard[0][0].text == "Play"
    assert message.document_replies == []
    assert "copiado al portapapeles" in message.replies[-1]


def test_finalize_play_session_cleans_artifacts_only_after_keyboard_reset(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    saved = bot.save_note(
        settings.notes_dir,
        {
            "title": "Nota textual",
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
        },
    )
    note_id = bot._note_id_from_saved(saved)
    for action in bot.PLAY_SEQUENCE:
        audio_path = bot._play_audio_path(note_id, action)
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(b"x" * 256)
    bot._write_play_state(note_id, list(bot.PLAY_SEQUENCE))

    note_context = {
        "title": saved.title,
        "note_path": str(saved.note_path),
        "corrected_text": "Texto corregido.",
        "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
        "related_terms": [],
        "status_message": DummyMessage(),
        "play_active": True,
        "play_jobs_pending": 0,
        "play_sent_actions": list(bot.PLAY_SEQUENCE),
    }
    bot._NOTE_CONTEXT_REGISTRY[note_id] = bot._register_note_context(note_id, note_context)

    async def fake_refresh_failure(note_id_arg):
        return False

    monkeypatch.setattr(bot, "_refresh_note_action_keyboard", fake_refresh_failure)

    asyncio.run(bot._finalize_play_session(note_id))

    assert bot._play_state_path(note_id).exists()
    assert bot._play_audio_path(note_id, "explain").exists()

    async def fake_refresh_success(note_id_arg):
        return True

    monkeypatch.setattr(bot, "_refresh_note_action_keyboard", fake_refresh_success)

    asyncio.run(bot._finalize_play_session(note_id))

    assert not bot._play_state_path(note_id).exists()
    assert not bot._play_audio_path(note_id, "explain").exists()


def test_play_waits_until_foreground_note_delivery_finishes(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    saved = bot.save_note(
        settings.notes_dir,
        {
            "title": "Nota textual",
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
        },
    )
    derivative_file = saved.note_path.with_name(f"{saved.note_path.stem}.explain.md")
    derivative_file.write_text(
        "# Explicar\n\nNota origen: [nota](nota.md)\n\n## Metadata\n\n{}\n\n## Nucleo\n\nSalida explicar\n",
        encoding="utf-8",
    )

    note_id = bot._note_id_from_saved(saved)
    message = DummyMessage()
    bot._NOTE_CONTEXT_REGISTRY[note_id] = {
        "title": saved.title,
        "note_path": str(saved.note_path),
        "corrected_text": "Texto corregido.",
        "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
        "related_terms": [],
        "derivative_statuses": {"explain": "completed"},
        "derivative_texts": {"explain": "Salida explicar"},
        "status_message": message,
        "play_active": False,
        "play_jobs_pending": 0,
    }

    calls: list[str] = []

    async def fake_send_or_resume_play_audio(message, note_id_arg, action, text, prefix):
        calls.append(prefix)
        return True

    monkeypatch.setattr(bot, "_send_or_resume_play_audio", fake_send_or_resume_play_audio)

    async def scenario():
        async with bot._foreground_note_delivery():
            task = asyncio.create_task(bot._run_derivative_job("play", note_id, "explain", message))
            await asyncio.sleep(0)
            assert calls == []
        await task

    asyncio.run(scenario())

    assert calls == [f"action_explain_{note_id}_play"]


def test_handle_note_action_enqueues_research_with_expected_prompt(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    captured = {}
    base_settings = make_settings(tmp_path)
    settings = Settings(
        telegram_bot_token=base_settings.telegram_bot_token,
        notes_dir=base_settings.notes_dir,
        audio_storage_dir=base_settings.audio_storage_dir,
        bot_mode=base_settings.bot_mode,
        azure_speech_key=base_settings.azure_speech_key,
        azure_speech_region=base_settings.azure_speech_region,
        azure_speech_language=base_settings.azure_speech_language,
        research_max_tokens=2400,
        telegram_reply_audio_enabled=base_settings.telegram_reply_audio_enabled,
        aws_access_key_id=base_settings.aws_access_key_id,
        aws_secret_access_key=base_settings.aws_secret_access_key,
        aws_region=base_settings.aws_region,
        aws_polly_voice_id=base_settings.aws_polly_voice_id,
        aws_polly_engine=base_settings.aws_polly_engine,
        aws_polly_language_code=base_settings.aws_polly_language_code,
        aws_polly_sample_rate=base_settings.aws_polly_sample_rate,
        polly_max_chars=base_settings.polly_max_chars,
        azure_openai_endpoint=base_settings.azure_openai_endpoint,
        azure_openai_api_key=base_settings.azure_openai_api_key,
        azure_openai_chat_deployment=base_settings.azure_openai_chat_deployment,
        azure_openai_api_version=base_settings.azure_openai_api_version,
    )
    monkeypatch.setattr(bot, "SETTINGS", settings)
    saved = bot.save_note(
        settings.notes_dir,
        {
            "title": "Nota textual",
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
        },
    )
    note_id = bot._note_id_from_saved(saved)

    def fake_invoke_chat(settings, messages, max_tokens, temperature, response_format_json):
        captured["messages"] = messages
        captured["max_tokens"] = max_tokens
        captured["temperature"] = temperature
        captured["response_format_json"] = response_format_json
        return "Investigacion generada."

    monkeypatch.setattr(bot, "invoke_chat", fake_invoke_chat)
    monkeypatch.setattr(bot, "polly_audio_enabled", lambda settings: False)
    monkeypatch.setattr(bot, "_copy_text_to_clipboard", lambda text: captured.setdefault("clipboard", text) or True)

    message = DummyMessage()
    context = DummyContext()
    context.user_data["notes"] = {
        note_id: {
            "title": saved.title,
            "note_path": str(saved.note_path),
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
        }
    }

    async def scenario():
        query = DummyCallbackQuery(f"note_action:research:{note_id}", message)
        await bot.handle_note_action(DummyUpdate(callback_query=query), context)
        assert query.answers == ["Procesando..."]
        assert message.replies == ["Investigar: pendiente. Se esta generando en segundo plano."]
        await bot._wait_for_background_jobs()

    asyncio.run(scenario())

    assert captured["max_tokens"] == settings.azure_openai_max_output_tokens
    assert captured["temperature"] == 0.4
    assert captured["response_format_json"] is False
    assert "Investiga y sintetiza el tema central" in captured["messages"][1]["content"]
    assert "resumen ejecutivo" in captured["messages"][1]["content"]
    assert "hallazgos e inferencias" in captured["messages"][1]["content"]
    assert "verificacion externa" in captured["messages"][1]["content"]


def test_handle_note_action_loads_saved_note_after_restart(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    saved = bot.save_note(
        settings.notes_dir,
        {
            "title": "Nota persistida",
            "corrected_text": "Texto persistido.",
            "concepts": [{"term": "Idea", "definition": "Concepto guardado."}],
            "related_terms": ["memoria"],
        },
    )
    note_id = bot._note_id_from_saved(saved)
    captured = {}

    def fake_invoke_chat(settings, messages, max_tokens, temperature, response_format_json):
        captured["messages"] = messages
        return "Dialectica generada."

    monkeypatch.setattr(bot, "invoke_chat", fake_invoke_chat)
    monkeypatch.setattr(bot, "polly_audio_enabled", lambda settings: False)
    monkeypatch.setattr(bot, "_copy_text_to_clipboard", lambda text: captured.setdefault("clipboard", text) or True)

    message = DummyMessage()
    context = DummyContext()

    async def scenario():
        query = DummyCallbackQuery(f"note_action:dialectic:{note_id}", message)
        await bot.handle_note_action(DummyUpdate(callback_query=query), context)
        assert query.answers == ["Procesando..."]
        assert message.replies == ["Dialectica: pendiente. Se esta generando en segundo plano."]
        await bot._wait_for_background_jobs()

    asyncio.run(scenario())

    assert note_id in context.user_data["notes"]
    assert "Texto persistido." in captured["messages"][1]["content"]
    assert "Idea: Concepto guardado." in captured["messages"][1]["content"]
    assert "Idea contraria" in captured["messages"][1]["content"]


def test_handle_note_action_reports_missing_note() -> None:
    message = DummyMessage()
    query = DummyCallbackQuery("note_action:suggest:desconocida", message)
    update = DummyUpdate(callback_query=query)
    context = DummyContext()

    asyncio.run(bot.handle_note_action(update, context))

    assert query.answers == ["Procesando..."]
    assert len(message.replies) == 1
    assert message.replies[0].startswith("No encuentro la nota reciente para procesarla.")


def test_reply_audio_copy_sends_single_audio_and_cleans_file(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        telegram_bot_token="token",
        notes_dir=tmp_path / "notes",
        audio_storage_dir=tmp_path / "audio",
        bot_mode="polling",
        azure_speech_key="speech-key",
        azure_speech_region="eastus",
        azure_speech_language="es-MX",
        telegram_reply_audio_enabled=True,
        aws_access_key_id="aws-key",
        aws_secret_access_key="aws-secret",
    )
    monkeypatch.setattr(bot, "SETTINGS", settings)
    monkeypatch.setattr(bot, "polly_audio_enabled", lambda current: True)

    audio_file = settings.audio_storage_dir / "tts" / "reply_merged.mp3"
    audio_file.parent.mkdir(parents=True, exist_ok=True)
    audio_file.write_bytes(b"x" * 256)
    monkeypatch.setattr(bot, "synthesize_text_to_single_mp3", lambda current, text, prefix: audio_file)

    message = DummyMessage()
    asyncio.run(bot._reply_audio_copy(message, "Hola mundo", "test"))

    assert len(message.audio_replies) == 1
    assert message.audio_replies[0]["kwargs"]["filename"] == "Hola_mundo.mp3"
    assert not audio_file.exists()


def test_reply_audio_copy_uses_saved_note_filename_when_prefix_matches_note(tmp_path: Path, monkeypatch) -> None:
    reset_bot_runtime()
    settings = make_settings(tmp_path)
    settings.audio_storage_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(bot, "SETTINGS", settings)
    monkeypatch.setattr(bot, "polly_audio_enabled", lambda current: True)

    saved = bot.save_note(
        settings.notes_dir,
        {
            "title": "Nota textual",
            "corrected_text": "Texto corregido.",
            "concepts": [],
            "related_terms": [],
        },
    )
    note_id = bot._note_id_from_saved(saved)
    bot._NOTE_CONTEXT_REGISTRY[note_id] = {
        "title": saved.title,
        "note_path": str(saved.note_path),
        "corrected_text": "Texto corregido.",
        "concepts": [],
        "related_terms": [],
        "derivative_statuses": {},
        "derivative_texts": {},
    }

    audio_file = settings.audio_storage_dir / "tts" / "reply_note.mp3"
    audio_file.parent.mkdir(parents=True, exist_ok=True)
    audio_file.write_bytes(b"x" * 256)
    monkeypatch.setattr(bot, "synthesize_text_to_single_mp3", lambda current, text, prefix: audio_file)

    message = DummyMessage()
    asyncio.run(bot._reply_audio_copy(message, "Texto hablado", f"note_{note_id}"))

    assert len(message.audio_replies) == 1
    assert message.audio_replies[0]["kwargs"]["filename"] == saved.note_path.with_suffix(".mp3").name
    assert not audio_file.exists()


def test_reply_audio_copy_returns_false_when_reply_audio_fails(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        telegram_bot_token="token",
        notes_dir=tmp_path / "notes",
        audio_storage_dir=tmp_path / "audio",
        bot_mode="polling",
        azure_speech_key="speech-key",
        azure_speech_region="eastus",
        azure_speech_language="es-MX",
        telegram_reply_audio_enabled=True,
        aws_access_key_id="aws-key",
        aws_secret_access_key="aws-secret",
    )
    monkeypatch.setattr(bot, "SETTINGS", settings)
    monkeypatch.setattr(bot, "polly_audio_enabled", lambda current: True)

    audio_file = settings.audio_storage_dir / "tts" / "reply_failed.mp3"
    audio_file.parent.mkdir(parents=True, exist_ok=True)
    audio_file.write_bytes(b"x" * 256)
    monkeypatch.setattr(bot, "synthesize_text_to_single_mp3", lambda current, text, prefix: audio_file)

    class FailingAudioMessage(DummyMessage):
        async def reply_audio(self, audio=None, **kwargs):
            raise RuntimeError("telegram failed")

    message = FailingAudioMessage()
    result = asyncio.run(bot._reply_audio_copy(message, "Hola mundo", "test"))

    assert result is False
    assert not audio_file.exists()


def test_handle_text_sends_audio_copy_when_enabled(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        telegram_bot_token="token",
        notes_dir=tmp_path / "notes",
        audio_storage_dir=tmp_path / "audio",
        bot_mode="polling",
        azure_speech_key="speech-key",
        azure_speech_region="eastus",
        azure_speech_language="es-MX",
        telegram_reply_audio_enabled=True,
        aws_access_key_id="aws-key",
        aws_secret_access_key="aws-secret",
    )
    monkeypatch.setattr(bot, "SETTINGS", settings)
    monkeypatch.setattr(
        bot,
        "analyze_text",
        lambda text, source_audio, analysis_settings, source_type: {
            "title": "Nota textual",
            "corrected_text": "Texto corregido.",
            "concepts": [{"term": "Texto", "definition": "Nota enviada como mensaje."}],
            "related_terms": [],
            "raw_transcript": text,
            "source_audio": source_audio,
            "source_type": source_type,
        },
    )
    captured = {}

    async def fake_reply_audio_copy(message, text, prefix):
        captured["text"] = text
        captured["prefix"] = prefix
        return True

    monkeypatch.setattr(bot, "_reply_audio_copy", fake_reply_audio_copy)

    message = DummyMessage()
    message.text = "texto crudo"
    update = DummyUpdate(message)
    context = DummyContext()

    asyncio.run(bot.handle_text(update, context))

    assert "Nota textual" in captured["text"]
    assert captured["prefix"].startswith("note_")


def test_send_text_with_optional_audio_keeps_original_message_with_buttons(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        telegram_bot_token="token",
        notes_dir=tmp_path / "notes",
        audio_storage_dir=tmp_path / "audio",
        bot_mode="polling",
        azure_speech_key="speech-key",
        azure_speech_region="eastus",
        azure_speech_language="es-MX",
        telegram_reply_audio_enabled=True,
        aws_access_key_id="aws-key",
        aws_secret_access_key="aws-secret",
    )
    monkeypatch.setattr(bot, "SETTINGS", settings)

    async def fake_reply_audio_copy(message, text, prefix):
        return True

    monkeypatch.setattr(bot, "_reply_audio_copy", fake_reply_audio_copy)

    message = DummyMessage()
    asyncio.run(bot._send_text_with_optional_audio(message, "Texto principal", "note_test_prefix", reply_markup={"k": "v"}))

    assert message.replies[0] == "Texto principal"
    assert message.reply_kwargs[0]["reply_markup"] == {"k": "v"}
    assert len(message.replies) == 1


def test_send_text_with_optional_audio_sends_long_text_as_single_document(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        telegram_bot_token="token",
        notes_dir=tmp_path / "notes",
        audio_storage_dir=tmp_path / "audio",
        bot_mode="polling",
        azure_speech_key="speech-key",
        azure_speech_region="eastus",
        azure_speech_language="es-MX",
        telegram_reply_audio_enabled=False,
    )
    monkeypatch.setattr(bot, "SETTINGS", settings)

    message = DummyMessage()
    long_text = "Linea de respuesta larga. " * 300
    asyncio.run(bot._send_text_with_optional_audio(message, long_text, "action_long", reply_markup={"k": "v"}))

    assert message.replies == []
    assert len(message.document_replies) == 1
    assert message.document_replies[0]["kwargs"]["filename"] == "action_long.md"
    assert message.document_replies[0]["kwargs"]["caption"] == "Respuesta completa en un solo archivo."
    assert message.document_replies[0]["kwargs"]["reply_markup"] == {"k": "v"}


def test_send_text_with_optional_audio_skips_status_prefix(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        telegram_bot_token="token",
        notes_dir=tmp_path / "notes",
        audio_storage_dir=tmp_path / "audio",
        bot_mode="polling",
        azure_speech_key="speech-key",
        azure_speech_region="eastus",
        azure_speech_language="es-MX",
        telegram_reply_audio_enabled=True,
        aws_access_key_id="aws-key",
        aws_secret_access_key="aws-secret",
    )
    monkeypatch.setattr(bot, "SETTINGS", settings)
    calls = {"count": 0}

    async def fake_reply_audio_copy(message, text, prefix):
        calls["count"] += 1
        return True

    monkeypatch.setattr(bot, "_reply_audio_copy", fake_reply_audio_copy)

    message = DummyMessage()
    asyncio.run(bot._send_text_with_optional_audio(message, "Texto recibido. Analizando y guardando nota...", "processing_text"))

    assert calls["count"] == 0
    assert message.replies == ["Texto recibido. Analizando y guardando nota..."]


def test_send_note_reply_with_audio_sends_text_before_audio(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        telegram_bot_token="token",
        notes_dir=tmp_path / "notes",
        audio_storage_dir=tmp_path / "audio",
        bot_mode="polling",
        azure_speech_key="speech-key",
        azure_speech_region="eastus",
        azure_speech_language="es-MX",
        telegram_reply_audio_enabled=True,
        aws_access_key_id="aws-key",
        aws_secret_access_key="aws-secret",
    )
    monkeypatch.setattr(bot, "SETTINGS", settings)

    order: list[str] = []

    async def fake_reply_audio_copy(message, text, prefix):
        order.append("audio")
        return True

    original_reply_text = DummyMessage.reply_text

    async def tracked_reply_text(self, text, **kwargs):
        order.append("text")
        return await original_reply_text(self, text, **kwargs)

    monkeypatch.setattr(bot, "_reply_audio_copy", fake_reply_audio_copy)
    monkeypatch.setattr(DummyMessage, "reply_text", tracked_reply_text)

    message = DummyMessage()
    asyncio.run(
        bot._send_note_reply_with_audio(
            message,
            "Texto principal con botones",
            "Texto hablado",
            "note_20260524_220000",
            reply_markup={"k": "v"},
        )
    )

    assert order == ["text", "audio"]
    assert message.replies == ["Texto principal con botones"]
    assert message.reply_kwargs[0]["reply_markup"] == {"k": "v"}


def test_build_note_audio_text_omits_section_headers(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    saved = bot.save_note(
        settings.notes_dir,
        {
            "title": "Fuerzas primarias de la naturaleza",
            "corrected_text": "Fuerzas primarias de la naturaleza.",
            "concepts": [
                {
                    "term": "Fuerzas primarias de la naturaleza",
                    "definition": "ExpresiÃ³n que alude a fuerzas fundamentales.",
                }
            ],
            "related_terms": ["naturaleza", "fÃ­sica"],
        },
    )

    audio_text = bot._build_note_audio_text(
        {
            "corrected_text": "Fuerzas primarias de la naturaleza.",
            "concepts": [
                {
                    "term": "Fuerzas primarias de la naturaleza",
                    "definition": "ExpresiÃ³n que alude a fuerzas fundamentales.",
                }
            ],
        },
        saved,
    )

    assert "Nota limpia" not in audio_text
    assert "Terminos relacionados" not in audio_text
    assert "Fuerzas primarias de la naturaleza." in audio_text
    assert "Conceptos clave." in audio_text

