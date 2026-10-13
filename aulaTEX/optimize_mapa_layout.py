#!/usr/bin/env python3
r"""Optimizador de LAYOUT de mapa conceptual (mc*) para eliminar choques,
empalmes, palabras de enlace comidas y huecos, llenando bien la página landscape.

Reutilizable para cualquier reporte de mapa conceptual del proyecto que use los
estilos mcroot/mcbranch/mcleaf/mcsub con posicionamiento relativo below=/left=/right=.

Flujo:
 1. Extrae el bloque tikzpicture del mapa (root + mcbranch) del .tex.
 2. Convierte el posicionamiento relativo a coordenadas absolutas (cadena de refs).
 3. Corre un motor de FUERZA DIRIGIDA (repulsión entre cajas + resortes a ancla +
    límites de página) hasta 0 solapes o convergencia, además de las ETIQUETAS de
    enlace (midpoints) como pseudo-nodos para evitar que queden "comidas".
 4. Renderiza cada cierto nº de iteraciones un PNG usando el PREÁMBULO REAL de estilos
    mc* extraído del documento (para ver el resultado fiel).
 5. Reinyecta las coordenadas absolutas al .tex real (el primer nodo mantiene at (0,0)
    para la raíz) reemplazando el posicionamiento relativo; recompilar aparte.

Uso:
  python aulaTEX/optimize_mapa_layout.py <tex> --iters 400 --write
  python aulaTEX/optimize_mapa_layout.py <tex> --iters 400            # dry-run (no escribe)
"""
from __future__ import annotations

import argparse
import math
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass, field

# --- dimensiones por estilo (cm): text width + 2*inner sep (ancho), alto por líneas ---
STYLE_W = {"mcroot": 3.3 + 0.9, "mcbranch": 2.5 + 0.7, "mcleaf": 2.7 + 0.6, "mcsub": 2.5 + 0.5}
STYLE_H = {"mcroot": 1.25, "mcbranch": 1.05, "mcleaf": 1.35, "mcsub": 1.25}

NODE_RE = re.compile(
    r"\\node\[(?P<style>[^\]]+)\]\s*\((?P<name>[^)]+)\)\s*"
    r"(?:at\s*\((?P<x>-?[0-9.]+),\s*(?P<y>-?[0-9.]+)\)\s*)?"
    r"\{(?P<text>(?:[^{}]|\{[^{}]*\})*)\}\s*;",
    re.S,
)
DRAW_RE = re.compile(
    r"\\draw\[(?P<opt>[^\]]*)\]\s*\((?P<a>[A-Za-z0-9_]+)\)\s*(?P<mid>--|to\[[^\]]*\])\s*"
    r"node\[mclabel(?:[^\]]*)\]\{(?P<label>(?:[^{}]|\{[^{}]*\})*)\}\s*\((?P<b>[A-Za-z0-9_]+)\)\s*;",
    re.S,
)

REL_PATTERNS = [
    (re.compile(r"below left=(?P<a>[0-9.]+)cm and (?P<b>[0-9.]+)cm of (?P<ref>[A-Za-z0-9_]+)"), "below_left"),
    (re.compile(r"below right=(?P<a>[0-9.]+)cm and (?P<b>[0-9.]+)cm of (?P<ref>[A-Za-z0-9_]+)"), "below_right"),
    (re.compile(r"below=(?P<a>[0-9.]+)cm of (?P<ref>[A-Za-z0-9_]+)"), "below"),
    (re.compile(r"left=(?P<a>[0-9.]+)cm of (?P<ref>[A-Za-z0-9_]+)"), "left"),
    (re.compile(r"right=(?P<a>[0-9.]+)cm of (?P<ref>[A-Za-z0-9_]+)"), "right"),
]


@dataclass
class Node:
    name: str
    style: str
    text: str
    x: float
    y: float
    ax: float  # ancla
    ay: float
    pinned: bool = False
    is_label: bool = False  # pseudo-nodo: etiqueta de enlace (mclabel)
    a: str = ""             # nodo origen de la arista (solo labels)
    b: str = ""             # nodo destino de la arista (solo labels)


def base_style(s: str) -> str:
    return s.split(",")[0].strip()


# ancho aprox de una etiqueta mclabel (font \tiny\itshape): ~0.11cm por carácter, alto ~0.30cm
# LABEL_CLEARANCE: factor global de holgura de la caja de etiqueta (para que place_labels
# reserve más margen alrededor de la etiqueta y no quede pegada a los nodos).
LABEL_CLEARANCE = 1.0


def label_dims(text: str) -> tuple[float, float]:
    w = max(0.6, 0.115 * len(text.strip()) + 0.15)
    return (w * LABEL_CLEARANCE, 0.34 * LABEL_CLEARANCE)


def parse_edge_labels(block: str):
    """Devuelve lista de (a, b, label_text) de las aristas \\draw ... node[mclabel]{...}."""
    edges = []
    for m in DRAW_RE.finditer(block):
        edges.append((m.group("a").strip(), m.group("b").strip(), m.group("label")))
    return edges


def extract_block(tex: str):
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


def extract_style_preamble(tex: str) -> str:
    """Extrae los \\definecolor mc* y el \\tikzset con los estilos mc*."""
    lines = []
    # definecolores mc*
    for m in re.finditer(r"\\definecolor\{mc[A-Za-z]+\}\{HTML\}\{[0-9A-Fa-f]{6}\}", tex):
        lines.append(m.group(0))
    lines.append("\\providecommand{\\mcGold}{}\\colorlet{mcGold}{mcAccent}")
    # el tikzset mc* completo
    ts = tex.find("\\tikzset{")
    while ts >= 0:
        # equilibrar llaves
        depth = 0
        i = tex.find("{", ts)
        j = i
        while j < len(tex):
            if tex[j] == "{":
                depth += 1
            elif tex[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        chunk = tex[ts : j + 1]
        if "mcroot" in chunk or "mclink" in chunk:
            lines.append(chunk)
            break
        ts = tex.find("\\tikzset{", j + 1)
    return "\n".join(lines)


def solve_coords(block: str):
    order, raw = [], {}
    abs_xy: dict[str, tuple[float, float]] = {}
    for m in NODE_RE.finditer(block):
        name = m.group("name").strip()
        order.append(name)
        raw[name] = (m.group("style"), m.group("text"))
        if m.group("x") is not None:
            abs_xy[name] = (float(m.group("x")), float(m.group("y")))
    coords: dict[str, tuple[float, float]] = {}

    def resolve(name):
        if name in coords:
            return coords[name]
        # si el nodo ya trae coordenada absoluta at (x,y), usarla directamente
        if name in abs_xy:
            coords[name] = abs_xy[name]
            return coords[name]
        style_list, _ = raw[name]
        bs = base_style(style_list)
        rel = None
        for rx, kind in REL_PATTERNS:
            mm = rx.search(style_list)
            if mm:
                rel = (kind, mm)
                break
        if rel is None:
            coords[name] = (0.0, 0.0)
            return coords[name]
        kind, mm = rel
        ref = mm.group("ref")
        rx0, ry0 = resolve(ref)
        ref_bs = base_style(raw[ref][0])
        hh_ref, hh_me = STYLE_H.get(ref_bs, 1.0) / 2, STYLE_H.get(bs, 1.0) / 2
        hw_ref, hw_me = STYLE_W.get(ref_bs, 2.8) / 2, STYLE_W.get(bs, 2.8) / 2
        a = float(mm.group("a"))
        if kind == "below":
            x, y = rx0, ry0 - (hh_ref + a + hh_me)
        elif kind == "left":
            x, y = rx0 - (hw_ref + a + hw_me), ry0
        elif kind == "right":
            x, y = rx0 + (hw_ref + a + hw_me), ry0
        elif kind == "below_left":
            b = float(mm.group("b"))
            x, y = rx0 - (hw_ref + b + hw_me), ry0 - (hh_ref + a + hh_me)
        else:  # below_right
            b = float(mm.group("b"))
            x, y = rx0 + (hw_ref + b + hw_me), ry0 - (hh_ref + a + hh_me)
        coords[name] = (x, y)
        return coords[name]

    for n in order:
        resolve(n)
    nodes = {}
    for n in order:
        bs = base_style(raw[n][0])
        x, y = coords[n]
        nodes[n] = Node(n, bs, raw[n][1], x, y, x, y, pinned=(n == "root"))
    return order, raw, nodes


def bbox(n: Node):
    if n.is_label:
        w, h = label_dims(n.text)
        pad = 0.05
        return (n.x - w / 2 - pad, n.y - h / 2 - pad, n.x + w / 2 + pad, n.y + h / 2 + pad)
    pad = 0.10
    hw = STYLE_W.get(n.style, 2.8) / 2 + pad
    hh = STYLE_H.get(n.style, 1.0) / 2 + pad
    return (n.x - hw, n.y - hh, n.x + hw, n.y + hh)


def sync_labels(nodes):
    """Recoloca cada etiqueta en el punto medio de su arista (tras mover los nodos)."""
    for n in nodes.values():
        if n.is_label and n.a in nodes and n.b in nodes:
            na, nb = nodes[n.a], nodes[n.b]
            n.x = (na.x + nb.x) / 2
            n.y = (na.y + nb.y) / 2


def overlap(a: Node, b: Node):
    ax1, ay1, ax2, ay2 = bbox(a)
    bx1, by1, bx2, by2 = bbox(b)
    return (min(ax2, bx2) - max(ax1, bx1), min(ay2, by2) - max(ay1, by1))


def _pair_relevant(a: Node, b: Node) -> bool:
    """Ignora el par etiqueta-vs-sus-propios-extremos (siempre solapan por construcción)."""
    if a.is_label and (b.name == a.a or b.name == a.b):
        return False
    if b.is_label and (a.name == b.a or a.name == b.b):
        return False
    if a.is_label and b.is_label:
        # dos etiquetas que comparten extremo (cadena) suelen quedar cerca; se cuentan igual
        return True
    return True


def count_overlaps(nodes) -> int:
    arr = list(nodes.values())
    c = 0
    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):
            if not _pair_relevant(arr[i], arr[j]):
                continue
            ox, oy = overlap(arr[i], arr[j])
            if ox > 0 and oy > 0:
                c += 1
    return c


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def step(nodes, repulsion, step_max, spring, xlim, ylim):
    arr = list(nodes.values())
    moved = 0
    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):
            a, b = arr[i], arr[j]
            if not _pair_relevant(a, b):
                continue
            ox, oy = overlap(a, b)
            if ox > 0 and oy > 0:
                dx, dy = b.x - a.x, b.y - a.y
                if abs(dx) < 1e-6 and abs(dy) < 1e-6:
                    dx = 0.01
                mag = math.hypot(dx, dy) or 1e-6
                ux, uy = dx / mag, dy / mag
                push = min(step_max, repulsion * (1 + 0.6 * (ox + oy)))
                # Las etiquetas NO se mueven libremente (siguen el midpoint de su arista):
                # si una etiqueta choca con un nodo, se empuja SOLO al nodo real.
                a_movable = (not a.pinned) and (not a.is_label)
                b_movable = (not b.pinned) and (not b.is_label)
                if a_movable and b_movable:
                    a.x -= ux * push * 0.5; a.y -= uy * push * 0.5
                    b.x += ux * push * 0.5; b.y += uy * push * 0.5
                elif a_movable:
                    a.x -= ux * push; a.y -= uy * push
                elif b_movable:
                    b.x += ux * push; b.y += uy * push
                moved += 1
    for n in nodes.values():
        if n.pinned or n.is_label:
            continue
        n.x += (n.ax - n.x) * spring
        n.y += (n.ay - n.y) * spring
        n.x = clamp(n.x, -xlim, xlim)
        n.y = clamp(n.y, -ylim, ylim)
    sync_labels(nodes)  # recolocar etiquetas en los midpoints actualizados
    return moved


def rebuild_block(block: str, nodes) -> str:
    """Reescribe los \\node con coordenadas absolutas, quitando el posicionamiento relativo."""
    def strip_rel(style_list: str) -> str:
        s = style_list
        for rx, _ in REL_PATTERNS:
            s = rx.sub("", s)
        parts = [p.strip() for p in s.split(",") if p.strip()]
        return ", ".join(parts)

    def repl(m):
        name = m.group("name").strip()
        if name not in nodes:
            return m.group(0)
        n = nodes[name]
        rest = strip_rel(m.group("style"))
        return f"\\node[{rest}] ({name}) at ({n.x:.2f},{n.y:.2f}) {{{n.text}}};"

    return NODE_RE.sub(repl, block)


def _label_box_at(cx, cy, text):
    w, h = label_dims(text)
    pad = 0.04
    return (cx - w / 2 - pad, cy - h / 2 - pad, cx + w / 2 + pad, cy + h / 2 + pad)


def _box_overlap_area(bx, ny):
    x1, y1, x2, y2 = bx
    nx1, ny1, nx2, ny2 = ny
    ox = min(x2, nx2) - max(x1, nx1)
    oy = min(y2, ny2) - max(y1, ny1)
    if ox > 0 and oy > 0:
        return ox * oy
    return 0.0


def place_labels(block: str, nodes) -> str:
    r"""HEURÍSTICA EFECTIVA anti-empalme de etiquetas: para cada \draw ... node[mclabel]{txt},
    prueba varias posiciones (pos) a lo largo de la arista Y desplazamientos perpendiculares,
    elige la que MENOS solapa con las cajas de TODOS los nodos y emite
    node[mclabel, pos=P, xshift=..pt, yshift=..pt]. Así la posición real en TikZ coincide con
    una zona libre (no queda 'comida' sobre un nodo)."""
    node_boxes = [bbox(n) for n in nodes.values() if not n.is_label]

    positions = [0.5, 0.44, 0.56, 0.38, 0.62, 0.32, 0.68, 0.26, 0.74, 0.20, 0.80, 0.15, 0.85]
    # desplazamientos perpendiculares (cm) a evaluar (mayores para sacar la etiqueta del nodo)
    perp_offsets = [0.0, 0.3, -0.3, 0.5, -0.5, 0.75, -0.75, 1.05, -1.05, 1.4, -1.4]

    def best_for_edge(na, nb, text):
        if na not in nodes or nb not in nodes:
            return None
        ax, ay = nodes[na].x, nodes[na].y
        bx, by = nodes[nb].x, nodes[nb].y
        dx, dy = bx - ax, by - ay
        mag = math.hypot(dx, dy) or 1e-6
        # perpendicular unitaria
        px, py = -dy / mag, dx / mag
        best = None
        for pos in positions:
            lx = ax + dx * pos
            ly = ay + dy * pos
            for off in perp_offsets:
                cx = lx + px * off
                cy = ly + py * off
                lb = _label_box_at(cx, cy, text)
                area = sum(_box_overlap_area(lb, nb_) for nb_ in node_boxes)
                # penalizar alejarse mucho del midpoint y del centro de la arista
                penalty = abs(pos - 0.5) * 0.15 + abs(off) * 0.05
                score = area + penalty
                if best is None or score < best[0]:
                    best = (score, pos, off, px, py)
        return best

    def repl(m):
        na, nb, text = m.group("a").strip(), m.group("b").strip(), m.group("label")
        mid = m.group("mid")
        opt = m.group("opt")
        best = best_for_edge(na, nb, text)
        if best is None:
            return m.group(0)
        _, pos, off, px, py = best
        xsh = px * off * 28.4527  # cm -> pt
        ysh = py * off * 28.4527
        extra = f"pos={pos:.2f}"
        if abs(off) > 1e-3:
            extra += f", xshift={xsh:.1f}pt, yshift={ysh:.1f}pt"
        return f"\\draw[{opt}] ({na}) {mid} node[mclabel, {extra}]{{{text}}} ({nb});"

    return DRAW_RE.sub(repl, block)


def build_preview(style_preamble: str, block_abs: str, margin=0.5, caption=1.3) -> str:
    return (
        "\\documentclass[a4paper,landscape]{article}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage[T1]{fontenc}\n"
        f"\\usepackage[a4paper,landscape,margin={margin}cm]{{geometry}}\n"
        "\\usepackage{amssymb}\n"
        "\\usepackage{graphicx}\n"
        "\\usepackage[dvipsnames]{xcolor}\n"
        "\\usepackage{tikz}\n"
        "\\usetikzlibrary{arrows.meta,positioning,calc,shapes.geometric}\n"
        + style_preamble
        + "\n\\pagestyle{empty}\n\\begin{document}\n\\noindent\\centering\n"
        "\\resizebox{\\linewidth}{!}{%\n"
        + block_abs
        + "}\n\\end{document}\n"
    )


def render(preview_tex: str, out_dir: pathlib.Path, idx: int) -> bool:
    out_dir.mkdir(parents=True, exist_ok=True)
    tp = out_dir / f"it_{idx:03d}.tex"
    pp = out_dir / f"it_{idx:03d}.pdf"
    tp.write_text(preview_tex, encoding="utf8")
    r = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "-output-directory", str(out_dir), str(tp)],
        capture_output=True, text=True,
    )
    if not pp.exists():
        return False
    subprocess.run(["pdftocairo", "-png", "-singlefile", "-r", "130", str(pp), str(out_dir / f"it_{idx:03d}")],
                   capture_output=True, text=True)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tex", type=pathlib.Path)
    ap.add_argument("--iters", type=int, default=400)
    ap.add_argument("--repulsion", type=float, default=0.5)
    ap.add_argument("--step", type=float, default=0.35)
    ap.add_argument("--spring", type=float, default=0.02)
    ap.add_argument("--xlim", type=float, default=13.8)  # media anchura útil landscape (cm)
    ap.add_argument("--ylim", type=float, default=9.0)   # media altura útil landscape (cm)
    ap.add_argument("--render-every", type=int, default=0)
    ap.add_argument("--out-dir", default=".aulatex-temp/opt-mapa2")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--target-aspect", type=float, default=0.0,
                    help="Si >0, estira Y tras optimizar para que ancho/alto se acerque a este ratio (p.ej. 1.5 llena más el vertical en landscape). Reverifica sin choques.")
    ap.add_argument("--vspread", type=float, default=1.0,
                    help="Factor de separación VERTICAL extra tras optimizar (>1 aleja los nodos en Y para dar aire a las etiquetas; usa el espacio libre del alto).")
    ap.add_argument("--hspread", type=float, default=1.0,
                    help="Factor de separación HORIZONTAL extra tras optimizar (>1 aleja en X sin salir de página).")
    ap.add_argument("--label-clearance", type=float, default=1.0,
                    help="Holgura de la caja de etiqueta para place_labels (>1 reserva más margen y evita empalmes etiqueta-nodo).")
    args = ap.parse_args()

    # aplicar clearance global de etiquetas
    global LABEL_CLEARANCE
    LABEL_CLEARANCE = max(0.5, float(args.label_clearance))

    tex = args.tex.read_text(encoding="utf8")
    s, e, block = extract_block(tex)
    style_preamble = extract_style_preamble(tex)
    order, raw, nodes = solve_coords(block)

    # Añadir las ETIQUETAS DE ENLACE como pseudo-nodos (para detectar empalmes etiqueta<->nodo)
    for idx, (na, nb, ltext) in enumerate(parse_edge_labels(block)):
        if na in nodes and nb in nodes:
            mx = (nodes[na].x + nodes[nb].x) / 2
            my = (nodes[na].y + nodes[nb].y) / 2
            lname = f"__lbl{idx}"
            nodes[lname] = Node(lname, "mclabel", ltext, mx, my, mx, my,
                                is_label=True, a=na, b=nb)

    ov0 = count_overlaps(nodes)
    out_dir = pathlib.Path(args.out_dir)
    best = None
    best_ov = 10**9
    for it in range(1, args.iters + 1):
        moved = step(nodes, args.repulsion, args.step, args.spring, args.xlim, args.ylim)
        ov = count_overlaps(nodes)
        if ov < best_ov:
            best_ov = ov
            best = {n: (nd.x, nd.y) for n, nd in nodes.items()}
        if args.render_every and (it % args.render_every == 0 or ov == 0):
            blk = rebuild_block(block, nodes)
            render(build_preview(style_preamble, blk), out_dir, it)
        if ov == 0 and moved == 0:
            break

    # restaurar mejor configuración
    if best:
        for n, (x, y) in best.items():
            nodes[n].x, nodes[n].y = x, y
    sync_labels(nodes)

    # ESTIRAMIENTO VERTICAL para llenar el alto (evita banda ancha-baja con hueco arriba/abajo).
    # Estira las coordenadas Y de los nodos reales acercando el aspect ratio al objetivo,
    # y reoptimiza brevemente para reacomodar sin choques.
    if args.target_aspect and args.target_aspect > 0:
        reals = [n for n in nodes.values() if not n.is_label]
        xs = [n.x for n in reals]; ys = [n.y for n in reals]
        w = (max(xs) - min(xs)) or 1e-6
        h = (max(ys) - min(ys)) or 1e-6
        cur = w / h
        if cur > args.target_aspect:  # demasiado ancho -> estirar Y y comprimir X
            # repartir la corrección: sqrt para estirar Y y comprimir X a la vez
            ratio = cur / args.target_aspect
            ystretch = min(3.0, ratio ** 0.65)
            xsquash = max(0.55, ratio ** -0.35)
            for n in reals:
                if not n.pinned:
                    n.y *= ystretch
                    n.x *= xsquash
            sync_labels(nodes)
            # reoptimizar SOLO para separar choques, con límites acordes al nuevo marco
            new_xlim = args.xlim * xsquash + 1
            new_ylim = args.ylim * ystretch + 2
            for _ in range(2000):
                moved = step(nodes, args.repulsion, args.step, args.spring, new_xlim, new_ylim)
                if count_overlaps(nodes) == 0 and moved == 0:
                    break
            sync_labels(nodes)

    # SEPARACIÓN EXTRA vertical/horizontal para dar aire a las etiquetas y usar el espacio
    # libre de la página. Escala las coordenadas respecto al centroide; la horizontal se
    # limita para NO exceder el ancho de página (los extremos ya están al máximo).
    if args.vspread != 1.0 or args.hspread != 1.0:
        reals = [n for n in nodes.values() if not n.is_label]
        cx = sum(n.x for n in reals) / len(reals)
        cy = sum(n.y for n in reals) / len(reals)
        # límite horizontal: no crecer más allá del marco actual (evita desbordar)
        cur_halfw = max(abs(n.x - cx) for n in reals) or 1e-6
        max_halfw = args.xlim  # media anchura útil
        hcap = min(args.hspread, max_halfw / cur_halfw)
        hcap = max(1.0, hcap)  # nunca comprimir aquí
        for n in reals:
            if not n.pinned:
                n.y = cy + (n.y - cy) * args.vspread
                n.x = cx + (n.x - cx) * hcap
        sync_labels(nodes)
        # micro-reoptimización solo para deshacer choques nodo-nodo que la expansión no cause
        vy = args.ylim * args.vspread + 3
        vx = args.xlim + 1
        for _ in range(800):
            moved = step(nodes, args.repulsion * 0.6, args.step * 0.7, 0.0, vx, vy)
            if count_overlaps(nodes) == 0 and moved == 0:
                break
        sync_labels(nodes)

    new_block = rebuild_block(block, nodes)
    # HEURÍSTICA anti-empalme de etiquetas: reescribe cada \draw con pos+shift óptimos
    new_block = place_labels(new_block, nodes)
    ov_final = count_overlaps(nodes)
    print(f"overlaps: {ov0} -> {ov_final} (mejor {best_ov}); nodos {len(nodes)}")

    # reportar los pares que aún se empalman (para diagnóstico / ajuste de etiquetas)
    arr = list(nodes.values())
    remaining = []
    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):
            if not _pair_relevant(arr[i], arr[j]):
                continue
            ox, oy = overlap(arr[i], arr[j])
            if ox > 0 and oy > 0:
                tag = lambda n: (f"LABEL[{n.text.strip()[:20]}]({n.a}->{n.b})" if n.is_label else n.name)
                remaining.append(f"{tag(arr[i])}  X  {tag(arr[j])}")
    if remaining:
        print("EMPALMES restantes:")
        for r in remaining:
            print("  -", r)

    # render final siempre
    render(build_preview(style_preamble, new_block), out_dir, 999)
    print(f"preview: {out_dir}/it_999.png")

    if args.write:
        new_tex = tex[:s] + new_block + tex[e:]
        args.tex.write_text(new_tex, encoding="utf8")
        print(f"escrito .tex con coordenadas absolutas optimizadas")


if __name__ == "__main__":
    main()
