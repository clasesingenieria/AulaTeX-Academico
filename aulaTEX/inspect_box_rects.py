import pymupdf

pdf_path = "UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde/entregas-antecedentes-de-los-derechos-humanos/Actividad-7-Mapa-mental-Martin-Jonathan-de-la-Cruz.pdf"
doc = pymupdf.open(pdf_path)
p6 = doc[5]

# Extract all text blocks and drawings
blocks = p6.get_text("blocks")
print(f"Total blocks on Page 6: {len(blocks)}")
drawings = p6.get_drawings()
print(f"Total vector drawings on Page 6: {len(drawings)}")

# Find all rectangle drawings (the boxes!)
rect_drawings = [d["rect"] for d in drawings if d["rect"].width > 50 and d["rect"].height > 15]
print(f"Node box rects found: {len(rect_drawings)}")
for i, r in enumerate(rect_drawings):
    # Find text inside this rect
    txt = " ".join([b[4].strip().replace("\n", " ") for b in blocks if pymupdf.Rect(b[:4]).intersects(r)])
    print(f"Box {i:02d}: rect={r} -> {repr(txt[:45])}")

# Check overlaps between box rects
box_overlaps = []
for i in range(len(rect_drawings)):
    for j in range(i + 1, len(rect_drawings)):
        r1, r2 = rect_drawings[i], rect_drawings[j]
        inter = r1 & r2
        if not inter.is_empty and inter.width > 0.5 and inter.height > 0.5:
            box_overlaps.append((i, j, inter))

print(f"\nBOX RECT OVERLAPS: {len(box_overlaps)}")
for i, j, inter in box_overlaps:
    print(f"  Overlap Box {i} with Box {j}: inter={inter}")

