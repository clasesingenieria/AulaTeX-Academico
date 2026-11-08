import subprocess, os, shutil, sys
from pathlib import Path
import pymupdf

tex_path = Path("UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde/reporte-antecedentes-de-los-derechos-humanos-Actividad-9.tex")
content = tex_path.read_text(encoding="utf-8")

s_landscape = content.find(r"\begin{landscape}")
e_landscape = content.find(r"\end{landscape}") + len(r"\end{landscape}")
assert s_landscape >= 0 and e_landscape > s_landscape, "Landscape block not found!"

perfect_landscape = r"""\begin{landscape}
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
\node[mcleaf] (l1_1) at (-10.80, -1.50) {\textbf{Cilindro de Ciro (539 a.C.):}\\Tolerancia de cultos, liberaci\'on y repatriaci\'on de cautivos};
\node[mcleaf] (l1_2) at (-10.80, -4.10) {\textbf{Carta Magna inglesa (1215):}\\Juicio legal de iguales, debido proceso e interdicci\'on arbitraria};
\node[mcleaf] (l1_3) at (-10.80, -6.70) {\textbf{Tradici\'on brit\'anica (s. XVII):}\\Petition of Right (1628), Habeas Corpus y Bill of Rights (1689)};

% Hojas b2: Corrientes filosoficas y teoricas
\node[mcleaf] (l2_1) at (-5.40, -1.50) {\textbf{Iusnaturalismo racionalista:}\\Prerrogativas innatas previas al Estado: vida, libertad y propiedad};
\node[mcleaf] (l2_2) at (-5.40, -4.10) {\textbf{Contractualismo y poderes:}\\Soberan\'ia popular, voluntad general y divisi\'on org\'anica de poderes};
\node[mcleaf] (l2_3) at (-5.40, -6.70) {\textbf{Garantismo y Estado social:}\\L\'imites sustantivos r\'igidos y cartas pioneras de 1917 y 1919};

% Hojas b5: Reconocimiento en Mexico
\node[mcleaf] (l5_1) at (0.00, -1.50) {\textbf{Reforma Constitucional 2011:}\\Art\'iculo 1$^\circ$ CPEUM; personas titulares de derechos humanos};
\node[mcleaf] (l5_2) at (0.00, -4.10) {\textbf{Bloque de constitucionalidad:}\\Tratados supremos y par\'ametro vinculante de regularidad};
\node[mcleaf] (l5_3) at (0.00, -6.70) {\textbf{Principios rectores:}\\Principio pro persona, universalidad, interpretaci\'on y progresividad};

% Hojas b3: Revoluciones liberales
\node[mcleaf] (l3_1) at (5.40, -1.50) {\textbf{Independencia EE.UU. (1776):}\\Declaraci\'on de Virginia; derechos inalienables y felicidad};
\node[mcleaf] (l3_2) at (5.40, -4.10) {\textbf{Revoluci\'on Francesa (1789):}\\Declaraci\'on del Hombre y del Ciudadano; igualdad formal y soberan\'ia};
\node[mcleaf] (l3_3) at (5.40, -6.70) {\textbf{Constituci\'on de C\'adiz (1812):}\\Soberan\'ia nacional y libertades en el espacio hispanoamericano};

% Hojas b4: Internacionalizacion post-guerra
\node[mcleaf] (l4_1) at (10.80, -1.50) {\textbf{Carta de la ONU (1945):}\\Paz internacional ligada a la tutela universal de la dignidad};
\node[mcleaf] (l4_2) at (10.80, -4.10) {\textbf{DUDH (1948):}\\Cat\'alogo de 30 art\'iculos indivisibles y consenso global};
\node[mcleaf] (l4_3) at (10.80, -6.70) {\textbf{Tratados vinculantes:}\\Pactos ONU 1966 (PIDCP/PIDESC) y Pacto de San Jos\'e (1969)};

% Enlaces ramas -> hojas
\draw[mclink] (b1) -- (l1_1); \draw[mclink] (b1) -- (l1_2); \draw[mclink] (b1) -- (l1_3);
\draw[mclink] (b2) -- (l2_1); \draw[mclink] (b2) -- (l2_2); \draw[mclink] (b2) -- (l2_3);
\draw[mclink] (b5) -- (l5_1); \draw[mclink] (l5_1) -- (l5_2); \draw[mclink] (l5_2) -- (l5_3);
\draw[mclink] (b3) -- (l3_1); \draw[mclink] (b3) -- (l3_2); \draw[mclink] (b3) -- (l3_3);
\draw[mclink] (b4) -- (l4_1); \draw[mclink] (l4_1) -- (l4_2); \draw[mclink] (l4_2) -- (l4_3);

\end{tikzpicture}%
}

\vspace{0.15cm}
{\footnotesize \textit{Figura 1.} Mapa conceptual de los aspectos hist\'oricos, doctrinales e internacionales determinantes de los derechos humanos. Elaboraci\'on propia con base en \citet{rabinovich2014derechos}, \citet{marcano2018derechos}, \citet{ferrajoli2008paradigma}, \citet{arteaga2016derecho} y \citet{alvarezIcaza2009ADH}.}
\end{center}
\end{landscape}"""

content = content[:s_landscape] + perfect_landscape + content[e_landscape:]
tex_path.write_text(content, encoding="utf-8")
print("1. Injected 5-column landscape tree into .tex!")

# Run optimize_mapa_layout.py
cmd = [
    sys.executable, "aulaTEX/optimize_mapa_layout.py", str(tex_path),
    "--iters", "2000", "--repulsion", "0.4", "--step", "0.2",
    "--spring", "0.01", "--xlim", "13.5", "--ylim", "8.5",
    "--write"
]
print("2. Running layout optimizer...")
res = subprocess.run(cmd, capture_output=True, text=True)
print("Optimizer output:\n", res.stdout)
assert res.returncode == 0, "Optimizer failed!"

# Compile PDF
root = Path('.').resolve()
subj = tex_path.parent
tex_name = 'reporte-antecedentes-de-los-derechos-humanos-Actividad-9'

env = os.environ.copy()
env['PATH'] = 'C:/texlive/2026/bin/windows;' + env['PATH']
env['TEXINPUTS'] = f'{root}/aulaTEX/base/Plantilla-Informe//;{subj}//;'

print("3. Compiling PDF (Pass 1)...")
res1 = subprocess.run(['pdflatex', '-interaction=nonstopmode', f'{tex_name}.tex'], env=env, cwd=str(subj), capture_output=True, text=True)
assert res1.returncode == 0, f"Pass 1 failed: {res1.stdout[-300:]}"

print("4. Compiling PDF (Pass 2)...")
res2 = subprocess.run(['pdflatex', '-interaction=nonstopmode', f'{tex_name}.tex'], env=env, cwd=str(subj), capture_output=True, text=True)
assert res2.returncode == 0, f"Pass 2 failed: {res2.stdout[-300:]}"

# Copy to deliverable path
delivery = subj / 'entregas-antecedentes-de-los-derechos-humanos/Actividad-7-Mapa-mental-Martin-Jonathan-de-la-Cruz.pdf'
shutil.copy2(subj / f'{tex_name}.pdf', delivery)
print(f"5. Copied deliverable to {delivery}")

# Check all pages with PyMuPDF
doc = pymupdf.open(subj / f'{tex_name}.pdf')
print(f"\nAUDIT: Total pages in document = {len(doc)}")
total_block_overlaps = 0
total_word_overlaps = 0

for pno in range(len(doc)):
    page = doc[pno]
    blocks = page.get_text("blocks")
    words = page.get_text("words")
    
    b_ov = []
    for i in range(len(blocks)):
        for j in range(i + 1, len(blocks)):
            b1, b2 = blocks[i][:4], blocks[j][:4]
            ix1, iy1 = max(b1[0], b2[0]), max(b1[1], b2[1])
            ix2, iy2 = min(b1[2], b2[2]), min(b1[3], b2[3])
            if ix2 > ix1 + 2 and iy2 > iy1 + 2:
                b_ov.append((blocks[i][4].strip().replace("\n", " ")[:25], blocks[j][4].strip().replace("\n", " ")[:25]))
    
    w_ov = []
    for i in range(len(words)):
        for j in range(i + 1, len(words)):
            b1, b2 = words[i][:4], words[j][:4]
            ix1, iy1 = max(b1[0], b2[0]), max(b1[1], b2[1])
            ix2, iy2 = min(b1[2], b2[2]), min(b1[3], b2[3])
            if ix2 > ix1 + 1 and iy2 > iy1 + 1:
                w_ov.append((words[i][4], words[j][4]))
                
    if b_ov or w_ov:
        print(f"  Page {pno+1}: {len(b_ov)} block overlaps, {len(w_ov)} word overlaps! ({b_ov})")
        total_block_overlaps += len(b_ov)
        total_word_overlaps += len(w_ov)
    else:
        print(f"  Page {pno+1}: 0 block overlaps, 0 word overlaps (PERFECT)")

print(f"\nFINAL VERIFICATION: Block overlaps = {total_block_overlaps}, Word overlaps = {total_word_overlaps}")

