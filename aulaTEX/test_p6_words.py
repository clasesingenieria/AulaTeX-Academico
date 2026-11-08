import pymupdf

doc = pymupdf.open("UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde/reporte-antecedentes-de-los-derechos-humanos-Actividad-9.pdf")
p6 = doc[5]
words = p6.get_text("words")
print(f"Total words on Page 6: {len(words)}")

word_overlaps = []
for i in range(len(words)):
    for j in range(i + 1, len(words)):
        w1, w2 = words[i], words[j]
        b1, b2 = w1[:4], w2[:4]
        ix1, iy1 = max(b1[0], b2[0]), max(b1[1], b2[1])
        ix2, iy2 = min(b1[2], b2[2]), min(b1[3], b2[3])
        if ix2 > ix1 + 1 and iy2 > iy1 + 1:
            word_overlaps.append((w1[4], w2[4], (ix2-ix1)*(iy2-iy1)))

print(f"WORD OVERLAPS on Page 6: {len(word_overlaps)}")
for w1, w2, area in word_overlaps:
    print(f"   [{w1}] vs [{w2}] (area={area:.1f})")

