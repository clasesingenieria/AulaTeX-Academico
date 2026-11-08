import pymupdf

doc = pymupdf.open("UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde/reporte-antecedentes-de-los-derechos-humanos-Actividad-9.pdf")
p1 = doc[0]
blocks = p1.get_text("blocks")
for b in blocks:
    print(f"bbox: {b[:4]} -> {repr(b[4].strip()[:50])}")

