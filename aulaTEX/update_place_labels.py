from pathlib import Path

opt_path = Path("aulaTEX/optimize_mapa_layout.py")
text = opt_path.read_text(encoding="utf-8")

old_place = """def place_labels(block: str, nodes) -> str:
    r\"\"\"HEURÍSTICA EFECTIVA anti-empalme de etiquetas: para cada \\draw ... node[mclabel]{txt},
    prueba varias posiciones (pos) a lo largo de la arista Y desplazamientos perpendiculares,
    elige la que MENOS solapa con las cajas de TODOS los nodos y emite
    node[mclabel, pos=P, xshift=..pt, yshift=..pt]. Así la posición real en TikZ coincide con
    una zona libre (no queda 'comida' sobre un nodo).\"\"\"
    node_boxes = [bbox(n) for n in nodes.values() if not n.is_label]

    positions = [0.5, 0.44, 0.56, 0.38, 0.62, 0.32, 0.68, 0.26, 0.74, 0.20, 0.80, 0.15, 0.85]
    # desplazamientos perpendiculares (cm) a evaluar (mayores para sacar la etiqueta del nodo)
    perp_offsets = [0.0, 0.3, -0.3, 0.5, -0.5, 0.75, -0.75, 1.05, -1.05, 1.4, -1.4]

    def best_for_edge(na, nb, text):
        if na not in nodes or nb not in nodes:
            return None
        ax, ay = nodes[na].x, nodes[na].y
        bx, by = nodes[nb].x, nodes[nb].y
        dx, dy = bx - ax, by - ay
        mag = math.hypot(dx, dy) or 1e-6
        # perpendicular unitaria
        px, py = -dy / mag, dx / mag
        best = None
        for pos in positions:
            lx = ax + dx * pos
            ly = ay + dy * pos
            for off in perp_offsets:
                cx = lx + px * off
                cy = ly + py * off
                lb = _label_box_at(cx, cy, text)
                area = sum(_box_overlap_area(lb, nb_) for nb_ in node_boxes)
                # penalizar alejarse mucho del midpoint y del centro de la arista
                penalty = abs(pos - 0.5) * 0.15 + abs(off) * 0.05
                score = area + penalty
                if best is None or score < best[0]:
                    best = (score, pos, off, px, py)
        return best"""

new_place = """def place_labels(block: str, nodes) -> str:
    r\"\"\"HEURÍSTICA EFECTIVA anti-empalme de etiquetas: para cada \\draw ... node[mclabel]{txt},
    prueba varias posiciones (pos) a lo largo de la arista Y desplazamientos perpendiculares,
    elige la que MENOS solapa con las cajas de TODOS los nodos Y con otras etiquetas ya colocadas,
    y emite node[mclabel, pos=P, xshift=..pt, yshift=..pt].\"\"\"
    node_boxes = [bbox(n) for n in nodes.values() if not n.is_label]
    placed_labels: list[tuple[float, float, float, float]] = []

    positions = [0.5, 0.44, 0.56, 0.38, 0.62, 0.32, 0.68, 0.26, 0.74, 0.20, 0.80, 0.15, 0.85]
    # desplazamientos perpendiculares (cm) a evaluar (mayores para sacar la etiqueta del nodo)
    perp_offsets = [0.0, 0.3, -0.3, 0.5, -0.5, 0.75, -0.75, 1.05, -1.05, 1.4, -1.4]

    def best_for_edge(na, nb, text):
        if na not in nodes or nb not in nodes:
            return None
        ax, ay = nodes[na].x, nodes[na].y
        bx, by = nodes[nb].x, nodes[nb].y
        dx, dy = bx - ax, by - ay
        mag = math.hypot(dx, dy) or 1e-6
        # perpendicular unitaria
        px, py = -dy / mag, dx / mag
        best = None
        for pos in positions:
            lx = ax + dx * pos
            ly = ay + dy * pos
            for off in perp_offsets:
                cx = lx + px * off
                cy = ly + py * off
                lb = _label_box_at(cx, cy, text)
                area = sum(_box_overlap_area(lb, nb_) for nb_ in node_boxes)
                # Penalizar también solapamiento con etiquetas ya colocadas
                area += sum(_box_overlap_area(lb, pl) * 4.0 for pl in placed_labels)
                # penalizar alejarse mucho del midpoint y del centro de la arista
                penalty = abs(pos - 0.5) * 0.15 + abs(off) * 0.05
                score = area + penalty
                if best is None or score < best[0]:
                    best = (score, pos, off, px, py, lb, cx, cy)
        if best is not None:
            placed_labels.append(best[5])
            # actualizar pseudo-nodo si existe
            for n in nodes.values():
                if n.is_label and n.a == na and n.b == nb and n.text.strip() == text.strip():
                    n.x = best[6]
                    n.y = best[7]
                    break
        return best"""

text_norm = text.replace("\r\n", "\n")
old_place_norm = old_place.replace("\r\n", "\n")
assert old_place_norm in text_norm, "old_place not found!"
text_norm = text_norm.replace(old_place_norm, new_place)

opt_path.write_text(text_norm, encoding="utf-8")
print("Successfully added label-label anti-overlap to place_labels!")

