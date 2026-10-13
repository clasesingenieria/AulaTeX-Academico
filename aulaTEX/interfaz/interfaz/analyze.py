from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from .azure_openai_client import build_pdf_input_message, invoke_chat, uses_openai_v1_endpoint
from .config import Settings, load_settings
from .config import Settings, llm_max_output_tokens, load_settings


SYSTEM_PROMPT = """Eres un editor experto de notas personales en espanol.
Tu tarea es transformar una transcripcion cruda en una nota clara y util para una base de conocimiento.

Reglas:
1. Propón un titulo breve, especifico y usable como nombre clave, pero redactado en lenguaje natural. No uses slugs, guiones, guiones bajos ni nombres de archivo.
2. Reescribe la nota con redaccion limpia, manteniendo la intencion original.
2.1 Conserva la perspectiva narrativa original del autor. Si el texto habla en primera persona, mantenlo en primera persona.
2.2 No describas el contenido como "la nota", "el texto", "el autor" o "la transcripcion". Reescribe directamente las ideas.
2.3 No conviertas ideas en comentarios metalinguisticos del tipo "la nota plantea", "el texto menciona" o similares.
2.4 Si la entrada es un cuestionario, examen, lista de preguntas con opciones, formulario o material de estudio altamente estructurado, conserva su estructura original.
2.5 En ese caso, limita los cambios a correcciones menores de ortografia, puntuacion, gramatica, sintaxis y formato. No lo conviertas en prosa ni en un resumen narrativo.
2.6 Conserva preguntas, opciones, orden y repeticiones relevantes. No respondas el cuestionario ni infieras respuestas correctas salvo que la entrada ya las incluya.
3. Si la entrada es un documento extenso, sintetizalo en una nota-resumen autocontenida y concisa en lugar de copiarlo casi entero.
4. Extrae conceptos clave con definiciones breves basadas solo en la nota.
5. Extrae terminos relacionados que ayuden a clasificar y recuperar la nota.
6. Clasifica el texto en exactamente uno de estos tipos: cuestionario, problema_enunciado, procedimental, narrativo, lirico, descriptivo, informativo, formal o nota_libre.
7. Ajusta la edicion segun el tipo detectado.
7.1 cuestionario: conserva preguntas, opciones, orden y formato.
7.2 problema_enunciado: conserva el enunciado, los datos, las restricciones, las variables y los pasos relevantes para resolverlo, sin convertirlo en ensayo.
7.3 procedimental: conserva la secuencia de pasos, comandos, listas y advertencias.
7.4 narrativo: mejora claridad, continuidad y puntuacion sin borrar la voz ni la cronologia.
7.5 lirico: conserva versos, saltos de linea, ritmo e imagenes centrales; solo corrige lo imprescindible.
7.6 descriptivo: conserva rasgos, cualidades, atributos y relaciones espaciales o sensoriales.
7.7 informativo: prioriza definiciones, hechos, hallazgos, tesis y estructura expositiva.
7.8 formal: conserva el registro institucional, la cortesia y la estructura del mensaje.
7.9 nota_libre: deja la nota clara sin forzar una estructura que no esta en la fuente.
8. No inventes datos externos ni agregues informacion que no pueda inferirse.

Responde exclusivamente con JSON valido en esta forma:
{
  "title": "...",
    "text_type": "...",
  "corrected_text": "...",
  "concepts": [
    {"term": "...", "definition": "..."}
  ],
  "related_terms": ["..."]
}"""

JSON_REPAIR_SYSTEM_PROMPT = """Corrige respuestas JSON malformadas para dejarlas como JSON valido.
Debes responder exclusivamente con un objeto JSON valido con esta forma:
{
    "title": "...",
    "text_type": "...",
    "corrected_text": "...",
    "concepts": [
        {"term": "...", "definition": "..."}
    ],
    "related_terms": ["..."]
}
No agregues explicaciones, Markdown ni texto fuera del JSON."""


def _is_document_source(source_type: str) -> bool:
    return "document" in source_type.casefold()


QUESTION_OPTION_RE = re.compile(r"^\s*(?:[◯○●•\-*]\s*)?[a-zA-Z][\.)]\s+")
FORMAL_OPENING_MARKERS = (
    "estimado",
    "estimada",
    "cordial saludo",
    "por medio de la presente",
    "a quien corresponda",
    "señor",
    "senor",
)
FORMAL_CLOSING_MARKERS = (
    "atentamente",
    "cordialmente",
    "saludos cordiales",
    "quedo atento",
    "quedo atenta",
)
PROCEDURAL_MARKERS = (
    "paso ",
    "primero",
    "segundo",
    "tercero",
    "despues",
    "luego",
    "finalmente",
    "instala",
    "configura",
    "ejecuta",
)
PROBLEM_MARKERS = (
    "problema",
    "enunciado",
    "resuelve",
    "demuestra",
    "calcula",
    "determina",
    "encuentra",
    "datos:",
    "solucion",
)
NARRATIVE_MARKERS = (
    "entonces",
    "despues",
    "luego",
    "de pronto",
    "al final",
    "un dia",
    "cuando",
    "mientras",
)
LYRICAL_MARKERS = (
    "alma",
    "noche",
    "silencio",
    "viento",
    "sombra",
    "amor",
    "piel",
    "lluvia",
    "eco",
)
DESCRIPTIVE_MARKERS = (
    "se caracteriza",
    "presenta",
    "tiene",
    "consiste en",
    "esta compuesto",
    "esta formada",
    "apariencia",
    "textura",
    "color",
    "forma",
)
TEXT_TYPE_CATALOG = {
    "cuestionario": "Conserva preguntas, opciones y estructura original.",
    "problema_enunciado": "Conserva el enunciado, los datos, las variables y las restricciones sin volverlo ensayo.",
    "procedimental": "Conserva la secuencia de pasos, comandos, listas y advertencias.",
    "narrativo": "Preserva voz, secuencia temporal y continuidad del relato.",
    "lirico": "Preserva versos, saltos de linea e imagenes centrales.",
    "descriptivo": "Preserva atributos, cualidades y relaciones sensoriales o espaciales.",
    "informativo": "Prioriza definiciones, hechos, tesis y estructura expositiva.",
    "formal": "Mantiene registro institucional, cortesia y estructura de mensaje formal.",
    "nota_libre": "Aclara el texto sin imponer una estructura ajena.",
}


def _questionnaire_stats(text: str) -> tuple[int, int]:
    question_count = 0
    option_count = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if QUESTION_OPTION_RE.match(line):
            option_count += 1
            continue
        if "?" in line and len(line) >= 12:
            question_count += 1
    return question_count, option_count


def _looks_like_questionnaire(text: str) -> bool:
    question_count, option_count = _questionnaire_stats(text)
    return question_count >= 2 and option_count >= 4 and option_count >= question_count * 2


def _count_marker_hits(text: str, markers: tuple[str, ...]) -> int:
    lowered = text.casefold()
    return sum(1 for marker in markers if marker in lowered)


def _nonempty_lines(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return [line.strip() for line in normalized.split("\n") if line.strip()]


def _looks_like_formal_text(text: str) -> bool:
    lines = _nonempty_lines(text)
    if not lines:
        return False
    opening = " ".join(lines[:3]).casefold()
    closing = " ".join(lines[-3:]).casefold()
    return any(marker in opening for marker in FORMAL_OPENING_MARKERS) or any(marker in closing for marker in FORMAL_CLOSING_MARKERS)


def _looks_like_problem_statement(text: str) -> bool:
    marker_hits = _count_marker_hits(text, PROBLEM_MARKERS)
    numeric_density = len(re.findall(r"\d", text))
    return marker_hits >= 2 or (marker_hits >= 1 and numeric_density >= 3)


def _looks_like_procedural(text: str) -> bool:
    lines = _nonempty_lines(text)
    step_lines = sum(1 for line in lines if re.match(r"^(?:paso\s*\d+[:\.)]?|\d+[\.)]|[-*])\s+", line.casefold()))
    marker_hits = _count_marker_hits(text, PROCEDURAL_MARKERS)
    return step_lines >= 2 or (marker_hits >= 3 and len(lines) >= 3)


def _looks_like_lyrical(text: str) -> bool:
    lines = _nonempty_lines(text)
    if len(lines) < 4:
        return False
    short_lines = sum(1 for line in lines if len(line) <= 55)
    marker_hits = _count_marker_hits(text, LYRICAL_MARKERS)
    return short_lines >= max(3, int(len(lines) * 0.6)) and marker_hits >= 1


def _looks_like_narrative(text: str) -> bool:
    lowered = text.casefold()
    marker_hits = _count_marker_hits(lowered, NARRATIVE_MARKERS)
    past_verbs = len(re.findall(r"\b(?:fue|era|estaba|llegue|llego|dije|dijo|vi|vio|pense|penso|senti|sintio)\b", lowered))
    return marker_hits >= 2 or (marker_hits >= 1 and past_verbs >= 2)


def _looks_like_descriptive(text: str) -> bool:
    marker_hits = _count_marker_hits(text, DESCRIPTIVE_MARKERS)
    commas = text.count(",")
    return marker_hits >= 2 or (marker_hits >= 1 and commas >= 2)


def _detect_text_type(raw_text: str, source_type: str = "telegram_audio") -> str:
    text = raw_text.strip()
    if not text:
        return "nota_libre"
    if _looks_like_questionnaire(text):
        return "cuestionario"
    if _looks_like_formal_text(text):
        return "formal"
    if _looks_like_problem_statement(text):
        return "problema_enunciado"
    if _looks_like_procedural(text):
        return "procedimental"
    if _looks_like_lyrical(text):
        return "lirico"
    if _looks_like_narrative(text):
        return "narrativo"
    if _looks_like_descriptive(text):
        return "descriptivo"
    if _is_document_source(source_type):
        return "informativo"
    if len(_nonempty_lines(text)) >= 3 and len(text) >= 180:
        return "informativo"
    return "nota_libre"


def _normalize_text_type(value: Any, raw_text: str, source_type: str) -> str:
    candidate = re.sub(r"[^a-z_]+", "_", str(value or "").strip().casefold()).strip("_")
    if candidate in TEXT_TYPE_CATALOG:
        return candidate
    return _detect_text_type(raw_text, source_type)


def _build_text_type_instruction(raw_text: str, source_type: str) -> str:
    probable_text_type = _detect_text_type(raw_text, source_type)
    return (
        "Clasifica la entrada en el campo text_type usando solo este catalogo cerrado: "
        f"{', '.join(TEXT_TYPE_CATALOG)}.\n"
        f"Tipo textual probable: {probable_text_type}.\n"
        f"Tratamiento editorial sugerido para ese tipo: {TEXT_TYPE_CATALOG[probable_text_type]}\n\n"
    )


def _preserve_structured_text(text: str) -> str:
    lines: list[str] = []
    blank_run = 0
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            blank_run += 1
            if blank_run <= 1:
                lines.append("")
            continue
        blank_run = 0
        lines.append(line)
    return "\n".join(lines).strip()


def _questionnaire_structure_preserved(raw_text: str, candidate_text: str) -> bool:
    raw_questions, raw_options = _questionnaire_stats(raw_text)
    candidate_questions, candidate_options = _questionnaire_stats(candidate_text)
    if candidate_questions < max(2, int(raw_questions * 0.7)):
        return False
    if candidate_options < max(4, int(raw_options * 0.7)):
        return False
    return len(candidate_text.strip()) >= max(120, int(len(raw_text.strip()) * 0.65))


def _build_analysis_request(raw_text: str, source_type: str) -> str:
    text_type_instruction = _build_text_type_instruction(raw_text, source_type)
    if _looks_like_questionnaire(raw_text):
        return (
            "Analiza este cuestionario o nota estructurada y devuelve solo el JSON solicitado.\n\n"
            f"{text_type_instruction}"
            "El campo corrected_text debe conservar la estructura original del cuestionario: preguntas, opciones, orden, "
            "saltos de linea y repeticiones relevantes. Solo aplica correcciones menores de ortografia, puntuacion, "
            "gramatica, sintaxis y formato. No respondas el cuestionario, no lo resumas y no lo conviertas en prosa.\n\n"
            f"TEXTO:\n{raw_text}"
        )

    if _is_document_source(source_type):
        return (
            "Analiza este documento y devuelve solo el JSON solicitado.\n\n"
            f"{text_type_instruction}"
            "El campo corrected_text debe ser una nota-resumen clara, sintetica y autocontenida, "
            "no una copia extensa del documento. Apunta normalmente a unas 350-600 palabras o "
            "alrededor de 3 minutos de lectura, salvo que el contenido pida menos. Prioriza tesis, "
            "hallazgos, argumentos, decisiones y conclusiones utiles.\n\n"
            f"DOCUMENTO:\n{raw_text}"
        )

    return (
        "Analiza esta transcripcion o nota y devuelve solo el JSON solicitado.\n\n"
        f"{text_type_instruction}"
        f"TEXTO:\n{raw_text}"
    )


def _build_pdf_analysis_request(source_type: str) -> str:
    if _is_document_source(source_type):
        return (
            "Analiza este PDF y devuelve solo el JSON solicitado. "
            "El campo corrected_text debe ser una nota-resumen clara, sintetica y autocontenida, "
            "no una copia extensa del documento. Apunta normalmente a unas 350-600 palabras o "
            "alrededor de 3 minutos de lectura, salvo que el contenido pida menos. "
            "Usa el contenido textual y visual del PDF si aporta contexto."
        )
    return "Analiza este PDF y devuelve solo el JSON solicitado."


def _build_json_repair_request(raw_text: str, source_type: str, invalid_content: str) -> str:
    source_label = "DOCUMENTO" if _is_document_source(source_type) else "TEXTO"
    return (
        "La respuesta previa del modelo no fue JSON valido. Reconstruye el resultado final y devuelve solo JSON valido.\n\n"
        f"{_build_text_type_instruction(raw_text, source_type)}"
        "RESPUESTA_PREVIA_INVALIDA:\n"
        f"{invalid_content}\n\n"
        f"{source_label}_FUENTE:\n{raw_text}"
    )


def _extract_json(content: str) -> dict[str, Any]:
    text = content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.S | re.I)
    if fenced:
        text = fenced.group(1).strip()

    try:
        data = json.loads(text, strict=False)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"La respuesta de Azure OpenAI no fue JSON valido: {exc}") from exc

    if not isinstance(data, dict):
        raise RuntimeError("La respuesta de Azure OpenAI no devolvio un objeto JSON.")
    return data


def _clean_text(value: Any, fallback: str = "") -> str:
    text = str(value if value is not None else "").strip()
    return text or fallback


def _build_fallback_title(text: str) -> str:
    normalized = " ".join(text.split())
    if not normalized:
        return "Nota"
    return normalized[:60].rstrip(" ,.;:") or "Nota"


def _normalize_concepts(raw_concepts: Any) -> list[dict[str, str]]:
    if not isinstance(raw_concepts, list):
        return []

    concepts: list[dict[str, str]] = []
    seen_terms: set[str] = set()
    for item in raw_concepts:
        if not isinstance(item, dict):
            continue
        term = _clean_text(item.get("term"))
        if not term:
            continue
        key = term.casefold()
        if key in seen_terms:
            continue
        seen_terms.add(key)
        concepts.append(
            {
                "term": term[:80],
                "definition": _clean_text(item.get("definition"), "Sin definicion.")[:300],
            }
        )
        if len(concepts) >= 12:
            break
    return concepts


def _normalize_related_terms(raw_terms: Any) -> list[str]:
    if not isinstance(raw_terms, list):
        return []

    terms: list[str] = []
    seen_terms: set[str] = set()
    for item in raw_terms:
        term = _clean_text(item)[:60]
        if not term:
            continue
        key = term.casefold()
        if key in seen_terms:
            continue
        seen_terms.add(key)
        terms.append(term)
        if len(terms) >= 20:
            break
    return terms


def _normalize_analysis(data: dict[str, Any], raw_text: str, source_audio: str = "", source_type: str = "telegram_audio") -> dict[str, Any]:
    title = _clean_text(data.get("title"), _build_fallback_title(raw_text))
    text_type = _normalize_text_type(data.get("text_type"), raw_text, source_type)
    corrected_text = _clean_text(data.get("corrected_text"), raw_text)
    if _looks_like_questionnaire(raw_text):
        preserved_raw_text = _preserve_structured_text(raw_text)
        candidate_text = _preserve_structured_text(corrected_text)
        corrected_text = (
            candidate_text
            if _questionnaire_structure_preserved(preserved_raw_text, candidate_text)
            else preserved_raw_text
        )

    return {
        "title": title[:100],
        "text_type": text_type,
        "corrected_text": corrected_text,
        "concepts": _normalize_concepts(data.get("concepts")),
        "related_terms": _normalize_related_terms(data.get("related_terms")),
        "raw_transcript": raw_text,
        "source_audio": source_audio,
        "source_type": source_type,
        "analyzer": "azure_openai",
    }


def _can_send_pdf_directly(settings: Settings, source_audio: str, source_type: str) -> bool:
    if not _is_document_source(source_type):
        return False
    if not source_audio:
        return False
    if not uses_openai_v1_endpoint(settings.azure_openai_endpoint):
        return False
    path = Path(source_audio)
    return path.exists() and path.suffix.lower() == ".pdf"


def analyze_text(
    text: str,
    source_audio: str = "",
    settings: Settings | None = None,
    source_type: str = "telegram_audio",
) -> dict[str, Any]:
    settings = settings or load_settings()
    raw_text = text.strip()
    if not raw_text:
        raise RuntimeError("No hay texto para analizar.")
    prompt_text = _build_analysis_request(raw_text, source_type)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": prompt_text,
        },
    ]

    content = ""
    if _can_send_pdf_directly(settings, source_audio, source_type):
        try:
            content = invoke_chat(
                settings,
                [{"role": "system", "content": SYSTEM_PROMPT}],
                max_tokens=llm_max_output_tokens(settings),
                temperature=0.2,
                response_format_json=True,
                input_override=build_pdf_input_message(source_audio, _build_pdf_analysis_request(source_type)),
            )
        except RuntimeError:
            content = ""

    if not content:
        content = invoke_chat(
            settings,
            messages,
            max_tokens=llm_max_output_tokens(settings),
            temperature=0.2,
            response_format_json=True,
        )
    try:
        data = _extract_json(content)
    except RuntimeError:
        repair_messages = [
            {"role": "system", "content": JSON_REPAIR_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _build_json_repair_request(raw_text, source_type, content),
            },
        ]
        repaired_content = invoke_chat(
            settings,
            repair_messages,
            max_tokens=llm_max_output_tokens(settings),
            temperature=0,
            response_format_json=True,
        )
        data = _extract_json(repaired_content)

    return _normalize_analysis(data, raw_text, source_audio, source_type)
