"""Elimina el metadiscurso 'Refuerzo editorial Ciclo A' de un .tex de actividad.

Quita de forma segura (solo bloques bien delimitados):
- El bloque '% --- Ciclo A: ...' ... '% --- Fin Ciclo A ---' (incluye la
  \\section*{Refuerzo editorial Ciclo A} y sus subsecciones genéricas).
- El apartado '\\subsection*{Citas de refuerzo Ciclo A}' y su párrafo.
- Sustituye 'La Actividad N', 'Esta actividad', 'el producto solicitado' por
  variantes temáticas neutrales en el TEXTO VISIBLE (no en comentarios).

Uso: python aulaTEX/limpiar-metadiscurso-cicloA.py <ruta.tex> [--dry-run]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def limpiar(tex: str) -> tuple[str, list[str]]:
    cambios: list[str] = []

    # 1) Bloque delimitado por marcadores Ciclo A.
    patron_bloque = re.compile(
        r"\n?% --- Ciclo A:.*?% --- Fin Ciclo A ---\n?",
        re.DOTALL,
    )
    if patron_bloque.search(tex):
        tex = patron_bloque.sub("\n", tex)
        cambios.append("bloque '--- Ciclo A ... --- Fin Ciclo A ---' eliminado")

    # 2) Sección visible \section*{Refuerzo editorial Ciclo A} hasta antes de la
    #    siguiente \section (por si no tuviera los marcadores de comentario).
    patron_seccion = re.compile(
        r"\\section\*\{\s*Refuerzo editorial Ciclo A\s*\}.*?(?=\\section\b)",
        re.DOTALL,
    )
    if patron_seccion.search(tex):
        tex = patron_seccion.sub("", tex)
        cambios.append("\\section*{Refuerzo editorial Ciclo A} eliminada")

    # 3) Apartado \subsection*{Citas de refuerzo Ciclo A} + su párrafo, hasta la
    #    siguiente sección/subsección o \end{document}.
    patron_citas = re.compile(
        r"\\subsection\*\{\s*Citas de refuerzo Ciclo A\s*\}.*?(?=\\section\b|\\subsection\b|\\end\{document\})",
        re.DOTALL,
    )
    if patron_citas.search(tex):
        tex = patron_citas.sub("", tex)
        cambios.append("\\subsection*{Citas de refuerzo Ciclo A} eliminada")

    # 4) Metadiscurso en texto visible (respeta comentarios: se procesa línea a línea).
    reemplazos = [
        (re.compile(r"\bLa Actividad\s+\d+\b"), "El cuestionario resuelto"),
        (re.compile(r"\bEsta actividad\b"), "El desarrollo"),
        (re.compile(r"\besta actividad\b"), "este desarrollo"),
        (re.compile(r"el producto solicitado"), "el cuestionario resuelto"),
    ]
    nuevas: list[str] = []
    hits_texto = 0
    for linea in tex.splitlines(keepends=True):
        sin_com = linea.split("%", 1)[0]
        if sin_com.strip():
            for rx, rep in reemplazos:
                if rx.search(sin_com):
                    # Reemplazar solo en la parte de código (antes del %).
                    if "%" in linea:
                        code, _, comment = linea.partition("%")
                        code = rx.sub(rep, code)
                        linea = code + "%" + comment
                    else:
                        linea = rx.sub(rep, linea)
                    hits_texto += 1
        nuevas.append(linea)
    tex = "".join(nuevas)
    if hits_texto:
        cambios.append(f"metadiscurso en texto visible sustituido ({hits_texto} línea/s)")

    # 5) Neutralizar \newcommand{\pendiente} si imprime metadiscurso.
    tex2 = re.sub(
        r"\\newcommand\{\\pendiente\}\[1\]\{\\textcolor\{red\}\{[^}]*\}\}",
        r"\\newcommand{\\pendiente}[1]{}",
        tex,
    )
    if tex2 != tex:
        tex = tex2
        cambios.append("\\pendiente neutralizado (sin metadiscurso)")

    return tex, cambios


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    if not args:
        print("Uso: python aulaTEX/limpiar-metadiscurso-cicloA.py <ruta.tex> [--dry-run]")
        return 2
    path = Path(args[0])
    if not path.exists():
        print(f"No existe: {path}")
        return 1
    original = path.read_text(encoding="utf-8")
    nuevo, cambios = limpiar(original)
    if not cambios:
        print(f"{path.name}: sin metadiscurso Ciclo A (nada que hacer)")
        return 0
    print(f"{path.name}: {'; '.join(cambios)}")
    if not dry:
        path.write_text(nuevo, encoding="utf-8")
        print("  -> escrito")
    else:
        print("  -> dry-run (no escrito)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
