import fitz

pdf_path = "UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde/reporte-antecedentes-de-los-derechos-humanos-Actividad-9.pdf"
doc = fitz.open(pdf_path)
print("Total pages:", len(doc))

for pno, page in enumerate(doc):
    blocks = page.get_text("blocks")
    overlaps = []
    for i in range(len(blocks)):
        for j in range(i + 1, len(blocks)):
            b1, b2 = blocks[i][:4], blocks[j][:4]
            ix1 = max(b1[0], b2[0])
            iy1 = max(b1[1], b2[1])
            ix2 = min(b1[2], b2[2])
            iy2 = min(b1[3], b2[3])
            if ix2 > ix1 + 1 and iy2 > iy1 + 1:
                t1 = blocks[i][4].strip().replace("\n", " ")[:35]
                t2 = blocks[j][4].strip().replace("\n", " ")[:35]
                overlaps.append((t1, t2, (ix2 - ix1) * (iy2 - iy1)))
    if overlaps:
        print(f"Page {pno+1}: {len(overlaps)} text block overlaps:")
        for t1, t2, area in overlaps:
            print(f"   [{t1}] vs [{t2}] (area={area:.1f})")
    else:
        print(f"Page {pno+1}: 0 overlaps")

