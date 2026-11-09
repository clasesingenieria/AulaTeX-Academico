# Planeación Académica: Reporte de la solución de un caso de aplicación de los conceptos de valores y vectores propios

**Unidad de Aprendizaje:** Álgebra Lineal (`REF-01ef444f23`)
**Programa Educativo:** Ingeniero Agrónomo
**Institución:** UANL
**Docente Titular:** M.C. José de Jesús Miranda Vázquez
**Estudiante:** Carlos Mauricio Carvajal Coronado (Matrícula: 1977875)
**Actividad Contractual:** actividad-4 (Nexus 3.6)
**Fase / Unidad:** Fase 3: Valores y vectores propios
**Ponderación:** 10.0 pts
**Estado de Revisión:** `ready` (Validación semántica: `passed`)

---

## 1. Identificación y Contrato de Artefactos

```json
{
  "schema_version": "1.0.0",
  "plan_id": "pca-uanl-algebra-lineal-actividad-4",
  "subject_id": "algebra-lineal",
  "offering_id": "REF-01ef444f23",
  "deliverables_directory": "entregas-algebra-lineal"
}
```

---

## 2. Instrucción y Consigna Formativa

### Planteamiento y Objetivos
- Resolución exacta del Sistema 11 asignado:
  $$\begin{aligned}
  -4x + 2y + 6z &= -6, \\
  10x + 3y + 2z &= -6, \\
  -9x - 7y + 10z &= -7.
  \end{aligned}$$
  por Eliminación de Gauss-Jordan, Regla de Cramer y Método de la Matriz Inversa ($\det(A) = -670$, solución $x = -103/335, y = -74/335, z = -379/335$).
- Modelado procedimental mediante diagrama estructurado de algoritmo en TikZ.
- **Depuración estricta de contenidos innecesarios**: supresión de repeticiones redundantes de la solución del sistema lineal y descarte de derivaciones colaterales no solicitadas (como partes simétricas ajenas).
- **Deducción paso a paso y con cuidado expositivo** de los valores propios y vectores propios de la matriz de coeficientes $A$:
  - Planteamiento de la ecuación secular $\det(A - \lambda I) = 0$ y desarrollo detallado por cofactores.
  - Deducción del polinomio característico $P(\lambda) = -\lambda^3 + 9\lambda^2 - 26\lambda - 670 = 0$.
  - Solución paso a paso de la ecuación cúbica mediante la ecuación deprimida $t^3 - t + 694 = 0$ y análisis del discriminante de Cardano ($\Delta > 0$).
  - Obtención de los autovalores: raíz real $\lambda_1 \approx -5.8912$ y raíces complejas conjugadas $\lambda_{2,3} \approx 7.4456 \pm 7.6348i$.
  - Deducción analítica de los autovectores resolviendo $(A - \lambda_i I)\mathbf{v}_i = \mathbf{0}$, mostrando la expresión paramétrica general y las bases de los subespacios propios.
  - Estudio de diagonalizabilidad en $\mathbb{R}$ (no diagonalizable) y $\mathbb{C}$ (diagonalizable con $A = V D V^{-1}$).
  - Verificación analítica independiente ($\operatorname{tr}(A) = 9$, $\det(A) = -670$, $A\mathbf{v}_i = \lambda_i \mathbf{v}_i$).
  - Aplicación agronómica cuantitativa en dinámica poblacional de Leslie y desacoplamiento de difusión de nutrientes en el suelo.

### Requisitos Contractuales
- **req-1:** Desarrollo analítico riguroso y depurado, sin contenido redundante o innecesario.
- **req-2:** Cuidado expositivo detallado en autovalores, autovectores y diagonalizabilidad.
- **req-3:** Aparato crítico y referencias bibliográficas en formato APA 7ma edición validadas contra `algebra-lineal.bib`.

---

## 3. Entregables y Productos Verificados

### Producto: `prod-actividad-4`
- **Denominación:** reporte_academico
- **Formato editable:** `application/x-tex` -> `reporte-algebra-lineal-Actividad-4.tex`
- **Formato de entrega:** `application/pdf` -> `reporte-algebra-lineal-Actividad-4.pdf`
- **Extensión presupuestada:** 7 a 10 páginas
- **Patrón de nomenclatura:** `reporte-algebra-lineal-Actividad-4.pdf`

---

## 4. Criterios de Evaluación y Rúbrica Oficial

- **Ponderación total:** 10.0 pts
- **crit-1:** Rigor matemático, resolución exacta y cuidado expositivo espectral (5.0 pts)
- **crit-2:** Calidad editorial, integración fluida sin redundancias y aparato crítico APA (5.0 pts)
- **Comprobaciones editoriales obligatorias:** Sin citas huérfanas, sin bloques meta-pedagógicos desarticulados, compilación limpia con `latexmk` a PDF.

---

## 5. Políticas Académicas y Éticas

- **Uso de Inteligencia Artificial:** Declaración transparente de asistencia algorítmica en nota al pie institucional.
- **Integridad Científica:** Cero tolerancia al plagio; fuentes primarias académicas verificadas.
- **Citación:** APA 7ma edición sincronizada con el archivo bibliográfico.
