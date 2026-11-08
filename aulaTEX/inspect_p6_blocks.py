import pymupdf

doc = pymupdf.open("UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde/reporte-antecedentes-de-los-derechos-humanos-Actividad-9.pdf")
p6 = doc[5]
print("Page 6 Rect:", p6.rect, "Rotation:", p6.rotation)
blocks = p6.get_text("blocks")
print(f"Total blocks on Page 6: {len(blocks)}")
for i, b in enumerate(blocks):
    txt = b[4].strip().replace("\n", " ")
    print(f"B{i:02d} {b[:4]} -> {repr(txt[:60])}")

