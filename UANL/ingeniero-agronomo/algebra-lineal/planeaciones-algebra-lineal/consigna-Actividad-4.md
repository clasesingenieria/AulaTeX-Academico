# Consigna Oficial: Actividad 3.6 (Fase 3 - Valores y Vectores Propios)

**Identificador institucional:** Actividad 3.6 (Evidencia de Aprendizaje de la Fase 3)  
**Materia:** Álgebra Lineal (`algebra-lineal`), REF#261104755137  
**Programa:** Ingeniero Agrónomo, Facultad de Agronomía, Universidad Autónoma de Nuevo León (UANL)  
**Estudiante:** Carlos Mauricio Carvajal Coronado (Matrícula: 1977875)  
**Docente:** M.C. José de Jesús Miranda Vázquez  

---

## 1. Datos Factuales Explícitos (Plataforma Nexus UANL)

- **Título en plataforma:** `3.6 - Reporte de la solución de un caso de aplicación de los conceptos de valores y vectores propios`
- **Fase curricular:** Fase 3: Valores y vectores propios
- **Ponderación sumativa oficial:** 10 puntos (10 pts)
- **Modalidad:** Individual
- **Período de entrega:** Desde el 19 de agosto de 2026 (01:46 A.M.) hasta el 13 de noviembre de 2026 (11:59 P.M.)
- **Caso / Hoja de asignación:** Asignación docente correspondiente al **Sistema 11** de la hoja de evidencias:
  $$\begin{aligned}
  -4x + 2y + 6z &= -6, \\
  10x + 3y + 2z &= -6, \\
  -9x - 7y + 10z &= -7.
  \end{aligned}$$
  Matriz de coeficientes del sistema:
  $$A = \begin{pmatrix} -4 & 2 & 6 \\ 10 & 3 & 2 \\ -9 & -7 & 10 \end{pmatrix}, \quad \mathbf{b} = \begin{pmatrix} -6 \\ -6 \\ -7 \end{pmatrix}$$
- **Contenidos obligatorios declarados:**
  1. Definición de valor y vector propio.
  2. Polinomio característico y cálculo de valores propios.
  3. Diagonalización matricial en $\mathbb{R}$ y $\mathbb{C}$.
  4. Matrices simétricas y diagonalización ortogonal.
  5. Aplicaciones agronómicas cuantitativas de los valores y vectores propios.
- **Criterios de desempeño oficiales:**
  - Solución matemática detallada paso a paso.
  - Interpretación rigurosa de los resultados analíticos a través de conclusiones argumentadas.
  - Orden lógico, precisión, sin invención ni copia.
  - Formato PDF estructurado con estándares editoriales.

---

## 2. Inferencias Pedagógicas y Supuestos Declarados

1. **Inferencia de articulación temática:** La actividad 3.6 solicita un caso de aplicación de valores y vectores propios basándose en la matriz $A$ del Sistema 11 asignado en la Fase 2, articulando la resolución del sistema lineal compatible determinado ($\det(A) = -670 \neq 0$, solución $(-103, -74, -379)/335$) con su análisis espectral completo.
2. **Supuesto de aplicación agronómica:** Dado que el Sistema 11 no contiene unidades físicas en la hoja docente, el análisis espectral se transfiere conceptualmente a dos ámbitos agronómicos canónicos:
   - Dinámica poblacional discreta mediante matrices de Leslie ($x_{k+1} = M x_k$) y el Teorema de Perron-Frobenius (tasa intrínseca de crecimiento $\lambda_{\max}$ y estructura etaria estable).
   - Desacoplamiento de matrices de transporte y difusión de solutos/nutrientes (N-P-K) en la rizosfera mediante cambio de base modal.
3. **Metodología matemática requerida:** 7 etapas formales con derivación del polinomio característico $P(\lambda) = -\lambda^3 + 9\lambda^2 - 26\lambda - 670 = 0$, deducción de autovalores reales y complejos conjugados, autoespacios asociados, análisis de diagonalizabilidad y verificación independiente mediante sustitución directa y propiedades de invariancia de traza ($\operatorname{tr}(A) = 9$) y determinante ($\det(A) = -670$).
