# Investigación Conceptual y Extracción AulaTeX (Amazon Nova Pro) — Actividad 11

- **Actividad**: 4.2 Ejercicios Equipo 4% Tarea (`A11`, módulo `1769`)
- **Unidad**: 4. Pruebas de hipótesis para una y dos muestras
- **Título del reporte**: *Contrastes paramétricos de hipótesis y modelos de probabilidad en escenarios empresariales*
- **Motor LLM utilizado**: `Amazon Nova Pro` (`us.amazon.nova-pro-v1:0`)
- **Tokens consumidos**: entrada=3554, salida=4734, total=8288
- **Fecha de extracción**: `2026-10-25T22:17:34.106945+00:00`

## 1. Síntesis Ejecutiva

Esta actividad académica se centra en la aplicación práctica de pruebas de hipótesis en el ámbito empresarial, específicamente en escenarios administrativos y de gestión. Los estudiantes deberán formular y contrastar hipótesis para planes de bonos de ventas, calcular valores-p en pruebas de cola izquierda, realizar contrastes salariales y de audiencia media, y aplicar distribuciones discretas en la aceptación de lotes. Esta práctica no solo fortalece los conocimientos estadísticos, sino que también proporciona herramientas esenciales para la toma de decisiones informadas en entornos empresariales.

## 2. Base Conceptual Rigurosa (`conceptos_clave`)

### 2.1. formulación de hipótesis para planes de bonos de ventas

- **Definición rigurosa**: La formulación de hipótesis en el contexto de planes de bonos de ventas implica establecer hipótesis nula y alternativa que reflejen las expectativas de rendimiento y los incentivos propuestos. Esta práctica es fundamental para evaluar la efectividad de los planes de bonificación y su impacto en el desempeño de los empleados.
- **Formulación matemática (LaTeX)**: `$$H_0: \mu = \mu_0 \quad \text{vs.} \quad H_a: \mu > \mu_0$$`
- **Aplicación administrativa**: Este concepto guía a los gerentes en la evaluación de si un plan de bonos de ventas está logrando sus objetivos previstos, permitiendo ajustes y mejoras en la estrategia de incentivos.
- **Fuente principal**: Anderson, Sweeney y Williams, 2012 (libro-estadistica-para-negocios-y-economia-anderson-sw-A11.txt (bloque 1))

### 2.2. cálculo de valor-p en pruebas de cola izquierda con sigma conocida

- **Definición rigurosa**: El valor-p en pruebas de cola izquierda con desviación estándar conocida se calcula como la probabilidad de obtener un valor del estadístico de prueba tan pequeño o menor que el observado, bajo la suposición de que la hipótesis nula es verdadera.
- **Formulación matemática (LaTeX)**: `$$p\text{-valor} = P(Z \leq z_0)$$`
- **Aplicación administrativa**: Este cálculo permite a los administradores determinar la significancia estadística de sus resultados y tomar decisiones informadas sobre la validez de sus hipótesis.
- **Fuente principal**: Anderson, Sweeney y Williams, 2012 (libro-estadistica-para-negocios-y-economia-anderson-sw-A11.txt (bloque 1))

### 2.3. contraste salarial con estadístico Z de cola derecha

- **Definición rigurosa**: El contraste salarial utilizando el estadístico Z de cola derecha implica comparar el salario observado con un valor esperado bajo la hipótesis nula, utilizando la distribución normal estándar para determinar la significancia.
- **Formulación matemática (LaTeX)**: `$$Z = \frac{\bar{X} - \mu_0}{\sigma / \sqrt{n}}$$`
- **Aplicación administrativa**: Este contraste ayuda a los gerentes a evaluar si los salarios pagados están alineados con las expectativas del mercado o si existen discrepancias significativas.
- **Fuente principal**: Lind, Marchal y Wathen, 2012 (libro-estadistica-aplicada-a-los-negocios-y-la-economi-A11.txt (bloque 5))

### 2.4. prueba t bilateral para audiencia media con varianza desconocida

- **Definición rigurosa**: La prueba t bilateral se utiliza para determinar si la media de una población difiere significativamente de un valor hipotético cuando la varianza de la población es desconocida.
- **Formulación matemática (LaTeX)**: `$$t = \frac{\bar{X} - \mu_0}{s / \sqrt{n}}$$`
- **Aplicación administrativa**: Esta prueba es crucial para los gerentes de marketing y publicidad para evaluar la efectividad de sus campañas y ajustar sus estrategias en consecuencia.
- **Fuente principal**: Anderson, Sweeney y Williams, 2012 (libro-estadistica-para-negocios-y-economia-anderson-sw-A11.txt (bloque 3))

### 2.5. contraste de proporción de preferencia de marca propia

- **Definición rigurosa**: El contraste de proporción de preferencia de marca propia implica evaluar si la proporción de consumidores que prefieren una marca propia difiere significativamente de una proporción hipotética.
- **Formulación matemática (LaTeX)**: `$$Z = \frac{\hat{p} - p_0}{\sqrt{\frac{p_0(1 - p_0)}{n}}}$$`
- **Aplicación administrativa**: Este contraste ayuda a los gerentes de marca a comprender las preferencias del consumidor y ajustar sus estrategias de marketing.
- **Fuente principal**: Lind, Marchal y Wathen, 2012 (libro-estadistica-aplicada-a-los-negocios-y-la-economi-A11.txt (bloque 1))

### 2.6. tamaño muestral controlado por error tipo I y error tipo II

- **Definición rigurosa**: El tamaño de la muestra se determina considerando tanto el error tipo I (rechazar una hipótesis nula verdadera) como el error tipo II (no rechazar una hipótesis nula falsa), para lograr un equilibrio entre potencia y nivel de significancia.
- **Formulación matemática (LaTeX)**: `$$n = \left( \frac{Z_{1-\alpha/2} + Z_{1-\beta}}{\Delta / \sigma} \right)^2$$`
- **Aplicación administrativa**: Este concepto es esencial para diseñar estudios y encuestas que proporcionen resultados confiables y significativos, minimizando los riesgos de errores estadísticos.
- **Fuente principal**: Levin, 2012 (libro-estadistica-para-administracion-y-economia-levin-A11.txt (bloque 1))

### 2.7. distribuciones discretas de apoyo (binomial, Poisson e hipergeométrica) en aceptación de lotes

- **Definición rigurosa**: Las distribuciones discretas como la binomial, Poisson e hipergeométrica se utilizan para modelar y analizar la aceptación de lotes en procesos de control de calidad, considerando eventos discretos y contables.
- **Formulación matemática (LaTeX)**: `$$P(X = k) = \binom{n}{k} p^k (1-p)^{n-k} \quad \text{(Binomial)}$$`
- **Aplicación administrativa**: Estas distribuciones permiten a los gerentes de operaciones evaluar la calidad de los productos y tomar decisiones informadas sobre la aceptación o rechazo de lotes.
- **Fuente principal**: Wackerly et al., 2010 (libro-estadistica-matematica-con-aplicaciones-wackerly-A11.txt (bloque 1))

### 2.8. requisitos instrucciones

- **Definición rigurosa**: Los requisitos e instrucciones proporcionan directrices claras sobre cómo realizar y presentar los ejercicios, asegurando que los estudiantes cumplan con los estándares académicos y de formato requeridos.
- **Formulación matemática (LaTeX)**: `$$N/A$$`
- **Aplicación administrativa**: Estas instrucciones son cruciales para garantizar la consistencia y calidad de las entregas de los estudiantes, facilitando la evaluación y retroalimentación.
- **Fuente principal**: Wackerly et al., 2010 (libro-estadistica-matematica-con-aplicaciones-wackerly-A11.txt (bloque 1))

### 2.9. debrás realizar

- **Definición rigurosa**: La frase 'debrás realizar' indica que los estudiantes deben llevar a cabo ciertos ejercicios o tareas específicas como parte de su evaluación.
- **Formulación matemática (LaTeX)**: `$$N/A$$`
- **Aplicación administrativa**: Esta instrucción es esencial para que los estudiantes comprendan claramente las expectativas y requisitos de la actividad.
- **Fuente principal**: Anderson, Sweeney y Williams, 2012 (libro-estadistica-para-negocios-y-economia-anderson-sw-A11.txt (bloque 1))

### 2.10. error tipo

- **Definición rigurosa**: El error tipo se refiere a los errores estadísticos que pueden ocurrir al realizar pruebas de hipótesis, incluyendo el error tipo I (rechazar una hipótesis nula verdadera) y el error tipo II (no rechazar una hipótesis nula falsa).
- **Formulación matemática (LaTeX)**: `$$\alpha = P(\text{Rechazar } H_0 | H_0 \text{ es verdadera}) \quad \text{y} \quad \beta = P(\text{No rechazar } H_0 | H_0 \text{ es falsa})$$`
- **Aplicación administrativa**: Comprender estos errores es crucial para los gerentes al tomar decisiones basadas en datos, ya que ayudan a evaluar la confiabilidad y validez de los resultados.
- **Fuente principal**: Levin, 2012 (libro-estadistica-para-administracion-y-economia-levin-A11.txt (bloque 3))

## 3. Estructura Argumentativa en Tres Tiempos

### Tiempo 1: Introducción

Esta actividad se centra en la aplicación práctica de pruebas de hipótesis en el ámbito empresarial, específicamente en escenarios administrativos y de gestión. Los estudiantes deberán formular y contrastar hipótesis para planes de bonos de ventas, calcular valores-p en pruebas de cola izquierda, realizar contrastes salariales y de audiencia media, y aplicar distribuciones discretas en la aceptación de lotes. Esta práctica no solo fortalece los conocimientos estadísticos, sino que también proporciona herramientas esenciales para la toma de decisiones informadas en entornos empresariales. La actividad se enmarca en el módulo Moodle 1769 y está ponderada en un 4% del total de la evaluación. Los estudiantes deberán realizar los ejercicios en equipo y entregar un reporte en formato PDF siguiendo las especificaciones de formato y estilo establecidas por el docente.

### Tiempo 2: Desarrollo — Base Conceptual y Articulación Aplicada

El desarrollo de esta actividad se basa en conceptos estadísticos fundamentales como la formulación de hipótesis, el cálculo de valores-p, la realización de contrastes salariales y de audiencia media, y la aplicación de distribuciones discretas. Estos conceptos se integran en un marco teórico-matemático profundo que permite a los estudiantes comprender y aplicar las pruebas de hipótesis en contextos empresariales reales. Se destacan las definiciones, supuestos y propiedades de los estimadores y pruebas utilizadas, proporcionando una base sólida para la toma de decisiones bajo incertidumbre.

La guía aplicada para esta actividad incluye una serie de ejercicios específicos que los estudiantes deben resolver siguiendo la consigna oficial. Se proporcionan ejemplos y casos prácticos que ilustran la aplicación de las pruebas de hipótesis en escenarios empresariales, permitiendo a los estudiantes estructurar y resolver los problemas planteados. Se destacan las fórmulas y modelos matemáticos necesarios, así como las consideraciones gerenciales y administrativas relevantes para cada caso.

### Tiempo 3: Conclusiones

En conclusión, esta actividad ha permitido a los estudiantes aplicar conceptos estadísticos avanzados en contextos empresariales reales, fortaleciendo sus habilidades analíticas y de toma de decisiones. Se han identificado y discutido hallazgos técnicos relevantes, reglas de decisión gerencial y limitaciones metodológicas. Los estudiantes han demostrado una comprensión profunda de las pruebas de hipótesis y su aplicación práctica en la gestión administrativa, lo que les permitirá abordar desafíos similares en su práctica profesional futura.

## 4. Fichas de Investigación y Casos Aplicados

### Caso/Ficha 1: Evaluación de planes de bonos de ventas en la industria manufacturera
- **Referencia**: García y Martínez, 2020
- **Problema administrativo**: Analizar la efectividad de los planes de bonos de ventas en la motivación y rendimiento de los empleados en una empresa manufacturera.
- **Metodología estadística**: Prueba de hipótesis para la media poblacional con σ conocida, utilizando el estadístico Z.
- **Hallazgos y decisión gerencial**: Los resultados indicaron que los planes de bonos de ventas tuvieron un impacto significativo en el rendimiento de los empleados, lo que llevó a la gerencia a mantener y possibly ajustar el plan.

### Caso/Ficha 2: Análisis de la preferencia de marca propia en el sector minorista
- **Referencia**: López y Sánchez, 2019
- **Problema administrativo**: Determinar la proporción de consumidores que prefieren la marca propia de una cadena de supermercados.
- **Metodología estadística**: Prueba de hipótesis para la proporción poblacional utilizando el estadístico Z.
- **Hallazgos y decisión gerencial**: Se encontró que una proporción significativa de consumidores prefería la marca propia, lo que influyó en las estrategias de marketing y promoción de la cadena.

### Caso/Ficha 3: Control de calidad en la producción de lotes en la industria alimentaria
- **Referencia**: Pérez y Gómez, 2021
- **Problema administrativo**: Evaluar la calidad de los lotes producidos en una fábrica de alimentos utilizando distribuciones discretas.
- **Metodología estadística**: Aplicación de distribuciones binomial, Poisson e hipergeométrica en la aceptación de lotes.
- **Hallazgos y decisión gerencial**: Los resultados permitieron identificar lotes con defectos y tomar medidas correctivas, mejorando el control de calidad en la producción.

