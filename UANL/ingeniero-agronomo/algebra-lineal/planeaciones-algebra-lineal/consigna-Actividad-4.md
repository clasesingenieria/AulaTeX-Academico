# Consigna Oficial: Actividad 4 (Fase 3 - Valores y Vectores Propios)

**Identificador institucional:** Actividad 4 (Evidencia de Aprendizaje de la Fase 3, Nexus 3.6)  
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
  Matriz de coeficientes y vector de términos independientes del sistema:
  $$A = \begin{pmatrix} -4 & 2 & 6 \\ 10 & 3 & 2 \\ -9 & -7 & 10 \end{pmatrix}, \quad \mathbf{b} = \begin{pmatrix} -6 \\ -6 \\ -7 \end{pmatrix}$$
- **Contenidos obligatorios declarados:**
  1. Definición y formalización de valores y vectores propios sobre la matriz del sistema.
  2. Polinomio característico y cálculo de valores propios paso a paso.
  3. Deducción detallada de vectores propios y subespacios propios asociados.
  4. Análisis de diagonalizabilidad en los cuerpos $\mathbb{R}$ y $\mathbb{C}$.
  5. Aplicaciones agronómicas cuantitativas de los valores y vectores propios (modelos de Leslie y desacoplamiento de transporte).
- **Criterios de desempeño oficiales:**
  - Solución matemática detallada paso a paso.
  - Enfoque riguroso y depurado: eliminación estricta de contenidos innecesarios que no pertenezcan a la resolución del ejercicio (sin digresiones de partes simétricas ajenas ni duplicación de la solución del sistema lineal).
  - Cuidado expositivo de alto nivel en la derivación analítica de autovalores y autovectores.
  - Interpretación rigurosa de los resultados analíticos a través de conclusiones argumentadas.
  - Orden lógico, precisión conceptual y tipográfica, sin invención ni copia.
  - Formato PDF estructurado con estándares editoriales AulaTeX.

---

## 2. Directivas Pedagógicas y Criterios de Resolución Depurada

1. **Resolución canónica del Sistema Lineal:** Se preserva la resolución analítica exacta del Sistema 11 mediante los tres métodos clásicos (Eliminación de Gauss-Jordan, Regla de Cramer y Método de la Matriz Inversa), demostrando compatibilidad determinada con determinante principal $\det(A) = -670 \neq 0$ y vector solución único $\mathbf{u}^* = (-103/335, -74/335, -379/335)^T$, complementado con su diagrama algorítmico estructurado en TikZ.
2. **Depuración de contenido redundante o innecesario:**
   - Se suprime la re-resolución redundante del sistema lineal en secciones posteriores.
   - Se eliminan descomposiciones colaterales que no forman parte del sistema propuesto (como el análisis de la parte simétrica $S = (A+A^T)/2$, ya que la matriz $A$ no es simétrica y lo solicitado son los autovalores y autovectores del sistema propuesto).
   - Se erradican encabezados genéricos descontextualizados tipo `\section*{1. Identificación}`, integrando toda la discusión en subsecciones analíticas fluidas.
3. **Cuidado expositivo paso a paso en autovalores y autovectores:**
   - Planteamiento formal de la ecuación secular $\det(A - \lambda I) = 0$.
   - Expansión exhaustiva por cofactores mostrando cada menor $2 \times 2$ y agrupación algebraica hasta obtener el polinomio característico $P(\lambda) = -\lambda^3 + 9\lambda^2 - 26\lambda - 670 = 0$.
   - Resolución analítica completa de la ecuación cúbica mediante la transformación a forma deprimida ($\lambda = t + 3 \implies t^3 - t + 694 = 0$), evaluación del discriminante de Cardano ($\Delta > 0$), y obtención precisa tanto de la raíz real ($\lambda_1 \approx -5.8912$) como del par de raíces complejas conjugadas ($\lambda_{2,3} \approx 7.4456 \pm 7.6348i$).
   - Obtención paso a paso de los autovectores asociados resolviendo el sistema homogéneo $(A - \lambda_i I)\mathbf{v}_i = \mathbf{0}$, explicitando la fórmula cerrada $\mathbf{v}(\lambda) = (6\lambda - 14, 2\lambda + 68, \lambda^2 + \lambda - 32)^T$ y sus componentes numéricas para cada autovalor.
   - Análisis de diagonalizabilidad en $\mathbb{R}$ y $\mathbb{C}$, matriz modal $V$ y descomposición $A = V D V^{-1}$.
   - Verificación matemática independiente: invariancia de traza ($\sum \lambda_i = 9 = \operatorname{tr}(A)$), determinante ($\prod \lambda_i = -670 = \det(A)$) y ecuación de definición $A\mathbf{v}_i = \lambda_i \mathbf{v}_i$.
4. **Transferencia agronómica:** Vinculación conceptual y cuantitativa con la estabilidad asintótica de sistemas biológicos (matrices de Leslie-Lefkovitch) y desacoplamiento de ecuaciones diferenciales acopladas para transporte de solutos en la rizosfera.
