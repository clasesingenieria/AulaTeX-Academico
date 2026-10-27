from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote


SUBJECT = Path(__file__).resolve().parents[1]
REPOSITORY = SUBJECT.parents[2]
PLANS = SUBJECT / "planeaciones-plan-de-negocios"
CATALOG = PLANS / "catalogo-editorial.json"
NUMBERING = SUBJECT / "referencias-plan-de-negocios/notas-plan-de-negocios/materiales-generales/registros/numeracion-actividades.json"
sys.path.insert(0, str(REPOSITORY / "aulaTEX"))

from aulatex.planning_conversion import convert_source, render_editorial_markdown
from aulatex.planning_layout import catalogued_plan_paths
from aulatex.planning_validation import validate_pedagogical
from aulatex.workspace import AulaTeXWorkspace


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encode(document: dict) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def integrate(document: dict, path: Path, raw: bytes) -> None:
    text = raw.decode("utf-8")
    if text.encode("utf-8") != raw:
        raise ValueError("lossy_document_encoding")
    store = document.setdefault("extensions", {}).setdefault("integrated_documents", {"objects": {}, "files": {}})
    store["objects"].setdefault(digest(raw), {"text": text})
    store["files"][path.relative_to(SUBJECT).as_posix()] = digest(raw)


def embedded_source(document: dict, identifier: str, path: Path) -> None:
    raw = path.read_bytes()
    document["sources"].append({"id": identifier, "kind": "other", "authority": "editorial", "title": path.name,
        "url": None, "path": None, "sha256": digest(raw), "captured_at": None, "media_type": "text/plain"})
    document["extensions"].setdefault("embedded_sources", {})[identifier] = {"encoding": "utf-8", "text": raw.decode("utf-8")}


def render(document: dict) -> str:
    editorial = document["extensions"]["editorial"]
    text = render_editorial_markdown(document)
    lines = [text, "## Correspondencia y archivos existentes", "", f"Actividad editorial: {editorial['number']}. Modulo documentado: {editorial['module_id']}.", "",
             "Reportes institucionales de tres tiempos: introduccion, desarrollo tematico y conclusiones. Se conservan los nombres, variantes y formatos existentes; no se recompilan ni sustituyen entregables."]
    for path in editorial["reports"] + editorial["notes"] + editorial["delivery_candidates"]:
        lines.append(f"- [{Path(path).name}](../{path.replace(' ', '%20')})")
    lines.extend(["", "## Calendario documental, no operativo", "", "El calendario operativo esta vacio. Los siguientes literales se conservan como evidencia de captura, no como apertura o prorroga.", "",
                  "<details>", "<summary>Consultar fechas y observaciones originales</summary>", "", editorial["deadline_literal"] or "Literal no documentado.", "",
                  editorial["calendar_note"] or "", "", "</details>", "", "## Integracion y limites", "",
                  f"Se absorbieron {len(document['extensions']['integrated_documents']['files'])} documentos completos, deduplicados por SHA-256 dentro de este modelo. No se requieren las carpetas anteriores.", "",
                  "Las conversiones, revisiones de nodo y fichas originales son evidencia de procedencia; no se convierten automaticamente en requisitos docentes ni en aprobaciones."])
    if editorial["number"] in {2, 3, 4, 9, 13}:
        lines.extend(["", "**Cuestionario o examen:** conserva reporte documental; no genera PDF de entrega por defecto. Una guia de preparacion no acredita respuestas ni un intento finalizado."])
    if editorial["number"] == 1:
        lines.extend(["", "**Foro evaluable:** mantiene su numero 1 y no esta omitido. La omision de foros de Estadistica no aplica aqui."])
    if editorial["number"] == 6:
        lines.extend(["", "**Variantes de empresa:** AM Taller, Industrial Revolucionaria y NexoTeX no se unifican por inferencia. Ninguna variante se selecciona para entrega en esta revision."])
    if editorial["number"] in {3, 12, 15}:
        lines.extend(["", "Existe evidencia documental de un intento finalizado o envio previo. No repetirlo. El envio registrado no acredita cumplimiento integral de todos los requisitos; especialmente, las diapositivas no sustituyen el video real de la Actividad 15."])
    return ("\n".join(lines) + "\n").replace("\r\n", "\n").replace("\r", "\n")


def render_index(catalog: dict) -> str:
    lines = ["# Planeaciones de Plan de Negocios", "", "15 pares JSON/Markdown con la numeracion local documentada, sin aprobacion ni habilitacion automatica.", "",
             "| Actividad | Modulo | Tema | Vista |", "| --- | --- | --- | --- |"]
    for entry in catalog["activities"]:
        title = entry["title"].replace("|", "/")
        lines.append(f"| {entry['number']} | {entry['module_id']} | {title} | [Consultar]({Path(entry['markdown']).name}) |")
    lines.extend(["", "## Alcance", "", "- Foro 1 evaluable; no se omite.", "- Examenes y cuestionarios conservan reporte documental, sin PDF de entrega por defecto.",
                  "- Fechas operativas vacias; capturas y literales originales integrados en JSON.", "- Variantes de Actividad 6 conservadas, sin elegir un proyecto por inferencia.",
                  "- Sondeo real pendiente en 10 y 14; grabacion y enlace verificado pendientes en 15. La limpieza no completa esos productos.",
                  f"- {len(catalog['absorption']['files'])} archivos absorbidos completos; fichas antiguas, importaciones y canonicas retiradas, sin respaldos nuevos.", "",
                  "## Verificacion", "", "El script local `integrar_planeaciones_json_md.py` permite `--validate` y `--render-views`. El JSON es el modelo completo; Markdown es su vista visual. No se consultan cuentas ni se ejecutan actividades.", ""])
    return "\n".join(lines)


def prepare() -> tuple[dict, dict[Path, bytes], dict[Path, bytes]]:
    numbering = load(NUMBERING)["activities"]
    if [item["number"] for item in numbering] != list(range(1, 16)):
        raise ValueError("numbering_not_documented")
    sources = {number: PLANS / f"planeacion-actividad-{number}.json" for number in range(1, 16)}
    originals = {path: path.read_bytes() for path in PLANS.rglob("*") if path.is_file()}
    workspace = AulaTeXWorkspace(REPOSITORY)
    subject = next(scope for scope in workspace.scan_editorial_scopes() if scope.level == "materia" and workspace.resolve_target(scope.relative_path) == SUBJECT)
    catalog = {"version": "1.0", "date": "2026-10-27", "activities": [], "antecedents": [], "approved": [], "automatic_execution": False,
               "extensions": {}, "absorption": {"files": {}, "new_backup_files": 0}}
    documents = {}
    for row in numbering:
        number = row["number"]
        original = load(sources[number])
        if original["chronological_numbering"]["local_number"] != number or original["activity"]["id"] != row["module_id"]:
            raise ValueError("module_number_mismatch")
        numbered_reports = list(SUBJECT.glob(f"reporte-plan-de-negocios-Actividad-{number}-*.tex"))
        if not numbered_reports or not any(path.with_suffix(".pdf").is_file() for path in numbered_reports):
            raise ValueError("numbered_report_not_verified")
        document, _mapping = convert_source(workspace, subject, sources[number])
        document["revision"] += 1
        document["identity"]["program"] = "maestria-en-gestion-administrativa"
        activity = document["activities"][0]
        activity["calendar"] = {key: None for key in activity["calendar"]}
        document["sources"][0]["path"] = None
        document["extensions"]["embedded_sources"] = {"src-local": {"encoding": "utf-8", "text": originals[sources[number]].decode("utf-8")}}
        embedded_source(document, "src-numbering", NUMBERING)
        embedded_source(document, "src-master", SUBJECT / "README.md")
        embedded_source(document, "src-status", SUBJECT / "ESTADO-ENTREGABLES.md")
        document["extensions"]["organizacion_interna"] = {"internal_number": number, "official_number": None}
        document["extensions"]["editorial_view"] = {"warnings": ["La consigna del modelo anterior es un resumen; el contenido original integro permanece en las fuentes integradas. No se declara cotejo academico completo."]}
        document["curriculum"]["purpose"] = original.get("purpose", {}).get("value")
        activity["policies"]["collaboration"] = original.get("work_mode", {}).get("value")
        requirements = [item["id"] for item in activity["requirements"]]
        for product in activity["products"]:
            product["requirement_ids"] = requirements
        for step in activity["sequence"]:
            step["requirement_ids"] = requirements
        document["extensions"]["assessment_original"] = original.get("assessment_table")
        document["extensions"]["resources_original"] = original["sources"]
        document["extensions"]["issues_original"] = original.get("open_issues", [])
        document["review"].update(reviewed_at="2026-10-27", reviewer_role="integracion-documental-local", state="needs_review", semantic_validation="failed")
        document["review"]["critical_gaps"].append("Integridad tecnica no equivale a aprobacion academica, envio ni validacion de resultados empiricos.")
        notes = [path.relative_to(SUBJECT).as_posix() for path in (SUBJECT / "referencias-plan-de-negocios/notas-plan-de-negocios").glob(f"actividad-{number:02d}-*") if path.is_dir()]
        reports = [path.relative_to(SUBJECT).as_posix() for path in SUBJECT.glob(f"reporte-plan-de-negocios-Actividad-{number}-*") if path.suffix in {".tex", ".pdf"}]
        deliveries = [path.relative_to(SUBJECT).as_posix() for path in (SUBJECT / "entregas-plan-de-negocios").glob(f"*Actividad-{number}-*") if path.is_file()]
        activity["bindings"] = {"notes_directory": notes[0] if len(notes) == 1 else None, "extractor_directory": None, "research_directory": None}
        document["extensions"]["editorial"] = {"number": number, "module_id": str(row["module_id"]), "reports": reports, "notes": notes,
            "delivery_candidates": deliveries, "deadline_literal": row.get("deadline_literal"), "calendar_note": original["activity"].get("note"),
            "original_calendar": original["activity"].get("calendar"), "execution_allowed": False, "submission_allowed": False, "generate_pdf_by_default": False,
            "already_completed_evidence": number in {3, 12, 15}}
        documents[number] = document
    destinations = {}
    for number, path in sources.items():
        destinations[path] = number
        destinations[path.with_suffix(".md")] = number
    destinations[PLANS / "README.md"] = None
    for path in originals:
        if path.name != "planeacion.json":
            continue
        data = load(path)
        if path.is_relative_to(PLANS / "importaciones"):
            match = re.search(r"planeacion-actividad-(\d+)\.(?:json|md)$", data["sources"][0]["path"] or "")
            if not match:
                raise ValueError("unmapped_conversion")
            number = int(match[1])
            names = ("planeacion.json", "planeacion.md", "cotejo-local.json")
        elif path.is_relative_to(PLANS / "canonicas"):
            match = re.search(r"/actividad-(\d+)$", data["node"]["key"])
            number = int(match[1]) if match else None
            names = ("planeacion.json", "planeacion.md")
        else:
            continue
        if number is not None and number not in documents:
            raise ValueError("unknown_conversion_number")
        for name in names:
            sibling = path.with_name(name)
            if sibling not in originals:
                raise ValueError("incomplete_conversion")
            destinations[sibling] = number
    if set(destinations) != set(originals):
        raise ValueError("unmapped_cleanup_files")
    catalog_relative = CATALOG.relative_to(SUBJECT).as_posix()
    for path, raw in originals.items():
        number = destinations[path]
        target = f"planeaciones-plan-de-negocios/planeacion-plan-de-negocios-Actividad-{number}.json" if number is not None else catalog_relative
        integrate(documents[number] if number is not None else catalog, path, raw)
        catalog["absorption"]["files"][path.relative_to(SUBJECT).as_posix()] = {"target": target, "sha256": digest(raw)}
    prepared = {}
    for number, document in documents.items():
        report = validate_pedagogical(document, SUBJECT)
        destination = PLANS / f"planeacion-plan-de-negocios-Actividad-{number}.json"
        prepared[destination] = encode(document)
        prepared[destination.with_suffix(".md")] = render(document).encode("utf-8")
        catalog["activities"].append({"number": number, "module_id": str(document["activities"][0]["id"]), "title": document["activities"][0]["title"],
            "json": destination.relative_to(SUBJECT).as_posix(), "markdown": destination.with_suffix(".md").relative_to(SUBJECT).as_posix(),
            "plan_id": document["plan_id"], "revision": document["revision"], "state": "needs_review", "semantic_passed": report["passed"], "findings": report["findings"],
            "sha256": digest(prepared[destination]), "execution_allowed": False, "submission_allowed": False})
    prepared[CATALOG] = encode(catalog)
    prepared[PLANS / "README.md"] = render_index(catalog).encode("utf-8")
    for path in prepared:
        if path.exists() and path not in originals:
            raise FileExistsError("destination_exists")
    return catalog, prepared, originals


def validate() -> dict:
    catalog = load(CATALOG)
    errors = []
    documents = {CATALOG.relative_to(SUBJECT).as_posix(): catalog}
    if [entry["number"] for entry in catalog["activities"]] != list(range(1, 16)) or len(catalogued_plan_paths(SUBJECT)) != 15:
        errors.append("catalog_inventory")
    for entry in catalog["activities"]:
        path = SUBJECT / entry["json"]
        document = load(path)
        documents[entry["json"]] = document
        report = validate_pedagogical(document, SUBJECT)
        if digest(path.read_bytes()) != entry["sha256"] or report["findings"] != entry["findings"]:
            errors.append("active_model_changed")
        if any(document["activities"][0]["calendar"].values()):
            errors.append("operational_dates_not_empty")
        if any(item["code"] in {"missing_source", "source_hash_changed", "unresolved_reference", "unresolved_pointer", "duplicate_id"} for item in report["findings"]):
            errors.append("structural_validation")
        markdown = SUBJECT / entry["markdown"]
        text = markdown.read_text(encoding="utf-8")
        if text != render(document) or "```" in text:
            errors.append("markdown_derivation")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if "://" not in target and not target.startswith("#") and not (markdown.parent / unquote(target.split("#")[0])).exists():
                errors.append("missing_view_link")
    for relative, record in catalog["absorption"]["files"].items():
        raw = documents[record["target"]]["extensions"]["integrated_documents"]["objects"][record["sha256"]]["text"].encode("utf-8")
        if digest(raw) != record["sha256"] or (SUBJECT / relative).exists() and relative != "planeaciones-plan-de-negocios/README.md":
            errors.append("absorption_integrity")
    if any((PLANS / name).exists() for name in ("canonicas", "importaciones")) or list(PLANS.glob("planeacion-actividad-*")):
        errors.append("old_files_remaining")
    if (PLANS / "README.md").read_text(encoding="utf-8") != render_index(catalog):
        errors.append("index_derivation")
    return {"passed": not errors, "errors": errors, "pairs": 15, "absorbed_files": len(catalog["absorption"]["files"]), "ready": 0, "execution": False, "submission": False}


def apply() -> dict:
    if CATALOG.exists():
        return validate()
    catalog, prepared, originals = prepare()
    for path, raw in prepared.items():
        path.write_bytes(raw)
    saved = load(CATALOG)
    for path, raw in originals.items():
        record = saved["absorption"]["files"][path.relative_to(SUBJECT).as_posix()]
        document = load(SUBJECT / record["target"])
        integrated = document["extensions"]["integrated_documents"]["objects"][record["sha256"]]["text"].encode("utf-8")
        if integrated != raw or path not in prepared and path.read_bytes() != raw:
            raise ValueError("absorption_failed_before_deletion")
    if any(path.read_bytes() != raw for path, raw in prepared.items()):
        raise ValueError("output_verification_failed")
    for path in originals:
        if path not in prepared:
            path.unlink()
    for name in ("importaciones", "canonicas"):
        directory = PLANS / name
        for child in sorted((path for path in directory.rglob("*") if path.is_dir()), key=lambda path: len(path.parts), reverse=True):
            child.rmdir()
        directory.rmdir()
    return validate()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--render-views", action="store_true")
    arguments = parser.parse_args()
    if arguments.apply:
        result = apply()
    elif arguments.validate or arguments.render_views:
        if arguments.render_views:
            catalog = load(CATALOG)
            for entry in catalog["activities"]:
                (SUBJECT / entry["markdown"]).write_text(render(load(SUBJECT / entry["json"])), encoding="utf-8", newline="\n")
            (PLANS / "README.md").write_text(render_index(catalog), encoding="utf-8", newline="\n")
        result = validate()
    else:
        catalog, prepared, originals = prepare()
        result = {"passed": True, "pairs": 15, "outputs": len(prepared), "absorbed_files": len(originals), "writes": 0}
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())