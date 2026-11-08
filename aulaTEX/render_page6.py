import pymupdf

pdf_path = "UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde/entregas-antecedentes-de-los-derechos-humanos/Actividad-7-Mapa-mental-Martin-Jonathan-de-la-Cruz.pdf"
doc = pymupdf.open(pdf_path)
p6 = doc[5]

# Render to PNG at 200 dpi
pix = p6.get_pixmap(dpi=200)
out_png = ".aulatex-temp/page6_radial_inspected.png"
pix.save(out_png)
print(f"Rendered Page 6 to {out_png}: width={pix.width}, height={pix.height}")

