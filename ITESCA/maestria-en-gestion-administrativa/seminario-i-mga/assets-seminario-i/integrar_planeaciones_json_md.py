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
PLANS = SUBJECT / "planeaciones-seminario-i"
CATALOG = PLANS / "catalogo-editorial.json"
MASTER = SUBJECT / "Readme - Seminario I.md"
sys.path.insert(0, str(REPOSITORY / "aulaTEX"))

from aulatex.planning_conversion import _empty_activity
from aulatex.planning_layout import catalogued_plan_paths
from aulatex.planning_validation import validate_pedagogical


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def encoded(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def inventory() -> tuple[list[dict], dict[Path, bytes]]:
    records = []
    originals = {path: path.read_bytes() for path in PLANS.glob("Planeacion - *.md")}
    master = MASTER.read_text(encoding="utf-8")
    for path, raw in originals.items():
        text = raw.decode("utf-8-sig")
        heading = text.splitlines()[0]
        match = re.search(r"(?:Tarea|Actividad)\s+(\d+)\b", heading)
        number = int(match[1]) if match else None
        if number is None and not heading.startswith("# Foro:"):
            raise ValueError("source_without_documented_identity")
        if number is not None and not re.search(rf"\bTarea {number}\b", master):
            raise ValueError("number_not_in_master")
        modules = set(re.findall(r"Modulo(?: Moodle)?\s*[:.]?\s*(\d+)", text, re.I))
        if len(modules) > 1:
            raise ValueError("ambiguous_module")
        records.append({"number": number, "module_id": next(iter(modules), None), "source": path, "text": text, "heading": heading, "imports": []})
    if sorted(item["number"] for item in records if item["number"] is not None) != list(range(1, 19)) or len(records) != 19:
        raise ValueError("unexpected_source_inventory")
    sources = {item["source"].relative_to(SUBJECT).as_posix(): item for item in records}
    import_files = {path: path.read_bytes() for path in (PLANS / "importaciones").rglob("*") if path.is_file()}
    consumed = set()
    for path in import_files:
        if path.name != "planeacion.json":
            continue
        document = load(path)
        relative = document["sources"][0]["path"]
        if relative not in sources:
            raise ValueError("import_without_source_mapping")
        for name in ("planeacion.json", "planeacion.md", "cotejo-local.json"):
            sibling = path.with_name(name)
            if sibling not in import_files:
                raise ValueError("incomplete_import_revision")
            sources[relative]["imports"].append(sibling)
            consumed.add(sibling)
    if consumed != set(import_files) or any(not item["imports"] for item in records):
        raise ValueError("unmapped_imports")
    originals.update(import_files)
    return sorted(records, key=lambda item: item["number"] or 0), originals


def sections(text: str) -> dict[str, str]:
    result = {}
    for chunk in re.split(r"^## ", text, flags=re.M)[1:]:
        heading, _, content = chunk.partition("\n")
        result[heading.strip()] = content.strip()
    return result


def source(document: dict, identifier: str, path: Path, *, authority: str = "editorial", embed: bool = False) -> None:
    raw = path.read_bytes()
    document["sources"].append({"id": identifier, "kind": "other", "authority": authority, "title": path.name, "url": None,
        "path": None if embed else path.relative_to(SUBJECT).as_posix(), "sha256": sha(raw), "captured_at": None,
        "media_type": "application/json" if path.suffix == ".json" else "text/plain"})
    if embed:
        document["extensions"].setdefault("embedded_sources", {})[identifier] = {"encoding": "utf-8", "text": raw.decode("utf-8")}


def status(path: str, state: str, reason: str, source_id: str | None = None, quote: str | None = None) -> dict:
    return {"path": path, "state": state, "reason": reason,
            "evidence": [{"source_id": source_id, "locator": "texto archivado", "quoted_text": quote}] if source_id else [], "alternatives": []}


def build(record: dict, originals: dict[Path, bytes]) -> dict:
    imported = sorted((path for path in record["imports"] if path.name == "planeacion.json"), key=lambda path: path.parent.name)[-1]
    document = copy.deepcopy(load(imported))
    number = record["number"]
    module = record["module_id"]
    source_sections = sections(record["text"])
    title = record["source"].stem.split(" - ", 2)[-1].replace("-", " ").capitalize() if number else "Conectando nuestras ideas de investigacion"
    activity = _empty_activity(module or f"actividad-{number}", title)
    activity["policies"]["exceptions"] = []
    document.update(revision=document["revision"] + 1, sources=[], activities=[activity], field_status=[])
    document["identity"].update(subject_title="Seminario I", subject_id="seminario-i-mga", institution="ITESCA", program="maestria-en-gestion-administrativa")
    document["extensions"] = {"embedded_sources": {}, "integrated_documents": {"objects": {}, "files": {}},
                              "original_sections": source_sections, "original_conversion": document.get("extensions", {})}
    source(document, "src-local", record["source"], embed=True)
    source(document, "src-master", MASTER, embed=True)
    source(document, "src-delivery-status", SUBJECT / "ESTADO-ENTREGABLES.md", embed=True)
    teacher_id = None
    evidence_paths = []
    for target in re.findall(r"\]\(([^)]+)\)", record["text"]):
        if "://" in target:
            continue
        path = (PLANS / unquote(target.split("#")[0])).resolve()
        if not path.is_relative_to(SUBJECT):
            raise ValueError("source_link_outside_subject")
        if path.is_file():
            evidence_paths.append(path.relative_to(SUBJECT).as_posix())
            if path.name == "cotejo-plataforma-2026-10-10.json":
                evidence = load(path)
                if str(evidence["modulo"]) != module:
                    raise ValueError("teacher_module_mismatch")
                if source_sections.get("Consigna oficial consultada", "").strip() != evidence["consigna"].strip():
                    raise ValueError("teacher_instruction_mismatch")
                teacher_id = "src-teacher"
                source(document, teacher_id, path, authority="instructional")
                document["sources"][-1]["captured_at"] = evidence["fecha"]
    instruction = source_sections.get("Consigna oficial consultada")
    if instruction is None:
        instruction = "\n\n".join(f"{heading}\n{content}" for heading, content in source_sections.items() if heading != "Alcance de esta planeacion")
    activity["instruction"] = instruction
    topic = {"id": "topic-local", "text": title, "children": []}
    purpose = None
    paragraphs = [part.strip() for part in instruction.split("\n\n") if part.strip()]
    for index, paragraph in enumerate(paragraphs[:-1]):
        if re.search(r"Objetivo|Prop[oó]sito", paragraph, re.I) and len(paragraph) < 100:
            purpose = paragraphs[index + 1]
            break
    document["curriculum"] = {"purpose": purpose, "competencies": [], "outcomes": [], "topics": [topic]}
    activity["topic_ids"] = [topic["id"]]
    if purpose:
        document["curriculum"]["outcomes"] = [{"id": "outcome-local", "text": purpose}]
        activity["outcome_ids"] = ["outcome-local"]
    requirement_text = instruction
    instruction_marker = re.search(r"^.*Instrucciones[^\n]*\n", instruction, re.M | re.I)
    if instruction_marker:
        requirement_text = instruction[instruction_marker.end():]
    requirement_text = re.split(r"^.*(?:R[uú]brica de evaluaci[oó]n|Criterios de evaluaci[oó]n).*$", requirement_text, maxsplit=1, flags=re.M | re.I)[0]
    for line in requirement_text.splitlines():
        if len(line.strip()) < 20 or line.startswith("#"):
            continue
        identifier = f"req-{len(activity['requirements']) + 1:03d}"
        activity["requirements"].append({"id": identifier, "text": line.strip()})
        for question in re.findall(r"¿[^?]+\?", line):
            activity["questions"].append({"id": f"question-{len(activity['questions']) + 1:03d}", "context": "Consigna archivada", "text": question, "requirement_ids": [identifier]})
    requirement_ids = [item["id"] for item in activity["requirements"]]
    for index, (phase, action, output) in enumerate((
        ("preparation", "Cotejar consigna, fuentes y requisitos pendientes antes de elaborar.", "Notas y fuentes verificadas"),
        ("construction", "Organizar el producto segun la consigna; distinguir evidencia y propuesta propia.", "Borrador del producto solicitado"),
        ("review", "Comprobar cobertura, formato, fuentes y conflictos; no enviar automaticamente.", "Revision local con pendientes explicitos")), 1):
        activity["sequence"].append({"id": f"step-{index}", "order": index, "phase": phase, "action": action, "inputs": ["Consigna y fuentes archivadas"],
            "output": output, "completion_check": "Verificacion documental de requisitos y bloqueos", "requirement_ids": requirement_ids, "depends_on": [f"step-{index-1}"] if index > 1 else []})
    for line in instruction.splitlines():
        cells = line.split("\t")
        if len(cells) >= 3 and re.fullmatch(r"\d+(?:[.,]\d+)?\s*%", cells[-1].strip()):
            activity["assessment"]["criteria"].append({"id": f"criterion-{len(activity['assessment']['criteria'])+1}", "text": cells[0].strip(), "points": None,
                "descriptors": [{"level": cells[-1].strip(), "description": " ".join(cells[1:-1]), "points": None}], "requirement_ids": requirement_ids})
    is_forum = number is None or number == 7
    format_lines = [line.strip() for line in instruction.splitlines() if re.search(r"\bPDF\b|\bWord\b|\bDOCX\b", line)]
    product_text = source_sections.get("Producto previsto") or source_sections.get("Productos")
    activity["products"] = [{"id": "product-local", "kind": "forum_participation" if is_forum else "questionnaire" if number == 5 else "documented_product",
        "recipient": None, "editable_format": None, "submission_format": "\n".join(format_lines) or None,
        "structure": [product_text] if product_text else [], "length": None, "filename_pattern": None, "accessibility": None,
        "requirement_ids": requirement_ids, "paths": {"editable": None, "delivery": None}}]
    if purpose:
        activity["alignment"] = [{"outcome_id": "outcome-local", "requirement_ids": requirement_ids, "step_ids": [item["id"] for item in activity["sequence"]],
                                 "product_ids": ["product-local"], "criterion_ids": [item["id"] for item in activity["assessment"]["criteria"]]}]
    notes = list((SUBJECT / "referencias-seminario-i/notas-seminario-i").glob(f"actividad-{number}-*")) if number else []
    if len(notes) == 1:
        activity["bindings"]["notes_directory"] = notes[0].relative_to(SUBJECT).as_posix()
        research = notes[0] / "investigacion"
        if research.is_dir():
            activity["bindings"]["research_directory"] = research.relative_to(SUBJECT).as_posix()
    reports = {suffix: f"reporte-seminario-i-Actividad-{number}.{suffix}" if (SUBJECT / f"reporte-seminario-i-Actividad-{number}.{suffix}").is_file() else None for suffix in ("tex", "pdf")}
    if number and number <= 14 and any(value is None for value in reports.values()):
        raise ValueError("missing_existing_report")
    omitted = number == 5
    if omitted and "T5 se omite por indicacion expresa" not in MASTER.read_text(encoding="utf-8"):
        raise ValueError("omission_not_documented")
    completed = number in {1, 2, 3, 8, 9, 10, 11, 12}
    bindings = {key: value for key, value in activity["bindings"].items() if value}
    document["extensions"]["editorial"] = {"number": number, "module_id": module, "title": title, "original_heading": record["heading"],
        "naming_evidence": "Encabezado de ficha y numeracion del documento maestro; reportes existentes cotejados sin renombrar.",
        "report": reports, "bindings": bindings, "evidence_paths": evidence_paths,
        "delivery_candidates": [path.relative_to(SUBJECT).as_posix() for path in (SUBJECT / "entregas-seminario-i").glob(f"Tarea{number}_*") if path.is_file()] if number else [],
        "generate_pdf_by_default": False, "already_completed_evidence": completed, "completion_evidence": "src-master; src-delivery-status" if completed else None,
        "omitted_by_user": omitted, "omission_evidence": "T5 se omite por indicacion expresa" if omitted else None,
        "execution_allowed": False, "submission_allowed": False, "moodle_required_for_planning": False,
        "calendar_historical": {"source_id": "src-local", "literal_lines": [line for line in record["text"].splitlines() if re.search(r"Cierre|Apertura|venc|\d{2}[-/]\d{2}[-/]20\d{2}", line, re.I)],
                                "master_source_id": "src-master", "operational": False},
        "section_origin": "Consigna local cotejada" if teacher_id else "Propuesta editorial; falta consigna docente integra"}
    document["field_status"] = [status("/identity", "inferred", "Identidad editorial local; periodo y modalidad no acreditados cuando estan vacios."),
        status("/activities/0/instruction", "confirmed" if teacher_id else "inferred", "Consigna cotejada con captura local." if teacher_id else "Propuesta editorial; no declarada consigna docente.", teacher_id or "src-local", instruction),
        status("/activities/0/requirements", "confirmed" if teacher_id else "inferred", "Segmentos literales, sin anadir exigencias.", teacher_id or "src-local"),
        status("/activities/0/questions", "confirmed" if teacher_id else "inferred", "Preguntas literales de la fuente.", teacher_id or "src-local"),
        status("/activities/0/assessment/criteria", "confirmed" if teacher_id else "inferred", "Filas literales; porcentajes no convertidos en calificacion ni escala oficial.", teacher_id or "src-local"),
        status("/activities/0/products", "inferred", "Clasificacion editorial y formatos citados; requieren cotejo de contrato completo.", "src-local"),
        status("/activities/0/sequence", "inferred", "Propuesta editorial, no secuencia docente."),
        status("/activities/0/alignment", "inferred", "Correspondencia editorial, no aprobacion academica."),
        status("/activities/0/calendar", "unknown", "Sin programacion operativa verificada. Literales conservados como evidencia no operativa.")]
    document["review"] = {"state": "needs_review", "reviewed_at": "2026-10-27", "reviewer_role": "integracion-documental-local", "semantic_validation": "failed",
        "critical_gaps": ["Cotejar contrato de producto, politicas y alineacion academica antes de habilitar.",
                          "La integracion documental no acredita apertura de plataforma, realizacion ni aprobacion academica."]}
    if not teacher_id:
        document["review"]["critical_gaps"].append("Consigna y rubrica docentes completas pendientes de recuperacion/cotejo; no se infieren de la propuesta editorial.")
    if omitted:
        document["review"]["critical_gaps"].append("Tarea 5 omitida por indicacion expresa documentada; no iniciar cuestionario ni generar entrega.")
    block_values = {"identidad_correspondencias": "cotejado", "consigna": "cotejada" if teacher_id else "propuesta_pendiente",
        "objetivos_temas": "documentados_parcialmente", "requisitos_preguntas": "segmentados", "secuencia": "propuesta_editorial", "recursos": "evidencias_locales",
        "productos": "pendiente_cotejo", "evaluacion_rubrica": "parcial" if activity["assessment"]["criteria"] else "pendiente", "politicas": "pendiente",
        "calendario": "sin_programacion", "alineacion": "propuesta_editorial", "rutas": "existencia_verificada", "evidencias_revision": "needs_review"}
    document["extensions"]["editorial"]["integration_blocks"] = block_values
    store = document["extensions"]["integrated_documents"]
    for path in [record["source"], *record["imports"]]:
        raw = originals[path]
        text = raw.decode("utf-8")
        if text.encode("utf-8") != raw:
            raise ValueError("lossy_absorption")
        store["objects"].setdefault(sha(raw), {"text": text})
        store["files"][path.relative_to(SUBJECT).as_posix()] = sha(raw)
    validate_pedagogical(document, SUBJECT)
    return document


def render(document: dict) -> str:
    activity = document["activities"][0]
    editorial = document["extensions"]["editorial"]
    label = f"Actividad {editorial['number']}" if editorial["number"] else "Foro de presentacion"
    lines = [f"# {label} · {activity['title']}", "", "Seminario I · Maestria en Gestion Administrativa · ITESCA", "",
             "> **Pendiente de revision academica.** Sin habilitacion de ejecucion ni autorizacion de envio.", ""]
    if editorial["omitted_by_user"]:
        lines.extend(["**OMISIÓN — SIN ACCIÓN A REALIZAR**, por indicacion expresa documentada para Tarea 5. No se declara resuelta ni se altera una calificacion.", ""])
    if editorial["already_completed_evidence"]:
        lines.extend(["**Existe evidencia documental de entrega. No repetir envios.** Los archivos locales listados no son, por ese solo hecho, las versiones enviadas.", ""])

    def section(title: str) -> None:
        lines.extend(["", "## " + title, ""])

    def cell(value) -> str:
        return "No documentado" if value is None else " ".join(str(value).split()).replace("|", "\\|")

    def table(headers: list[str], rows: list) -> None:
        lines.extend(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _heading in headers) + " |"])
        lines.extend("| " + " | ".join(cell(value) for value in row) + " |" for row in rows)

    section("1. Identidad y correspondencia")
    table(["Dato", "Valor"], [["Identidad editorial", label], ["Modulo documentado", editorial["module_id"]], ["Revision", document["revision"]], ["Correspondencia", editorial["naming_evidence"]]])
    section("2. Consigna y alcance documental")
    lines.extend(["**Origen:** " + editorial["section_origin"] + ".", "", activity["instruction"]])
    section("3. Objetivos y temas")
    lines.extend([document["curriculum"]["purpose"] or "Objetivo docente no acreditado en la ficha disponible.", "", "Tema editorial: " + activity["title"] + "."])
    section("4. Requisitos y preguntas")
    lines.append("Los siguientes fragmentos se transcriben de la fuente; su organizacion no crea nuevas exigencias.")
    for item in activity["requirements"]:
        lines.extend(["", f"- **{item['id']}:** {item['text']}"])
    if activity["questions"]:
        lines.extend(["", "### Preguntas literales", ""])
        lines.extend(f"{index}. {item['text']}" for index, item in enumerate(activity["questions"], 1))
    section("5. Secuencia editorial propuesta")
    table(["Paso", "Accion", "Resultado"], [[item["order"], item["action"], item["output"]] for item in activity["sequence"]])
    section("6. Recursos y evidencias")
    for path in editorial["evidence_paths"]:
        lines.append(f"- [{Path(path).name}](../{path.replace(' ', '%20')})")
    if not editorial["evidence_paths"]:
        lines.append("Recursos pendientes de cotejo. No se presume disponibilidad ni vigencia por aparecer en una propuesta.")
    section("7. Productos y formatos")
    product = activity["products"][0]
    lines.extend(["Contrato de producto pendiente de cotejo completo. No se genera un PDF de entrega por defecto.", "",
                  product["submission_format"] or "Formato docente no acreditado.", ""])
    lines.extend(product["structure"])
    lines.extend(["", "Los reportes existentes mantienen su plantilla institucional y estructura de introduccion, desarrollo tematico y conclusiones; no se renumeran ni se recompilan en esta integracion."])
    section("8. Evaluacion y rubrica")
    rows = [[item["text"], descriptor["description"], descriptor["level"]] for item in activity["assessment"]["criteria"] for descriptor in item["descriptors"]]
    if rows:
        table(["Criterio", "Descripcion literal", "Ponderacion registrada"], rows)
    else:
        lines.append("Rubrica pendiente de segmentacion o recuperacion. La ausencia de una tabla no acredita ausencia de criterios docentes.")
    lines.extend(["", "Se conservan las ponderaciones y discrepancias originales. No se infiere una escala total ni se emite calificacion oficial."])
    section("9. Politicas")
    lines.append("Las politicas docentes permanecen en la consigna literal; su segmentacion esta pendiente. No se presumen permisos de IA, prorroga, nuevos intentos o acceso a terceros.")
    section("10. Calendario operativo")
    lines.extend(["| Apertura | Prevista | Limite | Cierre | Zona horaria |", "| --- | --- | --- | --- | --- |", "|  |  |  |  |  |", "",
                  "Sin programacion verificable. Fechas vacias no acreditan apertura ni autorizan envios. Moodle es opcional como integracion.", "",
                  "<details>", "<summary>Literales documentales previos, no operativos</summary>", ""])
    lines.extend(editorial["calendar_historical"]["literal_lines"] or ["Las fechas documentales completas permanecen en las fuentes integradas."])
    lines.extend(["", "</details>"])
    section("11. Alineacion")
    lines.append("Propuesta editorial: contrastar cada requisito con el producto y su criterio de evaluacion; no equivale a validacion academica.")
    table(["Bloque", "Estado"], [[key.replace("_", " ").capitalize(), value.replace("_", " ")] for key, value in editorial["integration_blocks"].items()])
    section("12. Archivos existentes")
    for label, path in {"Reporte TEX": editorial["report"]["tex"], "Reporte PDF": editorial["report"]["pdf"], **editorial["bindings"]}.items():
        lines.append(f"- **{label}:** [{Path(path).name}](../{path.replace(' ', '%20')})" if path else f"- **{label}:** no existe archivo asociado; no se crea por inferencia.")
    if editorial["delivery_candidates"]:
        lines.extend(["", "### Archivos de entrega existentes", "", "Inventario local; no selecciona una version ni autoriza reenviarla.", ""])
        lines.extend(f"- [{Path(path).name}](../{path.replace(' ', '%20')})" for path in editorial["delivery_candidates"])
    section("13. Revision, estado y procedencia")
    lines.extend("- " + gap for gap in document["review"]["critical_gaps"])
    for heading in ("Estado observado", "Retroalimentacion consultada"):
        if heading in document["extensions"]["original_sections"]:
            lines.extend(["", "### " + heading + " en la captura original", "", document["extensions"]["original_sections"][heading]])
    lines.extend(["", "Los estados anteriores se distinguen de las confirmaciones posteriores del maestro y del estado de entregables. No se actualiza la plataforma.", "",
                  "La ficha anterior y sus conversiones se absorbieron completas, con sus SHA-256. No se conservan archivos paralelos ni carpetas de importacion."])
    return ("\n".join(lines) + "\n").replace("\r\n", "\n").replace("\r", "\n")


def render_index(catalog: dict) -> str:
    lines = ["# Planeaciones de Seminario I", "", "18 actividades y un foro de presentacion. Pares JSON/Markdown visuales, sin habilitacion automatica.", "",
             "| Actividad | Tema | Modulo documentado | Vista |", "| --- | --- | --- | --- |"]
    for item in catalog["activities"]:
        lines.append(f"| {item['number']} | {item['title']} | {item['module_id'] or ''} | [Planeacion]({Path(item['markdown']).name}) |")
    forum = catalog["complementary_plans"][0]
    lines.extend(["", "## Foro de presentacion", "", f"[Conectando nuestras ideas de investigacion]({Path(forum['markdown']).name}). Modulo {forum['module_id']}; sin numero de reporte. No esta omitido.", "",
                  "## Alcances y controles", "", "- Tarea 7 es un foro evaluable y conserva su numero 7.",
                  "- Tarea 5 mantiene la omision expresa documentada por el usuario; no se inicia cuestionario ni se crea una entrega sustitutiva.",
                  "- Los reportes 1 a 14 mantienen nombre y contenido. Para 15 a 18 no se inventan reportes ni IDs Moodle.",
                  "- Las fechas operativas quedan vacias; las capturas y fechas historicas permanecen en las fuentes integradas.",
                  "- Las 19 fichas y los 57 archivos de importacion se absorbieron completos, verificados por SHA-256, sin respaldos nuevos.",
                  "- La integracion tecnica no es aprobacion academica, calificacion oficial ni permiso de envio.", "",
                  "## Regeneracion", "", "El script local de integracion ofrece `--validate` y `--render-views`; ambos conservan el JSON como modelo principal. No consultan cuentas ni ejecutan actividades.", ""])
    return "\n".join(lines)


def prepare() -> tuple[dict, dict[Path, bytes], dict[Path, bytes]]:
    records, originals = inventory()
    catalog = {"version": "1.0", "date": "2026-10-27", "activities": [], "complementary_plans": [], "antecedents": [], "approved": [], "automatic_execution": False,
               "absorption": {"files": {}, "new_backup_files": 0}}
    prepared = {}
    for record in records:
        document = build(record, originals)
        filename = f"planeacion-seminario-i-Actividad-{record['number']}" if record["number"] else "planeacion-seminario-i-Foro-presentacion"
        destination = PLANS / (filename + ".json")
        report = validate_pedagogical(document, SUBJECT)
        entry = {"number": record["number"], "module_id": record["module_id"], "title": document["activities"][0]["title"], "json": destination.relative_to(SUBJECT).as_posix(),
                 "markdown": destination.with_suffix(".md").relative_to(SUBJECT).as_posix(), "plan_id": document["plan_id"], "revision": document["revision"],
                 "state": "needs_review", "semantic_passed": report["passed"], "findings": report["findings"], "execution_allowed": False, "submission_allowed": False}
        prepared[destination] = encoded(document)
        prepared[destination.with_suffix(".md")] = render(document).encode("utf-8")
        entry["sha256"] = sha(prepared[destination])
        catalog["activities" if record["number"] else "complementary_plans"].append(entry)
        for relative, digest in document["extensions"]["integrated_documents"]["files"].items():
            catalog["absorption"]["files"][relative] = {"target": entry["json"], "sha256": digest}
    prepared[CATALOG] = encoded(catalog)
    prepared[PLANS / "README.md"] = render_index(catalog).encode("utf-8")
    if len(catalog["absorption"]["files"]) != len(originals):
        raise ValueError("incomplete_absorption")
    for path in prepared:
        if path.exists():
            raise FileExistsError("canonical_destination_exists: " + path.name)
    return catalog, prepared, originals


def validate() -> dict:
    catalog = load(CATALOG)
    entries = catalog["activities"] + catalog["complementary_plans"]
    if len(entries) != 19 or [entry["number"] for entry in catalog["activities"]] != list(range(1, 19)):
        raise ValueError("invalid_final_inventory")
    if len(catalogued_plan_paths(SUBJECT)) != 19:
        raise ValueError("consumer_catalog_mismatch")
    errors = []
    documents = {}
    for entry in entries:
        path = SUBJECT / entry["json"]
        raw = path.read_bytes()
        document = json.loads(raw.decode("utf-8"))
        documents[entry["json"]] = document
        report = validate_pedagogical(document, SUBJECT)
        if report["findings"] != entry["findings"] or report["passed"] != entry["semantic_passed"]:
            errors.append(f"changed_findings: {entry['number']}")
        if sha(raw) != entry["sha256"]:
            errors.append(f"active_hash: {entry['number']}")
        for finding in report["findings"]:
            if finding["code"] in {"source_hash_changed", "missing_source", "unsafe_source_path", "unresolved_reference", "unresolved_pointer", "duplicate_id", "unresolved_evidence_source"}:
                errors.append(f"{entry['number']}: {finding['code']}")
        markdown_path = SUBJECT / entry["markdown"]
        markdown = markdown_path.read_text(encoding="utf-8")
        if markdown != render(document) or "```" in markdown:
            errors.append(f"markdown_derivation: {entry['number']}")
        if len(re.findall(r"^## \d+\.", markdown, re.M)) != 13:
            errors.append(f"markdown_structure: {entry['number']}")
        if any(document["activities"][0]["calendar"].values()):
            errors.append(f"operational_date: {entry['number']}")
        for target in re.findall(r"\]\(([^)]+)\)", markdown):
            if "://" not in target and not target.startswith("#"):
                if not (markdown_path.parent / unquote(target.split("#")[0])).exists():
                    errors.append(f"missing_markdown_link: {entry['number']}: {target}")
        if entry["number"]:
            if path.name != f"planeacion-seminario-i-Actividad-{entry['number']}.json":
                errors.append("editorial_name_mismatch")
        if document["extensions"]["editorial"]["omitted_by_user"] != (entry["number"] == 5):
            errors.append("omission_scope_mismatch")
    for relative, record in catalog["absorption"]["files"].items():
        raw = documents[record["target"]]["extensions"]["integrated_documents"]["objects"][record["sha256"]]["text"].encode("utf-8")
        if sha(raw) != record["sha256"] or (SUBJECT / relative).exists():
            errors.append("absorption_integrity: " + relative)
    if (PLANS / "importaciones").exists() or list(PLANS.glob("Planeacion - *.md")):
        errors.append("old_files_remaining")
    if (PLANS / "README.md").read_text(encoding="utf-8") != render_index(catalog):
        errors.append("index_derivation")
    return {"passed": not errors, "errors": errors, "activity_pairs": 18, "forum_pairs": 1,
            "absorbed_files": len(catalog["absorption"]["files"]), "ready": 0, "execution": False, "submission": False}


def apply() -> dict:
    if CATALOG.exists():
        return validate()
    catalog, prepared, originals = prepare()
    for path, raw in prepared.items():
        with path.open("xb") as stream:
            stream.write(raw)
    saved = load(CATALOG)
    for path, raw in prepared.items():
        if path.read_bytes() != raw:
            raise ValueError("publication_verification_failed")
    for path, raw in originals.items():
        record = saved["absorption"]["files"][path.relative_to(SUBJECT).as_posix()]
        document = load(SUBJECT / record["target"])
        integrated = document["extensions"]["integrated_documents"]["objects"][record["sha256"]]["text"].encode("utf-8")
        if path.read_bytes() != raw or integrated != raw:
            raise ValueError("absorption_verification_failed_before_deletion")
    for path in originals:
        path.unlink()
    directory = PLANS / "importaciones"
    for child in sorted((path for path in directory.rglob("*") if path.is_dir()), key=lambda path: len(path.parts), reverse=True):
        child.rmdir()
    directory.rmdir()
    return validate()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--render-views", action="store_true")
    arguments = parser.parse_args()
    if arguments.apply:
        result = apply()
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result["passed"] else 1
    if arguments.render_views:
        catalog = load(CATALOG)
        for entry in catalog["activities"] + catalog["complementary_plans"]:
            (SUBJECT / entry["markdown"]).write_text(render(load(SUBJECT / entry["json"])), encoding="utf-8", newline="\n")
        (PLANS / "README.md").write_text(render_index(catalog), encoding="utf-8", newline="\n")
    if arguments.validate or arguments.render_views:
        result = validate()
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result["passed"] else 1
    if arguments.prepare:
        catalog, prepared, originals = prepare()
        print(json.dumps({"pairs": len(catalog["activities"]) + len(catalog["complementary_plans"]), "outputs": len(prepared), "absorbed_files": len(originals), "writes": 0}, ensure_ascii=True))
        return 0
    records, originals = inventory()
    print(json.dumps({"activities": 18, "presentation_forum": 1, "original_files": len(originals),
                      "mapping": [{"number": item["number"], "module_id": item["module_id"], "source": item["source"].name} for item in records],
                      "writes": 0}, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())