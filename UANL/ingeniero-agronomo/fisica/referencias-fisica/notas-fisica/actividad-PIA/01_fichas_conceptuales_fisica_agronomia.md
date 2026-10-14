# Fichas Conceptuales: Principios Físicos en Procesos de Producción Agronómica
## Unidad de Aprendizaje: Física — Facultad de Agronomía UANL

### Ficha 1: Dinámica de Fluidos y Principio de Bernoulli en Sistemas de Riego
- **Concepto clave:** Conservación de la energía mecánica en fluidos incompresibles en régimen estacionario.
- **Ecuación de Bernoulli:**
  $$P_1 + \frac{1}{2}\rho v_1^2 + \rho g z_1 = P_2 + \frac{1}{2}\rho v_2^2 + \rho g z_2 + h_L$$
  donde $h_L = f \frac{L}{D} \frac{v^2}{2g}$ representa las pérdidas por fricción según la ecuación de Darcy-Weisbach.
- **Efecto Venturi en fertirrigación:**
  En una constricción de sección $A_2 < A_1$, por continuidad $v_2 = v_1 \frac{A_1}{A_2} > v_1$.
  La consecuente caída de presión estática:
  $$\Delta P = P_1 - P_2 = \frac{1}{2}\rho (v_2^2 - v_1^2)$$
  crea una succión de vacío que inyecta la solución madre de fertilizante directamente al caudal de riego sin bombas auxiliares de combustión.

### Ficha 2: Transferencia de Calor y Termodinámica en Climas Protegidos
- **Mecanismos acoplados:**
  1. *Radiación solar neta ($R_n$):* Entrada de onda corta ($0.3 - 3.0\,\mu\text{m}$) que traspasa el polietileno del invernadero y emisión de onda larga infrarroja retenida (efecto invernadero pasivo).
  2. *Conducción en suelo:* Ley de Fourier:
     $$q = -k \nabla T$$
  3. *Convección natural y forzada:* Ley de enfriamiento de Newton:
     $$q_c = h_c (T_{\text{planta}} - T_{\text{aire}})$$
- **Secado solar de granos:**
  Balance de entalpía y transferencia de masa del agua libre:
  $$\dot{m}_w \cdot \Delta H_{\text{vap}} = \dot{m}_a c_p (T_{\text{in}} - T_{\text{out}})$$

### Ficha 3: Electromagnetismo y Sensores Físicos en Agricultura de Precisión
- **Resistividad y Conductividad Eléctrica Aparente ($CE_a$):**
  La ley de Archie relaciona la conductividad aparente del suelo con la salinidad y contenido de humedad volumétrica ($\theta$):
  $$CE_a = a \cdot CE_w \cdot \theta^m$$
- **Sensores Capacitivos TDR/FDR:**
  La constante dieléctrica del agua ($\kappa_{\text{agua}} \approx 80$) frente a la del suelo seco ($\kappa_{\text{suelo}} \approx 3 - 5$) permite medir en tiempo real el contenido de agua en el bulbo radicular midiendo la frecuencia de oscilación de un circuito LC.

