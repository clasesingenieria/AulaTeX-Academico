# Planeación Académica: Reporte de la solución de un caso de aplicación de los conceptos de valores y vectores propios

**Unidad de Aprendizaje:** Álgebra Lineal (`REF-01ef444f23`)
**Programa Educativo:** Ingeniero Agrónomo
**Institución:** UANL
**Docente Titular:** M.C. José de Jesús Miranda Vázquez
**Estudiante:** Diego de la Cruz Muñoz (Matrícula: 1977875)
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

## 2. Estructuración en Tres Tiempos (Nivel Segundo Semestre de Ingeniería)

### Tiempo 1: Introducción y Planteamiento del Problema
- Contextualización de valores y vectores propios en la ingeniería agronómica.
- Planteamiento de la matriz de coeficientes $A = \begin{pmatrix} -4 & 2 & 6 \\ 10 & 3 & 2 \\ -9 & -7 & 10 \end{pmatrix}$.
- Definición de la ecuación secular $(A - \lambda I)\mathbf{v} = \mathbf{0}$ y meta analítica.

### Tiempo 2: Cálculo Analítico de Valores y Vectores Propios
- Cálculo directo del polinomio característico $\det(A - \lambda I) = \lambda^3 - 9\lambda^2 + 26\lambda + 670 = 0$.
- Obtención directa de los tres autovalores: raíz real $\lambda_1 \approx -5.8912$ y raíces complejas conjugadas $\lambda_{2,3} \approx 7.4456 \pm 7.6348i$ (por factorización y fórmula cuadrática estándar).
- Deducción paso a paso de los autovectores resolviendo el sistema homogéneo con variable libre $v_3 = 1$.
- Diagnóstico claro de diagonalizabilidad (no diagonalizable en $\mathbb{R}$, diagonalizable en $\mathbb{C}$).
- Verificación con traza y determinante.
- Mención aplicada en modelos de Leslie.

### Tiempo 3: Conclusiones y Transferencia Agronómica
- Conclusiones argumentadas con postura personal reflexiva.
- Transferencia al ámbito profesional.
- Declaración ética de IA y referencias bibliográficas en página nueva.

### Requisitos Contractuales
- **req-1:** Arquitectura de tres tiempos sin etiquetas literales en encabezados.
- **req-2:** Nivel de segundo semestre de ingeniería: directo, claro y enfocado exclusivamente en autovalores y autovectores.
- **req-3:** Citas bibliográficas APA 7ma edición validadas contra `algebra-lineal.bib`.

---

## 3. Entregables y Productos Verificados

### Producto: `prod-actividad-4`
- **Denominación:** reporte_academico
- **Formato editable:** `application/x-tex` -> `reporte-algebra-lineal-Actividad-4.tex`
- **Formato de entrega:** `application/pdf` -> `reporte-algebra-lineal-Actividad-4.pdf`
- **Extensión presupuestada:** 5 a 7 páginas
- **Patrón de nomenclatura:** `reporte-algebra-lineal-Actividad-4.pdf`
