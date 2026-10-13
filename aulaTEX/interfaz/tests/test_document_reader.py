from __future__ import annotations

from pathlib import Path

import pytest

from src import document_reader
from interfaz.document_reader import read_document_text


def test_read_document_text_txt(tmp_path: Path) -> None:
    file_path = tmp_path / "nota.txt"
    file_path.write_text("hola mundo", encoding="utf-8")

    result = read_document_text(file_path)

    assert result == "hola mundo"


def test_read_document_text_md(tmp_path: Path) -> None:
    file_path = tmp_path / "nota.md"
    file_path.write_text("# titulo\ncontenido", encoding="utf-8")

    result = read_document_text(file_path)

    assert "contenido" in result


def test_read_document_text_pdf_dispatches_to_pdf_reader(tmp_path: Path, monkeypatch) -> None:
    file_path = tmp_path / "nota.pdf"
    file_path.write_bytes(b"%PDF")

    monkeypatch.setattr(document_reader, "_read_pdf_text", lambda path: "contenido pdf")

    result = read_document_text(file_path)

    assert result == "contenido pdf"


def test_read_document_text_docx_dispatches_to_docx_reader(tmp_path: Path, monkeypatch) -> None:
    file_path = tmp_path / "nota.docx"
    file_path.write_bytes(b"PK")

    monkeypatch.setattr(document_reader, "_read_docx_text", lambda path: "contenido docx")

    result = read_document_text(file_path)

    assert result == "contenido docx"


def test_read_document_text_unsupported_extension(tmp_path: Path) -> None:
    file_path = tmp_path / "nota.rtf"
    file_path.write_text("texto", encoding="utf-8")

    with pytest.raises(RuntimeError):
        read_document_text(file_path)
