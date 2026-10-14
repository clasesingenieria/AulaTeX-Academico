import os
import subprocess
import numpy as np
import matplotlib.pyplot as plt
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

# Ensure directories exist
inter_dir = "/working_dir/c_c2d643968a323a94/artifacts/file_generation/ttl=63d/intermediate"
out_dir = "/working_dir/c_c2d643968a323a94/artifacts/file_generation/ttl=63d/output"
os.makedirs(inter_dir, exist_ok=True)
os.makedirs(out_dir, exist_ok=True)

# 1. Mathematical Verification via NumPy
A_dec = np.array([
    [0.12, 0.20, 0.15],
    [0.24, 0.10, 0.05],
    [0.12, 0.10, 0.30]
])
b_dec = np.array([99.0, 83.0, 84.0])
x_sol = np.linalg.solve(A_dec, b_dec)
A_int = np.array([
    [12, 20, 15],
    [24, 10, 5],
    [12, 10, 30]
], dtype=float)
b_int = np.array([9900.0, 8300.0, 8400.0])
det_A = round(np.linalg.det(A_int))
print(f"Solution x: {x_sol}, Det(A_int): {det_A}")
assert np.allclose(x_sol, [200.0, 300.0, 100.0])
assert det_A == -8400

# 2. Generate High-Resolution Matplotlib Chart
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#CBD5E1'
plt.rcParams['axes.linewidth'] = 0.8

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.4), dpi=300)

# Subplot 1: Cantidad de fertilizante requerido (kg/ha)
formulas = ['Fórmula A\n(12-24-12)\nArrancador', 'Fórmula B\n(20-10-10)\nDesarrollo', 'Fórmula C\n(15-05-30)\nLlenado']
cantidades = [200, 300, 100]
colores_f = ['#1B4332', '#2D6A4F', '#52B788']

bars1 = ax1.bar(formulas, cantidades, color=colores_f, width=0.52, edgecolor='none')
ax1.set_title('Dosis Óptima por Fertilizante Comercial\n(Solución del Sistema 3×3)', fontsize=11, fontweight='bold', color='#1B4332', pad=12)
ax1.set_ylabel('Cantidad requerida (kg/ha)', fontsize=9.5, color='#1F2937')
ax1.set_ylim(0, 360)
ax1.grid(axis='y', linestyle='--', alpha=0.4, color='#94A3B8')
ax1.set_axisbelow(True)

for bar in bars1:
    yval = bar.get_height()
    bultos = int(yval // 50)
    ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 8, f'{int(yval)} kg/ha\n({bultos} bultos)', ha='center', va='bottom', fontsize=9, fontweight='bold', color='#1F2937')

# Subplot 2: Aporte apilado de N, P2O5, K2O (kg/ha)
nutrientes = ['Nitrógeno\n(N)', 'Fósforo\n(P₂O₅)', 'Potasio\n(K₂O)']
aporte_A = np.array([24, 48, 24])
aporte_B = np.array([60, 30, 30])
aporte_C = np.array([15, 5, 30])

x_pos = np.arange(len(nutrientes))
w = 0.50
p1 = ax2.bar(x_pos, aporte_A, w, label='Fórmula A (12-24-12)', color='#1B4332')
p2 = ax2.bar(x_pos, aporte_B, w, bottom=aporte_A, label='Fórmula B (20-10-10)', color='#2D6A4F')
p3 = ax2.bar(x_pos, aporte_C, w, bottom=aporte_A + aporte_B, label='Fórmula C (15-05-30)', color='#52B788')

ax2.set_title('Aporte Nutricional Exacto por Macronutriente\n(Cumplimiento 100% de la Meta Agronómica)', fontsize=11, fontweight='bold', color='#1B4332', pad=12)
ax2.set_ylabel('Aporte neto de nutriente (kg/ha)', fontsize=9.5, color='#1F2937')
ax2.set_xticks(x_pos)
ax2.set_xticklabels(nutrientes, fontsize=9.5)
ax2.set_ylim(0, 118)
ax2.grid(axis='y', linestyle='--', alpha=0.4, color='#94A3B8')
ax2.set_axisbelow(True)
ax2.legend(loc='upper right', frameon=True, facecolor='#F8FAFC', edgecolor='#CBD5E1', fontsize=8.5)

totales = aporte_A + aporte_B + aporte_C
for i, total in enumerate(totales):
    ax2.text(x_pos[i], total + 3, f'Meta: {total} kg/ha', ha='center', va='bottom', fontsize=9, fontweight='bold', color='#1B4332')
    # internal labels
    ax2.text(x_pos[i], aporte_A[i]/2, f'{aporte_A[i]}', ha='center', va='center', fontsize=8, color='white', fontweight='bold')
    ax2.text(x_pos[i], aporte_A[i] + aporte_B[i]/2, f'{aporte_B[i]}', ha='center', va='center', fontsize=8, color='white', fontweight='bold')
    if aporte_C[i] >= 10:
        ax2.text(x_pos[i], aporte_A[i] + aporte_B[i] + aporte_C[i]/2, f'{aporte_C[i]}', ha='center', va='center', fontsize=8, color='white', fontweight='bold')

plt.tight_layout(pad=1.8)
chart_path = os.path.join(inter_dir, "balance_nutricional_npk.png")
plt.savefig(chart_path, dpi=300, bbox_inches='tight')
plt.close()
print(f"Chart saved to: {chart_path}")
