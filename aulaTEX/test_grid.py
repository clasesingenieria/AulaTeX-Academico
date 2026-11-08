import subprocess, sys
from pathlib import Path
import pymupdf

test_tex = Path(".aulatex-temp/test_perfect_grid.tex")

sample = r"""\documentclass[12pt,spanish,letterpaper,oneside]{article}
\usepackage{tikz}
\usetikzlibrary{shapes.geometric,arrows.meta,positioning,calc,fit,shadows}
\usepackage{pdflscape}
\usepackage{natbib}
\setcitestyle{authoryear,open={(},close={)}}

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
    align=center, inner sep=5pt, text width=4.0cm
  },
  mcbranch/.style={
    rectangle, rounded corners=3pt, draw=mcNode, line width=0.9pt,
    fill=mcNode, text=white, font=\bfseries\scriptsize,
    align=center, inner sep=4pt, text width=2.4cm
  },
  mcleaf/.style={
    rectangle, rounded corners=3pt, draw=mcNode!70, line width=0.5pt,
    fill=mcLeaf, text=mcInk, font=\scriptsize,
    align=center, inner sep=3pt, text width=2.5cm
  },
  mcsub/.style={
    rectangle, rounded corners=2pt, draw=mcGold!80, line width=0.4pt,
    fill=mcSub, text=mcInk, font=\tiny,
    align=center, inner sep=2.5pt, text width=2.4cm
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
\vspace*{-0.25cm}
{\color{mcRoot}\Large\bfseries Mapa Conceptual: Aspectos Hist\'oricos, Doctrinales e Internacionales de los Derechos Humanos}
\end{center}

\begin{center}
\resizebox{!}{0.84\textheight}{%
\begin{tikzpicture}

% Nodo raiz
\node[mcroot] (root) at (0.00, 3.80) {Concepto moderno de los derechos humanos y sus fundamentos};

% 5 Ramas
\node[mcbranch] (b1) at (-10.80, 1.10) {1. Antecedentes hist\'oricos remotos};
\node[mcbranch] (b2) at (-5.40, 1.10) {2. Corrientes filos\'oficas y te\'oricas};
\node[mcbranch] (b5) at (0.00, 1.10) {5. Reconocimiento en M\'exico};
\node[mcbranch] (b3) at (5.40, 1.10) {3. Revoluciones liberales};
\node[mcbranch] (b4) at (10.80, 1.10) {4. Internacionalizaci\'on post-guerra};

% Proposiciones raiz -> ramas
\draw[mclink] (root) -- node[mclabel]{se originan en} (b1);
\draw[mclink] (root) -- node[mclabel]{se fundamentan en} (b2);
\draw[mclink] (root) -- node[mclabel]{se positivaron en} (b3);
\draw[mclink] (root) -- node[mclabel]{se universalizan con} (b4);
\draw[mclink] (root) -- node[mclabel]{se garantizan en} (b5);

% Hojas b1: Antecedentes historicos remotos
\node[mcleaf] (l1_1) at (-10.80, -1.50) {\textbf{Cilindro de Ciro (539 a.C.):}\\Tolerancia de cultos, liberaci\'on y repatriaci\'on de cautivos \citep{rabinovich2014derechos}};
\node[mcleaf] (l1_2) at (-10.80, -4.10) {\textbf{Carta Magna (1215):}\\Juicio legal de iguales, debido proceso e interdicci\'on arbitraria \citep{parlamentoCarta1215ADH}};
\node[mcleaf] (l1_3) at (-10.80, -6.70) {\textbf{Tradici\'on brit\'anica:}\\Petition of Right (1628), Habeas Corpus y Bill of Rights \citep{parlamentoBill1689ADH}};

% Hojas b2: Corrientes filosoficas y teoricas
\node[mcleaf] (l2_1) at (-5.40, -1.50) {\textbf{Iusnaturalismo racionalista:}\\Prerrogativas innatas previas al Estado: vida y libertad \citep{marcano2018derechos}};
\node[mcleaf] (l2_2) at (-5.40, -4.10) {\textbf{Contractualismo y poderes:}\\Soberan\'ia popular, voluntad general y divisi\'on org\'anica de poderes};
\node[mcleaf] (l2_3) at (-5.40, -6.70) {\textbf{Garantismo y Estado social:}\\L\'imites sustantivos r\'igidos y cartas pioneras de 1917 y 1919 \citep{ferrajoli2008paradigma}};

% Hojas b5: Reconocimiento en Mexico
\node[mcleaf] (l5_1) at (0.00, -1.50) {\textbf{Reforma de 2011:}\\Art\'iculo 1$^\circ$ CPEUM; personas titulares de derechos humanos \citep{alvarezIcaza2009ADH}};
\node[mcleaf] (l5_2) at (0.00, -4.10) {\textbf{Bloque constitucional:}\\Tratados supremos y par\'ametro vinculante de regularidad \citep{scjnParametro2014ADH}};
\node[mcleaf] (l5_3) at (0.00, -6.70) {\textbf{Principios rectores:}\\Principio pro persona, universalidad, interpretaci\'on y progresividad \citep{medellin2013principio}};

% Hojas b3: Revoluciones liberales
\node[mcleaf] (l3_1) at (5.40, -1.50) {\textbf{Independencia EE.UU. (1776):}\\Declaraci\'on de Virginia; derechos inalienables y felicidad \citep{congresoVirginia1776ADH}};
\node[mcleaf] (l3_2) at (5.40, -4.10) {\textbf{Revoluci\'on Francesa (1789):}\\Declaraci\'on de derechos del hombre; igualdad formal y soberan\'ia \citep{declaracionFrancia1789ADH}};
\node[mcleaf] (l3_3) at (5.40, -6.70) {\textbf{Constituci\'on de C\'adiz (1812):}\\Soberan\'ia nacional y libertades en el espacio hispanoamericano \citep{arteaga2016derecho}};

% Hojas b4: Internacionalizacion post-guerra
\node[mcleaf] (l4_1) at (10.80, -1.50) {\textbf{Carta de la ONU (1945):}\\Paz internacional ligada a la tutela universal de la dignidad humana \citep{onuCarta1945ADH}};
\node[mcleaf] (l4_2) at (10.80, -4.10) {\textbf{DUDH (1948):}\\Cat\'alogo de 30 art\'iculos indivisibles y consenso global \citep{onuDeclaracion1948ADH}};
\node[mcleaf] (l4_3) at (10.80, -6.70) {\textbf{Tratados vinculantes:}\\Pactos ONU 1966 (PIDCP/PIDESC) y Pacto de San Jos\'e de 1969 \citep{oeaPacto1969ADH}};

% Enlaces ramas -> hojas
\draw[mclink] (b1) -- (l1_1); \draw[mclink] (l1_1) -- (l1_2); \draw[mclink] (l1_2) -- (l1_3);
\draw[mclink] (b2) -- (l2_1); \draw[mclink] (l2_1) -- (l2_2); \draw[mclink] (l2_2) -- (l2_3);
\draw[mclink] (b5) -- (l5_1); \draw[mclink] (l5_1) -- (l5_2); \draw[mclink] (l5_2) -- (l5_3);
\draw[mclink] (b3) -- (l3_1); \draw[mclink] (l3_1) -- (l3_2); \draw[mclink] (l3_2) -- (l3_3);
\draw[mclink] (b4) -- (l4_1); \draw[mclink] (l4_1) -- (l4_2); \draw[mclink] (l4_2) -- (l4_3);

\end{tikzpicture}%
}
\end{center}
\end{landscape}

\end{document}
"""

test_tex.write_text(sample, encoding="utf-8")

cmd = [
    sys.executable, "aulaTEX/optimize_mapa_layout.py", str(test_tex),
    "--iters", "2000", "--repulsion", "0.4", "--step", "0.2",
    "--spring", "0.01", "--xlim", "13.5", "--ylim", "8.5",
    "--write"
]
res = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:\n", res.stdout)

