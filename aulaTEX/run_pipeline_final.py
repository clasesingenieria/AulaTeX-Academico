import subprocess, os, shutil, sys
from pathlib import Path
import pymupdf

tex_path = Path("UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde/reporte-antecedentes-de-los-derechos-humanos-Actividad-9.tex")
content = tex_path.read_text(encoding="utf-8")

# Replace landscape block with the 5-column canonical tree
s_landscape = content.find(r"\begin{landscape}")
e_landscape = content.find(r"\end{landscape}") + len(r"\end{landscape}")
assert s_landscape >= 0 and e_landscape > s_landscape, "Landscape block not found!"

new_landscape_block = r"""\begin{landscape}
\thispagestyle{empty}
\pagestyle{empty}

\begin{center}
\vspace*{-0.25cm}
{\color{mcRoot}\Large\bfseries Mapa Conceptual: Aspectos Hist\'oricos, Doctrinales e Internacionales de los Derechos Humanos}
\end{center}

\begin{center}
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
\node[mcleaf, below=0.55cm of b1] (l1_1) {\textbf{Cilindro de Ciro (539 a.C.):}\\Tolerancia de cultos, liberaci\'on y repatriaci\'on de cautivos \citep{rabinovich2014derechos}};
\node[mcleaf, below=0.35cm of l1_1] (l1_2) {\textbf{Carta Magna (1215):}\\Juicio legal de iguales, debido proceso e interdicci\'on arbitraria \citep{parlamentoCarta1215ADH}};
\node[mcleaf, below=0.35cm of l1_2] (l1_3) {\textbf{Tradici\'on brit\'anica:}\\Petition of Right (1628), Habeas Corpus y Bill of Rights \citep{parlamentoBill1689ADH}};

% Hojas b2: Corrientes filosoficas y teoricas
\node[mcleaf, below=0.55cm of b2] (l2_1) {\textbf{Iusnaturalismo racionalista:}\\Prerrogativas innatas previas al Estado: vida y libertad \citep{marcano2018derechos}};
\node[mcleaf, below=0.35cm of l2_1] (l2_2) {\textbf{Contractualismo y poderes:}\\Soberan\'ia popular, voluntad general y divisi\'on org\'anica de poderes};
\node[mcleaf, below=0.35cm of l2_2] (l2_3) {\textbf{Garantismo y Estado social:}\\L\'imites sustantivos r\'igidos y cartas pioneras de 1917 y 1919 \citep{ferrajoli2008paradigma}};

% Hojas b5: Reconocimiento en Mexico
\node[mcleaf, below=0.55cm of b5] (l5_1) {\textbf{Reforma de 2011:}\\Art\'iculo 1$^\circ$ CPEUM; personas titulares de derechos humanos \citep{alvarezIcaza2009ADH}};
\node[mcleaf, below=0.35cm of l5_1] (l5_2) {\textbf{Bloque constitucional:}\\Tratados supremos y par\'ametro vinculante de regularidad \citep{scjnParametro2014ADH}};
\node[mcleaf, below=0.35cm of l5_2] (l5_3) {\textbf{Principios rectores:}\\Principio pro persona, universalidad, interpretaci\'on y progresividad \citep{medellin2013principio}};

% Hojas b3: Revoluciones liberales
\node[mcleaf, below=0.55cm of b3] (l3_1) {\textbf{Independencia EE.UU. (1776):}\\Declaraci\'on de Virginia; derechos inalienables y felicidad \citep{congresoVirginia1776ADH}};
\node[mcleaf, below=0.35cm of l3_1] (l3_2) {\textbf{Revoluci\'on Francesa (1789):}\\Declaraci\'on de derechos del hombre; igualdad formal y soberan\'ia \citep{declaracionFrancia1789ADH}};
\node[mcleaf, below=0.35cm of l3_2] (l3_3) {\textbf{Constituci\'on de C\'adiz (1812):}\\Soberan\'ia nacional y libertades en el espacio hispanoamericano \citep{arteaga2016derecho}};

% Hojas b4: Internacionalizacion post-guerra
\node[mcleaf, below=0.55cm of b4] (l4_1) {\textbf{Carta de la ONU (1945):}\\Paz internacional ligada a la tutela universal de la dignidad humana \citep{onuCarta1945ADH}};
\node[mcleaf, below=0.35cm of l4_1] (l4_2) {\textbf{DUDH (1948):}\\Cat\'alogo de 30 art\'iculos indivisibles y consenso global \citep{onuDeclaracion1948ADH}};
\node[mcleaf, below=0.35cm of l4_2] (l4_3) {\textbf{Tratados vinculantes:}\\Pactos ONU 1966 (PIDCP/PIDESC) y Pacto de San Jos\'e de 1969 \citep{oeaPacto1969ADH}};

% Enlaces ramas -> hojas
\draw[mclink] (b1) -- (l1_1); \draw[mclink] (l1_1) -- (l1_2); \draw[mclink] (l1_2) -- (l1_3);
\draw[mclink] (b2) -- (l2_1); \draw[mclink] (l2_1) -- (l2_2); \draw[mclink] (l2_2) -- (l2_3);
\draw[mclink] (b5) -- (l5_1); \draw[mclink] (l5_1) -- (l5_2); \draw[mclink] (l5_2) -- (l5_3);
\draw[mclink] (b3) -- (l3_1); \draw[mclink] (l3_1) -- (l3_2); \draw[mclink] (l3_2) -- (l3_3);
\draw[mclink] (b4) -- (l4_1); \draw[mclink] (l4_1) -- (l4_2); \draw[mclink] (l4_2) -- (l4_3);

\end{tikzpicture}%
}

\vspace{0.15cm}
{\footnotesize \textit{Figura 1.} Mapa conceptual de los aspectos hist\'oricos, doctrinales e internacionales determinantes de los derechos humanos. Elaboraci\'on propia con base en las fuentes consultadas.}
\end{center}
\end{landscape}"""

content = content[:s_landscape] + new_landscape_block + content[e_landscape:]
tex_path.write_text(content, encoding="utf-8")
print("Injected 5-column landscape tree into .tex!")

# Run optimize_mapa_layout.py
cmd = [
    sys.executable, "aulaTEX/optimize_mapa_layout.py", str(tex_path),
    "--iters", "2500", "--repulsion", "0.45", "--step", "0.25",
    "--spring", "0.008", "--xlim", "13.5", "--ylim", "8.5",
    "--write"
]
print("Running layout optimizer...")
res = subprocess.run(cmd, capture_output=True, text=True)
print("Optimizer output:\n", res.stdout)
if res.stderr:
    print("Optimizer stderr:\n", res.stderr)
assert res.returncode == 0, "Optimizer failed!"

# Compile PDF
root = Path('.').resolve()
subj = tex_path.parent
tex_name = 'reporte-antecedentes-de-los-derechos-humanos-Actividad-9'

env = os.environ.copy()
env['PATH'] = 'C:/texlive/2026/bin/windows;' + env['PATH']
env['TEXINPUTS'] = f'{root}/aulaTEX/base/Plantilla-Informe//;{subj}//;'

print("Pass 1 pdflatex...")
res1 = subprocess.run(['pdflatex', '-interaction=nonstopmode', f'{tex_name}.tex'], env=env, cwd=str(subj), capture_output=True, text=True)
assert res1.returncode == 0, f"Pass 1 failed: {res1.stdout[-300:]}"

print("Pass 2 pdflatex...")
res2 = subprocess.run(['pdflatex', '-interaction=nonstopmode', f'{tex_name}.tex'], env=env, cwd=str(subj), capture_output=True, text=True)
assert res2.returncode == 0, f"Pass 2 failed: {res2.stdout[-300:]}"

# Copy to deliverable path
delivery = subj / 'entregas-antecedentes-de-los-derechos-humanos/Actividad-7-Mapa-mental-Martin-Jonathan-de-la-Cruz.pdf'
shutil.copy2(subj / f'{tex_name}.pdf', delivery)
print(f"Copied deliverable to {delivery}")

# Check all pages with PyMuPDF
doc = pymupdf.open(subj / f'{tex_name}.pdf')
print(f"\nAUDIT: Total pages in document = {len(doc)}")
total_overlaps = 0
for pno in range(len(doc)):
    page = doc[pno]
    blocks = page.get_text("blocks")
    overlaps = []
    for i in range(len(blocks)):
        for j in range(i + 1, len(blocks)):
            b1, b2 = blocks[i][:4], blocks[j][:4]
            ix1, iy1 = max(b1[0], b2[0]), max(b1[1], b2[1])
            ix2, iy2 = min(b1[2], b2[2]), min(b1[3], b2[3])
            if ix2 > ix1 + 2 and iy2 > iy1 + 2:
                overlaps.append((blocks[i][4].strip().replace("\n", " ")[:25], blocks[j][4].strip().replace("\n", " ")[:25]))
    if overlaps:
        print(f"  Page {pno+1}: {len(overlaps)} overlaps: {overlaps}")
        total_overlaps += len(overlaps)
    else:
        print(f"  Page {pno+1}: 0 overlaps (OK)")

print(f"\nTOTAL OVERLAPS ACROSS ENTIRE DOCUMENT: {total_overlaps}")

