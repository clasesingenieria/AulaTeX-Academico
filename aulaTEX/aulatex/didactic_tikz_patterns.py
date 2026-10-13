"""Plantillas TikZ/LaTeX de referencia por FAMILIA de producto didáctico.

El consolidador (``didactic_builder_consolidator``) asigna a cada una de las 100
técnicas el patrón de su familia, para que el motor sepa CÓMO materializar el
producto con TikZ/LaTeX y no improvise. Las plantillas son mínimas, compilables
y pensadas para copiarse a la actividad concreta ajustando el contenido.

Cada patrón incluye:
- ``packages``: paquetes requeridos.
- ``skeleton``: esqueleto LaTeX/TikZ listo para adaptar.
- ``rules``: reglas de construcción específicas del patrón visual.
"""

from __future__ import annotations

from typing import Any

# Marcadores de plantilla usan <...> para que el motor los sustituya.

FAMILY_TIKZ_PATTERNS: dict[str, dict[str, Any]] = {
    "visual_jerarquico": {
        "packages": ["tikz", "\\usetikzlibrary{arrows.meta,positioning,fit,shapes.geometric}"],
        "skeleton": r"""\begin{figure}[H]\centering
\resizebox{!}{0.80\textheight}{%
\begin{tikzpicture}[
  nodo/.style={rectangle, draw, rounded corners=2pt, align=center,
    text width=3.2cm, minimum height=0.9cm, fill=blue!5},
  raiz/.style={nodo, fill=blue!15, font=\bfseries},
  enlace/.style={-{Stealth[length=2mm]}, thick}]
\node[raiz] (r) {<Concepto raíz>};
\node[nodo, below left=1.4cm and 2.2cm of r] (a) {<Rama A>};
\node[nodo, below=1.4cm of r] (b) {<Rama B>};
\node[nodo, below right=1.4cm and 2.2cm of r] (c) {<Rama C>};
\node[nodo, below=1.0cm of a, text width=2.8cm] (a1) {<Subconcepto A1>};
\node[nodo, below=0.7cm of a1, text width=2.8cm] (a2) {<Subconcepto A2>};
\draw[enlace] (r) -- node[above,sloped,font=\scriptsize]{<se clasifica en>} (a);
\draw[enlace] (r) -- (b);
\draw[enlace] (r) -- node[above,sloped,font=\scriptsize]{<comprende>} (c);
\draw[enlace] (a) -- (a1); \draw[enlace] (a1) -- (a2);
\end{tikzpicture}}
\caption{<Mapa/esquema de: tema>}\end{figure}""",
        "rules": "Raíz + 3-4 ramas + subconceptos apilados DEBAJO (below=) de cada rama; conectores con proposición de enlace; relaciones cruzadas entre ramas; escalar con \\resizebox{!}{0.80\\textheight} en landscape.",
    },
    "tabular": {
        "packages": ["longtable", "booktabs", "array", "pdflscape"],
        "skeleton": r"""\begin{landscape}
\begingroup\renewcommand{\arraystretch}{1.2}\footnotesize
\begin{longtable}{@{}p{0.16\linewidth}*{3}{p{0.24\linewidth}}@{}}
\caption{<Cuadro comparativo de: tema>}\label{tab:<id>}\\ \toprule
\textbf{Criterio} & \textbf{<Opción A>} & \textbf{<Opción B>} & \textbf{<Opción C>}\\ \midrule \endfirsthead
\toprule \textbf{Criterio} & \textbf{<A>} & \textbf{<B>} & \textbf{<C>}\\ \midrule \endhead
<Criterio 1> & <...> & <...> & <...>\\
<Criterio 2> & <...> & <...> & <...>\\
<Criterio 3> & <...> & <...> & <...>\\ \bottomrule
\end{longtable}\endgroup
\end{landscape}""",
        "rules": "Criterios en filas, opciones en columnas; caption + label; landscape en página propia; \\arraystretch<=1.2 y \\footnotesize; guía de lectura antes y análisis (semejanzas/diferencias) después.",
    },
    "temporal": {
        "packages": ["tikz", "\\usetikzlibrary{arrows.meta,positioning}"],
        "skeleton": r"""\begin{figure}[H]\centering
\begin{tikzpicture}[
  evento/.style={rectangle, draw, rounded corners=2pt, align=center,
    text width=2.8cm, font=\scriptsize, fill=orange!8},
  eje/.style={-{Stealth[length=2.4mm]}, very thick}]
\draw[eje] (0,0) -- (13,0);
\foreach \x/\anio/\txt/\dir in {
  0/<año>/<hito 1>/above, 3.2/<año>/<hito 2>/below,
  6.4/<año>/<hito 3>/above, 9.6/<año>/<hito 4>/below, 12.8/<año>/<hito 5>/above}{
  \draw (\x,0.12) -- (\x,-0.12);
  \node[evento, \dir=0.5cm] at (\x,0) {\textbf{\anio}\\ \txt};}
\end{tikzpicture}
\caption{<Línea de tiempo de: tema>}\end{figure}""",
        "rules": "Eje horizontal con hitos alternados arriba/abajo; año + evento breve; causa/consecuencia; lectura histórica (tendencias/rupturas) después del diagrama.",
    },
    "diagrama_relacional": {
        "packages": ["tikz", "\\usetikzlibrary{arrows.meta,positioning,shapes.geometric}"],
        "skeleton": r"""\begin{figure}[H]\centering
\begin{tikzpicture}[
  paso/.style={rectangle, draw, rounded corners=2pt, align=center,
    text width=3.1cm, minimum height=0.9cm, fill=green!6},
  decision/.style={diamond, draw, aspect=2, align=center,
    text width=2.6cm, inner sep=1pt, fill=yellow!12},
  flecha/.style={-{Stealth[length=2mm]}, thick}]
\node[paso] (i) {<Inicio>};
\node[paso, right=1.4cm of i] (p1) {<Paso 1>};
\node[decision, right=1.4cm of p1] (d) {<¿Condición?>};
\node[paso, below=1.1cm of d] (s) {<Salida sí>};
\node[paso, right=1.4cm of d] (n) {<Salida no>};
\draw[flecha] (i) -- (p1); \draw[flecha] (p1) -- (d);
\draw[flecha] (d) -- node[right,font=\scriptsize]{sí} (s);
\draw[flecha] (d) -- node[above,font=\scriptsize]{no} (n);
\end{tikzpicture}
\caption{<Diagrama de: proceso>}\end{figure}""",
        "rules": "Rectángulos para acciones, rombos para decisiones, flechas Stealth etiquetadas; para Venn usar círculos semitransparentes; para Gowin una V con teoría/evidencia; lectura del diagrama después.",
    },
    "cuantitativo": {
        "packages": ["pgfplots", "\\pgfplotsset{compat=1.18}"],
        "skeleton": r"""\begin{figure}[H]\centering
\begin{tikzpicture}
\begin{axis}[ybar, width=0.85\linewidth, height=6cm,
  xlabel={<Variable>}, ylabel={<Frecuencia>},
  symbolic x coords={<c1>,<c2>,<c3>,<c4>}, xtick=data,
  nodes near coords, ymin=0]
\addplot coordinates {(<c1>,<v1>) (<c2>,<v2>) (<c3>,<v3>) (<c4>,<v4>)};
\end{axis}\end{tikzpicture}
\caption{<Gráfico de: variable> (Fuente: <cita>)}\end{figure}""",
        "rules": "Declarar variable, fuente citada, escala y unidades. PROHIBIDO inventar cifras: sin datos confiables no se usa gráfico. Lectura del dato después.",
    },
    "oral_participativo": {
        "packages": ["tcolorbox", "\\tcbuselibrary{most}", "enumitem"],
        "skeleton": r"""\newtcolorbox{forobox}{enhanced, breakable, colback=black!2,
  colframe=green!45!black, boxrule=0.6pt, arc=2pt,
  title=\textbf{Participación publicada en el foro}}
\begin{forobox}
\begin{enumerate}[label=\textbf{\arabic*)}, leftmargin=*, itemsep=4pt]
\item <Apertura / encuadre del tema>.
\item <Respuesta a la pregunta guía con evidencia>. ``<cita textual>'' (<Apellido>, <año>, p.~<n>).
\item <Cierre con una pregunta al grupo>.
\end{enumerate}
\par\noindent\textbf{Referencias}\par
\hangindent=1.6em\hangafter=1 <Entrada APA 7 completa>.
\end{forobox}""",
        "rules": "Bloque forobox reproduce lo publicado (apertura, respuesta con cita textual APA 7, cierre con pregunta); texto seleccionable/copiable; apartado Referencias con sangría francesa; retroalimentación en forobox aparte.",
    },
    "reactivo_evaluativo": {
        "packages": ["longtable", "booktabs", "array"],
        "skeleton": r"""\begingroup\renewcommand{\arraystretch}{1.3}
\begin{longtable}{@{}p{0.05\linewidth}p{0.45\linewidth}p{0.20\linewidth}p{0.24\linewidth}@{}}
\caption{<Cuestionario de: tema>}\\ \toprule
\textbf{\#} & \textbf{Reactivo} & \textbf{Respuesta} & \textbf{Justificación}\\ \midrule \endhead
1 & <pregunta> & <respuesta> & <justificación con fuente>\\
2 & <pregunta> & <respuesta> & <justificación con fuente>\\ \bottomrule
\end{longtable}\endgroup""",
        "rules": "Conservar reactivo + respuesta + justificación en tabla; no convertir en ensayo; justificación con fuente.",
    },
    "escrito_expositivo": {
        "packages": [],
        "skeleton": r"""% Producto en prosa: sin TikZ salvo figuras.
\section{<Título temático (no 'Desarrollo')>}
<Marco conceptual que prepara el producto, con \citep{...}.>
\subsection{<Subtema 1>}<Análisis con fuentes.>
\subsection{<Subtema 2>}<Aplicación.>""",
        "rules": "Prosa con introducción (problema), desarrollo con fuentes y análisis, conclusión con postura, referencias APA 7. La voz convierte información en criterio.",
    },
    "escrito_argumentativo": {
        "packages": [],
        "skeleton": r"""\section{<Tesis / tema>}
<Introducción con tesis clara.>
<Argumento 1 con evidencia \citep{...}.> <Argumento 2.>
<Contraargumento y refutación.> <Cierre que reafirma la postura.>""",
        "rules": "Tesis clara, argumentos con evidencia citada, contraargumento y refutación, cierre con postura. Cada párrafo cumple una función.",
    },
}

# Familias sin patrón TikZ propio heredan el esqueleto de una familia afín.
FAMILY_FALLBACK = {
    "sintesis_lectura": "escrito_expositivo",
    "argumentativo_estructurado": "tabular",
    "analisis_caso": "escrito_expositivo",
    "instrumento_recoleccion": "tabular",
    "reflexivo_bitacora": "tabular",
    "comunicativo_visual": "visual_jerarquico",
    "audiovisual_guion": "escrito_expositivo",
    "dramatizacion_simulacion": "escrito_expositivo",
    "estrategia_cognitiva": "tabular",
    "colaborativo_proyecto": "tabular",
    "creativo_narrativo": "escrito_expositivo",
    "expositivo_oral": "escrito_expositivo",
    "analisis_textual": "tabular",
}


def pattern_for_family(family: str) -> dict[str, Any]:
    """Devuelve el patrón TikZ/LaTeX de una familia (con fallback)."""
    if family in FAMILY_TIKZ_PATTERNS:
        return FAMILY_TIKZ_PATTERNS[family]
    fallback = FAMILY_FALLBACK.get(family, "escrito_expositivo")
    return FAMILY_TIKZ_PATTERNS[fallback]
