"""Escáner de PRODUCTOS de actividad de AulaTeX.

Un PRODUCTO es el entregable de una actividad (mapa, cuadro, línea de tiempo,
cuestionario, estudio de caso, foro, etc.) incluido en un reporte o presentación
ligado a esa actividad.

Recorre todos los ``reporte-*Actividad*.tex`` del repositorio, valida cuáles tienen
un PRODUCTO COMPLETADO (título temático real, sin placeholders activos, con
contenido) y detecta la técnica didáctica de cada uno (catálogo de las 100 técnicas).

Genera ``aulaTEX/base/.../productos-actividad.json``: un inventario de los productos de
actividad por técnica, que sirve como (a) evidencia de qué técnicas ya se han
resuelto en producción y (b) fuente para curar patrones reales al catálogo.

Un producto se considera COMPLETADO cuando:
- Tiene ``\\def\\documenttitle`` o ``\\newcommand{\\documenttitle}`` con un título
  TEMÁTICO (no 'Actividad N - materia', no 'Plantilla ...', no vacío).
- No conserva ``\\pendiente{...}`` como placeholder ACTIVO (rojo). Si el archivo
  redefine ``\\pendiente`` para neutralizarlo, o no lo usa, se considera resuelto.
- Tiene contenido: al menos 2 ``\\section`` con texto sustancial.

Solo biblioteca estándar. Reutiliza la detección de técnica del catálogo.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Callable, Optional

try:
    from .didactic_catalog import TECHNIQUE_CONTRACTS, canonical_technique_id
except ImportError:
    import importlib.util as _ilu

    _HERE = Path(__file__).resolve().parent

    def _load(name: str):
        spec = _ilu.spec_from_file_location(name, _HERE / f"{name}.py")
        mod = _ilu.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        return mod

    _dc = _load("didactic_catalog")
    TECHNIQUE_CONTRACTS = _dc.TECHNIQUE_CONTRACTS
    canonical_technique_id = _dc.canonical_technique_id

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = (
    REPO_ROOT / "aulaTEX/base" / "latex" / "adaptadas" / "materias"
    / "tecnicas-didacticas-aprendizaje" / "productos-actividad.json"
)

# Títulos que denotan plantilla/borrador, no un producto completado.
_PLACEHOLDER_TITLE_PATTERNS = (
    re.compile(r"^\s*actividad\s+\d+\s*[-–]", re.IGNORECASE),
    re.compile(r"plantilla", re.IGNORECASE),
    re.compile(r"^\s*$"),
    # Título de EJEMPLO de la plantilla base (no un producto temático real):
    # aparece idéntico en decenas de materias sin resolver.
    re.compile(r"^\s*cuadro comparativo de conceptos fundamentales\s*$", re.IGNORECASE),
)


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip().lower()


def _extract_title(tex: str) -> str:
    """Extrae el valor de \\documenttitle (def o newcommand), IGNORANDO comentarios.

    Las plantillas incluyen ejemplos comentados como
    '% \\def\\documenttitle {Cuadro comparativo ...}'; deben ignorarse y tomar solo
    la definición activa.
    """
    # Quitar comentarios línea por línea antes de buscar.
    code = "\n".join(line.split("%", 1)[0] for line in tex.splitlines())
    for pat in (
        r"\\def\\documenttitle\s*\{([^}]*)\}",
        r"\\newcommand\{\\documenttitle\}\s*\{([^}]*)\}",
        r"\\renewcommand\{\\documenttitle\}\s*\{([^}]*)\}",
    ):
        m = re.search(pat, code)
        if m:
            return m.group(1).strip()
    return ""


def _title_is_placeholder(title: str) -> bool:
    if not title:
        return True
    # Si el título referencia otra macro (\itescadocumenttitle), es plantilla.
    if title.startswith("\\"):
        return True
    return any(p.search(title) for p in _PLACEHOLDER_TITLE_PATTERNS)


def _has_active_placeholder(tex: str) -> bool:
    """True si hay \\pendiente{...} como placeholder activo (rojo) sin neutralizar."""
    # ¿Se redefine \pendiente para neutralizarlo? (p. ej. 'Refuerzo ... materializado')
    neutralized = bool(
        re.search(r"\\newcommand\{\\pendiente\}\[1\]\{(?![^}]*#1)[^}]*\}", tex)
        or re.search(r"\\renewcommand\{\\pendiente\}\[1\]\{(?![^}]*#1)[^}]*\}", tex)
    )
    # ¿Hay usos de \pendiente{...} fuera de comentarios?
    uses = []
    for line in tex.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("%"):
            continue
        code = line.split("%", 1)[0]
        if re.search(r"\\pendiente\{", code):
            uses.append(line)
    if not uses:
        return False
    return not neutralized


def _count_sections(tex: str) -> int:
    body = tex
    # Contar \section (no comentadas) con algo de texto entre ellas.
    sections = [
        m for m in re.finditer(r"(?m)^\s*\\section\*?\{", tex)
        if not tex[max(0, m.start() - 1):m.start()].endswith("%")
    ]
    return len(sections)


def _extract_declared_product(tex: str) -> str:
    """Extrae el texto del campo '\\textbf{Producto elaborado:} ...' o 'Actividad:'.

    Muchas actividades (p. ej. UCNL) declaran explícitamente el producto ahí,
    aunque su \\documenttitle sea genérico. Es una señal fuerte de la técnica.
    """
    for label in (r"Producto\s+elaborado", r"Producto\s+solicitado", r"Actividad"):
        m = re.search(
            r"\\textbf\{\s*" + label + r"\s*:?\s*\}\s*(.+?)(?:\\textbf\{|\n\s*\n|$)",
            tex,
            re.IGNORECASE | re.DOTALL,
        )
        if m:
            frag = m.group(1)
            # Ignorar si es un placeholder \pendiente sin resolver.
            if "\\pendiente" in frag:
                continue
            frag_l = frag.lower()
            # Ignorar productos declarados GENÉRICOS de plantilla (sin resolver).
            if any(s in frag_l for s in (
                "refuerzo ciclo a", "indicar el producto", "indicar si es",
                "producto solicitado", "indicar la tecnica", "indicar la técnica",
            )):
                continue
            # Ignorar si enumera muchas técnicas (lista de plantilla, no un producto).
            tech_words = ("cuadro comparativo", "mapa conceptual", "linea de tiempo",
                          "línea de tiempo", "estudio de caso", "ensayo", "foro",
                          "portafolio", "glosario", "resumen", "esquema")
            if sum(1 for w in tech_words if w in frag_l) >= 3:
                continue
            frag = re.sub(r"\s+", " ", frag).strip()
            if len(frag) > 8:
                return frag[:300]
    return ""


# Frases de plantilla genéricas que mencionan técnicas sin que sean el producto.
# Se eliminan del cuerpo antes de detectar para evitar falsos positivos.
_TEMPLATE_NOISE = (
    "situaciones reales de desempeño: diagnóstico, toma de decisiones",
    "situaciones reales de desempeno: diagnostico, toma de decisiones",
    "cuadro comparativo, mapa conceptual, esquema, mapa mental, linea de tiempo",
    "cuadro comparativo, mapa conceptual, estudio de caso",
    "cuadro comparativo, mapa, esquema, linea de tiempo",
    "mapa conceptual, cuadro comparativo, linea de tiempo",
    "informe, cuadro, mapa, analisis de caso, matriz, linea de tiempo",
    "cuadro comparativo, esquema, linea de tiempo, mapa conceptual",
)

# Aliases demasiado genéricos: solo cuentan si aparecen en el TÍTULO, no en el cuerpo.
# "resumen"/"síntesis": la plantilla da a TODO reporte una sección abstract llamada
# "Resumen", así que en el cuerpo no distinguen el producto (un cuadro comparativo
# se detectaría como resumen). En el título sí son señal fiable.
_TITLE_ONLY_ALIASES = {
    "diagnóstico", "diagnostico", "conceptos", "diagrama", "situación", "situacion",
    "resumen", "síntesis", "sintesis",
}


def _strip_template_noise(text: str) -> str:
    low = text
    for phrase in _TEMPLATE_NOISE:
        low = re.sub(re.escape(phrase), " ", low, flags=re.IGNORECASE)
    return low


def infer_technique(tex: str, title: str) -> tuple[str, str, str]:
    """Detecta la técnica priorizando el TÍTULO y descartando ruido de plantilla.

    Devuelve (technique_id, alias, confianza) donde confianza ∈ {'alta','media','baja'}:
    - 'alta'  = detectada en el TÍTULO temático (señal fiable del producto).
    - 'media' = detectada en el cuerpo, en una \\section propia del producto.
    - 'baja'  = detectada solo en prosa del cuerpo (posible ruido de plantilla).
    """
    title_n = _norm(title)
    # El "Producto elaborado" declarado es tan fiable como el título.
    declared_n = _norm(_strip_template_noise(_extract_declared_product(tex)))

    # Paso 0: entorno-producto propio de una técnica (señal MÁS fiable que el título,
    # porque materializa el producto real). p. ej. resenabox -> reseña, wikibox ->
    # socioaprendizaje (la wiki es herramienta colaborativa de esa técnica anfitriona).
    _ENV_TECH = {
        r"\\begin\{resenabox\}": "resena",
        r"\\begin\{forobox\}": "foro_diagnostico",
        r"\\begin\{wikibox\}": "socioaprendizaje",
        # Mapa semántico: estilos TikZ propios msroot/msfield (distintos de los
        # mcroot/mcbranch del mapa conceptual). Señal fiable del producto gráfico.
        r"\\node\[msroot\]": "mapa_semantico",
        r"msroot/\.style": "mapa_semantico",
    }
    for env_pat, env_tid in _ENV_TECH.items():
        if re.search(env_pat, tex) and env_tid in TECHNIQUE_CONTRACTS:
            return env_tid, "<recuadro>", "alta"

    # Paso 1: match por título O producto declarado (el más específico gana) -> alta.
    # Los alias genéricos SÍ valen aquí: es el lugar donde son señal fiable del
    # producto. Los pasos siguientes (cuerpo) sí deben descartarlos.
    best_title: Optional[tuple[int, str, str]] = None
    for tech_id, contract in TECHNIQUE_CONTRACTS.items():
        for alias in contract.get("aliases", ()):
            alias_n = _norm(alias)
            if not alias_n:
                continue
            if alias_n in title_n or (len(alias_n) >= 6 and alias_n in declared_n):
                if best_title is None or len(alias_n) > best_title[0]:
                    best_title = (len(alias_n), tech_id, alias)
    if best_title is not None:
        return best_title[1], best_title[2], "alta"

    # Paso 2: match en títulos de \section (el producto suele nombrarse ahí).
    section_titles = " \n ".join(
        m.group(1) for m in re.finditer(r"(?m)^\s*\\section\*?\{([^}]*)\}", tex)
    )
    section_n = _norm(_strip_template_noise(section_titles))
    best_sec: Optional[tuple[int, str, str]] = None
    for tech_id, contract in TECHNIQUE_CONTRACTS.items():
        for alias in contract.get("aliases", ()):
            if alias in _TITLE_ONLY_ALIASES:
                continue
            alias_n = _norm(alias)
            if alias_n and len(alias_n) >= 6 and alias_n in section_n:
                if best_sec is None or len(alias_n) > best_sec[0]:
                    best_sec = (len(alias_n), tech_id, alias)
    if best_sec is not None:
        return best_sec[1], best_sec[2], "media"

    # Paso 3: cuerpo visible sin comentarios ni ruido -> confianza baja.
    visible = "\n".join(
        line.split("%", 1)[0] for line in tex.splitlines()
        if not line.lstrip().startswith("%")
    )
    visible = _norm(_strip_template_noise(visible))
    best_body: Optional[tuple[int, str, str]] = None
    for tech_id, contract in TECHNIQUE_CONTRACTS.items():
        for alias in contract.get("aliases", ()):
            if alias in _TITLE_ONLY_ALIASES:
                continue
            alias_n = _norm(alias)
            if alias_n and len(alias_n) >= 6 and alias_n in visible:
                if best_body is None or len(alias_n) > best_body[0]:
                    best_body = (len(alias_n), tech_id, alias)
    if best_body is not None:
        return best_body[1], best_body[2], "baja"
    return "general", "", "baja"


def detect_all_products(tex: str, title: str) -> list[dict[str, Any]]:
    """Detecta TODOS los productos de una actividad (puede tener varios).

    Una actividad puede combinar productos (p. ej. 'Glosario y análisis de caso').
    Cada \\section cuyo nombre coincide con un alias de técnica se registra como un
    producto propio; además, el título aporta un producto de confianza alta.
    Devuelve una lista de {technique_id, nombre, seccion, confianza} sin duplicados.
    """
    found: dict[str, dict[str, Any]] = {}

    def _register(tech_id: str, alias: str, seccion: str, confianza: str) -> None:
        tech_id = canonical_technique_id(tech_id)
        prev = found.get(tech_id)
        rank = {"alta": 3, "media": 2, "baja": 1}
        if prev is None or rank[confianza] > rank[prev["confianza"]]:
            contract = TECHNIQUE_CONTRACTS.get(tech_id, {})
            found[tech_id] = {
                "technique_id": tech_id,
                "nombre": contract.get("nombre_oficial"),
                "catalogo_no": contract.get("catalogo_no"),
                "alias_match": alias,
                "seccion": seccion,
                "confianza": confianza,
            }

    # (a) Título o producto declarado -> producto principal (confianza alta).
    tid, alias, conf = infer_technique(tex, title)
    if tid != "general" and conf == "alta":
        origen = "<título>" if _norm(alias) in _norm(title) else "<producto elaborado>"
        _register(tid, alias, origen, "alta")

    # (a.bis) Entornos-producto propios de una técnica (señal de confianza ALTA):
    # el recuadro materializa el producto real aunque no aparezca en un \section.
    # p. ej. resenabox -> reseña, forobox -> foro. Más fiable que el alias en título.
    _ENV_PRODUCT = {
        r"\\begin\{resenabox\}": ("resena", "<recuadro resenabox>"),
        r"\\begin\{forobox\}": ("foro_diagnostico", "<recuadro forobox>"),
        r"\\begin\{wikibox\}": ("socioaprendizaje", "<recuadro wikibox>"),
        r"\\node\[msroot\]": ("mapa_semantico", "<mapa semántico msroot>"),
    }
    for env_pat, (env_tid, env_origen) in _ENV_PRODUCT.items():
        if re.search(env_pat, tex):
            _register(env_tid, env_origen.strip("<>"), env_origen, "alta")

    # (b) Cada \section o \subsection: buscar la técnica más específica en su título.
    for m in re.finditer(r"(?m)^\s*\\(?:sub)?section\*?\{([^}]*)\}", tex):
        sec_title = m.group(1)
        sec_n = _norm(_strip_template_noise(sec_title))
        best: Optional[tuple[int, str, str]] = None
        for tech_id, contract in TECHNIQUE_CONTRACTS.items():
            for al in contract.get("aliases", ()):
                if al in _TITLE_ONLY_ALIASES:
                    continue
                al_n = _norm(al)
                if al_n and len(al_n) >= 6 and al_n in sec_n:
                    if best is None or len(al_n) > best[0]:
                        best = (len(al_n), tech_id, al)
        if best is not None:
            _register(best[1], best[2], sec_title.strip(), "media")

    return sorted(found.values(), key=lambda p: (p["confianza"] != "alta", p.get("catalogo_no") or 999))


def scan_activity(tex_path: Path) -> Optional[dict[str, Any]]:
    """Valida y describe el producto de una actividad."""
    try:
        tex = tex_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    title = _extract_title(tex)
    declared = _extract_declared_product(tex)
    reasons: list[str] = []
    # Título genérico NO descalifica si hay un 'Producto elaborado' real declarado
    # (caso frecuente en UCNL: título 'Actividad N - materia' + producto real).
    if _title_is_placeholder(title) and not declared:
        reasons.append("titulo_placeholder_sin_producto_declarado")
    if _has_active_placeholder(tex):
        reasons.append("pendiente_activo")
    n_sections = _count_sections(tex)
    if n_sections < 2:
        reasons.append("menos_de_2_secciones")

    completed = not reasons
    tech_id, alias, confianza = infer_technique(tex, title) if completed else ("", "", "baja")
    tech_id = canonical_technique_id(tech_id) if tech_id else ""
    contract = TECHNIQUE_CONTRACTS.get(tech_id, {}) if tech_id else {}

    # Detección de MÚLTIPLES productos (una actividad puede combinar varios).
    productos = detect_all_products(tex, title) if completed else []

    rel = tex_path.relative_to(REPO_ROOT).as_posix()
    m_act = re.search(r"Actividad-(\d+)", tex_path.name)
    return {
        "archivo": rel,
        "titulo": title,
        "actividad": int(m_act.group(1)) if m_act else None,
        "completado": completed,
        "razones_incompleto": reasons,
        "secciones": n_sections,
        "tecnica_detectada": tech_id or None,
        "tecnica_nombre": contract.get("nombre_oficial") if contract else None,
        "catalogo_no": contract.get("catalogo_no") if contract else None,
        "alias_match": alias or None,
        "confianza": confianza,
        "productos": productos,
        "multiproducto": len(productos) > 1,
        "tiene_tikz": "\\begin{tikzpicture}" in tex,
        "tiene_longtable": "\\begin{longtable}" in tex,
    }


def scan_all(
    *,
    root: Path | str = REPO_ROOT,
    progress: Optional[Callable[[int, int, str], None]] = None,
) -> dict[str, Any]:
    """Recorre todos los reportes de actividad y clasifica sus productos."""
    root = Path(root)
    files = sorted(root.rglob("reporte-*Actividad*.tex"))
    productos: list[dict[str, Any]] = []
    for i, path in enumerate(files, 1):
        info = scan_activity(path)
        if info:
            productos.append(info)
        if progress:
            progress(i, len(files), path.name)

    completos = [p for p in productos if p["completado"]]
    incompletos = [p for p in productos if not p["completado"]]

    # Agrupar por técnica usando TODOS los productos de cada actividad (una
    # actividad puede aportar varios, p. ej. glosario + estudio de caso). Solo se
    # cuentan productos con confianza alta/media (título temático o \section propia).
    por_tecnica: dict[str, list[dict[str, Any]]] = {}
    multiproducto: list[dict[str, Any]] = []
    for p in completos:
        prods = [pr for pr in p.get("productos", []) if pr["confianza"] in ("alta", "media")]
        if len(prods) > 1:
            multiproducto.append({
                "archivo": p["archivo"],
                "titulo": p["titulo"],
                "actividad": p["actividad"],
                "productos": [pr["technique_id"] for pr in prods],
            })
        for pr in prods:
            por_tecnica.setdefault(pr["technique_id"], []).append({
                "archivo": p["archivo"],
                "titulo": p["titulo"],
                "actividad": p["actividad"],
                "confianza": pr["confianza"],
                "seccion": pr["seccion"],
                "tiene_tikz": p["tiene_tikz"],
                "tiene_longtable": p["tiene_longtable"],
            })
    for items in por_tecnica.values():
        items.sort(key=lambda x: (x["confianza"] != "alta", x["archivo"]))

    total_confirmados = sum(len(v) for v in por_tecnica.values())
    return {
        "_meta": {
            "proposito": "Inventario de PRODUCTOS de actividad (entregable en reporte/presentación) por técnica didáctica. Una actividad puede aportar varios productos.",
            "total_reportes_actividad": len(files),
            "productos_completos": len(completos),
            "productos_confirmados": total_confirmados,
            "actividades_multiproducto": len(multiproducto),
            "incompletos": len(incompletos),
            "tecnicas_con_producto": sorted(por_tecnica.keys()),
            "conteo_por_tecnica": {k: len(v) for k, v in sorted(por_tecnica.items(), key=lambda kv: -len(kv[1]))},
        },
        "por_tecnica": por_tecnica,
        "multiproducto": multiproducto,
        "productos": completos,
        "incompletos": incompletos,
    }


def run(
    *,
    out_path: Path | str = OUTPUT_PATH,
    progress: Optional[Callable[[int, int, str], None]] = None,
) -> dict[str, Any]:
    data = scan_all(progress=progress)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "out_path": str(path),
        "total": data["_meta"]["total_reportes_actividad"],
        "productos": data["_meta"]["productos_completos"],
        "incompletos": data["_meta"]["incompletos"],
        "tecnicas_con_producto": data["_meta"]["tecnicas_con_producto"],
    }


if __name__ == "__main__":  # pragma: no cover
    import argparse

    ap = argparse.ArgumentParser(description="Escanea los productos de actividad (entregables) por técnica.")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    def _cli(i: int, total: int, name: str) -> None:
        if not args.quiet:
            print(f"[{i:3d}/{total}] {name}", flush=True)

    print(json.dumps(run(progress=_cli), ensure_ascii=False, indent=2))
