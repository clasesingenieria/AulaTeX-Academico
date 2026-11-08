import os, re
from pathlib import Path

tex_path = Path("UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde/reporte-antecedentes-de-los-derechos-humanos-Actividad-9.tex")
content = tex_path.read_text(encoding="utf-8")

# 1. Update document title line spacing
content = content.replace(
    r"\def\documenttitle {Aspectos hist\'oricos y te\'oricos de los derechos humanos en el mundo}",
    r"\def\documenttitle {Aspectos hist\'oricos y te\'oricos de los\\[6pt]derechos humanos en el mundo}"
)

# 2. Replace color definitions with AulaTeX canonical mc* styles in preamble
old_colors = r"""\definecolor{mainCore}{HTML}{1A365D}
\definecolor{branchHist}{HTML}{2B6CB0}
\definecolor{branchTeor}{HTML}{2C7A7B}
\definecolor{branchDoc}{HTML}{C05621}
\definecolor{branchInt}{HTML}{742A2A}
\definecolor{branchRecep}{HTML}{44337A}"""

new_colors_and_styles = r"""% ---- Estilos del mapa conceptual (AulaTeX mc*) ----
\definecolor{mcRoot}{HTML}{1A365D}
\definecolor{mcNode}{HTML}{2B6CB0}
\definecolor{mcLeaf}{HTML}{EBF4FF}
\definecolor{mcAccent}{HTML}{B88A2A}
\definecolor{mcInk}{HTML}{1A202C}
\definecolor{mcSub}{HTML}{E2E8F0}

\tikzset{
  mcroot/.style={
    rectangle, rounded corners=4pt, draw=mcRoot, line width=1.1pt,
    fill=mcRoot, text=white, font=\bfseries\footnotesize,
    align=center, inner sep=5pt, text width=3.5cm
  },
  mcbranch/.style={
    rectangle, rounded corners=3pt, draw=mcNode, line width=0.9pt,
    fill=mcNode, text=white, font=\bfseries\scriptsize,
    align=center, inner sep=4pt, text width=2.6cm
  },
  mcleaf/.style={
    rectangle, rounded corners=3pt, draw=mcNode!70, line width=0.5pt,
    fill=mcLeaf, text=mcInk, font=\scriptsize,
    align=center, inner sep=3.5pt, text width=3.0cm
  },
  mcsub/.style={
    rectangle, rounded corners=2pt, draw=mcAccent!80, line width=0.4pt,
    fill=mcSub, text=mcInk, font=\tiny,
    align=center, inner sep=2.5pt, text width=2.6cm
  },
  mclink/.style={
    -{Latex[length=1.6mm]}, draw=mcRoot!70, line width=0.55pt
  },
  mclabel/.style={
    font=\tiny\itshape, text=mcAccent, fill=white, inner sep=1pt,
    align=center
  }
}
\providecommand{\mcGold}{}
\colorlet{mcGold}{mcAccent}"""

content = content.replace(old_colors, new_colors_and_styles)

# 3. Clean meta-discourse on line 90
old_intro_end = r"El presente documento desarrolla, en el riguroso esquema de tres tiempos contractualizado por AulaTeX, la reconstrucci\'on de esta trayectoria: un segundo tiempo dedicado a la representaci\'on gr\'afica horizontal del mapa mental y su correlativo examen doctrinal pormenorizado, y un tercer tiempo consagrado a las conclusiones jur\'idicas sustantivas y a la reflexi\'on personal argumentada sobre el compromiso \'etico del jurista."
new_intro_end = r"El presente estudio desarrolla la reconstrucci\'on dogm\'atica de esta trayectoria articulada en tres apartados fundamentales: una introducci\'on contextual, un an\'alisis anal\'itico integral complementado con la representaci\'on gr\'afica en mapa conceptual en p\'agina horizontal, y una secci\'on final de conclusiones sustantivas y reflexi\'on personal de car\'acter jur\'idico-cr\'itico."

content = content.replace(old_intro_end, new_intro_end)

# 4. Replace the landscape page block
# Find from \newgeometry{margin=1.2cm} before landscape up to \restoregeometry
s_landscape = content.find(r"\begin{landscape}")
e_landscape = content.find(r"\end{landscape}") + len(r"\end{landscape}")
assert s_landscape >= 0 and e_landscape > s_landscape, "Landscape block not found!"

new_landscape_block = r"""\begin{landscape}
\thispagestyle{empty}
\pagestyle{empty}

\begin{center}
\vspace*{-0.3cm}
{\color{mcRoot}\Large\bfseries Mapa Conceptual: Aspectos Hist\'oricos, Doctrinales e Internacionales de los Derechos Humanos}
\end{center}

\begin{center}
\resizebox{!}{0.80\textheight}{%
\begin{tikzpicture}

% Nodo raiz
\node[mcroot] (root) at (0.00,0.40) {Concepto moderno de los derechos humanos\\(Dignidad humana, universalidad, inalienabilidad e indivisibilidad)};

% 5 Ramas
\node[mcbranch] (b1) at (-6.60,4.20) {1. Antecedentes hist\'oricos remotos\\(L\'imites al poder)};
\node[mcbranch] (b2) at (6.60,4.20) {2. Corrientes filos\'oficas y te\'oricas\\(Fundamentaci\'on)};
\node[mcbranch] (b3) at (-6.60,-3.20) {3. Revoluciones liberales\\(Positivaci\'on)};
\node[mcbranch] (b4) at (6.60,-3.20) {4. Internacionalizaci\'on post-guerra\\(Universalizaci\'on)};
\node[mcbranch] (b5) at (0.00,-4.60) {5. Reconocimiento en M\'exico\\(Bloque constitucional)};

% Proposiciones raiz -> ramas
\draw[mclink] (root) -- node[mclabel]{se originan en} (b1);
\draw[mclink] (root) -- node[mclabel]{se fundamentan en} (b2);
\draw[mclink] (root) -- node[mclabel]{se positivaron en} (b3);
\draw[mclink] (root) -- node[mclabel]{se universalizan con} (b4);
\draw[mclink] (root) -- node[mclabel]{se garantizan en} (b5);

% Hojas b1: Antecedentes historicos remotos
\node[mcleaf] (l1_1) at (-11.40,6.00) {\textbf{Cilindro de Ciro (539 a.C.):}\\Tolerancia religiosa, liberaci\'on y repatriaci\'on de cautivos \citep{rabinovich2014derechos}.};
\node[mcleaf] (l1_2) at (-11.40,4.20) {\textbf{Carta Magna inglesa (1215):}\\Juicio legal de iguales, debido proceso e interdicci\'on arbitraria \citep{parlamentoCarta1215ADH}.};
\node[mcleaf] (l1_3) at (-11.40,2.40) {\textbf{Tradici\'on brit\'anica (s. XVII):}\\Petition of Right (1628), Habeas Corpus (1679) y Bill of Rights (1689) \citep{parlamentoBill1689ADH}.};

% Hojas b2: Corrientes filosoficas y teoricas
\node[mcleaf] (l2_1) at (11.40,6.00) {\textbf{Iusnaturalismo racionalista:}\\Locke y Grocio; derechos innatos previos y superiores al Estado \citep{marcano2018derechos}.};
\node[mcleaf] (l2_2) at (11.40,4.20) {\textbf{Contractualismo y contrapesos:}\\Montesquieu y Rousseau; soberan\'ia popular y divisi\'on org\'anica de poderes.};
\node[mcleaf] (l2_3) at (11.40,2.40) {\textbf{Garantismo y Estado social:}\\Ferrajoli (l\'imites r\'igidos) y cartas sociales pioneras de 1917 y 1919 \citep{ferrajoli2008paradigma}.};

% Hojas b3: Revoluciones liberales y positivacion
\node[mcleaf] (l3_1) at (-11.40,-1.40) {\textbf{Independencia EE.UU. (1776):}\\Declaraci\'on de Virginia; derechos inalienables a la vida, libertad y felicidad \citep{congresoVirginia1776ADH}.};
\node[mcleaf] (l3_2) at (-11.40,-3.20) {\textbf{Revoluci\'on Francesa (1789):}\\Declaraci\'on del Hombre y del Ciudadano; igualdad formal y soberan\'ia \citep{declaracionFrancia1789ADH}.};
\node[mcleaf] (l3_3) at (-11.40,-5.00) {\textbf{Constituci\'on de C\'adiz (1812):}\\Soberan\'ia nacional y libertades civiles en el espacio hispanoamericano \citep{arteaga2016derecho}.};

% Hojas b4: Internacionalizacion post-guerra
\node[mcleaf] (l4_1) at (11.40,-1.40) {\textbf{Carta de la ONU (1945):}\\La paz mundial ligada indisolublemente a la tutela de derechos humanos \citep{onuCarta1945ADH}.};
\node[mcleaf] (l4_2) at (11.40,-3.20) {\textbf{DUDH (1948):}\\Declaraci\'on Universal; cat\'alogo \'etico global de 30 art\'iculos indivisibles \citep{onuDeclaracion1948ADH}.};
\node[mcleaf] (l4_3) at (11.40,-5.00) {\textbf{Tratados y Sistema Regional:}\\Pactos ONU 1966 (PIDCP/PIDESC) y Pacto de San Jos\'e (1969) \citep{oeaPacto1969ADH}.};

% Hojas b5: Reconocimiento en Mexico
\node[mcleaf] (l5_1) at (-4.40,-7.00) {\textbf{Reforma Constitucional 2011:}\\Art\'iculo 1$^\circ$ CPEUM; personas titulares de derechos de fuente nacional e internacional \citep{alvarezIcaza2009ADH}.};
\node[mcleaf] (l5_2) at (4.40,-7.00) {\textbf{Bloque de constitucionalidad:}\\Principio pro persona, interpretaci\'on conforme y par\'ametro vinculante \citep{scjnParametro2014ADH,medellin2013principio}.};

% Enlaces ramas -> hojas
\draw[mclink] (b1) -- (l1_1); \draw[mclink] (b1) -- (l1_2); \draw[mclink] (b1) -- (l1_3);
\draw[mclink] (b2) -- (l2_1); \draw[mclink] (b2) -- (l2_2); \draw[mclink] (b2) -- (l2_3);
\draw[mclink] (b3) -- (l3_1); \draw[mclink] (b3) -- (l3_2); \draw[mclink] (b3) -- (l3_3);
\draw[mclink] (b4) -- (l4_1); \draw[mclink] (b4) -- (l4_2); \draw[mclink] (b4) -- (l4_3);
\draw[mclink] (b5) -- (l5_1); \draw[mclink] (b5) -- (l5_2);

\end{tikzpicture}%
}

\vspace{0.15cm}
{\footnotesize \textit{Figura 1.} Mapa conceptual de los aspectos hist\'oricos, doctrinales e internacionales determinantes de los derechos humanos. Elaboraci\'on propia con base en las fuentes consultadas.}
\end{center}
\end{landscape}"""

content = content[:s_landscape] + new_landscape_block + content[e_landscape:]

tex_path.write_text(content, encoding="utf-8")
print("Updated reporte-antecedentes-de-los-derechos-humanos-Actividad-9.tex successfully!")

