import pymupdf

doc = pymupdf.open("UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde/reporte-antecedentes-de-los-derechos-humanos-Actividad-9.pdf")
p6 = doc[5]
blocks = p6.get_text("blocks")
for b in blocks:
    if "fundament" in b[4] or "se gara" in b[4]:
        print(f"bbox: {b[:4]} -> {repr(b[4])}")

