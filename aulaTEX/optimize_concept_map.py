#!/usr/bin/env python3
r"""
Heuristic optimizer for the UnADM Activity 6 conceptual map in TikZ.
- Parses node coordinates and style dimensions from the target .tex file
- Detects pairwise overlaps of rectangular node boxes
- Applies small repulsive adjustments per iteration with springs to anchors
- Optionally shrinks text widths / resize factor when hitting page bounds
- Compiles after each iteration using existing latexmk-build.ps1

Usage:
  python optimize_concept_map.py ..\UnADM\redaccion-en-contextos-virtuales\reporte-redaccion-en-contextos-virtuales-Actividad-6.tex \
      --max-iters 6 --export-png 0 --dry-run 0

Notes:
- Coordinates are in cm (x=1cm, y=1cm in tikzpicture)
- This is heuristic and conservative: keeps clusters at their side, root pinned
- Only edits the TikZ picture block (node coordinates and optional widths)
"""
import argparse
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, Tuple

NODE_RE = re.compile(r"\\node\[(?P<style>[^\]]+)\]\s*\((?P<name>[^)]+)\)\s*at\s*\((?P<x>-?[0-9]+\.?[0-9]*),(?P<y>-?[0-9]+\.?[0-9]*)\)\s*\{")
STYLE_WIDTH_RE = re.compile(r"(?P<style>root|branch|subbranch)\s*/\.style=.*?text width\s*=\s*(?P<width>[0-9]+\.?[0-9]*)cm", re.S)
RESIZE_RE = re.compile(r"\\resizebox\{(?P<scale>[0-9]+\.?[0-9]*)\\linewidth\}\{!\}")

@dataclass
class Node:
    name: str
    style: str
    x: float
    y: float
    w: float  # width cm
    h: float  # height cm (approx)
    anchor: Tuple[float, float]

PAGE_X_LIMIT = 9.6   # ~ half-width cm in the map's coordinate system
PAGE_Y_LIMIT = 6.2   # ~ half-height cm
MARGIN = 0.3         # cm soft margin before shrinking widths
STEP = 0.18          # cm max move per iter
REPULSION = 0.35     # cm magnitude for overlapping pairs
SPRING = 0.05        # spring to anchors
MIN_GAP = 0.22       # cm minimum desired clearance between node boxes

# Conservative heights per style (matches 'minimum height' from TikZ)
STYLE_HEIGHTS = {
    'root': 1.25,
    'branch': 0.95,
    'subbranch': 0.72,
}

CLUSTER_GUARD = {
    'modalidad': (-100.0, 0.0),       # keep at x <= 0
    'autogestion': (-100.0, -0.2),    # slightly left-of-center
    'comunicacion': (0.0, 100.0),     # keep at x >= 0
    'criterios': (0.2, 100.0),        # far right mostly
    'responsabilidad': (-999, 999),   # only y constraint in logic below
}


def parse_styles(tikz_block: str) -> Dict[str, float]:
    widths = {}
    for m in STYLE_WIDTH_RE.finditer(tikz_block):
        widths[m.group('style')] = float(m.group('width'))
    # Fallbacks if not found
    widths.setdefault('root', 4.3)
    widths.setdefault('branch', 2.75)
    widths.setdefault('subbranch', 2.55)
    return widths


def extract_tikz_block(tex: str, label_name: str) -> Tuple[Tuple[int,int], str]:
    label = tex.find(f"\\label{{{label_name}}}")
    if label < 0:
        raise RuntimeError(f"map label not found: {label_name}")
    start = tex.rfind("\\begin{tikzpicture}", 0, label)
    if start < 0:
        raise RuntimeError("tikzpicture start for map not found")
    end = tex.find("\\end{tikzpicture}", start)
    if end < 0 or end > label:
        raise RuntimeError("tikzpicture end for map not found")
    end += len("\\end{tikzpicture}")
    block = tex[start:end]
    if "(root)" not in block or "\\node[branch]" not in block:
        raise RuntimeError(
            "selected tikz block does not look like conceptual map (missing root/branch nodes)"
        )
    return (start, end), block


def parse_nodes(tikz: str, widths: Dict[str, float]) -> Dict[str, Node]:
    nodes: Dict[str, Node] = {}
    for m in NODE_RE.finditer(tikz):
        style = m.group('style').split(',')[0].strip()  # first style token
        if style not in ('root', 'branch', 'subbranch'):
            continue
        name = m.group('name').strip()
        x = float(m.group('x'))
        y = float(m.group('y'))
        w = widths.get(style, 2.8)
        h = STYLE_HEIGHTS.get(style, 0.9)
        nodes[name] = Node(name, style, x, y, w, h, (x, y))
    return nodes


def bbox(n: Node) -> Tuple[float,float,float,float]:
    hw = n.w/2.0 + 0.06
    hh = n.h/2.0 + 0.06
    return (n.x-hw, n.y-hh, n.x+hw, n.y+hh)


def overlap(a: Node, b: Node) -> Tuple[float,float]:
    ax1, ay1, ax2, ay2 = bbox(a)
    bx1, by1, bx2, by2 = bbox(b)
    ox = min(ax2, bx2) - max(ax1, bx1)
    oy = min(ay2, by2) - max(ay1, by1)
    return (ox, oy)


def clearance(a: Node, b: Node) -> Tuple[float,float]:
    ax1, ay1, ax2, ay2 = bbox(a)
    bx1, by1, bx2, by2 = bbox(b)
    gap_x = max(bx1 - ax2, ax1 - bx2, 0.0)
    gap_y = max(by1 - ay2, ay1 - by2, 0.0)
    return (gap_x, gap_y)


def clamp(val, lo, hi):
    return max(lo, min(hi, val))


def adjust_positions(nodes: Dict[str, Node]) -> int:
    moved = 0
    keys = list(nodes.keys())
    for i in range(len(keys)):
        for j in range(i+1, len(keys)):
            a = nodes[keys[i]]
            b = nodes[keys[j]]
            ox, oy = overlap(a, b)
            gap_x, gap_y = clearance(a, b)
            needs_push = False
            severity = 0.0
            if ox > 0 and oy > 0:
                needs_push = True
                severity = ox + oy
            elif gap_x < MIN_GAP and gap_y < MIN_GAP:
                needs_push = True
                severity = (MIN_GAP - gap_x) + (MIN_GAP - gap_y)
            if needs_push:
                # push apart horizontally more than vertically
                dx = REPULSION * (1 if a.x <= b.x else -1)
                dy = 0.5 * REPULSION * (1 if a.y <= b.y else -1)
                boost = 1.0 + 0.5 * severity
                # do not move the root; push the other instead
                if a.style == 'root' and b.style != 'root':
                    b.x += clamp(dx * boost, -STEP, STEP)
                    b.y += clamp(dy * boost, -STEP, STEP)
                elif b.style == 'root' and a.style != 'root':
                    a.x -= clamp(dx * boost, -STEP, STEP)
                    a.y -= clamp(dy * boost, -STEP, STEP)
                else:
                    a.x -= clamp(dx * boost / 2, -STEP, STEP)
                    b.x += clamp(dx * boost / 2, -STEP, STEP)
                    a.y -= clamp(dy * boost / 2, -STEP, STEP)
                    b.y += clamp(dy * boost / 2, -STEP, STEP)
                moved += 1
    # Springs to anchors to preserve overall layout intent
    for n in nodes.values():
        ax, ay = n.anchor
        n.x += clamp((ax - n.x) * SPRING, -STEP, STEP)
        n.y += clamp((ay - n.y) * SPRING, -STEP, STEP)
        # cluster guards
        if n.name.startswith('modalidad') or n.name == 'modalidad':
            n.x = min(n.x, -0.1)
        if n.name.startswith('comunicacion') or n.name == 'comunicacion':
            n.x = max(n.x, 0.1)
        if n.name.startswith('criterios') or n.name == 'criterios':
            n.x = max(n.x, 0.2)
        if n.name.startswith('responsabilidad') or n.name == 'responsabilidad':
            n.y = min(n.y, -0.5)
    return moved


def compute_extents(nodes: Dict[str, Node]) -> Tuple[float,float,float,float]:
    xs1, ys1, xs2, ys2 = [], [], [], []
    for n in nodes.values():
        x1,y1,x2,y2 = bbox(n)
        xs1.append(x1); ys1.append(y1); xs2.append(x2); ys2.append(y2)
    return min(xs1), min(ys1), max(xs2), max(ys2)


def write_nodes_back(tikz: str, nodes: Dict[str, Node]) -> str:
    def repl(m):
        style = m.group('style')
        name = m.group('name').strip()
        x = float(m.group('x'))
        y = float(m.group('y'))
        if name in nodes:
            n = nodes[name]
            return f"\\node[{style}] ({name}) at ({n.x:.2f},{n.y:.2f}) {{"
        return m.group(0)
    return NODE_RE.sub(repl, tikz)


def maybe_shrink_widths(tikz: str, widths: Dict[str,float], factor: float=0.96) -> Tuple[str, Dict[str,float]]:
    def sub_style(src: str, style: str, neww: float) -> str:
        return re.sub(
            rf"({style}/\\.style=.*?text width\s*=\s*)[0-9]+\.?[0-9]*(cm)",
            rf"\\1{neww:.2f}\\2",
            src,
            flags=re.S,
        )
    for s in ('branch', 'subbranch'):
        w = widths.get(s, 0)
        nw = max(2.10 if s == 'subbranch' else 2.30, w * factor)
        if nw < w - 1e-3:
            tikz = sub_style(tikz, s, nw)
            widths[s] = nw
    return tikz, widths


def maybe_adjust_resize(tex: str, grow: bool) -> str:
    m = RESIZE_RE.search(tex)
    if not m:
        return tex
    sc = float(m.group('scale'))
    target = clamp(sc + (0.02 if grow else -0.02), 0.78, 0.96)
    return RESIZE_RE.sub(lambda _: f"\\resizebox{{{target:.2f}\\linewidth}}{{!}}", tex, count=1)


def compile_tex(tex_path: pathlib.Path) -> int:
    # Use existing PowerShell build script for consistency
    ps_script = tex_path.parents[2] / 'aulaTEX' / 'latexmk-build.ps1'
    try:
        res = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ps_script), str(tex_path)],
                             capture_output=True, text=True, check=False)
        sys.stdout.write(res.stdout)
        sys.stderr.write(res.stderr)
        return res.returncode
    except FileNotFoundError:
        return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tex', type=pathlib.Path)
    ap.add_argument('--label', type=str, default='fig:mapa-conceptual-redaccion')
    ap.add_argument('--max-iters', type=int, default=6)
    ap.add_argument('--dry-run', type=int, default=0)
    ap.add_argument('--export-png', type=int, default=0)
    args = ap.parse_args()

    tex_path = args.tex.resolve()
    raw = tex_path.read_text(encoding='utf8')
    (s,e), tikz = extract_tikz_block(raw, args.label)
    widths = parse_styles(tikz)
    nodes = parse_nodes(tikz, widths)

    if not nodes:
        print('No nodes parsed; aborting.', file=sys.stderr)
        sys.exit(2)

    for it in range(args.max_iters):
        moved = adjust_positions(nodes)
        x1,y1,x2,y2 = compute_extents(nodes)
        # Decide if we need to shrink widths at edges
        hit_edge = (x1 < -PAGE_X_LIMIT+MARGIN or x2 > PAGE_X_LIMIT-MARGIN or y1 < -PAGE_Y_LIMIT+MARGIN or y2 > PAGE_Y_LIMIT-MARGIN)
        if hit_edge:
            tikz, widths = maybe_shrink_widths(tikz, widths, factor=0.97)
        if moved == 0 and not hit_edge:
            break

    # Write back
    new_tikz = write_nodes_back(tikz, nodes)
    new_raw = raw[:s] + new_tikz + raw[e:]
    # Grow resize a bit if we created more room
    new_raw = maybe_adjust_resize(new_raw, grow=True)

    if args.dry_run:
        backup = tex_path.with_suffix('.tex.bak')
        backup.write_text(raw, encoding='utf8')
        tex_path.write_text(new_raw, encoding='utf8')
        print('Dry run wrote .bak and updated .tex (no compile).')
        sys.exit(0)

    tex_path.write_text(new_raw, encoding='utf8')
    code = compile_tex(tex_path)
    if code != 0:
        print('Compilation error (see output above).', file=sys.stderr)
        sys.exit(code)

    if args.export_png:
        # Prefer pdftocairo (available) to export PNG
        pdf_path = tex_path.with_suffix('.pdf')
        if pdf_path.exists():
            out_png = pdf_path.with_suffix('.png')
            subprocess.run(['pdftocairo', '-png', '-singlefile', str(pdf_path), str(out_png.with_suffix(''))], check=False)
            print(f'Exported preview: {out_png}')
    print('Optimization completed successfully.')

if __name__ == '__main__':
    main()
