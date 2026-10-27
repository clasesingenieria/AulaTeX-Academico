"""Investigación conceptual y extracción documental con el cliente real de AulaTeX.

Solo envía al motor fuentes académicas públicas del corpus declarado. Las
credenciales se cargan dentro de AulaTeX y nunca se escriben en los artefactos.
No usa el adaptador TF-IDF como sustituto de una extracción semántica con Nova.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import types
from datetime import datetime, timezone
from dataclasses import replace
from pathlib import Path

SUBJECT = Path(__file__).resolve().parents[1]
ROOT = SUBJECT.parents[2]
NOTES = SUBJECT / "referencias-estadistica-aplicada-para-la-administracion/notas-estadistica-aplicada-para-la-administracion/unidad-1-muestreo"
KNOWLEDGE = SUBJECT / "investigacion-aulatex"
EXTRACTION = SUBJECT / "extractor-aulatex/conceptos-estadistica-unidad-1-nova"
PUBLIC_SOURCES = {
    "holmesMuestreo2023": ("holmesMuestreo2023.txt", "Holmes, Illowsky y Dean (2023), Introductory Business Statistics 2e, sección 1.2", "https://openstax.org/books/introductory-business-statistics-2e/pages/1-2-data-sampling-and-variation-in-data-and-sampling", None),
    "holmesProporcion2023": ("holmesProporcion2023.txt", "Holmes, Illowsky y Dean (2023), Introductory Business Statistics 2e, sección 8.3", "https://openstax.org/books/introductory-business-statistics-2e/pages/8-3-a-confidence-interval-for-a-population-proportion", None),
    "nistTamano": ("nistTamano.txt", "NIST/SEMATECH, e-Handbook, sección 7.2.4.2", "https://www.itl.nist.gov/div898/handbook/prc/section2/prc242.htm", None),
    "bradley2021": ("bradley2021.txt", "Bradley et al. (2021), Nature 600, 695-700, DOI 10.1038/s41586-021-04198-4", "https://www.nature.com/articles/s41586-021-04198-4", (46, 450)),
    "barrero2023": ("barrero2023.txt", "Barrero, Bloom y Davis (2023), Journal of Economic Perspectives 37(4), 23-50, DOI 10.1257/jep.37.4.23", "https://www.aeaweb.org/articles?id=10.1257/jep.37.4.23", (1, 170)),
    "bloom2024": ("bloom2024.txt", "Bloom, Han y Liang (2024), Nature 630, 920-925, DOI 10.1038/s41586-024-07500-2", "https://www.nature.com/articles/s41586-024-07500-2", (53, 674)),
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_json(text: str) -> dict:
    stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    payload = json.loads(stripped)
    if not isinstance(payload, dict):
        raise ValueError("La salida Nova debe ser un objeto JSON")
    return payload


def corpus(allowed=None) -> tuple[str, list[dict]]:
    chunks, inventory = [], []
    for key, (filename, title, url, limits) in PUBLIC_SOURCES.items():
        if allowed is not None and key not in allowed:
            continue
        path = NOTES / filename
        lines = path.read_text(encoding="utf-8").splitlines()
        selected, previous = [], None
        for number, line in enumerate(lines, 1):
            if limits and not limits[0] <= number <= limits[1]:
                continue
            # El PDF JEP tiene una capa textual duplicada. Conservamos los
            # localizadores del original al deduplicar únicamente líneas vecinas.
            if not line.strip() or line.strip() == previous:
                continue
            previous = line.strip()
            selected.append(f"[{key}:L{number}] {line}")
        chunks.append(f"\nFUENTE {key}: {title}\nURL: {url}\n" + "\n".join(selected))
        inventory.append({"id": key, "title": title, "url": url,
                          "text_path": path.relative_to(SUBJECT).as_posix(),
                          "sha256": sha(path), "original_lines": len(lines),
                          "included_line_range": list(limits) if limits else [1, len(lines)],
                          "locator_format": f"{key}:L<línea original>",
                          "deduplication": "solo líneas vacías y duplicados consecutivos"})
    return "\n\n".join(chunks), inventory


def call_stage(client, stage: str, prompt: str, destination: Path) -> tuple[dict, dict]:
    destination.mkdir(parents=True, exist_ok=True)
    previous_prompt = destination / f"{stage}-prompt.txt"
    previous_metadata = destination / f"{stage}-metadata.json"
    previous_payload = destination / f"{stage}.json"
    if previous_prompt.exists() and previous_metadata.exists() and previous_payload.exists():
        metadata = json.loads(previous_metadata.read_text(encoding="utf-8"))
        if metadata.get("ok") and previous_prompt.read_text(encoding="utf-8") == prompt:
            print(f"Reutilizando respuesta real ya conservada: {stage}", flush=True)
            return json.loads(previous_payload.read_text(encoding="utf-8")), metadata
    (destination / f"{stage}-prompt.txt").write_text(prompt, encoding="utf-8")
    started = datetime.now(timezone.utc).isoformat()
    result = client.call("Amazon Nova Pro", prompt, max_tokens=8000, timeout_seconds=300)
    metadata = {"stage": stage, "started_at_utc": started,
                "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                "engine": result.engine, "ok": result.ok,
                "requested_deployment": result.requested_deployment,
                "provider_model": result.provider_model,
                "finish_reason": result.finish_reason, "usage": result.usage,
                "transport": "AulaTeXLLMClient.call", "fallback_permitted": False,
                "effective_timeout_seconds": 300,
                "timeout_override_scope": "solo este proceso documental; .env sin cambios",
                "error_category": result.error.split(":")[0][:100] if not result.ok else ""}
    (destination / f"{stage}-metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    if not result.ok:
        # El error completo del proveedor podría incluir datos de conexión.
        raise RuntimeError(f"Nova falló en {stage}; revisar conexión sin registrar credenciales")
    (destination / f"{stage}-respuesta-original.txt").write_text(result.text, encoding="utf-8")
    payload = parse_json(result.text)
    (destination / f"{stage}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=True), flush=True)
    return payload, metadata


def render_conceptual(payload: dict) -> str:
    lines = ["# Base conceptual ampliada de muestreo", "",
             "Asistencia documental real: Amazon Nova Pro, mediante AulaTeXLLMClient. Las autoridades son las fuentes académicas identificadas; la salida del motor requiere cotejo editorial.", ""]
    for block in payload.get("secciones", []):
        lines.extend([f"## {block.get('titulo', '')}", "", block.get("contenido", ""), ""])
        for source in block.get("sustento", []):
            lines.append(f"- Sustento: {source}")
        lines.append("")
    lines.extend(["## Límites y decisiones editoriales", ""])
    lines.extend(f"- {x}" for x in payload.get("limites", []))
    return "\n".join(lines) + "\n"


def main():
    os.environ["AULATEX_REQUIRED_ENGINE"] = "Amazon Nova Pro"
    os.environ["AULATEX_MODEL_ROUTER_ONLY"] = "0"
    sys.path.insert(0, str(ROOT / "aulaTEX"))
    # __init__.py carga también UI, monitores y dependencias de entrenamiento.
    # Para este ejecutor documental cargamos el módulo público real y sus
    # imports relativos sin inicializar esos subsistemas ajenos al cliente.
    if "aulatex" not in sys.modules:
        package = types.ModuleType("aulatex")
        package.__path__ = [str(ROOT / "aulaTEX/aulatex")]
        sys.modules["aulatex"] = package
    from aulatex.llm_bridge import AulaTeXLLMClient, AulaTeXLLMConfig
    # La configuración local fija 45 s y from_env vuelve a cargar ese límite en
    # cada llamada. Se conserva la configuración real completa; únicamente el
    # timeout de este proceso se amplía para análisis documentales extensos.
    configured_from_env = AulaTeXLLMConfig.from_env
    def documentary_config(cls, engine_label=None):
        configured = configured_from_env(engine_label)
        return replace(configured, timeout_seconds=300) if configured is not None else None
    AulaTeXLLMConfig.from_env = classmethod(documentary_config)

    source_text, inventory = corpus()
    KNOWLEDGE.mkdir(parents=True, exist_ok=True)
    EXTRACTION.mkdir(parents=True, exist_ok=True)
    run = KNOWLEDGE / "nova-pro-unidad-1-2026-10-24-r3"
    run.mkdir(parents=True, exist_ok=True)
    (run / "corpus-localizado.txt").write_text(source_text, encoding="utf-8")
    (run / "inventario-fuentes.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    client = AulaTeXLLMClient()
    print("Corpus académico localizado; iniciando investigación conceptual Nova Pro", flush=True)
    conceptual_prompt = """Eres el investigador conceptual documental de AulaTeX. Elabora una base AMPLIA en español para Estadística aplicada a la administración, unidad Muestreo. No redactes la entrega breve todavía. Usa EXCLUSIVAMENTE las fuentes públicas del corpus; el LLM no es autoridad. No inventes fuentes, fórmulas ni tamaños. Distingue afirmación documental de ejemplo administrativo hipotético y de inferencia comparativa. Cada sección debe identificar clave y localizadores exactos fuente:Lx-Ly. No copies párrafos; sintetiza y analiza.
Responde solo JSON válido: {"secciones":[{"titulo":"...","contenido":"varios párrafos amplios separados con \\n\\n","sustento":["fuente:Lx-Ly"]}],"limites":["..."]}.
Produce 10 a 12 secciones, al menos 2000 palabras totales, que cubran: población objetivo/accesible, unidad de análisis, parámetro/estadístico, marco muestral; muestreo probabilístico con probabilidades conocidas NO necesariamente iguales, aleatorio simple/estratificado/sistemático/conglomerados; no probabilístico/conveniencia y límites; precisión vs sesgo/representatividad, cobertura/no respuesta y ponderación; intervalo y tamaño de muestra para proporción, supuestos y ajuste por respuesta sin prometer ausencia de sesgo; potencia/efecto y por qué NIST no equivale a fórmula de precisión; inferencia descriptiva y causal y límites; comparación y transferencia a decisiones administrativas y mercado; síntesis interpretativa que conecte evidencia y decisiones verificables. Debe servir también para sustentar una infografía de tipos de muestreo. Incluye cautelas sobre porcentajes/puntos porcentuales y supuestos. Los tres estudios empíricos se extraerán en una fase posterior; no describas detalles que no estén en este corpus conceptual.
CORPUS CON LOCALIZADORES:\n""" + corpus({"holmesMuestreo2023", "holmesProporcion2023", "nistTamano"})[0]
    conceptual, conceptual_meta = call_stage(client, "investigacion-conceptual", conceptual_prompt, run)
    (KNOWLEDGE / "base-conceptual-unidad-1-nova.json").write_text(json.dumps(conceptual, ensure_ascii=False, indent=2), encoding="utf-8")
    (KNOWLEDGE / "base-conceptual-unidad-1-nova.md").write_text(render_conceptual(conceptual), encoding="utf-8")
    canonical = {"scope_profile": ["Estadística aplicada a la administración: muestreo, unidad 1"],
                 "local_inventory": inventory, "sources": [x[2] for x in PUBLIC_SOURCES.values()],
                 "bibliography_notes": ["Fuentes formales existentes verificadas: Holmes 2023, NIST/SEMATECH, Bradley 2021, Barrero 2023 y Bloom 2024; no se agregan referencias autogeneradas."],
                 "conceptual_sections": conceptual.get("secciones", []),
                 "open_questions": conceptual.get("limites", []),
                 "source_role": "Nova asiste investigación; no constituye autoridad académica"}
    (KNOWLEDGE / "base-conocimiento.json").write_text(json.dumps(canonical, ensure_ascii=False, indent=2), encoding="utf-8")
    (KNOWLEDGE / "base-conocimiento.md").write_text(render_conceptual(conceptual), encoding="utf-8")
    (KNOWLEDGE / "fuentes-web.md").write_text("# Fuentes primarias y editoriales verificadas\n\n" + "\n".join(f"- {x['title']}: {x['url']}" for x in inventory) + "\n\nLos textos completos públicos ya estaban preservados en el corpus; esta corrida no afirma nuevas descargas. Los hashes y localizadores permiten cotejar cada extracción.\n", encoding="utf-8")

    extraction_prompt = """Eres extractor documental de AulaTeX usando Nova Pro. Extrae únicamente lo sustentado por el corpus público; no redactes supuestos como hechos. Devuelve solo JSON válido con:
{"fichas_conceptos":[{"id":"c01","concepto":"...","definicion_sintetica":"...","fuentes":[{"id":"fuente","localizador":"Lx-Ly"}],"aplicacion_administrativa_hipotetica":"...","limite":"..."}],"conceptos_detectados":["..."],"ideas_detectadas":[{"id":"i01","idea":"...","tipo":"hallazgo documental o inferencia comparativa o ejemplo hipotético","fuentes":[{"id":"fuente","localizador":"Lx-Ly"}]}],"articulos":[{"id":"...","titulo":"...","autores":"...","publicacion_anio":"...","poblacion_y_marco":"...","seleccion_muestreo":"...","tamano_y_disenio":"...","resultado_y_denominador":"...","uso_administrativo":"...","limites":"...","localizadores":["fuente:Lx-Ly"]}],"trazabilidad_fuentes":[{"id":"...","conceptos_o_resultados_sustentados":["..."],"localizadores":["fuente:Lx-Ly"]}],"alertas":["..."]}.
Al menos 20 fichas conceptuales, 12 ideas y exactamente 3 artículos (Bradley, Barrero y Bloom). Extrae diseños probabilísticos/no probabilísticos y sus diferencias, unidad/parámetro/marco, error aleatorio/sesgo, ponderación, precisión/potencia, validez causal/externa. Para cada artículo registra título/autores/revista/año, resumen aplicación del muestreo, conclusiones propias limitadas. Asegura Bradley 17/14 puntos porcentuales, Barrero 28% de días remunerados y no de empleados, Bloom 1612/792/820, 7.2% a 4.8% equivalente 2.4 puntos y reducción relativa de 1/3, sin confundir selección de empresas con asignación aleatoria. No conviertas ausencia de significación en prueba de igualdad. Valida localizadores contra etiquetas del corpus.
CORPUS CON LOCALIZADORES:\n""" + source_text
    extraction, extraction_meta = call_stage(client, "extraccion-documental", extraction_prompt, run)
    for name in ("fichas_conceptos", "conceptos_detectados", "ideas_detectadas", "trazabilidad_fuentes", "articulos", "alertas"):
        (EXTRACTION / f"{name}.json").write_text(json.dumps(extraction.get(name, []), ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {"created_at_utc": datetime.now(timezone.utc).isoformat(),
                "scope": "Estadística aplicada para la administración, unidad 1, actividades 1 y 2",
                "workflow": ["memoria y contratos locales consultados", "investigación conceptual amplia", "extracción semántica documental", "cotejo editorial y redacción", "compilación y QA visual"],
                "engine_required": "Amazon Nova Pro", "real_llm_calls": [conceptual_meta, extraction_meta],
                "sources": inventory, "human_review_claimed": False,
                "note": "No se ejecutó el extractor CLI TF-IDF: no admite Nova. Orquestación dedicada con cliente público AulaTeX, salidas originales y localizadores conservados.",
                "raw_run": run.relative_to(SUBJECT).as_posix(), "platform_submission": False}
    (KNOWLEDGE / "manifest-nova-unidad-1.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (EXTRACTION / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Investigación y extracción Nova Pro finalizadas", flush=True)


if __name__ == "__main__":
    main()
