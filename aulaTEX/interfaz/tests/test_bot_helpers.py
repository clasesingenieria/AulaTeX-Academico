from __future__ import annotations

from pathlib import Path

from interfaz.bot import _build_channel_text, _build_note_audio_text, _copy_clean_note_to_clipboard, _format_note_reply, _format_transcript_preview, _parse_derivative_markdown
from interfaz.notes import SavedNote


def test_format_transcript_preview_normalizes_whitespace() -> None:
    preview = _format_transcript_preview("hola\n\n   mundo\tprueba")

    assert preview == "hola mundo prueba"


def test_format_transcript_preview_truncates_long_text() -> None:
    preview = _format_transcript_preview("a" * 20, limit=10)

    assert preview == "aaaaaaa..."


def test_format_note_reply_reports_clipboard_success(tmp_path: Path) -> None:
    saved = SavedNote(note_path=tmp_path / "nota.md", title="Titulo")
    reply = _format_note_reply(
        {"corrected_text": "Texto corregido limpio.", "concepts": []},
        saved,
        clipboard_copied=True,
    )

    assert "Nota limpia:" not in reply
    assert "Texto corregido limpio." in reply
    assert "Redaccion limpia copiada al portapapeles local." not in reply


def test_format_note_reply_does_not_truncate_long_text_by_default(tmp_path: Path) -> None:
    saved = SavedNote(note_path=tmp_path / "nota.md", title="Titulo")
    long_text = "abc " * 500

    reply = _format_note_reply(
        {"corrected_text": long_text, "concepts": []},
        saved,
    )

    assert long_text.strip() in reply
    assert "..." not in reply


def test_build_note_audio_text_does_not_truncate_long_text_by_default(tmp_path: Path) -> None:
    saved = SavedNote(note_path=tmp_path / "nota.md", title="Titulo")
    long_text = "abc " * 500

    audio_text = _build_note_audio_text(
        {"corrected_text": long_text, "concepts": []},
        saved,
    )

    assert long_text.strip() in audio_text
    assert "..." not in audio_text


def test_copy_clean_note_to_clipboard_uses_corrected_text(monkeypatch) -> None:
    captured = {}

    def fake_copy(text: str) -> bool:
        captured["text"] = text
        return True

    monkeypatch.setattr("interfaz.bot._copy_text_to_clipboard", fake_copy)

    assert _copy_clean_note_to_clipboard({"corrected_text": "Texto corregido."}) is True
    assert captured["text"] == "Texto corregido."


def test_copy_clean_note_to_clipboard_prefers_saved_markdown(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def fake_copy(text: str) -> bool:
        captured["text"] = text
        return True

    note_path = tmp_path / "nota.md"
    note_path.write_text(
        "# 10:00 - Titulo\n\n## Nota limpia\n\nTexto desde markdown.\n\n## Conceptos clave\n\n- **Idea**: Definicion.\n",
        encoding="utf-8",
    )

    monkeypatch.setattr("interfaz.bot._copy_text_to_clipboard", fake_copy)

    assert _copy_clean_note_to_clipboard({"corrected_text": "Texto crudo.", "_note_path": str(note_path)}) is True
    assert captured["text"] == "Texto desde markdown."


def test_parse_derivative_markdown_tolerates_metadata_noise() -> None:
    markdown = """# 05:29 - La conquista de mÃ©xico, de hugh thomas Â· Dialectica

Nota origen: [05:29 - La conquista de mÃ©xico, de hugh thomas](nota.md)

## Metadata

{
  \"action\": \"dialectic\",
  \"label\": \"Dialectica\"
}1

## Nucleo

Tesis.
"""

    payload = _parse_derivative_markdown(markdown)

    assert payload["metadata"] == {"action": "dialectic", "label": "Dialectica"}


def test_build_channel_text_clipboard_preserves_argument_order_without_ratio_compaction() -> None:
    payload = {
        "title": "05:29 - La conquista de mÃ©xico, de hugh thomas Â· Dialectica",
        "source_title": "05:29 - La conquista de mÃ©xico, de hugh thomas",
        "sections": {
            "Nucleo": "NUCLEO\n\nRegla practica: usar el libro como mapa.",
            "Desarrollo": "DESARROLLO\n\nIntegracion operativa: mantener multicausalidad.",
            "Accionables": "ACCIONABLES\n\n1. Contrastar fuentes\n2. Revisar agencia indigena",
            "Evidencias y supuestos": "Sesgos posibles del analisis: archivo colonial.",
            "Sintesis breve": "Pregunta abierta: que tipo de centro explicativo conviene evitar.",
        },
    }

    clipboard = _build_channel_text(payload, "clipboard")

    assert clipboard.startswith("La conquista de mÃ©xico, de hugh thomas - DialÃ©ctica")
    assert clipboard.find("NUCLEO") < clipboard.find("DESARROLLO")
    assert clipboard.find("DESARROLLO") < clipboard.find("ACCIONABLES")
    assert "Sesgos posibles del analisis" not in clipboard
    assert "Regla practica:" not in clipboard
    assert "Integracion operativa:" not in clipboard
    assert "Pregunta abierta:" not in clipboard


def test_build_channel_text_audio_removes_editorial_labels_and_preserves_points() -> None:
    payload = {
        "title": "05:29 - La conquista de mÃ©xico, de hugh thomas Â· Dialectica",
        "source_title": "05:29 - La conquista de mÃ©xico, de hugh thomas",
        "sections": {
            "Nucleo": "Tesis: lectura amplia.\n\nAntitesis: marco colonial.",
            "Desarrollo": "Idea contraria: el centro narrativo puede sesgar la lectura.",
            "Accionables": "1. Contrastar con Cartas de relacion\n- Revisar voces nahuas",
            "Evidencias y supuestos": "Limites: sin edicion concreta.",
            "Sintesis breve": "Regla practica: usar la obra como mapa.",
        },
    }

    audio = _build_channel_text(payload, "audio")

    assert audio.startswith("Dialectica. Tesis: lectura amplia.")
    assert "Limites:" not in audio
    assert "Regla practica:" not in audio
    assert "Punto: Contrastar con Cartas de relacion" in audio
    assert "Punto: Revisar voces nahuas" in audio
