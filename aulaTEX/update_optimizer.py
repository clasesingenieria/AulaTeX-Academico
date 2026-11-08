import os, sys, re
from pathlib import Path

path = Path("aulaTEX/optimize_mapa_layout.py")
text = path.read_text(encoding="utf-8")

# 1. Add os import if not present
if "import os" not in text:
    text = text.replace("import pathlib\n", "import os\nimport pathlib\n")

# 2. Update bbox
old_bbox = """def bbox(n: Node):
    if n.is_label:
        w, h = label_dims(n.text)
        pad = 0.05
        return (n.x - w / 2 - pad, n.y - h / 2 - pad, n.x + w / 2 + pad, n.y + h / 2 + pad)
    pad = 0.10
    hw = STYLE_W.get(n.style, 2.8) / 2 + pad
    hh = STYLE_H.get(n.style, 1.0) / 2 + pad
    return (n.x - hw, n.y - hh, n.x + hw, n.y + hh)"""

new_bbox = """def bbox(n: Node):
    if n.is_label:
        w, h = label_dims(n.text)
        pad = 0.05
        return (n.x - w / 2 - pad, n.y - h / 2 - pad, n.x + w / 2 + pad, n.y + h / 2 + pad)
    pad = 0.10
    hw = STYLE_W.get(n.style, 2.8) / 2 + pad
    num_breaks = n.text.count(r"\\\\")
    clean_txt = re.sub(r"\\[a-zA-Z]+", "", n.text)
    raw_lines = max(1, num_breaks + 1, len(clean_txt) // 30 + 1)
    est_h = max(STYLE_H.get(n.style, 1.0), raw_lines * 0.42 + 0.3)
    hh = est_h / 2 + pad
    return (n.x - hw, n.y - hh, n.x + hw, n.y + hh)"""

text_norm = text.replace("\r\n", "\n")
old_bbox_norm = old_bbox.replace("\r\n", "\n")
assert old_bbox_norm in text_norm, "old_bbox not found!"
text_norm = text_norm.replace(old_bbox_norm, new_bbox)

# 3. Update render
old_render = """def render(preview_tex: str, out_dir: pathlib.Path, idx: int) -> bool:
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
    return True"""

new_render = """def render(preview_tex: str, out_dir: pathlib.Path, idx: int) -> bool:
    out_dir.mkdir(parents=True, exist_ok=True)
    tp = out_dir / f"it_{idx:03d}.tex"
    pp = out_dir / f"it_{idx:03d}.pdf"
    tp.write_text(preview_tex, encoding="utf8")
    env = os.environ.copy()
    if sys.platform == "win32" and "C:\\\\texlive\\\\2026\\\\bin\\\\windows" not in env.get("PATH", ""):
        env["PATH"] = "C:\\\\texlive\\\\2026\\\\bin\\\\windows;" + env.get("PATH", "")
    r = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "-output-directory", str(out_dir), str(tp)],
        env=env, capture_output=True, text=True,
    )
    if not pp.exists():
        return False
    try:
        import pymupdf
        doc = pymupdf.open(pp)
        pix = doc[0].get_pixmap(dpi=130)
        pix.save(str(out_dir / f"it_{idx:03d}.png"))
        return True
    except Exception:
        pass
    subprocess.run(["pdftocairo", "-png", "-singlefile", "-r", "130", str(pp), str(out_dir / f"it_{idx:03d}")],
                   capture_output=True, text=True)
    return True"""

old_render_norm = old_render.replace("\r\n", "\n")
assert old_render_norm in text_norm, "old_render not found!"
text_norm = text_norm.replace(old_render_norm, new_render)

path.write_text(text_norm, encoding="utf-8")
print("optimize_mapa_layout.py updated successfully!")

