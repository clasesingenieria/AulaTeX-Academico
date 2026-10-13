param(
    [switch]$UnadmDerecho,
    [switch]$ExistingEditorial,
    [switch]$Compile,
    [switch]$Commit,
    [int]$Limit = 0,
    [int]$StartIndex = 1,
    [int]$EndIndex = 0
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$BuildScript = Join-Path $ProjectRoot 'aulaTEX/latexmk-build.ps1'
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Write-TextFile {
    param(
        [string]$Path,
        [string]$Content,
        [switch]$Overwrite
    )

    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }

    if ((-not $Overwrite) -and (Test-Path -LiteralPath $Path)) {
        return $false
    }

    [System.IO.File]::WriteAllText($Path, $Content, $Utf8NoBom)
    return $true
}

function Get-SlugTitle {
    param([string]$Slug)
    $words = $Slug -replace '-(lde|lad|isc|mga)$','' -split '-'
    ($words | ForEach-Object {
        if ($_.Length -le 3 -and $_ -match '^(i|ii|iii|iv|v|vi|vii|viii|ix|x)$') {
            $_.ToUpperInvariant()
        } elseif ($_.Length -gt 0) {
            $_.Substring(0,1).ToUpperInvariant() + $_.Substring(1)
        }
    }) -join ' '
}

function Get-UnadmLawCourses {
    $courses = @(
        @{Name='Integridad en el servicio publico'; Slug='integridad-en-el-servicio-publico'; Semester=1; Block=1; Type='Obligatoria'; Credits='8'},
        @{Name='Historia del Derecho en Mexico'; Slug='historia-del-derecho-en-mexico'; Semester=1; Block=1; Type='Obligatoria'; Credits='8'},
        @{Name='Optativa Semestre 1 Bloque 1'; Slug='optativa-semestre-1-bloque-1'; Semester=1; Block=1; Type='Optativa'; Credits='6'},
        @{Name='Filosofia del Derecho'; Slug='filosofia-del-derecho'; Semester=1; Block=2; Type='Obligatoria'; Credits='8'},
        @{Name='Etica y Moral juridica'; Slug='etica-y-moral-juridica'; Semester=1; Block=2; Type='Obligatoria'; Credits='8'},
        @{Name='Optativa Semestre 1 Bloque 2'; Slug='optativa-semestre-1-bloque-2'; Semester=1; Block=2; Type='Optativa'; Credits='6'},
        @{Name='Garantias constitucionales'; Slug='garantias-constitucionales'; Semester=2; Block=1; Type='Obligatoria'; Credits='8'},
        @{Name='Derecho a la seguridad social'; Slug='derecho-a-la-seguridad-social'; Semester=2; Block=1; Type='Obligatoria'; Credits='8'},
        @{Name='Optativa Semestre 2 Bloque 1'; Slug='optativa-semestre-2-bloque-1'; Semester=2; Block=1; Type='Optativa'; Credits='6'},
        @{Name='Teoria del Estado y Constitucion'; Slug='teoria-del-estado-y-constitucion'; Semester=2; Block=2; Type='Obligatoria'; Credits='8'},
        @{Name='Derecho penal especial mexicano'; Slug='derecho-penal-especial-mexicano'; Semester=2; Block=2; Type='Obligatoria'; Credits='8'},
        @{Name='Optativa Semestre 2 Bloque 2'; Slug='optativa-semestre-2-bloque-2'; Semester=2; Block=2; Type='Optativa'; Credits='6'},
        @{Name='Sociologia'; Slug='sociologia'; Semester=3; Block=1; Type='Obligatoria'; Credits='8'},
        @{Name='Derechos de la persona y familia'; Slug='derechos-de-la-persona-y-familia'; Semester=3; Block=1; Type='Obligatoria seriada'; Credits='8'},
        @{Name='Optativa Semestre 3 Bloque 1'; Slug='optativa-semestre-3-bloque-1'; Semester=3; Block=1; Type='Optativa'; Credits='6'},
        @{Name='Economia'; Slug='economia'; Semester=3; Block=2; Type='Obligatoria'; Credits='8'},
        @{Name='Derecho financiero y bancario'; Slug='derecho-financiero-y-bancario'; Semester=3; Block=2; Type='Obligatoria'; Credits='8'},
        @{Name='Optativa Semestre 3 Bloque 2'; Slug='optativa-semestre-3-bloque-2'; Semester=3; Block=2; Type='Optativa'; Credits='6'},
        @{Name='Derechos de los contratos y obligaciones'; Slug='derechos-de-los-contratos-y-obligaciones'; Semester=4; Block=1; Type='Obligatoria'; Credits='8'},
        @{Name='Bases de derecho internacional publico'; Slug='bases-de-derecho-internacional-publico'; Semester=4; Block=1; Type='Obligatoria'; Credits='8'},
        @{Name='Optativa Semestre 4 Bloque 1'; Slug='optativa-semestre-4-bloque-1'; Semester=4; Block=1; Type='Optativa'; Credits='6'},
        @{Name='Antropologia de la cultura en Mexico'; Slug='antropologia-de-la-cultura-en-mexico'; Semester=4; Block=2; Type='Obligatoria'; Credits='8'},
        @{Name='Teoria del delito y tipos de responsabilidad social'; Slug='teoria-del-delito-y-tipos-de-responsabilidad-social'; Semester=4; Block=2; Type='Obligatoria'; Credits='8'},
        @{Name='Optativa Semestre 4 Bloque 2'; Slug='optativa-semestre-4-bloque-2'; Semester=4; Block=2; Type='Optativa'; Credits='6'},
        @{Name='Derechos de autor'; Slug='derechos-de-autor'; Semester=5; Block=1; Type='Obligatoria'; Credits='8'},
        @{Name='Propiedad industrial'; Slug='propiedad-industrial'; Semester=5; Block=1; Type='Obligatoria'; Credits='8'},
        @{Name='Mecanismos alternativos de resolucion de conflictos'; Slug='mecanismos-alternativos-de-resolucion-de-conflictos'; Semester=5; Block=1; Type='Obligatoria'; Credits='8'},
        @{Name='Sistema penal acusatorio y oral'; Slug='sistema-penal-acusatorio-y-oral'; Semester=5; Block=2; Type='Obligatoria'; Credits='8'},
        @{Name='Etapas del proceso y estrategia del litigio'; Slug='etapas-del-proceso-y-estrategia-del-litigio'; Semester=5; Block=2; Type='Obligatoria'; Credits='8'},
        @{Name='Instrumentos y mecanismos de proteccion de los derechos humanos'; Slug='instrumentos-y-mecanismos-de-proteccion-de-los-derechos-humanos'; Semester=5; Block=2; Type='Obligatoria'; Credits='8'},
        @{Name='Derecho administrativo y control'; Slug='derecho-administrativo-y-control'; Semester=6; Block=1; Type='Obligatoria'; Credits='8'},
        @{Name='Derecho de la responsabilidad civil y danos'; Slug='derecho-de-la-responsabilidad-civil-y-danos'; Semester=6; Block=1; Type='Obligatoria'; Credits='8'},
        @{Name='Derecho fiscal y tributario'; Slug='derecho-fiscal-y-tributario'; Semester=6; Block=1; Type='Obligatoria'; Credits='8'},
        @{Name='Derecho de la empresa y emprendimiento'; Slug='derecho-de-la-empresa-y-emprendimiento'; Semester=6; Block=2; Type='Obligatoria'; Credits='8'},
        @{Name='Derechos de contratos mercantiles y titulos valores'; Slug='derechos-de-contratos-mercantiles-y-titulos-valores'; Semester=6; Block=2; Type='Obligatoria'; Credits='8'},
        @{Name='Derecho de la contratacion internacional'; Slug='derecho-de-la-contratacion-internacional'; Semester=6; Block=2; Type='Obligatoria'; Credits='8'},
        @{Name='Derecho laboral y relaciones laborales'; Slug='derecho-laboral-y-relaciones-laborales'; Semester=7; Block=1; Type='Obligatoria'; Credits='8'},
        @{Name='Derecho de la propiedad y registro'; Slug='derecho-de-la-propiedad-y-registro'; Semester=7; Block=1; Type='Obligatoria'; Credits='8'},
        @{Name='Tecnica legislativa'; Slug='tecnica-legislativa'; Semester=7; Block=1; Type='Obligatoria'; Credits='8'},
        @{Name='Seminario de titulacion I'; Slug='seminario-de-titulacion-i'; Semester=7; Block=2; Type='Obligatoria seriada'; Credits='10'},
        @{Name='Electiva Semestre 7 Bloque 2'; Slug='electiva-semestre-7-bloque-2'; Semester=7; Block=2; Type='Electiva'; Credits=''},
        @{Name='Seminario de titulacion II'; Slug='seminario-de-titulacion-ii'; Semester=8; Block=1; Type='Obligatoria seriada'; Credits='10'},
        @{Name='Electiva Semestre 8 Bloque 1'; Slug='electiva-semestre-8-bloque-1'; Semester=8; Block=1; Type='Electiva'; Credits=''},
        @{Name='Seminario de titulacion III'; Slug='seminario-de-titulacion-iii'; Semester=8; Block=2; Type='Obligatoria seriada'; Credits='10'},
        @{Name='Electiva Semestre 8 Bloque 2'; Slug='electiva-semestre-8-bloque-2'; Semester=8; Block=2; Type='Electiva'; Credits=''},
        @{Name='Redaccion en contextos virtuales'; Slug='redaccion-en-contextos-virtuales'; Semester=''; Block=''; Type='Curso de apoyo existente'; Credits=''}
    )

    $courses | ForEach-Object { [PSCustomObject]$_ }
}

function Get-UnadmBibContent {
    param([object]$Course)
    @"
% Bibliografia local de $($Course.Name)
% Agregar entradas BibTeX especificas de esta asignatura.

@misc{unadmSitioWeb,
  author = {{Universidad Abierta y a Distancia de Mexico}},
  title = {Universidad Abierta y a Distancia de Mexico},
  year = {2026},
  howpublished = {\url{https://www.unadmexico.mx/}},
  note = {Sitio institucional; consulta: 2026-06-18}
}

@misc{unadmMallaDerecho2024,
  author = {{Universidad Abierta y a Distancia de Mexico}},
  title = {Malla curricular de la Licenciatura en Derecho},
  year = {2024},
  howpublished = {Archivo local: UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf},
  note = {Documento institucional incluido en assets-unadm}
}
"@
}

function Get-UnadmReportContent {
    param([object]$Course)
    $courseCode = if ($Course.Semester) { "LDE-S$($Course.Semester)B$($Course.Block)" } else { "LDE" }
    @"
\documentclass[
  spanish,
  letterpaper, oneside
]{article}

\def\documenttitle {Plantilla base de $($Course.Name)}
\def\documentsubtitle {Actividad X - $($Course.Name)}
\def\documentsubject {Licenciatura en Derecho}

\def\documentauthor {Martin Jonathan de la Cruz}
\def\coursename {$($Course.Name)}
\def\coursecode {$courseCode}

\def\universityname {Universidad Abierta y a Distancia de Mexico}
\def\universityfaculty {Licenciatura en Derecho}
\def\universitydepartment {$($Course.Name)}
\def\universitydepartmentimage {departamentos/UnADM}
\def\universitydepartmentimagecfg {height=1.57cm}
\def\universitylocation {Roma Norte, Ciudad de Mexico}

\def\authortable {
  \begin{tabular}{ll}
    \textbf{Alumno:}
    & \begin{tabular}[t]{l}
      Martin Jonathan de la Cruz \\
    \end{tabular} \\
    Matricula: & ES2611202040 \\
    Figura docente: & Nombre por definir \\
    Semestre/Bloque: & $($Course.Semester) / $($Course.Block) \\
    Tipo/Creditos: & $($Course.Type) / $($Course.Credits) \\
    & \\
    \multicolumn{2}{l}{Fecha de realizacion: \today} \\
    \multicolumn{2}{l}{\universitylocation}
  \end{tabular}
}

\input{template}
\usepackage{helvet}
\renewcommand{\familydefault}{\sfdefault}
\usepackage{array}
\usepackage{longtable}
\usepackage{pdflscape}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,calc,matrix,fit,shapes.geometric,shadows.blur}
\setcitestyle{authoryear,open={(},close={)}}

\def\coverwatermarkenabled {true}
\def\coverwatermarkimage {img/departamentos/UnADM.pdf}
\def\coverwatermarkopacity {0.16}
\def\coverwatermarkwidth {0.72\paperwidth}
\def\coverwatermarkxshift {0cm}
\def\coverwatermarkyshift {-0.35cm}

\newcommand{\insertcoverwatermark}{%
  \ifthenelse{\equal{\coverwatermarkenabled}{true}}{%
    \AddToShipoutPictureBG*{%
      \begin{tikzpicture}[remember picture,overlay]
        \node[
          opacity=\coverwatermarkopacity,
          inner sep=0pt,
          xshift=\coverwatermarkxshift,
          yshift=\coverwatermarkyshift
        ] at (current page.center) {%
          \includegraphics[width=\coverwatermarkwidth]{\coverwatermarkimage}%
        };
      \end{tikzpicture}%
    }%
  }{}%
}

\newcommand{\pendiente}[1]{\textcolor{red}{[PENDIENTE: #1]}}

\begin{document}

\insertcoverwatermark
\templatePortrait
\templatePagecfg
\onehalfspacing

\begin{abstractd}
  Esta plantilla establece el punto de partida editorial para la asignatura
  \textit{$($Course.Name)} dentro de la Licenciatura en Derecho de la UnADM.
  El documento debe convertirse en cada actividad a partir de la planeacion
  vigente, la malla curricular y las fuentes especificas de la materia.
\end{abstractd}

\templateIndex
\templateFinalcfg

\section{Encuadre de la asignatura}

\pendiente{Explicar el lugar de la asignatura en el semestre, bloque, problema juridico central y competencia que desarrolla.}

\section{Pauta de realizacion}

Toda entrega debe transformar la consigna en un problema juridico delimitado.
La redaccion debe incluir contexto, conceptos, fundamento normativo o doctrinal,
analisis propio, producto solicitado y conclusion transferible.

\section{Estructura sugerida}

\begin{enumerate}
  \item Introduccion: problema, objetivo y alcance.
  \item Desarrollo: conceptos, fuentes y analisis aplicado.
  \item Producto visual o evidencia: cuadro, mapa, caso, matriz o sintesis.
  \item Postura personal: criterio juridico argumentado.
  \item Conclusion: aprendizaje, consecuencia y posible aplicacion profesional.
\end{enumerate}

\section{Checklist editorial}

\begin{itemize}
  \item La actividad responde a la planeacion sin copiar instrucciones completas.
  \item Las fuentes citadas aparecen en la bibliografia local de la materia.
  \item El producto visual tiene titulo, criterio y lectura explicativa.
  \item La identidad UnADM aparece en portada, enfoque academico e integridad.
  \item La conclusion no resume solamente: interpreta una consecuencia juridica.
\end{itemize}

\section{Conclusion editable}

\pendiente{Cerrar con sintesis, aprendizaje y criterio propio sobre la asignatura.}

\clearpage
\nocite{unadmSitioWeb,unadmMallaDerecho2024}
\bibliography{$($Course.Slug)}

\end{document}
"@
}

function Get-UnadmPresentationContent {
    param([object]$Course)
    $courseCode = if ($Course.Semester) { "LDE-S$($Course.Semester)B$($Course.Block)" } else { "LDE" }
    @"
\documentclass[
  spanish,
  aspectratio=169,
  xcolor={dvipsnames,table}
]{beamer}

\geometry{paperwidth=19.2cm,paperheight=10.8cm}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[spanish,es-tabla]{babel}
\usepackage[scaled=.96]{helvet}
\renewcommand{\familydefault}{\sfdefault}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{ragged2e}
\usepackage{tikz}
\usepackage{hyperref}
\usetikzlibrary{calc,positioning,fit,shadows.blur}

\newcommand{\studentname}{Martin Jonathan de la Cruz}
\newcommand{\studentshort}{M. J. de la Cruz}
\newcommand{\studentid}{ES2611202040}
\newcommand{\universityname}{Universidad Abierta y a Distancia de Mexico}
\newcommand{\facultyname}{Licenciatura en Derecho}
\newcommand{\coursename}{$($Course.Name)}
\newcommand{\coursecode}{$courseCode}
\newcommand{\activitytitle}{Plantilla base de $($Course.Name)}
\newcommand{\activitysubtitle}{Actividad X - $($Course.Name)}
\newcommand{\activityweek}{Semana X}
\newcommand{\teachingfigure}{Nombre de la figura docente}
\newcommand{\deliverydate}{\today}
\newcommand{\locationname}{Roma Norte, Ciudad de Mexico}
\newcommand{\departmentlogo}{img/departamentos/UnADM.pdf}

\definecolor{unadmGreenDark}{HTML}{174A3A}
\definecolor{unadmGreen}{HTML}{5F8F3A}
\definecolor{unadmGold}{HTML}{B88A2A}
\definecolor{unadmPaper}{HTML}{F6F7F2}
\definecolor{unadmInk}{HTML}{1F2A24}

\mode<presentation>{
  \usetheme{default}
  \usefonttheme{professionalfonts}
  \setbeamertemplate{navigation symbols}{}
  \setbeamertemplate{blocks}[rounded][shadow=false]
}
\setbeamersize{text margin left=0.60cm,text margin right=0.60cm}
\setbeamercolor{background canvas}{bg=white}
\setbeamercolor{normal text}{fg=unadmInk,bg=white}
\setbeamercolor{structure}{fg=unadmGreenDark}
\setbeamercolor{frametitle}{fg=white,bg=unadmGreenDark}
\setbeamercolor{block title}{fg=white,bg=unadmGreen}
\setbeamercolor{block body}{fg=unadmInk,bg=unadmPaper}
\setbeamerfont{title}{size=\LARGE,series=\bfseries}
\setbeamerfont{frametitle}{size=\large,series=\bfseries}
\setbeamertemplate{itemize item}{\textcolor{unadmGreen}{\large$\blacktriangleright$}}

\setbeamertemplate{frametitle}{
  \nointerlineskip
  \begin{beamercolorbox}[wd=\textwidth,ht=1.02cm,dp=0.22cm,leftskip=0.35cm,rightskip=0.25cm]{frametitle}
    \insertframetitle\hfill\includegraphics[height=0.60cm]{\departmentlogo}
  \end{beamercolorbox}
  {\color{unadmGold}\rule{\textwidth}{1.3pt}}
}

\setbeamertemplate{footline}{
  \leavevmode
  \hbox{
    \begin{beamercolorbox}[wd=.34\paperwidth,ht=2.7ex,dp=1ex,leftskip=1em]{author in head/foot}\color{white}\studentshort\end{beamercolorbox}
    \begin{beamercolorbox}[wd=.40\paperwidth,ht=2.7ex,dp=1ex,center]{title in head/foot}\color{white}\coursename\end{beamercolorbox}
    \begin{beamercolorbox}[wd=.26\paperwidth,ht=2.7ex,dp=1ex,rightskip=1em plus 1fil]{date in head/foot}\color{white}\coursecode\hfill\insertframenumber/\inserttotalframenumber\end{beamercolorbox}
  }
}
\setbeamercolor{author in head/foot}{bg=unadmGreenDark}
\setbeamercolor{title in head/foot}{bg=unadmGreen}
\setbeamercolor{date in head/foot}{bg=unadmGreenDark}

\title[\coursecode]{\activitytitle}
\subtitle{\activitysubtitle}
\author[\studentshort]{\studentname\\\footnotesize Matricula: \studentid}
\institute[UnADM]{\universityname\\\facultyname}
\date[\activityweek]{\locationname\\\activityweek\\\deliverydate}

\begin{document}

\begin{frame}[plain]
  \begin{tikzpicture}[remember picture,overlay]
    \fill[unadmGreenDark] (current page.south west) rectangle ([xshift=0.58\paperwidth]current page.north west);
    \fill[unadmGreen] ([xshift=0.58\paperwidth]current page.south west) rectangle (current page.north east);
    \node[anchor=center,opacity=0.10] at (current page.center) {\includegraphics[width=0.72\paperwidth]{\departmentlogo}};
    \node[anchor=north west] at ([xshift=0.58cm,yshift=-0.46cm]current page.north west) {\includegraphics[width=2.55cm]{\departmentlogo}};
  \end{tikzpicture}
  \vspace*{1.80cm}
  {\color{white}\fontsize{25}{30}\selectfont\bfseries \activitytitle\par}
  \vspace{0.28cm}
  {\color{white!86}\large \activitysubtitle}\\[0.35cm]
  {\color{unadmGold}\rule{0.58\linewidth}{1.3pt}}\\[0.35cm]
  {\color{white}\studentname}\\
  {\color{white!82}\footnotesize \facultyname}
\end{frame}

\begin{frame}{Objetivo y alcance}
  \begin{block}{Objetivo editable}
    Convertir la consigna de la actividad en un problema juridico delimitado,
    con evidencia, fundamento y postura academica propia.
  \end{block}
  \begin{itemize}
    \item Semestre: $($Course.Semester). Bloque: $($Course.Block).
    \item Tipo: $($Course.Type). Creditos: $($Course.Credits).
    \item Fuente curricular: malla de Derecho UnADM incluida en assets-unadm.
  \end{itemize}
\end{frame}

\begin{frame}{Estructura narrativa}
  \begin{itemize}
    \item Problema o caso juridico.
    \item Conceptos y fuentes principales.
    \item Producto visual, matriz, cuadro o argumento central.
    \item Postura personal y cierre transferible.
  \end{itemize}
\end{frame}

\begin{frame}{Producto visual}
  \begin{block}{Espacio editable}
    Insertar aqui mapa conceptual, cuadro comparativo, linea de tiempo,
    matriz de analisis, red argumentativa o sintesis del caso.
  \end{block}
  \centering
  \fbox{\parbox[c][3.2cm][c]{0.76\linewidth}{\centering Evidencia visual o producto solicitado}}
\end{frame}

\begin{frame}{Fuentes y revision}
  \begin{itemize}
    \item Bibliografia local: \texttt{$($Course.Slug).bib}.
    \item Malla curricular: \texttt{UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf}.
    \item Revisar citas, ortografia, producto visual y conclusion juridica.
  \end{itemize}
\end{frame}

\end{document}
"@
}

function Get-UnadmReadmeContent {
    param([object]$Course)
    @"
# $($Course.Name)

Materia de la Licenciatura en Derecho de la UnADM.

## Ubicacion curricular

- Semestre: $($Course.Semester)
- Bloque: $($Course.Block)
- Tipo: $($Course.Type)
- Creditos: $($Course.Credits)
- Fuente: `UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf`

## Estructura

- `reporte-$($Course.Slug).tex`
- `presentacion-$($Course.Slug).tex`
- `$($Course.Slug).bib`
- `programa-analitico-$($Course.Slug).md`
- `referencias-$($Course.Slug)/`

## Pauta editorial

La carpeta funciona como punto de entrada canonico de la asignatura. Cada
actividad debe conservar identidad UnADM, integridad academica, citas
verificables y una conclusion juridica con criterio propio.
"@
}

function Get-UnadmProgramContent {
    param([object]$Course)
    @"
# Programa analitico editorial - $($Course.Name)

## Encuadre institucional

Asignatura de la Licenciatura en Derecho de la UnADM ubicada en semestre
$($Course.Semester), bloque $($Course.Block). Su funcion editorial es orientar
productos academicos con claridad, fundamento juridico, evidencia y transferencia
profesional.

## Proposito de realizacion

Transformar la planeacion semanal en reportes, presentaciones y productos
visuales que integren problema, conceptos, fuentes, analisis propio y cierre
argumentativo.

## Ejes de trabajo

1. Problema juridico o social que activa la asignatura.
2. Conceptos, normas, doctrina o datos pertinentes.
3. Producto solicitado por la planeacion.
4. Analisis propio y postura academica.
5. Conclusion transferible a la practica juridica.

## Bibliografia base

La bibliografia local inicia con fuentes institucionales UnADM y la malla
curricular de Derecho. Las fuentes especificas de cada actividad deben agregarse
en `$($Course.Slug).bib`.
"@
}

function Get-UnadmRefsContent {
    param([object]$Course)
    @"
# Referencias - $($Course.Name)

Carpeta para planeaciones, lecturas, notas, jurisprudencia, normas, casos,
datos y evidencia auxiliar de la asignatura.

## Convenciones

- Registrar toda fuente final en `../$($Course.Slug).bib`.
- Separar planeaciones, bibliografia, productos visuales y notas de clase.
- Conservar fecha, actividad y uso de cada fuente.
- No entregar material copiado: convertir la fuente en analisis propio.
"@
}

function Get-UnadmCompilationContent {
    param([object]$Course)
    @"
# Compilacion - $($Course.Name)

Ejecutar desde la raiz del proyecto:

```powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\$($Course.Slug)-lde\reporte-$($Course.Slug).tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\$($Course.Slug)-lde\presentacion-$($Course.Slug).tex
```

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en `$($Course.Slug).bib`.
- La identidad institucional usa `img/departamentos/UnADM.pdf`.
- La malla curricular base esta en `UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf`.
"@
}

function Ensure-UnadmLawCourse {
    param([object]$Course)

    $dir = Join-Path $ProjectRoot "UnADM/licenciatura-en-derecho-unadm/$($Course.Slug)-lde"
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }

    $changed = $false
    $changed = (Write-TextFile (Join-Path $dir 'README.md') (Get-UnadmReadmeContent $Course)) -or $changed
    $changed = (Write-TextFile (Join-Path $dir "programa-analitico-$($Course.Slug).md") (Get-UnadmProgramContent $Course)) -or $changed
    $changed = (Write-TextFile (Join-Path $dir "referencias-$($Course.Slug)/README.md") (Get-UnadmRefsContent $Course)) -or $changed
    $changed = (Write-TextFile (Join-Path $dir "COMPILACION-$($Course.Slug).md") (Get-UnadmCompilationContent $Course)) -or $changed

    $bibPath = Join-Path $dir "$($Course.Slug).bib"
    if (-not (Test-Path -LiteralPath $bibPath)) {
        $changed = (Write-TextFile $bibPath (Get-UnadmBibContent $Course)) -or $changed
    }

    $reportPath = Join-Path $dir "reporte-$($Course.Slug).tex"
    if (-not (Test-Path -LiteralPath $reportPath)) {
        $changed = (Write-TextFile $reportPath (Get-UnadmReportContent $Course)) -or $changed
    }

    $presentationPath = Join-Path $dir "presentacion-$($Course.Slug).tex"
    if (-not (Test-Path -LiteralPath $presentationPath)) {
        $changed = (Write-TextFile $presentationPath (Get-UnadmPresentationContent $Course)) -or $changed
    }

    if ($Compile) {
        foreach ($tex in @($reportPath, $presentationPath)) {
            $pdf = [System.IO.Path]::ChangeExtension($tex, '.pdf')
            if (Test-Path -LiteralPath $tex -PathType Leaf) {
                if (-not (Test-Path -LiteralPath $pdf)) {
                    & $BuildScript $tex -CleanMode none
                    $changed = $true
                }
            }
        }
    }

    if ($Commit) {
        $relDir = Resolve-Path -LiteralPath $dir | ForEach-Object { $_.Path.Substring($ProjectRoot.Length + 1) }
        $status = git -C $ProjectRoot status --short -- $relDir
        if ($status) {
            git -C $ProjectRoot add -- $relDir
            git -C $ProjectRoot commit -m "Completa plantilla UnADM $($Course.Slug)"
        }
    }

    [PSCustomObject]@{
        Course = $Course.Name
        Path = $dir
        Changed = $changed
    }
}

function Ensure-ExistingEditorialFolder {
    param([System.IO.DirectoryInfo]$Dir)

    $leaf = $Dir.Name
    $title = Get-SlugTitle $leaf
    $texFiles = @(Get-ChildItem -LiteralPath $Dir.FullName -Filter '*.tex' -File -ErrorAction SilentlyContinue)
    if ($texFiles.Count -eq 0) {
        return $null
    }

    $bibFiles = @(Get-ChildItem -LiteralPath $Dir.FullName -Filter '*.bib' -File -ErrorAction SilentlyContinue)
    $bibName = if ($bibFiles.Count -gt 0) { $bibFiles[0].Name } else { "$leaf.bib" }
    $refsName = "referencias-$leaf"

    $readme = @"
# $title

Carpeta de materia con plantillas academicas, bibliografia local y control
editorial.

## Estructura

- Archivos `.tex`: reportes, presentaciones o actividades.
- Bibliografia local: `$bibName`.
- Programa analitico editorial: `programa-analitico-$leaf.md`.
- Referencias: `$refsName/`.

## Pauta editorial

Cada producto debe conservar identidad institucional, responder a la consigna,
usar fuentes verificables, explicar el criterio de analisis y cerrar con una
conclusion transferible al campo profesional.
"@

    $program = @"
# Programa analitico editorial - $title

## Proposito

Normalizar la produccion academica de la materia mediante plantillas
institucionales, bibliografia trazable y pautas de redaccion orientadas a
evidencia, analisis propio y cierre profesional.

## Pautas de realizacion

- Definir el problema o consigna antes de redactar.
- Integrar conceptos, fuentes y evidencia con lectura critica.
- Usar tablas, mapas, matrices o esquemas solo cuando agreguen claridad.
- Cuidar portada, metadatos, citas, bibliografia y nomenclatura de entrega.
- Concluir con implicacion, criterio o aplicacion, no con resumen plano.

## Bibliografia

Registrar fuentes finales en `$bibName` y conservar evidencia auxiliar en
`$refsName/`.
"@

    $refs = @"
# Referencias - $title

Carpeta para lecturas, planeaciones, notas, datos, imagenes institucionales,
casos, rubricas y evidencia auxiliar de la materia.

## Convenciones

- Registrar fuentes finales en `../$bibName`.
- Separar materiales de clase, fuentes externas y productos propios.
- Anotar fecha, actividad y uso editorial de cada fuente relevante.
"@

    $changed = $false
    $changed = (Write-TextFile (Join-Path $Dir.FullName 'README.md') $readme) -or $changed
    $changed = (Write-TextFile (Join-Path $Dir.FullName "programa-analitico-$leaf.md") $program) -or $changed
    $changed = (Write-TextFile (Join-Path $Dir.FullName "$refsName/README.md") $refs) -or $changed
    if ($bibFiles.Count -eq 0) {
        $bib = "% Bibliografia local de $title`n% Agregar entradas BibTeX especificas de esta materia.`n"
        $changed = (Write-TextFile (Join-Path $Dir.FullName $bibName) $bib) -or $changed
    }

    [PSCustomObject]@{
        Folder = $Dir.FullName
        Changed = $changed
    }
}

if ($UnadmDerecho) {
    $count = 0
    foreach ($course in Get-UnadmLawCourses) {
        $count++
        if ($count -lt $StartIndex) { continue }
        if ($EndIndex -gt 0 -and $count -gt $EndIndex) { break }
        if ($Limit -gt 0 -and $count -gt $Limit) { break }
        Ensure-UnadmLawCourse $course
    }
}

if ($ExistingEditorial) {
    $roots = @('ITESCA','UCNL','UANL','IIIEPE')
    $count = 0
    foreach ($root in $roots) {
        $rootPath = Join-Path $ProjectRoot $root
        if (-not (Test-Path -LiteralPath $rootPath)) { continue }
        $dirs = Get-ChildItem -LiteralPath $rootPath -Recurse -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -notmatch '\\assets-|\\referencias-' }
        foreach ($dir in $dirs) {
            if ($Limit -gt 0 -and $count -ge $Limit) { break }
            $result = Ensure-ExistingEditorialFolder $dir
            if ($null -ne $result) {
                $count++
                if ($Commit) {
                    $relDir = $dir.FullName.Substring($ProjectRoot.Length + 1)
                    $status = git -C $ProjectRoot status --short -- $relDir
                    if ($status) {
                        git -C $ProjectRoot add -- $relDir
                        git -C $ProjectRoot commit -m "Completa control editorial $($dir.Name)"
                    }
                }
                $result
            }
        }
    }
}
