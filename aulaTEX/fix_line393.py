from pathlib import Path

path = Path("aulaTEX/optimize_mapa_layout.py")
text = path.read_text(encoding="utf-8")
text = text.replace("_, pos, off, px, py = best\n", "_, pos, off, px, py = best[:5]\n")
path.write_text(text, encoding="utf-8")
print("Fixed line 393 in optimize_mapa_layout.py!")

