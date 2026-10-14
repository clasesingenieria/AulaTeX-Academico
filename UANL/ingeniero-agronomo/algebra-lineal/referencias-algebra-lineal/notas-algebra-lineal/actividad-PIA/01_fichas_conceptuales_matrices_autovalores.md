# Fichas Conceptuales: Álgebra Matricial, Sistemas Lineales y Autovalores en Agronomía
## Unidad de Aprendizaje: Álgebra Lineal — Facultad de Agronomía UANL

### Ficha 1: Matrices y Sistemas de Ecuaciones en Balance de Masa de Suelos
- **Concepto clave:** Modelo de insumo-producto y balance de macronutrientes ($N, P, K$).
- **Formalismo matemático:**
  Sea el sistema lineal $A\mathbf{x} = \mathbf{b}$, donde:
  - $A \in \mathbb{R}^{3 \times 3}$ representa la matriz de concentraciones de nutrientes en tres fertilizantes comerciales (e.g. Urea, Superfosfato triple, Cloruro de potasio).
  - $\mathbf{x} = [x_1, x_2, x_3]^T$ son las dosis en kg/ha a aplicar.
  - $\mathbf{b} = [b_N, b_P, b_K]^T$ son los requerimientos nutrimentales del cultivo por hectárea según análisis de fertilidad de suelos.
- **Condición de solvencia y consistencia:**
  Por el Teorema de Rouché-Capelli (o Rouché-Frobenius), el sistema tiene solución única si y sólo si $\operatorname{rango}(A) = \operatorname{rango}([A|\mathbf{b}]) = 3$, lo que equivale a $\det(A) \neq 0$.
  La solución analítica se deduce mediante inversión matricial:
  $$\mathbf{x} = A^{-1}\mathbf{b} = \frac{1}{\det(A)}\operatorname{Adj}(A)\mathbf{b}$$

### Ficha 2: Matrices de Transición de Leslie y Dinámica Poblacional
- **Concepto clave:** Modelado estocástico/discreto de poblaciones estructuradas por edades (e.g. plagas de insectos en cultivos o rotación de ganado).
- **Ecuación matricial de Leslie:**
  $$\mathbf{n}(t+1) = L \cdot \mathbf{n}(t)$$
  donde el vector de estados $\mathbf{n}(t) = [n_1(t), n_2(t), \dots, n_k(t)]^T$ agrupa el número de individuos por clase de edad.
  La matriz de Leslie $L$ tiene la forma:
  $$L = \begin{pmatrix} f_1 & f_2 & \dots & f_{k-1} & f_k \\ s_1 & 0 & \dots & 0 & 0 \\ 0 & s_2 & \dots & 0 & 0 \\ \vdots & \vdots & \ddots & \vdots & \vdots \\ 0 & 0 & \dots & s_{k-1} & 0 \end{pmatrix}$$
  donde $f_i \ge 0$ es la fertilidad per cápita y $s_i \in (0, 1]$ es la probabilidad de supervivencia de la clase $i$ a la clase $i+1$.

### Ficha 3: Autovalores, Autovectores y Tasa Intrínseca de Crecimiento
- **Ecuación característica:**
  $$\det(L - \lambda I) = 0$$
- **Teorema de Perron-Frobenius:**
  Puesto que $L$ es una matriz no negativa e irreducible (asumiendo al menos dos fertilidades consecutivas positivas), existe un autovalor real, positivo y estrictamente dominante $\lambda_1 > |\lambda_j|$ para todo $j \neq 1$.
- **Interpretación agronómica:**
  - Si $\lambda_1 > 1$: la población de la plaga o cultivo crece exponencialmente a una tasa asintótica $\lambda_1 - 1$.
  - Si $\lambda_1 = 1$: población en estado estacionario homeostático.
  - Si $\lambda_1 < 1$: población en declive o erradicación biológica.
  - El autovector derecho $\mathbf{v}_1$ asociado a $\lambda_1$ determina la **estructura de edades estable** de la población:
    $$\lim_{t \to \infty} \frac{\mathbf{n}(t)}{\|\mathbf{n}(t)\|} = \frac{\mathbf{v}_1}{\|\mathbf{v}_1\|}$$

