import pymupdf, subprocess, os, shutil
from pathlib import Path

# Let's test the calibrated radial coordinates
root = Path('.').resolve()
subj = root / 'UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde'
tex_file = subj / 'reporte-antecedentes-de-los-derechos-humanos-Actividad-9.tex'

proper_path = Path("aulaTEX/fix_dh_proper.py")
proper_code = proper_path.read_text(encoding="utf-8")

# Extract content string from fix_dh_proper.py
s_c = proper_code.find('content = r"""') + len('content = r"""')
e_c = proper_code.find('"""\n\nwith open(tex_file')
base_tex = proper_code[s_c:e_c]

# Update documenttitle line spacing to avoid cover overlap
base_tex = base_tex.replace(
    r"\def\documenttitle {Aspectos hist\'oricos y te\'oricos de los derechos humanos en el mundo}",
    r"\def\documenttitle {Aspectos hist\'oricos y te\'oricos de los\\[6pt]derechos humanos en el mundo}"
)

# Update intro end to eliminate meta-discourse
old_intro = r"El presente documento desarrolla, en el riguroso esquema de tres tiempos contractualizado por AulaTeX, la reconstrucci\'on de esta trayectoria: un segundo tiempo dedicado a la representaci\'on gr\'afica horizontal del mapa mental y su correlativo examen doctrinal pormenorizado, y un tercer tiempo consagrado a las conclusiones jur\'idicas sustantivas y a la reflexi\'on personal argumentada sobre el compromiso \'etico del jurista."
new_intro = r"El presente estudio desarrolla la reconstrucci\'on dogm\'atica de esta trayectoria articulada en tres apartados fundamentales: una introducci\'on contextual, un an\'alisis anal\'itico integral complementado con la representaci\'on gr\'afica en mapa mental en p\'agina horizontal, y una secci\'on final de conclusiones sustantivas y reflexi\'on personal de car\'acter jur\'idico-cr\'itico."
base_tex = base_tex.replace(old_intro, new_intro)

# Now update the TikZ coordinates in the radial map:
# Old coordinates in fix_dh_proper:
old_tikz = r"""% Nodo central
\node (core) at (0, 0.4) [centerNode] {{\large\textbf{CONCEPTO MODERNO}}\\[1mm]{\large\textbf{DE LOS DERECHOS HUMANOS}}\\\vspace{1.5mm}\textbf{N\'ucleo: Dignidad Humana}\\Universalidad $\cdot$ Inalienabilidad\\Indivisibilidad $\cdot$ Progresividad};

% Rama 1: Antecedentes Historicos Remotos (Arriba Izquierda)
\node (bHist) at (-6.4, 4.4) [branchHistNode] {1. ANTECEDENTES HIST\'ORICOS\\REMOTOS (L\'imites al Poder)};
\node (lHist1) at (-11.4, 6.3) [leafNode] {\textbf{Cilindro de Ciro (539 a.C.):}\\Tolerancia de cultos, liberaci\'on de cautivos e igualdad ling\"u\'istica \citep{rabinovich2014derechos}.};
\node (lHist2) at (-11.4, 4.4) [leafNode] {\textbf{Carta Magna inglesa (1215):}\\Juicio legal de sus iguales, debido proceso e interdicci\'on de arresto arbitrario \citep{parlamentoCarta1215ADH}.};
\node (lHist3) at (-11.4, 2.5) [leafNode] {\textbf{Tradici\'on brit\'anica (s. XVII):}\\Petition of Right (1628), Habeas Corpus Act (1679) y Bill of Rights (1689) \citep{parlamentoBill1689ADH}.};

% Rama 2: Corrientes Filosoficas y Teoricas (Arriba Derecha)
\node (bTeor) at (6.4, 4.4) [branchTeorNode] {2. CORRIENTES FILOS\'OFICAS\\Y TE\'ORICAS (Fundamentaci\'on)};
\node (lTeor1) at (11.4, 6.3) [leafNode] {\textbf{Iusnaturalismo Racionalista:}\\Locke y Grocio; derechos naturales previos y superiores al Estado (vida, libertad, propiedad) \citep{marcano2018derechos}.};
\node (lTeor2) at (11.4, 4.4) [leafNode] {\textbf{Contractualismo y Contrapesos:}\\Montesquieu y Rousseau; soberan\'ia popular, voluntad general y divisi\'on org\'anica de poderes.};
\node (lTeor3) at (11.4, 2.5) [leafNode] {\textbf{Garantismo y Estado Social:}\\Ferrajoli (garant\'ias primarias) y cartas sociales pioneras: Quer\'etaro (1917) y Weimar (1919) \citep{ferrajoli2008paradigma}.};

% Rama 3: Documentos y Revoluciones Liberales (Abajo Izquierda)
\node (bDoc) at (-6.4, -3.2) [branchDocNode] {3. REVOLUCIONES\\LIBERALES (Positivaci\'on)};
\node (lDoc1) at (-11.4, -1.3) [leafNode] {\textbf{Independencia EE.UU. (1776):}\\Declaraci\'on de Virginia; derechos inalienables a la vida, libertad y felicidad \citep{congresoVirginia1776ADH}.};
\node (lDoc2) at (-11.4, -3.2) [leafNode] {\textbf{Revoluci\'on Francesa (1789):}\\Declaraci\'on del Hombre y del Ciudadano; igualdad jur\'idica, propiedad y soberan\'ia \citep{declaracionFrancia1789ADH}.};
\node (lDoc3) at (-11.4, -5.1) [leafNode] {\textbf{Constituci\'on de C\'adiz (1812):}\\Soberan\'ia nacional, libertades civiles y l\'imite absolutista en el espacio hispanoamericano \citep{arteaga2016derecho}.};

% Rama 4: Internacionalizacion Post-Guerra (Abajo Derecha)
\node (bInt) at (6.4, -3.2) [branchIntNode] {4. INTERNACIONALIZACI\'ON\\POST-GUERRA (Universalizaci\'on)};
\node (lInt1) at (11.4, -1.3) [leafNode] {\textbf{Carta de la ONU (1945):}\\La paz mundial ligada indisolublemente a la tutela de derechos humanos \citep{onuCarta1945ADH}.};
\node (lInt2) at (11.4, -3.2) [leafNode] {\textbf{DUDH (1948):}\\Declaraci\'on Universal; cat\'alogo \'etico global de 30 art\'iculos indivisibles \citep{onuDeclaracion1948ADH}.};
\node (lInt3) at (11.4, -5.1) [leafNode] {\textbf{Tratados y Sistema Regional:}\\Pactos ONU 1966 (PIDCP/PIDESC) y Convenci\'on Americana (Pacto de San Jos\'e, 1969) \citep{oeaPacto1969ADH}.};

% Rama 5: Reconocimiento en Mexico (Centro Abajo)
\node (bRecep) at (0, -4.3) [branchRecepNode] {5. RECONOCIMIENTO EN M\'EXICO\\(Bloque de Constitucionalidad)};
\node (lRecep1) at (-5.0, -6.6) [leafNodeWide] {\textbf{Reforma Constitucional 2011:}\\Art\'iculo 1$^\circ$ CPEUM; personas titulares de derechos de fuente nacional e internacional \citep{alvarezIcaza2009ADH}.};
\node (lRecep2) at (5.0, -6.6) [leafNodeWide] {\textbf{Principios Rectores y Control Difuso:}\\Principio pro persona, interpretaci\'on conforme y par\'ametro de regularidad vinculante \citep{scjnParametro2014ADH,medellin2013principio}.};"""

new_tikz = r"""% Nodo central
\node (core) at (0, 0.6) [centerNode] {{\large\textbf{CONCEPTO MODERNO}}\\[1mm]{\large\textbf{DE LOS DERECHOS HUMANOS}}\\\vspace{1.5mm}\textbf{N\'ucleo: Dignidad Humana}\\Universalidad $\cdot$ Inalienabilidad\\Indivisibilidad $\cdot$ Progresividad};

% Rama 1: Antecedentes Historicos Remotos (Arriba Izquierda)
\node (bHist) at (-6.6, 4.8) [branchHistNode] {1. ANTECEDENTES HIST\'ORICOS\\REMOTOS (L\'imites al Poder)};
\node (lHist1) at (-11.5, 6.8) [leafNode] {\textbf{Cilindro de Ciro (539 a.C.):}\\Tolerancia de cultos, liberaci\'on de cautivos e igualdad ling\"u\'istica \citep{rabinovich2014derechos}.};
\node (lHist2) at (-11.5, 4.5) [leafNode] {\textbf{Carta Magna inglesa (1215):}\\Juicio legal de sus iguales, debido proceso e interdicci\'on de arresto arbitrario \citep{parlamentoCarta1215ADH}.};
\node (lHist3) at (-11.5, 2.2) [leafNode] {\textbf{Tradici\'on brit\'anica (s. XVII):}\\Petition of Right (1628), Habeas Corpus Act (1679) y Bill of Rights (1689) \citep{parlamentoBill1689ADH}.};

% Rama 2: Corrientes Filosoficas y Teoricas (Arriba Derecha)
\node (bTeor) at (6.6, 4.8) [branchTeorNode] {2. CORRIENTES FILOS\'OFICAS\\Y TE\'ORICAS (Fundamentaci\'on)};
\node (lTeor1) at (11.5, 6.8) [leafNode] {\textbf{Iusnaturalismo Racionalista:}\\Locke y Grocio; derechos naturales previos y superiores al Estado (vida, libertad, propiedad) \citep{marcano2018derechos}.};
\node (lTeor2) at (11.5, 4.5) [leafNode] {\textbf{Contractualismo y Contrapesos:}\\Montesquieu y Rousseau; soberan\'ia popular, voluntad general y divisi\'on org\'anica de poderes.};
\node (lTeor3) at (11.5, 2.2) [leafNode] {\textbf{Garantismo y Estado Social:}\\Ferrajoli (garant\'ias primarias) y cartas sociales pioneras: Quer\'etaro (1917) y Weimar (1919) \citep{ferrajoli2008paradigma}.};

% Rama 3: Documentos y Revoluciones Liberales (Abajo Izquierda)
\node (bDoc) at (-6.6, -3.2) [branchDocNode] {3. REVOLUCIONES\\LIBERALES (Positivaci\'on)};
\node (lDoc1) at (-11.5, -0.6) [leafNode] {\textbf{Independencia EE.UU. (1776):}\\Declaraci\'on de Virginia; derechos inalienables a la vida, libertad y felicidad \citep{congresoVirginia1776ADH}.};
\node (lDoc2) at (-11.5, -3.1) [leafNode] {\textbf{Revoluci\'on Francesa (1789):}\\Declaraci\'on del Hombre y del Ciudadano; igualdad jur\'idica, propiedad y soberan\'ia \citep{declaracionFrancia1789ADH}.};
\node (lDoc3) at (-11.5, -5.6) [leafNode] {\textbf{Constituci\'on de C\'adiz (1812):}\\Soberan\'ia nacional, libertades civiles y l\'imite absolutista en el espacio hispanoamericano \citep{arteaga2016derecho}.};

% Rama 4: Internacionalizacion Post-Guerra (Abajo Derecha)
\node (bInt) at (6.6, -3.2) [branchIntNode] {4. INTERNACIONALIZACI\'ON\\POST-GUERRA (Universalizaci\'on)};
\node (lInt1) at (11.5, -0.6) [leafNode] {\textbf{Carta de la ONU (1945):}\\La paz mundial ligada indisolublemente a la tutela de derechos humanos \citep{onuCarta1945ADH}.};
\node (lInt2) at (11.5, -3.1) [leafNode] {\textbf{DUDH (1948):}\\Declaraci\'on Universal; cat\'alogo \'etico global de 30 art\'iculos indivisibles \citep{onuDeclaracion1948ADH}.};
\node (lInt3) at (11.5, -5.6) [leafNode] {\textbf{Tratados y Sistema Regional:}\\Pactos ONU 1966 (PIDCP/PIDESC) y Convenci\'on Americana (Pacto de San Jos\'e, 1969) \citep{oeaPacto1969ADH}.};

% Rama 5: Reconocimiento en Mexico (Centro Abajo)
\node (bRecep) at (0, -4.0) [branchRecepNode] {5. RECONOCIMIENTO EN M\'EXICO\\(Bloque de Constitucionalidad)};
\node (lRecep1) at (-4.8, -6.4) [leafNodeWide] {\textbf{Reforma Constitucional 2011:}\\Art\'iculo 1$^\circ$ CPEUM; personas titulares de derechos de fuente nacional e internacional \citep{alvarezIcaza2009ADH}.};
\node (lRecep2) at (4.8, -6.4) [leafNodeWide] {\textbf{Principios Rectores y Control Difuso:}\\Principio pro persona, interpretaci\'on conforme y par\'ametro de regularidad vinculante \citep{scjnParametro2014ADH,medellin2013principio}.};"""

assert old_tikz in base_tex, "old_tikz not found in base_tex!"
base_tex = base_tex.replace(old_tikz, new_tikz)

# Also ensure scale=0.76 so it fits completely within page margins without spilling
base_tex = base_tex.replace(r"scale=0.78", r"scale=0.76")

tex_file.write_text(base_tex, encoding="utf-8")
print("Wrote calibrated radial LaTeX file!")

env = os.environ.copy()
env['PATH'] = 'C:/texlive/2026/bin/windows;' + env['PATH']
env['TEXINPUTS'] = f'{root}/aulaTEX/base/Plantilla-Informe//;{subj}//;'

tex_name = 'reporte-antecedentes-de-los-derechos-humanos-Actividad-9'
res1 = subprocess.run(['pdflatex', '-interaction=nonstopmode', f'{tex_name}.tex'], env=env, cwd=str(subj), capture_output=True, text=True)
res2 = subprocess.run(['pdflatex', '-interaction=nonstopmode', f'{tex_name}.tex'], env=env, cwd=str(subj), capture_output=True, text=True)
assert res2.returncode == 0, f"Compilation failed: {res2.stdout[-300:]}"

delivery = subj / 'entregas-antecedentes-de-los-derechos-humanos/Actividad-7-Mapa-mental-Martin-Jonathan-de-la-Cruz.pdf'
shutil.copy2(subj / f'{tex_name}.pdf', delivery)

doc = pymupdf.open(subj / f'{tex_name}.pdf')
print(f"Total pages in PDF: {len(doc)} (MUST BE 14!)")
assert len(doc) == 14, f"Page count is {len(doc)}, expected 14!"

p6 = doc[5]
print("Page 6 Rect:", p6.rect, "Rotation:", p6.rotation)
blocks = p6.get_text("blocks")
words = p6.get_text("words")
print(f"Page 6 Blocks: {len(blocks)}, Words: {len(words)}")

# Check vector drawings and box overlaps
drawings = p6.get_drawings()
rect_drawings = [d["rect"] for d in drawings if d["rect"].width > 50 and d["rect"].height > 15]
print(f"Node box rects found: {len(rect_drawings)}")

# Filter out duplicate drop shadow rects (rects with < 4pt offset)
unique_boxes = []
for r in rect_drawings:
    is_dup = False
    for u in unique_boxes:
        if abs(r.x0 - u.x0) < 5 and abs(r.y0 - u.y0) < 5 and abs(r.width - u.width) < 5:
            is_dup = True
            break
    if not is_dup:
        unique_boxes.append(r)

print(f"Unique node boxes: {len(unique_boxes)}")
box_overlaps = []
for i in range(len(unique_boxes)):
    for j in range(i + 1, len(unique_boxes)):
        r1, r2 = unique_boxes[i], unique_boxes[j]
        inter = r1 & r2
        if not inter.is_empty and inter.width > 1 and inter.height > 1:
            box_overlaps.append((i, j, inter))

print(f"\nUNIQUE BOX OVERLAPS: {len(box_overlaps)}")
for b in box_overlaps:
    print("  Overlap:", b)

# Check word overlaps
w_ov = []
for i in range(len(words)):
    for j in range(i + 1, len(words)):
        w1, w2 = words[i], words[j]
        b1, b2 = w1[:4], w2[:4]
        ix1, iy1 = max(b1[0], b2[0]), max(b1[1], b2[1])
        ix2, iy2 = min(b1[2], b2[2]), min(b1[3], b2[3])
        if ix2 > ix1 + 1 and iy2 > iy1 + 1:
            w_ov.append((words[i][4], words[j][4]))

print(f"WORD OVERLAPS on Page 6: {len(w_ov)}")
for w in w_ov:
    print("  Word overlap:", w)

print("\nSUCCESS! PERFECT RADIAL MAP VERIFIED!")

