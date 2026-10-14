# Consigna de Evaluación: Producto Integrador de Aprendizaje (PIA)
## Unidad de Aprendizaje: Cálculo Integral (REF#261013755131)
### Facultad de Agronomía — Universidad Autónoma de Nuevo León

- **Valor porcentual:** 30% (30 puntos sobre 100)
- **Modalidad:** Trabajo individual o parejas
- **Formato del producto:**
  1. Reporte formal en formato institucional UANL (`reporte-calculo-integral-PIA.pdf`).
  2. Presentación ejecutiva Beamer 16:9 (`presentacion-calculo-integral-PIA.pdf`).

---

## 1. Propósito y Contextualización
Diseñar y modelar analíticamente un sistema integral de aprovechamiento hídrico y balance volumétrico para un distrito de riego agrícola empleando cálculo integral. 

El estudiante deberá resolver un problema de ingeniería agronómica que integre:
1. Determinación de perfiles de área superficial de parcelas irregulares mediante integración definida numérica y analítica:
   $$A = \int_{a}^{b} [f(x) - g(x)]\,dx$$
2. Modelación volumétrica de tanques australianos y reservorios de almacenamiento hídrico con paredes de revolución mediante cascarones y discos:
   $$V = \pi \int_{a}^{b} [R(x)]^2\,dx \quad \text{o} \quad V = 2\pi \int_{a}^{b} x \cdot f(x)\,dx$$
3. Cálculo del trabajo mecánico $W = \int F\,ds$ requerido para el bombeo de fluidos fertilizantes y dinámica de sedimentación mediante integrales impropias.

---

## 2. Requisitos de Estructura Institucional (AulaTeX)

1. **Carátula Oficial UANL / Agronomía:**
   - Logotipos institucionales normalizados.
   - Matrícula del estudiante (Carlos Mauricio Carvajal Coronado - 1977875).
   - Datos de la unidad y fecha de entrega.
2. **Resumen y Abstracción del Modelo:**
   - Planteamiento formal del modelo matemático y justificación agronómica.
3. **Desarrollo Matemático y Demostraciones:**
   - Graficación de fronteras y recintos de integración.
   - Demostración de convergencia en integrales impropias.
   - Obtención paso a paso de antiderivadas y evaluación analítica por el Teorema Fundamental del Cálculo.
4. **Validación y Aplicación Práctica:**
   - Discusión de capacidad de almacenaje hídrico, tasa de recarga y horas de bombeo.
5. **Referencias Bibliográficas:**
   - Citación estricta en APA 7 (Larson, Stewart, Thomas, manuales de riego de SAGARPA/CONAGUA).

---

## 3. Rúbrica de Evaluación del PIA (100 puntos = 30% final)

| Criterio | Excelente (100-90%) | Satisfactorio (89-75%) | Básico (74-60%) | No Aprobatorio (<60%) | Ponderación |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Modelación y Planteamiento de Integrales** | Definición impecable de diferenciales, límites de integración y funciones seccionadas para modelar el reservorio y parcela. | Planteamiento correcto con ligeras omisiones en la justificación de límites. | Planteamiento básico con imprecisiones en el elemento diferencial $dx$ o $dy$. | Errores en la formulación de las integrales que invalidan el cálculo. | **30%** |
| **Rigor en la Integración y Procedimiento** | Métodos analíticos avanzados empleados con pulcritud; cálculo exacto de volúmenes y trabajo de bombeo. | Procedimiento correcto con errores aritméticos menores que no afectan la lógica. | Aplicación mecánica de fórmulas con pasos omitidos. | Procedimiento algebraico inconsistente o resultados ficticios. | **35%** |
| **Interpretación y Viabilidad Agronómica** | Vinculación sobresaliente entre el resultado volumétrico y la lámina de riego para los cultivos. | Explicación correcta de la utilidad técnica de las curvas y volúmenes calculados. | Análisis meramente numérico sin contextualizar el sector agrícola. | Cero vinculación profesional con la agronomía. | **20%** |
| **Formato Institucional y Bibliografía APA 7** | Adherencia total al estándar AulaTeX UANL, compilación limpia en XeLaTeX, figuras nítidas y citas canónicas. | Formato general adecuado con detalles tipográficos menores. | Omisiones en el aparato crítico o tipografía no institucional. | Formato no oficial o sin bibliografía. | **15%** |

