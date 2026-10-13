from __future__ import annotations

from datetime import datetime

from interfaz.notes import build_derivative_display_title, build_derivative_markdown, build_display_title, build_note_markdown, derivative_filename, save_note, save_note_derivative, sentence_case, slugify_title


def test_slugify_title_limits_and_replaces_invalid_chars() -> None:
    value = slugify_title("  Nota: prueba/rapida con simbolos *** y espacios  ")

    assert value.startswith("nota_prueba_rapida_con_simbolos")
    assert "/" not in value
    assert len(value) <= 80


def test_sentence_case_formats_title_like_sentence() -> None:
    assert sentence_case("  CONTEXTO CULTURAL Y VOZ SOBRENATURAL  ") == "Contexto cultural y voz sobrenatural"
    assert sentence_case("Â¿QUE PASA CON AZURE?") == "Â¿Que pasa con azure?"
    assert sentence_case("deuda-imperio-explotacion") == "Deuda imperio explotacion"


def test_build_display_title_prefixes_hour() -> None:
    assert build_display_title("CONTEXTO CULTURAL", datetime(2026, 5, 24, 20, 17, 10)) == (
        "20:17 - Contexto cultural"
    )


def test_build_derivative_display_title_uses_note_title_and_action() -> None:
    assert build_derivative_display_title("20:17 - Contexto cultural", "dialectic") == (
        "20:17 - Contexto cultural Â· Dialectica"
    )


def test_build_note_markdown_contains_knowledge_sections() -> None:
    payload = {
        "title": "TITULO DE PRUEBA",
        "text_type": "procedimental",
        "corrected_text": "Texto corregido.",
        "raw_transcript": "Texto original.",
        "source_audio": "data/audio/a.ogg",
        "source_type": "telegram_voice",
        "concepts": [{"term": "X", "definition": "Definicion X"}],
        "related_terms": ["Y"],
    }

    md = build_note_markdown(payload, datetime(2026, 5, 24, 10, 0, 0))

    assert 'title: "10:00 - Titulo de prueba"' in md
    assert 'key: "titulo_de_prueba"' in md
    assert 'text_type: "procedimental"' in md
    assert "source:" not in md
    assert "source_audio:" not in md
    assert "kind:" not in md
    assert "status:" not in md
    assert "privacy:" not in md
    assert "concepts:" not in md
    assert "tags:\n  - \"X\"" in md
    assert "related_terms:\n  - \"Y\"" in md
    assert "# 10:00 - Titulo de prueba" in md
    assert "## Nota limpia" in md
    assert "Texto corregido." in md
    assert "## Conceptos clave" in md
    assert "- **X**: Definicion X" in md
    assert "## Transcripcion original" not in md
    assert "Texto original." not in md
    assert "## Procesamientos derivados" in md
    assert "- Explicar: pendiente" in md
    assert "- Sugerencias: pendiente" in md
    assert "- Investigar: pendiente" in md
    assert "- Dialectica: pendiente" in md


def test_save_note_writes_note_and_indexes(tmp_path) -> None:
    payload = {
        "title": "Nota prueba",
        "text_type": "informativo",
        "corrected_text": "Texto corregido.",
        "raw_transcript": "Texto original.",
        "concepts": [{"term": "Idea", "definition": "Concepto importante."}],
        "related_terms": [],
    }

    saved = save_note(tmp_path, payload)

    assert saved.note_path.exists()
    assert saved.daily_index_path and saved.daily_index_path.exists()
    assert saved.master_index_path and saved.master_index_path.exists()
    assert "Nota prueba" in saved.daily_index_path.read_text(encoding="utf-8")
    index_content = saved.master_index_path.read_text(encoding="utf-8")
    assert '"key": "nota_prueba"' in index_content
    assert '"text_type": "informativo"' in index_content
    assert '"tags": [' in index_content
    assert '"Idea"' in index_content
    assert '"concepts"' not in index_content
    assert saved.title[:5].count(":") == 1


def test_save_note_derivative_writes_markdown_and_updates_note_links(tmp_path) -> None:
    saved = save_note(
        tmp_path,
        {
            "title": "Nota derivable",
            "corrected_text": "Texto base.",
            "concepts": [],
            "related_terms": [],
        },
    )

    derivative_path = save_note_derivative(saved.note_path, "explain", "Explicacion ampliada.", note_title=saved.title)

    assert derivative_path.name == derivative_filename(saved.note_path, "explain")
    derivative_markdown = derivative_path.read_text(encoding="utf-8")
    assert f"# {saved.title} Â· Explicar" in derivative_markdown
    assert "Explicacion ampliada." in derivative_markdown
    assert f"[{saved.title}]({saved.note_path.name})" in derivative_markdown

    note_markdown = saved.note_path.read_text(encoding="utf-8")
    assert f"- Explicar: [{derivative_path.name}]({derivative_path.name})" in note_markdown
    assert "- Sugerencias: pendiente" in note_markdown


def test_build_derivative_markdown_preserves_structured_sections_from_model_output(tmp_path) -> None:
    saved = save_note(
        tmp_path,
        {
            "title": "Conocer mÃ¡s allÃ¡ de percibir",
            "corrected_text": "Texto base.",
            "concepts": [],
            "related_terms": [],
        },
    )

    content = """Resumen ejecutivo

Idea central.

Hallazgos clave

Desarrollo amplio.

Acciones recomendadas para profundizar

- Paso 1
- Paso 2

Preguntas abiertas

- Duda A

Sintesis final

Cierre util.
"""

    markdown = build_derivative_markdown(saved.note_path, "research", content, note_title=saved.title)

    assert "## Nucleo\n\nIdea central." in markdown
    assert "## Desarrollo\n\nDesarrollo amplio." in markdown
    assert "## Accionables\n\n- Paso 1\n- Paso 2" in markdown
    assert "## Evidencias y supuestos\n\n- Duda A" in markdown
    assert "## Sintesis breve\n\nCierre util." in markdown
