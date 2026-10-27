from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path


SUBJECT = Path(__file__).resolve().parents[1]
REPOSITORY = SUBJECT.parents[2]
sys.path.insert(0, str(REPOSITORY / "aulaTEX"))

from aulatex.planning_layout import catalogued_plan_paths, subject_layout
from aulatex.planning_validation import validate_pedagogical


PLANS = subject_layout(SUBJECT)["plans"]
CATALOG = PLANS / "catalogo-editorial.json"
SLUG = "estadistica-aplicada-para-la-administracion"
OMISSION = "OMISI\u00d3N \u2014 SIN ACCI\u00d3N A REALIZAR"
BLOCKS = {
    "identidad_correspondencias", "consigna", "objetivos_temas", "requisitos_preguntas",
    "secuencia", "recursos", "productos", "evaluacion_rubrica", "politicas", "calendario",
    "alineacion", "rutas", "evidencias_revision",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode(document: dict) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def local_path(relative: str) -> Path:
    path = (SUBJECT / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(SUBJECT):
        raise ValueError("unsafe_subject_path")
    return path


def markdown_sections(document: dict) -> dict:
    activity = document["activities"][0]
    editorial = document["extensions"]["editorial"]
    return {
        "Identidad y correspondencias": {"identity": document["identity"], "number": editorial["number"], "module_id": editorial["module_id"]},
        "Objetivos y temas": document["curriculum"],
        "Requisitos y preguntas": {"requirements": activity["requirements"], "questions": activity["questions"]},
        "Secuencia editorial": activity["sequence"], "Recursos": activity["resources"],
        "Productos": activity["products"], "Evaluacion y rubrica": activity["assessment"],
        "Politicas": activity["policies"], "Alineacion editorial": activity["alignment"],
        "Rutas": {"bindings": activity["bindings"], "report": editorial["report"], "delivery": editorial["delivery"]},
        "Evidencias y revision": {"sources": document["sources"], "field_status": document["field_status"], "review": document["review"]},
        "Calendario historico: no operativo": editorial["historical_calendar"],
    }


def render_absorbed(document: dict) -> str:
    activity = document["activities"][0]
    editorial = document["extensions"]["editorial"]
    identity = document["identity"]
    lines = [f"# Actividad {editorial['number']} · {activity['title']}", "", identity["subject_title"], "",
             f"> **Pendiente de revision academica.** Revision editorial {document['revision']}. Sin autorizacion de ejecucion ni envio."]

    def section(title: str) -> None:
        lines.extend(["", "## " + title, ""])

    def cell(value) -> str:
        if value is None or value == []:
            return "No documentado"
        if isinstance(value, bool):
            return "Si" if value else "No"
        if isinstance(value, list):
            return "; ".join(cell(item) for item in value)
        return " ".join(str(value).split()).replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")

    def table(headers: list[str], rows: list) -> None:
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join("---" for _header in headers) + " |")
        lines.extend("| " + " | ".join(cell(value) for value in row) + " |" for row in rows)

    def items(values: list, empty: str = "Pendiente de documentar y cotejar.") -> None:
        if not values:
            lines.append(empty)
        for number, value in enumerate(values, 1):
            text = value.get("text", "") if isinstance(value, dict) else value
            lines.append(f"{number}. {cell(text)}")

    section("1. Identidad y correspondencia")
    table(["Dato", "Valor"], [["Institucion", identity["institution"]], ["Programa", identity["program"]],
          ["Actividad", editorial["number"]], ["Modulo de origen", editorial["module_id"]], ["Periodo", identity["period"]], ["Modalidad", identity["modality"]]])
    if editorial["already_completed_evidence"]:
        lines.extend(["", "**Existe evidencia de realizacion. No repetir la actividad ni su envio.**"])
    section("2. Consigna docente")
    lines.extend(["La transcripcion conserva el texto de la fuente; no resuelve sus contradicciones ni acredita el estado actual de la plataforma.", "",
                  "<details>", "<summary>Consultar consigna y captura literal completas</summary>", "", activity["instruction"], "", "</details>"])
    section("3. Objetivos y temas")
    lines.extend([document["curriculum"]["purpose"] or "Objetivo pendiente de cotejo con la fuente docente.", "", "### Resultados de aprendizaje", ""])
    items(document["curriculum"]["outcomes"])
    lines.extend(["", "### Temas", ""])
    items(document["curriculum"]["topics"])
    section("4. Requisitos y preguntas")
    items(activity["requirements"])
    lines.extend(["", "### Preguntas documentadas", ""])
    items(activity["questions"], "No hay preguntas segmentadas en el modelo. Consultar la consigna; no asumir su inexistencia.")
    section("5. Secuencia editorial propuesta")
    lines.extend(["Organizacion de trabajo propuesta; no sustituye instrucciones docentes ni habilita la ejecucion.", ""])
    if activity["sequence"]:
        phases = {"preparation": "Preparacion", "production": "Desarrollo", "closure": "Cierre", "review": "Revision"}
        for step in activity["sequence"]:
            lines.extend([f"### Paso {step['order']}. {phases.get(step['phase'], step['phase'])}", "", step["action"], ""])
            table(["Componente", "Detalle"], [["Insumos", step["inputs"]], ["Resultado", step["output"]], ["Comprobacion", step["completion_check"]]])
    else:
        lines.append("Secuencia pendiente de integracion.")
    section("6. Recursos")
    if activity["resources"]:
        table(["Recurso", "Fuente", "Obligatorio", "Acceso"], [[item.get("title", item["id"]), item["source_id"], item["required"], item["access"]] for item in activity["resources"]])
    else:
        lines.append("Recursos pendientes de segmentacion o verificacion. Las fuentes documentales se identifican al final.")
    section("7. Productos y reportes")
    for product in activity["products"]:
        lines.extend(["### " + product["id"], ""])
        table(["Caracteristica", "Requisito documentado"], [["Destinatario", product["recipient"]], ["Formato", product["submission_format"]],
              ["Formato editable", product["editable_format"]], ["Estructura", product["structure"]], ["Extension", product["length"]], ["Nombre de entrega", product["filename_pattern"]]])
        lines.append("")
    if not activity["products"]:
        lines.append("Producto pendiente de definicion y alineacion. El reporte existente no sustituye esta comprobacion.")
    lines.extend(["", "**Reporte institucional:** Introduccion, desarrollo tematico y conclusiones. Se conserva la plantilla y los archivos establecidos."])
    if editorial["delivery"]["generate_pdf_by_default"] is False:
        lines.extend(["", "**Cuestionario:** conserva reporte documental, pero no genera PDF de entrega por defecto."])
    section("8. Evaluacion y rubrica")
    assessment = activity["assessment"]
    table(["Dato", "Valor documentado"], [["Ponderacion", str(assessment["weight"]) + "%" if assessment["weight_unit"] == "percent" else assessment["weight"]], ["Escala total oficial", assessment["scale_total"]]])
    if not assessment["criteria"]:
        lines.extend(["", "Rubrica pendiente de segmentacion y cotejo. Consultar la captura docente sin inferir criterios ni puntajes."])
    for criterion in assessment["criteria"]:
        lines.extend(["", "### " + criterion["text"], "", f"Puntaje registrado del criterio: {cell(criterion['points'])}.", ""])
        table(["Nivel", "Descriptor literal", "Puntos"], [[item["level"], item["description"], item["points"]] for item in criterion["descriptors"]])
    lines.extend(["", "Los puntajes y descriptores transcritos no acreditan una calificacion oficial. No se corrigen inconsistencias por inferencia."])
    section("9. Politicas")
    labels = {"ai": "Uso de IA", "integrity": "Integridad academica", "collaboration": "Colaboracion", "citation": "Citacion", "attempts": "Intentos", "late_submission": "Entrega tardia", "accessibility": "Accesibilidad", "privacy": "Privacidad", "exceptions": "Excepciones"}
    table(["Politica", "Texto documentado"], [[labels.get(key, key), value] for key, value in activity["policies"].items()])
    section("10. Calendario operativo")
    lines.extend(["| Apertura | Prevista | Limite | Cierre | Zona horaria |", "| --- | --- | --- | --- | --- |", "|  |  |  |  |  |", "",
                  "Sin programacion verificada. Moodle es opcional como integracion. Una fecha vacia no acredita apertura ni autoriza envios."])
    section("11. Alineacion editorial")
    if activity["alignment"]:
        table(["Resultado", "Requisitos", "Pasos", "Productos", "Criterios"], [[item["outcome_id"], item["requirement_ids"], item["step_ids"], item["product_ids"], item["criterion_ids"]] for item in activity["alignment"]])
    else:
        lines.append("Alineacion pendiente. No hay una relacion validada entre objetivos, requisitos, productos y evaluacion.")
    section("12. Archivos de trabajo")
    routes = {"Notas": activity["bindings"]["notes_directory"], "Extraccion": activity["bindings"]["extractor_directory"], "Investigacion": activity["bindings"]["research_directory"],
              "Reporte TEX": editorial["report"]["tex"], "Reporte PDF": editorial["report"]["pdf"], "Entrega existente": editorial["delivery"]["existing_path"]}
    for label, relative in routes.items():
        lines.append(f"- **{label}:** [{relative}](../{relative.replace(' ', '%20')})" if relative else f"- **{label}:** sin archivo asociado.")
    section("13. Evidencias y revision")
    lines.extend(["### Bloqueos pendientes", ""])
    items(document["review"]["critical_gaps"])
    for status in document["field_status"]:
        if status["state"] == "conflict":
            lines.extend(["", "**Conflicto documentado:** " + status["reason"], ""])
            items([item["value"] for item in status["alternatives"]])
    lines.extend(["", "### Fuentes", ""])
    authorities = {"editorial": "Editorial", "instructional": "Docente", "scholarly": "Academica", "support": "Apoyo", "unknown": "Sin confirmar"}
    for source in document["sources"]:
        lines.append(f"- **{source['title']}**. Autoridad: {authorities[source['authority']]}. Captura: {cell(source['captured_at'])}. " +
                     (f"[Consultar fuente](../{source['path'].replace(' ', '%20')})." if source["path"] else "Contenido integro absorbido en el modelo; sin archivo suelto."))
    lines.extend(["", "### Captura historica: no operativa", "", "Los estados, plazos y mensajes siguientes son evidencia de una captura pasada, no datos vigentes.", "",
                  "<details>", "<summary>Consultar literal historico</summary>", "", editorial["historical_calendar"]["literal"] or "Sin literal documentado.", "", "</details>", "",
                  "### Integridad documental", "", "Los dos documentos originales se absorbieron completos y se verificaron por SHA-256 antes de eliminar los archivos sueltos. Esta integracion no constituye aprobacion academica."])
    integrated = document.get("extensions", {}).get("integrated_documents")
    if integrated:
        lines.extend(["", "### Contenido de importaciones integrado", "",
                      f"Se absorbieron {len(integrated['reviews'])} revisiones y {len(integrated['files'])} archivos, conservados como {len(integrated['objects'])} documentos distintos dentro del modelo. No se requieren carpetas auxiliares ni archivos de revision separados.", "",
                      "Las observaciones anteriores se conservan como evidencia de conversion; no sustituyen el dictamen actual ni agregan requisitos docentes.", ""])
        table(["Revision de origen", "Estado registrado", "Hallazgos de conversion"],
              [[item["revision"], "Pendiente de revision" if item["state"] == "needs_review" else item["state"], len(item["findings"])] for item in integrated["reviews"]])
        gaps = list(dict.fromkeys(gap for item in integrated["reviews"] for gap in item["critical_gaps"]))
        lines.extend(["", "**Observaciones documentales previas:**", ""])
        items(gaps, "No hay observaciones adicionales registradas.")
    return "\n".join(lines) + "\n"


def render_antecedent(document: dict) -> str:
    return (f"# {document['title']}\n\n**{OMISSION}**\n\n"
            "Sin numero de Actividad. No genera tareas, reportes ni entregables; no participa en campañas, extractores o monitores.\n\n"
            f"## Identificacion\n\n- Modulo de origen: {document['module_id']}.\n- Uso: antecedente documental exclusivamente.\n\n"
            "## Contenido integrado\n\nLos originales JSON y Markdown estan absorbidos integramente en el modelo, con sus hashes verificados; se eliminaron los archivos sueltos sin crear respaldos.\n\n"
            "## Alcance de la omision\n\nSolo los tres foros iniciales de Estadistica. No aplica a otros foros evaluables.\n")


def absorbed_bytes(catalog: dict, relative: str) -> bytes | None:
    integrated = catalog.get("consolidation", {}).get("files", {}).get(relative)
    if integrated is not None:
        document = catalog if integrated["target"] == CATALOG.relative_to(SUBJECT).as_posix() else load(local_path(integrated["target"]))
        return document["extensions"]["integrated_documents"]["objects"][integrated["sha256"]]["text"].encode("utf-8")
    record = catalog.get("absorption", {}).get("files", {}).get(relative)
    if record is None:
        return None
    document = load(local_path(record["absorbed_into"]))
    if "antecedent_id" in record:
        document = next(item["document"] for item in document["antecedents"] if item["module_id"] == record["antecedent_id"])
    embedded = document["extensions"]["embedded_sources"][record["source_id"]]
    return embedded["text"].encode(embedded["encoding"])


def render_catalog(catalog: dict) -> str:
    lines = ["# Planeaciones de Estadistica", "", "22 actividades con correspondencia documental. El JSON conserva el modelo completo y el Markdown su vista de lectura.", "",
             "> **Sin habilitacion automatica.** La limpieza documental no aprueba actividades, no programa fechas y no autoriza envios.", "",
             "## Actividades", "", "| Actividad | Modulo | Planeacion | Revision | Estado |", "| --- | --- | --- | --- | --- |"]
    for entry in catalog["activities"]:
        lines.append(f"| {entry['number']} | {entry['module_id']} | [Consultar]({Path(entry['markdown']).name}) | {entry['revision']} | Pendiente de revision |")
    lines.extend(["", "Actividades 1 a 5: existe evidencia de realizacion; no repetir. Cuestionarios 3, 6, 9, 12 y 19: reporte documental, sin PDF de entrega por defecto.", "",
                  "## Foros iniciales omitidos", "", "No son actividades numeradas. No generan tareas, reportes ni entregables y no participan en campañas, extractores ni monitores."])
    for entry in catalog["antecedents"]:
        document = entry["document"]
        lines.extend(["", f"<a id=\"foro-{entry['module_id']}\"></a>", f"### {document['title']}", "", f"**{OMISSION}**", "", f"Modulo de origen: {entry['module_id']}."])
        original = json.loads(document["extensions"]["embedded_sources"]["src-local"]["text"].lstrip("\ufeff"))
        instructions = original.get("activity", {}).get("requirements")
        if isinstance(instructions, str) and instructions.strip():
            lines.extend(["", "<details>", "<summary>Contenido documental anterior, sin accion obligatoria</summary>", "", instructions, "", "</details>"])
    consolidation = catalog["consolidation"]
    lines.extend(["", "Esta omision solo corresponde a los tres foros iniciales de Estadistica, no a otros foros evaluables.", "",
                  "## Integracion documental", "", f"Se integraron {len(consolidation['files'])} archivos de importaciones y antecedentes, incluyendo {consolidation['revisions']} revisiones. No se conservan esas carpetas ni se crean respaldos nuevos.", "",
                  "Los documentos identicos se almacenan una sola vez dentro de cada modelo. Se conservan sus contenidos completos, hashes y correspondencias; las capturas y revisiones previas no se tratan como requisitos nuevos ni como aprobaciones.", "",
                  "## Bloqueos academicos", "", "La Actividad 7 conserva conflicto de extension (3 paginas frente a 3 cuartillas sin portada ni fuentes), escala oficial no verificada y comprobacion pendiente de portada/producto. Las otras 21 actividades mantienen integracion academica pendiente.", "",
                  "## Calendario y acceso", "", "Fechas operativas sin programar. Una fecha vacia no acredita apertura ni autoriza envios. Moodle es una integracion opcional.", "",
                  "## Validacion y vistas", "", "El auditor local comprueba modelos, fuentes integradas, enlaces y vistas. La opcion `--render-views` regenera Markdown desde JSON; no ejecuta actividades. `--consolidate-folders` absorbe las dos carpetas y verifica su integridad antes de eliminarlas.", "",
                  "Los dictamenes anteriores son capturas de su fecha y no describen el inventario actual.", ""])
    return "\n".join(lines)


def prepare_folder_cleanup() -> tuple[dict, dict[Path, bytes], dict[Path, bytes]]:
    catalog = copy.deepcopy(load(CATALOG))
    if "consolidation" in catalog:
        raise ValueError("folders_already_consolidated")
    directories = [PLANS / "importaciones", PLANS / "antecedentes"]
    originals = {path: path.read_bytes() for directory in directories for path in directory.rglob("*") if path.is_file()}
    if not originals or any(path.is_symlink() or not path.resolve().is_relative_to(PLANS.resolve()) for path in originals):
        raise ValueError("invalid_cleanup_inventory")
    activities = {entry["module_id"]: entry for entry in catalog["activities"]}
    documents = {module: copy.deepcopy(load(local_path(entry["json"]))) for module, entry in activities.items()}
    antecedents = {entry["module_id"]: entry for entry in catalog["antecedents"]}
    destinations = {}
    revisions = []
    for path in originals:
        if path.name != "planeacion.json" or not path.is_relative_to(PLANS / "importaciones"):
            continue
        historical = json.loads(originals[path].decode("utf-8-sig"))
        source_path = historical["sources"][0]["path"] or ""
        match = re.search(r"planeacion-modulo-(\d+)\.(?:json|md)$", source_path)
        if match is None or match[1] not in activities.keys() | antecedents.keys():
            raise ValueError("unmapped_historical_revision")
        module = match[1]
        revisions.append((path, historical, module))
        for name in ("planeacion.json", "planeacion.md", "cotejo-local.json"):
            sibling = path.with_name(name)
            if sibling not in originals:
                raise ValueError("incomplete_historical_revision")
            destinations[sibling] = module
    for path in originals:
        if path.is_relative_to(PLANS / "antecedentes"):
            destinations[path] = None
    if set(destinations) != set(originals):
        raise ValueError("unmapped_cleanup_file")
    catalog_relative = CATALOG.relative_to(SUBJECT).as_posix()
    integrated_files = {}
    for path, raw in originals.items():
        module = destinations[path]
        document = documents[module] if module in documents else catalog
        target = activities[module]["json"] if module in documents else catalog_relative
        text = raw.decode("utf-8")
        if text.encode("utf-8") != raw:
            raise ValueError("lossy_cleanup_encoding")
        sha256 = hashlib.sha256(raw).hexdigest()
        store = document.setdefault("extensions", {}).setdefault("integrated_documents", {"objects": {}, "files": {}, "reviews": []})
        store["objects"].setdefault(sha256, {"text": text, "media_type": "application/json" if path.suffix == ".json" else "text/markdown"})
        relative = path.relative_to(SUBJECT).as_posix()
        store["files"][relative] = sha256
        integrated_files[relative] = {"target": target, "sha256": sha256}
    for path, historical, module in revisions:
        document = documents[module] if module in documents else catalog
        review = json.loads(originals[path.with_name("cotejo-local.json")].decode("utf-8-sig"))
        document["extensions"]["integrated_documents"]["reviews"].append({"module_id": module, "revision": historical["revision"], "plan_id": historical["plan_id"],
            "document_sha256": hashlib.sha256(originals[path]).hexdigest(), "state": historical["review"]["state"], "findings": review["findings"], "critical_gaps": historical["review"]["critical_gaps"]})
    for entry in catalog["antecedents"]:
        document = json.loads(originals[local_path(entry["json"])].decode("utf-8-sig"))
        entry["document"] = document
        entry.pop("json")
        entry.pop("markdown")
        entry.pop("sha256", None)
        entry["anchor"] = f"foro-{entry['module_id']}"
    for record in catalog["absorption"]["files"].values():
        for entry in catalog["antecedents"]:
            if record["absorbed_into"].endswith(f"/antecedente-foro-{entry['module_id']}.json"):
                record["absorbed_into"] = catalog_relative
                record["antecedent_id"] = entry["module_id"]
    prepared = {}
    for module, document in documents.items():
        entry = activities[module]
        before = validate_pedagogical(load(local_path(entry["json"])), SUBJECT)
        editorial = document["extensions"]["editorial"]
        previous = editorial["previous_sha256"]
        if previous not in document["extensions"]["integrated_documents"]["objects"]:
            raise ValueError("previous_revision_not_integrated")
        editorial["previous_revision"] = None
        document["revision"] += 1
        document["extensions"]["integration"] = {"date": "2026-10-27", "separate_history_retained": False, "academic_approval": False}
        after = validate_pedagogical(document, SUBJECT)
        if after != before:
            raise ValueError("cleanup_changed_academic_validation")
        content = encode(document).encode("utf-8")
        entry.update(revision=document["revision"], sha256=hashlib.sha256(content).hexdigest())
        prepared[local_path(entry["json"])] = content
        prepared[local_path(entry["markdown"])] = render_absorbed(document).encode("utf-8")
    catalog["consolidation"] = {"date": "2026-10-27", "revisions": len(revisions), "files": integrated_files, "new_backup_files": 0}
    prepared[CATALOG] = encode(catalog).encode("utf-8")
    prepared[PLANS / "README.md"] = render_catalog(catalog).encode("utf-8")
    prepared[PLANS / "INDICE-ACTIVIDADES.md"] = b"# Indice de planeaciones\n\n[Actividades y antecedentes integrados](README.md).\n"
    for path, raw in originals.items():
        record = integrated_files[path.relative_to(SUBJECT).as_posix()]
        destination = json.loads(prepared[local_path(record["target"])].decode("utf-8"))
        integrated = destination["extensions"]["integrated_documents"]["objects"][record["sha256"]]["text"].encode("utf-8")
        if integrated != raw:
            raise ValueError("incomplete_folder_absorption")
    return catalog, prepared, originals


def consolidate_folders() -> dict:
    if "consolidation" in load(CATALOG):
        if any((PLANS / name).exists() for name in ("importaciones", "antecedentes")):
            raise ValueError("folders_reappeared_after_cleanup")
        return {"already_consolidated": True, "removed_files": 0}
    catalog, prepared, originals = prepare_folder_cleanup()
    for path, content in prepared.items():
        path.write_bytes(content)
    saved = load(CATALOG)
    for path, content in prepared.items():
        if path.read_bytes() != content:
            raise ValueError("cleanup_output_verification_failed")
    for path, raw in originals.items():
        if path.read_bytes() != raw or absorbed_bytes(saved, path.relative_to(SUBJECT).as_posix()) != raw:
            raise ValueError("cleanup_input_changed_before_removal")
    for path in originals:
        path.unlink()
    for name in ("importaciones", "antecedentes"):
        directory = PLANS / name
        for child in sorted((path for path in directory.rglob("*") if path.is_dir()), key=lambda path: len(path.parts), reverse=True):
            child.rmdir()
        directory.rmdir()
    return {"removed_files": len(originals), "integrated_revisions": catalog["consolidation"]["revisions"], "active_pairs": 22, "inline_omitted_forums": 3, "new_backup_files": 0}


def absorb_originals() -> dict:
    catalog = load(CATALOG)
    if "absorption" in catalog:
        if list(PLANS.glob("planeacion-modulo-*")):
            raise ValueError("originals_reappeared_after_absorption")
        return {"removed_files": 0, "already_absorbed": True}
    entries = catalog["activities"] + catalog["antecedents"]
    expected_paths = {PLANS / f"planeacion-modulo-{entry['module_id']}{suffix}" for entry in entries for suffix in (".json", ".md")}
    if set(PLANS.glob("planeacion-modulo-*")) != expected_paths or len(expected_paths) != 50:
        raise ValueError("unexpected_original_inventory")
    originals = {path: path.read_bytes() for path in expected_paths}
    prepared = {}
    absorbed = {}
    for entry in entries:
        path = local_path(entry["json"])
        document = copy.deepcopy(load(path))
        is_activity = "number" in entry
        before_findings = validate_pedagogical(document, SUBJECT)["findings"] if is_activity else []
        embedded = document.setdefault("extensions", {}).setdefault("embedded_sources", {})
        for suffix, source_id in ((".json", "src-local"), (".md", "src-original-markdown")):
            original_path = PLANS / f"planeacion-modulo-{entry['module_id']}{suffix}"
            raw = originals[original_path]
            relative = original_path.relative_to(SUBJECT).as_posix()
            sha256 = hashlib.sha256(raw).hexdigest()
            if catalog["historical_files"].get(relative) != sha256:
                raise ValueError("original_hash_changed: " + relative)
            text = raw.decode("utf-8")
            if text.encode("utf-8") != raw:
                raise ValueError("original_encoding_not_lossless")
            embedded[source_id] = {"encoding": "utf-8", "text": text, "original_name": original_path.name, "sha256": sha256}
            absorbed[relative] = {"absorbed_into": entry["json"], "source_id": source_id, "sha256": sha256}
            if is_activity:
                if suffix == ".json":
                    if json.loads(text.lstrip("\ufeff")) != document["extensions"]["conversion"]["source_payload"]:
                        raise ValueError("original_payload_not_fully_absorbed")
                    source = next(item for item in document["sources"] if item["id"] == source_id)
                    source["path"] = None
                else:
                    document["sources"].append({"id": source_id, "kind": "other", "authority": "editorial", "title": original_path.name,
                                                "url": None, "path": None, "sha256": sha256, "captured_at": None, "media_type": "text/markdown"})
        if is_activity:
            previous = PLANS / "importaciones" / document["plan_id"] / f"r{document['revision']:04d}" / "planeacion.json"
            editorial = document["extensions"]["editorial"]
            editorial["previous_revision"] = previous.relative_to(SUBJECT).as_posix()
            editorial["previous_sha256"] = digest(previous)
            document["revision"] += 1
            document["extensions"]["absorption"] = {"date": "2026-10-26", "complete_json_and_markdown": True, "separate_originals_retained": False}
            report = validate_pedagogical(document, SUBJECT)
            if report["findings"] != before_findings:
                raise ValueError("absorption_changed_academic_findings")
            markdown = render_absorbed(document)
            entry.update(revision=document["revision"], findings=report["findings"], semantic_passed=report["passed"])
        else:
            document.pop("original_json", None)
            document.pop("original_md", None)
            markdown = render_antecedent(document)
        content = encode(document).encode("utf-8")
        entry["sha256"] = hashlib.sha256(content).hexdigest()
        prepared[path] = content
        prepared[local_path(entry["markdown"])] = markdown.encode("utf-8")
    catalog["absorption"] = {"date": "2026-10-26", "policy": "integrated_sources_no_separate_backups", "files": absorbed}
    for path, raw in prepared.items():
        path.write_bytes(raw)
    CATALOG.write_text(encode(catalog), encoding="utf-8", newline="\n")
    for original_path, raw in originals.items():
        relative = original_path.relative_to(SUBJECT).as_posix()
        if original_path.read_bytes() != raw or absorbed_bytes(catalog, relative) != raw:
            raise ValueError("absorption_verification_failed_before_removal")
    for path, raw in prepared.items():
        if path.read_bytes() != raw:
            raise ValueError("active_output_verification_failed")
    for path in originals:
        path.unlink()
    if list(PLANS.glob("planeacion-modulo-*")):
        raise ValueError("originals_remaining")
    return {"removed_files": len(originals), "active_pairs": 22, "omitted_antecedents": 3, "new_backup_files": 0}


def audit() -> dict:
    catalog = load(CATALOG)
    master = SUBJECT / "Estad\u00edstica aplicada para la administraci\u00f3n.md"
    master_text = master.read_text(encoding="utf-8-sig")
    mapping = {int(number): module for number, module in re.findall(r"^\| \*\*(\d+)\*\* \| `A\d+` \| `(\d+)`", master_text, re.M)}
    errors = []
    rows = []
    active_paths = catalogued_plan_paths(SUBJECT)
    if set(mapping) != set(range(1, 23)) or len(active_paths or ()) != 22:
        errors.append("master_or_catalog_count")
    revisions = list(PLANS.glob("importaciones/*/r*/planeacion.json"))
    historical_differences = []
    for section in ("historical_files", "protected_files"):
        for relative, expected in catalog[section].items():
            path = local_path(relative)
            embedded = absorbed_bytes(catalog, relative)
            actual = digest(path) if path.is_file() else hashlib.sha256(embedded).hexdigest() if embedded is not None else None
            if actual != expected:
                if section == "historical_files" and relative in {
                    f"{PLANS.name}/README.md", f"{PLANS.name}/INDICE-ACTIVIDADES.md",
                }:
                    historical_differences.append({"path": relative, "historical_sha256": expected, "current_sha256": digest(path) if path.is_file() else None})
                else:
                    errors.append(f"{section}: {relative}")
    for entry in catalog["activities"]:
        number = entry["number"]
        path = local_path(entry["json"])
        document = load(path)
        activity = document["activities"][0]
        editorial = document["extensions"]["editorial"]
        report = validate_pedagogical(document, SUBJECT)
        if mapping.get(number) != entry["module_id"] or activity["id"] != entry["module_id"] or editorial["number"] != number:
            errors.append(f"mapping: {number}")
        if path.name != f"planeacion-{SLUG}-Actividad-{number}.json":
            errors.append(f"name: {number}")
        if editorial["master_row"] not in master_text:
            errors.append(f"master_row: {number}")
        archived = PLANS / "importaciones" / document["plan_id"] / f"r{document['revision']:04d}" / "planeacion.json"
        if "absorption" in catalog:
            if entry.get("sha256") != digest(path):
                errors.append(f"active_hash: {number}")
        elif not archived.is_file() or digest(archived) != digest(path):
            errors.append(f"active_revision: {number}")
        if (entry["plan_id"], entry["revision"], entry["state"]) != (document["plan_id"], document["revision"], document["review"]["state"]):
            errors.append(f"catalog_revision: {number}")
        if entry["semantic_passed"] != report["passed"] or entry["findings"] != report["findings"]:
            errors.append(f"stale_findings: {number}")
        for finding in report["findings"]:
            if finding["code"] in {"source_hash_changed", "missing_source", "unsafe_source_path", "unresolved_reference", "unresolved_pointer", "duplicate_id", "unresolved_evidence_source"}:
                errors.append(f"{number}: {finding['code']}: {finding['path']}")
        for field in ("tex", "pdf"):
            if editorial["report"][field] != f"reporte-{SLUG}-Actividad-{number}.{field}" or not local_path(editorial["report"][field]).is_file():
                errors.append(f"report_{field}: {number}")
        for relative in activity["bindings"].values():
            if relative is not None and not local_path(relative).is_dir():
                errors.append(f"binding: {number}: {relative}")
        if editorial["previous_revision"] is None:
            previous_text = document.get("extensions", {}).get("integrated_documents", {}).get("objects", {}).get(editorial["previous_sha256"], {}).get("text")
            if previous_text is None or hashlib.sha256(previous_text.encode("utf-8")).hexdigest() != editorial["previous_sha256"]:
                errors.append(f"previous_revision: {number}")
        elif digest(local_path(editorial["previous_revision"])) != editorial["previous_sha256"]:
            errors.append(f"previous_revision: {number}")
        if any(activity["calendar"].values()):
            errors.append(f"operational_calendar_not_empty: {number}")
        original = document["extensions"]["conversion"]["source_payload"]
        if original.get("retrieved_at_utc") != document["sources"][0]["captured_at"]:
            errors.append(f"capture_date: {number}")
        if number in {3, 6, 9, 12, 19} and (editorial["delivery"]["generate_pdf_by_default"] is not False or editorial["delivery"]["existing_path"] is not None):
            errors.append(f"quiz_delivery: {number}")
        if number <= 5 and not editorial["already_completed_evidence"]:
            errors.append(f"completed_evidence: {number}")
        if set(editorial["integration_blocks"]) != BLOCKS:
            errors.append(f"integration_blocks: {number}")
        markdown_path = local_path(entry["markdown"])
        markdown = markdown_path.read_text(encoding="utf-8")
        if activity["instruction"] not in markdown or "|  |  |  |  |  |" not in markdown:
            errors.append(f"markdown_instruction_calendar: {number}")
        observed_sections = {}
        for section in re.split(r"^## ", markdown, flags=re.M)[1:]:
            title = section.splitlines()[0]
            blocks = re.findall(r"```json\n(.*?)\n```", section, re.S)
            if len(blocks) == 1:
                observed_sections[title] = json.loads(blocks[0])
        if "absorption" not in catalog:
            for title, expected in markdown_sections(document).items():
                if observed_sections.get(title) != expected:
                    errors.append(f"markdown_derivation: {number}: {title}")
        if "absorption" in catalog and markdown != render_absorbed(document):
            errors.append(f"markdown_full_derivation: {number}")
        teacher = next(source for source in document["sources"] if source["id"] == "src-teacher")
        if activity["instruction"] not in local_path(teacher["path"]).read_text(encoding="utf-8"):
            errors.append(f"instruction_literal: {number}")
        rows.append({"number": number, "module_id": entry["module_id"], "json": entry["json"], "revision": document["revision"], "state": document["review"]["state"], "semantic_passed": report["passed"], "findings": report["findings"], "blocks": {key: value["status"] for key, value in editorial["integration_blocks"].items()}})
    if {entry["module_id"] for entry in catalog["antecedents"]} != {"1726", "1727", "1738"}:
        errors.append("initial_forums")
    for entry in catalog["antecedents"]:
        antecedent = entry["document"] if "document" in entry else load(local_path(entry["json"]))
        if antecedent["status"] != OMISSION or antecedent["activity_number"] is not None or antecedent["reports"] or antecedent["deliverables"]:
            errors.append(f"antecedent: {entry['module_id']}")
        if any(antecedent[key] is not False for key in ("execution_allowed", "campaign_allowed", "extractor_allowed", "monitor_allowed")):
            errors.append(f"antecedent_permissions: {entry['module_id']}")
        antecedent_view = (PLANS / "README.md") if "document" in entry else local_path(entry["markdown"])
        if OMISSION not in antecedent_view.read_text(encoding="utf-8"):
            errors.append(f"antecedent_markdown: {entry['module_id']}")
    for relative, record in catalog.get("absorption", {}).get("files", {}).items():
        if local_path(relative).exists() or hashlib.sha256(absorbed_bytes(catalog, relative)).hexdigest() != record["sha256"]:
            errors.append(f"absorption_integrity: {relative}")
    for relative, record in catalog.get("consolidation", {}).get("files", {}).items():
        if local_path(relative).exists() or hashlib.sha256(absorbed_bytes(catalog, relative)).hexdigest() != record["sha256"]:
            errors.append(f"consolidation_integrity: {relative}")
    if "consolidation" in catalog:
        if any((PLANS / name).exists() for name in ("importaciones", "antecedentes")):
            errors.append("consolidated_folders_still_present")
        if (PLANS / "README.md").read_text(encoding="utf-8") != render_catalog(catalog):
            errors.append("catalog_markdown_derivation")
    return {"kind": "estadistica-editorial-audit", "date": "2026-10-27", "technical_passed": not errors, "errors": errors,
            "active_pairs": len(rows), "original_pairs": len(list(PLANS.glob("planeacion-modulo-*.json"))),
            "absorbed_original_files": len(catalog.get("absorption", {}).get("files", {})),
            "consolidated_folder_files": len(catalog.get("consolidation", {}).get("files", {})),
            "integrated_revisions": catalog.get("consolidation", {}).get("revisions", 0),
            "conversion_chains": len({path.parent.parent for path in revisions}), "stored_revisions": len(revisions),
            "revision_states": dict(Counter(load(path)["review"]["state"] for path in revisions)),
            "protected_files_checked": len(catalog["protected_files"]), "historical_files_checked": len(catalog["historical_files"]),
            "historical_index_differences": historical_differences, "activities": rows, "pilot": catalog["pilot"],
            "academic_approval": False, "cycles_executed": 0, "platform_accessed": False, "submission_allowed": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", help="Nuevo nombre de diagnostico sin extension")
    parser.add_argument("--absorb-originals", action="store_true", help="Absorber 25 pares completos y eliminar originales sin respaldos nuevos")
    parser.add_argument("--render-views", action="store_true", help="Regenerar vistas visuales Markdown desde los JSON activos")
    parser.add_argument("--consolidate-folders", action="store_true", help="Absorber importaciones y antecedentes, y eliminar sus carpetas sin respaldos")
    arguments = parser.parse_args()
    if arguments.record and not re.fullmatch(r"[a-z0-9-]+", arguments.record):
        parser.error("Nombre de diagnostico inseguro")
    if arguments.absorb_originals:
        print(json.dumps(absorb_originals(), ensure_ascii=True))
    if arguments.consolidate_folders:
        print(json.dumps(consolidate_folders(), ensure_ascii=True))
    if arguments.render_views:
        catalog = load(CATALOG)
        if "absorption" not in catalog:
            raise ValueError("absorption_required_before_visual_rendering")
        entries = catalog["activities"] if "consolidation" in catalog else catalog["activities"] + catalog["antecedents"]
        for entry in entries:
            document = load(local_path(entry["json"]))
            text = render_absorbed(document) if "number" in entry else render_antecedent(document)
            local_path(entry["markdown"]).write_text(text, encoding="utf-8", newline="\n")
        if "consolidation" in catalog:
            (PLANS / "README.md").write_text(render_catalog(catalog), encoding="utf-8", newline="\n")
    result = audit()
    if arguments.record:
        path = PLANS / (arguments.record + ".json")
        markdown_path = path.with_suffix(".md")
        if path.exists() or markdown_path.exists():
            raise FileExistsError("audit_record_exists")
        lines = ["# Cotejo reproducible de Estadistica", "", "Fecha documental: " + result["date"], "",
                 f"Pares activos: {result['active_pairs']}. Originales: {result['original_pairs']}. Cadenas: {result['conversion_chains']}. Revisiones: {result['stored_revisions']}.", "",
                 "## Dictamen", "", "Habilitacion bloqueada. Validacion tecnica y aprobacion academica son controles distintos.",
                 "No se publicaron revisiones de planeacion, no se ejecutaron ciclos, extractores, monitores ni envios; no se accedio a Moodle.", "",
                 "## Discrepancias de integridad", ""]
        lines.extend("- " + error for error in result["errors"])
        lines.extend(["", "Los hashes historicos no se han reescrito. Dos indices activos ya diferian de sus huellas historicas antes de este cotejo:", ""])
        lines.extend("- " + item["path"] for item in result["historical_index_differences"])
        lines.extend(["", "## Correspondencias y bloqueos", "", "| Actividad | Modulo | Revision | Estado | Hallazgos |", "| --- | --- | --- | --- | --- |"])
        for row in result["activities"]:
            findings = ", ".join(sorted({item["code"] for item in row["findings"]}))
            lines.append(f"| {row['number']} | {row['module_id']} | {row['revision']} | {row['state']} | {findings} |")
        lines.extend(["", "## Limites academicos", "",
                      "Actividad 7: extension contradictoria (3 paginas frente a 3 cuartillas sin portada ni fuentes), portada/producto pendientes y escala oficial no verificada. La suma observada de 24 puntos no es calificacion oficial.",
                      "Las otras 21 actividades conservan bloques pendientes de segmentacion, productos y alineacion; la existencia del bloque no significa que este completo.",
                      "Cuestionarios 3, 6, 9, 12 y 19: reporte documental, sin PDF de entrega por defecto. Actividades 1 a 5: evidencia de realizacion; no repetir.", "",
                      "## Antecedentes excluidos", ""])
        lines.extend(f"- {module}: {OMISSION}." for module in ("1726", "1727", "1738"))
        lines.extend(["", "Sin numero, tareas, reportes, entregables, campañas, extractores ni monitores. La exclusion no aplica a otros foros evaluables.", "",
                      "## Comprobaciones", "", "Esquema, correspondencia con maestro, revision archivada, hashes de fuentes, referencias internas, rutas y bloques Markdown cotejados contra JSON.",
                      "Calendarios operativos vacios; capturas, revisiones y literales historicos preservados. Los detalles por bloque estan en el JSON de este dictamen.", ""])
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(encode(result))
        with markdown_path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write("\n".join(lines))
    summary = {key: value for key, value in result.items() if key not in {"activities", "historical_index_differences"}}
    summary["historical_index_differences"] = [item["path"] for item in result["historical_index_differences"]]
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 0 if result["technical_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())