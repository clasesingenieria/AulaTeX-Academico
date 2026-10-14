"""Genera variantes DEGRADADAS de las actividades de alta calidad.

Motivo
------
``reward.jsonl`` está sesgado: 75% de los ejemplos puntúan por debajo de 50 y
apenas 8% superan 95. El modelo ve mucha mediocridad y poca excelencia, así que
aprende a detectar lo malo pero discrimina mal entre *bueno* y *excelente* —
que es justo la decisión difícil cuando el optimizador ya llegó a 97.

Este script toma los TEX que puntúan alto y produce versiones degradadas de
forma CONTROLADA: cada degradación ataca un componente concreto de la métrica
(citas, conectores, estructura, listas, postura, conceptos destacados). El
resultado es un conjunto de pares muy parecidos entre sí salvo por el rasgo
degradado, que es la señal que el modelo necesita para afinar el rango alto.

Límites conocidos
-----------------
* El score sigue siendo el proxy heurístico, no juicio humano. Esto densifica
  la frontera del proxy; no redefine qué es calidad editorial.
* Las degradaciones son sintéticas. Enseñan "qué le falta a este texto", no
  "cómo escribe mal un humano". Sirven para el ranking fino, no para generación.
* Se descarta la variante si no baja el score: sin contraste no hay señal.

Uso:
    python aulaTEX/aulatex_training/augment_reward_corpus.py
    python aulaTEX/aulatex_training/augment_reward_corpus.py --min-score 90 --dry-run
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

CONECTORES = (r"\b(por tanto|por ello|en consecuencia|sin embargo|no obstante|es decir|"
              r"en cambio|por el contrario|de ese modo|as[íi]|adem[áa]s|dado que|puesto que|"
              r"en efecto|por consiguiente)\b")
POSTURA = (r"\b(desde mi perspectiva|considero|sostengo|mi postura|a mi juicio|"
           r"reflexi[óo]n propia)\b")
TITULOS_ETIQUETA = ("Desarrollo", "Marco conceptual", "Metodología")


def load_scorer():
    sys.path.insert(0, str(REPO_ROOT / "aulaTEX"))
    from aulatex.activity_optimizer import ActivityOptimizer

    optimizer = ActivityOptimizer.__new__(ActivityOptimizer)
    optimizer._current_concepts = None
    return optimizer._quality_score


# --------------------------------------------------------------- degradaciones
# Cada función devuelve el texto degradado o None si no aplica al documento.

def _sustituir(texto: str, matches, reemplazo: str) -> str:
    """Aplica los reemplazos de derecha a izquierda.

    `rng.sample` devuelve orden ALEATORIO: hay que ordenar por posición
    descendente o los índices se corren y el texto queda corrupto.
    """
    for m in sorted(matches, key=lambda x: x.start(), reverse=True):
        texto = texto[:m.start()] + reemplazo + texto[m.end():]
    return texto


def quitar_citas(texto: str, rng: random.Random, dejar: int = 2):
    """Deja `dejar` citas: por debajo de 5 la métrica ya no da el tope.

    No se borra el comando (eso descuadra grupos cuando la cita vive dentro de
    otra macro): se renombra a \\ignorecite, que la métrica ya no cuenta.
    """
    citas = list(re.finditer(r"\\cite[tp]?\*?(?=[\[{])", texto))
    if len(citas) <= dejar:
        return None
    return _sustituir(texto, rng.sample(citas, len(citas) - dejar), "\\ignorecite")


def citas_escasas(texto: str, rng: random.Random):
    """Deja 3 citas: escalón intermedio entre el tope (5) y la ausencia."""
    return quitar_citas(texto, rng, dejar=3)


def sin_ninguna_cita(texto: str, rng: random.Random):
    return quitar_citas(texto, rng, dejar=0)


def quitar_conectores(texto: str, rng: random.Random, fraccion: float = 0.8):
    hits = list(re.finditer(CONECTORES, texto, re.IGNORECASE))
    if len(hits) < 3:
        return None
    objetivo = max(1, int(len(hits) * fraccion))
    texto = _sustituir(texto, rng.sample(hits, objetivo), "")
    # Limpia la puntuación que queda huérfana al borrar el conector.
    return re.sub(r"\s+,", ",", re.sub(r"  +", " ", texto))


def quitar_postura(texto: str, rng: random.Random):
    hits = list(re.finditer(POSTURA, texto, re.IGNORECASE))
    if not hits:
        return None
    return _sustituir(texto, hits, "se observa que")


def aplanar_negritas(texto: str, rng: random.Random, dejar: int = 2):
    """Deja `dejar` términos destacados: el tope exige 8 distintos.

    Se renombra a \\mbox en lugar de eliminar las llaves, para no alterar el
    balance de grupos cuando el contenido incluye otras macros.
    """
    hits = list(re.finditer(r"\\textbf(?=\s*\{)", texto))
    if len(hits) <= dejar:
        return None
    return _sustituir(texto, rng.sample(hits, len(hits) - dejar), "\\mbox")


def listas_a_prosa(texto: str, rng: random.Random):
    """Disuelve las listas en prosa plana: pierde el punto de `listas`."""
    if r"\begin{itemize}" not in texto and r"\begin{enumerate}" not in texto:
        return None
    nuevo = re.sub(r"\\begin\{(itemize|enumerate)\}", "", texto)
    nuevo = re.sub(r"\\end\{(itemize|enumerate)\}", "", nuevo)
    nuevo = re.sub(r"\\item(\[[^\]]*\])?\s*", "", nuevo)
    return nuevo if nuevo != texto else None


def inflar_listas(texto: str, rng: random.Random):
    """Duplica listas existentes: 3+ listas penalizan fuerte."""
    m = re.search(r"\\begin\{itemize\}.*?\\end\{itemize\}", texto, re.DOTALL)
    if not m:
        return None
    bloque = m.group(0)
    return texto[:m.end()] + "\n\n" + bloque + "\n\n" + bloque + texto[m.end():]


def titulos_etiqueta(texto: str, rng: random.Random):
    """Sustituye títulos temáticos por etiquetas genéricas."""
    hits = list(re.finditer(r"\\subsection\{([^{}]{8,80})\}", texto))
    if len(hits) < 2:
        return None
    for i, m in enumerate(sorted(hits, key=lambda x: x.start(), reverse=True)):
        etiqueta = TITULOS_ETIQUETA[i % len(TITULOS_ETIQUETA)]
        texto = texto[:m.start()] + "\\subsection{" + etiqueta + "}" + texto[m.end():]
    return texto


def truncar_desarrollo(texto: str, rng: random.Random, fraccion: float = 0.45):
    """Recorta párrafos del cuerpo sin cortar dentro de un entorno abierto."""
    ini = texto.find(r"\begin{document}")
    fin = texto.rfind(r"\end{document}")
    if ini < 0 or fin < 0:
        return None
    parrafos = texto[ini:fin].split("\n\n")
    if len(parrafos) < 8:
        return None

    objetivo = max(4, int(len(parrafos) * (1 - fraccion)))
    abiertos: list[str] = []
    seguros: list[int] = []
    for i, parrafo in enumerate(parrafos):
        activo = _sin_comentarios(parrafo)
        for nombre in re.findall(r"\\begin\{(\w+\*?)\}", activo):
            if nombre != "document":  # queda abierto por definición del recorte
                abiertos.append(nombre)
        for nombre in re.findall(r"\\end\{(\w+\*?)\}", activo):
            if nombre in abiertos:
                abiertos.remove(nombre)
        # Solo es seguro cortar donde no queda ningún entorno abierto.
        if not abiertos and _balance_llaves("\n\n".join(parrafos[:i + 1])) == 0:
            seguros.append(i + 1)
    # El corte seguro más cercano al objetivo, sin quedarse con el documento entero.
    validos = [c for c in seguros if 4 <= c < len(parrafos)]
    if not validos:
        return None
    corte = min(validos, key=lambda c: abs(c - objetivo))
    return texto[:ini] + "\n\n".join(parrafos[:corte]) + "\n\n" + texto[fin:]


def _sin_comentarios(texto: str) -> str:
    """Quita comentarios LaTeX: sus llaves no cuentan para el balance."""
    return re.sub(r"(?<!\\)%.*$", "", texto, flags=re.MULTILINE)


def _balance_llaves(texto: str) -> int:
    activo = _sin_comentarios(texto)
    # Primero \\ (salto de fila): si no, el 2.o backslash se lee como escape de {.
    activo = activo.replace("\\\\", "")
    activo = re.sub(r"\\[{}]", "", activo)  # \{ y \} son literales, no delimitan
    return activo.count("{") - activo.count("}")


def estructura_intacta(original: str, variante: str) -> bool:
    """La degradación debe empeorar la CALIDAD, no romper el LaTeX.

    Se compara contra el ORIGINAL, no contra el ideal: varios TEX ya traen
    desbalances aparentes en zonas comentadas y no deben bloquear la variante.
    """
    if _balance_llaves(variante) != _balance_llaves(original):
        return False
    act_o = _sin_comentarios(original)
    act_v = _sin_comentarios(variante)
    for env in set(re.findall(r"\\begin\{(\w+\*?)\}", act_o)):
        pat_b = r"\\begin\{%s\}" % re.escape(env)
        pat_e = r"\\end\{%s\}" % re.escape(env)
        delta_o = len(re.findall(pat_b, act_o)) - len(re.findall(pat_e, act_o))
        delta_v = len(re.findall(pat_b, act_v)) - len(re.findall(pat_e, act_v))
        if delta_o != delta_v:
            return False
    return True


DEGRADACIONES = [
    ("sin-citas", sin_ninguna_cita),
    ("citas-escasas", citas_escasas),
    ("sin-conectores", quitar_conectores),
    ("sin-postura", quitar_postura),
    ("sin-conceptos-destacados", aplanar_negritas),
    ("listas-disueltas", listas_a_prosa),
    ("exceso-de-listas", inflar_listas),
    ("titulos-etiqueta", titulos_etiqueta),
    ("desarrollo-truncado", truncar_desarrollo),
]


def iter_fuentes(root: Path, min_score: float, score_of):
    excluded = {".git", ".venv", "base", "node_modules", "__pycache__"}
    for tex in sorted(root.rglob("*.tex")):
        if excluded.intersection(tex.parts):
            continue
        name = tex.name.lower()
        if not name.startswith(("reporte-", "presentacion-")) or "actividad-" not in name:
            continue
        texto = tex.read_text(encoding="utf-8", errors="ignore")
        if "POR DEFINIR" in texto or len(texto) < 400:
            continue
        score = score_of(texto)
        if score >= min_score:
            yield tex, texto, score


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-score", type=float, default=95.0,
                        help="Score mínimo para usar un TEX como fuente.")
    parser.add_argument("--min-drop", type=float, default=1.5,
                        help="Caída mínima de score para conservar la variante.")
    parser.add_argument("--seed", type=int, default=20260811)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out", type=Path,
                        default=REPO_ROOT / "aulaTEX" / "retroalimentacion-editorial" / "aulatex"
                        / "training" / "reward-augmented.jsonl")
    args = parser.parse_args()

    score_of = load_scorer()
    rng = random.Random(args.seed)

    fuentes = list(iter_fuentes(REPO_ROOT, args.min_score, score_of))
    print(f"[augment] fuentes con score >= {args.min_score:.0f}: {len(fuentes)}")
    if not fuentes:
        print("[augment] nada que hacer.")
        return 1

    filas: list[dict] = []
    por_tipo: dict[str, int] = {}
    descartadas = 0
    corruptas = 0

    for tex, texto, score in fuentes:
        for nombre, funcion in DEGRADACIONES:
            variante = funcion(texto, rng)
            if variante is None or variante == texto:
                descartadas += 1
                continue
            if not estructura_intacta(texto, variante):
                corruptas += 1
                continue
            nuevo = score_of(variante)
            if score - nuevo < args.min_drop:
                descartadas += 1
                continue
            rel = tex.relative_to(REPO_ROOT).as_posix()
            filas.append({
                "text": variante,
                "score": round(nuevo, 2),
                "source": "degradacion-sintetica-validada",
                "target": f"{rel}::{nombre}",
                "source_target": rel,
                "institution": rel.split("/", 1)[0],
                "activity_number": None,
                "kind": "presentacion" if tex.name.lower().startswith("presentacion-") else "reporte",
                "degradacion": nombre,
                "score_origen": round(score, 2),
            })
            por_tipo[nombre] = por_tipo.get(nombre, 0) + 1

    print(f"[augment] variantes generadas : {len(filas)}")
    print(f"[augment] descartadas         : {descartadas} (no aplicaba o sin caída)")
    print(f"[augment] descartadas corruptas: {corruptas} (rompían el LaTeX)")
    print()
    print("[augment] por tipo de degradación:")
    for nombre, _ in DEGRADACIONES:
        n = por_tipo.get(nombre, 0)
        caidas = [f["score_origen"] - f["score"] for f in filas if f["degradacion"] == nombre]
        media = sum(caidas) / len(caidas) if caidas else 0.0
        print(f"   {nombre:<26} {n:3d}   caída media {media:5.1f} pts")

    if filas:
        sc = sorted(f["score"] for f in filas)
        print()
        print(f"[augment] scores generados: min {sc[0]:.1f} | mediana "
              f"{sc[len(sc)//2]:.1f} | max {sc[-1]:.1f}")

    if args.dry_run:
        print("\n[augment] --dry-run: no se escribió nada.")
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for fila in filas:
            fh.write(json.dumps(fila, ensure_ascii=False) + "\n")
    print(f"\n[augment] escrito -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
