#!/usr/bin/env python3
r"""Convierte el mapa conceptual con posicionamiento RELATIVO (below=/left=/right=/
below left=/below right=) a COORDENADAS ABSOLUTAS at (x,y), para poder alimentar
el optimizador de choques (optimize_tikz_snippet.py / optimize_concept_map.py),
que requiere \node[style] (name) at (x,y) {...}.

- Resuelve la cadena de referencias relativas a partir de la raíz en (0,0).
- Mapea estilos mc* -> root/branch/subbranch (los que el optimizador reconoce),
  vía \tikzset alias, SIN cambiar la apariencia (mcroot/mcbranch/mcleaf/mcsub).
- Mantiene TODOS los \draw ... node[mclabel]{...} intactos (usan (name), no coords).

Uso:
  python aulaTEX/rel2abs_map.py <tex> --label fig:mapa --write   # reescribe el .tex
  python aulaTEX/rel2abs_map.py <tex> --label fig:mapa           # dry-run (imprime)
"""
from __future__ import annotations

import argparse
import pathlib
import re

# Dimensiones aproximadas por estilo mc* (cm). text width + inner sep*2, alto ~ nº líneas.
# Se usan solo para calcular offsets de borde en el posicionamiento relativo.
STYLE_W = {"mcroot": 3.3, "mcbranch": 2.5, "mcleaf": 2.7, "mcsub": 2.5}
STYLE_H = {"mcroot": 1.2, "mcbranch": 0.9, "mcleaf": 1.0, "mcsub": 0.95}

NODE_RE = re.compile(
    r"\\node\[(?P<style>[^\]]+)\]\s*\((?P<name>[^)]+)\)\s*\{(?P<text>[^}]*)\}\s*;",
    re.S,
)

# Patrones de posicionamiento relativo dentro de la lista de opciones del nodo.
REL_PATTERNS = [
    (re.compile(r"below left=(?P<a>[0-9.]+)cm and (?P<b>[0-9.]+)cm of (?P<ref>[A-Za-z0-9_]+)"), "below_left"),
    (re.compile(r"below right=(?P<a>[0-9.]+)cm and (?P<b>[0-9.]+)cm of (?P<ref>[A-Za-z0-9_]+)"), "below_right"),
    (re.compile(r"below=(?P<a>[0-9.]+)cm of (?P<ref>[A-Za-z0-9_]+)"), "below"),
    (re.compile(r"left=(?P<a>[0-9.]+)cm of (?P<ref>[A-Za-z0-9_]+)"), "left"),
    (re.compile(r"right=(?P<a>[0-9.]+)cm of (?P<ref>[A-Za-z0-9_]+)"), "right"),
]


def base_style(style_list: str) -> str:
    return style_list.split(",")[0].strip()


def extract_block(tex: str, label: str):
    lp = tex.find(f"\\label{{{label}}}") if label else -1
    if lp >= 0:
        s = tex.rfind("\\begin{tikzpicture}", 0, lp)
        e = tex.find("\\end{tikzpicture}", s)
        if s < 0 or e < 0:
            raise SystemExit("No se encontró el bloque tikzpicture del label")
        e += len("\\end{tikzpicture}")
        return s, e, tex[s:e]
    # Sin label: buscar el tikzpicture que contenga el mapa (root + mcbranch)
    pos = 0
    while True:
        s = tex.find("\\begin{tikzpicture}", pos)
        if s < 0:
            break
        e = tex.find("\\end{tikzpicture}", s)
        if e < 0:
            break
        e += len("\\end{tikzpicture}")
        block = tex[s:e]
        if "(root)" in block and "mcbranch" in block:
            return s, e, block
        pos = e
    raise SystemExit("No se encontró el bloque del mapa (root + mcbranch)")


def solve_coords(block: str):
    """Devuelve dict name -> (x, y, base_style, style_list, text) resolviendo relativos."""
    order = []
    raw = {}
    for m in NODE_RE.finditer(block):
        style_list = m.group("style")
        name = m.group("name").strip()
        text = m.group("text")
        order.append(name)
        raw[name] = (style_list, text)

    coords: dict[str, tuple[float, float]] = {}

    def resolve(name: str) -> tuple[float, float]:
        if name in coords:
            return coords[name]
        style_list, _ = raw[name]
        bs = base_style(style_list)
        # ¿tiene relativo?
        rel = None
        for rx, kind in REL_PATTERNS:
            mm = rx.search(style_list)
            if mm:
                rel = (kind, mm)
                break
        if rel is None:
            # raíz u origen
            coords[name] = (0.0, 0.0)
            return coords[name]
        kind, mm = rel
        ref = mm.group("ref")
        rx0, ry0 = resolve(ref)
        ref_bs = base_style(raw[ref][0])
        # medias alturas/anchos para calcular separación borde-a-borde
        hh_ref = STYLE_H.get(ref_bs, 0.9) / 2
        hh_me = STYLE_H.get(bs, 0.9) / 2
        hw_ref = STYLE_W.get(ref_bs, 2.5) / 2
        hw_me = STYLE_W.get(bs, 2.5) / 2
        if kind == "below":
            a = float(mm.group("a"))
            x = rx0
            y = ry0 - (hh_ref + a + hh_me)
        elif kind == "left":
            a = float(mm.group("a"))
            x = rx0 - (hw_ref + a + hw_me)
            y = ry0
        elif kind == "right":
            a = float(mm.group("a"))
            x = rx0 + (hw_ref + a + hw_me)
            y = ry0
        elif kind == "below_left":
            a = float(mm.group("a"))
            b = float(mm.group("b"))
            x = rx0 - (hw_ref + b + hw_me)
            y = ry0 - (hh_ref + a + hh_me)
        elif kind == "below_right":
            a = float(mm.group("a"))
            b = float(mm.group("b"))
            x = rx0 + (hw_ref + b + hw_me)
            y = ry0 - (hh_ref + a + hh_me)
        else:
            x, y = rx0, ry0
        coords[name] = (x, y)
        return coords[name]

    for name in order:
        resolve(name)
    return order, raw, coords


def strip_rel(style_list: str) -> str:
    """Quita las opciones de posicionamiento relativo, deja el resto (mc* + otras)."""
    s = style_list
    for rx, _ in REL_PATTERNS:
        s = rx.sub("", s)
    # limpiar comas dobles/espacios
    parts = [p.strip() for p in s.split(",") if p.strip()]
    return ", ".join(parts)


def rebuild(block: str, order, raw, coords) -> str:
    """Reescribe cada \node con at (x,y) y estilo aliased root/branch/subbranch."""
    alias = {"mcroot": "root", "mcbranch": "branch", "mcleaf": "subbranch", "mcsub": "subbranch"}
    # construir nuevas líneas de nodo
    def node_line(name):
        style_list, text = raw[name]
        bs = base_style(style_list)
        rest = strip_rel(style_list)
        # anteponer el alias que el optimizador reconoce, conservando el mc* real para apariencia
        opt_style = alias.get(bs, "subbranch")
        # el ALIAS primero (el optimizador toma split(',')[0]); luego el estilo real mc* (apariencia)
        # rest ya empieza por el mc* base; anteponemos el alias reconocido
        new_style = f"{opt_style}, {rest}" if rest else opt_style
        x, y = coords[name]
        return f"\\node[{new_style}] ({name}) at ({x:.2f},{y:.2f}) {{{text}}};"

    # reemplazar cada nodo por su versión absoluta
    def repl(m):
        name = m.group("name").strip()
        return node_line(name)

    return NODE_RE.sub(repl, block)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tex", type=pathlib.Path)
    ap.add_argument("--label", default="")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    tex = args.tex.read_text(encoding="utf8")
    s, e, block = extract_block(tex, args.label)
    order, raw, coords = solve_coords(block)
    new_block = rebuild(block, order, raw, coords)
    # definir alias de estilos + minimum height para que el optimizador lea dims
    # (insertamos \tikzset tras \begin{tikzpicture})
    inject = (
        "\n% alias para optimizador de choques (root/branch/subbranch con minimum height)\n"
        "\\tikzset{root/.style={minimum height=1.2cm, text width=3.3cm},"
        " branch/.style={minimum height=0.9cm, text width=2.5cm},"
        " subbranch/.style={minimum height=0.95cm, text width=2.6cm}}\n"
    )
    new_block = new_block.replace("]\n", "]" + inject + "\n", 1)
    new_tex = tex[:s] + new_block + tex[e:]
    if args.write:
        args.tex.write_text(new_tex, encoding="utf8")
        print(f"escrito: {args.tex} ({len(order)} nodos a coordenadas absolutas)")
    else:
        print(new_block)
        print(f"\n--- {len(order)} nodos; coords muestra ---")
        for n in order[:8]:
            print(n, "->", tuple(round(c, 2) for c in coords[n]))


if __name__ == "__main__":
    main()
