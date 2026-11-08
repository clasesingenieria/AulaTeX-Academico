import subprocess, sys
from pathlib import Path

test_tex = Path(".aulatex-temp/test_radial.tex")

sample = r"""\documentclass[12pt,spanish,letterpaper,oneside]{article}
\usepackage{tikz}
\usetikzlibrary{shapes.geometric,arrows.meta,positioning,calc,fit,shadows}
\usepackage{pdflscape}

\definecolor{mcRoot}{HTML}{1A365D}
\definecolor{mcNode}{HTML}{2B6CB0}
\definecolor{mcLeaf}{HTML}{EBF4FF}
\definecolor{mcAccent}{HTML}{B88A2A}
\definecolor{mcInk}{HTML}{1A202C}
\definecolor{mcSub}{HTML}{E2E8F0}

\tikzset{
  mcroot/.style={
    rectangle, rounded corners=4pt, draw=mcRoot, line width=1pt,
    fill=mcRoot, text=white, font=\bfseries\footnotesize,
    align=center, inner sep=5pt, text width=3.4cm
  },
  mcbranch/.style={
    rectangle, rounded corners=3pt, draw=mcNode, line width=0.9pt,
    fill=mcNode, text=white, font=\bfseries\scriptsize,
    align=center, inner sep=4pt, text width=2.6cm
  },
  mcleaf/.style={
    rectangle, rounded corners=3pt, draw=mcNode!70, line width=0.5pt,
    fill=mcLeaf, text=mcInk, font=\scriptsize,
    align=center, inner sep=3pt, text width=2.8cm
  },
  mcsub/.style={
    rectangle, rounded corners=2pt, draw=mcGold!80, line width=0.4pt,
    fill=mcSub, text=mcInk, font=\tiny,
    align=center, inner sep=2.5pt, text width=2.5cm
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
\colorlet{mcGold}{mcAccent}

\begin{document}

\begin{landscape}
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
\node[mcroot] (root) at (0.00, 0.40) {Concepto moderno de los derechos humanos\\(Dignidad, universalidad e inalienabilidad)};

% 5 Ramas
\node[mcbranch] (b1) at (-6.50, 4.20) {1. Antecedentes hist\'oricos remotos};
\node[mcbranch] (b2) at (6.50, 4.20) {2. Corrientes filos\'oficas y te\'oricas};
\node[mcbranch] (b3) at (-6.50, -3.20) {3. Revoluciones liberales y positivaci\'on};
\node[mcbranch] (b4) at (6.50, -3.20) {4. Internacionalizaci\'on post-guerra};
\node[mcbranch] (b5) at (0.00, -4.60) {5. Reconocimiento en M\'exico};

% Proposiciones raiz -> ramas
\draw[mclink] (root) -- node[mclabel]{se originan en} (b1);
\draw[mclink] (root) -- node[mclabel]{se fundamentan en} (b2);
\draw[mclink] (root) -- node[mclabel]{se positivaron en} (b3);
\draw[mclink] (root) -- node[mclabel]{se universalizan con} (b4);
\draw[mclink] (root) -- node[mclabel]{se garantizan en} (b5);

% Hojas b1: Antecedentes historicos remotos
\node[mcleaf] (l1_1) at (-11.20, 6.00) {\textbf{Cilindro de Ciro (539 a.C.):}\\Tolerancia de cultos y liberaci\'on};
\node[mcleaf] (l1_2) at (-11.20, 4.20) {\textbf{Carta Magna inglesa (1215):}\\Juicio legal y debido proceso};
\node[mcleaf] (l1_3) at (-11.20, 2.40) {\textbf{Tradici\'on brit\'anica (s. XVII):}\\Petition of Right y Bill of Rights};

% Hojas b2: Corrientes filosoficas y teoricas
\node[mcleaf] (l2_1) at (11.20, 6.00) {\textbf{Iusnaturalismo racionalista:}\\Prerrogativas innatas previas al Estado};
\node[mcleaf] (l2_2) at (11.20, 4.20) {\textbf{Contractualismo y contrapesos:}\\Soberan\'ia popular y divisi\'on de poderes};
\node[mcleaf] (l2_3) at (11.20, 2.40) {\textbf{Garantismo y Estado social:}\\L\'imites r\'igidos y cartas de 1917 y 1919};

% Hojas b3: Revoluciones liberales y positivacion
\node[mcleaf] (l3_1) at (-11.20, -1.40) {\textbf{Independencia EE.UU. (1776):}\\Declaraci\'on de Virginia y derechos};
\node[mcleaf] (l3_2) at (-11.20, -3.20) {\textbf{Revoluci\'on Francesa (1789):}\\Declaraci\'on de derechos del hombre};
\node[mcleaf] (l3_3) at (-11.20, -5.00) {\textbf{Constituci\'on de C\'adiz (1812):}\\Soberan\'ia nacional y libertades};

% Hojas b4: Internacionalizacion post-guerra
\node[mcleaf] (l4_1) at (11.20, -1.40) {\textbf{Carta de la ONU (1945):}\\Paz internacional y derechos humanos};
\node[mcleaf] (l4_2) at (11.20, -3.20) {\textbf{DUDH (1948):}\\Cat\'alogo de 30 art\'iculos indivisibles};
\node[mcleaf] (l4_3) at (11.20, -5.00) {\textbf{Tratados y Sistema Regional:}\\Pactos ONU 1966 y Pacto de San Jos\'e};

% Hojas b5: Reconocimiento en Mexico
\node[mcleaf] (l5_1) at (-4.20, -7.00) {\textbf{Reforma Constitucional 2011:}\\Art\'iculo 1$^\circ$ CPEUM y centralidad};
\node[mcleaf] (l5_2) at (4.20, -7.00) {\textbf{Bloque de constitucionalidad:}\\Tratados supremos y par\'ametro vinculante};

% Enlaces ramas -> hojas
\draw[mclink] (b1) -- (l1_1); \draw[mclink] (b1) -- (l1_2); \draw[mclink] (b1) -- (l1_3);
\draw[mclink] (b2) -- (l2_1); \draw[mclink] (b2) -- (l2_2); \draw[mclink] (b2) -- (l2_3);
\draw[mclink] (b3) -- (l3_1); \draw[mclink] (b3) -- (l3_2); \draw[mclink] (b3) -- (l3_3);
\draw[mclink] (b4) -- (l4_1); \draw[mclink] (b4) -- (l4_2); \draw[mclink] (b4) -- (l4_3);
\draw[mclink] (b5) -- (l5_1); \draw[mclink] (b5) -- (l5_2);

\end{tikzpicture}%
}
\end{center}
\end{landscape}

\end{document}
"""

test_tex.write_text(sample, encoding="utf-8")

cmd = [
    sys.executable, "aulaTEX/optimize_mapa_layout.py", str(test_tex),
    "--iters", "1500", "--repulsion", "0.4", "--step", "0.25",
    "--spring", "0.01", "--xlim", "13.5", "--ylim", "8.5",
    "--write"
]
res = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:\n", res.stdout)
if res.stderr:
    print("STDERR:\n", res.stderr)

