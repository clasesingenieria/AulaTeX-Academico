from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from .node_planning import PEDAGOGICAL_SCHEMA_PATH, draft_plan, plan_directory, publish_plan, validate_schema
from .planning_layout import _reject_credentials, _require_versionable, catalogued_plan_paths, subject_artifact_contract, subject_layout
from .planning_validation import validate_pedagogical
from .workspace import AulaTeXWorkspace, EditorialScope


def read_planning_source(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict):
            raise ValueError("unsupported_json_root")
        _reject_credentials(payload)
        return payload, []
    if suffix == ".pdf":
        import pymupdf

        with pymupdf.open(path) as document:
            blocks = [{"locator": f"page:{index + 1}", "text": page.get_text("text", sort=True)} for index, page in enumerate(document)]
    elif suffix == ".docx":
        from docx import Document

        document = Document(path)
        blocks = [{"locator": f"body:{index + 1}", "text": "\n".join(element.xpath(".//w:t/text()"))} for index, element in enumerate(document.element.body)]
    elif suffix in {".html", ".htm"}:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(path.read_text(encoding="utf-8-sig"), "html.parser")
        for element in soup(["script", "style"]):
            element.decompose()
        blocks = [{"locator": "body", "text": soup.get_text("\n", strip=True)}]
    elif suffix in {".md", ".txt", ".markdown"}:
        blocks = [{"locator": "document", "text": path.read_text(encoding="utf-8-sig")}]
    else:
        raise ValueError("unsupported_source_format")
    if not any(block["text"].strip() for block in blocks):
        raise ValueError("empty_document_or_ocr_required")
    _reject_credentials(blocks)
    return None, blocks


def _text(value: Any) -> str | None:
    if isinstance(value, dict):
        return _text(value.get("value"))
    if isinstance(value, str) and value.strip():
        return value
    return None


def _items(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        items = [_text(item) for item in value]
        return [item for item in items if item]
    return []


def _field_state(path: str, state: str, reason: str, locator: str | None = None, quote: str | None = None) -> dict[str, Any]:
    return {"path": path, "state": state, "reason": reason, "evidence": [{"source_id": "src-local", "locator": locator, "quoted_text": quote}] if locator else [], "alternatives": []}


def _empty_activity(identifier: str, title: str) -> dict[str, Any]:
    return {
        "id": identifier, "title": title, "role": "learning", "platform": None, "unit_id": None, "weeks": [], "outcome_ids": [], "topic_ids": [],
        "cognitive": {key: None for key in ("taxonomy", "level", "verb", "object", "conditions", "observable_evidence", "justification")},
        "instruction": None, "requirements": [], "questions": [], "sequence": [], "resources": [],
        "assessment": {"kind": None, "scale_total": None, "weight": None, "weight_unit": None, "criteria": [], "editorial_checks": []},
        "products": [], "calendar": {key: None for key in ("opens_at", "expected_at", "due_at", "closes_at", "timezone", "literal")},
        "policies": {key: None for key in ("ai", "integrity", "collaboration", "citation", "attempts", "late_submission", "accessibility", "privacy")},
        "dependencies": [], "alignment": [], "bindings": {"extractor_directory": None, "notes_directory": None, "research_directory": None},
    }


def convert_source(workspace: AulaTeXWorkspace, subject: EditorialScope, source_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if subject.level != "materia":
        raise ValueError("conversion_requires_subject")
    root = workspace.resolve_target(subject.relative_path)
    source_path = source_path.resolve()
    if not source_path.is_relative_to(root):
        raise ValueError("source_outside_subject")
    raw = source_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    imported, blocks = read_planning_source(source_path)
    data = imported or {}
    if data.get("document_type") == "planning_index":
        raise ValueError("auxiliary_planning_index")
    if imported is not None and imported.get("schema_version") == "1.0.0":
        raise ValueError("already_canonical_use_validation")
    if "activity_id_local" in data and isinstance(data.get("product"), dict):
        product = data["product"]
        requirements = [item["description"] for item in product.get("content_requirements", []) if isinstance(item, dict) and _text(item.get("description"))]
        originals = [("/", dict(data, id=str(data.get("moodle_module_id") or data.get("activity_id_aula")), requirements=requirements, format=_text(product.get("format")), product=product.get("type")))]
    elif isinstance(data.get("activity"), dict):
        originals = [("/activity", data["activity"])]
    elif isinstance(data.get("activities"), list) and data["activities"]:
        originals = [(f"/activities/{index}", activity) for index, activity in enumerate(data["activities"])]
    elif data.get("mode") == "ruta_preparatoria_no_oficial" and isinstance(data.get("blocks"), list):
        originals = [(f"/blocks/{index}", dict(block, id=f"preparatoria-{index + 1}", requirements=block.get("tasks_proposed", []), type="self_study")) for index, block in enumerate(data["blocks"])]
    elif imported is None:
        originals = [("document", {"id": "source-" + digest[:16], "title": source_path.stem})]
    else:
        raise ValueError("json_without_activity_contract")
    if not originals or any(not isinstance(activity, dict) for _locator, activity in originals):
        raise ValueError("invalid_activity_contract")

    key_hash = hashlib.sha256((subject.key + "/" + source_path.relative_to(root).as_posix()).encode("utf-8")).hexdigest()[:20]
    period = _text(data.get("period"))
    offering = "oferta-" + hashlib.sha256((subject.key + ":" + (period or "pendiente")).encode("utf-8")).hexdigest()[:16]
    contract = subject_artifact_contract(root)
    canonical = {
        "schema_version": "1.0.0", "plan_id": "pca-" + key_hash, "revision": 1,
        "identity": {"institution": subject.institution, "program": _text(data.get("program")) or subject.career or None, "subject_id": subject.subject, "subject_title": _text(data.get("subject")) or _text(data.get("course", {}).get("name")) or subject.label, "offering_id": offering, "period": period, "modality": None},
        "sources": [{"id": "src-local", "kind": {".pdf": "pdf", ".docx": "docx", ".html": "platform", ".htm": "platform"}.get(source_path.suffix.lower(), "other"), "authority": "editorial" if imported is not None else "unknown", "title": source_path.name, "url": None, "path": source_path.relative_to(root).as_posix(), "sha256": digest, "captured_at": _text(data.get("retrieved_at_utc")) or _text(data.get("consulted_on")) or _text(data.get("revision_date")), "media_type": {".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".json": "application/json"}.get(source_path.suffix.lower(), "text/plain")}],
        "curriculum": {"purpose": _text(data.get("purpose")), "competencies": [], "outcomes": [], "topics": []},
        "activities": [], "field_status": [],
        "review": {"state": "needs_review", "reviewed_at": None, "reviewer_role": None, "critical_gaps": ["Cotejar consigna y procedencia docente; conversion local no equivale a aprobacion"], "semantic_validation": "failed"},
        "artifact_contract": contract,
        "extensions": {"conversion": {"version": "1.0", "source_format": source_path.suffix.lower(), "source_sha256": digest, "source_payload": imported, "source_blocks": blocks, "unsegmented_document": imported is None, "period_pending": period is None, "activity_mapping": []}},
    }
    statuses = canonical["field_status"]
    statuses.append(_field_state("/identity", "inferred", "Identidad editorial del catalogo; oferta interna, periodo y modalidad no acreditados cuando faltan."))
    statuses.append(_field_state("/sources", "confirmed", "Archivo local preservado; su huella no acredita autoria ni vigencia docente.", "local-file"))
    statuses.append(_field_state("/curriculum", "unknown", "No se deducen competencias, resultados ni temario que no esten documentados."))
    if canonical["curriculum"]["purpose"]:
        statuses.append(_field_state("/curriculum/purpose", "inferred", "Proposito preservado; el modelo anterior puede contener una parafrasis.", "/purpose", canonical["curriculum"]["purpose"]))
    for index, (locator, original) in enumerate(originals):
        identifier = str(original.get("id", ""))
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", identifier):
            raise ValueError("activity_id_missing_or_unsafe")
        activity = _empty_activity(identifier, _text(original.get("title")) or "Documento pendiente de segmentacion")
        activity["policies"]["exceptions"] = []
        path = f"/activities/{index}"
        kind = original.get("type") or original.get("kind")
        if kind == "self_study":
            activity["role"] = "self_study"
        elif kind in {"quiz", "scorm", "h5p"}:
            activity["role"] = "assessment"
        course_id = data.get("course_id") or data.get("moodle_course_id") or data.get("course", {}).get("id")
        if course_id is not None and kind != "self_study":
            activity["platform"] = {"name": "Moodle", "course_id": str(course_id), "module_ids": [identifier]}
        if original.get("unit") is not None:
            activity["unit_id"] = str(original["unit"])
        week = original.get("week")
        if isinstance(week, int) and week > 0:
            activity["weeks"] = [week]
        requirements = _items(original.get("requirements"))
        activity["requirements"] = [{"id": f"req-{position + 1:03d}", "text": text} for position, text in enumerate(requirements)]
        if imported is None:
            activity["instruction"] = "\n\n".join(f"[{block['locator']}]\n{block['text']}" for block in blocks)
        else:
            activity["instruction"] = _text(original.get("instruction")) or ("\n".join(requirements) if requirements else None)
        statuses.append(_field_state(path, "unknown", "Campos sin datos no se completan por inferencia; la consigna puede estar resumida o sin segmentar."))
        statuses.append(_field_state(path + "/role", "inferred", "Clasificacion operativa provisional a partir del tipo original; no impone obligatoriedad."))
        if activity["instruction"]:
            statuses.append(_field_state(path + "/instruction", "inferred", "Texto completo importado o requisitos del modelo local; pendiente cotejo con consigna docente.", locator, activity["instruction"]))
        objective_fields = ("official_objective", "proposed_objective", "objective_proposed", "objective")
        objective_field = next((field for field in objective_fields if _text(original.get(field))), None)
        if objective_field:
            objective = _text(original[objective_field])
            outcome_id = "outcome-" + identifier
            position = len(canonical["curriculum"]["outcomes"])
            canonical["curriculum"]["outcomes"].append({"id": outcome_id, "text": objective})
            activity["outcome_ids"] = [outcome_id]
            state = "confirmed" if objective_field == "official_objective" else "inferred"
            statuses.append(_field_state(f"/curriculum/outcomes/{position}", state, "Objetivo preservado del modelo local; oficialidad y propuesta no se equiparan.", locator + "/" + objective_field, objective))
        topic = _text(original.get("topic")) or _text(original.get("section"))
        if topic:
            topic_id = "topic-" + identifier
            position = len(canonical["curriculum"]["topics"])
            canonical["curriculum"]["topics"].append({"id": topic_id, "text": topic, "children": []})
            activity["topic_ids"] = [topic_id]
            statuses.append(_field_state(f"/curriculum/topics/{position}", "confirmed", "Tema o seccion explicitamente registrado en el modelo local.", locator + "/topic", topic))
        if requirements:
            state = "inferred" if kind == "self_study" else "confirmed"
            statuses.append(_field_state(path + "/requirements", state, "Coinciden con la entrada local; no se acredita que sean requisitos docentes integros.", locator + "/requirements"))
        for position, question in enumerate(_items(original.get("observed_questions"))):
            activity["questions"].append({"id": f"question-{position + 1:03d}", "context": None, "text": question, "requirement_ids": []})
        calendar = original.get("calendar") if isinstance(original.get("calendar"), dict) else {}
        for target, aliases in {"opens_at": ("opens_at", "opening"), "due_at": ("due_at", "due"), "closes_at": ("closes_at", "closing"), "expected_at": ("expected_at",), "timezone": ("timezone",), "literal": ("literal",)}.items():
            activity["calendar"][target] = next((_text(calendar.get(alias)) for alias in aliases if _text(calendar.get(alias))), None)
        if activity["calendar"]["literal"] is None:
            activity["calendar"]["literal"] = _text(original.get("dates_and_status"))
        sequence = original.get("proposed_sequence") or original.get("sequence") or original.get("tasks_proposed") or []
        for position, step in enumerate(sequence if isinstance(sequence, list) else []):
            action = _text(step) or (_text(step.get("student")) if isinstance(step, dict) else None) or (_text(step[1]) if isinstance(step, list) and len(step) > 1 else None)
            if not action:
                continue
            phase = step.get("phase") if isinstance(step, dict) else (step[0] if isinstance(step, list) and step else None)
            phase_key = "".join(character for character in unicodedata.normalize("NFKD", str(phase).casefold()) if not unicodedata.combining(character))
            phase = {"preparacion": "preparation", "cierre": "review"}.get(phase_key, "construction")
            activity["sequence"].append({"id": f"step-{position + 1:03d}", "order": position + 1, "phase": phase, "action": action, "inputs": [], "output": "Salida pendiente de precisar", "completion_check": "Cotejar criterio observable antes de ejecutar", "requirement_ids": [], "depends_on": []})
        cognitive = original.get("cognitive")
        if isinstance(cognitive, dict):
            for field in activity["cognitive"]:
                activity["cognitive"][field] = _text(cognitive.get(field))
            statuses.append(_field_state(path + "/cognitive", "inferred", "Demanda cognitiva explicitamente aportada; no se deduce nivel solo por un verbo.", locator + "/cognitive"))
        if activity["sequence"]:
            statuses.append(_field_state(path + "/sequence", "inferred", "Secuencia propuesta preservada; fases, insumos, salidas y controles necesitan revision.", locator + "/sequence"))
        product = _text(original.get("product")) or _text(original.get("practice_product_proposed"))
        if product:
            activity["products"] = [{"id": "product-001", "kind": "platform_response" if kind in {"quiz", "scorm", "h5p"} else "unspecified", "recipient": None, "editable_format": None, "submission_format": _text(original.get("format")), "structure": [product], "length": None, "filename_pattern": None, "accessibility": None, "requirement_ids": [], "paths": {"editable": None, "delivery": None}}]
            statuses.append(_field_state(path + "/products", "inferred", "Descripcion original preservada; no convierte examen o foro en informe LaTeX.", locator + "/product", product))
        activity["assessment"]["editorial_checks"] = _items(original.get("proposed_review_criteria")) or _items(original.get("review_criteria_proposed")) or _items(original.get("criterion_proposed"))
        activity["bindings"] = {"extractor_directory": contract["paths_relative_to_subject"]["extractions"], "notes_directory": contract["paths_relative_to_subject"]["notes"], "research_directory": contract["paths_relative_to_subject"]["research"]}
        canonical["activities"].append(activity)
        numbering = data.get("chronological_numbering", {})
        local_number = numbering.get("local_number") if len(originals) == 1 else None
        if local_number is None:
            local_number = original.get("activity_id_local")
        canonical["extensions"]["conversion"]["activity_mapping"].append({"activity_id": identifier, "local_number": local_number, "source_locator": locator, "source_is_summary": imported is not None})
        for pending in _items(original.get("pending")):
            if pending not in canonical["review"]["critical_gaps"]:
                canonical["review"]["critical_gaps"].append(pending)
    if imported is None:
        canonical["review"]["critical_gaps"].append("Documento sin segmentar: identificar actividades, requisitos, preguntas y rubrica antes de ejecutar")
    previous = sorted((subject_layout(root)["plans"] / "importaciones" / canonical["plan_id"]).glob("r*/planeacion.json"))
    if previous:
        last = json.loads(previous[-1].read_text(encoding="utf-8"))
        canonical["revision"] = last["revision"] if last["extensions"]["conversion"]["source_sha256"] == digest else last["revision"] + 1
        if canonical["revision"] == last["revision"] and canonical != last:
            canonical["revision"] += 1
    validate_schema(canonical, PEDAGOGICAL_SCHEMA_PATH)
    return canonical, canonical["extensions"]["conversion"]["activity_mapping"]


def render_editorial_markdown(document: dict[str, Any], source_prefix: str = "../") -> str:
    identity = document["identity"]
    organization = document.get("extensions", {}).get("organizacion_interna", {})
    labels = {"draft": "Borrador", "needs_review": "Pendiente de revision academica", "ready": "Revision editorial aprobada", "superseded": "Revision sustituida"}
    lines = [f"# {identity['subject_title']}", "", f"**{labels[document['review']['state']]}.** Revision editorial {document['revision']}. No autoriza publicaciones ni envios.", "", "## Identidad", "", "| Dato | Valor |", "| --- | --- |"]
    for label, value in (("Institucion", identity["institution"]), ("Programa", identity["program"]), ("Reporte interno", organization.get("internal_number")), ("Numero oficial", organization.get("official_number")), ("Periodo", identity["period"])):
        lines.append(f"| {label} | {value if value is not None else ''} |")

    def paragraphs(title: str, values: list[str]) -> None:
        lines.extend(["", "### " + title, ""])
        lines.extend(["- " + value for value in values] or ["No documentado; pendiente de cotejo."])

    outcomes = {item["id"]: item["text"] for item in document["curriculum"]["outcomes"]}
    topics: dict[str, str] = {}

    def collect_topics(items: list[dict[str, Any]]) -> None:
        for item in items:
            topics[item["id"]] = item["text"]
            collect_topics(item["children"])

    collect_topics(document["curriculum"]["topics"])
    for activity in document["activities"]:
        lines.extend(["", "## " + activity["title"], "", "Semana: " + ", ".join(str(week) for week in activity["weeks"]), "", "### Consigna docente", "", activity["instruction"] or "Consigna no archivada; no completar por analogia."])
        paragraphs("Objetivos", [outcomes[identifier] for identifier in activity["outcome_ids"] if identifier in outcomes])
        paragraphs("Temas", [topics[identifier] for identifier in activity["topic_ids"] if identifier in topics])
        paragraphs("Requisitos", [item["text"] for item in activity["requirements"]])
        lines.extend(["", "### Preguntas y casos", ""])
        contexts: set[str] = set()
        for index, question in enumerate(activity["questions"], 1):
            if question["context"] and question["context"] not in contexts:
                lines.extend([question["context"], ""])
                contexts.add(question["context"])
            lines.extend([f"{index}. {question['text']}", ""])
        if not activity["questions"]:
            lines.append("No hay preguntas independientes documentadas.")
        paragraphs("Secuencia editorial propuesta", [f"{step['order']}. {step['action']} Resultado: {step['output']} Comprobacion: {step['completion_check']}" for step in sorted(activity["sequence"], key=lambda item: item["order"])])
        lines.extend(["", "### Productos y formato", ""])
        for product in activity["products"]:
            lines.append("- " + "; ".join(product["structure"]))
            for label, key in (("Formato editable docente", "editable_format"), ("Formato de entrega", "submission_format"), ("Extension", "length"), ("Nombre de entrega", "filename_pattern")):
                if product[key] is not None:
                    lines.append(f"  {label}: {product[key]}")
        assessment = activity["assessment"]
        lines.extend(["", "### Evaluacion y rubrica", "", f"Puntaje del instrumento: {assessment['scale_total'] if assessment['scale_total'] is not None else 'No documentado'}.", "", "| Criterio docente | Puntos |", "| --- | --- |"])
        for criterion in assessment["criteria"]:
            lines.append(f"| {criterion['text'].replace('|', '/').replace(chr(10), ' ')} | {criterion['points'] if criterion['points'] is not None else ''} |")
            for descriptor in criterion["descriptors"]:
                lines.append(f"| {descriptor['level']}: {descriptor['description'].replace('|', '/').replace(chr(10), ' ')} | {descriptor['points'] if descriptor['points'] is not None else ''} |")
        if not assessment["criteria"]:
            lines.append("| Rubrica no documentada | |")
        paragraphs("Controles editoriales", assessment["editorial_checks"])
        policy_labels = {"ai": "Inteligencia artificial", "integrity": "Integridad academica", "collaboration": "Colaboracion", "citation": "Citas y referencias", "attempts": "Intentos", "late_submission": "Entrega extemporanea", "accessibility": "Accesibilidad", "privacy": "Privacidad"}
        paragraphs("Politicas", [f"{label}: {activity['policies'][key]}" for key, label in policy_labels.items() if activity["policies"][key] is not None] + [item["reason"] for item in activity["policies"].get("exceptions", [])])
        lines.extend(["", "### Calendario operativo", "", "| Dato | Fecha |", "| --- | --- |"])
        for label, key in (("Apertura", "opens_at"), ("Fecha esperada", "expected_at"), ("Entrega", "due_at"), ("Cierre", "closes_at"), ("Zona horaria", "timezone")):
            lines.append(f"| {label} | {activity['calendar'][key] or ''} |")
        lines.extend(["", "Los plazos originales se conservan como evidencia documental; no acreditan disponibilidad actual ni reapertura."])
        requirement_text = {item["id"]: item["text"] for item in activity["requirements"]}
        paragraphs("Alineacion editorial propuesta", [outcomes.get(item["outcome_id"], "Objetivo pendiente") + ": " + "; ".join(requirement_text[identifier] for identifier in item["requirement_ids"] if identifier in requirement_text) for item in activity["alignment"]])
    lines.extend(["", "## Recursos documentales", ""])
    for source in document["sources"]:
        label = source["title"]
        lines.append(f"- [{label}]({source_prefix}{source['path'].replace(' ', '%20')})" if source["path"] else "- " + label)
    editorial = document.get("extensions", {}).get("editorial_view", {})
    for text in editorial.get("warnings", []):
        lines.extend(["", text])
    paragraphs("Pendientes y limites de revision", document["review"]["critical_gaps"])
    return "\n".join(lines) + "\n"


def render_pedagogical_markdown(document: dict[str, Any]) -> str:
    if document.get("extensions", {}).get("editorial_view"):
        return render_editorial_markdown(document)
    lines = [f"# Planeacion: {document['identity']['subject_title']}", "", f"Estado: {document['review']['state']}. Revision local; no autoriza envios a plataforma.", "", "## Identificacion", "", "```json", json.dumps(document["identity"], ensure_ascii=False, indent=2), "```"]
    for activity in document["activities"]:
        lines.extend(["", f"## Actividad {activity['id']}: {activity['title']}", "", "### Consigna importada", "", activity["instruction"] or "No documentada", "", "### Requisitos", ""])
        lines.extend(f"{index + 1}. {item['text']}" for index, item in enumerate(activity["requirements"]))
        for name in ("platform", "role", "unit_id", "weeks", "outcome_ids", "topic_ids", "questions", "cognitive", "sequence", "products", "assessment", "policies", "resources", "dependencies", "alignment", "bindings"):
            lines.extend(["", "### " + name, "", "```json", json.dumps(activity[name], ensure_ascii=False, indent=2), "```"])
        lines.extend(["", "### calendar", "", "| Campo operativo | Valor |", "| --- | --- |"])
        for name in ("opens_at", "expected_at", "due_at", "closes_at", "timezone"):
            lines.append(f"| {name} | {activity['calendar'].get(name) or ''} |")
        if activity["calendar"].get("literal"):
            lines.extend(["", "Evidencia historica del calendario (no programacion operativa):", "", activity["calendar"]["literal"]])
    for name in ("curriculum", "artifact_contract", "sources", "field_status", "review", "extensions"):
        lines.extend(["", "## " + name, "", "```json", json.dumps(document[name], ensure_ascii=False, indent=2), "```"])
    return "\n".join(lines) + "\n"


def publish_conversion(workspace: AulaTeXWorkspace, subject: EditorialScope, document: dict[str, Any]) -> dict[str, Any]:
    validate_schema(document, PEDAGOGICAL_SCHEMA_PATH)
    root = workspace.resolve_target(subject.relative_path)
    state = document["review"]["state"]
    if document["identity"]["subject_id"] != subject.subject or state not in {"needs_review", "ready"}:
        raise ValueError("conversion_identity_or_state_mismatch")
    report = validate_pedagogical(document, root)
    if state == "ready" and (not report["passed"] or not document["review"]["reviewed_at"] or not document["review"]["reviewer_role"]):
        raise ValueError("review_not_validated")
    directory = subject_layout(root)["plans"] / "importaciones" / document["plan_id"] / f"r{document['revision']:04d}"
    if not directory.resolve().is_relative_to(root):
        raise ValueError("unsafe_conversion_output")
    outputs = {
        directory / "planeacion.json": (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        directory / "planeacion.md": render_pedagogical_markdown(document).encode("utf-8"),
        directory / "cotejo-local.json": (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    }
    _require_versionable(root, list(outputs))
    for path, content in outputs.items():
        if path.exists() and path.read_bytes() != content:
            raise FileExistsError("conversion_revision_conflict")
    directory.mkdir(parents=True, exist_ok=True)
    for path, content in outputs.items():
        if not path.exists():
            with path.open("xb") as stream:
                stream.write(content)
    return {"plan_id": document["plan_id"], "pedagogical_json": workspace.relative(directory / "planeacion.json"), "artifacts": [workspace.relative(path) for path in outputs], "semantic_passed": report["passed"], "findings": report["findings"], "state": state}


def publish_candidate_nodes(workspace: AulaTeXWorkspace, records: list[dict[str, Any]]) -> dict[str, Any]:
    scopes, _children = workspace.editorial_scope_index()
    candidates: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for record in records:
        for candidate in record.get("candidate_node_bindings", []):
            candidates.setdefault(candidate["scope_key"], []).append((record, candidate))
    ambiguous = sorted(key for key, values in candidates.items() if len(values) != 1)
    needed: set[str] = set()
    for key in candidates.keys() - set(ambiguous):
        scope = scopes[key]
        while True:
            needed.add(scope.key)
            if not scope.parent_key:
                break
            scope = scopes[scope.parent_key]
    published: dict[str, dict[str, Any]] = {}
    for scope in sorted((scopes[key] for key in needed), key=lambda item: (item.depth, item.key)):
        model = draft_plan(scope)
        model["review"] = {"state": "needs_review", "semantic_validation": "failed", "critical_gaps": ["Perfil y fuentes pendientes de cotejo; publicacion no habilita ejecucion"]}
        if scope.parent_key in published:
            parent = published[scope.parent_key]
            model["bindings"]["parent_plan"] = {"path": parent["path"], "sha256": parent["sha256"], "activity_id": None}
        if scope.level == "actividad":
            record, candidate = candidates[scope.key][0]
            path = workspace.resolve_target(record["pedagogical_json"])
            document = json.loads(path.read_text(encoding="utf-8"))
            activity = next(item for item in document["activities"] if item["id"] == candidate["activity_id"])
            model["profile"]["activity_id"] = candidate["activity_id"]
            model["profile"]["offering_id"] = candidate["offering_id"]
            model["profile"]["product_ids"] = [item["id"] for item in activity["products"]]
            model["bindings"]["pedagogical_plan"] = {"path": record["pedagogical_json"], "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "activity_id": candidate["activity_id"]}
        previous = sorted(plan_directory(workspace, scope).parent.glob("r*/planeacion.json"))
        if previous:
            last = json.loads(previous[-1].read_text(encoding="utf-8"))
            model["revision"] = last["revision"]
            if model != last:
                model["revision"] += 1
        path, _markdown = publish_plan(workspace, scope, model)
        published[scope.key] = {"scope_key": scope.key, "level": scope.level, "path": workspace.relative(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "revision": model["revision"], "state": "needs_review"}
    return {"approved": [], "pending": list(published.values()), "ambiguous_scope_keys": ambiguous, "automatic_execution": False}


def convert_local_batch(workspace: AulaTeXWorkspace, output: Path, target: str = ".", *, publish_bindings: bool = False) -> dict[str, Any]:
    from jsonschema import ValidationError

    target_path = workspace.resolve_target(target)
    output = output.resolve()
    if not output.is_relative_to(workspace.repo_root):
        raise ValueError("batch_output_outside_project")
    manifest_path = output / "resultado-conversion.json"
    markdown_path = output / "resultado-conversion.md"
    if any((output / name).exists() for name in ("resultado-conversion.json", "resultado-conversion.md", "indice-planeaciones.json", "cola-cotejo.json")):
        raise FileExistsError("batch_output_exists")
    scopes = workspace.scan_editorial_scopes()
    rows = []
    subject_count = 0
    for subject in (scope for scope in scopes if scope.level == "materia"):
        root = workspace.resolve_target(subject.relative_path)
        if not root.is_relative_to(target_path) and root != target_path:
            continue
        subject_count += 1
        catalogued = catalogued_plan_paths(root)
        files = list(catalogued or ())
        if catalogued is None:
            for folder in sorted(root.glob("planeaciones*")):
                if folder.is_dir():
                    files.extend(path for path in folder.rglob("*") if path.is_file() and not any(part in {"canonicas", "importaciones", "planeaciones-generadas"} for part in path.relative_to(folder).parts))
        for path in sorted(set(files)):
            stem = "".join(character for character in unicodedata.normalize("NFKD", path.stem.casefold()) if not unicodedata.combining(character))
            if path.suffix.lower() not in {".json", ".pdf", ".md", ".txt", ".docx", ".html", ".htm"} or not stem.startswith(("planeacion", "planificacion", "consigna", "ruta-preparatoria", "modelo-planeacion")):
                continue
            row = {"subject_key": subject.key, "source": workspace.relative(path), "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            try:
                if catalogued is not None:
                    document = json.loads(path.read_text(encoding="utf-8-sig"))
                    report = validate_pedagogical(document, root)
                    if document["identity"]["subject_id"] != subject.subject:
                        raise ValueError("catalog_subject_mismatch")
                    row.update(state="catalogued", plan_id=document["plan_id"], pedagogical_json=workspace.relative(path), review_state=document["review"]["state"], semantic_passed=report["passed"], findings=report["findings"])
                    rows.append(row)
                    continue
                document, mapping = convert_source(workspace, subject, path)
                result = publish_conversion(workspace, subject, document)
                candidates = []
                for item in mapping:
                    if item["local_number"] is not None:
                        key = subject.key + f"/actividad-{item['local_number']}"
                        if any(scope.key == key for scope in scopes):
                            candidates.append({"scope_key": key, "activity_id": item["activity_id"], "offering_id": document["identity"]["offering_id"]})
                row.update(result, activity_mapping=mapping, candidate_node_bindings=candidates)
            except (OSError, ValueError, KeyError, TypeError, AttributeError, ValidationError, ImportError) as error:
                known_reasons = {"unsupported_json_root", "unsupported_source_format", "empty_document_or_ocr_required", "already_canonical_use_validation", "json_without_activity_contract", "invalid_activity_contract", "activity_id_missing_or_unsafe", "auxiliary_planning_index"}
                reason = str(error) if isinstance(error, ValueError) and str(error) in known_reasons else type(error).__name__
                row.update(state="skipped_index" if reason == "auxiliary_planning_index" else "not_converted", reason=reason)
            rows.append(row)
    registry = publish_candidate_nodes(workspace, rows) if publish_bindings else {"approved": [], "pending": [], "ambiguous_scope_keys": [], "automatic_execution": False}
    linked_keys = {item["scope_key"] for item in registry["pending"] if item["level"] == "actividad"}
    source_by_subject: dict[str, list[str]] = {}
    for row in rows:
        source_by_subject.setdefault(row["subject_key"], []).append(row["source"])
    queue = [{"scope_key": scope.key, "subject_key": scope.parent_key, "state": "linked_needs_review" if scope.key in linked_keys else "pending_source_mapping", "candidate_subject_sources": source_by_subject.get(scope.parent_key, []), "ready": False} for scope in scopes if scope.level == "actividad" and workspace.resolve_target(scope.relative_path).is_relative_to(target_path)]
    registry["unmapped_activity_scope_keys"] = [item["scope_key"] for item in queue if item["state"] == "pending_source_mapping"]
    result = {"kind": "local-planning-conversion", "version": "1.0", "mode": "publish_needs_review_only", "subjects_scanned": subject_count, "converted": sum(row["state"] == "needs_review" for row in rows), "not_converted": sum(row["state"] == "not_converted" for row in rows), "skipped_indexes": sum(row["state"] == "skipped_index" for row in rows), "node_plans_published": len(registry["pending"]), "ready": 0, "automatic_execution": False, "records": rows}
    result["catalogued"] = sum(row["state"] == "catalogued" for row in rows)
    lines = ["# Resultado de conversion local", "", "Estado: needs_review. No se aprobaron planeaciones ni se ejecutaron actividades.", "", f"Materias revisadas: {subject_count}. Conversiones: {result['converted']}. Sin convertir: {result['not_converted']}. Listas para ejecutar: 0.", "", "| Materia | Fuente | Estado |", "| --- | --- | --- |"]
    lines.extend(f"| {row['subject_key']} | {row['source']} | {row['state']} |" for row in rows)
    output.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output / "indice-planeaciones.json").write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "cola-cotejo.json").write_text(json.dumps({"kind": "planning-review-queue", "automatic_execution": False, "activities": queue}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result