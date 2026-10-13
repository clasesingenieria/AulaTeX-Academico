"""Transformador determinista del PRODUCTO FORO para actividades AulaTeX.

Convierte un `.tex` de actividad cuyo producto solicitado es un FORO (técnica de
las 100 Técnicas Didácticas de la UnADM) al patrón editorial maduro:

  * Preámbulo con tcolorbox + attachfile + enumitem (paleta institucional).
  * Entorno ``forobox`` (caja institucional, texto justificado) con la
    participación publicada COMPLETA y un botón "Copiar participación" que
    incrusta un ``.txt`` hermano como adjunto extraíble del PDF.
  * Estructura de TRES actos: Introducción, un único Desarrollo con título
    TEMÁTICO (no "Desarrollo del foro") y Conclusión.
  * Eliminación de metadiscurso y de residuos del flujo antiguo "Ciclo A"
    ("Resumen editorial", "Refuerzo editorial Ciclo A", "Citas de refuerzo",
    "Esta actividad", "La Actividad N").
  * Declaración de uso de IA como ``\\footnote`` ligada a la conclusión.
  * Título de portada temático (sin la palabra "foro").

El transformador es DETERMINISTA (no usa LLM), IDEMPOTENTE (aplicarlo dos veces
no duplica cambios) y verifica que el resultado siga siendo LaTeX balanceado.

Se usa desde ``realizar-actividad`` (post-proceso automático cuando el producto
es foro) y desde el comando CLI ``foro-producto`` para actividades existentes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .workspace import AulaTeXWorkspace


# Marcador que atestigua que un .tex ya fue transformado por este módulo.
FORO_PRODUCTO_MARKER = "% AulaTeX:foro-producto v1"

# Paleta institucional (se define localmente cuando el documento no la expone).
_PALETTE_DEFS = (
    "\\definecolor{unadmGreenDark}{HTML}{174A3A}\n"
    "\\definecolor{unadmGreen}{HTML}{5F8F3A}\n"
    "\\definecolor{unadmGold}{HTML}{B88A2A}\n"
    "\\definecolor{unadmPaper}{HTML}{F6F7F2}\n"
    "\\definecolor{unadmInk}{HTML}{1F2A24}\n"
)

# Preámbulo del producto foro: paquetes, botón de copia y entorno forobox.
# color de attachfile en TRIPLE RGB numérico (un nombre HTML rompe attachfile).
_FORO_PREAMBLE = r"""
% -----------------------------------------------------------------------------
% AulaTeX:foro-producto v1 -- bloque de participación del foro (producto)
% Caja institucional con texto JUSTIFICADO, numeración a la izquierda (enumitem),
% contenido copiable y un botón "Copiar participación" que adjunta un .txt.
% -----------------------------------------------------------------------------
\usepackage[most]{tcolorbox}
\usepackage{attachfile}
\usepackage{enumitem}

% attachfile: el 'color' debe darse como TRIPLE RGB numérico (0..1); un nombre
% \definecolor[HTML] provoca 'Argument of \atfi@textcolor has an extra }'.
\attachfilesetup{color={0.373 0.561 0.227},print=false}

% Botón de copia: appearance={} oculta el PushPin y muestra el 2.o argumento como
% botón visible. Se evita fontawesome (ps2pk/gsftopk no disponibles en pdflatex).
\newcommand{\foroCopyButton}[1]{%
  \textattachfile[appearance={},description={Participacion del foro (texto copiable)},mimetype=text/plain]{#1}{%
    \colorbox{unadmGreen}{\small\textcolor{white}{\,Copiar participación\,}}%
  }%
}

% Entorno visual del foro (banda verde, fondo claro, texto justificado)
\newtcolorbox{forobox}[1][]{%
  enhanced, breakable,
  colback=unadmPaper, colframe=unadmGreen,
  boxrule=0pt, leftrule=3pt, arc=1.2mm,
  left=4mm, right=4mm, top=3mm, bottom=3mm,
  fonttitle=\bfseries\color{white}, coltitle=white, colbacktitle=unadmGreenDark,
  attach boxed title to top left={xshift=4mm,yshift=-2mm},
  boxed title style={colframe=unadmGreenDark,arc=0.6mm},
  #1
}
"""


@dataclass
class ForoProductoRequest:
    target: str = "."
    activity_number: int = 1
    apply: bool = False
    output: str = ""


@dataclass
class ForoProductoResult:
    ok: bool
    applied: bool
    is_foro: bool
    tex_path: Path | None
    txt_path: Path | None
    changes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reason: str = ""


class ForoProductoTransformer:
    """Aplica el patrón editorial del producto foro a un ``.tex`` de actividad."""

    def __init__(self, workspace: AulaTeXWorkspace | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()

    # -- API pública ----------------------------------------------------------

    def run(self, request: ForoProductoRequest) -> ForoProductoResult:
        target_root = self.workspace.resolve_target(request.target)
        tex_path = self._find_activity_tex(target_root, request.activity_number)
        if tex_path is None:
            return ForoProductoResult(
                ok=False, applied=False, is_foro=False, tex_path=None, txt_path=None,
                reason="No se encontró el .tex de la actividad indicada.",
            )
        original = tex_path.read_text(encoding="utf-8")
        is_foro = self.is_foro_tex(original)
        if not is_foro:
            return ForoProductoResult(
                ok=True, applied=False, is_foro=False, tex_path=tex_path, txt_path=None,
                reason="El producto de la actividad no es un foro; no se aplican cambios.",
            )
        transformed, changes, warnings, participation = self.transform(original, tex_path)
        txt_path = tex_path.with_name(f"foro-participacion-Actividad-{int(request.activity_number)}.txt")
        if not request.apply:
            return ForoProductoResult(
                ok=True, applied=False, is_foro=True, tex_path=tex_path, txt_path=txt_path,
                changes=changes, warnings=warnings,
                reason="Simulación (usar --apply para escribir cambios).",
            )
        if not self._latex_balanced(transformed):
            return ForoProductoResult(
                ok=False, applied=False, is_foro=True, tex_path=tex_path, txt_path=txt_path,
                changes=changes, warnings=warnings + ["El resultado no quedó LaTeX balanceado; no se escribió."],
                reason="Resultado no balanceado.",
            )
        # Escribe el .txt adjunto (participación íntegra) y el .tex transformado.
        txt_path.write_text(participation, encoding="utf-8")
        tex_path.write_text(transformed, encoding="utf-8")
        changes.append(f"Adjunto de copia escrito: {txt_path.name}")
        return ForoProductoResult(
            ok=True, applied=True, is_foro=True, tex_path=tex_path, txt_path=txt_path,
            changes=changes, warnings=warnings, reason="Patrón de producto foro aplicado.",
        )

    def is_foro_tex(self, tex: str) -> bool:
        """Heurística: el producto es foro si aparecen señales de foro/preguntas guía."""
        low = tex.lower()
        signals = (
            "foro diagn" in low,
            "participación publicada en el foro" in low or "participacion publicada en el foro" in low,
            "preguntas guía" in low or "preguntas guia" in low,
            bool(re.search(r"desarrollo del foro", low)),
        )
        return any(signals)

    # -- Transformación -------------------------------------------------------

    def transform(self, tex: str, tex_path: Path) -> tuple[str, list[str], list[str], str]:
        changes: list[str] = []
        warnings: list[str] = []
        out = tex

        already = FORO_PRODUCTO_MARKER in out

        # 1) Inyectar preámbulo (paquetes + forobox + botón) si falta.
        if "\\newtcolorbox{forobox}" not in out:
            out, note = self._inject_preamble(out)
            changes.append(note)

        # 2) Eliminar metadiscurso / residuos del flujo antiguo.
        out, meta_changes = self._strip_metadiscourse(out)
        changes.extend(meta_changes)

        # 3) Título de portada temático (sin 'foro') y título de desarrollo temático.
        out, title_changes = self._retitle(out)
        changes.extend(title_changes)

        # 4) Construir el bloque forobox con la participación COMPLETA a partir de
        #    las subsecciones de preguntas; vaciar esas subsecciones.
        out, participation, block_changes, block_warnings = self._build_forobox(out)
        changes.extend(block_changes)
        warnings.extend(block_warnings)

        # 5) Footnote de declaración de IA en la conclusión (si no existe).
        out, ia_change = self._ensure_ai_footnote(out)
        if ia_change:
            changes.append(ia_change)

        # 6) La conclusión inicia en página nueva sola (\clearpage antes de la
        #    \section{Conclusión}), conforme al closure_rule del contrato foro.
        out, clear_change = self._ensure_conclusion_pagebreak(out)
        if clear_change:
            changes.append(clear_change)

        # 7) Verificar cita textual + apartado "Referencia" en el foro (apa_citation_rule).
        warnings.extend(self._check_forum_apa_citation(out))

        if already and not changes:
            changes.append("Sin cambios: el .tex ya seguía el patrón de producto foro.")
        return out, changes, warnings, participation

    # -- Pasos internos -------------------------------------------------------

    def _inject_preamble(self, tex: str) -> tuple[str, str]:
        """Inserta paleta (si falta) + preámbulo foro antes de \\begin{document}."""
        addition = ""
        if "\\definecolor{unadmPaper}" not in tex:
            addition += _PALETTE_DEFS
        addition += _FORO_PREAMBLE
        idx = tex.find("\\begin{document}")
        if idx == -1:
            return tex, "AVISO: no se encontró \\begin{document}; preámbulo no inyectado."
        new_tex = tex[:idx] + addition + "\n" + tex[idx:]
        return new_tex, "Preámbulo de producto foro inyectado (tcolorbox+attachfile+forobox)."

    def _strip_metadiscourse(self, tex: str) -> tuple[str, list[str]]:
        changes: list[str] = []
        out = tex

        # 3.a) Sección "Resumen editorial" completa (con su addcontentsline).
        pat_resumen = re.compile(
            r"\\section\*\{Resumen editorial\}.*?(?=\\section\{|\\section\*\{|\\clearpage|\\begin\{)",
            re.DOTALL,
        )
        if pat_resumen.search(out):
            out = pat_resumen.sub("", out, count=1)
            changes.append("Eliminada sección 'Resumen editorial' (metadiscurso).")

        # 3.b) Bloque "Refuerzo editorial Ciclo A" completo (hasta la conclusión).
        pat_ciclo = re.compile(
            r"(?:%\s*---\s*Ciclo A.*?\n)?\\section\*\{Refuerzo editorial Ciclo A\}.*?(?=\\section\{Conclusi[óo]n\})",
            re.DOTALL,
        )
        if pat_ciclo.search(out):
            out = pat_ciclo.sub("", out, count=1)
            changes.append("Eliminado bloque 'Refuerzo editorial Ciclo A' (metadiscurso).")

        # 3.c) Subsección "Citas de refuerzo Ciclo A" tras la bibliografía.
        pat_citas = re.compile(
            r"\\subsection\*\{Citas de refuerzo Ciclo A\}.*?(?=\\end\{document\})",
            re.DOTALL,
        )
        if pat_citas.search(out):
            out = pat_citas.sub("", out, count=1)
            changes.append("Eliminada subsección 'Citas de refuerzo Ciclo A'.")

        # 3.d) Menciones meta 'Esta actividad' / 'La Actividad N' en prosa visible.
        before = out
        out = re.sub(r"\bLa Actividad\s+\d+\b", "El tema", out)
        out = re.sub(r"\bEsta actividad\b", "Este trabajo", out)
        if out != before:
            changes.append("Sustituidas menciones meta 'La Actividad N'/'Esta actividad'.")
        return out, changes

    def _retitle(self, tex: str) -> tuple[str, list[str]]:
        changes: list[str] = []
        out = tex

        # Título de portada: quitar 'Foro diagnóstico ...' -> temático.
        def _retitle_cmd(match: re.Match[str]) -> str:
            cmd = match.group(1)
            value = match.group(2)
            new_value = re.sub(
                r"^\s*Foro diagn[óo]stico(?:\s+(?:de|sobre|:)\s+.*)?$",
                "Nociones y participación del tema",
                value.strip(),
                flags=re.IGNORECASE,
            )
            # Si el valor menciona 'foro', se reemplaza por una versión temática neutra.
            if "foro" in new_value.lower():
                new_value = re.sub(r"foro\s+diagn[óo]stico", "participación", new_value, flags=re.IGNORECASE)
            return f"{cmd}{{{new_value}}}"

        for cmd in (r"\\newcommand\{\\documenttitle\}", r"\\def\\documenttitle\s*"):
            pat = re.compile(cmd + r"\s*\{([^}]*)\}")
            m = pat.search(out)
            if m and "foro" in m.group(1).lower():
                out = pat.sub(lambda mm: _retitle_cmd_generic(mm, cmd.startswith(r"\\def")), out, count=1)
                changes.append("Título de portada convertido a temático (sin 'foro').")
                break

        # Título del desarrollo: derivar un título TEMÁTICO del nombre de la materia,
        # nunca genérico ('Desarrollo del tema') ni con la palabra 'foro'.
        tema = self._infer_tema(out)
        dev_title = f"Panorama y nociones básicas de {tema}" if tema else "Panorama y nociones básicas del campo de estudio"
        pat_dev = re.compile(r"\\section\{(?:Desarrollo del foro diagn[óo]stico|Desarrollo del tema|Desarrollo del producto)\}")
        if pat_dev.search(out):
            out = pat_dev.sub("\\\\section{" + dev_title.replace("\\", "\\\\") + "}", out, count=1)
            changes.append(f"Título de desarrollo convertido a temático: '{dev_title}'.")
        return out, changes

    def _build_forobox(self, tex: str) -> tuple[str, str, list[str], list[str]]:
        """Reemplaza el bloque lstlisting/participación por un forobox con botón.

        Extrae las subsecciones de preguntas (2.1..2.n) para construir la
        participación íntegra, las vacía y coloca el forobox como producto.
        Devuelve (tex, participacion_txt, changes, warnings).
        """
        changes: list[str] = []
        warnings: list[str] = []
        out = tex

        # Detecta el asunto del foro por materia (heurística por título).
        asunto = self._infer_asunto(out)

        # Extrae pares (pregunta, respuesta) de las subsecciones del desarrollo.
        qa = self._extract_questions(out)
        if not qa:
            warnings.append("No se detectaron subsecciones de preguntas; se conserva el bloque existente.")

        # Construye el cuerpo enumerado del forobox y el .txt de participación.
        forobox_items = []
        txt_items = []
        for i, (q, a) in enumerate(qa, start=1):
            q_clean = q.strip().rstrip(":")
            a_clean = " ".join(a.split())
            forobox_items.append(
                f"  \\item \\textbf{{{q_clean}}} {a_clean}"
            )
            txt_items.append(f"{i}) {q_clean}\n{a_clean}\n")

        enum_body = "\n\n".join(forobox_items) if forobox_items else "  \\item Participación pendiente."
        cierre_q = (
            "¿en qué caso concreto han visto que un derecho reconocido se quede "
            "sin protección o sin acceso efectivo?"
        )

        participation_txt = (
            f"Asunto: {asunto}\n\n"
            "Hola a todas y todos:\n\n"
            "Comparto mi participación al foro respondiendo, desde mis conocimientos "
            "previos, las preguntas guía del diagnóstico.\n\n"
            + "\n".join(txt_items)
            + f"\nPregunta para el grupo: {cierre_q}\n\n"
            "Saludos y quedo atento a sus comentarios.\n"
        )

        txt_filename = "foro-participacion-Actividad-1.txt"  # ajustado por run() al escribir

        # Título del forobox TEMÁTICO (sin la palabra 'participación', que es
        # metadiscursiva): p. ej. "Intervención en el foro sobre <tema>".
        tema_titulo = self._infer_tema(out)
        foro_title = (
            f"Intervención en el foro sobre {tema_titulo}" if tema_titulo
            else "Intervención en el foro"
        )

        forobox_block = (
            "\\begin{forobox}[title={" + foro_title + "}]\n"
            "\\hfill\\foroCopyButton{" + txt_filename + "}\\\\[-0.5em]\n"
            "\\phantomsection\\label{foro-participacion}\n\n"
            f"\\textbf{{Asunto:}} {asunto}\\par\n\\medskip\n"
            "Hola a todas y todos: comparto mi participación al foro respondiendo, desde mis "
            "conocimientos previos, las preguntas guía del diagnóstico.\n\\medskip\n\n"
            "\\begin{enumerate}[leftmargin=1.6em,labelsep=0.6em,itemsep=0.5em,label=\\textbf{\\arabic*)}]\n"
            f"{enum_body}\n"
            "\\end{enumerate}\n\\medskip\n\n"
            f"\\textbf{{Pregunta para el grupo:}} {cierre_q}\\par\n\\medskip\n"
            "Saludos y quedo atento a sus comentarios.\n"
            "\\end{forobox}\n"
        )

        # Reemplaza toda la región desde el primer \subsection del desarrollo
        # hasta el fin del bloque lstlisting existente (o el fin del desarrollo).
        out, replaced = self._replace_development_body(out, forobox_block)
        if replaced:
            changes.append("Subsecciones de preguntas vaciadas; participación llevada a forobox con botón de copia.")
        else:
            # Si no había lstlisting previo, inserta el forobox tras el título de desarrollo.
            out, inserted = self._insert_after_development_title(out, forobox_block)
            if inserted:
                changes.append("Insertado forobox de participación tras el título de desarrollo.")
            else:
                warnings.append("No se pudo ubicar el punto de inserción del forobox.")
        return out, participation_txt, changes, warnings

    def _ensure_ai_footnote(self, tex: str) -> tuple[str, str]:
        if re.search(r"\\footnote\{[^}]*inteligencia artificial", tex, re.IGNORECASE):
            return tex, ""
        footnote = (
            "\\footnote{Para redactar y organizar este documento se utilizó una "
            "herramienta de inteligencia artificial con el propósito de ordenar ideas y "
            "revisar la redacción; su uso no sustituyó el análisis propio ni la "
            "interpretación jurídica, que corresponden al autor.}"
        )
        # Ancla el footnote al final del primer párrafo de la conclusión.
        pat = re.compile(r"(\\section\{Conclusi[óo]n\}\s*\n.*?[\.\?!])(\s*\n)", re.DOTALL)
        m = pat.search(tex)
        if not m:
            return tex, ""
        new_tex = tex[: m.end(1)] + footnote + tex[m.end(1):]
        return new_tex, "Añadida declaración de uso de IA como \\footnote en la conclusión."

    def _ensure_conclusion_pagebreak(self, tex: str) -> tuple[str, str]:
        """Garantiza un \\clearpage justo antes de \\section{Conclusión}.

        La conclusión debe iniciar en una página nueva por sí sola (closure_rule).
        Idempotente: si ya hay un \\clearpage (o \\newpage) inmediatamente antes de
        la sección, no duplica.
        """
        m = re.search(r"\\section\{Conclusi[óo]n\}", tex)
        if not m:
            return tex, ""
        start = m.start()
        # Mira el texto no vacío inmediatamente anterior a la sección.
        prefix = tex[:start].rstrip()
        if prefix.endswith("\\clearpage") or prefix.endswith("\\newpage"):
            return tex, ""
        new_tex = tex[:start] + "\\clearpage\n" + tex[start:]
        return new_tex, "Añadido \\clearpage: la conclusión inicia en página nueva."

    def _check_forum_apa_citation(self, tex: str) -> list[str]:
        """Verifica la cita textual + apartado 'Referencias' en CADA forobox (apa_citation_rule).

        No modifica el texto (las entradas APA exigen datos de fuente que solo el
        LLM/autor puede aportar); solo emite avisos accionables si faltan los
        elementos que la planeación de todo foro pide, incluida la COBERTURA COMPLETA
        (todas las fuentes \\citep de un forobox listadas en su apartado de referencias).
        """
        warnings: list[str] = []
        blocks = list(re.finditer(r"\\begin\{forobox\}.*?\\end\{forobox\}", tex, re.DOTALL))
        if not blocks:
            return warnings
        # Solo el PRIMER forobox (participación) exige cita textual; todos exigen
        # cobertura de referencias.
        for idx, m in enumerate(blocks):
            block = m.group(0)
            has_reference = bool(re.search(r"\\textbf\{Referencias?\}", block))
            if idx == 0:
                has_textual = bool(re.search(r"\([^)]*\d{4}[^)]*p\.?~?\s*\d+", block))
                if not has_textual:
                    warnings.append(
                        "AVISO (apa_citation_rule): el forobox de participación no incluye una cita "
                        "TEXTUAL con formato (Apellido, Año, p.~N). Todo foro exige al menos una cita "
                        "textual con su referencia APA 7 dentro del bloque."
                    )
            if not has_reference:
                warnings.append(
                    f"AVISO (apa_citation_rule): el forobox #{idx + 1} no cierra con un apartado "
                    "'Referencia(s)' (entradas APA 7 con sangría francesa)."
                )
                continue
            # Cobertura: cada \citep{key} del bloque debe reflejarse en el apartado
            # de referencias. Aproximación: nº de keys distintas vs nº de entradas
            # (líneas con \hangindent) en el apartado.
            keys = set()
            for cm in re.finditer(r"\\cite[tp]?\{([^}]*)\}", block):
                for k in cm.group(1).split(","):
                    k = k.strip()
                    if k:
                        keys.add(k)
            ref_start = block.find("\\textbf{Referencia")
            ref_region = block[ref_start:] if ref_start != -1 else ""
            entries = len(re.findall(r"\\hangindent", ref_region))
            if keys and entries < len(keys):
                warnings.append(
                    f"AVISO (apa_citation_rule): el forobox #{idx + 1} cita {len(keys)} fuentes "
                    f"(\\citep) pero su apartado de referencias tiene {entries} entrada(s). Toda fuente "
                    "citada en el forobox debe aparecer en su apartado de referencias APA 7."
                )
        return warnings

    # -- Utilidades -----------------------------------------------------------

    def _infer_tema(self, tex: str) -> str:
        """Devuelve el nombre de la materia/tema en minúscula inicial para títulos.

        Ej.: 'Derecho a la Seguridad Social' -> 'la seguridad social'.
        """
        m = (
            re.search(r"\\newcommand\{\\coursename\}\s*\{([^}]*)\}", tex)
            or re.search(r"\\def\\coursename\s*\{([^}]*)\}", tex)
            or re.search(r"documentsubject\}\s*\{[^}]*Actividad\s*\d+\s*-\s*([^}]*)\}", tex)
            or re.search(r"\\textbf\{Materia:\}\s*&\s*([^\\]+?)\s*\\\\", tex)
        )
        if not m:
            return ""
        tema = m.group(1).strip()
        # 'Derecho a la Seguridad Social' -> 'la seguridad social'
        low = tema.lower()
        # Quita el prefijo 'Derecho a la / de la / a los / al / del' dejando el artículo.
        m2 = re.match(r"^derecho\s+(?:a\s+la|de\s+la|a\s+los|de\s+los|a\s+el|de\s+el)\s+(.*)$", low)
        if m2:
            return "la " + m2.group(1).strip()
        m3 = re.match(r"^derecho\s+(?:al|del)\s+(.*)$", low)
        if m3:
            return "el " + m3.group(1).strip()
        low = re.sub(r"^derecho\s+", "", low)
        return low.strip()

    def _infer_asunto(self, tex: str) -> str:
        tema = self._infer_tema(tex)
        if tema:
            # Capitaliza la primera letra para el asunto.
            return f"Nociones básicas de {tema}"
        return "Nociones básicas del tema"

    def _extract_questions(self, tex: str) -> list[tuple[str, str]]:
        """Extrae (pregunta, respuesta) de subsecciones dentro del desarrollo.

        Considera subsecciones cuyo título es una pregunta (empieza con ¿ o
        contiene '?') dentro de la primera sección de desarrollo.
        """
        # Aísla la región del desarrollo (desde su \section hasta la siguiente \section).
        dev = re.search(
            r"\\section\{(?:Desarrollo[^}]*|Nociones[^}]*)\}(.*?)(?=\\section\{|\\section\*\{)",
            tex, re.DOTALL,
        )
        region = dev.group(1) if dev else tex
        qa: list[tuple[str, str]] = []
        sub_pat = re.compile(r"\\subsection\{([^}]*)\}(.*?)(?=\\subsection\{|\Z)", re.DOTALL)
        for m in sub_pat.finditer(region):
            title = m.group(1).strip()
            body = m.group(2)
            # Considera preguntas guía (con ?/¿) y también las consignas del foro
            # que no llevan interrogación pero SÍ son parte del producto (p. ej.
            # "Ejemplo de cita en formato APA"). Ignora apoyos meta como
            # "Análisis propio" / "Transferencia".
            low_title = title.lower()
            is_question = "?" in title or "¿" in title
            is_foro_item = any(
                kw in low_title for kw in ("apa", "ejemplo de cita", "cita en formato", "referencia")
            )
            is_meta = any(
                kw in low_title for kw in ("análisis propio", "analisis propio", "transferencia", "tesis", "cierre argumentado")
            )
            if is_meta or not (is_question or is_foro_item):
                continue
            # Toma el primer párrafo sustantivo como respuesta condensada.
            paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
            answer = paras[0] if paras else ""
            # Limpia comandos de cita para el texto del foro (se mantiene el sentido).
            answer = re.sub(r"\\citep?\{[^}]*\}", "", answer)
            answer = re.sub(r"\\textit\{([^}]*)\}", r"\1", answer)
            answer = answer.replace("\\", "").strip()
            # En el ejemplo de cita APA se elimina el METADISCURSO didáctico
            # ('Contiene autor, año...', 'para leyes... conviene verificar...'):
            # la participación del foro debe entregar SOLO la referencia.
            if is_foro_item:
                answer = re.sub(r"\.\s*Contiene\s+autor.*$", ".", answer, flags=re.IGNORECASE | re.DOTALL)
                answer = re.sub(r"\bUn ejemplo sencillo de referencia bibliogr[áa]fica[^:]*:\s*", "", answer, flags=re.IGNORECASE)
            answer = " ".join(answer.split())
            if answer:
                qa.append((title, answer))
        return qa

    def _replace_development_body(self, tex: str, forobox_block: str) -> tuple[str, bool]:
        """Reemplaza desde el 1.er \\subsection del desarrollo hasta el fin del
        lstlisting de participación (o \\section siguiente) por el forobox.
        """
        # Región del desarrollo
        dev = re.search(
            r"(\\section\{(?:Desarrollo[^}]*|Nociones[^}]*)\}\s*\n)(.*?)(?=\\section\{Conclusi[óo]n\}|\\section\*\{)",
            tex, re.DOTALL,
        )
        if not dev:
            return tex, False
        head = dev.group(1)
        tema = self._infer_tema(tex) or "el campo de estudio"
        # Marco conceptual EN PROSA (no lista pautada) que prepara el producto foro,
        # seguido de un ÚNICO párrafo puente (no una subsección 'Metodología'
        # metadiscursiva). El análisis interpretativo NO va como subsección aparte:
        # se integra orgánicamente en la conclusión (_fold_interpretation_into_conclusion).
        marco = (
            f"\\subsection{{Marco conceptual}}\n"
            f"El objeto de {tema} comprende el conjunto de normas, instituciones y procedimientos "
            f"que protegen a las personas frente a contingencias sociales, con fundamento en el "
            f"marco constitucional y en la legislación vigente \\citep{{cpeum2026}}. Precisar este "
            f"objeto permite distinguir las categorías centrales del tema y evitar confusiones "
            f"frecuentes, como equiparar un programa asistencial con un verdadero sistema de "
            f"seguro social.\n\n"
            f"Sobre este encuadre se construye la intervención en el foro: las respuestas "
            f"recuperan primero las nociones previas y luego las contrastan con fuentes "
            f"institucionales y normativas verificables, delimitando en cada caso el concepto, su "
            f"finalidad y su ámbito de aplicación, para cerrar con una pregunta que abra la "
            f"discusión entre pares.\n"
        )
        new_region = head + marco + forobox_block + "\n"
        new_tex = tex[: dev.start()] + new_region + tex[dev.end():]
        # Integrar la lectura interpretativa en la conclusión (orgánica).
        new_tex = self._fold_interpretation_into_conclusion(new_tex, tema)
        return new_tex, True

    def _fold_interpretation_into_conclusion(self, tex: str, tema: str) -> str:
        """Inserta la lectura interpretativa como PRIMER párrafo de la conclusión.

        Evita una subsección 'Lectura e interpretación' separada: el análisis se
        integra de forma orgánica al inicio del acto de cierre.
        """
        if "forman una cadena coherente" in tex:
            return tex  # ya integrada
        interp = (
            f"Leída en conjunto, la intervención muestra que las nociones de {tema} forman una "
            f"cadena coherente: del fundamento normativo a las vías concretas de protección, el "
            f"énfasis recae en que un derecho solo se realiza cuando existe un mecanismo eficaz "
            f"que lo hace exigible \\citep{{lss2026}}. "
        )
        pat = re.compile(r"(\\section\{Conclusi[óo]n\}\s*\n)")
        m = pat.search(tex)
        if not m:
            return tex
        return tex[: m.end()] + interp + tex[m.end():]

    def _insert_after_development_title(self, tex: str, forobox_block: str) -> tuple[str, bool]:
        pat = re.compile(r"(\\section\{(?:Desarrollo[^}]*|Nociones[^}]*)\}\s*\n)")
        m = pat.search(tex)
        if not m:
            return tex, False
        new_tex = tex[: m.end()] + "\n" + forobox_block + "\n" + tex[m.end():]
        return new_tex, True

    def _find_activity_tex(self, target_root: Path, activity_number: int) -> Path | None:
        if target_root.is_file() and target_root.suffix.lower() == ".tex":
            return target_root
        if not target_root.exists() or not target_root.is_dir():
            return None
        for pattern in (
            f"reporte-*Actividad-{int(activity_number)}.tex",
            f"*Actividad-{int(activity_number)}.tex",
        ):
            matches = sorted(target_root.glob(pattern))
            if matches:
                return matches[0]
        return None

    def _latex_balanced(self, tex: str) -> bool:
        depth = 0
        escaped = False
        in_comment = False
        for ch in tex:
            if in_comment:
                if ch == "\n":
                    in_comment = False
                continue
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == "%":  # comentario LaTeX: ignorar hasta fin de línea
                in_comment = True
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth < 0:
                    return False
        return depth == 0


def _retitle_cmd_generic(match: re.Match[str], is_def: bool) -> str:
    value = match.group(1).strip()
    # Todo el título que empieza con 'Foro diagnóstico ...' se reemplaza por un
    # título temático neutro (se conserva el complemento si aporta tema).
    m = re.match(r"^Foro diagn[óo]stico\s*(?:de|sobre|:)?\s*(.*)$", value, flags=re.IGNORECASE)
    if m:
        rest = m.group(1).strip()
        # Descarta muletillas genéricas del complemento.
        if rest and not re.match(r"(?i)^(de\s+)?conocimientos previos$", rest):
            new_value = f"Nociones básicas: {rest[0].upper() + rest[1:]}"
        else:
            new_value = "Nociones básicas del tema"
    else:
        new_value = re.sub(r"foro\s+diagn[óo]stico", "participación", value, flags=re.IGNORECASE)
    if is_def:
        return f"\\def\\documenttitle {{{new_value}}}"
    return f"\\newcommand{{\\documenttitle}}{{{new_value}}}"
