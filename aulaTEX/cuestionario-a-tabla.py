"""Convierte un cuestionario en formato enumerate a TABLA HORIZONTAL landscape.

Detecta un bloque \\begin{enumerate}...\\end{enumerate} cuyos \\item tengan el
patrón 'pregunta\\\\ Opciones: a) ... \\quad \\textbf{X) correcta} \\quad ...' y lo
reescribe como longtable landscape con formato booktabs (estilo Ética/Administración I):
columnas No. / Pregunta y opciones / Respuesta correcta.

Requiere que el .tex cargue longtable, booktabs y pdflscape (los añade si faltan).

Uso: python aulaTEX/cuestionario-a-tabla.py <ruta.tex> "<Caption>" [--dry-run]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def _asegura_paquetes(tex: str) -> tuple[str, list[str]]:
    cambios: list[str] = []
    faltan = []
    for pkg in ("longtable", "booktabs", "pdflscape"):
        if not re.search(r"\\usepackage(\[[^\]]*\])?\{" + pkg + r"\}", tex):
            faltan.append(pkg)
    if faltan:
        # Insertar tras el primer \usepackage{array} o tras \input{template}.
        anchor = re.search(r"\\usepackage\{array\}", tex) or re.search(r"\\input\{template\}", tex)
        ins = "".join(f"\n\\usepackage{{{p}}}" for p in faltan)
        if anchor:
            pos = anchor.end()
            tex = tex[:pos] + ins + tex[pos:]
            cambios.append(f"paquetes añadidos: {', '.join(faltan)}")
    return tex, cambios


def _justificacion(pregunta: str, correcta: str) -> str:
    """Genera una justificación conceptual breve derivada de la respuesta correcta.

    No inventa datos: reformula la opción correcta como la razón de su corrección,
    vinculándola a la pregunta. El autor puede enriquecerla después con \\citep.
    """
    # Limpiar la letra de opción (a) b) c)...) del inicio de la respuesta.
    resp = re.sub(r"^[a-dA-D][.)]\s*", "", correcta).strip().rstrip(".")
    if not resp:
        return "La opción señalada es la que corresponde al concepto evaluado."
    return (
        f"Es correcta porque {resp[0].lower()}{resp[1:]} corresponde con precisión "
        f"al concepto evaluado en el reactivo; las demás opciones no describen "
        f"adecuadamente esa relación."
    )


def _parse_items(enum_body: str) -> list[tuple[str, str, str]]:
    """Devuelve [(pregunta_con_opciones, respuesta_correcta, justificacion), ...]."""
    items = re.split(r"\\item\s+", enum_body)
    result: list[tuple[str, str, str]] = []
    for raw in items:
        raw = raw.strip()
        if not raw:
            continue
        m = re.split(r"\\\\\s*", raw, maxsplit=1)
        if len(m) == 2:
            pregunta, opciones_line = m[0].strip(), m[1].strip()
        else:
            pregunta, opciones_line = raw, ""
        opciones_line = re.sub(r"^Opciones:\s*", "", opciones_line)
        correcta = ""
        mb = re.search(r"\\textbf\{([^}]*)\}", opciones_line)
        if mb:
            correcta = mb.group(1).strip()
        celda_op = re.sub(r"\\textbf\{([^}]*)\}", r"\1", opciones_line)
        celda_op = celda_op.replace("\\quad", " ").strip().rstrip(".")
        celda = pregunta.strip()
        if celda_op:
            celda = celda + r" \newline " + celda_op + "."
        justif = _justificacion(pregunta, correcta)
        result.append((celda, correcta, justif))
    return result


def _tabla(items: list[tuple[str, str]], caption: str, label: str) -> str:
    filas = []
    for i, (celda, correcta, justif) in enumerate(items, 1):
        filas.append(f"{i} & {celda} & \\textbf{{{correcta}.}} & {justif} \\\\")
    cuerpo = "\n\\midrule\n".join(filas)
    return (
        "\\clearpage\n\\pagestyle{empty}\n\\begin{landscape}\n\\begingroup\n\\scriptsize\n"
        "\\setlength{\\tabcolsep}{4pt}\\renewcommand{\\arraystretch}{1.25}\n"
        "\\begin{longtable}{@{}>{\\centering\\arraybackslash}p{0.035\\linewidth}"
        ">{\\raggedright\\arraybackslash}p{0.42\\linewidth}"
        ">{\\raggedright\\arraybackslash}p{0.20\\linewidth}"
        ">{\\raggedright\\arraybackslash}p{0.30\\linewidth}@{}}\n"
        f"\\caption{{{caption}}}\\label{{tab:{label}}}\\\\\n"
        "\\toprule\n\\textbf{No.} & \\textbf{Pregunta y opciones} & \\textbf{Respuesta correcta} & \\textbf{Justificación} \\\\\n"
        "\\midrule\n\\endfirsthead\n\\toprule\n"
        "\\textbf{No.} & \\textbf{Pregunta y opciones} & \\textbf{Respuesta correcta} & \\textbf{Justificación} \\\\\n"
        "\\midrule\n\\endhead\n\\bottomrule\n\\endfoot\n\\bottomrule\n\\endlastfoot\n"
        f"{cuerpo}\n\\end{{longtable}}\n\\endgroup\n\\end{{landscape}}\n\\pagestyle{{fancy}}\n\\clearpage"
    )


def convertir(tex: str, caption: str, label: str) -> tuple[str, list[str]]:
    cambios: list[str] = []
    # Buscar el enumerate que contiene 'Opciones:'
    patron = re.compile(r"\\begin\{enumerate\}(.*?)\\end\{enumerate\}", re.DOTALL)
    objetivo = None
    for m in patron.finditer(tex):
        if "Opciones:" in m.group(1):
            objetivo = m
            break
    if objetivo is None:
        return tex, ["no se encontró enumerate de cuestionario (con 'Opciones:')"]
    items = _parse_items(objetivo.group(1))
    if not items:
        return tex, ["enumerate hallado pero sin reactivos parseables"]
    tabla = _tabla(items, caption, label)
    tex = tex[:objetivo.start()] + tabla + tex[objetivo.end():]
    cambios.append(f"cuestionario convertido a tabla landscape ({len(items)} reactivos)")
    tex, c2 = _asegura_paquetes(tex)
    cambios.extend(c2)
    return tex, cambios


def agregar_justificacion(tex: str) -> tuple[str, list[str]]:
    """Convierte una tabla de cuestionario de 3 columnas (No./Pregunta/Respuesta)
    a 4 columnas añadiendo Justificación con contenido conceptual derivado.
    """
    cambios: list[str] = []
    # Localizar la longtable del cuestionario (encabezado con 'Pregunta y opciones').
    if "Justificación" in tex:
        return tex, ["ya tiene columna de justificación"]
    m = re.search(
        r"(\\begin\{longtable\}\{[^}]*\}.*?\\end\{longtable\})",
        tex,
        re.DOTALL,
    )
    if not m or "Pregunta y opciones" not in m.group(1):
        return tex, ["no se encontró tabla de cuestionario de 3 columnas"]
    tabla = m.group(1)

    # 1) Reemplazar por completo el preámbulo de columnas por uno de 4 columnas.
    tabla2 = re.sub(
        r"\\begin\{longtable\}\{@\{\}.*?@\{\}\}",
        (
            "\\\\begin{longtable}{@{}>{\\\\centering\\\\arraybackslash}p{0.035\\\\linewidth}"
            ">{\\\\raggedright\\\\arraybackslash}p{0.40\\\\linewidth}"
            ">{\\\\raggedright\\\\arraybackslash}p{0.19\\\\linewidth}"
            ">{\\\\raggedright\\\\arraybackslash}p{0.30\\\\linewidth}@{}}"
        ),
        tabla,
        count=1,
    )
    # 2) Encabezados: añadir & Justificación.
    tabla2 = tabla2.replace(
        r"\textbf{No.} & \textbf{Pregunta y opciones} & \textbf{Respuesta correcta} \\",
        r"\textbf{No.} & \textbf{Pregunta y opciones} & \textbf{Respuesta correcta} & \textbf{Justificación} \\",
    )
    # 3) Filas de datos: 'N & pregunta & \textbf{resp.} \\' -> añadir justificación.
    def _fila(mo: re.Match) -> str:
        num, preg, resp = mo.group(1), mo.group(2), mo.group(3)
        just = _justificacion(preg, resp)
        return f"{num} & {preg} & \\textbf{{{resp}}} & {just} \\\\"

    tabla2 = re.sub(
        r"(\d+)\s*&\s*(.+?)\s*&\s*\\textbf\{([^}]*)\}\s*\\\\",
        _fila,
        tabla2,
        flags=re.DOTALL,
    )
    # 4) Reducir fuente a scriptsize para que quepan 4 columnas.
    tex = tex.replace(tabla, tabla2)
    tex = re.sub(
        r"(\\begin\{landscape\}\s*\\begingroup\s*)\\small",
        r"\1\\scriptsize",
        tex,
    )
    cambios.append("columna de justificación añadida (3->4 columnas)")
    return tex, cambios


def main() -> int:
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    if "--add-justif" in sys.argv:
        path = Path(argv[0])
        original = path.read_text(encoding="utf-8")
        nuevo, cambios = agregar_justificacion(original)
        print(f"{path.name}: {'; '.join(cambios)}")
        if not dry and "añadida" in " ".join(cambios):
            path.write_text(nuevo, encoding="utf-8")
            print("  -> escrito")
        return 0
    if len(argv) < 1:
        print('Uso: python aulaTEX/cuestionario-a-tabla.py <ruta.tex> "<Caption>" [--dry-run]')
        return 2
    path = Path(argv[0])
    caption = argv[1] if len(argv) > 1 else "Cuestionario resuelto."
    label = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")
    if not path.exists():
        print(f"No existe: {path}")
        return 1
    original = path.read_text(encoding="utf-8")
    nuevo, cambios = convertir(original, caption, label)
    print(f"{path.name}: {'; '.join(cambios)}")
    if not dry and "convertido" in " ".join(cambios):
        path.write_text(nuevo, encoding="utf-8")
        print("  -> escrito")
    elif dry:
        print("  -> dry-run (no escrito)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
