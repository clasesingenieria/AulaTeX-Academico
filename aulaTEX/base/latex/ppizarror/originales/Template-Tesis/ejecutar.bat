@REM ## Contenido

@REM 1. Introducción
@REM     1.1 La Estructura y Componentes de un Sistema de Control Realimentado
@REM     - Los componentes de un sistema de control realimentado
@REM     - Las señales en un sistema de control realimentado
@REM     1.2 ¿Por qué Realimentación?
@REM     1.3 Elementos a Considerar por Diseñadores de Sistemas de Control Realimentado
@REM     - Especificaciones de diseño
@REM     - Incertidumbre de los parámetros de la planta
@REM     - Saturación de la planta
@REM     - Amplificación del ruido del sensor
@REM     1.4 Contenido del Libro

@REM 2. Propiedades Básicas y Diseño de Sistemas de Realimentación SISO
@REM     2.1 Definiciones Introductoras
@REM     2.2 Definición Matemática de Realimentación
@REM     - 2.2.1 El Origen de la Teoría de Realimentación
@REM     - 2.2.2 Razón de Retorno, Diferencia de Retorno e Invariancia de su Polinomio Numerador
@REM     - 2.2.3 Estabilidad Asintótica y Estabilidad Interna
@REM       - Estabilidad asintótica
@REM     2.3 Definición de Algunos Problemas de Control de Realimentación Usando la Realimentación Básica
@REM     - 2.3.1 Consideraciones de Estabilidad Asintótica y Relativa en el Plano-$s$ y en el Dominio-$\omega$
@REM       - Criterio de estabilidad de Nyquist
@REM       - Estabilidad relativa (márgenes de ganancia y fase)
@REM     - 2.3.2 Diseño en el Dominio de la Frecuencia Usando Técnicas de Bode
@REM       - Magnitud logarítmica
@REM       - Decibelio
@REM       - Gráficos de Bode
@REM     - 2.3.3 El Gráfico de Nichols y sus Características Especiales
@REM       - Contornos de ganancia constante de realimentación unitaria en el gráfico de Nichols
@REM       - Ubicación del punto crítico de estabilidad e identificación de márgenes de fase y ganancia
@REM       - Gráfico de Nichols invertido para análisis de perturbaciones y diseño
@REM       - Superioridad del diseño basado en gráficos de Bode y en el gráfico de Nichols sobre el diseño basado en el gráfico de Nyquist en el plano complejo
@REM     - 2.3.4 Distinción entre Sistemas de Realimentación de Uno y Dos Grados de Libertad
@REM     - 2.3.5 Diseño en el Dominio de la Frecuencia de Sistemas de Realimentación ODOF
@REM       - Frecuencia de cruce $\omega_{co}$ y frecuencia GM $\omega_{GM}$
@REM       - Estabilidad condicional
@REM       - Desempeño de bucle cerrado y ancho de banda, $\omega_{-3dB}$
@REM       - Rechazo de perturbaciones
@REM       - Conformación del bucle
@REM       - Limitaciones de sistemas de realimentación de un grado de libertad
@REM     - 2.3.6 Diseño en el Dominio de la Frecuencia de Sistemas TDOF
@REM     2.4 Compensaciones de Diseño en Sistemas de Realimentación
@REM     - 2.4.1 El Problema de Amplificación del Ruido del Sensor en Sistemas de Realimentación
@REM     - 2.4.2 Cálculo RMS de $|T_m(j\omega)|$
@REM     - 2.4.3 Optimización de la Función de Transmisión del Bucle $L(j\omega)$
@REM     2.5 Conformación del Bucle Basada en Optimización de Norma $H_\infty$
@REM     - 2.5.1 Definición de las Normas $H_\infty$ y $H_2$
@REM       - Interpretación de las normas $H_2$ y $H_\infty$ en sistemas físicos reales
@REM     - 2.5.2 Requisitos de Desempeño de Estabilidad Relativa Básica
@REM       - Márgenes de ganancia y fase en términos de $|T_1(j\omega)|_{max}$
@REM       - Márgenes de ganancia y fase en términos de $|S(j\omega)|_{max}$
@REM     - 2.5.3 Sensibilidad Ponderada
@REM     - 2.5.4 Sensibilidad Mixta
@REM     - 2.5.5 El Problema Estándar del Regulador $H_\infty$
@REM     - 2.5.6 Selección de Función de Ponderación
@REM     - 2.5.7 Solución de Norma $H_\infty$ del Problema de Sensibilidad Mixta
@REM     2.6 Conformación del Bucle con Norma $H_\infty$ Clásica versus Moderna
@REM     2.7 Resumen

@REM 3. Temas Prácticos en el Diseño de Sistemas de Realimentación SISO
@REM     3.1 Introducción
@REM     3.2 Traducciones del Dominio de Frecuencia y Dominio-$s$ al Dominio del Tiempo
@REM     - 3.2.1 Traducción del Dominio-$s$ al Dominio del Tiempo
@REM       - El enfoque del polo dominante
@REM       - Algunas definiciones de respuesta al escalón
@REM     - 3.2.2 Traducción del Dominio de Frecuencia al Dominio del Tiempo: Traducción de $R(\omega)$ a $y(t)$
@REM       - Evaluación de la respuesta al impulso en el tiempo a partir de una parte estándar trapezoidal real
@REM       - Evaluación de la respuesta al escalón unitario en el tiempo a partir de una parte estándar trapezoidal real
@REM       - Sobrepaso de respuesta al escalón en el tiempo evaluado a partir de características de respuesta en frecuencia
@REM     - 3.2.3 Traducción del Dominio de Frecuencia al Dominio del Tiempo: Traducción de $|T(j\omega)|$ a $y(t)$
@REM       - Retardo de tiempo debido a polos ubicados en frecuencias altas
@REM       - Tiempo de subida $t_r$
@REM     3.3 Características del Dominio del Tiempo de Entrada-Salida de Sistemas de Realimentación SISO NMP
@REM     3.4 $L(j\omega)$ Óptimo para Sistemas de Realimentación de Fase Mínima
@REM     - 3.4.1 Formulación del Problema
@REM     - 3.4.2 La Característica de Bode Ideal y su Derivación
@REM       - Cálculo de $\omega_1$
@REM       - Cálculo de $\omega_2$ (primer enfoque)
@REM       - Cálculo de $\omega_2$ (segundo enfoque)
@REM     - 3.4.3 Optimización de $L(j\omega)$ para Sistemas Condicionalmente Estables
@REM       - Beneficios de la realimentación y el número de integradores en $s=0$
@REM       - Optimización de la función de transmisión del bucle
@REM     3.5 Limitaciones en $L(j\omega)$ incluyendo polos o ceros en el semiplano derecho
@REM     - 3.5.1 Limitaciones en la Función de Sensibilidad $S(j\omega)$ para Sistemas de Realimentación con Polos RHP
@REM     - 3.5.2 Limitaciones de Ancho de Banda Debidas a Ceros RHP, Máximo $\omega_{co}$ Alcanzable
@REM       - Formulación del problema
@REM       - Cálculo de relaciones entre margen de ganancia, margen de fase y $\omega_{co}$
@REM     - 3.5.3 Aproximación NMP Cero Equivalente a Múltiples Ceros NMP
@REM     3.6 Limitaciones en $L(j\omega)$ Inestable - Mínimo $\omega_{co}$ Alcanzable
@REM     - 3.6.1 Introducción
@REM     - 3.6.2 Relaciones Funcionales
@REM     - 3.6.3 Aplicación de los Resultados en Problemas Prácticos
@REM     - 3.6.4 Aproximación de Polo RHP Equivalente a Varios Polos RHP
@REM     3.7 Estabilización
@REM     - 3.7.1 Introducción
@REM     - 3.7.2 Plantas Fuertemente Estabilizables
@REM     - 3.7.3 Parametrización del Controlador Estabilizante: Planta Estable
@REM     - 3.7.4 Parametrización del Controlador Estabilizante: Planta Inestable
@REM       - Factorización coprima
@REM       - Parametrización del controlador estabilizante
@REM     3.8 Un Procedimiento de Diseño para Maximizar Márgenes de Ganancia y Fase de una Clase de Plantas Inestables-NMP
@REM     - 3.8.1 Formulación del Problema
@REM     - 3.8.2 Solución Básica del Problema
@REM     3.9 Limitación en Sistemas de Realimentación Incluyendo una Planta Inestable-NMP
@REM     - 3.9.1 Reformulación del Problema de Diseño
@REM     - 3.9.2 Planta con un Polo Inestable Precediendo un Cero NMP
@REM     3.10 Resumen

@REM 4. Síntesis de Sistemas de Realimentación LTI Inciertos SISO
@REM     4.1 Introducción
@REM     4.2 Planteamiento del Problema de Realimentación de Planta Incierta
@REM     - Especificaciones de seguimiento
@REM     - Especificaciones de rechazo de perturbaciones
@REM     - Picos en las ganancias de funciones de transferencia de rechazo de perturbaciones
@REM     4.3 Una Técnica de Diseño para Plantas LTI Inciertas de Fase Mínima
@REM     - 4.3.1 Paso 1: Traducción de Tolerancias del Dominio del Tiempo al Dominio de Frecuencia
@REM       - Traducción directa del dominio del tiempo al dominio de frecuencia
@REM       - Traducción del dominio del tiempo al dominio de frecuencia vía dominio-$s$
@REM     - 4.3.2 Paso 2: Preparación de Plantillas para la Planta Incierta
@REM     - 4.3.3 Paso 3: Derivación de Límites en la Transmisión del Bucle $L_n(j\omega)$ en el Gráfico de Nichols
@REM       - Límites en $L_n(j\omega)$ para satisfacer especificaciones de sensibilidad de seguimiento (entrada-salida)
@REM       - Límites en $L_n(j\omega)$ para satisfacer especificaciones de rechazo de perturbaciones
@REM       - Límites en $L_n(j\omega)$ para satisfacer máximo pico en $|T_1(j\omega)|$
@REM       - Límites combinados para seguimiento y rechazo de perturbaciones
@REM     - 4.3.4 Especificaciones y Diseño
@REM     - 4.3.5 Definición y propiedades de $L(j\omega)$ óptimo
@REM     - 4.3.6 Paso 6: Diseño del Prefiltro $F(s)$ para Lograr Especificaciones de $|T(j\omega)|$
@REM     - 4.3.7 Paso 7: Evaluación del Diseño
@REM     4.4 Técnica de Diseño para Plantas Inciertas Inestables
@REM     4.5 Técnica de Diseño para Plantas Inciertas NMP
@REM     - Límites en $L(j\omega)$ en el gráfico de Nichols para sistemas NMP
@REM     4.6 Técnica de Diseño para Plantas con Retardos de Tiempo Puros
@REM     4.7 Técnica de Diseño para Sistemas de Realimentación de Datos Muestreados con Plantas LTI Inciertas
@REM     - 4.7.1 Diseño de Sistemas de Realimentación de Datos Muestreados en el Dominio de Frecuencia
@REM     - 4.7.2 Traducción del Tiempo al Dominio de Frecuencia para Sistemas de Datos Muestreados
@REM     - 4.7.3 Técnica de Síntesis para Sistemas de Realimentación de Datos Muestreados con Plantas Inciertas
@REM     4.8 Diseño de Sistemas de Realimentación LTI Inciertos Continuos por Optimización de Norma $H_\infty$
@REM     - 4.8.1 Introducción
@REM     - 4.8.2 Estabilidad robusta
@REM     - 4.8.3 Modelado de Incertidumbre de la Planta
@REM       - Modelo de incertidumbre multiplicativa
@REM       - Modelo de incertidumbre multiplicativa inversa
@REM       - Modelo de incertidumbre aditiva
@REM       - Modelo de incertidumbre aditiva inversa
@REM     - 4.8.4 Estabilidad Robusta para Diferentes Tipos de Modelos de Incertidumbre de la Planta
@REM     - 4.8.5 Desempeño Robusto
@REM       - Derivación algebraica
@REM       - Derivación gráfica
@REM       - Restricciones de diseño algebraicas
@REM       - Diseño para especificaciones de desempeño robusto
@REM     - 4.8.6 Optimización de Norma $H_\infty$ Utilizada en Diseño de Estructuras de Sistemas de Realimentación TDOF
@REM     - 4.8.7 Comparación entre Diseños de Control "Clásico" y "$H_\infty$"
@REM     4.9 Resumen

@REM 5. Sistemas de Realimentación Inciertos de Entrada Simple/Múltiple Salida
@REM     5.1 Introducción
@REM     5.2 Planteamiento del Problema
@REM     - 5.2.1 Filosofía de Diseño
@REM     - 5.2.2 Límites en $L_2$
@REM       - Derivación de límites en $L_2$ en el rango de frecuencia $R_J$, $\omega > \omega_a$
@REM       - Límites universales en $L_2(j\omega)$ en el rango de frecuencia $R_1$, $\omega > \omega$
@REM       - Límites en $L_2$ en el rango de frecuencia $R_2$, $\omega > \omega > \omega_1$
@REM       - Límites en $L_2$ en el rango de frecuencia $R_3$, $\omega < \omega_h$
@REM     - 5.2.3 El Problema de Amplificación del Ruido del Sensor
@REM       - Derivación de red de control
@REM     5.3 Extensión a Tres Bucles

@REM 6. Sistemas Robustos de Realimentación MIMO Resueltos con Técnicas de Diseño Basadas en Nyquist/Bode
@REM     6.1 Introducción
@REM     - 6.1.1 Definiciones Introductorias para Sistemas de Realimentación MIMO
@REM     6.2 Diseño de Sistemas de Realimentación MIMO con Plantas Ciertas
@REM     - 6.2.1 Complejidad del Problema del Sistema de Realimentación $n \times n$
@REM     - 6.2.2 Diseño por Diagonalización Directa de la Matriz de Función de Transferencia en Bucle Abierto
@REM     - 6.2.3 No Interacción por Controlador Basado en Inverso
@REM     - 6.2.4 Técnica de Cierre Secuencial de Bucles
@REM     - 6.2.5 Teorema de Estabilidad de Nyquist Generalizado
@REM       - Funciones de transferencia características y funciones de vector propio correspondientes
@REM       - Loci características
@REM       - Adaptación del criterio de estabilidad de Nyquist a sistemas MIMO
@REM     - 6.2.6 El Método de Diseño del Locus Característico
@REM     - 6.2.7 Estabilidad Interna en Sistemas de Realimentación MIMO
@REM       - Buen planteamiento de bucles de realimentación
@REM     - 6.2.8 Parametrización-$Q$
@REM       - Parametrización-$Q$: plantas estables
@REM       - Parametrización-$Q$: plantas inestables
@REM     6.3 Sistemas de Realimentación MIMO Inciertos, Enfoque Clásico-Planteamiento del Problema
@REM     - 6.3.1 Complejidad del Problema del Sistema de Realimentación $n \times n$
@REM     - 6.3.2 Derivación de una Técnica de Síntesis Basada en QFT
@REM     - 6.3.3 El Problema de Diseño del Sistema de Realimentación Incierto $2 \times 2$
@REM       - Modificación de las tolerancias
@REM       - Restricciones en frecuencias altas
@REM       - El caso general interactuante
@REM     - 6.3.4 El Problema de Diseño del Sistema de Realimentación $3 \times 3$
@REM     6.4 Resumen

@REM 7. Introducción a Técnicas de Diseño en el Marco del Espacio de Estados
@REM     7.1 Introducción
@REM     7.2 Control de Realimentación MIMO en el Marco del Espacio de Estados
@REM     7.3 El Problema Regulador Lineal-Cuadrático (LQR)
@REM     - 7.3.1 El Caso General
@REM       - Solución de la ecuación de Riccati
@REM     - 7.3.2 El Problema LQR en Estado Estacionario
@REM       - Controlabilidad
@REM       - Estabilizabilidad
@REM       - Observabilidad
@REM       - Detectabilidad
@REM     - 7.3.3 Selección de las Matrices $\mathbf{Q}$, $\mathbf{R}$ y $\mathbf{M}$
@REM     - 7.3.4 Técnicas de Diseño LQR Orientadas al Seguimiento de Modelo
@REM       - Seguimiento de modelo implícito
@REM       - Seguimiento de modelo explícito
@REM     - 7.3.5 Caracterización en el Dominio de Frecuencia de la Optimalidad en Diseño Orientado LQR
@REM       - Desigualdad de Kalman
@REM     - 7.3.6 Márgenes de Ganancia y Fase para Sistemas de Realimentación Diseñados con LQR Óptimo
@REM     7.4 El Problema Lineal-Cuadrático-Gaussiano (LQG)
@REM     - 7.4.1 El Problema del Estimador de Estado
@REM     - 7.4.2 Filtro de Kalman-Bucy
@REM     - 7.4.3 El Principio de Separación y la Solución del Problema LQG
@REM     - 7.4.4 Recuperación de Transferencia de Bucle (LTR)
@REM     7.5 Resumen

@REM 8. Sistemas Robustos de Realimentación MIMO Resueltos con Técnica de Optimización de Norma $H_\infty$
@REM     8.1 Introducción
@REM     8.2 Valores Singulares y su Uso en Sistemas de Realimentación MIMO
@REM     - 8.2.1 Valores Singulares como Medio para Expresar el Tamaño de la Matriz de Función de Transferencia
@REM       - Valores singulares
@REM       - Ganancias principales
@REM       - Descomposición de valor singular de una matriz
@REM     - 8.2.2 Valores Singulares como Medio para Definir Desempeño en Sistemas de Realimentación MIMO
@REM     8.3 Solución del Problema Estándar del Regulador $H_\infty$
@REM     - 8.3.1 Introducción
@REM       - Definición de la planta generalizada
@REM       - Realización en espacio de estados de la planta generalizada
@REM     - 8.3.2 Algoritmos para la Solución del Problema de Control Estándar $H_\infty$
@REM       - Formulación general del problema de control
@REM       - Suposiciones en $\mathbf{M}(s)$ para viabilidad del controlador óptimo
@REM       - Interpretación de supuestos restrictivos en $\mathbf{M}(s)$
@REM       - Solución de un algoritmo de optimización $H_\infty$
@REM       - Iteración-$\gamma$
@REM     - 8.3.3 Conformación del Bucle de Sistemas de Control de Realimentación MIMO con Plantas Fijas y Conocidas
@REM     8.4 Incertidumbre, Estabilidad Robusta y Desempeño en Sistemas de Realimentación MIMO
@REM     - 8.4.1 Introducción
@REM     - 8.4.2 Modelado de Incertidumbre de Plantas MIMO
@REM       - Modelado de perturbación multiplicativa
@REM       - Modelado de incertidumbre multiplicativa de salida
@REM       - Modelado de incertidumbre multiplicativa de entrada
@REM       - Modelado de incertidumbre multiplicativa inversa
@REM       - Modelado de perturbación aditiva
@REM     - 8.4.3 Consideraciones de Estabilidad y el Teorema de Ganancia Pequeña
@REM       - Teorema de ganancia pequeña
@REM     - 8.4.4 Estabilidad Robusta para Sistemas de Realimentación MIMO Inciertos
@REM       - Condiciones para estabilidad robusta con modelado de incertidumbre multiplicativa de salida
@REM     - 8.4.5 Desempeño Robusto de Sistemas de Realimentación MIMO Inciertos
@REM     8.5 Diseño de Sistemas de Realimentación MIMO Inciertos TDOF
@REM     - 8.5.1 Introducción
@REM     - 8.5.2 Procedimiento de Diseño para el Sistema de Realimentación MIMO Incierto TDOF
@REM     8.6 Resumen

@REM Apéndice A. Gráficos de Flujo de Señales
@REM    - A.1 Introducción
@REM    - A.2 Definiciones para Gráficos de Flujo de Señales
@REM    - A.3 Fórmula de Ganancia para Gráficos de Flujo de Señales

@REM Apéndice B. Antecedentes Matemáticos Relacionados con MIMO y Análisis y Diseño $H_\infty$
@REM   -  B.1 Introducción
@REM   -  B.2 Normas Algebraicas y Vectoriales
@REM         - B.2.1 Funciones Escalares del Dominio del Tiempo
@REM         - B.2.2 Funciones Escalares del Sistema
@REM         - B.2.3 Normas Vectoriales
@REM   -  B.3 Normas de Matriz
@REM         - B.3.1 Valores Singulares y Ganancias Principales de Matrices de Función de Transferencia
@REM             - Descomposición de valor singular de una matriz
@REM             - Definición de normas de matriz
@REM         - B.3.2 Desigualdades de Valor Singular
@REM   -  B.4 Formulación del Espacio de Estados de Sistemas Lineales
@REM         - B.4.1 Formulación en Espacio de Estados
@REM         - B.4.2 Realización en Espacio de Estados y Realización Mínima
@REM         - B.4.3 Propiedades Básicas y Conceptos de Teoría del Espacio de Estados
@REM             - Controlabilidad
@REM             - Observabilidad
@REM             - Estabilización asintótica por retroalimentación de estado
@REM             - Modos ocultos
@REM         - B.4.4 Polinomios Característicos en Sistemas de Control de Realimentación
@REM   -  B.5 Valores Propios y Vectores Propios de Matrices de Función de Transferencia
@REM   -  B.6 Transformación Lineal Fractional (LFT)

@REM Apéndice C. Redes de Control para Conformación del Bucle
@REM    - C.1 Introducción
@REM    - C.2 Respuesta en Frecuencia de un Polo (cero) Real
@REM    - C.3 Respuesta en Frecuencia de un Polo (cero) Complejo
@REM    - C.4 Respuesta en Frecuencia de una Red de Control Adelanto-Atraso
@REM    - C.5 Respuesta en Frecuencia de una Red de Control Adelanto-Atraso-Atraso-Adelanto
@REM    - C.6 El Gráfico de Nichols
@REM    - C.7 El Gráfico de Nichols Invertido

@REM Apéndice D. Hechos Acerca de Transformadas de Fourier y Laplace
@REM    - D.1 Introducción
@REM    - D.2 Definiciones y Algunas Propiedades Generales de las Transformadas de Fourier
@REM         - Funciones de tiempo real
@REM         - Funciones de tiempo causal
@REM    - D.3 Definiciones y Algunas Propiedades Generales de las Transformadas de Laplace
@REM    - D.4 Solución de Ecuaciones Diferenciales Lineales
@REM         - Teorema de diferenciación
@REM         - Teorema de integración
@REM    - D.5 Teoremas de Valor Inicial y Final
@REM    - D.6 Teorema de Convolución de Tiempo
@REM    - D.7 Teorema de Convolución de Frecuencia
@REM    - D.8 Fórmula de Parseval

@REM Apéndice E. Fórmulas de Bode y Relaciones de Transformadas
@REM    - E.1 Introducción
@REM    - E.2 Definiciones Preliminares y Hechos
@REM    - E.3 Algunas Restricciones en Función de Transmisión Física en Frecuencias Reales
@REM         - E.3.1 Teoremas de Integral de Cauchy
@REM         - E.3.2 Integral de la Función de Sensibilidad
@REM         - E.3.3 Integral de Fase
@REM    - E.4 Fórmulas que Relacionan las Partes Real e Imaginaria de Funciones de Transmisión
@REM         - E.4.1 Características de Fase Correspondientes a una Característica de Atenuación Prescrita
@REM             - Características de fase correspondientes a una característica de atenuación de pendiente constante
@REM             - Las características de pendiente constante semi-infinitas
@REM         - E.4.2 Características de Atenuación Correspondientes a una Característica de Fase Prescrita

@echo off
chcp 65001 > nul

@REM Vamoss a crear un archivo por cada capítulo del libro, con el mismo nombre que el título del capítulo, pero sin espacios ni caracteres especiales, y con extensión .tex. Cada archivo contendrá el contenido del capítulo correspondiente.

echo 1. Introducción > Capitulo1_Introduccion.tex
echo 2. Propiedades Básicas y Diseño de Sistemas de Realimentación SISO >> Capitulo2_PropiedadesBasicasYDisenoSistemasRealimentacionSISO.tex
echo 3. Temas Prácticos en el Diseño de Sistemas de Realimentación SISO >> Capitulo3_TemasPracticosDisenoSistemasRealimentacionSISO.tex
echo 4. Síntesis de Sistemas de Realimentación LTI Inciertos SISO >> Capitulo4_SintesisSistemasRealimentacionLTIInciertosSISO.tex
echo 5. Sistemas de Realimentación Inciertos de Entrada Simple/Múltiple Salida >> Capitulo5_SistemasRealimentacionInciertosEntradaSimpleMultipleSalida.tex
echo 6. Sistemas Robustos de Realimentación MIMO Resueltos con Técnicas de Diseño Basadas en Nyquist/Bode >> Capitulo6_SistemasRobustosRealimentacionMIMOResueltosTecnicasDisenoBasadasNyquistBode.tex
echo 7. Introducción a Técnicas de Diseño en el Marco del Espacio de Estados >> Capitulo7_IntroduccionTecnicasDisenoMarcoEspacioEstados.tex
echo 8. Sistemas Robustos de Realimentación MIMO Resueltos con Técnica de Optimización de Norma H_infinity >> Capitulo8_SistemasRobustosRealimentacionMIMOResueltosTecnicaOptimizacionNormaH_infinity.tex
echo Apéndice A. Gráficos de Flujo de Señales >> ApéndiceA_GraficosFlujoSenales.tex
echo Apéndice B. Antecedentes Matemáticos Relacionados con MIMO y Análisis y Diseño H_infinity >> ApéndiceB_AntecedentesMatematicosRelacionadosMIMOAnalisisDisenoH_infinity.tex
echo Apéndice C. Redes de Control para Conformación del Bucle >> ApéndiceC_RedesControlConformacionBucle.tex
echo Apéndice D. Hechos Acerca de Transformadas de Fourier y Laplace >> ApéndiceD_HechosAcercaTransformadasFourierLaplace.tex
echo Apéndice E. Fórmulas de Bode y Relaciones de Transformadas >> ApéndiceE_FormulasBodeRelacionesTransformadas.tex