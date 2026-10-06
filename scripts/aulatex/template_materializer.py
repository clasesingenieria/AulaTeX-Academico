from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .workspace import AulaTeXWorkspace
from .planning_layout import subject_layout


@dataclass(frozen=True)
class MaterializationResult:
    ok: bool
    target_dir: Path
    artifacts: tuple[Path, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class SubjectProfile:
    slug: str
    folder_slug: str
    title: str
    course_code: str
    semester: str
    block: str
    credits: str
    subject_type: str
    activity_number: int


class TemplateMaterializer:
    """Create concrete AulaTeX subject templates from persisted editorial memory."""

    def __init__(self, workspace: AulaTeXWorkspace | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()

    def materialize_subject(self, target: str | Path, *, activity_number: int = 1, force: bool = False) -> MaterializationResult:
        target_dir = self.workspace.resolve_target(target)
        if target_dir == self.workspace.repo_root:
            return MaterializationResult(
                False,
                target_dir,
                (),
                ("No se materializa sobre la raiz del repositorio para evitar sobrescribir README.md.",),
            )
        supported_parent = (self.workspace.repo_root / "UnADM" / "licenciatura-en-derecho-unadm").resolve()
        if target_dir.parent != supported_parent:
            return MaterializationResult(
                False,
                target_dir,
                (),
                ("El materializador actual solo admite materias de UnADM/licenciatura-en-derecho-unadm. "
                 "Utiliza el adaptador institucional de la materia; no se ha creado ni modificado ningun archivo.",),
            )
        target_dir.mkdir(parents=True, exist_ok=True)
        profile = self._profile(target_dir, activity_number)
        memory = self._load_memory(target_dir)
        notes: list[str] = []
        artifacts: list[Path] = []

        for folder in subject_layout(target_dir).values():
            folder.mkdir(parents=True, exist_ok=True)
            artifacts.append(folder)

        files = {
            "README.md": self._render_readme(profile, memory),
            f"COMPILACION-{profile.slug}.md": self._render_compilation(profile),
            f"programa-analitico-{profile.slug}.md": self._render_program(profile, memory),
            f"{profile.slug}.bib": self._render_bib(profile, memory),
            f"reporte-{profile.slug}.tex": self._render_report_tex(profile, memory, activity=False),
            f"reporte-{profile.slug}-Actividad-{profile.activity_number}.tex": self._render_report_tex(profile, memory, activity=True),
            f"presentacion-{profile.slug}.tex": self._render_presentation_tex(profile, memory, activity=False),
            f"presentacion-{profile.slug}-Actividad-{profile.activity_number}.tex": self._render_presentation_tex(profile, memory, activity=True),
            "estructura-aulatex.json": self._render_structure_json(profile, memory),
        }
        for name, text in files.items():
            path = target_dir / name
            if path.exists() and not force:
                notes.append(f"Conservado sin cambios: {self.workspace.relative(path)}")
            else:
                path.write_text(text, encoding="utf-8")
                notes.append(f"Materializado: {self.workspace.relative(path)}")
            artifacts.append(path)

        return MaterializationResult(True, target_dir, tuple(artifacts), tuple(notes))

    def _profile(self, target_dir: Path, activity_number: int) -> SubjectProfile:
        folder_slug = target_dir.name
        slug = re.sub(r"-(lde|lad|mga|isc|imtc)$", "", folder_slug, flags=re.IGNORECASE)
        title = _title_from_slug(slug)
        program_text = ""
        for candidate in target_dir.glob("programa-analitico*.md"):
            program_text = candidate.read_text(encoding="utf-8", errors="replace")
            break
        semester = _first_match(program_text, r"semestre\s+(\d+)", "2")
        block = _first_match(program_text, r"bloque\s+(\d+)", "1")
        credits = _first_match(program_text, r"(\d+)\s*cr[eé]ditos", "8")
        subject_type = "Obligatoria" if re.search(r"obligatoria", program_text, re.IGNORECASE) else "Obligatoria"
        course_code = f"LDE-S{semester}B{block}" if "licenciatura-en-derecho" in str(target_dir).lower() else ""
        return SubjectProfile(slug, folder_slug, title, course_code, semester, block, credits, subject_type, int(activity_number))

    def _load_memory(self, target_dir: Path) -> dict[str, Any]:
      candidates = (
        target_dir / f"memoria-fundacional-{_subject_slug_from_dir(target_dir)}.json",
        target_dir / "memoria-fundacional.json",
      )
      for path in candidates:
        if not path.exists():
          continue
        try:
          payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
          continue
        if isinstance(payload, dict):
          return payload
      return {}

    def _memory_list(self, memory: dict[str, Any], section: str, limit: int = 6) -> list[str]:
        values = memory.get("memoria_fundacional", {}).get(section, [])
        if not isinstance(values, list):
            return []
        return _dedupe([_clean_text(str(value).strip()) for value in values if str(value).strip()])[:limit]

    def _plan_list(self, memory: dict[str, Any], section: str, limit: int = 6) -> list[str]:
        values = memory.get("plan_editorial", {}).get(section, [])
        if not isinstance(values, list):
            return []
        return _dedupe([_clean_text(str(value).strip()) for value in values if str(value).strip()])[:limit]

    def _tex_list(self, memory: dict[str, Any], section: str, limit: int = 6) -> list[str]:
      values = memory.get("tex_editorial", {}).get(section, [])
      if not isinstance(values, list):
        return []
      return _dedupe([_clean_text(str(value).strip()) for value in values if str(value).strip()])[:limit]

    def _render_readme(self, profile: SubjectProfile, memory: dict[str, Any]) -> str:
        return f"""# {profile.title}

Materia de la Licenciatura en Derecho de la UnADM preparada por AulaTeX.

## Estructura canonica

- `reporte-{profile.slug}.tex`: plantilla base de reporte/informe academico.
- `reporte-{profile.slug}-Actividad-{profile.activity_number}.tex`: plantilla inicial de actividad.
- `presentacion-{profile.slug}.tex`: presentacion base.
- `presentacion-{profile.slug}-Actividad-{profile.activity_number}.tex`: presentacion inicial de actividad.
- `{profile.slug}.bib`: bibliografia local verificable.
- `programa-analitico-{profile.slug}.md`: encuadre editorial de la materia.
- `planeaciones-{profile.slug}/`: planeaciones y consignas.
- `referencias-{profile.slug}/`: fuentes, lecturas y documentos de apoyo.
- `referencias-{profile.slug}/notas-{profile.slug}/`: notas por unidad o actividad.
- `assets-{profile.slug}/`: imagenes o evidencias visuales especificas.
- `extractor-aulatex/`: extracciones y fichas documentales.
- `investigacion-aulatex/`: analisis y evidencias de investigacion.

Los materiales academicos se conservan dentro de la materia y son versionables.
No se crean exclusiones Git ni se desvian a data/private. Credenciales y secretos
no son materiales academicos y nunca deben incluirse en estas salidas.

## Control editorial

La memoria fundacional se conserva en `memoria-fundacional-{profile.slug}.json`; `generar-plantilla`
materializa esta carpeta y deja archivos editables para investigar, redactar,
evaluar y compilar sin perder identidad institucional.
"""

    def _render_compilation(self, profile: SubjectProfile) -> str:
        return f"""# Compilacion - {profile.title}

Comandos desde la raiz del repositorio:

```powershell
.\\scripts\\latexmk-build.ps1 .\\UnADM\\licenciatura-en-derecho-unadm\\{profile.folder_slug}\\reporte-{profile.slug}.tex
.\\scripts\\latexmk-build.ps1 .\\UnADM\\licenciatura-en-derecho-unadm\\{profile.folder_slug}\\reporte-{profile.slug}-Actividad-{profile.activity_number}.tex
.\\scripts\\latexmk-build.ps1 .\\UnADM\\licenciatura-en-derecho-unadm\\{profile.folder_slug}\\presentacion-{profile.slug}.tex
```

Validaciones:

- `\\input{{template}}` debe resolver a la plantilla compartida.
- El archivo `.bib` local debe contener toda fuente citada.
- La salida final debe conservar portada institucional UnADM, desarrollo,
  producto solicitado, conclusion y bibliografia.
"""

    def _render_program(self, profile: SubjectProfile, memory: dict[str, Any]) -> str:
        markers = self._memory_list(memory, "research_markers", 8) or [
            "Marco constitucional y normativo de la materia.",
            "Instituciones, sujetos y problemas juridicos relevantes.",
            "Aplicacion practica en contexto mexicano.",
        ]
        lines = [
            f"# Programa analitico editorial - {profile.title}",
            "",
            "## Encuadre institucional",
            "",
            f"Asignatura de la Licenciatura en Derecho de la UnADM ubicada en semestre {profile.semester}, bloque {profile.block}.",
            f"Tipo: {profile.subject_type}. Creditos: {profile.credits}.",
            "",
            "## Proposito de realizacion",
            "",
            "Transformar cada consigna en un producto juridico verificable: problema, fundamento, analisis, evidencia, postura y cierre profesional.",
            "",
            "## Ejes de trabajo",
            "",
        ]
        lines.extend(f"{index}. {item}" for index, item in enumerate(markers[:6], start=1))
        lines.extend(
            [
                "",
                "## Bibliografia base",
                "",
                f"La bibliografia local se concentra en `{profile.slug}.bib` y debe ampliarse solo con fuentes verificadas.",
                "",
            ]
        )
        return "\n".join(lines)

    def _render_bib(self, profile: SubjectProfile, memory: dict[str, Any]) -> str:
        entries = [
            "% Bibliografia local materializada por AulaTeX.",
            "% Revisar vigencia antes de entregar actividades finales.",
            "",
            "@misc{unadmSitioWeb,",
            "  author = {{Universidad Abierta y a Distancia de Mexico}},",
            "  title = {Universidad Abierta y a Distancia de Mexico},",
            "  year = {2026},",
            "  howpublished = {\\url{https://www.unadmexico.mx/}},",
            "  note = {Sitio institucional; consulta: 2026-06-20}",
            "}",
            "",
            "@misc{unadmMallaDerecho2024,",
            "  author = {{Universidad Abierta y a Distancia de Mexico}},",
            "  title = {Malla curricular de la Licenciatura en Derecho},",
            "  year = {2024},",
            "  howpublished = {Archivo local: UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf},",
            "  note = {Documento institucional incluido en assets-unadm}",
            "}",
            "",
        ]
        if "seguridad-social" in profile.slug or _contains(memory, "seguridad social"):
            entries.extend(
                [
                    "@misc{cpeum2026,",
                    "  author = {{Camara de Diputados del H. Congreso de la Union}},",
                    "  title = {Constitucion Politica de los Estados Unidos Mexicanos},",
                    "  year = {2026},",
                    "  howpublished = {\\url{https://www.diputados.gob.mx/LeyesBiblio/pdf/CPEUM.pdf}},",
                    "  note = {Texto vigente; ultima reforma DOF 02-06-2026; consulta: 2026-06-20}",
                    "}",
                    "",
                    "@misc{lss2026,",
                    "  author = {{Camara de Diputados del H. Congreso de la Union}},",
                    "  title = {Ley del Seguro Social},",
                    "  year = {2026},",
                    "  howpublished = {\\url{https://www.diputados.gob.mx/LeyesBiblio/pdf/LSS.pdf}},",
                    "  note = {Texto vigente; ultima reforma DOF 15-01-2026; consulta: 2026-06-20}",
                    "}",
                    "",
                    "@misc{lissste2026,",
                    "  author = {{Camara de Diputados del H. Congreso de la Union}},",
                    "  title = {Ley del Instituto de Seguridad y Servicios Sociales de los Trabajadores del Estado},",
                    "  year = {2026},",
                    "  howpublished = {\\url{https://www.diputados.gob.mx/LeyesBiblio/pdf/LISSSTE.pdf}},",
                    "  note = {Texto vigente; consulta: 2026-06-20}",
                    "}",
                    "",
                ]
            )
        return "\n".join(entries)

    def _render_report_tex(self, profile: SubjectProfile, memory: dict[str, Any], *, activity: bool) -> str:
        title = f"Actividad {profile.activity_number} - {profile.title}" if activity else f"Plantilla base de {profile.title}"
        subtitle = f"Actividad {profile.activity_number} - {profile.title}" if activity else f"Plantilla de reporte - {profile.title}"
        citations = "unadmSitioWeb,unadmMallaDerecho2024"
        if "seguridad-social" in profile.slug:
            citations += ",cpeum2026,lss2026,lissste2026"
        rules = _dedupe(
          self._tex_list(memory, "plantilla", 3)
          + self._tex_list(memory, "reporte", 4)
          + (self._tex_list(memory, "actividad", 2) if activity else [])
          + self._memory_list(memory, "structure_rules", 5)
        )[:7]
        markers = _dedupe(
          (self._tex_list(memory, "actividad", 2) if activity else [])
          + self._memory_list(memory, "research_markers", 5)
        )[:6]
        gates = _dedupe(self._tex_list(memory, "reporte", 3) + self._memory_list(memory, "quality_gates", 5))[:6]
        return self._render_light_report_tex(profile, title, subtitle, citations, rules, markers, gates)
        _legacy_report_template = f"""% AulaTeX - plantilla materializada desde memoria editorial
\\documentclass[
  spanish,
  letterpaper, oneside
]{{article}}

\\def\\documenttitle {{{_latex(title)}}}
\\def\\documentsubtitle {{{_latex(subtitle)}}}
\\def\\documentsubject {{Licenciatura en Derecho}}

\\def\\documentauthor {{Martin Jonathan de la Cruz}}
\\def\\coursename {{{_latex(profile.title)}}}
\\def\\coursecode {{{profile.course_code}}}

\\def\\universityname {{Universidad Abierta y a Distancia de Mexico}}
\\def\\universityfaculty {{Licenciatura en Derecho}}
\\def\\universitydepartment {{{_latex(profile.title)}}}
\\def\\universitydepartmentimage {{departamentos/UnADM}}
\\def\\universitydepartmentimagecfg {{height=1.57cm}}
\\def\\universitylocation {{Roma Norte, Ciudad de Mexico}}

\\def\\authortable {{
  \\begin{{tabular}}{{ll}}
    \\textbf{{Alumno:}} & Martin Jonathan de la Cruz \\\\
    Matricula: & ES2611202040 \\\\
    Figura docente: & Nombre por definir \\\\
    Semestre/Bloque: & {profile.semester} / {profile.block} \\\\
    Tipo/Creditos: & {_latex(profile.subject_type)} / {profile.credits} \\\\
    & \\\\
    \\multicolumn{{2}}{{l}}{{Fecha de realizacion: \\today}} \\\\
    \\multicolumn{{2}}{{l}}{{\\universitylocation}}
  \\end{{tabular}}
}}

\\input{{template}}
\\usepackage{{helvet}}
\\renewcommand{{\\familydefault}}{{\\sfdefault}}
\\usepackage{{array}}
\\usepackage{{longtable}}
\\usepackage{{booktabs}}
\\usepackage{{pdflscape}}
\\usepackage{{tikz}}
\\usetikzlibrary{{arrows.meta,positioning,calc,matrix,fit,shapes.geometric,shadows.blur}}
\\setcitestyle{{authoryear,open={{(}},close={{)}}}}

\\newcommand{{\\pendiente}}[1]{{\\textcolor{{red}}{{[PENDIENTE: #1]}}}}

\\begin{{document}}

\\templatePortrait
\\templatePagecfg
\\onehalfspacing

\\begin{{abstractd}}
  Esta plantilla materializa la memoria editorial de \\textit{{{_latex(profile.title)}}}.
  La entrega debe convertir la consigna en un problema juridico delimitado, con
  fundamento verificable, analisis propio y conclusion aplicable.
\\end{{abstractd}}

\\templateIndex
\\templateFinalcfg

\\section{{Introduccion}}

\\pendiente{{Abrir con una afirmacion fuerte que traduzca la consigna a problema juridico.}}

\\section{{Encuadre institucional y juridico}}

La materia se trabaja desde la identidad academica de la UnADM y desde la
formacion juridica aplicada. La bibliografia local debe sostener el analisis
con fuentes institucionales, normativas y academicas verificables \\citep{{{citations}}}.

\\section{{Memoria editorial aplicada}}

{_latex_itemize(rules or ["Organizar la entrega en problema, marco juridico, analisis, producto, conclusion y referencias."])}

\\section{{Marcadores de investigacion}}

{_latex_itemize(markers or ["Delimitar fuentes oficiales, doctrina pertinente y criterios aplicables antes de redactar."])}

\\section{{Desarrollo del producto}}

\\pendiente{{Insertar aqui el producto solicitado: informe, cuadro, mapa, analisis de caso, matriz, linea de tiempo o ensayo.}}

\\subsection{{Analisis propio}}

\\pendiente{{Explicar la consecuencia juridica del producto y sostener una postura personal argumentada.}}

\\section{{Checklist de calidad}}

{_latex_itemize(gates or ["Verificar citas, bibliografia, coherencia de estructura, ortografia y compilacion."])}

\\section{{Conclusion}}

\\pendiente{{Cerrar con aprendizaje, criterio juridico propio y aplicacion profesional.}}

\\clearpage
\\nocite{{{citations}}}
\\bibliography{{{profile.slug}}}

\\end{{document}}
"""

    def _render_light_report_tex(
        self,
        profile: SubjectProfile,
        title: str,
        subtitle: str,
        citations: str,
        rules: list[str],
        markers: list[str],
        gates: list[str],
    ) -> str:
        return f"""% AulaTeX - plantilla materializada desde memoria editorial
\\documentclass[12pt,letterpaper,oneside]{{article}}
\\usepackage[margin=2.35cm]{{geometry}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage[spanish,es-tabla]{{babel}}
\\usepackage[scaled=.96]{{helvet}}
\\renewcommand{{\\familydefault}}{{\\sfdefault}}
\\usepackage{{setspace}}
\\usepackage{{graphicx}}
\\usepackage[table]{{xcolor}}
\\usepackage{{booktabs}}
\\usepackage{{array}}
\\usepackage{{longtable}}
\\usepackage{{hyperref}}
\\usepackage[authoryear,round]{{natbib}}

\\definecolor{{unadmGreenDark}}{{HTML}}{{174A3A}}
\\definecolor{{unadmGreen}}{{HTML}}{{5F8F3A}}
\\definecolor{{unadmGold}}{{HTML}}{{B88A2A}}
\\definecolor{{unadmPaper}}{{HTML}}{{F6F7F2}}
\\definecolor{{unadmInk}}{{HTML}}{{1F2A24}}
\\hypersetup{{colorlinks=true,linkcolor=unadmGreenDark,citecolor=unadmGreenDark,urlcolor=unadmGreenDark}}
\\setlength{{\\parindent}}{{0pt}}
\\setlength{{\\parskip}}{{0.72em}}
\\onehalfspacing
\\bibliographystyle{{plainnat}}

\\newcommand{{\\pendiente}}[1]{{\\textcolor{{red}}{{[PENDIENTE: #1]}}}}

\\begin{{document}}

\\begin{{titlepage}}
  \\pagecolor{{unadmPaper}}
  \\color{{unadmInk}}
  \\begin{{center}}
    \\vspace*{{0.8cm}}
    \\includegraphics[height=2.05cm]{{img/departamentos/UnADM.pdf}}\\\\[0.7cm]
    {{\\Large Universidad Abierta y a Distancia de Mexico}}\\\\[0.2cm]
    {{\\large Licenciatura en Derecho}}\\\\[1.2cm]
    {{\\color{{unadmGreenDark}}\\rule{{0.82\\linewidth}}{{1.4pt}}}}\\\\[0.55cm]
    {{\\Huge\\bfseries {_latex(title)}\\par}}
    \\vspace{{0.35cm}}
    {{\\Large {_latex(subtitle)}\\par}}
    \\vspace{{0.45cm}}
    {{\\color{{unadmGold}}\\rule{{0.62\\linewidth}}{{1.1pt}}}}\\\\[1.1cm]
    \\begin{{tabular}}{{rl}}
      \\textbf{{Alumno:}} & Martin Jonathan de la Cruz \\\\
      \\textbf{{Matricula:}} & ES2611202040 \\\\
      \\textbf{{Figura docente:}} & Nombre por definir \\\\
      \\textbf{{Materia:}} & {_latex(profile.title)} \\\\
      \\textbf{{Semestre/Bloque:}} & {profile.semester} / {profile.block} \\\\
      \\textbf{{Tipo/Creditos:}} & {_latex(profile.subject_type)} / {profile.credits} \\\\
      \\textbf{{Fecha:}} & \\today
    \\end{{tabular}}
    \\vfill
    {{\\small Roma Norte, Ciudad de Mexico}}
  \\end{{center}}
  \\nopagecolor
\\end{{titlepage}}

\\tableofcontents
\\clearpage

\\section*{{Resumen editorial}}
\\addcontentsline{{toc}}{{section}}{{Resumen editorial}}
Esta plantilla materializa la memoria editorial de \\textit{{{_latex(profile.title)}}}.
La entrega debe convertir la consigna en un problema juridico delimitado, con
fundamento verificable, analisis propio y conclusion aplicable.

\\section{{Introduccion}}
\\pendiente{{Abrir con una afirmacion fuerte que traduzca la consigna a problema juridico.}}

\\section{{Encuadre institucional y juridico}}
La materia se trabaja desde la identidad academica de la UnADM y desde la
formacion juridica aplicada. La bibliografia local debe sostener el analisis
con fuentes institucionales, normativas y academicas verificables \\citep{{{citations}}}.

\\section{{Memoria editorial aplicada}}
{_latex_itemize(rules or ["Organizar la entrega en problema, marco juridico, analisis, producto, conclusion y referencias."])}

\\section{{Marcadores de investigacion}}
{_latex_itemize(markers or ["Delimitar fuentes oficiales, doctrina pertinente y criterios aplicables antes de redactar."])}

\\section{{Desarrollo del producto}}
\\pendiente{{Insertar aqui el producto solicitado: informe, cuadro, mapa, analisis de caso, matriz, linea de tiempo o ensayo.}}

\\subsection{{Analisis propio}}
\\pendiente{{Explicar la consecuencia juridica del producto y sostener una postura personal argumentada.}}

\\section{{Checklist de calidad}}
{_latex_itemize(gates or ["Verificar citas, bibliografia, coherencia de estructura, ortografia y compilacion."])}

\\section{{Conclusion}}
\\pendiente{{Cerrar con aprendizaje, criterio juridico propio y aplicacion profesional.}}

\\clearpage
\\nocite{{{citations}}}
\\bibliography{{{profile.slug}}}

\\end{{document}}
"""

    def _render_informe_tex(self, profile: SubjectProfile, memory: dict[str, Any]) -> str:
        citations = "unadmSitioWeb,unadmMallaDerecho2024"
        if "seguridad-social" in profile.slug:
            citations += ",cpeum2026,lss2026,lissste2026"
        rules = self._memory_list(memory, "structure_rules", 5)
        markers = self._memory_list(memory, "research_markers", 5)
        gates = self._memory_list(memory, "quality_gates", 5)
        return self._render_light_report_tex(
            profile,
            f"Informe academico base de {profile.title}",
            f"Informe academico - {profile.title}",
            citations,
            rules,
            markers,
            gates,
        )

    def _render_presentation_tex(self, profile: SubjectProfile, memory: dict[str, Any], *, activity: bool) -> str:
        title = f"Actividad {profile.activity_number}: {profile.title}" if activity else profile.title
        markers = _dedupe(self._tex_list(memory, "presentacion", 3) + self._memory_list(memory, "research_markers", 4))[:5]
        gates = _dedupe(self._tex_list(memory, "presentacion", 3) + self._memory_list(memory, "quality_gates", 4))[:5]
        guidance = _dedupe(
            self._tex_list(memory, "plantilla", 2)
            + self._tex_list(memory, "presentacion", 4)
            + (self._tex_list(memory, "actividad", 2) if activity else [])
        )[:5]
        return self._render_light_presentation_tex(profile, markers, gates, title, guidance)
        _legacy_beamer_template = f"""% AulaTeX - presentacion materializada desde memoria editorial
\\documentclass[
  spanish,
  aspectratio=169,
  xcolor={{dvipsnames,table}}
]{{beamer}}
\\geometry{{paperwidth=19.2cm,paperheight=10.8cm}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage[spanish,es-tabla]{{babel}}
\\usepackage[scaled=.96]{{helvet}}
\\renewcommand{{\\familydefault}}{{\\sfdefault}}
\\usepackage{{booktabs}}
\\usepackage{{graphicx}}
\\usepackage{{ragged2e}}
\\usepackage{{tikz}}
\\usepackage{{hyperref}}
\\usetikzlibrary{{calc,positioning,fit,shadows.blur}}

\\definecolor{{unadmGreenDark}}{{HTML}}{{174A3A}}
\\definecolor{{unadmGreen}}{{HTML}}{{5F8F3A}}
\\definecolor{{unadmGold}}{{HTML}}{{B88A2A}}
\\definecolor{{unadmPaper}}{{HTML}}{{F6F7F2}}
\\definecolor{{unadmInk}}{{HTML}}{{1F2A24}}

\\mode<presentation>{{
  \\usetheme{{default}}
  \\usefonttheme{{professionalfonts}}
  \\setbeamertemplate{{navigation symbols}}{{}}
  \\setbeamertemplate{{blocks}}[rounded][shadow=false]
}}
\\setbeamersize{{text margin left=0.60cm,text margin right=0.60cm}}
\\setbeamercolor{{background canvas}}{{bg=white}}
\\setbeamercolor{{normal text}}{{fg=unadmInk,bg=white}}
\\setbeamercolor{{structure}}{{fg=unadmGreenDark}}
\\setbeamercolor{{frametitle}}{{fg=white,bg=unadmGreenDark}}
\\setbeamercolor{{block title}}{{fg=white,bg=unadmGreen}}
\\setbeamercolor{{block body}}{{fg=unadmInk,bg=unadmPaper}}
\\setbeamerfont{{title}}{{size=\\LARGE,series=\\bfseries}}
\\setbeamerfont{{frametitle}}{{size=\\large,series=\\bfseries}}
\\setbeamertemplate{{itemize item}}{{\\textcolor{{unadmGreen}}{{\\large$\\blacktriangleright$}}}}
\\setbeamertemplate{{navigation symbols}}{{}}

\\title{{{_latex(title)}}}
\\subtitle{{Licenciatura en Derecho - UnADM}}
\\author{{Martin Jonathan de la Cruz}}
\\date{{\\today}}

\\begin{{document}}

\\begin{{frame}}[plain]
  \\begin{{tikzpicture}}[remember picture,overlay]
    \\fill[unadmGreenDark] (current page.south west) rectangle ([xshift=0.58\\paperwidth]current page.north west);
    \\fill[unadmGreen] ([xshift=0.58\\paperwidth]current page.south west) rectangle (current page.north east);
    \\node[anchor=center,opacity=0.10] at (current page.center) {{\\includegraphics[width=0.72\\paperwidth]{{img/departamentos/UnADM.pdf}}}};
  \\end{{tikzpicture}}
  \\vspace*{{1.6cm}}
  {{\\color{{white}}\\fontsize{{24}}{{29}}\\selectfont\\bfseries {_latex(title)}\\par}}
  \\vspace{{0.25cm}}
  {{\\color{{white!85}}\\large Licenciatura en Derecho - UnADM}}\\\\[0.35cm]
  {{\\color{{unadmGold}}\\rule{{0.58\\linewidth}}{{1.3pt}}}}\\\\[0.35cm]
  {{\\color{{white}}Martin Jonathan de la Cruz}}
\\end{{frame}}

\\begin{{frame}}{{Objetivo editorial}}
  \\begin{{block}}{{Objetivo editable}}
    Convertir la consigna en problema juridico verificable, con evidencia,
    fundamento y postura academica propia.
  \\end{{block}}
  \\begin{{itemize}}
    \\item Semestre: {profile.semester}. Bloque: {profile.block}.
    \\item Tipo: {_latex(profile.subject_type)}. Creditos: {profile.credits}.
    \\item Bibliografia local: \\texttt{{{profile.slug}.bib}}.
  \\end{{itemize}}
\\end{{frame}}

\\begin{{frame}}{{Marcadores de investigacion}}
{_beamer_items(markers or ["Delimitar marco juridico.", "Identificar instituciones y sujetos.", "Vincular problema con practica profesional."])}
\\end{{frame}}

\\begin{{frame}}{{Producto y estructura}}
  \\begin{{enumerate}}
    \\item Problema.
    \\item Marco conceptual y normativo.
    \\item Analisis o producto visual.
    \\item Postura personal.
    \\item Conclusion.
  \\end{{enumerate}}
\\end{{frame}}

\\begin{{frame}}{{Criterios de calidad}}
{_beamer_items(gates or ["Citas verificables.", "Bibliografia local consistente.", "Compilacion limpia.", "Redaccion formal."])}
\\end{{frame}}

\\begin{{frame}}{{Cierre}}
  \\centering
  La plantilla queda lista para desarrollar la actividad con criterio juridico,
  trazabilidad y control editorial.
\\end{{frame}}

\\end{{document}}
"""

    def _render_light_presentation_tex(
        self,
        profile: SubjectProfile,
        markers: list[str],
        gates: list[str],
        title: str,
        guidance: list[str],
    ) -> str:
        return f"""% AulaTeX - presentacion materializada desde memoria editorial
\\documentclass[spanish]{{article}}
\\usepackage[paperwidth=19.2cm,paperheight=10.8cm,margin=0cm]{{geometry}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage[spanish,es-tabla]{{babel}}
\\usepackage[scaled=.96]{{helvet}}
\\renewcommand{{\\familydefault}}{{\\sfdefault}}
\\usepackage[table]{{xcolor}}
\\usepackage{{graphicx}}
\\usepackage{{ragged2e}}
\\usepackage{{hyperref}}

\\definecolor{{unadmGreenDark}}{{HTML}}{{174A3A}}
\\definecolor{{unadmGreen}}{{HTML}}{{5F8F3A}}
\\definecolor{{unadmGold}}{{HTML}}{{B88A2A}}
\\definecolor{{unadmPaper}}{{HTML}}{{F6F7F2}}
\\definecolor{{unadmInk}}{{HTML}}{{1F2A24}}

\\pagestyle{{empty}}
\\setlength{{\\parindent}}{{0pt}}
\\setlength{{\\fboxsep}}{{0pt}}
\\renewcommand{{\\labelitemi}}{{\\textcolor{{unadmGreen}}{{\\bfseries >}}}}

\\newcommand{{\\CoverSlide}}{{%
  \\thispagestyle{{empty}}
  \\noindent\\colorbox{{unadmGreenDark}}{{%
    \\begin{{minipage}}[t][10.55cm][t]{{0.58\\paperwidth}}
      \\vspace*{{1.15cm}}
      \\hspace*{{0.75cm}}\\begin{{minipage}}{{9.7cm}}
        {{\\color{{white}}\\fontsize{{24}}{{29}}\\selectfont\\bfseries {_latex(title)}\\par}}
        \\vspace{{0.35cm}}
        {{\\color{{white!85}}\\Large Licenciatura en Derecho - UnADM\\par}}
        \\vspace{{0.45cm}}
        {{\\color{{unadmGold}}\\rule{{8.8cm}}{{1.2pt}}\\par}}
        \\vspace{{0.45cm}}
        {{\\color{{white}}\\large Martin Jonathan de la Cruz\\par}}
      \\end{{minipage}}
    \\end{{minipage}}%
  }}%
  \\colorbox{{unadmGreen}}{{%
    \\begin{{minipage}}[t][10.55cm][t]{{0.42\\paperwidth}}
      \\vspace*{{1.25cm}}
      \\centering
      \\includegraphics[height=2.2cm]{{img/departamentos/UnADM.pdf}}\\\\[0.65cm]
      {{\\color{{white}}\\Large\\bfseries AulaTeX}}\\\\[0.15cm]
      {{\\color{{white!85}}Plantilla editorial verificable}}\\\\[5.9cm]
      {{\\color{{white}}\\small {_latex(profile.subject_type)} - Semestre {profile.semester} - Bloque {profile.block}}}
    \\end{{minipage}}%
  }}%
}}

\\newcommand{{\\ContentSlide}}[2]{{%
  \\clearpage
  \\thispagestyle{{empty}}
  \\noindent\\begin{{minipage}}[t][10.55cm][t]{{\\paperwidth}}
    \\noindent\\colorbox{{unadmGreenDark}}{{%
      \\begin{{minipage}}[c][1.18cm][c]{{\\paperwidth}}
        \\hspace*{{0.65cm}}{{\\color{{white}}\\Large\\bfseries #1}}
      \\end{{minipage}}%
    }}
    \\vspace{{0.55cm}}

    \\hspace*{{0.8cm}}\\begin{{minipage}}{{17.55cm}}
      \\Large\\color{{unadmInk}}#2
    \\end{{minipage}}
    \\vfill
    \\noindent\\colorbox{{unadmGreen}}{{%
      \\begin{{minipage}}[c][0.56cm][c]{{\\paperwidth}}
        \\hspace*{{0.65cm}}{{\\color{{white}}\\small {_latex(profile.title)} - UnADM - \\today}}
      \\end{{minipage}}%
    }}
  \\end{{minipage}}
}}

\\begin{{document}}

\\CoverSlide

\\ContentSlide{{Objetivo editorial}}{{
  {{\\bfseries Objetivo editable}}\\\\[0.25cm]
  Convertir la consigna en problema juridico verificable, con evidencia,
  fundamento y postura academica propia.
  \\vspace{{0.45cm}}
  \\begin{{itemize}}
    \\item Semestre: {profile.semester}. Bloque: {profile.block}.
    \\item Tipo: {_latex(profile.subject_type)}. Creditos: {profile.credits}.
    \\item Bibliografia local: \\texttt{{{profile.slug}.bib}}.
  \\end{{itemize}}
}}

\\ContentSlide{{Marcadores de investigacion}}{{
{_beamer_items(markers or ["Delimitar marco juridico.", "Identificar instituciones y sujetos.", "Vincular problema con practica profesional."])}
}}

\\ContentSlide{{Producto y estructura}}{{
  \\begin{{enumerate}}
    \\item Problema.
    \\item Marco conceptual y normativo.
    \\item Analisis o producto visual.
    \\item Postura personal.
    \\item Conclusion.
  \\end{{enumerate}}
}}

\\ContentSlide{{Indicaciones editoriales}}{{
{_beamer_items(guidance or ["Sintetizar la memoria editorial de la materia sin perder continuidad con reporte y actividad."])}
}}

\\ContentSlide{{Criterios de calidad}}{{
{_beamer_items(gates or ["Citas verificables.", "Bibliografia local consistente.", "Compilacion limpia.", "Redaccion formal."])}
}}

\\ContentSlide{{Cierre}}{{
  \\centering\\vspace*{{1.8cm}}
  La plantilla queda lista para desarrollar la actividad con criterio juridico,
  trazabilidad y control editorial.
}}

\\end{{document}}
"""

    def _render_structure_json(self, profile: SubjectProfile, memory: dict[str, Any]) -> str:
        payload = {
        "schema_version": "1.0",
        "kind": "subject_file_inventory",
            "node": profile.folder_slug,
            "slug": profile.slug,
            "title": profile.title,
            "activity_number": profile.activity_number,
            "files": [
                f"{profile.slug}.bib",
                f"reporte-{profile.slug}.tex",
                f"reporte-{profile.slug}-Actividad-{profile.activity_number}.tex",
                f"presentacion-{profile.slug}.tex",
                f"presentacion-{profile.slug}-Actividad-{profile.activity_number}.tex",
                f"programa-analitico-{profile.slug}.md",
                f"COMPILACION-{profile.slug}.md",
                "README.md",
            ],
            "folders": [
                f"referencias-{profile.slug}",
              f"referencias-{profile.slug}/notas-{profile.slug}",
                f"planeaciones-{profile.slug}",
                f"assets-{profile.slug}",
              "extractor-aulatex",
              "investigacion-aulatex",
            ],
            "memory_summary": self._memory_list(memory, "summary", 8),
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)


def _first_match(text: str, pattern: str, default: str) -> str:
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1) if match else default


def _subject_slug_from_dir(target_dir: Path) -> str:
  return re.sub(r"-(lde|lad|mga|isc|imtc)$", "", target_dir.name, flags=re.IGNORECASE)


def _title_from_slug(slug: str) -> str:
    minor = {"a", "al", "de", "del", "la", "las", "los", "y", "en"}
    words = []
    for index, word in enumerate(slug.replace("_", "-").split("-")):
        if not word:
            continue
        words.append(word if index > 0 and word in minor else word.capitalize())
    return " ".join(words)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        key = re.sub(r"\s+", " ", value).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def _contains(payload: Any, needle: str) -> bool:
    return needle.lower() in json.dumps(payload, ensure_ascii=False).lower()


def _clean_text(value: str) -> str:
    text = value
    for _ in range(2):
        try:
            decoded = text.encode("latin1").decode("utf-8")
        except UnicodeError:
            break
        if decoded == text:
            break
        text = decoded
    replacements = {
        "MÃ©xico": "Mexico",
        "mÃ©xico": "Mexico",
        "jurÃ­dica": "juridica",
        "jurÃ­dico": "juridico",
        "anÃ¡lisis": "analisis",
        "investigaciÃ³n": "investigacion",
        "redacciÃ³n": "redaccion",
        "canÃ³nico": "canonico",
        "canÃ³nicos": "canonicos",
        "mÃ­nima": "minima",
        "Ãºtiles": "utiles",
        "rÃºbrica": "rubrica",
        "no discriminaciÃ³n": "no discriminacion",
        "rÃ©gimen": "regimen",
        "diseÃ±o": "diseno",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text


def _latex(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in str(value))


def _latex_itemize(items: list[str]) -> str:
    lines = ["\\begin{itemize}"]
    lines.extend(f"  \\item {_latex(item)}" for item in items)
    lines.append("\\end{itemize}")
    return "\n".join(lines)


def _beamer_items(items: list[str]) -> str:
    lines = ["  \\begin{itemize}"]
    lines.extend(f"    \\item {_latex(item)}" for item in items)
    lines.append("  \\end{itemize}")
    return "\n".join(lines)
