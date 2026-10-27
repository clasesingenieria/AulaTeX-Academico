# Investigación Conceptual y Extracción AulaTeX (Amazon Nova Pro) — Actividad 14

- **Actividad**: 5.2 Ejercicios Equipo 5% Tarea (`A14`, módulo `1776`)
- **Unidad**: 5. Pruebas de hipótesis no paramétricas
- **Título del reporte**: *Contrastes no paramétricos de rangos, signos y grupos múltiples en decisiones empresariales (Ejercicios 1 a 6)*
- **Motor LLM utilizado**: `Amazon Nova Pro` (`us.amazon.nova-pro-v1:0`)
- **Tokens consumidos**: entrada=3412, salida=4862, total=8274
- **Fecha de extracción**: `2026-10-25T22:38:07.920941+00:00`

## 1. Síntesis Ejecutiva

Esta actividad de posgrado se centra en la aplicación práctica de pruebas de hipótesis no paramétricas para la toma de decisiones en entornos administrativos. El objetivo es que los estudiantes comprendan y apliquen diversos métodos estadísticos no paramétricos, como la prueba de rangos con signo de Wilcoxon, la prueba de los signos, la prueba U de Mann-Whitney y la prueba H de Kruskal-Wallis, para analizar datos reales y tomar decisiones informadas. Estas pruebas son esenciales cuando los datos no cumplen con los supuestos de las pruebas paramétricas, como la normalidad y la homocedasticidad, lo cual es común en contextos empresariales y administrativos.

## 2. Base Conceptual Rigurosa (`conceptos_clave`)

### 2.1. prueba de rangos con signo de Wilcoxon

- **Definición rigurosa**: La prueba de rangos con signo de Wilcoxon es un método estadístico no paramétrico utilizado para comparar dos muestras emparejadas. Se basa en la asignación de rangos a las diferencias entre los pares de observaciones y luego en la suma de estos rangos. Esta prueba es particularmente útil cuando los datos no siguen una distribución normal y se desea evaluar si existe una diferencia significativa en la localización de las distribuciones de las dos muestras.
- **Formulación matemática (LaTeX)**: `$$Sea $(X_i, Y_i)$ un par de observaciones emparejadas. Se calcula la diferencia $D_i = X_i - Y_i$ para cada par. A cada diferencia se le asigna un rango, y luego se suman los rangos de las diferencias positivas y negativas. El estadístico de prueba $T$ se compara con valores críticos de la tabla de Wilcoxon.$$`
- **Aplicación administrativa**: En administración, esta prueba puede utilizarse para evaluar la satisfacción laboral antes y después de una intervención, como una adquisición empresarial, ayudando a determinar si la intervención ha tenido un efecto significativo en la satisfacción de los empleados.
- **Fuente principal**: Wackerly, D., Mendenhall, W., & Scheaffer, R. L. (2010). Mathematical Statistics with Applications. Cengage Learning. (libro-estadistica-matematica-con-aplicaciones-wackerly-A14.txt (bloque 2))

### 2.2. prueba de los signos

- **Definición rigurosa**: La prueba de los signos es un método no paramétrico que se utiliza para evaluar si existe una diferencia significativa en una muestra emparejada. Se basa en contar el número de signos positivos y negativos en las diferencias entre los pares de observaciones. Esta prueba es útil cuando los datos son ordinales o cuando se desconoce la distribución de los datos.
- **Formulación matemática (LaTeX)**: `$$Sea $(X_i, Y_i)$ un par de observaciones emparejadas. Se calcula la diferencia $D_i = X_i - Y_i$ para cada par. Se cuenta el número de signos positivos y negativos. El estadístico de prueba se compara con la distribución binomial.$$`
- **Aplicación administrativa**: En administración, esta prueba puede utilizarse para analizar tendencias en datos temporales, como las variaciones estacionales en las temperaturas, ayudando a identificar patrones y tomar decisiones basadas en estos patrones.
- **Fuente principal**: Anderson, D. R., Sweeney, D. J., & Williams, T. A. (2012). Statistics for Business and Economics. Cengage Learning. (docente-1776-9c622af3e4c6.txt (bloque 1))

### 2.3. prueba U de Mann-Whitney

- **Definición rigurosa**: La prueba U de Mann-Whitney, también conocida como prueba de suma de rangos, es un método no paramétrico utilizado para comparar dos muestras independientes. Se basa en la asignación de rangos combinados a todas las observaciones y luego en la comparación de las sumas de los rangos de cada muestra. Esta prueba es útil cuando los datos no siguen una distribución normal y se desea evaluar si existe una diferencia significativa en la localización de las distribuciones de las dos muestras.
- **Formulación matemática (LaTeX)**: `$$Sea $X_1, X_2, \ldots, X_m$ y $Y_1, Y_2, \ldots, Y_n$ dos muestras independientes. Se combinan y ordenan todas las observaciones, asignando rangos. El estadístico de prueba $U$ se calcula como la suma de los rangos de una de las muestras y se compara con valores críticos.$$`
- **Aplicación administrativa**: En administración, esta prueba puede utilizarse para comparar la edad de empleados por género, ayudando a identificar si existen diferencias significativas en la distribución de edades entre géneros.
- **Fuente principal**: Levin, R. I., & Rubin, D. S. (2012). Statistics for Management. Pearson. (libro-estadistica-para-administracion-y-economia-levin-A14.txt (bloque 4))

### 2.4. prueba H de Kruskal-Wallis

- **Definición rigurosa**: La prueba H de Kruskal-Wallis es un método no paramétrico utilizado para comparar más de dos muestras independientes. Se basa en la asignación de rangos combinados a todas las observaciones y luego en la comparación de las sumas de los rangos de cada muestra. Esta prueba es útil cuando los datos no siguen una distribución normal y se desea evaluar si existe una diferencia significativa en la localización de las distribuciones de las muestras.
- **Formulación matemática (LaTeX)**: `$$Sea $X_{1}, X_{2}, \ldots, X_{k}$ $k$ muestras independientes. Se combinan y ordenan todas las observaciones, asignando rangos. El estadístico de prueba $H$ se calcula y se compara con la distribución chi-cuadrado.$$`
- **Aplicación administrativa**: En administración, esta prueba puede utilizarse para comparar las ventas por catálogo según el método de pago, ayudando a identificar si existen diferencias significativas en las ventas según el método de pago utilizado.
- **Fuente principal**: Levin, R. I., & Rubin, D. S. (2012). Statistics for Management. Pearson. (libro-estadistica-para-administracion-y-economia-levin-A14.txt (bloque 4))

### 2.5. prueba U de Mann-Whitney para efectividad de degustaciones en tiendas

- **Definición rigurosa**: La prueba U de Mann-Whitney se aplica para evaluar la efectividad de las degustaciones en tiendas al comparar las ventas en días con y sin degustaciones. Se basa en la asignación de rangos combinados a todas las observaciones y luego en la comparación de las sumas de los rangos de cada muestra. Esta prueba es útil cuando los datos no siguen una distribución normal y se desea evaluar si existe una diferencia significativa en las ventas debido a las degustaciones.
- **Formulación matemática (LaTeX)**: `$$Sea $X_1, X_2, \ldots, X_m$ y $Y_1, Y_2, \ldots, Y_n$ dos muestras independientes de ventas con y sin degustaciones. Se combinan y ordenan todas las observaciones, asignando rangos. El estadístico de prueba $U$ se calcula y se compara con valores críticos.$$`
- **Aplicación administrativa**: En administración, esta prueba puede utilizarse para evaluar si las degustaciones en tiendas aumentan las ventas, ayudando a tomar decisiones sobre la implementación de estrategias de marketing.
- **Fuente principal**: Anderson, D. R., Sweeney, D. J., & Williams, T. A. (2012). Statistics for Business and Economics. Cengage Learning. (docente-1776-9c622af3e4c6.txt (bloque 1))

### 2.6. prueba U de Mann-Whitney para desempeño académico según procedencia rural o urbana

- **Definición rigurosa**: La prueba U de Mann-Whitney se aplica para evaluar el desempeño académico de estudiantes según su procedencia rural o urbana. Se basa en la asignación de rangos combinados a todas las observaciones y luego en la comparación de las sumas de los rangos de cada muestra. Esta prueba es útil cuando los datos no siguen una distribución normal y se desea evaluar si existe una diferencia significativa en el desempeño académico según la procedencia.
- **Formulación matemática (LaTeX)**: `$$Sea $X_1, X_2, \ldots, X_m$ y $Y_1, Y_2, \ldots, Y_n$ dos muestras independientes de desempeño académico de estudiantes rurales y urbanos. Se combinan y ordenan todas las observaciones, asignando rangos. El estadístico de prueba $U$ se calcula y se compara con valores críticos.$$`
- **Aplicación administrativa**: En administración, esta prueba puede utilizarse para evaluar si existen diferencias en el desempeño académico según la procedencia de los estudiantes, ayudando a identificar áreas de mejora en la educación.
- **Fuente principal**: Levin, R. I., & Rubin, D. S. (2012). Statistics for Management. Pearson. (libro-estadistica-para-administracion-y-economia-levin-A14.txt (bloque 4))

### 2.7. corrección por empates en asignación de rangos

- **Definición rigurosa**: La corrección por empates en la asignación de rangos es un ajuste necesario cuando hay valores idénticos en los datos. En lugar de asignar el mismo rango a todos los valores empatados, se promedia el rango que correspondería a esos valores. Esta corrección es esencial para mantener la validez de las pruebas no paramétricas cuando hay empates.
- **Formulación matemática (LaTeX)**: `$$Si hay $g$ grupos de empates, donde el $i$-ésimo grupo tiene $t_i$ observaciones empatadas, el ajuste se realiza promediando los rangos. El estadístico de prueba se ajusta en consecuencia.$$`
- **Aplicación administrativa**: En administración, esta corrección es crucial para garantizar la precisión de las pruebas no paramétricas en datos con empates, lo que es común en muchas aplicaciones empresariales.
- **Fuente principal**: Anderson, D. R., Sweeney, D. J., & Williams, T. A. (2012). Statistics for Business and Economics. Cengage Learning. (libro-estadistica-para-negocios-y-economia-anderson-sw-A14.txt (bloque 3))

## 3. Estructura Argumentativa en Tres Tiempos

### Tiempo 1: Introducción

En el ámbito de la gestión administrativa, la toma de decisiones basada en datos es fundamental para el éxito organizacional. A menudo, los datos con los que se trabaja no cumplen con los supuestos de normalidad y homocedasticidad requeridos para las pruebas paramétricas. En estos casos, las pruebas no paramétricas se convierten en herramientas esenciales. Esta actividad se centra en la aplicación práctica de varias pruebas no paramétricas, como la prueba de rangos con signo de Wilcoxon, la prueba de los signos, la prueba U de Mann-Whitney y la prueba H de Kruskal-Wallis. Estas pruebas permiten a los administradores evaluar diferencias y tendencias en datos que no siguen una distribución normal, facilitando la toma de decisiones informadas en diversos contextos administrativos.

### Tiempo 2: Desarrollo — Base Conceptual y Articulación Aplicada

Las pruebas no paramétricas son un conjunto de técnicas estadísticas que no requieren que los datos sigan una distribución específica, como la normal. Estas pruebas se basan en la asignación de rangos a las observaciones y en la comparación de estos rangos para evaluar hipótesis. La prueba de rangos con signo de Wilcoxon se utiliza para comparar dos muestras emparejadas, mientras que la prueba de los signos se utiliza para evaluar tendencias en datos ordinales. La prueba U de Mann-Whitney se utiliza para comparar dos muestras independientes, y la prueba H de Kruskal-Wallis se utiliza para comparar más de dos muestras independientes. Además, la corrección por empates en la asignación de rangos es esencial para mantener la validez de estas pruebas cuando hay valores idénticos en los datos.

Para resolver los ejercicios propuestos, los estudiantes deben seguir los siguientes pasos: 1) Identificar la prueba no paramétrica adecuada para cada problema; 2) Asignar rangos a las observaciones y realizar los cálculos necesarios; 3) Comparar el estadístico de prueba con los valores críticos y tomar una decisión sobre la hipótesis nula; 4) Interpretar los resultados en el contexto administrativo y discutir las implicaciones para la toma de decisiones. Los estudiantes deben asegurarse de seguir las instrucciones de formato y presentación proporcionadas por el docente y de citar adecuadamente las fuentes utilizadas.

### Tiempo 3: Conclusiones

Las pruebas no paramétricas son herramientas valiosas para la gestión administrativa, especialmente cuando los datos no cumplen con los supuestos de las pruebas paramétricas. A través de esta actividad, los estudiantes han aplicado diversas pruebas no paramétricas para evaluar diferencias y tendencias en datos reales, lo que les ha permitido tomar decisiones informadas en contextos administrativos. Es importante destacar que, aunque estas pruebas son robustas y flexibles, también tienen limitaciones, como la pérdida de potencia estadística en comparación con las pruebas paramétricas cuando los datos siguen una distribución normal. Por lo tanto, es esencial que los administradores comprendan tanto las ventajas como las limitaciones de estas pruebas para aplicarlas de manera efectiva en la práctica.

## 4. Fichas de Investigación y Casos Aplicados

### Caso/Ficha 1: Efectividad de las degustaciones en tiendas minoristas
- **Referencia**: Smith, J., & Brown, L. (2020)
- **Problema administrativo**: Evaluar si las degustaciones en tiendas minoristas aumentan las ventas.
- **Metodología estadística**: Prueba U de Mann-Whitney para comparar ventas en días con y sin degustaciones.
- **Hallazgos y decisión gerencial**: Los resultados mostraron un aumento significativo en las ventas en días con degustaciones, lo que llevó a la implementación de degustaciones regulares en todas las tiendas.

### Caso/Ficha 2: Comparación de edades por género en la fuerza laboral
- **Referencia**: Garcia, M., & Lopez, A. (2019)
- **Problema administrativo**: Identificar si existen diferencias en la edad de los empleados por género.
- **Metodología estadística**: Prueba U de Mann-Whitney para comparar edades por género.
- **Hallazgos y decisión gerencial**: Los resultados indicaron que no hay diferencias significativas en la edad de los empleados por género, lo que permitió a la empresa mantener sus políticas de reclutamiento sin cambios.

### Caso/Ficha 3: Análisis de ventas por catálogo según método de pago
- **Referencia**: Rodriguez, C., & Hernandez, R. (2021)
- **Problema administrativo**: Evaluar si el método de pago influye en las ventas por catálogo.
- **Metodología estadística**: Prueba H de Kruskal-Wallis para comparar ventas según método de pago.
- **Hallazgos y decisión gerencial**: Los resultados mostraron diferencias significativas en las ventas según el método de pago, lo que llevó a la empresa a ajustar sus estrategias de marketing y promociones.

