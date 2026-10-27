from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

from aulatex.planning_conversion import _empty_activity, publish_conversion, read_planning_source
from aulatex.workspace import AulaTeXWorkspace


def segment_document(document: dict, blocks: list[dict]) -> dict:
    revised = copy.deepcopy(document)
    pages = {block["locator"]: block["text"] for block in blocks}

    def page(number: int) -> str:
        text = re.sub(r"Página\s+\d+\s+de\s+\d+", "", pages[f"page:{number}"])
        return "\n".join(line.strip() for line in text.splitlines())

    joined = "\n".join(page(number) for number in (6, 7, 8))
    case_text = joined.split("Caso 1.", 1)[1].split("3. Integración del análisis", 1)[0]
    cases = re.split(r"Caso ([2-5])\.\s*", case_text)
    contents = [cases[0]] + [cases[index + 1] for index in range(1, len(cases), 2)]
    if len(contents) != 5:
        raise ValueError("expected_five_cases")
    activity = _empty_activity("s3-estudio-casos", "Estudio de casos")
    activity["weeks"] = [3]
    activity["unit_id"] = "2"
    activity["instruction"] = joined
    activity["bindings"] = copy.deepcopy(document["activities"][0]["bindings"])
    activity["policies"]["exceptions"] = []
    activity["assessment"].update(kind="summative", scale_total=15, weight=15, weight_unit="percent")
    activity["calendar"]["literal"] = "Semana 3 (Del 12 al 18 de octubre de 2026). Fecha de entrega: 18 de Octubre."
    activity["policies"]["collaboration"] = "La actividad deberá realizarse de manera individual."
    activity["policies"]["citation"] = "Utiliza citas y referencias conforme al formato APA, séptima edición."
    activity["policies"]["attempts"] = 1
    activity["policies"]["late_submission"] = "Penalización de 20% menos; recepción hasta el cierre de aula, 02 de diciembre."
    statuses = []

    def status(path: str, locators: list[str], state: str = "confirmed", reason: str = "Segmentacion local cotejada con el PDF; no acredita vigencia actual de plataforma.") -> None:
        statuses.append({"path": path, "state": state, "reason": reason, "evidence": [{"source_id": "src-local", "locator": locator, "quoted_text": pages[locator]} for locator in locators], "alternatives": []})

    status("/activities/0/instruction", ["page:6", "page:7", "page:8"])
    case_records = []
    points = (3, 2, 3, 2, 3)
    descriptions = (
        "Distingue ambos delitos, identifica sus elementos jurídicos y reconoce posibles agravantes y atenuantes.",
        "Identifica los elementos del delito y explica la relevancia del parentesco y sus diferencias respecto del homicidio.",
        "Reconoce conductas de violencia familiar, identifica posibles razones de género y distingue las figuras del homicidio.",
        "Identifica las conductas, sujetos y elementos jurídicos, distinguiendo inducción, auxilio y ejecución directa.",
        "Diferencia ambos supuestos y explica la relevancia del consentimiento, la gestación y las disposiciones aplicables.",
    )
    for index, content in enumerate(contents):
        title, remainder = content.strip().split("\n", 1)
        context, questions_text = remainder.split("Responde:", 1)
        questions = re.split(r"(?:^|\n)\s*[abc]\)\s*", questions_text)[1:]
        if len(questions) != 3:
            raise ValueError("expected_three_questions_per_case")
        requirement = {"id": f"req-caso-{index + 1}", "text": f"Caso {index + 1}. {title}: responder los tres cuestionamientos con argumentos jurídicos sustentados en la legislación aplicable."}
        activity["requirements"].append(requirement)
        case_records.append({"id": f"caso-{index + 1}", "title": title, "context": context.strip(), "question_ids": [f"pregunta-{index + 1}-{position + 1}" for position in range(3)]})
        for position, question in enumerate(questions):
            activity["questions"].append({"id": f"pregunta-{index + 1}-{position + 1}", "context": context.strip(), "text": " ".join(question.split()), "requirement_ids": [requirement["id"]]})
        activity["assessment"]["criteria"].append({"id": f"criterio-caso-{index + 1}", "text": descriptions[index], "points": points[index], "descriptors": [], "requirement_ids": [requirement["id"]]})
    activity["requirements"].extend([
        {"id": "req-tabla", "text": "Elaborar una tabla de síntesis: caso, delito o figura jurídica, conducta relevante y fundamento legal; identificar las figuras que correspondan sin suponer hechos no descritos."},
        {"id": "req-presentacion", "text": "Redacción individual y propia; argumentos fundados en artículos aplicables, citas y referencias APA 7; máximo de ocho cuartillas incluyendo datos de identificación, desarrollo, tabla y referencias."},
    ])
    activity["assessment"]["criteria"].extend([
        {"id": "criterio-tabla", "text": "Identifica y organiza correctamente las figuras jurídicas, conductas y fundamentos legales de los cinco casos.", "points": 1, "descriptors": [], "requirement_ids": ["req-tabla"]},
        {"id": "criterio-presentacion", "text": "Redacta con sus propias palabras, respeta el máximo de ocho cuartillas e incluye citas y referencias APA 7.", "points": 1, "descriptors": [], "requirement_ids": ["req-presentacion"]},
    ])
    requirement_ids = [item["id"] for item in activity["requirements"]]
    activity["products"] = [{"id": "producto-estudio-casos", "kind": "report", "recipient": None, "editable_format": "Word o equivalente", "submission_format": None, "structure": ["Datos de identificación", "Análisis de cinco casos y quince respuestas", "Tabla de síntesis", "Referencias"], "length": "Máximo de 8 cuartillas, incluyendo datos de identificación, desarrollo, tabla y referencias.", "filename_pattern": None, "accessibility": None, "requirement_ids": requirement_ids, "paths": {"editable": None, "delivery": None}}]
    objective = "Analizar situaciones jurídicas relacionadas con los delitos contra la vida e integridad corporal mediante el estudio de casos hipotéticos y la interpretación de las disposiciones legales aplicables."
    revised["curriculum"]["outcomes"] = [{"id": "resultado-s3", "text": objective}]
    activity["outcome_ids"] = ["resultado-s3"]
    activity["alignment"] = [{"outcome_id": "resultado-s3", "requirement_ids": requirement_ids, "step_ids": [], "product_ids": ["producto-estudio-casos"], "criterion_ids": [item["id"] for item in activity["assessment"]["criteria"]]}]
    status("/curriculum/outcomes/0", ["page:6"], "inferred", "Sintesis editorial del proposito; el literal completo se conserva en la evidencia.")
    status("/activities/0/requirements", ["page:6", "page:7", "page:8"])
    status("/activities/0/questions", ["page:6", "page:7", "page:8"])
    status("/activities/0/products", ["page:6", "page:8"])
    status("/activities/0/assessment", ["page:8", "page:10"])
    status("/activities/0/policies", ["page:8", "page:9"])
    status("/activities/0/calendar", ["page:4"], "unknown", "Fecha literal preservada; no inferir hora ni zona horaria.")
    status("/activities/0/products/0/length", ["page:8"], "conflict", "La preferencia editorial excluye preliminares y referencias; el PDF docente los incluye. Confirmacion docente pendiente.")
    statuses[-1]["alternatives"] = [
        {"value": "Ocho cuartillas incluyendo identificacion, desarrollo, tabla y referencias.", "evidence": [{"source_id": "src-local", "locator": "page:8", "quoted_text": pages["page:8"]}]},
        {"value": "Ocho cuartillas solo de cuerpo, excluyendo portada, resumen, indice y referencias.", "evidence": [{"source_id": "src-editorial", "locator": "Diferencia de criterios de extension", "quoted_text": "el 12/10/2026 el estudiante preciso que cuenta las ocho cuartillas solo para introduccion, desarrollo y conclusion, excluyendo portada, resumen, indice y referencias."}]},
    ]
    revised["activities"] = [activity]
    revised["field_status"] = statuses
    revised["sources"][0]["authority"] = "instructional"
    revised["review"] = {"state": "needs_review", "reviewed_at": "2026-10-26", "reviewer_role": "cotejo-documental-local", "semantic_validation": "failed", "critical_gaps": ["Resolver discrepancia del computo de ocho cuartillas con docente.", "Acreditar correspondencia entre actividad real, nodo local y oferta; recurso 216749 no es ID de tarea.", "Verificar recursos obligatorios, vigencia de plataforma y fidelidad visual de la rubrica."]}
    conversion = revised["extensions"]["conversion"]
    conversion["unsegmented_document"] = False
    conversion["activity_mapping"] = [{"activity_id": activity["id"], "local_number": None, "source_locator": "page:6..8", "source_is_summary": False}]
    revised["extensions"]["cotejo"] = {"method": "segmentacion PDF por localizadores y cotejo con transcripcion estructurada", "resource_module_id": "216749", "resource_is_activity_id": False, "cases": case_records, "question_count": len(activity["questions"]), "rubric_points": sum(item["points"] for item in activity["assessment"]["criteria"]), "platform_current_verified": False, "visual_rubric_verified": False}
    return revised


def segment_later_document(document: dict, blocks: list[dict], week: int) -> dict:
    if week not in {4, 5}:
        raise ValueError("unsupported_week")
    revised = copy.deepcopy(document)
    pages = {block["locator"]: block["text"] for block in blocks}
    cleaned = {locator: "\n".join(line.strip() for line in re.sub(r"Página\s+\d+\s+de\s+\d+", "", text).splitlines()) for locator, text in pages.items()}
    joined = "\n".join(cleaned[f"page:{number}"] for number in (6, 7, 8))
    title = "Valoración de decisiones" if week == 4 else "Simulación de expediente jurídico"
    activity = _empty_activity(f"s{week}-" + ("valoracion-decisiones" if week == 4 else "simulacion-expediente"), title)
    activity["weeks"] = [week]
    activity["unit_id"] = str(week - 1)
    activity["instruction"] = joined
    activity["bindings"] = copy.deepcopy(document["activities"][0]["bindings"])
    activity["policies"]["exceptions"] = []
    activity["assessment"].update(kind="summative", scale_total=10 if week == 4 else 15, weight=10 if week == 4 else 15, weight_unit="percent")
    activity["calendar"]["literal"] = cleaned["page:4"]
    activity["policies"].update(collaboration="Individual", citation="APA 7", attempts=1)
    investigation = "Tabla de investigación jurídica: para cada figura, conducta, artículo y legislación; indicar figuras no localizadas o no vigentes. No transcribir definiciones ni artículos completos." if week == 4 else "Tabla de cinco figuras con cuatro columnas: Figura delictiva / Ley y artículo / Conducta descrita / Elemento que la diferencia. En secuestro incluir una circunstancia modificativa; revisar leyes especiales cuando corresponda. No transcribir artículos completos."
    activity["requirements"].append({"id": "req-investigacion", "text": investigation})
    if week == 4:
        selected = joined.split("Caso 1.", 1)[1].split("3. Decisión fundamentada", 1)[0]
        parts = re.split(r"Caso ([2-3])\.\s*", selected)
        contents = [parts[0]] + [parts[index + 1] for index in range(1, len(parts), 2)]
        prompts = None
    else:
        selected = joined.split("Ficha 1.", 1)[1].split("4. Informe breve y entrega", 1)[0]
        parts = re.split(r"Ficha ([2-3])\.\s*", selected)
        contents = [parts[0]] + [parts[index + 1] for index in range(1, len(parts), 2)]
        procedure = joined.split("Para estudiar cualquier hecho, sigue este orden:", 1)[1].split("Ejemplo:", 1)[0]
        prompts = re.split(r"(?:^|\n)\s*[A-E]\.\s*", procedure)[1:]
        if len(prompts) != 5:
            raise ValueError("expected_five_procedure_questions")
    if len(contents) != 3:
        raise ValueError("expected_three_cases_or_cards")
    case_records = []
    for index, content in enumerate(contents):
        case_title, remainder = content.strip().split("\n", 1)
        requirement_id = f"req-{'caso' if week == 4 else 'ficha'}-{index + 1}"
        if week == 4:
            context, question_text = remainder.split("Responde:", 1)
            questions = re.split(r"(?:^|\n)\s*[ab]\)\s*", question_text)[1:]
            if len(questions) != 2:
                raise ValueError("expected_two_questions_per_case")
        else:
            context, questions = remainder, prompts
        requirement_text = f"{'Caso' if week == 4 else 'Ficha'} {index + 1}. {case_title}: aplicar los cuestionamientos docentes y fundamentar la clasificación sin suponer hechos."
        if week == 5:
            requirement_text += " Tabla por ficha: Hechos conocidos / Elementos legales identificados / Datos que faltan / Posible figura y fundamento. La conclusión puede ser información insuficiente."
        activity["requirements"].append({"id": requirement_id, "text": requirement_text})
        case_records.append({"id": requirement_id, "title": case_title, "context": context.strip(), "question_ids": []})
        for position, question in enumerate(questions):
            question_id = f"pregunta-{index + 1}-{position + 1}"
            activity["questions"].append({"id": question_id, "context": context.strip(), "text": " ".join(question.split()), "requirement_ids": [requirement_id]})
            case_records[-1]["question_ids"].append(question_id)
    activity["requirements"].extend([
        {"id": "req-cierre", "text": "Elegir un caso o ficha y redactar una decisión o conclusión de cinco a siete líneas, con fundamento consultado e información adicional indispensable."},
        {"id": "req-integracion", "text": "PDF individual con portada, tabla de investigación, respuestas o fichas, cierre y referencias APA 7. Los límites de extensión contradictorios se conservan en el cotejo."},
    ])
    descriptions = (
        [("Investigación jurídica", "Identifica las figuras delictivas, sus conductas y fundamentos legales.", 2, "req-investigacion"),
         ("Caso 1", "Identifica los posibles delitos y los elementos necesarios para su configuración.", 2, "req-caso-1"),
         ("Caso 2", "Reconoce las figuras delictivas, obligaciones y circunstancias relevantes.", 2, "req-caso-2"),
         ("Caso 3", "Distingue las conductas y los elementos jurídicos aplicables.", 2, "req-caso-3"),
         ("Decisión fundamentada", "Presenta una conclusión coherente y sustentada jurídicamente.", 1, "req-cierre"),
         ("Integración y presentación", "Organiza el trabajo e incluye las referencias en APA 7.", 1, "req-integracion")]
        if week == 4 else
        [("Investigación jurídica", "Localiza cinco figuras, sus fundamentos y un elemento distintivo de cada una.", 3, "req-investigacion"),
         ("Ficha 1", "Identifica hechos, finalidad, requisitos legales y datos por comprobar.", 3, "req-ficha-1"),
         ("Ficha 2", "Distingue hechos conocidos y requisitos de intervención y desaparición por verificar.", 3, "req-ficha-2"),
         ("Ficha 3", "Diferencia posibles figuras según guarda, consentimiento, finalidad y datos faltantes.", 3, "req-ficha-3"),
         ("Informe jurídico", "Formula una conclusión preliminar con fundamento y reserva cuando falten datos.", 2, "req-cierre"),
         ("Informe jurídico", "Presenta una conclusión preliminar coherente y fundamentada.", 2, "req-cierre"),
         ("Integración y presentación", "Organiza el documento e incluye referencias APA 7.", 1, "req-integracion")]
    )
    activity["assessment"]["criteria"] = [{"id": f"criterio-{index + 1}", "text": name + ": " + description, "points": points, "descriptors": [], "requirement_ids": [requirement]} for index, (name, description, points, requirement) in enumerate(descriptions)]
    requirement_ids = [item["id"] for item in activity["requirements"]]
    activity["products"] = [{"id": "producto-documento", "kind": "report", "recipient": None, "editable_format": "Procesador de textos", "submission_format": "PDF", "structure": ["Portada", "Tabla de investigación", "Respuestas a tres casos" if week == 4 else "Tres fichas con las cuatro columnas docentes", "Decisión fundamentada de cinco a siete líneas" if week == 4 else "Conclusión de cinco a siete líneas", "Referencias APA 7"], "length": "Límite de extensión en conflicto; consultar alternativas y fuentes.", "filename_pattern": None, "accessibility": None, "requirement_ids": requirement_ids, "paths": {"editable": None, "delivery": None}}]
    outcome_id = f"resultado-s{week}"
    revised["curriculum"]["outcomes"] = [{"id": outcome_id, "text": "Identificar elementos legales, distinguir hechos de inferencias y fundamentar una clasificación jurídica preliminar."}]
    activity["outcome_ids"] = [outcome_id]
    activity["alignment"] = [{"outcome_id": outcome_id, "requirement_ids": requirement_ids, "step_ids": [], "product_ids": ["producto-documento"], "criterion_ids": [item["id"] for item in activity["assessment"]["criteria"]]}]
    statuses = []

    def evidence(locator: str) -> dict:
        return {"source_id": "src-local", "locator": locator, "quoted_text": pages[locator]}

    for field, locators in (("instruction", (6, 7, 8)), ("requirements", (6, 7, 8)), ("questions", (6, 7)), ("products", (7, 8)), ("assessment", (8, 9)), ("policies", (8, 9))):
        statuses.append({"path": "/activities/0/" + field, "state": "confirmed", "reason": "Segmentacion local del PDF docente; vigencia de plataforma y fidelidad visual pendientes.", "evidence": [evidence(f"page:{number}") for number in locators], "alternatives": []})
    statuses.append({"path": "/curriculum/outcomes/0", "state": "inferred", "reason": "Sintesis editorial del proposito; el literal se conserva en la consigna.", "evidence": [evidence("page:6")], "alternatives": []})
    length_alternatives = [
        {"value": "Cuatro cuartillas incluyendo portada y referencias.", "evidence": [evidence("page:7" if week == 4 else "page:8")]},
        {"value": "Seis cuartillas incluyendo portada, tabla y bibliografia." if week == 4 else "Ocho cuartillas; observaciones del PDF.", "evidence": [evidence("page:8")]},
        {"value": "Cuatro paginas solo del cuerpo; preferencia editorial, no confirmacion docente.", "evidence": [{"source_id": "src-editorial", "locator": "Criterios de evaluacion docente" if week == 4 else "Arquitectura y extension", "quoted_text": None}]},
    ]
    statuses.append({"path": "/activities/0/products/0/length", "state": "conflict", "reason": "PDF con limites contradictorios y preferencia editorial distinta; conservar las tres versiones.", "evidence": [evidence("page:7"), evidence("page:8")], "alternatives": length_alternatives})
    if week == 5:
        statuses.append({"path": "/activities/0/assessment/scale_total", "state": "conflict", "reason": "Las siete filas impresas suman 17; el total impreso es 15. No deduplicar Informe juridico para simular una correccion docente.", "evidence": [evidence("page:9")], "alternatives": [{"value": 15, "evidence": [evidence("page:9")]}, {"value": 17, "evidence": [evidence("page:9")]}]})
    revised["activities"] = [activity]
    revised["field_status"] = statuses
    revised["sources"][0]["authority"] = "instructional"
    revised["review"] = {"state": "needs_review", "reviewed_at": "2026-10-26", "reviewer_role": "cotejo-documental-local", "semantic_validation": "failed", "critical_gaps": ["Resolver limites de extension contradictorios con la figura docente.", "Acreditar correspondencia entre tarea, nodo local y oferta; no usar ID de recurso como ID de tarea.", "Verificar recursos obligatorios, vigencia de plataforma y rubrica visual."]}
    if week == 5:
        revised["review"]["critical_gaps"].append("Confirmar la duplicacion de Informe juridico y el total docente 15 frente a suma 17.")
    revised["extensions"]["conversion"]["unsegmented_document"] = False
    revised["extensions"]["conversion"]["activity_mapping"] = [{"activity_id": activity["id"], "local_number": None, "source_locator": "page:6..8", "source_is_summary": False}]
    revised["extensions"]["cotejo"] = {"method": "segmentacion PDF por localizadores", "resource_module_id": "218336" if week == 4 else None, "resource_is_activity_id": False, "cases": case_records, "question_count": len(activity["questions"]), "rubric_points": sum(item["points"] for item in activity["assessment"]["criteria"]), "printed_total": activity["assessment"]["scale_total"], "duplicate_criterion_preserved": week == 5, "platform_current_verified": False, "visual_rubric_verified": False}
    return revised


def main() -> None:
    parser = argparse.ArgumentParser(description="Cotejar y segmentar PDF originales Penal S3-S5 sin habilitar ejecucion.")
    parser.add_argument("--week", type=int, choices=(3, 4, 5), default=3)
    args = parser.parse_args()
    workspace = AulaTeXWorkspace(Path(__file__).resolve().parents[1])
    subject_key = "UnADM/licenciatura-en-derecho-unadm/derecho-penal-especial-mexicano-lde"
    scopes, _children = workspace.editorial_scope_index()
    subject = scopes[subject_key]
    identifiers = {3: "pca-59835c6a72ea8aba5dfc", 4: "pca-4dd40f72de8af2db1526", 5: "pca-3057c47ded95b7ad2de1"}
    directory = workspace.resolve_target(subject.relative_path) / "planeaciones-derecho-penal-especial-mexicano/importaciones" / identifiers[args.week]
    original = json.loads((directory / "r0001/planeacion.json").read_text(encoding="utf-8"))
    source = workspace.resolve_target(subject.relative_path) / original["sources"][0]["path"]
    if hashlib.sha256(source.read_bytes()).hexdigest() != original["sources"][0]["sha256"]:
        raise ValueError("source_hash_changed")
    editorial = source.parent.parent / ("planeacion-S3.md" if args.week == 3 else f"planeacion-S{args.week}-estructurada.md")
    original["sources"].append({"id": "src-editorial", "kind": "other", "authority": "editorial", "title": "Nota local S3: discrepancia de extension" if args.week == 3 else f"Nota local S{args.week}: discrepancias documentales", "url": None, "path": editorial.relative_to(workspace.resolve_target(subject.relative_path)).as_posix(), "sha256": hashlib.sha256(editorial.read_bytes()).hexdigest(), "captured_at": None, "media_type": "text/markdown"})
    _payload, blocks = read_planning_source(source)
    revised = segment_document(original, blocks) if args.week == 3 else segment_later_document(original, blocks, args.week)
    previous = sorted(directory.glob("r*/planeacion.json"))
    last = json.loads(previous[-1].read_text(encoding="utf-8"))
    revised["revision"] = last["revision"]
    if revised != last:
        revised["revision"] += 1
    result = publish_conversion(workspace, subject, revised)
    print(json.dumps({"week": args.week, "revision": revised["revision"], "path": result["pedagogical_json"], "cases": len(revised["extensions"]["cotejo"]["cases"]), "questions": len(revised["activities"][0]["questions"]), "criteria": len(revised["activities"][0]["assessment"]["criteria"]), "points": revised["extensions"]["cotejo"]["rubric_points"], "state": result["state"], "findings": result["findings"]}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()