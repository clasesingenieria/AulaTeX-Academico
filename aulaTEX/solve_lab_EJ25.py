from fractions import Fraction
from pathlib import Path

def fmt_entry(x):
    if isinstance(x, Fraction):
        if x.denominator == 1:
            return str(x.numerator)
        return '\\frac{%d}{%d}' % (x.numerator, x.denominator)
    return str(x)

def mat_repr(M):
    # join entries with & and rows with \\\\ for proper pmatrix formatting
    rows = [ ' & '.join(fmt_entry(x) for x in row) for row in M ]
    return '\\begin{pmatrix}' + ' \\\\ '.join(rows) + '\\end{pmatrix}'

def augment(A, b):
    return [row[:] + [b_i] for row, b_i in zip(A, b)]

def copy_mat(M):
    return [row[:] for row in M]

def row_swap(M, i, j):
    M[i], M[j] = M[j], M[i]

def row_mul(M, i, k):
    M[i] = [x * k for x in M[i]]

def row_add(M, target, src, k):
    M[target] = [t + k * s for t, s in zip(M[target], M[src])]

def gaussian_elimination_steps(Aug):
    M = copy_mat(Aug)
    m = len(M)
    n = len(M[0])
    steps = []
    # forward elimination with snapshots
    row = 0
    for col in range(n-1):
        # find pivot
        pivot = None
        for r in range(row, m):
            if M[r][col] != 0:
                pivot = r
                break
        if pivot is None:
            continue
        if pivot != row:
            row_swap(M, pivot, row)
            steps.append(("F_{%d} \\leftrightarrow F_{%d}" % (pivot+1, row+1), copy_mat(M)))
        # normalize pivot to 1
        pv = M[row][col]
        if pv != 1:
            k = Fraction(1,1)/pv
            row_mul(M, row, k)
            steps.append(("%sF_{%d}" % (fmt_entry(k), row+1), copy_mat(M)))
        # eliminate below
        for r in range(row+1, m):
            if M[r][col] != 0:
                factor = -M[r][col]
                row_add(M, r, row, factor)
                steps.append(("F_{%d} + (%s)F_{%d}" % (r+1, fmt_entry(factor), row+1), copy_mat(M)))
        row += 1
        if row >= m:
            break
    return steps, M

def gauss_jordan_steps(Aug):
    M = copy_mat(Aug)
    m = len(M)
    n = len(M[0])
    steps = []
    # full reduction with snapshots
    pivots = []
    r = 0
    for c in range(n-1):
        pivot = None
        for i in range(r, m):
            if M[i][c] != 0:
                pivot = i
                break
        if pivot is None:
            continue
        if pivot != r:
            row_swap(M, pivot, r)
            steps.append(("F_{%d} \\leftrightarrow F_{%d}" % (pivot+1, r+1), copy_mat(M)))
        pv = M[r][c]
        if pv != 1:
            k = Fraction(1,1)/pv
            row_mul(M, r, k)
            steps.append(("%sF_{%d}" % (fmt_entry(k), r+1), copy_mat(M)))
        for i in range(m):
            if i != r and M[i][c] != 0:
                factor = -M[i][c]
                row_add(M, i, r, factor)
                steps.append(("F_{%d} + (%s)F_{%d}" % (i+1, fmt_entry(factor), r+1), copy_mat(M)))
        pivots.append((r,c))
        r += 1
        if r>=m:
            break
    return steps, M


def det(matrix):
    # recursive determinant using Fractions
    n = len(matrix)
    if n == 1:
        return matrix[0][0]
    if n == 2:
        return matrix[0][0]*matrix[1][1] - matrix[0][1]*matrix[1][0]
    total = Fraction(0,1)
    for col in range(n):
        sub = [[matrix[r][c] for c in range(n) if c!=col] for r in range(1,n)]
        sign = Fraction(1 if col%2==0 else -1,1)
        total += sign * matrix[0][col] * det(sub)
    return total

def det_steps(matrix):
    # returns (latex_expr, value)
    n = len(matrix)
    if n == 1:
        return (fmt_entry(matrix[0][0]), matrix[0][0])
    if n == 2:
        a,b = matrix[0][0], matrix[0][1]
        c,d = matrix[1][0], matrix[1][1]
        expr = f"({fmt_entry(a)})({fmt_entry(d)}) - ({fmt_entry(b)})({fmt_entry(c)})"
        val = a*d - b*c
        return (expr, val)
    parts = []
    total = Fraction(0,1)
    for col in range(n):
        a = matrix[0][col]
        # build minor
        sub = [[matrix[r][c] for c in range(n) if c!=col] for r in range(1,n)]
        sign = 1 if col%2==0 else -1
        sub_expr, sub_val = det_steps(sub)
        part_expr = f"{fmt_entry(a)}\\cdot({sub_expr})"
        if sign==-1:
            parts.append("- "+part_expr)
            total -= a * sub_val
        else:
            parts.append(part_expr)
            total += a * sub_val
    expr = ' + '.join(parts).replace('+ -', '- ')
    return (expr, total)


def det_cofactor(matrix, name='A'):
    """Return (value, lines) where lines is a list of LaTeX lines explaining cofactor expansion."""
    n = len(matrix)
    if n == 1:
        val = matrix[0][0]
        return val, [f'\\[\\det({name}) = {fmt_entry(val)}\\]']
    if n == 2:
        a,b = matrix[0][0], matrix[0][1]
        c,d = matrix[1][0], matrix[1][1]
        val = a*d - b*c
        lines = []
        lines.append('\\[\\det(%s) = (%s)(%s) - (%s)(%s) = %s\\]' % (name, fmt_entry(a), fmt_entry(d), fmt_entry(b), fmt_entry(c), fmt_entry(val)))
        return val, lines
    total = Fraction(0,1)
    lines = []
    lines.append(f'Expansión por cofactores de $\\det({name})$ por la primera fila:')
    term_exprs = []
    for j in range(n):
        a = matrix[0][j]
        sign = Fraction(1 if j%2==0 else -1,1)
        # minor
        minor = [[matrix[r][c] for c in range(n) if c!=j] for r in range(1,n)]
        lines.append(f'Matriz menor $M_{{1,{j+1}}}$:')
        lines.append('\\[' + mat_repr(minor) + '\\]')
        # build a safe minor name based on root of current name to avoid double subscripts
        root = name.split('{')[0].rstrip('_')
        minor_name = f'{root}_{{1,{j+1}}}'
        minor_val, minor_lines = det_cofactor(minor, name=minor_name)
        # show minor determinant details
        lines.extend(minor_lines)
        # cofactor and term
        lines.append(f'Cofactor $C_{{1,{j+1}}} = (-1)^{{1+{j+1}}} = {fmt_entry(sign)}$')
        term = sign * a * minor_val
        lines.append(f'Término asociado: $ {fmt_entry(a)} \\cdot {fmt_entry(minor_val)} = {fmt_entry(term)} $')
        term_exprs.append(fmt_entry(term))
        total += term
    # sum
    lines.append('Suma de términos:')
    lines.append('\\[\\det(%s) = %s = %s\\]' % (name, ' + '.join(term_exprs).replace('+ -', '- '), fmt_entry(total)))
    return total, lines


def frac(x):
    if isinstance(x, Fraction):
        return x
    return Fraction(x,1)

systems = []
# I a)
A1 = [[-1,-5,4],[7,-3,5],[-4,-5,6]]
b1 = [21,0,29]
systems.append((A1,b1,'I.a'))
# I b)
A2 = [[5,-6,-7],[-1,-1,-4],[-1,2,6]]
b2 = [10,27,-31]
systems.append((A2,b2,'I.b'))
# I c)
A3 = [[-2,-2,1],[-3,-1,0],[-3,-3,1]]
b3 = [3,3,-1]
systems.append((A3,b3,'I.c'))
# I d) 4x4
A4 = [[-4,2,4,1],[4,-1,1,-4],[5,-5,-5,-3],[-2,-2,3,-5]]
b4 = [-6,19,6,3]
systems.append((A4,b4,'I.d'))
# II a)
A5 = [[-1,4,-2],[-3,5,0],[-6,-1,-7]]
b5 = [-23,-25,-63]
systems.append((A5,b5,'II.a'))
# II b) 4x4
A6 = [[3,4,-2,0],[-3,3,4,-1],[-2,-4,0,4],[-5,1,3,4]]
b6 = [-13,-8,6,-9]
systems.append((A6,b6,'II.b'))

out = Path(r"c:\Users\Sysx\Documents\AulaTeX-Academico\UANL\ingeniero-agronomo\algebra-lineal\Segundo_Laboratorio_EJ25_solucion.tex")

lines = []
lines.append('\\documentclass{article}')
lines.append('\\usepackage[utf8]{inputenc}')
lines.append('\\usepackage{amsmath,amssymb}')
lines.append('\\usepackage{geometry}')
lines.append('\\geometry{margin=1in}')
lines.append('\\begin{document}')
lines.append('\\title{Soluciones: Segundo Laboratorio \\ Álgebra Lineal — EJ 25}')
lines.append('\\author{Equipo}\\date{}')
lines.append('\\maketitle')

for A,b,label in systems:
    lines.append('\\section*{Sistema ' + label + '}')
    m = len(A)
    lines.append('Coeficientes y vector independiente:')
    lines.append('\\[\\left( ' + mat_repr(A) + '\\right) \\,, \\quad ' + '\\begin{pmatrix}' + ' \\\\ '.join(str(x) for x in b) + '\\end{pmatrix}\\]')
    # Augmented
    Aug = augment([[frac(x) for x in row] for row in A],[frac(x) for x in b])
    # Gauss
    steps, M_end = gaussian_elimination_steps(Aug)
    lines.append('\\subsection*{Método de Gauss (eliminación hacia adelante)}')
    lines.append('Matriz aumentada inicial:')
    lines.append('\\[' + mat_repr(Aug) + '\\]')
    if steps:
        lines.append('Operaciones y sustituciones:')
        # agrupar en filas de 3: cada celda muestra la flechita con la operación y la matriz resultante
        cols = 3
        cells = []
        for i,(op,mat) in enumerate(steps):
            cell = []
            # construir celda con salto de línea entre flecha y matriz
            cell_str = '\\begin{tabular}{c} ' + '$\\xrightarrow{{%s}}$' % op + ' \\\\[2mm] ' + '$' + mat_repr(mat) + '$' + ' \\end{tabular}'
            cells.append(cell_str)
        # construir tabla con n columnas
        lines.append('\\begin{center}')
        lines.append('\\begin{tabular}{' + 'c'*cols + '}')
        for i in range(0, len(cells), cols):
            row = cells[i:i+cols]
            # rellenar con celdas vacías si falta
            while len(row) < cols:
                row.append('')
            lines.append(' & '.join(row) + ' \\\\')
        lines.append('\\end{tabular}')
        lines.append('\\end{center}')
    lines.append('Matriz tras eliminación (forma escalonada aproximada):')
    lines.append('\\[' + mat_repr(M_end) + '\\]')
    # Back substitution to get solution
    # Convert augmented matrix to floats to solve quickly using fractions
    # Build coefficient and rhs after elimination by solving via naive method: use determinant/Cramer's or gaussian elimination fully
    # We'll use Cramer's rule for final numeric solution
    # Cramer
    # compute determinant of A (detailed)
    A_frac = [[frac(x) for x in row] for row in A]
    det_expr, det_val = det_steps(A_frac)
    detA = det_val
    lines.append('\\subsection*{Regla de Cramer}')
    # detailed determinant by cofactors
    det_val, det_lines = det_cofactor(A_frac, name='A')
    lines.append('Cálculo detallado del determinante por cofactores:')
    for dl in det_lines:
        lines.append(dl)
    if det_val == 0:
        lines.append('El determinante es cero, Cramer no aplica o hay infinitas/ninguna solución.')
    else:
        sols = []
        for col in range(len(A)):
            Mcol = [[A_frac[r][c] if c!=col else b[r] for c in range(len(A))] for r in range(len(A))]
            dcol_val, dcol_lines = det_cofactor(Mcol, name=f'A_{{{col+1}}}')
            lines.append(f'Detalle de $\\det(A_{{{col+1}}})$:')
            for dl in dcol_lines:
                lines.append(dl)
            sols.append(f'x_{col+1} = {fmt_entry(dcol_val)}/{fmt_entry(det_val)} = {fmt_entry(dcol_val/det_val)}')
        lines.append('Valores mediante Cramer:')
        lines.append('\\[' + '\\quad '.join(sols) + '\\]')
    # Gauss-Jordan
    ops2, M_rref = gauss_jordan_steps(Aug)
    lines.append('\\subsection*{Gauss-Jordan (reducción por filas)}')
    lines.append('Operaciones y sustituciones (Gauss-Jordan):')
    if ops2:
        lines.append('Operaciones y sustituciones (Gauss-Jordan):')
        cols = 3
        gj_cells = []
        for i,(op,mat) in enumerate(ops2):
            cell = []
            cell_str = '\\begin{tabular}{c} ' + '$\\xrightarrow{{%s}}$' % op + ' \\\\[2mm] ' + '$' + mat_repr(mat) + '$' + ' \\end{tabular}'
            gj_cells.append(cell_str)
        lines.append('\\begin{center}')
        lines.append('\\begin{tabular}{' + 'c'*cols + '}')
        for i in range(0, len(gj_cells), cols):
            row = gj_cells[i:i+cols]
            while len(row) < cols:
                row.append('')
            lines.append(' & '.join(row) + ' \\\\')
        lines.append('\\end{tabular}')
        lines.append('\\end{center}')
    lines.append('Matriz en forma reducida por filas:')
    lines.append('\\[' + mat_repr(M_rref) + '\\]')
    # If detA !=0 get solution from last column
    if detA != 0:
        # extract solution from RREF
        sol = []
        for i in range(len(M_rref)):
            val = Fraction(M_rref[i][-1])
            sol.append(val)
        lines.append('Solución:')
        lines.append('\\[' + ',\\quad '.join([f'x_{i+1} = {s}' for i,s in enumerate(sol)]) + '\\]')
    else:
        lines.append('No se presenta solución única en este método.')

lines.append('\\end{document}')

out.write_text('\n'.join(lines), encoding='utf-8')
print('WROTE TEX:', out)
