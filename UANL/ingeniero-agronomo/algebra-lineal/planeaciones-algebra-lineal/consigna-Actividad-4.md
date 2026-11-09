# Consigna Oficial: Actividad 4 (Fase 3 - Valores y Vectores Propios)

**Identificador institucional:** Actividad 4 (Evidencia de Aprendizaje de la Fase 3, Nexus 3.6)  
**Materia:** Álgebra Lineal (`algebra-lineal`), REF#261104755137  
**Programa:** Ingeniero Agrónomo, Facultad de Agronomía, Universidad Autónoma de Nuevo León (UANL)  
**Estudiante:** Diego de la Cruz Muñoz (Matrícula: 1977875)  
**Docente:** M.C. José de Jesús Miranda Vázquez  

---

## 1. Datos Factuales Explícitos (Plataforma Nexus UANL)

- **Título en plataforma:** `3.6 - Reporte de la solución de un caso de aplicación de los conceptos de valores y vectores propios`
- **Fase curricular:** Fase 3: Valores y vectores propios
- **Ponderación sumativa oficial:** 10 puntos (10 pts)
- **Modalidad:** Individual
- **Período de entrega:** Desde el 19 de agosto de 2026 (01:46 A.M.) hasta el 13 de noviembre de 2026 (11:59 P.M.)
- **Caso / Matriz de coeficientes asignada (Sistema 11):**
  $$A = \begin{pmatrix} -4 & 2 & 6 \\ 10 & 3 & 2 \\ -9 & -7 & 10 \end{pmatrix}$$
- **Objetivo central del reporte:** Obtener los valores propios (autovalores) y vectores propios (autovectores) de la matriz $A$, evaluar la condición de diagonalizabilidad y vincular el resultado con una aplicación agronómica.

---

## 2. Directivas Pedagógicas y Arquitectura de Tres Tiempos

Conforme a los estándares formativos de un curso de Álgebra Lineal de **segundo semestre de ingeniería**, el reporte se estructura estrictamente en la **arquitectura interna de tres tiempos**:

1. **Tiempo 1 (Introducción y planteamiento del problema):**
   - Contextualización breve del papel de los valores y vectores propios en la ingeniería agronómica.
   - Definición formal de la ecuación de autovalores: $A\mathbf{v} = \lambda \mathbf{v} \iff (A - \lambda I)\mathbf{v} = \mathbf{0}$.
   - Declaración de la matriz secular y el objetivo de la actividad.

2. **Tiempo 2 (Desarrollo analítico a nivel de segundo semestre de ingeniería):**
   - **Polinomio característico:** Cálculo de $\det(A - \lambda I) = 0$ por expansión por cofactores paso a paso, obteniendo $\lambda^3 - 9\lambda^2 + 26\lambda + 670 = 0$.
   - **Obtención directa de los autovalores:** Determinación de la raíz real $\lambda_1 \approx -5.8912$, división sintética para obtener el factor cuadrático remanente y aplicación de la fórmula cuadrática general para deducir $\lambda_{2,3} \approx 7.4456 \pm 7.6348i$.
   - **Obtención paso a paso de los autovectores:** Resolución del sistema homogéneo $(A - \lambda_i I)\mathbf{v} = \mathbf{0}$ para cada valor propio mediante sustitución y eliminación por renglones fijando la variable libre ($v_3 = 1$).
   - **Diagnóstico conciso de diagonalizabilidad:** Verificación en $\mathbb{R}$ (no diagonalizable por raíces complejas) y en $\mathbb{C}$ (diagonalizable con matriz modal $V$).
   - **Verificación básica:** Comprobación mediante traza $\operatorname{tr}(A) = 9$ y determinante $\det(A) = -670$.
   - **Transferencia agronómica:** Vinculación directa con modelos de Leslie (dinámica poblacional).

3. **Tiempo 3 (Conclusiones y transferencia):**
   - Conclusiones argumentadas con postura en primera persona sobria.
   - Transferencia práctica al perfil profesional agronómico.
   - Nota ética sobre uso de IA adherida al cierre.
