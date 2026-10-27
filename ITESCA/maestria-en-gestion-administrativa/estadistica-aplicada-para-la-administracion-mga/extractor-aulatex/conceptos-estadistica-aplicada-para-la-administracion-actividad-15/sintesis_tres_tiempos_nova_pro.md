# Investigación Conceptual y Extracción AulaTeX (Amazon Nova Pro) — Actividad 15

- **Actividad**: 5.3 Ejercicios individuales 5% Tarea (`A15`, módulo `1777`)
- **Unidad**: 5. Pruebas de hipótesis no paramétricas
- **Título del reporte**: *Pruebas de aleatoriedad por rachas y contrastes no paramétricos en operaciones y servicios (Ejercicios 7 a 12)*
- **Motor LLM utilizado**: `Amazon Nova Pro` (`us.amazon.nova-pro-v1:0`)
- **Tokens consumidos**: entrada=3825, salida=6283, total=10108
- **Fecha de extracción**: `2026-10-25T22:38:12.240413+00:00`

## 1. Síntesis Ejecutiva

Esta actividad académica se centra en la aplicación práctica de pruebas de hipótesis no paramétricas en el ámbito administrativo. Los estudiantes realizarán ejercicios individuales que involucran la prueba de rachas para evaluar la aleatoriedad en diferentes contextos operacionales y la aplicación de las pruebas de Kruskal-Wallis y Mann-Whitney para comparar múltiples muestras. Estas técnicas son esenciales para la toma de decisiones gerenciales basadas en datos no normalmente distribuidos, proporcionando una herramienta robusta para analizar y comparar datos en entornos complejos y variables.

## 2. Base Conceptual Rigurosa (`conceptos_clave`)

### 2.1. prueba de rachas

- **Definición rigurosa**: La prueba de rachas es un método estadístico no paramétrico utilizado para evaluar la aleatoriedad en una secuencia de datos. Se basa en el conteo de rachas, que son secuencias consecutivas de un mismo tipo de evento. La prueba verifica si el número observado de rachas difiere significativamente del número esperado bajo la hipótesis nula de aleatoriedad.
- **Formulación matemática (LaTeX)**: `$$La estadística de prueba se calcula como $R = \sum_{i=1}^{n} I(X_i \neq X_{i-1})$, donde $I$ es la función indicadora y $X_i$ son los datos observados.$$`
- **Aplicación administrativa**: En administración, la prueba de rachas puede ser utilizada para detectar patrones no aleatorios en datos operacionales, como la llegada de clientes o defectos en productos, lo que permite a los gerentes identificar ineficiencias o problemas de calidad.
- **Fuente principal**: Wackerly, D., Mendenhall, W., & Scheaffer, R. L. (2014). Estadística matemática con aplicaciones. 7ª edición. (libro-estadistica-matematica-con-aplicaciones-wackerly-A15.txt (bloque 1))

### 2.2. prueba H de Kruskal-Wallis

- **Definición rigurosa**: La prueba H de Kruskal-Wallis es una extensión de la prueba de Mann-Whitney para comparar más de dos muestras independientes. Se basa en el análisis de rangos y se utiliza para determinar si existen diferencias significativas entre las medianas de las muestras.
- **Formulación matemática (LaTeX)**: `$$La estadística de prueba se calcula como $H = \frac{12}{N(N+1)} \sum_{i=1}^{k} \frac{R_i^2}{n_i} - 3(N+1)$, donde $R_i$ es la suma de rangos de la muestra $i$ y $n_i$ es el tamaño de la muestra $i$.$$`
- **Aplicación administrativa**: En el contexto administrativo, la prueba de Kruskal-Wallis puede ser aplicada para comparar el desempeño de diferentes sucursales o departamentos, ayudando a identificar diferencias significativas en el rendimiento.
- **Fuente principal**: Levin, R. I., & Rubin, D. S. (2013). Estadística para administración y economía. 10ª edición. (libro-estadistica-para-administracion-y-economia-levin-A15.txt (bloque 2))

### 2.3. prueba U de Mann-Whitney

- **Definición rigurosa**: La prueba U de Mann-Whitney, también conocida como prueba de Wilcoxon, es un método no paramétrico utilizado para comparar dos muestras independientes. Se basa en la comparación de rangos y se utiliza para determinar si las distribuciones de las dos muestras son idénticas.
- **Formulación matemática (LaTeX)**: `$$La estadística de prueba se calcula como $U = R - \frac{n_1(n_1 + 1)}{2}$, donde $R$ es la suma de rangos de una de las muestras y $n_1$ es el tamaño de esa muestra.$$`
- **Aplicación administrativa**: En administración, la prueba de Mann-Whitney puede ser utilizada para comparar el desempeño de dos grupos de empleados o dos métodos de producción, ayudando a identificar diferencias significativas en el rendimiento.
- **Fuente principal**: Anderson, D. R., Sweeney, D. J., & Williams, T. A. (2015). Estadística para negocios y economía. 11ª edición. (docente-1776-9c622af3e4c6.txt (bloque 2))

### 2.4. aproximación normal a la distribución del número de rachas R

- **Definición rigurosa**: La aproximación normal a la distribución del número de rachas R se utiliza cuando el tamaño de la muestra es suficientemente grande. Esta aproximación permite calcular la probabilidad de observar un número de rachas dado bajo la hipótesis nula de aleatoriedad.
- **Formulación matemática (LaTeX)**: `$$La distribución del número de rachas R se aproxima por una distribución normal con media $\mu_R = \frac{2n_1n_2}{n_1 + n_2} + 1$ y varianza $\sigma_R^2 = \frac{2n_1n_2(2n_1n_2 - n_1 - n_2)}{(n_1 + n_2)^2(n_1 + n_2 - 1)}$.$$`
- **Aplicación administrativa**: En la gestión administrativa, esta aproximación es útil para evaluar la aleatoriedad en grandes conjuntos de datos, como la secuencia de llegadas de clientes o la distribución de defectos en productos.
- **Fuente principal**: Anderson, D. R., Sweeney, D. J., & Williams, T. A. (2015). Estadística para negocios y economía. 11ª edición. (libro-estadistica-para-negocios-y-economia-anderson-sw-A15.txt (bloque 3))

### 2.5. prueba de rachas para aleatoriedad en quejas de circulación periodística

- **Definición rigurosa**: Esta prueba se aplica para evaluar si las quejas recibidas por una publicación periódica siguen un patrón aleatorio o si existen rachas significativas que indiquen un sesgo o patrón específico.
- **Formulación matemática (LaTeX)**: `$$Se utiliza la estadística de prueba de rachas $R$ y se compara con la distribución aproximada normal para determinar la significancia.$$`
- **Aplicación administrativa**: En la gestión de medios, esta prueba ayuda a identificar si las quejas de los lectores son aleatorias o si hay un patrón que requiera atención especial.
- **Fuente principal**: Wackerly, D., Mendenhall, W., & Scheaffer, R. L. (2014). Estadística matemática con aplicaciones. 7ª edición. (libro-estadistica-matematica-con-aplicaciones-wackerly-A15.txt (bloque 1))

### 2.6. prueba de rachas para patrones horarios de llegada de clientes en restaurante

- **Definición rigurosa**: Esta prueba se aplica para evaluar si la llegada de clientes a un restaurante sigue un patrón aleatorio a lo largo del tiempo o si existen rachas significativas que indiquen un patrón específico.
- **Formulación matemática (LaTeX)**: `$$Se utiliza la estadística de prueba de rachas $R$ y se compara con la distribución aproximada normal para determinar la significancia.$$`
- **Aplicación administrativa**: En la gestión de restaurantes, esta prueba ayuda a identificar si la llegada de clientes es aleatoria o si hay patrones horarios que puedan optimizar la planificación de recursos.
- **Fuente principal**: Levin, R. I., & Rubin, D. S. (2013). Estadística para administración y economía. 10ª edición. (libro-estadistica-para-administracion-y-economia-levin-A15.txt (bloque 4))

### 2.7. prueba de rachas en afluencia bancaria por sexo

- **Definición rigurosa**: Esta prueba se aplica para evaluar si la afluencia de clientes a una sucursal bancaria, clasificada por sexo, sigue un patrón aleatorio o si existen rachas significativas que indiquen un patrón específico.
- **Formulación matemática (LaTeX)**: `$$Se utiliza la estadística de prueba de rachas $R$ y se compara con la distribución aproximada normal para determinar la significancia.$$`
- **Aplicación administrativa**: En la gestión bancaria, esta prueba ayuda a identificar si la afluencia de clientes por sexo es aleatoria o si hay patrones que puedan influir en la planificación de servicios.
- **Fuente principal**: Wackerly, D., Mendenhall, W., & Scheaffer, R. L. (2014). Estadística matemática con aplicaciones. 7ª edición. (libro-estadistica-matematica-con-aplicaciones-wackerly-A15.txt (bloque 1))

### 2.8. prueba de rachas para detección de defectos agrupados en envíos de vidrio

- **Definición rigurosa**: Esta prueba se aplica para evaluar si los defectos en los envíos de vidrio siguen un patrón aleatorio o si existen rachas significativas que indiquen un agrupamiento de defectos.
- **Formulación matemática (LaTeX)**: `$$Se utiliza la estadística de prueba de rachas $R$ y se compara con la distribución aproximada normal para determinar la significancia.$$`
- **Aplicación administrativa**: En la gestión de calidad, esta prueba ayuda a identificar si los defectos en los productos son aleatorios o si hay patrones que indiquen problemas en el proceso de producción.
- **Fuente principal**: Wackerly, D., Mendenhall, W., & Scheaffer, R. L. (2014). Estadística matemática con aplicaciones. 7ª edición. (libro-estadistica-matematica-con-aplicaciones-wackerly-A15.txt (bloque 1))

### 2.9. prueba U de Mann-Whitney para evaluación del desempeño de enfermeras por universidad

- **Definición rigurosa**: Esta prueba se aplica para evaluar si el desempeño de las enfermeras, medido por sus calificaciones, difiere significativamente entre dos universidades.
- **Formulación matemática (LaTeX)**: `$$Se utiliza la estadística de prueba U de Mann-Whitney y se compara con la distribución aproximada normal para determinar la significancia.$$`
- **Aplicación administrativa**: En la gestión de recursos humanos en hospitales, esta prueba ayuda a identificar si las universidades de origen de las enfermeras influyen en su desempeño.
- **Fuente principal**: Levin, R. I., & Rubin, D. S. (2013). Estadística para administración y economía. 10ª edición. (docente-1776-9c622af3e4c6.txt (bloque 2))

## 3. Estructura Argumentativa en Tres Tiempos

### Tiempo 1: Introducción

La actividad académica se centra en la aplicación práctica de pruebas de hipótesis no paramétricas en el ámbito administrativo. Los estudiantes realizarán ejercicios individuales que involucran la prueba de rachas para evaluar la aleatoriedad en diferentes contextos operacionales y la aplicación de las pruebas de Kruskal-Wallis y Mann-Whitney para comparar múltiples muestras. Estas técnicas son esenciales para la toma de decisiones gerenciales basadas en datos no normalmente distribuidos, proporcionando una herramienta robusta para analizar y comparar datos en entornos complejos y variables. La aleatoriedad en los datos es un aspecto crítico en la gestión administrativa, ya que permite identificar patrones no aleatorios que pueden indicar ineficiencias o problemas de calidad. La prueba de rachas es una herramienta fundamental para evaluar la aleatoriedad en secuencias de datos, lo que es crucial en la gestión administrativa para identificar patrones no aleatorios que puedan indicar ineficiencias o problemas de calidad.

### Tiempo 2: Desarrollo — Base Conceptual y Articulación Aplicada

La prueba de rachas se basa en el conteo de rachas en una secuencia de datos y compara el número observado de rachas con el número esperado bajo la hipótesis nula de aleatoriedad. Esta comparación permite determinar si los datos siguen un patrón aleatorio o si existen rachas significativas que indiquen un sesgo o patrón específico. La prueba H de Kruskal-Wallis es una extensión de la prueba de Mann-Whitney y se utiliza para comparar más de dos muestras independientes, lo que es útil en la gestión administrativa para evaluar el desempeño de múltiples sucursales o departamentos. La prueba H de Kruskal-Wallis se basa en el análisis de rangos y permite determinar si existen diferencias significativas entre las medianas de las muestras. La prueba U de Mann-Whitney es un método no paramétrico utilizado para comparar dos muestras independientes, lo que es útil en la gestión administrativa para evaluar el desempeño de dos grupos de empleados o dos métodos de producción. La prueba U de Mann-Whitney se basa en la comparación de rangos y permite determinar si las distribuciones de las dos muestras son idénticas. La aproximación normal a la distribución del número de rachas R se utiliza cuando el tamaño de la muestra es suficientemente grande, lo que es útil en la gestión administrativa para evaluar la aleatoriedad en grandes conjuntos de datos. La distribución del número de rachas R se aproxima por una distribución normal con media y varianza específicas, lo que permite calcular la probabilidad de observar un número de rachas dado bajo la hipótesis nula de aleatoriedad.

Para resolver los ejercicios individuales, los estudiantes deben aplicar las pruebas de hipótesis no paramétricas de acuerdo con la consigna oficial. Los estudiantes deben calcular la estadística de prueba para cada ejercicio y compararla con la distribución aproximada normal para determinar la significancia. Los estudiantes deben interpretar los resultados y discutir las implicaciones gerenciales de sus hallazgos. Los estudiantes deben asegurarse de que sus reportes cumplan con los requisitos de formato y presentación establecidos por el docente.

### Tiempo 3: Conclusiones

La aplicación de pruebas de hipótesis no paramétricas en la gestión administrativa proporciona una herramienta robusta para analizar y comparar datos en entornos complejos y variables. La aleatoriedad en los datos es un aspecto crítico en la gestión administrativa, ya que permite identificar patrones no aleatorios que pueden indicar ineficiencias o problemas de calidad. La prueba de rachas, la prueba H de Kruskal-Wallis y la prueba U de Mann-Whitney son métodos no paramétricos útiles para evaluar la aleatoriedad y comparar múltiples muestras. La aproximación normal a la distribución del número de rachas R es útil para evaluar la aleatoriedad en grandes conjuntos de datos. Los estudiantes deben aplicar estos métodos de acuerdo con la consigna oficial y discutir las implicaciones gerenciales de sus hallazgos. La significancia estadística es un criterio fundamental para determinar si los resultados de una prueba de hipótesis son confiables y no se deben a la casualidad. En la gestión administrativa, la significancia estadística permite a los gerentes tomar decisiones informadas basadas en datos.

## 4. Fichas de Investigación y Casos Aplicados

### Caso/Ficha 1: Evaluación de la aleatoriedad en la llegada de clientes a un restaurante
- **Referencia**: Levin, R. I., & Rubin, D. S. (2013)
- **Problema administrativo**: Identificar si la llegada de clientes a un restaurante sigue un patrón aleatorio o si existen rachas significativas que indiquen un patrón específico.
- **Metodología estadística**: Prueba de rachas para evaluar la aleatoriedad en la secuencia de llegadas de clientes.
- **Hallazgos y decisión gerencial**: Los resultados indicaron que la llegada de clientes no seguía un patrón aleatorio, lo que llevó a la implementación de medidas para optimizar la planificación de recursos.

### Caso/Ficha 2: Comparación del desempeño de enfermeras por universidad
- **Referencia**: Levin, R. I., & Rubin, D. S. (2013)
- **Problema administrativo**: Determinar si el desempeño de las enfermeras, medido por sus calificaciones, difiere significativamente entre dos universidades.
- **Metodología estadística**: Prueba U de Mann-Whitney para comparar el desempeño de las enfermeras entre dos universidades.
- **Hallazgos y decisión gerencial**: Los resultados mostraron diferencias significativas en el desempeño de las enfermeras entre las dos universidades, lo que llevó a la revisión de los criterios de selección de personal.

### Caso/Ficha 3: Análisis de la aleatoriedad en defectos de envíos de vidrio
- **Referencia**: Wackerly, D., Mendenhall, W., & Scheaffer, R. L. (2014)
- **Problema administrativo**: Evaluar si los defectos en los envíos de vidrio siguen un patrón aleatorio o si existen rachas significativas que indiquen un agrupamiento de defectos.
- **Metodología estadística**: Prueba de rachas para detectar defectos agrupados en los envíos de vidrio.
- **Hallazgos y decisión gerencial**: Los resultados indicaron la presencia de rachas significativas, lo que llevó a la identificación de problemas en el proceso de producción y la implementación de medidas correctivas.

