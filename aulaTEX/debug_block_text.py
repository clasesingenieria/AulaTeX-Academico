import pymupdf

doc = pymupdf.open("UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde/reporte-antecedentes-de-los-derechos-humanos-Actividad-9.pdf")
p6 = doc[5]
blocks = p6.get_text("blocks")
for i, b in enumerate(blocks):
    if "1919" in b[4] or "ce Estados Unidos" in b[4] or "rechos humanos" in b[4]:
        print(f"B{i}: bbox={b[:4]}")
        print("   TEXT:", repr(b[4]))

