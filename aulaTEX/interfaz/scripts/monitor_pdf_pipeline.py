from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analyze import _build_pdf_analysis_request, _extract_json, analyze_text
from src.azure_openai_client import build_pdf_input_message, invoke_chat, uses_openai_v1_endpoint
from src.config import load_settings
from src.document_reader import read_document_text


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_content_stream(lines: list[str]) -> bytes:
    commands = ["BT", "/F1 11 Tf", "72 770 Td", "14 TL"]
    first_line = True
    for line in lines:
        if not line:
            line = " "
        escaped = _escape_pdf_text(line)
        if first_line:
            commands.append(f"({escaped}) Tj")
            first_line = False
        else:
            commands.append("T*")
            commands.append(f"({escaped}) Tj")
    commands.append("ET")
    return "\n".join(commands).encode("latin-1", errors="replace")


def _write_minimal_pdf(pdf_path: Path, text: str, lines_per_page: int = 42) -> None:
    normalized_lines = [line[:110] for line in text.splitlines() if line.strip()]
    if not normalized_lines:
        normalized_lines = ["Documento de prueba vacío."]

    page_chunks = [normalized_lines[index : index + lines_per_page] for index in range(0, len(normalized_lines), lines_per_page)]

    objects: list[bytes] = []
    object_numbers: list[int] = []

    def add_object(content: bytes) -> int:
        object_number = len(objects) + 1
        objects.append(content)
        object_numbers.append(object_number)
        return object_number

    font_id = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids: list[int] = []
    pages_placeholder_id = len(objects) + 1
    objects.append(b"")
    object_numbers.append(pages_placeholder_id)

    for chunk in page_chunks:
        stream = _build_content_stream(chunk)
        content_id = add_object(b"<< /Length %d >>\nstream\n%b\nendstream" % (len(stream), stream))
        page_id = add_object(
            (
                f"<< /Type /Page /Parent {pages_placeholder_id} 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
            ).encode("ascii")
        )
        page_ids.append(page_id)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_placeholder_id - 1] = f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>".encode("ascii")
    catalog_id = add_object(f"<< /Type /Catalog /Pages {pages_placeholder_id} 0 R >>".encode("ascii"))

    buffer = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, content in enumerate(objects, start=1):
        offsets.append(len(buffer))
        buffer.extend(f"{index} 0 obj\n".encode("ascii"))
        buffer.extend(content)
        buffer.extend(b"\nendobj\n")

    xref_offset = len(buffer)
    buffer.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    buffer.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        buffer.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    buffer.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    pdf_path.write_bytes(buffer)


def _build_probe_payload(pdf_path: Path) -> dict:
    settings = load_settings()
    result: dict[str, object] = {
        "timestamp": datetime.now().isoformat(),
        "pdf_path": str(pdf_path),
        "pdf_size_bytes": pdf_path.stat().st_size,
        "endpoint_type": "responses_v1" if uses_openai_v1_endpoint(settings.azure_openai_endpoint) else "chat_completions",
        "model": settings.azure_openai_chat_deployment,
    }

    started = time.perf_counter()
    extracted_text = read_document_text(pdf_path)
    result["extract_seconds"] = round(time.perf_counter() - started, 3)
    result["extracted_chars"] = len(extracted_text)
    result["extracted_preview"] = extracted_text[:500]

    if uses_openai_v1_endpoint(settings.azure_openai_endpoint):
        direct_started = time.perf_counter()
        try:
            direct_content = invoke_chat(
                settings,
                [{"role": "system", "content": "Eres un editor experto de notas personales en espanol."}],
                max_tokens=140000,
                temperature=0.2,
                response_format_json=True,
                input_override=build_pdf_input_message(pdf_path, _build_pdf_analysis_request("monitor_document")),
            )
            result["direct_pdf_seconds"] = round(time.perf_counter() - direct_started, 3)
            result["direct_pdf_raw_preview"] = direct_content[:1200]
            result["direct_pdf_json_valid"] = isinstance(_extract_json(direct_content), dict)
        except Exception as exc:
            result["direct_pdf_seconds"] = round(time.perf_counter() - direct_started, 3)
            result["direct_pdf_error"] = str(exc)

    analysis_started = time.perf_counter()
    analysis = analyze_text(extracted_text, str(pdf_path), settings, "monitor_document")
    result["analysis_seconds"] = round(time.perf_counter() - analysis_started, 3)
    result["analysis_title"] = analysis.get("title", "")
    result["analysis_corrected_chars"] = len(str(analysis.get("corrected_text", "")))
    result["analysis_concepts_count"] = len(analysis.get("concepts", [])) if isinstance(analysis.get("concepts"), list) else 0
    result["analysis_related_terms_count"] = len(analysis.get("related_terms", [])) if isinstance(analysis.get("related_terms"), list) else 0
    result["analysis_preview"] = str(analysis.get("corrected_text", ""))[:800]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Ejecuta una prueba monitoreada del pipeline PDF.")
    parser.add_argument("--pdf", dest="pdf_path", help="Ruta a un PDF existente.")
    parser.add_argument("--from-text", dest="text_path", help="Ruta a un .txt para generar un PDF sintético.")
    args = parser.parse_args()

    if not args.pdf_path and not args.text_path:
        raise SystemExit("Debes indicar --pdf o --from-text.")

    monitoring_dir = ROOT / "data" / "monitoring"
    monitoring_dir.mkdir(parents=True, exist_ok=True)

    temp_pdf_path: Path | None = None
    if args.pdf_path:
        pdf_path = Path(args.pdf_path).resolve()
    else:
        text_path = Path(args.text_path).resolve()
        source_text = text_path.read_text(encoding="utf-8", errors="ignore")
        temp_dir = Path(tempfile.mkdtemp(prefix="notas_pdf_probe_", dir=str(monitoring_dir)))
        temp_pdf_path = temp_dir / "probe.pdf"
        _write_minimal_pdf(temp_pdf_path, source_text)
        pdf_path = temp_pdf_path

    payload = _build_probe_payload(pdf_path)
    output_path = monitoring_dir / f"pdf_pipeline_probe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(output_path)
    if temp_pdf_path:
        print(temp_pdf_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())