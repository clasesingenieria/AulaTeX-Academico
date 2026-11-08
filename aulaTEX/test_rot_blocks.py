import pymupdf

doc = pymupdf.open("UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde/reporte-antecedentes-de-los-derechos-humanos-Actividad-9.pdf")
p6 = doc[5]
print("Original rot:", p6.rotation)
# If rotation is 90, the page is rendered landscape.
# Let's check text blocks in the actual reading orientation:
# We can render the page to a pixmap or inspect words
blocks_raw = p6.get_text("blocks")
print("Raw blocks:", len(blocks_raw))

# Also check with rotation = 0:
p6.set_rotation(0)
blocks_rot0 = p6.get_text("blocks")
print("Blocks rot 0:", len(blocks_rot0))
overlaps_rot0 = []
for i in range(len(blocks_rot0)):
    for j in range(i + 1, len(blocks_rot0)):
        b1, b2 = blocks_rot0[i][:4], blocks_rot0[j][:4]
        ix1 = max(b1[0], b2[0]); iy1 = max(b1[1], b2[1])
        ix2 = min(b1[2], b2[2]); iy2 = min(b1[3], b2[3])
        if ix2 > ix1 + 2 and iy2 > iy1 + 2:
            t1 = blocks_rot0[i][4].strip().replace("\n", " ")[:25]
            t2 = blocks_rot0[j][4].strip().replace("\n", " ")[:25]
            overlaps_rot0.append((t1, t2, (ix2-ix1)*(iy2-iy1)))
print("Overlaps with rot 0:", len(overlaps_rot0))
for o in overlaps_rot0:
    print("  Overlap rot 0:", o[0], "vs", o[1], f"area={o[2]:.1f}")

