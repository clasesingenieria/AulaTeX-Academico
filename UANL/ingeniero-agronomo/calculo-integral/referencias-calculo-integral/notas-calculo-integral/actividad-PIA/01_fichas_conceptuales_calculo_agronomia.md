# Fichas Conceptuales: Cálculo Integral Aplicado a la Ingeniería Agronómica
## Unidad de Aprendizaje: Cálculo Integral — Facultad de Agronomía UANL

### Ficha 1: Cuantificación de Áreas Irregulares y Escorrentía Superficial
- **Concepto clave:** Modelado de perfiles topográficos de cuencas de captación y parcelas mediante integración definida.
- **Formulación matemática:**
  Dadas las cotas de nivel $f(x)$ y $g(x)$ que delimitan un valle agrícola o cauce de riego en el intervalo $[a, b]$:
  $$A = \int_{a}^{b} [f(x) - g(x)]\,dx$$
  Cuando los datos provienen de levantamientos topográficos con estación total o GPS diferencial en nodos discretos $\{x_0, x_1, \dots, x_n\}$, se aplica la Regla de Simpson Compuesta de $\frac{1}{3}$:
  $$A \approx \frac{\Delta x}{3} \left[ y_0 + 4 \sum_{i=1,3,\dots}^{n-1} y_i + 2 \sum_{i=2,4,\dots}^{n-2} y_i + y_n \right]$$
  con error de truncamiento $E_S = -\frac{(b-a)h^4}{180}f^{(4)}(\xi)$.

### Ficha 2: Volúmenes de Sólidos de Revolución en Almacenamiento Hidráulico
- **Concepto clave:** Diseño geométrico de reservorios de almacenamiento hídrico, tajamares y tanques australianos.
- **Método de Discos y Arandelas:**
  Para una presa de tierra o depósito cuya sección transversal gira en torno al eje $x$:
  $$V = \pi \int_{a}^{b} [R(x)^2 - r(x)^2]\,dx$$
- **Método de Cascarones Cilíndricos:**
  Para sólidos generados al rotar en torno al eje $y$:
  $$V = 2\pi \int_{a}^{b} x \cdot [f(x) - g(x)]\,dx$$
- **Capacidad útil agronómica:**
  Se relaciona con la lámina de riego neta ($Ln$) requerida por los cultivos:
  $$V_{\text{util}} = 10 \cdot A_{\text{cultivo}} \cdot Ln$$

### Ficha 3: Trabajo de Bombeo e Integrales Impropias en Dinámica de Fluidos
- **Concepto clave:** Cálculo de la energía y potencia requerida para extraer agua subterránea de pozos agrícolas y dinámicas de decaimiento químico de pesticidas.
- **Trabajo mecánico de vaciado:**
  $$W = \int_{0}^{H} \rho g \cdot A(y) \cdot (H - y)\,dy$$
- **Cinética de degradación e integrales impropias:**
  La persistencia acumulada de un agroquímico en el perfil de suelo con tasa de degradación de primer orden $C(t) = C_0 e^{-kt}$:
  $$\text{Dosis Acumulada Total} = \int_{0}^{\infty} C_0 e^{-kt}\,dt = \lim_{b \to \infty} \left[ -\frac{C_0}{k} e^{-kt} \right]_0^b = \frac{C_0}{k}$$

