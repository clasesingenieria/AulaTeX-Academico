"""Dispatch LaTeX Workshop recipes without importing the editorial/IA stack."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tex")
    parser.add_argument("--tikz", action="store_true")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    tex = Path(args.tex)
    if tex.suffix.lower() != ".tex":
        tex = tex.with_name(tex.name + ".tex")
    if os.name == "nt":
        script = "tikz-export.ps1" if args.tikz else "latexmk-build.ps1"
        command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(root / "scripts" / script), str(tex)]
        if args.tikz:
            command.extend(["-Format", "all"])
    else:
        if args.tikz:
            print("La exportación TikZ PDF/SVG/PNG sigue siendo Windows-only; usa la receta PDF en Linux.", file=sys.stderr)
            return 2
        command = ["bash", str(root / "scripts" / "latexmk-build.sh"), str(tex)]
    try:
        return subprocess.run(command, cwd=root, check=False).returncode
    except OSError as exc:
        print(f"No se pudo iniciar la compilación: {exc}", file=sys.stderr)
        return 127


if __name__ == "__main__":
    raise SystemExit(main())