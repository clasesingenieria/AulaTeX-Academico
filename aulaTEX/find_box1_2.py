import pymupdf

pdf_path = "UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde/entregas-antecedentes-de-los-derechos-humanos/Actividad-7-Mapa-mental-Martin-Jonathan-de-la-Cruz.pdf"
doc = pymupdf.open(pdf_path)
p6 = doc[5]
blocks = p6.get_text("blocks")
drawings = p6.get_drawings()
rect_drawings = [d["rect"] for d in drawings if d["rect"].width > 50 and d["rect"].height > 15]

unique_boxes = []
for r in rect_drawings:
    is_dup = False
    for u in unique_boxes:
        if abs(r.x0 - u.x0) < 5 and abs(r.y0 - u.y0) < 5 and abs(r.width - u.width) < 5:
            is_dup = True
            break
    if not is_dup:
        unique_boxes.append(r)

for i in (1, 2):
    r = unique_boxes[i]
    txt = " ".join([b[4].strip().replace("\n", " ") for b in blocks if pymupdf.Rect(b[:4]).intersects(r)])
    print(f"Box {i}: rect={r} -> {repr(txt[:60])}")

