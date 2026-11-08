import subprocess, os, shutil, hashlib, pymupdf
from pathlib import Path

root = Path('.').resolve()
subj = root / 'UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde'
tex_file = subj / 'reporte-antecedentes-de-los-derechos-humanos-Actividad-9.tex'

with open(tex_file, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Fix subtitle, header, and footer wrapping variables
old_sub = r"\def\documentsubtitle {Evoluci\'on internacional, fundamentaci\'on dogm\'atica y recepci\'on constitucional}"
new_sub = (
    r"\def\documentsubtitle {Evoluci\'on y fundamentaci\'on dogm\'atica}" + "\n" +
    r"\def\documenttitlehf {Evoluci\'on de los derechos humanos}" + "\n" +
    r"\def\hfwidthwrap {true}" + "\n" +
    r"\def\hfwidthtitle {0.48}" + "\n" +
    r"\def\hfwidthcourse {0.46}"
)
if old_sub in text:
    text = text.replace(old_sub, new_sub)

# Also ensure \hfwidthwrap is true even if old_sub was already modified
if r"\def\hfwidthwrap {true}" not in text:
    text = text.replace(r"\def\documentsubject", new_sub + "\n" + r"\def\documentsubject")

# 2. Fix the AI declaration footnote strictly adhering to user instructions:
# "sólo tiene que señalar que un modelo quizás chatGPT fue usado para la revisión del texo y que la originalidad del contenido es propio, la autoria es propia, la responsalidad del texo contenido e ides son propias, algo así"
# NO mentions of aulatex, latex, tikz
old_fn_start = text.find(r"\footnote{Declaraci\'on")
if old_fn_start != -1:
    old_fn_end = text.find(r"}", text.find(r"formuladas.", old_fn_start)) + 1
    new_footnote = r"\footnote{Declaraci\'on sobre el uso de inteligencia artificial: Se utiliz\'o un modelo de lenguaje (asistencia tipo ChatGPT) exclusivamente como apoyo para la revisi\'on y correcci\'on de estilo del texto. La autor\'ia intelectual, la originalidad del contenido y las ideas desarrolladas son propias del estudiante, quien asume la plena responsabilidad sobre el texto, el an\'alisis jur\'idico y las conclusiones aqu\'i formuladas.}"
    text = text[:old_fn_start] + new_footnote + text[old_fn_end:]
    print("Replaced AI footnote successfully!")

# 3. Replace TikZ diagram with scaled and nicely centered version
t_start = text.find(r"\begin{tikzpicture}[")
t_end = text.find(r"\end{tikzpicture}") + len(r"\end{tikzpicture}")
assert t_start != -1 and t_end != -1, "TikZ block not found"

new_tikz = r"""\begin{tikzpicture}[
  scale=0.82, every node/.style={transform shape},
  centerNode/.style={ellipse, draw=mainCore, fill=mainCore!12, line width=2pt, align=center, text width=5.4cm, font=\bfseries\small, drop shadow},
  branchHistNode/.style={rectangle, rounded corners=5pt, draw=branchHist, fill=branchHist!10, line width=1.4pt, align=center, text width=4.1cm, font=\bfseries\footnotesize},
  branchTeorNode/.style={rectangle, rounded corners=5pt, draw=branchTeor, fill=branchTeor!10, line width=1.4pt, align=center, text width=4.1cm, font=\bfseries\footnotesize},
  branchDocNode/.style={rectangle, rounded corners=5pt, draw=branchDoc, fill=branchDoc!10, line width=1.4pt, align=center, text width=4.1cm, font=\bfseries\footnotesize},
  branchIntNode/.style={rectangle, rounded corners=5pt, draw=branchInt, fill=branchInt!10, line width=1.4pt, align=center, text width=4.1cm, font=\bfseries\footnotesize},
  branchRecepNode/.style={rectangle, rounded corners=5pt, draw=branchRecep, fill=branchRecep!10, line width=1.4pt, align=center, text width=5.6cm, font=\bfseries\footnotesize},
  leafNode/.style={rectangle, rounded corners=3pt, draw=gray!50, fill=white, line width=0.7pt, align=left, text width=4.2cm, font=\scriptsize, drop shadow},
  leafNodeWide/.style={rectangle, rounded corners=3pt, draw=gray!50, fill=white, line width=0.7pt, align=left, text width=4.6cm, font=\scriptsize, drop shadow},
  connMain/.style={-Latex, line width=1.5pt},
  connLeaf/.style={-Latex, line width=1.0pt, draw=gray!70}
]

% Nodo central
\node (core) at (0, 0.4) [centerNode] {{\large\textbf{CONCEPTO MODERNO}}\\[1mm]{\large\textbf{DE LOS DERECHOS HUMANOS}}\\\vspace{1.5mm}\textbf{N\'ucleo: Dignidad Humana}\\Universalidad $\cdot$ Inalienabilidad\\Indivisibilidad $\cdot$ Progresividad};

% Rama 1: Antecedentes Historicos Remotos (Arriba Izquierda)
\node (bHist) at (-6.2, 3.7) [branchHistNode] {1. ANTECEDENTES HIST\'ORICOS\\REMOTOS (L\'imites al Poder)};
\node (lHist1) at (-11.2, 5.2) [leafNode] {\textbf{Cilindro de Ciro (539 a.C.):}\\Tolerancia de cultos, liberaci\'on de cautivos e igualdad ling\"u\'istica \citep{rabinovich2014derechos}.};
\node (lHist2) at (-11.2, 3.7) [leafNode] {\textbf{Carta Magna inglesa (1215):}\\Juicio legal de sus iguales, debido proceso e interdicci\'on de arresto arbitrario \citep{parlamentoCarta1215ADH}.};
\node (lHist3) at (-11.2, 2.2) [leafNode] {\textbf{Tradici\'on brit\'anica (s. XVII):}\\Petition of Right (1628), Habeas Corpus Act (1679) y Bill of Rights (1689) \citep{parlamentoBill1689ADH}.};

% Rama 2: Corrientes Filosoficas y Teoricas (Arriba Derecha)
\node (bTeor) at (6.2, 3.7) [branchTeorNode] {2. CORRIENTES FILOS\'OFICAS\\Y TE\'ORICAS (Fundamentaci\'on)};
\node (lTeor1) at (11.2, 5.2) [leafNode] {\textbf{Iusnaturalismo Racionalista:}\\Locke y Grocio; derechos naturales previos y superiores al Estado (vida, libertad, propiedad) \citep{marcano2018derechos}.};
\node (lTeor2) at (11.2, 3.7) [leafNode] {\textbf{Contractualismo y Contrapesos:}\\Montesquieu y Rousseau; soberan\'ia popular, voluntad general y divisi\'on org\'anica de poderes.};
\node (lTeor3) at (11.2, 2.2) [leafNode] {\textbf{Garantismo y Estado Social:}\\Ferrajoli (garant\'ias primarias) y cartas sociales pioneras: Quer\'etaro (1917) y Weimar (1919) \citep{ferrajoli2008paradigma}.};

% Rama 3: Documentos y Revoluciones Liberales (Abajo Izquierda)
\node (bDoc) at (-6.2, -2.1) [branchDocNode] {3. REVOLUCIONES\\LIBERALES (Positivaci\'on)};
\node (lDoc1) at (-11.2, -0.6) [leafNode] {\textbf{Independencia EE.UU. (1776):}\\Declaraci\'on de Virginia; derechos inalienables a la vida, libertad y felicidad \citep{congresoVirginia1776ADH}.};
\node (lDoc2) at (-11.2, -2.1) [leafNode] {\textbf{Revoluci\'on Francesa (1789):}\\Declaraci\'on del Hombre y del Ciudadano; igualdad jur\'idica, propiedad y soberan\'ia \citep{declaracionFrancia1789ADH}.};
\node (lDoc3) at (-11.2, -3.6) [leafNode] {\textbf{Constituci\'on de C\'adiz (1812):}\\Soberan\'ia nacional, libertades civiles y l\'imite absolutista en el espacio hispanoamericano \citep{arteaga2016derecho}.};

% Rama 4: Internacionalizacion Post-Guerra (Abajo Derecha)
\node (bInt) at (6.2, -2.1) [branchIntNode] {4. INTERNACIONALIZACI\'ON\\POST-GUERRA (Universalizaci\'on)};
\node (lInt1) at (11.2, -0.6) [leafNode] {\textbf{Carta de la ONU (1945):}\\La paz mundial ligada indisolublemente a la tutela de derechos humanos \citep{onuCarta1945ADH}.};
\node (lInt2) at (11.2, -2.1) [leafNode] {\textbf{DUDH (1948):}\\Declaraci\'on Universal; cat\'alogo \'etico global de 30 art\'iculos indivisibles \citep{onuDeclaracion1948ADH}.};
\node (lInt3) at (11.2, -3.6) [leafNode] {\textbf{Tratados y Sistema Regional:}\\Pactos ONU 1966 (PIDCP/PIDESC) y Convenci\'on Americana (Pacto de San Jos\'e, 1969) \citep{oeaPacto1969ADH}.};

% Rama 5: Reconocimiento en Mexico (Centro Abajo)
\node (bRecep) at (0, -3.1) [branchRecepNode] {5. RECONOCIMIENTO EN M\'EXICO\\(Bloque de Constitucionalidad)};
\node (lRecep1) at (-4.7, -4.9) [leafNodeWide] {\textbf{Reforma Constitucional 2011:}\\Art\'iculo 1$^\circ$ CPEUM; personas titulares de derechos de fuente nacional e internacional \citep{alvarezIcaza2009ADH}.};
\node (lRecep2) at (4.7, -4.9) [leafNodeWide] {\textbf{Principios Rectores y Control Difuso:}\\Principio pro persona, interpretaci\'on conforme y par\'ametro de regularidad vinculante \citep{scjnParametro2014ADH,medellin2013principio}.};

% Conexiones centro a ramas
\draw [connMain, draw=branchHist] (core) to [bend left=12] (bHist);
\draw [connMain, draw=branchTeor] (core) to [bend right=12] (bTeor);
\draw [connMain, draw=branchDoc] (core) to [bend right=12] (bDoc);
\draw [connMain, draw=branchInt] (core) to [bend left=12] (bInt);
\draw [connMain, draw=branchRecep] (core) -- (bRecep);

% Conexiones ramas a hojas
\draw [connLeaf, draw=branchHist] (bHist) -- (lHist1);
\draw [connLeaf, draw=branchHist] (bHist) -- (lHist2);
\draw [connLeaf, draw=branchHist] (bHist) -- (lHist3);

\draw [connLeaf, draw=branchTeor] (bTeor) -- (lTeor1);
\draw [connLeaf, draw=branchTeor] (bTeor) -- (lTeor2);
\draw [connLeaf, draw=branchTeor] (bTeor) -- (lTeor3);

\draw [connLeaf, draw=branchDoc] (bDoc) -- (lDoc1);
\draw [connLeaf, draw=branchDoc] (bDoc) -- (lDoc2);
\draw [connLeaf, draw=branchDoc] (bDoc) -- (lDoc3);

\draw [connLeaf, draw=branchInt] (bInt) -- (lInt1);
\draw [connLeaf, draw=branchInt] (bInt) -- (lInt2);
\draw [connLeaf, draw=branchInt] (bInt) -- (lInt3);

\draw [connLeaf, draw=branchRecep] (bRecep) -- (lRecep1);
\draw [connLeaf, draw=branchRecep] (bRecep) -- (lRecep2);

\end{tikzpicture}"""

text = text[:t_start] + new_tikz + text[t_end:]

with open(tex_file, 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated LaTeX file successfully!")

# Compile with pdflatex twice
env = os.environ.copy()
env['PATH'] = 'C:/texlive/2026/bin/windows;' + env['PATH']
env['TEXINPUTS'] = f'{root}/aulaTEX/base/Plantilla-Informe//;{subj}//;;'

tex_name = 'reporte-antecedentes-de-los-derechos-humanos-Actividad-9'

print("Compiling pdflatex pass 1...")
res1 = subprocess.run(['pdflatex', '-interaction=nonstopmode', f'{tex_name}.tex'], env=env, cwd=str(subj), capture_output=True, text=True)
if res1.returncode != 0:
    print("Pass 1 error:")
    for l in res1.stdout.splitlines()[-30:]:
        print(l)
    exit(1)

print("Compiling pdflatex pass 2...")
res2 = subprocess.run(['pdflatex', '-interaction=nonstopmode', f'{tex_name}.tex'], env=env, cwd=str(subj), capture_output=True, text=True)
if res2.returncode != 0:
    print("Pass 2 error:")
    for l in res2.stdout.splitlines()[-30:]:
        print(l)
    exit(1)

pdf_file = subj / f'{tex_name}.pdf'
assert pdf_file.exists(), "PDF not found!"
doc = pymupdf.open(str(pdf_file))
print(f"Compilation SUCCESS! Total pages: {len(doc)}")

# Verify all pages for overlapping text blocks:
total_overlaps = 0
for idx, page in enumerate(doc):
    blocks = page.get_text('blocks')
    t_blocks = [b for b in blocks if b[4].strip()]
    n = len(t_blocks)
    page_overlaps = 0
    for i in range(n):
        for j in range(i+1, n):
            b1 = t_blocks[i]
            b2 = t_blocks[j]
            x_overlap = max(0, min(b1[2], b2[2]) - max(b1[0], b2[0]))
            y_overlap = max(0, min(b1[3], b2[3]) - max(b1[1], b2[1]))
            if x_overlap > 3 and y_overlap > 3:
                page_overlaps += 1
                total_overlaps += 1
                print(f"OVERLAP on Page {idx+1}:")
                print(f"   Block A ({b1[0]:.1f}, {b1[1]:.1f}, {b1[2]:.1f}, {b1[3]:.1f}): {b1[4].strip()[:40]!r}")
                print(f"   Block B ({b2[0]:.1f}, {b2[1]:.1f}, {b2[2]:.1f}, {b2[3]:.1f}): {b2[4].strip()[:40]!r}")
    if page_overlaps == 0:
        print(f"Page {idx+1} ({page.rect}, rot={page.rotation}): 0 overlaps (perfect!)")

print(f"\nTOTAL DOCUMENT OVERLAPS: {total_overlaps}")

# Check footers specifically
print("\n--- AUDIT OF FOOTERS ACROSS PORTRAIT PAGES ---")
for idx, page in enumerate(doc):
    if page.rotation == 0:
        footers = [b for b in page.get_text('blocks') if b[1] > page.rect.height - 70 and b[4].strip()]
        txt = " | ".join(f.strip() for b in footers for f in b[4].splitlines() if f.strip())
        print(f"Page {idx+1} footer: {txt}")

# Check landscape page bounds specifically
p_land = doc[5]
print("\n--- AUDIT OF LANDSCAPE PAGE 6 BOUNDS ---")
print(f"Landscape page rect: {p_land.rect}, rot: {p_land.rotation}")
land_blocks = [b for b in p_land.get_text('blocks') if b[4].strip()]
min_x = min(b[0] for b in land_blocks)
max_x = max(b[2] for b in land_blocks)
min_y = min(b[1] for b in land_blocks)
max_y = max(b[3] for b in land_blocks)
print(f"Landscape text extent: x in [{min_x:.1f}, {max_x:.1f}] (page width={p_land.rect.width}), y in [{min_y:.1f}, {max_y:.1f}] (page height={p_land.rect.height})")

# Copy to deliverable folder
entregas_dir = subj / 'entregas-antecedentes-de-los-derechos-humanos'
deliv = entregas_dir / 'Actividad-7-Mapa-mental-Martin-Jonathan-de-la-Cruz.pdf'
shutil.copy2(str(pdf_file), str(deliv))

with open(pdf_file, 'rb') as f:
    h = hashlib.sha256(f.read()).hexdigest()

print(f"SHA-256: {h}")
print(f"Deliverable updated: {deliv.name}")
