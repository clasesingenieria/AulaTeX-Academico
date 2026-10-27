from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

from aulatex.node_planning import PEDAGOGICAL_SCHEMA_PATH, validate_schema
from aulatex.planning_conversion import _empty_activity, read_planning_source, render_editorial_markdown, render_pedagogical_markdown
from aulatex.planning_layout import _require_versionable, subject_artifact_contract
from aulatex.planning_validation import relocated_source, validate_pedagogical


BASE = Path("UnADM/licenciatura-en-derecho-unadm")
SUBJECTS = {
    "derecho-penal-especial-mexicano": "README.md",
    "teoria-del-estado-y-constitucion": "README.md",
    "antecedentes-de-los-derechos-humanos": "Readme - Antecedentes de los derechos humanos.md",
}
DATE = "2026-10-26"
SPECS = {
    "derecho-penal-especial-mexicano": [
        (1, None, 1, "213541", "Foro diagnostico", "forum", "pca-90292c893849da5ed1aa", None),
        (2, None, 2, "215277", "Cuadro comparativo del robo", "report", "pca-7fe86e758b6160e6122e", None),
        (3, None, 3, "216751", "Estudio de casos", "report", "pca-59835c6a72ea8aba5dfc", None),
        (4, None, 4, None, "Valoracion de decisiones", "report", "pca-4dd40f72de8af2db1526", None),
        (5, None, 5, None, "Simulacion de expediente juridico", "report", "pca-3057c47ded95b7ad2de1", None),
    ],
    "teoria-del-estado-y-constitucion": [
        (1, None, 1, None, "Foro diagnostico", "forum", None, None),
        (2, None, 2, None, "Linea de tiempo", "report", "pca-6991dd8903fb94036a65", ("I.- SEMANA 2", "II.- SEMANA 3")),
        (3, None, 3, None, "Analisis de hechos", "report", "pca-6991dd8903fb94036a65", ("II.- SEMANA 3", "Evidencia de la evaluaci")),
        (4, None, 4, None, "Foro", "forum", "pca-5dd1ab04716367c015d2", ("I.- SEMANA 4", "II.- SEMANA 5")),
    ],
    "antecedentes-de-los-derechos-humanos": [
        (1, None, 1, "210552", "Examen Diagnostico", "platform_response", None, None),
        (2, None, 1, "211991", "Foro diagnostico", "forum", None, None),
        (3, 1, 2, "211993", "Resena critica de video", "report", "pca-28e904bbd89dbe0247cf", ("Actividad 1:", "Actividad 2:")),
        (4, 2, 2, "211997", "Foro de participacion", "forum", "pca-28e904bbd89dbe0247cf", ("Actividad 2:", "Evidencia de la evaluaci")),
        (5, 3, 3, "211999", "Resumen de lectura", "report", "pca-9b9456e44b3d26f699ea", ("Actividad 3:", "Actividad 4.")),
        (6, 4, 3, "212000", "Foro de participacion y debate", "forum", "pca-9b9456e44b3d26f699ea", ("Actividad 4.", "Evidencia de la evaluaci")),
        (7, 5, 4, "212010", "Cuadro comparativo", "report", "pca-0562c6e0508cce181aa6", ("Actividad 5:", "Actividad 6:")),
        (8, 6, 4, "212011", "Examen Parcial I", "platform_response", "pca-0562c6e0508cce181aa6", ("Actividad 6:", "Evidencia de la evaluaci")),
    ],
}
ARCHIVED_TEXTS = {
    ("teoria-del-estado-y-constitucion", 1): "referencias-teoria-del-estado-y-constitucion/notas-teoria-del-estado-y-constitucion/actividad-01-foro-diagnostico/consignas/Foro-diagnostico-modulo-7.txt",
    ("antecedentes-de-los-derechos-humanos", 2): "referencias-antecedentes-de-los-derechos-humanos/notas-antecedentes-de-los-derechos-humanos/actividad-2-foro-diagnostico/modulo-6.txt",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def theory_history_directory(subject: Path) -> Path:
    archive = subject / "referencias-teoria-del-estado-y-constitucion/notas-teoria-del-estado-y-constitucion/materiales-generales/historico-planeaciones"
    return archive if (archive / "importaciones").is_dir() else subject / "planeaciones-teoria-del-estado-y-constitucion"


def latest_documents(subject: Path, slug: str) -> dict[str, tuple[Path, dict]]:
    documents = {}
    history = theory_history_directory(subject) if slug == "teoria-del-estado-y-constitucion" else subject / f"planeaciones-{slug}"
    for group in sorted((history / "importaciones").glob("pca-*")):
        paths = sorted(group.glob("r*/planeacion.json"))
        if paths:
            path = paths[-1]
            documents[group.name] = (path, json.loads(path.read_text(encoding="utf-8-sig")))
    return documents


def diagnose(root: Path) -> dict:
    rows = []
    for slug, entry in SUBJECTS.items():
        subject = root / BASE / f"{slug}-lde"
        if not (subject / entry).is_file():
            raise ValueError("missing_subject_entry")
        records = []
        for path, document in latest_documents(subject, slug).values():
            report = validate_pedagogical(document, subject)
            records.append({"path": path.relative_to(subject).as_posix(), "sha256": digest(path), "review": document["review"], "validation": report})
        rows.append({"subject": slug, "entry": entry, "entry_sha256": digest(subject / entry), "existing_reports": [path.name for path in sorted(subject.glob(f"reporte-{slug}-Actividad-*.tex"))], "records": records})
    return {"kind": "diagnostico-unadm-tres-materias", "documentary_date": DATE, "mode": "read_only", "editorial_cycles": 0, "platform_operations": [], "subjects": rows}


def segment(text: str, start: str, end: str) -> str:
    start_match = re.search(re.escape(start).replace(r"\ ", r"\s+"), text)
    if start_match is None:
        raise ValueError("activity_start_not_found")
    end_match = re.search(re.escape(end).replace(r"\ ", r"\s+"), text[start_match.end():])
    if end_match is None:
        raise ValueError("activity_end_not_found")
    return text[start_match.start():start_match.end() + end_match.start()]


def field_status(path: str, state: str, reason: str, source_id: str | None = None, text: str | None = None) -> dict:
    return {"path": path, "state": state, "reason": reason, "evidence": [{"source_id": source_id, "locator": "document", "quoted_text": text}] if source_id else [], "alternatives": []}


def build_model(subject: Path, slug: str, spec: tuple, documents: dict) -> dict:
    number, official, week, module, title, kind, source_key, boundaries = spec
    contract = subject_artifact_contract(subject)
    source_document = documents[source_key][1] if source_key else None
    preserved_segmentation = bool(source_document and not source_document["extensions"]["conversion"]["unsegmented_document"])
    if source_document:
        model = copy.deepcopy(source_document)
    else:
        model = {
            "schema_version": "1.0.0", "revision": 1,
            "identity": {"institution": "UnADM", "program": "Licenciatura en Derecho", "subject_id": f"{slug}-lde", "subject_title": slug, "offering_id": "oferta-documental-2026-2-B2", "period": "2026-2 B2", "modality": None},
            "sources": [], "curriculum": {"purpose": None, "competencies": [], "outcomes": [], "topics": []}, "activities": [], "field_status": [], "review": {}, "extensions": {},
        }
    entry = SUBJECTS[slug]
    entry_text = (subject / entry).read_text(encoding="utf-8-sig")
    model["sources"].append({"id": "src-control-actual", "kind": "other", "authority": "editorial", "title": entry, "url": None, "path": entry, "sha256": digest(subject / entry), "captured_at": DATE, "media_type": "text/markdown"})
    model["plan_id"] = "pca-interno-" + hashlib.sha256(f"{slug}/{number}".encode()).hexdigest()[:20]
    model["revision"] = 1
    model["artifact_contract"] = contract
    gaps = list(model.get("review", {}).get("critical_gaps", []))
    activity = model["activities"][0] if preserved_segmentation else _empty_activity(f"interna-{number}", title)
    activity["policies"].setdefault("exceptions", [])
    activity["weeks"] = [week]
    activity["bindings"] = {"extractor_directory": contract["paths_relative_to_subject"]["extractions"], "notes_directory": contract["paths_relative_to_subject"]["notes"], "research_directory": contract["paths_relative_to_subject"]["research"]}
    if not preserved_segmentation:
        model["field_status"] = []
        blocks = model.get("extensions", {}).get("conversion", {}).get("source_blocks", [])
        full_text = "\n\n".join(block["text"] for block in blocks)
        activity["instruction"] = segment(full_text, *boundaries) if boundaries else full_text or None
        archived = ARCHIVED_TEXTS.get((slug, number))
        instruction_source = "src-local"
        if archived:
            archived_path = subject / archived
            activity["instruction"] = archived_path.read_text(encoding="utf-8-sig")
            instruction_source = "src-consigna-archivada"
            model["sources"].append({"id": instruction_source, "kind": "other", "authority": "instructional", "title": archived_path.name, "url": None, "path": archived, "sha256": digest(archived_path), "captured_at": None, "media_type": "text/plain"})
        if activity["instruction"]:
            activity["requirements"] = [{"id": "req-consigna", "text": activity["instruction"]}]
            model["field_status"].append(field_status("/activities/0/instruction", "inferred", "Texto archivado preservado; verificar integridad, preguntas, tablas y limites antes de aprobar.", instruction_source, activity["instruction"]))
        gaps.append("Completar segmentacion fina de requisitos, preguntas, objetivos, temas, secuencia y alineacion con evidencia por campo.")
        gaps.append("Cotejar visualmente las filas y descriptores de la rubrica del producto; no trasladar puntuaciones de otra actividad.")
        model["field_status"].append(field_status("/activities/0", "unknown", "Modelo documental bloqueado: no inferir oficialidad ni integracion completa."))
    activity["role"] = "diagnostic" if week == 1 else "assessment" if kind == "platform_response" else "learning"
    if kind != "report":
        activity["products"] = [{"id": "producto-plataforma", "kind": kind, "recipient": None, "editable_format": None, "submission_format": None, "structure": [title], "length": None, "filename_pattern": None, "accessibility": None, "requirement_ids": [], "paths": {"editable": None, "delivery": None}}]
    elif not activity["products"]:
        activity["products"] = [{"id": "producto-documental", "kind": "report", "recipient": None, "editable_format": None, "submission_format": None, "structure": [title], "length": None, "filename_pattern": None, "accessibility": None, "requirement_ids": [], "paths": {"editable": None, "delivery": None}}]
    original_calendar = copy.deepcopy(activity["calendar"])
    for field in ("opens_at", "expected_at", "due_at", "closes_at", "timezone"):
        activity["calendar"][field] = None
    reason = "Sin programacion temporal acreditada al 26/10/2026: fechas pasadas, desconocidas o sin hora/zona verificable. Los literales originales no prueban prorroga, reapertura ni disponibilidad actual."
    calendar_status = next((item for item in model["field_status"] if item["path"] == "/activities/0/calendar"), None)
    if calendar_status:
        calendar_status.update(state="unknown", reason=reason)
    else:
        model["field_status"].append(field_status("/activities/0/calendar", "unknown", reason))
    if not activity["calendar"]["literal"]:
        activity["calendar"]["literal"] = None
    model["activities"] = [activity]
    if source_document:
        source_path, _source = documents[source_key]
        historical = {"path": source_path.relative_to(subject).as_posix(), "sha256": digest(source_path), "plan_id": source_document["plan_id"], "revision": source_document["revision"]}
    else:
        historical = None
    model["extensions"]["organizacion_interna"] = {
        "documentary_date": DATE, "internal_number": number, "official_number": official, "week": week,
        "task_module_id": module, "task_module_current_verified": False,
        "identity_evidence": {"source_id": "src-control-actual", "locator": "tabla vigente e identidad interior de reporte", "number_is_not_inferred_from_week": True},
        "previous_revision": historical, "original_calendar": original_calendar, "calendar_reason": reason,
        "historical_control": {"text": entry_text, "current_platform_status": None},
        "report_paths": {"tex": f"reporte-{slug}-Actividad-{number}.tex", "pdf": f"reporte-{slug}-Actividad-{number}.pdf", "internal_support_only": kind != "report"},
        "editorial_policy": {"template": "UnADM", "preserve_specific_format": True, "preserve_three_part_structure_when_applicable": True, "declare_ai_as_required_without_claiming_personal_review": True, "teaching_material_is_not_legal_authority": True},
        "temporal_state": "unprogrammed", "platform_operations": [], "editorial_cycle": "blocked",
        "integration_complete": False, "rubric_visual_verified": False,
    }
    if not preserved_segmentation and source_document:
        model["extensions"]["conversion"]["unsegmented_document"] = True
    if "conversion" in model["extensions"]:
        model["extensions"]["conversion"]["activity_mapping"] = [{"activity_id": activity["id"], "local_number": number, "official_number": official, "source_locator": "explicit_documentary_correspondence", "source_is_summary": not preserved_segmentation}]
    if slug == "derecho-penal-especial-mexicano":
        gaps.append("Verificar legislacion, reformas y jurisprudencia en fuentes oficiales antes del ciclo; no inventar hechos, competencia, pruebas ni diligencias realizadas.")
    if slug == "teoria-del-estado-y-constitucion":
        gaps.append("Cotejar hechos e influencia historica con fuentes primarias; separar linea de tiempo y analisis de hechos; conservar conflicto Word/LaTeX.")
    if slug == "antecedentes-de-los-derechos-humanos":
        gaps.append("Conservar ocho reportes, entregas y comprobantes existentes; no repetir publicaciones ni intentos. La excepcion de foros ITESCA no aplica.")
        if number == 2:
            activity["policies"]["exceptions"] = [{"scope": "foro-diagnostico-interno-2", "authority": "consigna-docente-archivada", "reason": "Una unica publicacion, conocimientos previos, sin investigar ni responder a pares. Excepcion exclusiva de esta consigna.", "evidence": [{"source_id": "src-consigna-archivada", "locator": "Indicaciones", "quoted_text": activity["instruction"]}]}]
        if number == 8:
            gaps.append("Parcial: PDF docente registra cuatro reactivos de opcion multiple y uno abierto; control historico de 23/10 registra verdadero/falso. No resolver por inferencia; no hay intento ni respuestas del parcial acreditados.")
            conflict = field_status("/activities/0/instruction", "conflict", gaps[-1], "src-local", activity["instruction"])
            conflict["alternatives"] = [
                {"value": "Cuatro reactivos de opcion multiple y uno de respuesta abierta.", "evidence": [{"source_id": "src-local", "locator": "page:9..11", "quoted_text": activity["instruction"]}]},
                {"value": "Cuatro reactivos de opcion multiple y uno verdadero/falso; registro historico del 23 de octubre.", "evidence": [{"source_id": "src-control-actual", "locator": "Consulta autenticada del 23 de octubre de 2026", "quoted_text": entry_text}]},
            ]
            model["field_status"] = [item for item in model["field_status"] if item["path"] != "/activities/0/instruction"] + [conflict]
    gaps.extend(["Revision academica/personal no acreditada; la organizacion no equivale a aprobacion.", "Completar recursos, politicas, rutas de producto y alineacion por consigna antes de admitir un unico ciclo."])
    model["review"] = {"state": "needs_review", "reviewed_at": DATE, "reviewer_role": "organizacion-documental-local-no-aprobacion-academica", "semantic_validation": "failed", "critical_gaps": list(dict.fromkeys(gaps))}
    validate_schema(model, PEDAGOGICAL_SCHEMA_PATH)
    return model


def preflight(root: Path) -> dict:
    records = []
    for slug in SUBJECTS:
        subject = root / BASE / f"{slug}-lde"
        documents = latest_documents(subject, slug)
        for spec in SPECS[slug]:
            model = build_model(subject, slug, spec, documents)
            report = validate_pedagogical(model, subject)
            records.append({"subject": slug, "internal_number": spec[0], "official_number": spec[1], "state": model["review"]["state"], "passed": report["passed"], "codes": sorted({item["code"] for item in report["findings"]})})
    return {"mode": "preflight_read_only", "records": records, "ready": 0, "editorial_cycles": 0}


def publish(root: Path) -> dict:
    diagnostic = diagnose(root)
    pending: dict[Path, bytes] = {}
    outcomes = []
    baseline = {}
    for slug, entry in SUBJECTS.items():
        subject = root / BASE / f"{slug}-lde"
        baseline.update({path: digest(path) for path in subject.rglob("*") if path.is_file()})
        folder = subject / f"planeaciones-{slug}"
        documents = latest_documents(subject, slug)
        catalog = {"kind": "catalogo-editorial-interno-unadm", "documentary_date": DATE, "source_of_truth": "JSON", "activities": [], "antecedents": [], "approved": [], "editorial_cycles": 0, "platform_operations": []}
        for spec in SPECS[slug]:
            number, official, week, module, title, kind, _source, _boundaries = spec
            model = build_model(subject, slug, spec, documents)
            report = validate_pedagogical(model, subject)
            name = f"planeacion-{slug}-Actividad-{number}"
            revision_folder = folder / "revisiones-organizacion" / "r0001"
            for destination in (folder, revision_folder):
                pending[destination / f"{name}.json"] = encoded(model)
                pending[destination / f"{name}.md"] = render_pedagogical_markdown(model).encode("utf-8")
            pending[revision_folder / f"cotejo-Actividad-{number}.json"] = encoded(report)
            catalog["activities"].append({"number": number, "official_number": official, "week": week, "module_id": module, "title": title, "product_kind": kind, "json": (folder / f"{name}.json").relative_to(subject).as_posix(), "md": (folder / f"{name}.md").relative_to(subject).as_posix(), "sha256": hashlib.sha256(encoded(model)).hexdigest(), "immutable_revision": (revision_folder / f"{name}.json").relative_to(subject).as_posix(), "review": "needs_review", "semantic_passed": report["passed"]})
        pending[folder / "catalogo-editorial.json"] = encoded(catalog)
        lines = ["# Planeaciones por reporte interno", "", "JSON es el modelo; Markdown es una vista derivada. Revision documental del 26 de octubre de 2026.", "", "Estado: needs_review. Cero actividades aprobadas, cero ciclos y cero operaciones de plataforma.", "", "| Interno | Oficial | Semana | Producto | Modelo | Vista |", "| --- | --- | --- | --- | --- | --- |"]
        for item in catalog["activities"]:
            lines.append(f"| {item['number']} | {item['official_number'] if item['official_number'] is not None else ''} | {item['week']} | {item['title']} | [JSON]({Path(item['json']).name}) | [Markdown]({Path(item['md']).name}) |")
        lines.extend(["", "Los reportes, notas y entregas no se renombran. Los numeros oficiales desconocidos no se deducen de la semana.", "", "Los originales y las importaciones anteriores conservan sus bytes y hashes. Las copias activas tienen una revision inmutable en revisiones-organizacion/r0001.", "", "Fechas operativas no acreditadas: null en JSON y en blanco en la vista. Las fechas documentales y los literales originales permanecen como evidencia.", "", "La consigna puede sustentarse con un documento docente archivado; Moodle no es obligatorio. Un recurso documental no es una tarea.", "", "Pendiente: segmentacion fina, rubricas y descriptores, recursos, alineacion, revision personal y cotejo primario. No se admite un ciclo por borrar fechas ni por una puntuacion automatica.", ""])
        pending[folder / "INDICE-PLANEACIONES-INTERNAS.md"] = "\n".join(lines).encode("utf-8")
        diagnostic_row = next(row for row in diagnostic["subjects"] if row["subject"] == slug)
        pending[folder / "revisiones-organizacion/r0001/diagnostico-inicial.json"] = encoded(diagnostic_row)
        outcomes.append({"subject": slug, "plans": len(catalog["activities"]), "revision": 1, "ready": 0})
    for path, content in pending.items():
        if path.exists() and path.read_bytes() != content:
            raise FileExistsError(f"immutable_output_conflict: {path.name}")
    for slug in SUBJECTS:
        subject = root / BASE / f"{slug}-lde"
        _require_versionable(subject, [path for path in pending if path.is_relative_to(subject)])
    created = []
    for path, content in pending.items():
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(content)
            created.append(path.relative_to(root).as_posix())
        if path.read_bytes() != content:
            raise OSError("generated_output_mismatch")
    if any(not path.is_file() or digest(path) != previous for path, previous in baseline.items()):
        raise OSError("existing_subject_file_changed")
    return {"subjects": outcomes, "created": created, "existing_files_preserved": len(baseline), "editorial_cycles": 0, "platform_operations": []}


def theory_editorial(root: Path, *, apply: bool = False) -> dict:
    slug = "teoria-del-estado-y-constitucion"
    subject = root / BASE / f"{slug}-lde"
    folder = subject / f"planeaciones-{slug}"
    notes = subject / f"referencias-{slug}/notas-{slug}"
    if (notes / "materiales-generales/historico-planeaciones/absorcion-control.json").is_file():
        return absorb_theory_control(root, apply=apply)
    activity_notes = {1: "actividad-01-foro-diagnostico", 2: "actividad-02-linea-de-tiempo", 3: "actividad-03-analisis-de-hechos", 4: "actividad-04-foro-estado"}
    for name in activity_notes.values():
        if not (notes / name).is_dir():
            raise ValueError("missing_activity_notes")
    archive = notes / "materiales-generales/originales-docentes/planificaciones-multisemana"
    revision = 4
    revision_folder = folder / f"revisiones-organizacion/r{revision:04d}"
    outputs: dict[Path, bytes] = {}
    moves = []
    filenames = [f"Planificacion-de-actividades-S2-S3-Teoria-del-Estado-y-Constitucion.{suffix}" for suffix in ("pdf", "txt")] + ["Planificacion-de-actividades-S4-S5-Teoria-del-Estado-y-Constitucion.pdf"]
    for filename in filenames:
        original, destination = folder / filename, archive / filename
        source = original if original.is_file() else destination
        if not source.is_file():
            raise ValueError("missing_original_planning_document")
        if original.is_file() and destination.exists():
            raise FileExistsError("original_destination_already_exists")
        moves.append({"from": original.relative_to(subject).as_posix(), "to": destination.relative_to(subject).as_posix(), "sha256": digest(source), "operation": "move_original"})
    control_snapshot = notes / "materiales-generales/registros-organizacion/revision-editorial-r0002/README-materia-anterior.md"
    control_source = control_snapshot if control_snapshot.is_file() else subject / "README.md"
    outputs[control_snapshot] = control_source.read_bytes()
    moves.append({"from": "README.md", "to": control_snapshot.relative_to(subject).as_posix(), "sha256": digest(control_source), "operation": "preserve_historical_control"})
    relocation = {"kind": "documentary-relocation", "documentary_date": "2026-10-27", "moves": moves, "historical_revisions_unchanged": True}
    registry_path = folder / "reubicaciones-documentales.json"
    if registry_path.is_file():
        existing_registry = json.loads(registry_path.read_text(encoding="utf-8-sig"))
        for existing_move in existing_registry.get("moves", []):
            if existing_move not in moves:
                moves.append(existing_move)
        if "registry_revision" in existing_registry:
            relocation["registry_revision"] = existing_registry["registry_revision"]
    outputs[folder / "reubicaciones-documentales.json"] = encoded(relocation)
    catalog_path = folder / "catalogo-editorial.json"
    catalog_snapshot = revision_folder / "catalogo-editorial-anterior.json"
    outputs[catalog_snapshot] = catalog_snapshot.read_bytes() if catalog_snapshot.is_file() else catalog_path.read_bytes()
    catalog = json.loads(outputs[catalog_snapshot].decode("utf-8-sig"))
    catalog["documentary_date"] = "2026-10-27"
    models = []
    rubric_rows = {
        1: [],
        2: [("Identifica principales hechos", 3, [0]), ("Incluye Antiguedad, Edad Media, Absolutismo, Revolucion francesa y Estado moderno", 2, [1]), ("Estructura y forma de la actividad", 2, [0, 4]), ("Opinion critica", 2, [2]), ("Cita en APA", 1, [3])],
        3: [("Identifica la Revolucion Francesa y la independencia de Mexico", 5, [1]), ("Relaciona las ideas de Rousseau y Montesquieu con los Sentimientos de la Nacion", 5, [2]), ("Estructura y forma de la actividad", 2, [0, 5]), ("Opinion critica", 2, [3]), ("Cita en APA", 1, [4])],
        4: [("Contestacion de cada pregunta propuesta", 3, [0, 1, 2]), ("Redaccion y opinion critica", 1, [0, 1, 2])],
    }
    requirements = {
        1: ["Responder las cinco preguntas del foro de presentacion y diagnostico.", "Consultar el objetivo y la introduccion a la asignatura; tiempo docente estimado: dos horas."],
        2: ["Colocar nombre completo, numero de actividad y titulo en el formato docente.", "Construir una linea de tiempo de la historia y origen del Estado con Antiguedad, Edad Media, Absolutismo, Revolucion francesa y Estado moderno.", "Emitir brevemente una opinion critica en cada etapa.", "Incluir bibliografia en APA 7.", "Guardar o imprimir como PDF con la nomenclatura docente; tiempo estimado: cuatro horas."],
        3: ["Colocar nombre completo, numero de actividad y titulo en el formato docente.", "Analizar la Revolucion Francesa y la independencia de Mexico.", "Relacionar las ideas de Rousseau y Montesquieu con los Sentimientos de la Nacion.", "Concluir criticamente sobre la influencia de pensadores europeos en la normativa mexicana.", "Incluir bibliografia en APA 7.", "Guardar o imprimir como PDF con la nomenclatura docente; tiempo estimado: cuatro horas."],
        4: ["Responder si el Estado establece un orden en la sociedad o es una representacion de ella.", "Explicar la aportacion principal de Maquiavelo, Hobbes, Locke, Rousseau y Montesquieu a la formacion del Estado.", "Argumentar cual de los enciclopedistas realizo una mayor aportacion a la formacion del Estado de Derecho.", "Ingresar al foro y responder las tres preguntas; tiempo docente estimado: dos horas."],
    }
    objectives = {1: "Diagnosticar y conocer al estudiante.", 2: "Identificar las causas y fines del Estado de acuerdo al contexto economico, politico, social e historico.", 3: "Comprender la influencia de la Revolucion Francesa para identificar los objetivos del Estado moderno, especificamente del entorno en Mexico.", 4: "Identificar la importancia del Estado y las principales concepciones del mismo."}
    themes = {1: ["Expectativas personales", "Derecho y fuentes formales", "Estado de Derecho"], 2: ["Historia y origen del Estado", "Formaciones politicas antiguas y medievales", "Absolutismo", "Revolucion francesa", "Estado moderno"], 3: ["Revolucion Francesa e independencia de Mexico", "Rousseau y Montesquieu", "Sentimientos de la Nacion"], 4: ["Estado y sociedad", "Maquiavelo, Hobbes, Locke, Rousseau y Montesquieu", "Estado de Derecho"]}
    for number in range(1, 5):
        name = f"planeacion-{slug}-Actividad-{number}"
        previous_path = folder / "revisiones-organizacion/r0001" / f"{name}.json"
        model = json.loads(previous_path.read_text(encoding="utf-8-sig"))
        activity = model["activities"][0]
        model["revision"] = revision
        model["identity"]["subject_title"] = "Teoria del Estado y Constitucion"
        model["identity"]["program"] = "Licenciatura en Derecho"
        predecessor = folder / "revisiones-organizacion/r0003" / f"{name}.json"
        model["extensions"]["organizacion_interna"]["previous_revision"] = {"path": predecessor.relative_to(subject).as_posix(), "sha256": digest(predecessor), "revision": 3}
        model["extensions"]["organizacion_interna"]["documentary_date"] = "2026-10-27"
        model["extensions"]["organizacion_interna"]["integration_complete"] = True
        model["extensions"]["organizacion_interna"]["rubric_visual_verified"] = False
        model["extensions"]["editorial_view"] = {"version": "2.0", "warnings": ["La secuencia y la alineacion son propuestas editoriales; no sustituyen la consigna docente.", "Las fechas operativas quedan sin programar. Los originales completos, las fechas documentales y el historial permanecen en el modelo JSON."]}
        for source in model["sources"]:
            movement = next((item for item in moves if item["from"] == source["path"] and item["sha256"] == source["sha256"]), None)
            if movement:
                source["path"] = movement["to"]
            if source["id"] == "src-local":
                source["authority"] = "instructional"

        def add_source(identifier: str, relative: str, authority: str = "editorial", kind: str = "other") -> str:
            path = subject / relative
            if not path.is_file():
                raise ValueError("missing_required_documentary_resource: " + relative)
            model["sources"].append({"id": identifier, "kind": kind, "authority": authority, "title": path.name, "url": None, "path": relative, "sha256": digest(path), "captured_at": None, "media_type": None})
            return identifier

        if number in (2, 3):
            txt_name = filenames[1]
            txt_source = folder / txt_name if (folder / txt_name).is_file() else archive / txt_name
            text = txt_source.read_text(encoding="utf-8-sig")
            start, end = ("I.- SEMANA 2", "II.- SEMANA 3") if number == 2 else ("II.- SEMANA 3", "Evidencia de la evaluaci")
            activity["instruction"] = segment(text, start, end)
            model["sources"].append({"id": "src-transcripcion", "kind": "other", "authority": "instructional", "title": txt_name, "url": None, "path": (archive / txt_name).relative_to(subject).as_posix(), "sha256": digest(txt_source), "captured_at": None, "media_type": "text/plain"})
            source_id = "src-transcripcion"
        elif number == 4:
            pdf_source = folder / filenames[2] if (folder / filenames[2]).is_file() else archive / filenames[2]
            import pymupdf
            with pymupdf.open(pdf_source) as pdf:
                page4 = pdf[3].get_text("text", clip=pymupdf.Rect(230, 0, pdf[3].rect.width, pdf[3].rect.height), sort=True)
                page5 = pdf[4].get_text("text", sort=True)
            activity["instruction"] = segment(page4 + "\n" + page5, "I.- SEMANA 4", "II.- SEMANA 5")
            source_id = "src-local"
        else:
            source_id = "src-consigna-archivada"
        model["extensions"]["literal_instruction_before_cleanup"] = activity["instruction"]
        activity["instruction"] = re.sub(r"P[áa]gina\s+\d+\s+de\s+\d+", "", activity["instruction"])
        if number == 4:
            activity["instruction"] = re.sub(r"(?m)^\s*Actividad:\s*Foro\.[^\n]*", "Actividad: Foro.", activity["instruction"])
        activity["instruction"] = "\n".join(line.strip() for line in activity["instruction"].splitlines()).strip()
        activity["requirements"] = [{"id": f"req-{index + 1}", "text": text} for index, text in enumerate(requirements[number])]
        requirement_ids = [item["id"] for item in activity["requirements"]]
        objective_id = f"objetivo-{number}"
        model["curriculum"]["outcomes"] = [{"id": objective_id, "text": objectives[number]}]
        model["curriculum"]["topics"] = [{"id": f"tema-{index + 1}", "text": text, "children": []} for index, text in enumerate(themes[number])]
        activity["outcome_ids"] = [objective_id]
        activity["topic_ids"] = [item["id"] for item in model["curriculum"]["topics"]]
        activity["questions"] = []
        if number in (1, 4):
            question_text = activity["instruction"].split("preguntas:", 1)[1].split("- Tiempo estimado", 1)[0]
            questions = re.split(r"(?:^|\n)\s*\d+\.\s*", question_text)[1:]
            if len(questions) != (5 if number == 1 else 3):
                raise ValueError("incorrect_theory_question_count")
            activity["questions"] = [{"id": f"pregunta-{index + 1}", "context": None, "text": " ".join(text.split()), "requirement_ids": [requirement_ids[index if number == 4 else 0]]} for index, text in enumerate(questions)]
        actions = ["Leer la consigna y comprobar el producto y sus restricciones.", "Consultar los recursos pertinentes y organizar notas con localizadores.", "Preparar el producto solicitado sin modificar hechos ni atribuir experiencias no aportadas.", "Cotejar requisitos, fuentes, rubrica y declaracion de IA; solicitar revision personal."]
        activity["sequence"] = [{"id": f"paso-{index + 1}", "order": index + 1, "phase": "preparation" if index < 2 else "construction" if index == 2 else "review", "action": action, "inputs": [], "output": "Producto o nota local verificable", "completion_check": "Cotejar con los requisitos; no publicar ni enviar desde esta secuencia.", "requirement_ids": requirement_ids, "depends_on": [] if index == 0 else [f"paso-{index}"]} for index, action in enumerate(actions)]
        activity["assessment"].update(kind="diagnostic" if number == 1 else "formative" if number == 4 else "summative", scale_total={1: None, 2: 10, 3: 15, 4: 4}[number], weight={1: None, 2: 10, 3: 15, 4: 4}[number], weight_unit=None if number == 1 else "percent")
        activity["assessment"]["criteria"] = [{"id": f"criterio-{index + 1}", "text": text, "points": points, "descriptors": [], "requirement_ids": [requirement_ids[position] for position in positions]} for index, (text, points, positions) in enumerate(rubric_rows[number])]
        activity["assessment"]["editorial_checks"] = ["Preservar el producto docente y los hechos documentados.", "Distinguir fecha documental de programacion operativa.", "No duplicar entregas o publicaciones confirmadas.", "Revisar personalmente contenido y fuentes antes de aprobar."]
        product = activity["products"][0]
        product["kind"] = "timeline" if number == 2 else "report" if number == 3 else "forum"
        product["structure"] = ["Identificacion", "Linea de tiempo y opinion por etapa", "Bibliografia APA 7"] if number == 2 else ["Identificacion", "Analisis de hechos", "Opinion critica", "Bibliografia APA 7"] if number == 3 else ["Respuestas a cinco preguntas diagnosticas" if number == 1 else "Respuestas argumentadas a las tres preguntas"]
        product["requirement_ids"] = requirement_ids
        product["editable_format"] = "Word (observacion docente de rubrica); LaTeX por instruccion editorial, diferencia no resuelta" if number in (2, 3) else "Texto en plataforma"
        product["submission_format"] = "PDF" if number in (2, 3) else None
        product["filename_pattern"] = f"2026_TeoriaEstado_S{number}_<Nombre y apellidos>.pdf" if number in (2, 3) else None
        product["length"] = None
        product["paths"]["editable"] = f"reporte-{slug}-Actividad-{number}.tex" if number in (2, 3) else "foro-participacion-Actividad-4.txt" if number == 4 else None
        product["paths"]["delivery"] = None
        activity["bindings"]["notes_directory"] = (notes / activity_notes[number]).relative_to(subject).as_posix()
        activity["policies"].update(integrity="No inventar datos personales, opiniones, hechos ni fuentes; revision personal pendiente.", privacy="Conservar solo la evidencia necesaria; no registrar credenciales ni sesiones.")
        if number != 1:
            activity["policies"].update(ai="Declarar el uso de IA conforme a los lineamientos docentes. No estimar porcentajes ni afirmar revision personal no acreditada.", citation="APA 7", attempts=1 if number in (2, 3) else None, late_submission="Tabla docente: 1 a 3 dias habiles, 1 punto menos; 3 a 09 dias habiles, 2 puntos menos; mas de 09 dias habiles, 3 puntos menos. Limites solapados preservados; recepcion historica hasta 02 de diciembre, sin permiso actual acreditado.")
        activity["alignment"] = [{"outcome_id": objective_id, "requirement_ids": requirement_ids, "step_ids": [item["id"] for item in activity["sequence"]], "product_ids": [product["id"]], "criterion_ids": [item["id"] for item in activity["assessment"]["criteria"]]}]
        model["field_status"] = [field_status("/activities/0", "confirmed", "Consigna docente archivada, cotejo documental; no aprobacion academica.", source_id, activity["instruction"]), field_status("/curriculum/outcomes", "confirmed", "Proposito docente preservado.", source_id, objectives[number]), field_status("/curriculum/topics", "inferred", "Desglose editorial de los temas expresos, no nuevo programa.", source_id, activity["instruction"]), field_status("/activities/0/sequence", "inferred", "Secuencia editorial propuesta; no acciones realizadas."), field_status("/activities/0/alignment", "inferred", "Alineacion editorial de requisitos y criterios, no aprobacion docente."), field_status("/activities/0/calendar", "unknown", "Plazos pasados o sin vigencia operativa acreditada. Valores originales preservados."), field_status("/activities/0/products/0/editable_format", "inferred", "Formato docente distinguido de la preferencia editorial; no afirmar retiro de Word.")]
        warnings = ["Cotejar fuentes primarias y revision personal antes de aprobar; no se certifica vigencia juridica por el material docente."]
        if number in (2, 3):
            warnings.append("Conflicto Word/LaTeX pendiente de confirmacion; conservar ambos criterios.")
        if number == 4:
            warnings.append("El PDF S4/S5 conserva etiquetas S2/S3 y una sesion con ano 2025; no se corrigen los originales ni se usan esas fechas como programacion.")
        model["review"] = {"state": "needs_review", "reviewed_at": "2026-10-27", "reviewer_role": "cotejo-documental-y-vista-editorial", "critical_gaps": warnings, "semantic_validation": "failed"}
        if number in (2, 4):
            evidence_path = (notes / activity_notes[number] / ("comprobantes-envio/2026-10-11/recibo.json" if number == 2 else "comprobantes-publicacion/participacion-S4-2026-10-23.json"))
            evidence = json.loads(evidence_path.read_text(encoding="utf-8-sig"))
            add_source("src-comprobante-historico", evidence_path.relative_to(subject).as_posix())
            model["extensions"]["delivery_history"] = {"evidence": evidence, "repeat_prohibited": True, "current_platform_status_verified": False}
            model["extensions"]["editorial_view"]["warnings"].append("Existe comprobante historico de entrega o publicacion principal. No repetirla; no se acredita una calificacion actual.")
            if number == 2:
                model["extensions"]["organizacion_interna"]["task_module_id"] = str(evidence["modulo"])
                delivery = subject / f"entregas-{slug}" / evidence["archivo"]
                if delivery.is_file() and digest(delivery) == evidence["sha256_local"]:
                    product["paths"]["delivery"] = delivery.relative_to(subject).as_posix()
            else:
                model["extensions"]["organizacion_interna"]["task_module_id"] = str(evidence["forum_module"])
        bibliography = f"{slug}.bib"
        add_source("src-bibliografia-local", bibliography, "editorial")
        if number in (2, 3):
            formats = list((notes / "materiales-generales/auditorias/semana2-2026-10-11").glob("214812-*.docx"))
            if len(formats) != 1:
                raise ValueError("teacher_format_not_uniquely_archived")
            add_source("src-formato-docente", formats[0].relative_to(subject).as_posix(), "instructional", "docx")
            _imported, format_blocks = read_planning_source(formats[0])
            model["extensions"]["teacher_format"] = {"blocks": format_blocks, "word_latex_difference_unresolved": True}
        library = subject / f"referencias-{slug}/libros-{slug}"
        for index, filename in enumerate(("Teoria general del Estado (2a edicion) - Eduardo Andrade Sanchez.pdf", "Estado de derecho y principio de legalidad (2011) - Diego Garcia Ricci.pdf"), 1):
            add_source(f"src-libro-{index}", (library / filename).relative_to(subject).as_posix(), "scholarly", "pdf")
        if number in (3, 4):
            for index, filename in enumerate(("El contrato social - Juan Jacobo Rousseau.pdf", "Del espiritu de las leyes - Montesquieu.pdf"), 3):
                add_source(f"src-libro-{index}", (library / filename).relative_to(subject).as_posix(), "scholarly", "pdf")
        if number == 3:
            add_source("src-sentimientos-primario", f"referencias-{slug}/documentos-historicos-y-normas/INEHRM-Los-Sentimientos-de-la-Nacion-de-Jose-Maria-Morelos.pdf", "scholarly", "pdf")
        model["extensions"]["formal_integration"] = {"core_blocks_present": True, "instruction_and_original_document_preserved": True, "rubric_descriptors_not_invented": True, "documentary_limits": {"length": "No existe un limite de paginas acreditado para estos productos.", "rubric_descriptors": "La tabla docente S2/S3/S4 fija criterios y puntos, no niveles adicionales de desempeno.", "diagnostic_rubric": "La consigna S1 no fija una rubrica numerica; no se inventa.", "platform_access": "No consultado durante esta revision.", "personal_review": "Pendiente; la integracion documental no equivale a aprobacion."}}
        for field, reason in (("cognitive", "No se acredita una taxonomia docente; no deducir nivel a partir de verbos."), ("products/0/length", "Extension no fijada en las fuentes conservadas.")):
            model["field_status"].append(field_status("/activities/0/" + field, "unknown", reason))
        activity["resources"] = [{"id": f"recurso-{index + 1}", "source_id": source["id"], "purpose": "Cotejo de instrucciones y trazabilidad documental" if source["authority"] == "instructional" else "Control editorial o evidencia historica; no autoridad sustantiva", "required": source["authority"] == "instructional", "access": "local", "rights": "Conservacion local; no redistribucion automatica"} for index, source in enumerate(model["sources"])]
        for resource in activity["resources"]:
            source = next(item for item in model["sources"] if item["id"] == resource["source_id"])
            if source["authority"] == "scholarly":
                resource["purpose"] = "Investigacion documental: cotejar contenido, localizadores y alcance antes de citar; disponibilidad no acredita lectura ni vigencia."
        if "conversion" in model["extensions"]:
            model["extensions"]["conversion"]["unsegmented_document"] = False
        validate_schema(model, PEDAGOGICAL_SCHEMA_PATH)
        models.append(model)
        outputs[revision_folder / f"{name}.json"] = encoded(model)
        outputs[revision_folder / f"{name}.md"] = render_editorial_markdown(model, "../../../").encode("utf-8")
        outputs[folder / f"{name}.json"] = encoded(model)
        outputs[folder / f"{name}.md"] = render_editorial_markdown(model).encode("utf-8")
        row = next(item for item in catalog["activities"] if item["number"] == number)
        row.update(sha256=hashlib.sha256(encoded(model)).hexdigest(), immutable_revision=(revision_folder / f"{name}.json").relative_to(subject).as_posix(), module_id=model["extensions"]["organizacion_interna"]["task_module_id"], revision=revision, semantic_passed=False)
    outputs[catalog_path] = encoded(catalog)
    immutable = [path for path in outputs if path.is_relative_to(revision_folder) or path == control_snapshot or path.name == "reubicaciones-documentales.json"]
    for path in immutable:
        if path.exists() and path.read_bytes() != outputs[path]:
            raise FileExistsError("editorial_revision_conflict: " + path.name)
    result = {"subject": slug, "mode": "publish" if apply else "preflight_read_only", "moves": moves[:3], "notes_verified": list(activity_notes.values()), "models": len(models), "revision": revision, "ready": 0}
    if not apply:
        return result
    _require_versionable(subject, list(outputs) + [archive / filename for filename in filenames])
    for path in immutable:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(outputs[path])
    for movement in moves[:3]:
        original, destination = subject / movement["from"], subject / movement["to"]
        if original.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            original.rename(destination)
        if digest(destination) != movement["sha256"]:
            raise OSError("moved_original_hash_mismatch")
    for model in models:
        report = validate_pedagogical(model, subject)
        codes = {item["code"] for item in report["findings"]}
        if codes.intersection({"missing_source", "source_hash_changed", "unsafe_source_path", "unresolved_pointer", "unresolved_reference", "unresolved_evidence_source", "rubric_total_mismatch", "incomplete_alignment"}):
            raise ValueError("editorial_integrity_validation_failed: " + str(sorted(codes)))
        number = model["extensions"]["organizacion_interna"]["internal_number"]
        report_path = revision_folder / f"cotejo-Actividad-{number}.json"
        if report_path.exists() and report_path.read_bytes() != encoded(report):
            raise FileExistsError("editorial_review_conflict")
        if not report_path.exists():
            with report_path.open("xb") as stream:
                stream.write(encoded(report))
    for path, content in outputs.items():
        if path not in immutable:
            path.write_bytes(content)
    result["sources_verified"] = True
    return result


def preserve_theory_historical_source(root: Path) -> dict:
    slug = "teoria-del-estado-y-constitucion"
    subject = root / BASE / f"{slug}-lde"
    folder = subject / f"planeaciones-{slug}"
    imported = theory_history_directory(subject) / "importaciones/pca-e00ed29090307df7d020/r0001/planeacion.json"
    document = json.loads(imported.read_text(encoding="utf-8-sig"))
    source = document["sources"][0]
    text = document["extensions"]["conversion"]["source_blocks"][0]["text"]
    candidates = [text.encode("utf-8"), text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")]
    candidates += [b"\xef\xbb\xbf" + candidate for candidate in candidates]
    content = next((candidate for candidate in candidates if hashlib.sha256(candidate).hexdigest() == source["sha256"]), None)
    if content is None:
        raise ValueError("historical_source_cannot_be_reconstructed_exactly")
    archive = subject / f"referencias-{slug}/notas-{slug}/materiales-generales/registros-organizacion/revision-editorial-r0002"
    retained = archive / "planeacion-S2-anterior-a-reubicacion.md"
    if retained.exists() and retained.read_bytes() != content:
        raise FileExistsError("historical_snapshot_conflict")
    registry = folder / "reubicaciones-documentales.json"
    payload = json.loads(registry.read_text(encoding="utf-8-sig"))
    movement = {"from": source["path"], "to": retained.relative_to(subject).as_posix(), "sha256": source["sha256"], "operation": "preserve_historical_source"}
    if movement not in payload["moves"]:
        previous = archive / "reubicaciones-documentales-anterior-a-ficha-S2.json"
        if not previous.exists():
            with previous.open("xb") as stream:
                stream.write(registry.read_bytes())
        payload["moves"].append(movement)
        payload["registry_revision"] = 2
    if not retained.exists():
        with retained.open("xb") as stream:
            stream.write(content)
    registry.write_bytes(encoded(payload))
    if relocated_source(subject, source["path"], source["sha256"]) != retained:
        raise ValueError("retained_source_not_resolved")
    return {"historical_source_preserved": movement, "hash_verified": True}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--theory-editorial", action="store_true")
    parser.add_argument("--preserve-theory-history", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    result = preserve_theory_historical_source(root) if args.preserve_theory_history else theory_editorial(root, apply=args.publish) if args.theory_editorial else publish(root) if args.publish else preflight(root) if args.check else diagnose(root)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()