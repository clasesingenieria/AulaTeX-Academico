import subprocess, sys
from pathlib import Path
import pymupdf

test_tex = Path(".aulatex-temp/test_5col.tex")

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
    align=center, inner sep=5pt, text width=3.8cm
  },
  mcbranch/.style={
    rectangle, rounded corners=3pt, draw=mcNode, line width=0.9pt,
    fill=mcNode, text=white, font=\bfseries\scriptsize,
    align=center, inner sep=4pt, text width=2.4cm
  },
  mcleaf/.style={
    rectangle, rounded corners=3pt, draw=mcNode!70, line width=0.5pt,
    fill=mcLeaf, text=mcInk, font=\scriptsize,
    align=center, inner sep=3pt, text width=2.6cm
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
\resizebox{!}{0.84\textheight}{%
\begin{tikzpicture}[node distance=0.45cm and 0.8cm]

% Nodo raiz
\node[mcroot] (root) {Concepto moderno de los derechos humanos y sus fundamentos};

% 5 Ramas
\node[mcbranch, below left=1.5cm and 8.0cm of root] (b1) {1. Antecedentes hist\'oricos remotos};
\node[mcbranch, below left=1.5cm and 3.8cm of root] (b2) {2. Corrientes filos\'oficas y te\'oricas};
\node[mcbranch, below=1.6cm of root] (b5) {5. Reconocimiento en M\'exico};
\node[mcbranch, below right=1.5cm and 3.8cm of root] (b3) {3. Revoluciones liberales};
\node[mcbranch, below right=1.5cm and 8.0cm of root] (b4) {4. Internacionalizaci\'on post-guerra};

% Proposiciones raiz -> ramas
\draw[mclink] (root) -- node[mclabel]{se originan en} (b1);
\draw[mclink] (root) -- node[mclabel]{se fundamentan en} (b2);
\draw[mclink] (root) -- node[mclabel]{se positivaron en} (b3);
\draw[mclink] (root) -- node[mclabel]{se universalizan con} (b4);
\draw[mclink] (root) -- node[mclabel]{se garantizan en} (b5);

% Hojas b1: Antecedentes historicos remotos
\node[mcleaf, below=0.55cm of b1] (l1_1) {\textbf{Cilindro de Ciro (539 a.C.):}\\Tolerancia religiosa, liberaci\'on y repatriaci\'on de cautivos};
\node[mcleaf, below=0.35cm of l1_1] (l1_2) {\textbf{Carta Magna (1215):}\\Juicio de iguales, debido proceso e interdicci\'on arbitraria};
\node[mcleaf, below=0.35cm of l1_2] (l1_3) {\textbf{Tradici\'on brit\'anica:}\\Petition of Right (1628) y Bill of Rights (1689)};

% Hojas b2: Corrientes filosoficas y teoricas
\node[mcleaf, below=0.55cm of b2] (l2_1) {\textbf{Iusnaturalismo racionalista:}\\Prerrogativas innatas previas al Estado: vida, libertad y propiedad};
\node[mcleaf, below=0.35cm of l2_1] (l2_2) {\textbf{Contractualismo y poderes:}\\Soberan\'ia popular, voluntad general y divisi\'on org\'anica};
\node[mcleaf, below=0.35cm of l2_2] (l2_3) {\textbf{Garantismo y Estado social:}\\L\'imites r\'igidos y cartas pioneras de 1917 y 1919};

% Hojas b5: Reconocimiento en Mexico
\node[mcleaf, below=0.55cm of b5] (l5_1) {\textbf{Reforma de 2011:}\\Art\'iculo 1$^\circ$ CPEUM; personas titulares de derechos};
\node[mcleaf, below=0.35cm of l5_1] (l5_2) {\textbf{Bloque constitucional:}\\Tratados supremos y par\'ametro vinculante de la SCJN};
\node[mcleaf, below=0.35cm of l5_2] (l5_3) {\textbf{Principios rectores:}\\Principio pro persona, universalidad y progresividad};

% Hojas b3: Revoluciones liberales
\node[mcleaf, below=0.55cm of b3] (l3_1) {\textbf{Independencia EE.UU. (1776):}\\Declaraci\'on de Virginia; derechos inalienables y felicidad};
\node[mcleaf, below=0.35cm of l3_1] (l3_2) {\textbf{Revoluci\'on Francesa (1789):}\\Declaraci\'on de derechos; igualdad formal y soberan\'ia};
\node[mcleaf, below=0.35cm of l3_2] (l3_3) {\textbf{Constituci\'on de C\'adiz (1812):}\\Soberan\'ia nacional y libertades en el espacio hispano};

% Hojas b4: Internacionalizacion post-guerra
\node[mcleaf, below=0.55cm of b4] (l4_1) {\textbf{Carta de la ONU (1945):}\\Paz internacional y tutela universal de la dignidad};
\node[mcleaf, below=0.35cm of l4_1] (l4_2) {\textbf{DUDH (1948):}\\Cat\'alogo de 30 art\'iculos indivisibles e inalienables};
\node[mcleaf, below=0.35cm of l4_2] (l4_3) {\textbf{Tratados vinculantes:}\\Pactos ONU 1966 (PIDCP/PIDESC) y CADH 1969};

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
    "--iters", "2000", "--repulsion", "0.45", "--step", "0.25",
    "--spring", "0.008", "--xlim", "13.5", "--ylim", "8.5",
    "--write"
]
res = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:\n", res.stdout)
if res.stderr:
    print("STDERR:\n", res.stderr)

