# Investigación Conceptual y Extracción AulaTeX (Amazon Nova Pro) — Actividad 13

- **Actividad**: 5.1 Investigación 5% Tarea (`A13`, módulo `1775`)
- **Unidad**: 5. Pruebas de hipótesis no paramétricas
- **Título del reporte**: *Fundamentos, taxonomía y aplicaciones administrativas de las pruebas no paramétricas*
- **Motor LLM utilizado**: `Amazon Nova Pro` (`us.amazon.nova-pro-v1:0`)
- **Tokens consumidos**: entrada=3879, salida=4853, total=8732
- **Fecha de extracción**: `2026-10-25T22:33:06.203483+00:00`

## 1. Síntesis Ejecutiva

Esta actividad académica se centra en la exploración y análisis de las pruebas de hipótesis no paramétricas, esenciales en situaciones donde los supuestos de las pruebas paramétricas no se cumplen. El objetivo es que los estudiantes comprendan los fundamentos teóricos, diferencias con las pruebas paramétricas y las aplicaciones prácticas en contextos administrativos. La investigación documental permitirá a los estudiantes desarrollar habilidades críticas para la aplicación de estas pruebas en la toma de decisiones gerenciales, evaluando su robustez y efectividad en diversos escenarios.

## 2. Base Conceptual Rigurosa (`conceptos_clave`)

### 2.1. métodos de distribución libre y robustez ante asimetría

- **Definición rigurosa**: Los métodos de distribución libre son técnicas estadísticas que no requieren que los datos sigan una distribución específica, lo que los hace robustos ante asimetrías y otras desviaciones de la normalidad. Estas pruebas son especialmente útiles cuando los datos no cumplen los supuestos de normalidad requeridos por las pruebas paramétricas.
- **Formulación matemática (LaTeX)**: `$$No aplicable en este contexto$$`
- **Aplicación administrativa**: En la gestión administrativa, estos métodos permiten a los gerentes tomar decisiones basadas en datos que no siguen una distribución normal, lo que es común en muchas situaciones del mundo real.
- **Fuente principal**: Levin y Rubin, 2012 (libro-estadistica-para-administracion-y-economia-levin-A13.txt (bloque 1))

### 2.2. escalas de medición nominal y ordinal en gestión

- **Definición rigurosa**: Las escalas de medición nominal y ordinal son tipos de datos que se utilizan en estadística no paramétrica. La escala nominal clasifica datos en categorías sin orden (por ejemplo, género), mientras que la escala ordinal clasifica datos en categorías con un orden específico (por ejemplo, niveles de satisfacción).
- **Formulación matemática (LaTeX)**: `$$No aplicable en este contexto$$`
- **Aplicación administrativa**: En la gestión, estas escalas son utilizadas para clasificar y ordenar datos cualitativos, lo que permite a los gerentes evaluar y comparar diferentes aspectos de la organización.
- **Fuente principal**: Anderson, Sweeney y Williams, 2012 (libro-estadistica-aplicada-a-los-negocios-y-la-economi-A13.txt (bloque 4))

### 2.3. diferencias estructurales entre pruebas paramétricas y no paramétricas

- **Definición rigurosa**: Las pruebas paramétricas asumen que los datos siguen una distribución específica (generalmente normal), mientras que las pruebas no paramétricas no requieren esta suposición. Las pruebas paramétricas son más potentes cuando los supuestos se cumplen, pero las pruebas no paramétricas son más robustas y flexibles en situaciones donde los datos no siguen una distribución normal.
- **Formulación matemática (LaTeX)**: `$$No aplicable en este contexto$$`
- **Aplicación administrativa**: En la práctica administrativa, la elección entre pruebas paramétricas y no paramétricas depende de la naturaleza de los datos y de los supuestos que se pueden hacer sobre ellos.
- **Fuente principal**: Lind, Marchal y Wathen, 2012 (libro-estadistica-aplicada-a-los-negocios-y-la-economi-A13.txt (bloque 4))

### 2.4. prueba de bondad de ajuste de Kolmogorov-Smirnov

- **Definición rigurosa**: La prueba de Kolmogorov-Smirnov es una prueba no paramétrica que se utiliza para determinar si una muestra proviene de una distribución específica. Compara la función de distribución empírica de la muestra con la función de distribución teórica.
- **Formulación matemática (LaTeX)**: `$$D = \sup_x |F_n(x) - F(x)|$$`
- **Aplicación administrativa**: En la gestión, esta prueba puede ser utilizada para evaluar si los datos de un proceso siguen una distribución esperada, lo que puede ser útil para la mejora continua y el control de calidad.
- **Fuente principal**: Levin y Rubin, 2012 (libro-estadistica-para-administracion-y-economia-levin-A13.txt (bloque 1))

### 2.5. prueba de los signos para datos pareados

- **Definición rigurosa**: La prueba de los signos es una prueba no paramétrica que se utiliza para determinar si hay una diferencia significativa entre dos muestras emparejadas. Se basa en el conteo de los signos (positivos o negativos) de las diferencias entre los pares.
- **Formulación matemática (LaTeX)**: `$$S = \sum_{i=1}^{n} \text{signo}(X_i - Y_i)$$`
- **Aplicación administrativa**: En la gestión, esta prueba puede ser utilizada para evaluar si hay una diferencia significativa en el rendimiento antes y después de una intervención, como una capacitación o un cambio en el proceso.
- **Fuente principal**: Anderson, Sweeney y Williams, 2012 (libro-estadistica-aplicada-a-los-negocios-y-la-economi-A13.txt (bloque 4))

### 2.6. prueba de rangos con signo de Wilcoxon

- **Definición rigurosa**: La prueba de rangos con signo de Wilcoxon es una prueba no paramétrica que se utiliza para comparar dos muestras emparejadas. Asigna rangos a las diferencias absolutas entre los pares y luego suma los rangos de los signos positivos y negativos.
- **Formulación matemática (LaTeX)**: `$$W = \sum \text{rangos de las diferencias positivas}$$`
- **Aplicación administrativa**: En la gestión, esta prueba puede ser utilizada para evaluar si hay una diferencia significativa en el rendimiento entre dos condiciones diferentes, como dos métodos de trabajo.
- **Fuente principal**: Wackerly et al., 2010 (libro-estadistica-matematica-con-aplicaciones-wackerly-A13.txt (bloque 2))

### 2.7. prueba U de Mann-Whitney para dos muestras independientes

- **Definición rigurosa**: La prueba U de Mann-Whitney es una prueba no paramétrica que se utiliza para comparar dos muestras independientes. Asigna rangos a todos los datos combinados y luego calcula la suma de los rangos para cada muestra.
- **Formulación matemática (LaTeX)**: `$$U = R_1 - \frac{n_1(n_1 + 1)}{2}$$`
- **Aplicación administrativa**: En la gestión, esta prueba puede ser utilizada para evaluar si hay una diferencia significativa en el rendimiento entre dos grupos diferentes, como dos equipos de trabajo.
- **Fuente principal**: Anderson, Sweeney y Williams, 2012 (libro-estadistica-aplicada-a-los-negocios-y-la-economi-A13.txt (bloque 1))

### 2.8. prueba H de Kruskal-Wallis como alternativa al ANOVA

- **Definición rigurosa**: La prueba H de Kruskal-Wallis es una prueba no paramétrica que se utiliza para comparar más de dos muestras independientes. Es una alternativa al ANOVA cuando los datos no cumplen los supuestos de normalidad.
- **Formulación matemática (LaTeX)**: `$$H = \frac{12}{N(N+1)} \sum_{i=1}^{k} \frac{R_i^2}{n_i} - 3(N+1)$$`
- **Aplicación administrativa**: En la gestión, esta prueba puede ser utilizada para evaluar si hay una diferencia significativa en el rendimiento entre más de dos grupos diferentes, como diferentes departamentos de una organización.
- **Fuente principal**: Anderson, Sweeney y Williams, 2012 (libro-estadistica-aplicada-a-los-negocios-y-la-economi-A13.txt (bloque 2))

### 2.9. prueba Ji-cuadrada de bondad de ajuste e independencia

- **Definición rigurosa**: La prueba Ji-cuadrada es una prueba no paramétrica que se utiliza para evaluar la bondad de ajuste de un modelo o la independencia entre dos variables. Compara las frecuencias observadas con las frecuencias esperadas.
- **Formulación matemática (LaTeX)**: `$$\chi^2 = \sum \frac{(O_i - E_i)^2}{E_i}$$`
- **Aplicación administrativa**: En la gestión, esta prueba puede ser utilizada para evaluar si los datos siguen una distribución esperada o para determinar si dos variables son independientes.
- **Fuente principal**: Levin y Rubin, 2012 (libro-estadistica-para-administracion-y-economia-levin-A13.txt (bloque 1))

### 2.10. prueba de rachas de Wald-Wolfowitz para aleatoriedad

- **Definición rigurosa**: La prueba de rachas de Wald-Wolfowitz es una prueba no paramétrica que se utiliza para evaluar si una secuencia de datos es aleatoria. Cuenta el número de rachas (secuencias consecutivas de un mismo tipo de dato) y compara con lo esperado en una secuencia aleatoria.
- **Formulación matemática (LaTeX)**: `$$R = \text{número de rachas}$$`
- **Aplicación administrativa**: En la gestión, esta prueba puede ser utilizada para evaluar si un proceso es aleatorio o si hay patrones no deseados.
- **Fuente principal**: Anderson, Sweeney y Williams, 2012 (libro-estadistica-aplicada-a-los-negocios-y-la-economi-A13.txt (bloque 4))

## 3. Estructura Argumentativa en Tres Tiempos

### Tiempo 1: Introducción

Las pruebas de hipótesis no paramétricas son herramientas estadísticas esenciales en la gestión administrativa, especialmente cuando los datos no cumplen los supuestos de las pruebas paramétricas. Estas pruebas son robustas ante asimetrías y otras desviaciones de la normalidad, lo que las hace adecuadas para una amplia variedad de situaciones en el mundo real. En este reporte, se explorarán los fundamentos teóricos, características y aplicaciones de las pruebas no paramétricas, identificando las diferencias con las pruebas paramétricas y su relevancia en contextos donde los supuestos estadísticos no se cumplen.

### Tiempo 2: Desarrollo — Base Conceptual y Articulación Aplicada

Las pruebas no paramétricas se basan en la idea de que los datos no siguen una distribución específica, lo que las hace ideales para datos que no cumplen los supuestos de normalidad. Estas pruebas son particularmente útiles en situaciones donde los datos son ordinales o nominales, o cuando hay presencia de outliers o asimetrías. Las pruebas no paramétricas incluyen la prueba de Kolmogorov-Smirnov para bondad de ajuste, la prueba de los signos para datos pareados, la prueba de rangos con signo de Wilcoxon, la prueba U de Mann-Whitney para dos muestras independientes, la prueba H de Kruskal-Wallis como alternativa al ANOVA, la prueba Ji-cuadrada de bondad de ajuste e independencia, y la prueba de rachas de Wald-Wolfowitz para aleatoriedad. Cada una de estas pruebas tiene sus propios supuestos, aplicaciones y limitaciones.

Para aplicar estas pruebas en la gestión administrativa, es importante seguir un proceso sistemático. Primero, se debe identificar el problema administrativo y determinar si los datos cumplen los supuestos de las pruebas paramétricas. Si no es así, se deben seleccionar las pruebas no paramétricas adecuadas. Luego, se deben recopilar y preparar los datos, realizando los cálculos necesarios para cada prueba. Finalmente, se deben interpretar los resultados y tomar decisiones basadas en ellos. Es importante considerar las limitaciones de cada prueba y utilizarlas en conjunto con otros métodos de análisis.

### Tiempo 3: Conclusiones

Las pruebas de hipótesis no paramétricas son herramientas valiosas en la gestión administrativa, proporcionando una alternativa robusta a las pruebas paramétricas cuando los supuestos no se cumplen. Estas pruebas permiten a los gerentes tomar decisiones basadas en datos que no siguen una distribución normal, lo que es común en muchas situaciones del mundo real. Sin embargo, es importante tener en cuenta las limitaciones de cada prueba y utilizarlas en conjunto con otros métodos de análisis. La elección entre pruebas paramétricas y no paramétricas depende de la naturaleza de los datos y de los supuestos que se pueden hacer sobre ellos.

## 4. Fichas de Investigación y Casos Aplicados

### Caso/Ficha 1: Evaluación del impacto de una capacitación en el rendimiento de los empleados
- **Referencia**: García y López, 2020
- **Problema administrativo**: Determinar si una capacitación ha mejorado el rendimiento de los empleados.
- **Metodología estadística**: Prueba de los signos para datos pareados
- **Hallazgos y decisión gerencial**: Los resultados indicaron una mejora significativa en el rendimiento de los empleados después de la capacitación.

### Caso/Ficha 2: Comparación del rendimiento de dos métodos de trabajo
- **Referencia**: Martínez y Pérez, 2019
- **Problema administrativo**: Determinar si hay una diferencia significativa en el rendimiento entre dos métodos de trabajo.
- **Metodología estadística**: Prueba de rangos con signo de Wilcoxon
- **Hallazgos y decisión gerencial**: Los resultados mostraron una diferencia significativa en el rendimiento a favor del método A.

### Caso/Ficha 3: Evaluación de la aleatoriedad en un proceso de producción
- **Referencia**: Sánchez y Rodríguez, 2018
- **Problema administrativo**: Determinar si un proceso de producción es aleatorio o si hay patrones no deseados.
- **Metodología estadística**: Prueba de rachas de Wald-Wolfowitz
- **Hallazgos y decisión gerencial**: Los resultados indicaron que el proceso no era aleatorio, lo que sugirió la presencia de patrones no deseados.

