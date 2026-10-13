#!/usr/bin/env python3
r"""
Optimize a TikZ conceptual map snippet without compiling the main report PDF.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, Tuple

NODE_RE = re.compile(r"\\node\s*\[(?P<style>[^\]]+)\]\s*\((?P<name>[^)]+)\)\s*at\s*\((?P<x>-?[0-9]+\.?[0-9]*),\s*(?P<y>-?[0-9]+\.?[0-9]*)\)\s*\{")
STYLE_DEF_RE = {
    "root": re.compile(r"root\s*/\\.style\s*=\s*\{.*?text width\s*=\s*([0-9]+\.?[0-9]*)cm.*?minimum height\s*=\s*([0-9]+\.?[0-9]*)cm", re.S),
    "branch": re.compile(r"branch\s*/\\.style\s*=\s*\{.*?text width\s*=\s*([0-9]+\.?[0-9]*)cm.*?minimum height\s*=\s*([0-9]+\.?[0-9]*)cm", re.S),
    "subbranch": re.compile(r"subbranch\s*/\\.style\s*=\s*\{.*?text width\s*=\s*([0-9]+\.?[0-9]*)cm.*?minimum height\s*=\s*([0-9]+\.?[0-9]*)cm", re.S),
}
DEFAULT_WIDTHS = {"root": 4.25, "branch": 2.75, "subbranch": 2.55}
DEFAULT_HEIGHTS = {"root": 1.25, "branch": 0.95, "subbranch": 0.72}
MIN_GAP_DEFAULT = 0.22


@dataclass
class Node:
    name: str
    style: str
    x: float
    y: float
    w: float
    h: float
    anchor_x: float
    anchor_y: float


def read_source(src: str) -> str:
    if src == "-":
        return sys.stdin.read()
    return pathlib.Path(src).read_text(encoding="utf8")


def extract_tikz_by_label(tex: str, label: str) -> str:
    label_pos = tex.find(f"\\label{{{label}}}")
    if label_pos < 0:
        raise ValueError(f"Label not found: {label}")
    start = tex.rfind("\\begin{tikzpicture}", 0, label_pos)
    end = tex.find("\\end{tikzpicture}", start)
    if start < 0 or end < 0:
        raise ValueError("tikzpicture around label not found")
    return tex[start : end + len("\\end{tikzpicture}")]


def extract_first_tikz(text: str) -> str:
    s = text.find("\\begin{tikzpicture}")
    e = text.find("\\end{tikzpicture}", s)
    if s < 0 or e < 0:
        raise ValueError("No tikzpicture block found")
    return text[s : e + len("\\end{tikzpicture}")]


def parse_style_dims(tikz: str):
    widths = DEFAULT_WIDTHS.copy()
    heights = DEFAULT_HEIGHTS.copy()
    for style, rx in STYLE_DEF_RE.items():
        m = rx.search(tikz)
        if m:
            widths[style] = float(m.group(1))
            heights[style] = float(m.group(2))
    return widths, heights


def parse_nodes(tikz: str, widths: Dict[str, float], heights: Dict[str, float]) -> Dict[str, Node]:
    nodes = {}
    for m in NODE_RE.finditer(tikz):
        style = m.group("style").split(",")[0].strip()
        if style not in ("root", "branch", "subbranch"):
            continue
        name = m.group("name").strip()
        x = float(m.group("x"))
        y = float(m.group("y"))
        nodes[name] = Node(name, style, x, y, widths[style], heights[style], x, y)
    return nodes


def bbox(n: Node):
    pad = 0.06
    return (n.x - n.w / 2 - pad, n.y - n.h / 2 - pad, n.x + n.w / 2 + pad, n.y + n.h / 2 + pad)


def overlap_xy(a: Node, b: Node):
    ax1, ay1, ax2, ay2 = bbox(a)
    bx1, by1, bx2, by2 = bbox(b)
    return (min(ax2, bx2) - max(ax1, bx1), min(ay2, by2) - max(ay1, by1))


def clearance_xy(a: Node, b: Node):
    ax1, ay1, ax2, ay2 = bbox(a)
    bx1, by1, bx2, by2 = bbox(b)
    gap_x = max(bx1 - ax2, ax1 - bx2, 0.0)
    gap_y = max(by1 - ay2, ay1 - by2, 0.0)
    return gap_x, gap_y


def count_overlaps(nodes: Dict[str, Node], min_gap: float = 0.0) -> int:
    arr = list(nodes.values())
    c = 0
    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):
            ox, oy = overlap_xy(arr[i], arr[j])
            if ox > 0 and oy > 0:
                c += 1
                continue
            gap_x, gap_y = clearance_xy(arr[i], arr[j])
            if gap_x < min_gap and gap_y < min_gap:
                c += 1
    return c


def extents(nodes: Dict[str, Node]):
    xs1, ys1, xs2, ys2 = [], [], [], []
    for n in nodes.values():
        x1, y1, x2, y2 = bbox(n)
        xs1.append(x1)
        ys1.append(y1)
        xs2.append(x2)
        ys2.append(y2)
    return min(xs1), min(ys1), max(xs2), max(ys2)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def apply_step(nodes, repulsion, step, spring, xmin, xmax, ymin, ymax, min_gap):
    moved_pairs = 0
    arr = list(nodes.values())
    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):
            a, b = arr[i], arr[j]
            ox, oy = overlap_xy(a, b)
            gap_x, gap_y = clearance_xy(a, b)
            needs_push = False
            severity = 0.0
            if ox > 0 and oy > 0:
                needs_push = True
                severity = ox + oy
            elif gap_x < min_gap and gap_y < min_gap:
                needs_push = True
                severity = (min_gap - gap_x) + (min_gap - gap_y)
            if needs_push:
                dx, dy = b.x - a.x, b.y - a.y
                if dx == 0 and dy == 0:
                    dx = 0.001
                mag = (dx * dx + dy * dy) ** 0.5
                ux, uy = dx / mag, dy / mag
                push = min(step, repulsion * (1.0 + 0.5 * severity))
                a.x -= ux * push * 0.5
                a.y -= uy * push * 0.5
                b.x += ux * push * 0.5
                b.y += uy * push * 0.5
                moved_pairs += 1

    for n in nodes.values():
        n.x += (n.anchor_x - n.x) * spring
        n.y += (n.anchor_y - n.y) * spring
        n.x = clamp(n.x, xmin, xmax)
        n.y = clamp(n.y, ymin, ymax)

    return moved_pairs


def write_nodes_back(tikz, nodes):
    def repl(m):
        style = m.group("style")
        name = m.group("name").strip()
        if name in nodes:
            n = nodes[name]
            return f"\\node[{style}] ({name}) at ({n.x:.2f},{n.y:.2f}) {{"
        return m.group(0)

    return NODE_RE.sub(repl, tikz)


def maybe_shrink_style_widths(tikz, factor):
    def repl(style, min_w, src):
        rx = re.compile(rf"({style}\\s*/\\\\.style\\s*=\\s*\\{{.*?text width\\s*=\\s*)([0-9]+\\.?[0-9]*)(cm)", re.S)

        def _sub(m):
            w = float(m.group(2))
            nw = max(min_w, w * factor)
            return f"{m.group(1)}{nw:.2f}{m.group(3)}"

        return rx.sub(_sub, src, count=1)

    tikz = repl("branch", 2.20, tikz)
    tikz = repl("subbranch", 2.00, tikz)
    return tikz


def build_preview_document(tikz, margin_cm, caption_space_cm):
    usable_height = max(5.0, 21.0 - 2.0 * margin_cm - caption_space_cm)
    return (
        "\\documentclass[a4paper,landscape]{article}\n"
        "\\usepackage[utf8]{inputenc}\n"
        f"\\usepackage[a4paper,landscape,margin={margin_cm:.2f}cm]{{geometry}}\n"
        "\\usepackage[dvipsnames,table]{xcolor}\n"
        "\\usepackage{tikz}\n"
        "\\usetikzlibrary{arrows.meta,positioning,calc,matrix,fit,shapes.geometric,shadows.blur}\n"
        "\\definecolor{cardinalred}{RGB}{140, 21, 21}\n"
        "\\definecolor{dkcyan}{RGB}{0, 123, 167}\n"
        "\\definecolor{dkgray}{RGB}{90, 90, 90}\n"
        "\\definecolor{dkgreen}{RGB}{0, 150, 0}\n"
        "\\definecolor{gray}{RGB}{127, 127, 127}\n"
        "\\definecolor{lbrown}{RGB}{255, 252, 249}\n"
        "\\definecolor{lgray}{RGB}{240, 240, 240}\n"
        "\\definecolor{mauve}{RGB}{150, 0, 210}\n"
        "\\definecolor{mitred}{RGB}{161, 0, 47}\n"
        "\\definecolor{ocre}{RGB}{243, 102, 25}\n"
        "\\pagestyle{empty}\n"
        "\\begin{document}\n"
        "\\noindent\\begin{minipage}[t]["
        f"{usable_height:.2f}cm"
        "]{\\linewidth}\n"
        "\\centering\n"
        + tikz
        + "\n\\end{minipage}\n"
        "\\end{document}\n"
    )


def render_iteration(tex_content, out_dir, iter_idx):
    tex_path = out_dir / f"iter_{iter_idx:03d}.tex"
    pdf_path = out_dir / f"iter_{iter_idx:03d}.pdf"
    png_base = out_dir / f"iter_{iter_idx:03d}"
    tex_path.write_text(tex_content, encoding="utf8")

    try:
        subprocess.run([
            "pdflatex", "-interaction=batchmode", "-halt-on-error",
            "-output-directory", str(out_dir), str(tex_path)
        ], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stdout or "")
        sys.stderr.write(exc.stderr or "")
        return False

    if not pdf_path.exists():
        return False

    try:
        subprocess.run(["pdftocairo", "-png", "-singlefile", str(pdf_path), str(png_base)], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stdout or "")
        sys.stderr.write(exc.stderr or "")
        return False
    return True


def solve(args):
    raw = read_source(args.src)
    tikz = extract_first_tikz(raw) if args.input_mode == "snippet" else extract_tikz_by_label(raw, args.label)

    widths, heights = parse_style_dims(tikz)
    nodes = parse_nodes(tikz, widths, heights)
    if not nodes:
        raise RuntimeError("No nodes parsed from TikZ")

    usable_w = 29.7 - 2.0 * args.margin_cm
    usable_h = 21.0 - 2.0 * args.margin_cm - args.caption_space_cm
    xmin, xmax = -usable_w / 2.0, usable_w / 2.0
    ymin, ymax = -usable_h / 2.0, usable_h / 2.0

    best_tikz = tikz
    best_score = float("inf")
    history = []

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for it in range(1, args.max_iters + 1):
        moved = apply_step(nodes, args.repulsion, args.step, args.anchor_spring, xmin, xmax, ymin, ymax, args.min_gap)
        candidate = write_nodes_back(tikz, nodes)

        ov = count_overlaps(nodes, args.min_gap)
        ex1, ey1, ex2, ey2 = extents(nodes)
        out_penalty = 0.0
        if ex1 < xmin: out_penalty += abs(xmin - ex1)
        if ex2 > xmax: out_penalty += abs(ex2 - xmax)
        if ey1 < ymin: out_penalty += abs(ymin - ey1)
        if ey2 > ymax: out_penalty += abs(ey2 - ymax)

        score = ov * 1000.0 + out_penalty * 100.0 + moved
        render_ok = render_iteration(build_preview_document(candidate, args.margin_cm, args.caption_space_cm), out_dir, it)

        history.append({
            "iter": it,
            "overlaps": ov,
            "moved_pairs": moved,
            "bbox": [ex1, ey1, ex2, ey2],
            "target": [xmin, ymin, xmax, ymax],
            "out_penalty": out_penalty,
            "score": score,
            "render_ok": render_ok,
        })

        if score < best_score:
            best_score = score
            best_tikz = candidate

        if ov == 0 and out_penalty <= 1e-6:
            break

        if it % 6 == 0 and ov > 0:
            tikz = maybe_shrink_style_widths(tikz, args.shrink_factor)
            widths, heights = parse_style_dims(tikz)
            for n in nodes.values():
                n.w = widths.get(n.style, n.w)
                n.h = heights.get(n.style, n.h)

    metrics = {
        "input_mode": args.input_mode,
        "label": args.label,
        "max_iters": args.max_iters,
        "repulsion": args.repulsion,
        "step": args.step,
        "anchor_spring": args.anchor_spring,
        "min_gap": args.min_gap,
        "margin_cm": args.margin_cm,
        "caption_space_cm": args.caption_space_cm,
        "best_score": best_score,
        "history": history,
    }
    return best_tikz, metrics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--input-mode", choices=["full-tex", "snippet"], default="full-tex")
    ap.add_argument("--label", default="fig:mapa-conceptual-redaccion")
    ap.add_argument("--out-dir", default="aulaTEX/preview")
    ap.add_argument("--max-iters", type=int, default=30)
    ap.add_argument("--repulsion", type=float, default=0.58)
    ap.add_argument("--step", type=float, default=0.28)
    ap.add_argument("--anchor-spring", type=float, default=0.08)
    ap.add_argument("--min-gap", type=float, default=MIN_GAP_DEFAULT)
    ap.add_argument("--margin-cm", type=float, default=0.6)
    ap.add_argument("--caption-space-cm", type=float, default=1.5)
    ap.add_argument("--shrink-factor", type=float, default=0.97)
    args = ap.parse_args()

    optimized, metrics = solve(args)
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "optimized.tikz").write_text(optimized, encoding="utf8")
    (out_dir / "optimized-metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf8")
    print(optimized)


if __name__ == "__main__":
    main()
