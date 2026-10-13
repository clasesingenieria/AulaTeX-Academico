"""Consolidador de construcción TikZ/LaTeX + rúbrica por técnica (N ciclos).

Objetivo (petición del usuario): consolidar/contractualizar CÓMO AulaTeX construye
las actividades de cada técnica usando TikZ/LaTeX e investigar las PUNTUACIONES de
los productos, para integrarlo con ``realizar-actividad``.

Por cada técnica corre hasta ``cycles`` ciclos que refinan tres bloques y se
detienen al converger (contenido estable entre ciclos):

- ``tikz_pattern``: patrón LaTeX/TikZ de referencia (de su familia) + reglas.
- ``scoring_rubric``: criterios de puntuación del producto, derivados de las
  secciones oficiales (``build_steps``/``caveats``) ya scrapeadas y de la
  estructura de calidad del optimizador (activity_optimizer).
- ``realizar_actividad_integration``: instrucciones para el motor sobre cómo
  materializar el producto en el flujo realizar-actividad (dónde va, protagonismo,
  compilación).

Motor: DETERMINISTA por defecto (fuentes oficiales + repo + plantillas), sin
dependencias LLM. Si en el futuro se pasa un ``llm_refiner`` invocable, se usa para
pulir los snippets; si falla, degrada al determinista. Reproducible y sin costo.

Escribe ``aulaTEX/base/.../100tecnicas-construccion.json`` que ``didactic_catalog`` superpone
como ``construction_contract`` en cada técnica.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Optional

try:  # como parte del paquete
    from .didactic_catalog import TECHNIQUE_CONTRACTS
    from .didactic_tikz_patterns import pattern_for_family
except ImportError:  # ejecución directa
    import importlib.util as _ilu

    _HERE = Path(__file__).resolve().parent

    def _load(name: str):
        spec = _ilu.spec_from_file_location(name, _HERE / f"{name}.py")
        mod = _ilu.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        return mod

    TECHNIQUE_CONTRACTS = _load("didactic_catalog").TECHNIQUE_CONTRACTS
    pattern_for_family = _load("didactic_tikz_patterns").pattern_for_family

REPO_ROOT = Path(__file__).resolve().parents[2]
CONSTRUCTION_PATH = (
    REPO_ROOT / "aulaTEX/base" / "latex" / "adaptadas" / "materias"
    / "tecnicas-didacticas-aprendizaje" / "100tecnicas-construccion.json"
)

# Motores LLM confiables con prompts largos (ver memoria del repo: SOL falla).
_DEFAULT_LLM_ENGINES = ("GPT-5.6-Luna", "GPT-5.6-Terra")

# Componentes de puntuación base (alineados con activity_optimizer._quality_breakdown).
_BASE_SCORE_COMPONENTS = {
    "citas_apa": {"peso": 25, "criterio": "Citas APA 7 visibles y suficientes que sustentan el producto (mín. 3)."},
    "estructura_tres_actos": {"peso": 20, "criterio": "Tres actos: introducción (problema), desarrollo temático con el producto como núcleo, conclusión con postura."},
    "producto_protagonico": {"peso": 20, "criterio": "El producto de la técnica es el núcleo del desarrollo; el texto lo prepara antes y lo interpreta después."},
    "base_conceptual": {"peso": 15, "criterio": "Conceptos clave delimitados (\\textbf/\\textit) y cobertura de los subtemas de la planeación."},
    "conectores_prosa": {"peso": 10, "criterio": "Prosa con conectores lógicos; introducción y conclusión sin listas."},
    "integridad_postura": {"peso": 10, "criterio": "Postura propia (posición, razón, consecuencia) y declaración de IA como \\footnote."},
}


def _bullets_from_official(text: str, limit: int = 10) -> list[str]:
    """Extrae pasos/criterios de una sección oficial (numerados o con guiones)."""
    if not text:
        return []
    text = re.sub(r"\s+", " ", text).strip()
    items: list[str] = []
    # 1) Preferir separación por numeración "N. " (pasos: 1. ... 2. ...).
    num_positions = [m.start() for m in re.finditer(r"(?<!\d)\d{1,2}\.\s", text)]
    if len(num_positions) >= 2:
        num_positions.append(len(text))
        for i in range(len(num_positions) - 1):
            seg = text[num_positions[i]:num_positions[i + 1]]
            seg = re.sub(r"^\d{1,2}\.\s*", "", seg).strip()
            if 8 <= len(seg) <= 260:
                items.append(seg)
            if len(items) >= limit:
                break
        if items:
            return items
    # 2) Fallback: separar por viñetas o por oraciones.
    for seg in re.split(r"\n-\s|\s-\s(?=[A-ZÁÉÍÓÚ])|(?<=[.;])\s+", text):
        seg = seg.strip()
        if 12 <= len(seg) <= 260:
            items.append(seg)
        if len(items) >= limit:
            break
    return items


def build_scoring_rubric(tech_id: str, contract: dict[str, Any]) -> dict[str, Any]:
    """Construye la rúbrica de puntuación del producto de una técnica."""
    official = contract.get("official_contract", {})
    build_steps = official.get("build_steps") or contract.get("build_steps", "")
    caveats = official.get("caveats", "")

    build_criteria = _bullets_from_official(build_steps)
    caveat_criteria = _bullets_from_official(caveats)

    # Peso total 100: 60 estructura editorial base + 40 fidelidad al producto oficial.
    rubric = {
        "escala": "0-100",
        "componentes_editoriales": _BASE_SCORE_COMPONENTS,
        "criterios_de_construccion_oficial": [
            {"criterio": c, "peso": round(25 / max(1, len(build_criteria)), 2)}
            for c in build_criteria
        ] or [{"criterio": f"Materializar «{contract['nombre_oficial']}» conforme a su estructura oficial.", "peso": 25}],
        "consideraciones_para_puntuar": caveat_criteria or ["Evitar producto esquelético o decorativo; debe evidenciar decisión intelectual."],
        "umbral_aprobacion": 100,
        "nota": "El producto puntúa por fidelidad a la técnica (forma oficial) + calidad editorial (tres actos, citas, postura).",
    }
    return rubric


def build_construction_block(tech_id: str, contract: dict[str, Any]) -> dict[str, Any]:
    """Ensambla el bloque de construcción (TikZ + rúbrica + integración) de una técnica."""
    family = contract.get("familia", "")
    pattern = pattern_for_family(family)
    official = contract.get("official_contract", {})

    block: dict[str, Any] = {
        "tecnica": contract.get("nombre_oficial", tech_id),
        "catalogo_no": contract.get("catalogo_no"),
        "nivel": contract.get("nivel", ""),
        "familia": family,
        "tikz_pattern": {
            "packages": pattern.get("packages", []),
            "skeleton": pattern.get("skeleton", ""),
            "rules": pattern.get("rules", ""),
            "materializacion": contract.get("materialization", ""),
        },
        "scoring_rubric": build_scoring_rubric(tech_id, contract),
        "realizar_actividad_integration": {
            "deteccion": f"Aliases: {', '.join(contract.get('aliases', ()))}.",
            "producto_nucleo": contract.get("three_act_gravity_rule")
            or "El producto es el núcleo del desarrollo: prepararlo antes e interpretarlo después.",
            "estructura": contract.get("structure_rule", ""),
            "layout": contract.get("layout_rule", ""),
            "cierre": contract.get("closure_rule", ""),
            "preservacion_oficial": contract.get("preservation_rule_official", ""),
            "pasos_construccion": official.get("build_steps", ""),
            "compilacion": "Compilar con latexmk -pdf -bibtex; verificar el producto renderizando a PNG con pdftoppm (no solo returncode).",
        },
    }
    return block


def _extract_json(text: str) -> Optional[dict[str, Any]]:
    """Extrae el primer objeto JSON de una respuesta LLM (tolerante a fences)."""
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    raw = fenced.group(1) if fenced else None
    if raw is None:
        start = text.find("{")
        end = text.rfind("}")
        raw = text[start:end + 1] if start != -1 and end > start else None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def _validate_skeleton(skeleton: str) -> bool:
    """Valida que el snippet LaTeX/TikZ sea razonable.

    Acepta dos formas: (a) con entornos ``\\begin/\\end`` balanceados (visuales,
    tablas, TikZ), o (b) prosa LaTeX con comandos ``\\section/\\subsection`` (familias
    escritas). En ambos casos exige llaves balanceadas y marcadores <...> conservados.
    """
    if not skeleton or len(skeleton) < 40:
        return False
    if skeleton.count("{") != skeleton.count("}"):
        return False
    begins = len(re.findall(r"\\begin\{", skeleton))
    ends = len(re.findall(r"\\end\{", skeleton))
    if begins != ends:
        return False
    has_environments = begins > 0
    has_prose_structure = bool(re.search(r"\\(section|subsection|paragraph)\b", skeleton))
    if not (has_environments or has_prose_structure):
        return False
    # Debe conservar marcadores <...> para que el motor sustituya contenido.
    return "<" in skeleton and ">" in skeleton


def make_llm_refiner(
    engines: tuple[str, ...] = _DEFAULT_LLM_ENGINES,
    *,
    timeout_seconds: int = 120,
    max_tokens: int = 4000,
) -> Callable[[str, dict[str, Any], int], dict[str, Any]]:
    """Crea un refinador LLM que mejora el snippet TikZ y afina la rúbrica.

    Usa el bridge directo (aulaTEX/aulatex/llm_bridge.py, solo requests). Si el
    LLM no está disponible o devuelve algo inválido, retorna el bloque sin tocar
    (degradación a determinista). Idempotente por convergencia.
    """
    try:
        from .llm_bridge import AulaTeXLLMClient
    except ImportError:  # ejecución directa: cargar el subárbol aulatex.* por ruta
        import importlib.util as _ilu
        import sys as _sys
        import types as _types

        here = Path(__file__).resolve().parent
        # Registrar un paquete stub 'aulatex' apuntando a esta carpeta, de modo
        # que los imports relativos (from .config / from .llm_bridge) resuelvan
        # SIN ejecutar el __init__.py real (que importa langchain).
        if "aulatex" not in _sys.modules:
            pkg = _types.ModuleType("aulatex")
            pkg.__path__ = [str(here)]  # type: ignore[attr-defined]
            _sys.modules["aulatex"] = pkg

        def _load_submodule(name: str):
            full = f"aulatex.{name}"
            if full in _sys.modules:
                return _sys.modules[full]
            spec = _ilu.spec_from_file_location(full, here / f"{name}.py")
            mod = _ilu.module_from_spec(spec)
            assert spec and spec.loader
            _sys.modules[full] = mod
            spec.loader.exec_module(mod)
            return mod

        _load_submodule("config")
        AulaTeXLLMClient = _load_submodule("llm_bridge").AulaTeXLLMClient  # type: ignore[assignment]

    client = AulaTeXLLMClient()

    def refiner(tech_id: str, block: dict[str, Any], cycle: int) -> dict[str, Any]:
        tikz = block.get("tikz_pattern", {})
        prompt = (
            "Eres un experto en LaTeX/TikZ para documentos académicos UnADM. "
            f"Técnica: «{block.get('tecnica')}» (familia {block.get('familia')}, nivel {block.get('nivel')}).\n"
            "Mejora el SKELETON TikZ/LaTeX para que sea idiomático, compilable y específico del producto, "
            "CONSERVANDO los marcadores <...> (son placeholders que otro sistema sustituirá). "
            "No agregues \\documentclass ni \\begin{document}; solo el fragmento del producto.\n\n"
            f"SKELETON ACTUAL:\n{tikz.get('skeleton','')}\n\n"
            f"REGLAS DEL PRODUCTO:\n{tikz.get('rules','')}\n\n"
            "Responde SOLO un JSON con esta forma exacta: "
            '{"skeleton": "<latex mejorado con marcadores <...>>", "rules": "<reglas afinadas en 1-2 frases>", '
            '"scoring_hint": "<un criterio adicional para puntuar la fidelidad del producto>"}'
        )
        last_error = ""
        for engine in engines:
            result = client.call(engine, prompt, max_tokens=max_tokens, timeout_seconds=timeout_seconds)
            if not result.ok:
                last_error = result.error or "sin respuesta"
                continue
            data = _extract_json(result.text)
            if not data:
                last_error = "respuesta no-JSON"
                continue
            new_skeleton = str(data.get("skeleton", "")).strip()
            if _validate_skeleton(new_skeleton):
                block = dict(block)
                block["tikz_pattern"] = dict(tikz)
                block["tikz_pattern"]["skeleton"] = new_skeleton
                if data.get("rules"):
                    block["tikz_pattern"]["rules"] = str(data["rules"]).strip()
                block["tikz_pattern"]["llm_refined_by"] = engine
                if data.get("scoring_hint"):
                    rubric = dict(block.get("scoring_rubric", {}))
                    considers = list(rubric.get("consideraciones_para_puntuar", []))
                    hint = str(data["scoring_hint"]).strip()
                    if hint and hint not in considers:
                        considers.append(hint)
                    rubric["consideraciones_para_puntuar"] = considers
                    block["scoring_rubric"] = rubric
                return block
        # No se pudo refinar: dejar el bloque determinista intacto.
        block = dict(block)
        block.setdefault("tikz_pattern", {})
        block["tikz_pattern"] = dict(block["tikz_pattern"])
        block["tikz_pattern"]["llm_refined_by"] = f"none ({last_error})"
        return block

    return refiner


def consolidate(
    *,
    cycles: int = 10,
    only: Optional[list[str]] = None,
    llm_refiner: Optional[Callable[[str, dict[str, Any], int], dict[str, Any]]] = None,
    progress: Optional[Callable[[str, int, int, int], None]] = None,
) -> dict[str, dict[str, Any]]:
    """Corre hasta ``cycles`` ciclos por técnica con convergencia.

    ``progress(tech_id, pos, total, cycles_used)``.
    ``llm_refiner(tech_id, block, cycle) -> block`` (opcional).
    """
    ids = sorted(
        [t for t in TECHNIQUE_CONTRACTS if not only or t in only],
        key=lambda t: TECHNIQUE_CONTRACTS[t]["catalogo_no"],
    )
    result: dict[str, dict[str, Any]] = {}
    for pos, tech_id in enumerate(ids, 1):
        contract = TECHNIQUE_CONTRACTS[tech_id]
        prev_sig: Optional[str] = None
        block: dict[str, Any] = {}
        used = 0
        for cycle in range(1, cycles + 1):
            block = build_construction_block(tech_id, contract)
            if llm_refiner is not None:
                try:
                    block = llm_refiner(tech_id, block, cycle) or block
                except Exception:  # noqa: BLE001 - degradar a determinista
                    pass
            sig = json.dumps(block, ensure_ascii=False, sort_keys=True)
            used = cycle
            if sig == prev_sig:  # convergió
                break
            prev_sig = sig
        block["_cycles_used"] = used
        result[tech_id] = block
        if progress:
            progress(tech_id, pos, len(ids), used)
    return result


def run(
    *,
    cycles: int = 10,
    only: Optional[list[str]] = None,
    use_llm: bool = False,
    out_path: Path | str = CONSTRUCTION_PATH,
    progress: Optional[Callable[[str, int, int, int], None]] = None,
) -> dict[str, Any]:
    """Ejecuta la consolidación y escribe el JSON de construcción.

    Con ``only`` se re-procesan SOLO esas técnicas y se FUSIONAN con las ya
    existentes en el JSON (no se sobrescriben las demás), para poder re-refinar
    técnicas puntuales sin perder la corrida completa previa.
    """
    refiner = make_llm_refiner() if use_llm else None
    blocks = consolidate(cycles=cycles, only=only, llm_refiner=refiner, progress=progress)

    if only:
        path_existing = Path(out_path)
        if path_existing.exists():
            try:
                prev = json.loads(path_existing.read_text(encoding="utf-8")).get("construccion", {})
                merged = dict(prev)
                merged.update(blocks)
                blocks = merged
            except (OSError, ValueError):
                pass

    total_cycles = sum(b.get("_cycles_used", 0) for b in blocks.values())
    llm_refined = sum(
        1 for b in blocks.values()
        if str(b.get("tikz_pattern", {}).get("llm_refined_by", "")).startswith(("GPT", "Claude"))
    )
    payload = {
        "_meta": {
            "proposito": "Consolidar construcción TikZ/LaTeX + rúbrica de puntuación por técnica e integración con realizar-actividad.",
            "tecnicas": len(blocks),
            "cycles_max_por_tecnica": cycles,
            "ciclos_totales_ejecutados": total_cycles,
            "motor": "LLM (Luna/Terra) + determinista de respaldo" if use_llm else "determinista (fuentes oficiales + repo + plantillas TikZ)",
            "tecnicas_refinadas_llm": llm_refined if use_llm else 0,
        },
        "construccion": blocks,
    }
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "out_path": str(path),
        "tecnicas": len(blocks),
        "ciclos_totales": total_cycles,
        "cycles_max": cycles,
        "motor": "llm" if use_llm else "determinista",
        "tecnicas_refinadas_llm": llm_refined if use_llm else 0,
    }


if __name__ == "__main__":  # pragma: no cover
    import argparse

    ap = argparse.ArgumentParser(description="Consolida construcción TikZ/LaTeX + rúbrica por técnica (N ciclos).")
    ap.add_argument("--cycles", type=int, default=10, help="Ciclos por técnica (tope; converge antes).")
    ap.add_argument("--only", nargs="*", default=None, help="IDs de técnica a procesar (piloto).")
    ap.add_argument("--llm", action="store_true", help="Refinar snippets TikZ con LLM (Luna/Terra) vía bridge directo.")
    args = ap.parse_args()

    def _cli(tech_id: str, pos: int, total: int, used: int) -> None:
        print(f"[{pos:3d}/{total}] {tech_id} (ciclos={used})", flush=True)

    print(json.dumps(run(cycles=args.cycles, only=args.only, use_llm=args.llm, progress=_cli), ensure_ascii=False, indent=2))
