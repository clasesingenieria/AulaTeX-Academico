# INSTITUTO DE INVESTIGACIÓN, INNOVACIÓN Y ESTUDIOS DE POSGRADO PARA LA EDUCACIÓN (IIIEPE)
## Maestría en Aprendizaje y Enseñanza de las Matemáticas (MAEM)
### Asignatura: Temas Selectos de Matemáticas I (PFM02)
### Docente: Profr. Carlos Hugo De León González
### Estudiante / Expositor: Mtro. Martín Jonathan de la Cruz Muñoz | Matrícula: 00874
---
# GUION TÉCNICO Y PEDAGÓGICO DE CLASE MUESTRA EN VIDEO
## Título: "Estadística Aplicada y Medidas de Dispersión: Optimización y Toma de Decisiones en Procesos de Mantenimiento"
### Enfoque Didáctico: 5 Fases STEAM de la Nueva Escuela Mexicana (NEM) y Ejes Articuladores (Pensamiento Crítico e Inclusión)

---

## 1. Ficha Técnica de Producción

| Parámetro | Especificación |
| :--- | :--- |
| **Institución convocante** | IIIEPE - Monterrey, Nuevo León |
| **Programa de Posgrado** | Maestría en Aprendizaje y Enseñanza de las Matemáticas (MAEM) |
| **Unidad Curricular** | Temas Selectos de Matemáticas I (PFM02) |
| **Actividad de Plataforma** | Actividad 06 — Clase Muestra en Video y Ficha de Trabajo (30% Ponderación Final) |
| **Expositor / Personaje** | Mtro. Martín Jonathan de la Cruz Muñoz |
| **Voz Sintética (Polly)** | `Andres` (Neural Mexican Spanish, tono académico, pausado, asertivo y pedagógico) |
| **Formato de Salida** | Video MP4 Widescreen 16:9 (1080p), animatic Ken Burns dinámico, subtítulos SRT sincronizados |
| **Herramienta de Render** | Video Studio AI (`video-studio`) / AWS Polly Neural / FFmpeg / PyMuPDF |
| **Duración Estimada** | 5 a 6 minutos |

---

## 2. Matriz de Cobertura de Criterios de la Rúbrica Oficial (100 Puntos)

| Criterio Rúbrica Oficial (10 pts c/u) | Escena del Guion | Evidencia Matemática / Didáctica |
| :--- | :--- | :--- |
| **1. Rigor Conceptual Estadístico** | Escena 3 y 4 | Distinción explícita entre medidas de tendencia central (media, mediana, moda) y medidas de dispersión (rango, desviación media). |
| **2. Medidas de Dispersión y Desviación Media** | Escena 4 | Demostración paso a paso de la fórmula formal $DM = \frac{\sum \|x_i - \bar{x}\|}{n}$ con las sumatorias absolutas de ambos procesos. |
| **3. Lectura e Interpretación Gráfica** | Escena 5 | Análisis visual comparativo del gráfico de barras de tiempos por ajuste; correlación entre amplitud gráfica y dispersión numérica. |
| **4. Estructura Didáctica en 5 Fases STEAM** | Escenas 2 a 10 | Articulación explícita de las fases de la NEM: Saberes comunitarios, Plan de indagación, Organización y cálculo, Comunicación de resultados, Metacognición. |
| **5. Narrativa y Reto Detonador Contextualizado** | Escena 2 | Caso de mantenimiento preventivo y ajuste de mecanismos en planta industrial (Línea Alfa vs Línea Beta con igual promedio). |
| **6. Problemas Razonados y Prueba de Sensibilidad** | Escena 9 | Modelado de un evento atípico o falla crítica ($x_6 = 30$ min); análisis de la vulnerabilidad de la media y la robustez de la mediana. |
| **7. Ejes Articuladores (Pensamiento Crítico e Inclusión)** | Escena 8 | Cuestionamiento epistémico de decisiones basadas en un solo promedio; diseño universal con roles colaborativos rotativos. |
| **8. Estrategia de Evaluación Formativa** | Escena 10 | Rúbrica holística de 4 niveles de desempeño, coevaluación entre pares con retroalimentación dialógica y heteroevaluación docente. |
| **9. Ficha de Trabajo y Recursos** | Escena 10 | Articulación con la Ficha de Trabajo del Estudiante con 3 retos progresivos y preguntas de autorregulación metacognitiva. |
| **10. Conducción, Claridad Verbal y Tiempo** | Global | Locución estructurada, dicción precisa, ritmo equilibrado para asimilación conceptual y subtitulado completo. |

---

## 3. Guion Secuencial Plano por Plano (11 Escenas)

### Escena 01: Identidad Institucional y Presentación del Expositor
* **Tiempo:** 00:00 - 00:28 (28 s)
* **Visual:** Diapositiva 01 (Beamer 16:9). Fondo azul institucional IIIEPE, logo oficial vectorial blanco en cabecera, tipografía serif/sans limpia. Datos completos: IIIEPE, Maestría en Aprendizaje y Enseñanza de las Matemáticas, Temas Selectos de Matemáticas I, Expositor Mtro. Martín Jonathan de la Cruz Muñoz, Matrícula 00874.
* **Cámara / Efecto:** Ken Burns suave con acercamiento central lento (1.00x a 1.05x).
* **Audio de fondo:** Tono tenue neutro académico.
* **Parlamento de Locución (Andres - Neural):**
  > *"Estimada comunidad académica del Instituto de Investigación, Innovación y Estudios de Posgrado para la Educación del Estado de Nuevo León. Bienvenidos a esta clase muestra de la unidad curricular Temas Selectos de Matemáticas I, en la Maestría en Aprendizaje y Enseñanza de las Matemáticas. Les saluda el maestro Martín Jonathan de la Cruz Muñoz, con matrícula 00874. Hoy abordaremos el poder del análisis estadístico y las medidas de dispersión en la toma de decisiones técnicas, bajo el marco pedagógico de las cinco fases STEAM de la Nueva Escuela Mexicana."*

---

### Escena 02: Fase STEAM 1 · Saberes de Nuestra Comunidad y Reto Detonador
* **Tiempo:** 00:28 - 01:00 (32 s)
* **Visual:** Diapositiva 02. Fotografía esquemática de una celda de maquinado industrial. Dos paneles comparativos: Equipo Alfa (A) vs Equipo Beta (B). Seis mediciones de tiempo de mantenimiento: $A = \{8, 9, 10, 10, 11, 12\}$ minutos y $B = \{5, 7, 10, 10, 13, 15\}$ minutos.
* **Cámara / Efecto:** Paneo horizontal sutil destacando la pregunta detonadora en la base: "¿Basta el promedio para elegir el mejor proveedor de mantenimiento?".
* **Parlamento de Locución (Andres - Neural):**
  > *"Iniciamos con la Fase Uno: Saberes de nuestra comunidad. Imaginemos una planta de manufactura donde dos cuadrillas técnicas realizan seis servicios de ajuste preventivo a maquinaria crítica. El equipo A registra tiempos de ocho, nueve, diez, diez, once y doce minutos. El equipo B registra cinco, siete, diez, diez, trece y quince minutos. Si calculamos el promedio aritmético de ambos grupos, ambos obtienen exactamente diez minutos. La pregunta detonadora para nuestros estudiantes es: ¿Basta el promedio para decidir cuál cuadrilla garantiza un mantenimiento predecible y seguro?"*

---

### Escena 03: Paradoja de las Medidas de Tendencia Central
* **Tiempo:** 01:00 - 01:32 (32 s)
* **Visual:** Diapositiva 03. Tabla comparativa con colores institucionales destacando en verde pastel: Media = 10 min en ambos, Mediana = 10 min en ambos, Moda = 10 min en ambos. Cuadro de alerta inferior: "Las medidas de centralidad son idénticas, pero los procesos se comportan de forma radicalmente distinta".
* **Cámara / Efecto:** Zoom sutil sobre la fila de la mediana y moda.
* **Parlamento de Locución (Andres - Neural):**
  > *"Al analizar las medidas de tendencia central, descubrimos una paradoja didáctica fascinante. Para el equipo A, la suma de los tiempos es sesenta, dando una media de diez minutos; la mediana, al ordenar los datos, es diez, y la moda es diez. Para el equipo B, ocurre exactamente lo mismo: media diez, mediana diez y moda diez. Si nos quedáramos únicamente con la centralidad, concluiríamos erróneamente que ambos procesos son equivalentes. Aquí radica el núcleo de nuestro reto cognitivo: necesitamos cuantificar la variabilidad."*

---

### Escena 04: Fase STEAM 2 y 3 · Plan de Indagación y Medidas de Dispersión
* **Tiempo:** 01:32 - 02:18 (46 s)
* **Visual:** Diapositiva 04. Expresión matemática destacada en tcolorbox:
  $$DM = \frac{\sum_{i=1}^{n} |x_i - \bar{x}|}{n}$$
  Desarrollo paso a paso:
  Para A: $|-2| + |-1| + 0 + 0 + |+1| + |+2| = 6 \implies DM_A = 6/6 = 1.0\text{ min}$. Rango = $12 - 8 = 4\text{ min}$.
  Para B: $|-5| + |-3| + 0 + 0 + |+3| + |+5| = 16 \implies DM_B = 16/6 = 8/3 \approx 2.67\text{ min}$. Rango = $15 - 5 = 10\text{ min}$.
* **Cámara / Efecto:** Enfoque dinámico sobre la fórmula de la desviación media y su sumatoria modular.
* **Parlamento de Locución (Andres - Neural):**
  > *"En las Fases Dos y Tres, planificamos la indagación y organizamos las respuestas matemáticas mediante las medidas de dispersión. Primero, el rango muestra que el equipo A tiene una oscilación de apenas cuatro minutos, mientras que el equipo B se extiende a diez minutos. Pero la herramienta analítica fundamental es la Desviación Media: la suma de las distancias absolutas de cada dato respecto a la media, dividida entre el número de observaciones. En el proceso A, las desviaciones suman seis, resultando en una desviación media de un minuto exacto. En cambio, en el proceso B, las distancias suman dieciséis, arrojando una desviación media de dos punto sesenta y siete minutos. La dispersión del proceso B es casi el triple que la del proceso A."*

---

### Escena 05: Fase STEAM 4 · Lectura e Interpretación Gráfica Comparativa
* **Tiempo:** 02:18 - 02:54 (36 s)
* **Visual:** Diapositiva 05. Gráfico de barras de alta precisión (pgfplots) comparando los 6 ajustes: barras azules (Proceso A) compactas y estables junto a la línea media horizontal de 10 min; barras turquesas (Proceso B) con valles profundos en 5 min y picos altos en 15 min.
* **Cámara / Efecto:** Desplazamiento visual de izquierda a derecha siguiendo las 6 observaciones.
* **Parlamento de Locución (Andres - Neural):**
  > *"Llegamos a la Fase Cuatro: Presentación de resultados y lectura gráfica. El gráfico de barras comunica de manera instantánea lo que las cifras demuestran algebraicamente. Observemos cómo las barras del proceso A se mantienen homogéneas y estrechamente ceñidas a la línea promedio de diez minutos. En contraste, las barras del proceso B oscilan bruscamente desde un mínimo de cinco hasta un pico de quince minutos. El estudiante aprende a leer en la gráfica la fluctuación de un proceso, conectando la representación geométrica con la métrica de dispersión calculada."*

---

### Escena 06: Toma de Decisiones Técnicas y Límites de la Inferencia
* **Tiempo:** 02:54 - 03:26 (32 s)
* **Visual:** Diapositiva 06. Matriz de decisión técnica: Criterio de Previsibilidad vs Incertidumbre. Nota de rigor epistémico: "Seis observaciones didácticas permiten modelar el concepto, pero la generalización industrial exige control estadístico de procesos (SPC) y muestreo continuo".
* **Cámara / Efecto:** Zoom suave enfatizando el principio de previsibilidad.
* **Parlamento de Locución (Andres - Neural):**
  > *"¿Cómo se traducen estos datos en una decisión en el mundo real? Si una línea de ensamble requiere programar paros de mantenimiento con citas estrictas para no detener la producción, el proceso A es contundentemente superior por su predictibilidad y bajo riesgo. Sin embargo, con rigor metodológico, advertimos a los estudiantes sobre los límites de la inferencia: seis ajustes didácticos simulan el fenómeno, pero en la industria no se puede decretar calidad total sin auditar la complejidad del trabajo, las condiciones térmicas y el desgaste de los componentes."*

---

### Escena 07: Estructura Curricular en 5 Fases STEAM de la NEM
* **Tiempo:** 03:26 - 03:58 (32 s)
* **Visual:** Diapositiva 07. Diagrama de flujo circular en TikZ con las 5 fases STEAM: 1) Saberes previos, 2) Plan de acción, 3) Indagación y cálculo, 4) Socialización de hallazgos, 5) Reflexión y metacognición.
* **Cámara / Efecto:** Giro panorámico que destaca la interconexión cíclica de las fases.
* **Parlamento de Locución (Andres - Neural):**
  > *"El diseño didáctico de esta sesión sigue rigurosamente las cinco fases del aprendizaje basado en indagación bajo el enfoque STEAM de la Nueva Escuela Mexicana. Comenzamos explorando intuiciones comunitarias; formulamos hipótesis; modelamos la matemática en equipos de trabajo; comunicamos argumentos basados en datos empíricos; y cerramos con una fase metacognitiva donde cada estudiante autoevalúa el cambio en su razonamiento antes y después de conocer las medidas de dispersión."*

---

### Escena 08: Ejes Articuladores: Pensamiento Crítico e Inclusión
* **Tiempo:** 03:58 - 04:30 (32 s)
* **Visual:** Diapositiva 08. Dos pilares pedagógicos de la NEM: 1) Pensamiento Crítico (desmitificación de la estadística unidimensional; no dejarse engañar por un promedio). 2) Inclusión y Diversidad (distribución equitativa de roles: calculador, registrador, graficador y comunicador; mediación escalonada según ritmos de aprendizaje).
* **Cámara / Efecto:** Acercamiento progresivo a los dos bloques temáticos.
* **Parlamento de Locución (Andres - Neural):**
  > *"Articulamos dos ejes fundamentales del Plan de Estudio: Pensamiento Crítico e Inclusión. El Pensamiento Crítico se activa cuando los alumnos descubren que un promedio puede ocultar inequidades o riesgos operativos; aprenden a dudar y a exigir medidas de variabilidad. La Inclusión se materializa en el trabajo colaborativo con roles rotativos: registro, cálculo numérico, trazado gráfico y argumentación verbal, garantizando que todos los alumnos participen activamente según sus estilos y ritmos de aprendizaje."*

---

### Escena 09: Reto de Transferencia y Prueba de Sensibilidad ante Valores Atípicos
* **Tiempo:** 04:30 - 05:08 (38 s)
* **Visual:** Diapositiva 09. Problema de transferencia: ¿Qué sucede si el último dato del Proceso A cambia de 12 a 30 minutos debido a una rotura imprevista?
  Nuevo conjunto: $8, 9, 10, 10, 11, 30$.
  Nueva media: $78 / 6 = 13.0\text{ min}$ (sube 30%).
  Nueva mediana: $10.0\text{ min}$ (permanece idéntica).
  Nueva desviación media: $|-5|+|-4|+|-3|+|-3|+|-2|+|+17| = 34 / 6 \approx 5.67\text{ min}$ (se quintuplica).
* **Cámara / Efecto:** Enfoque sobre la comparación Mediana vs Media ante el outlier.
* **Parlamento de Locución (Andres - Neural):**
  > *"Para consolidar la transferencia del conocimiento, proponemos un reto de sensibilidad matemática: ¿Qué sucede si en el proceso A, el último ajuste sufre una complicación y toma treinta minutos en lugar de doce? La nueva media se dispara a trece minutos, y la desviación media sube drásticamente a cinco punto sesenta y siete minutos. Sin embargo, la mediana se mantiene inalterable en diez minutos. Esta experiencia demuestra experimentalmente por qué la mediana es un estimador robusto ante valores atípicos y cómo la desviación media detecta oportunamente anomalías críticas en un sistema."*

---

### Escena 10: Estrategia de Evaluación Formativa y Ficha de Trabajo
* **Tiempo:** 05:08 - 05:40 (32 s)
* **Visual:** Diapositiva 10. Matriz de Evaluación Formativa con los cuatro niveles de dominio: Inicial, Básico, Autónomo y Destacado. Muestra de la Ficha de Trabajo del Estudiante con los 3 retos y preguntas de autorregulación: 1) ¿Qué cálculo respalda mi conclusión? 2) ¿Cómo mejoró mi explicación tras la retroalimentación de mis pares?
* **Cámara / Efecto:** Paneo vertical sobre la rúbrica y la ficha didáctica.
* **Parlamento de Locución (Andres - Neural):**
  > *"Nuestra estrategia de evaluación es esencialmente formativa y dialógica. Mediante una rúbrica cualitativa de cuatro niveles, evaluamos el rigor del procedimiento, la precisión gráfica y la solidez argumentativa. La Ficha de Trabajo guía al alumno en tres retos progresivos e integra momentos explícitos de coevaluación y heteroevaluación. El error no se sanciona, sino que se transforma en palanca cognitiva para contrastar la predicción intuitiva contra la evidencia matemática."*

---

### Escena 11: Síntesis Metacognitiva, Conclusiones y Referencias Oficiales
* **Tiempo:** 05:40 - 06:12 (32 s)
* **Visual:** Diapositiva 11. Conclusión humanista de la educación matemática: "La estadística formativa no clasifica a las personas; comprende sus procesos para acompañar su desarrollo". Referencias oficiales completas en formato APA 7: IIIEPE (2026), SEP (2024, Fase 6), Batanero (Didáctica de la Estadística). Cierre con logos de IIIEPE y carátula final.
* **Cámara / Efecto:** Alejamiento gradual (zoom out) hacia la placa de crédito institucional completa.
* **Parlamento de Locución (Andres - Neural):**
  > *"En conclusión, enseñar estadística desde el enfoque STEAM de la Nueva Escuela Mexicana trasciende la memorización algorítmica: empodera a los estudiantes para analizar su entorno de manera crítica, colaborativa y humana. En el aula, al igual que en la industria, un promedio nunca refleja la historia completa de un grupo. Agradezco su atención a esta clase muestra de Temas Selectos de Matemáticas I para el Instituto de Investigación, Innovación y Estudios de Posgrado para la Educación. Muchas gracias."*

---

## 4. Solución Matemática Completa y Formal de los Retos

### Reto 1: Datos Base de Mantenimiento
* **Datos Proceso A:** $X_A = \{8, 9, 10, 10, 11, 12\}$, $n=6$.
  * Media: $\bar{x}_A = \frac{8+9+10+10+11+12}{6} = \frac{60}{6} = 10.0\text{ min}$.
  * Mediana: Datos ordenados en posiciones 3 y 4: $\frac{10+10}{2} = 10.0\text{ min}$.
  * Moda: Dato más frecuente $= 10.0\text{ min}$ (frecuencia 2).
  * Rango: $R_A = x_{\max} - x_{\min} = 12 - 8 = 4.0\text{ min}$.
  * Desviación Media:
    $$DM_A = \frac{|8-10| + |9-10| + |10-10| + |10-10| + |11-10| + |12-10|}{6} = \frac{2 + 1 + 0 + 0 + 1 + 2}{6} = \frac{6}{6} = 1.0\text{ min}$$

* **Datos Proceso B:** $X_B = \{5, 7, 10, 10, 13, 15\}$, $n=6$.
  * Media: $\bar{x}_B = \frac{5+7+10+10+13+15}{6} = \frac{60}{6} = 10.0\text{ min}$.
  * Mediana: $\frac{10+10}{2} = 10.0\text{ min}$.
  * Moda: $10.0\text{ min}$.
  * Rango: $R_B = 15 - 5 = 10.0\text{ min}$.
  * Desviación Media:
    $$DM_B = \frac{|5-10| + |7-10| + |10-10| + |10-10| + |13-10| + |15-10|}{6} = \frac{5 + 3 + 0 + 0 + 3 + 5}{6} = \frac{16}{6} = \frac{8}{3} \approx 2.6667\text{ min}$$

### Reto 2: Prueba de Sensibilidad ante Outlier ($x_6 = 30$)
* **Datos Proceso A Modificado ($A'$):** $X_{A'} = \{8, 9, 10, 10, 11, 30\}$, $n=6$.
  * Media: $\bar{x}_{A'} = \frac{8+9+10+10+11+30}{6} = \frac{78}{6} = 13.0\text{ min}$ (incremento de $30\%$).
  * Mediana: Sigue siendo $\frac{10+10}{2} = 10.0\text{ min}$ (invariante / robusta).
  * Rango: $R_{A'} = 30 - 8 = 22.0\text{ min}$.
  * Desviaciones respecto a la nueva media ($\bar{x}=13$):
    $|8-13| = 5$, $|9-13| = 4$, $|10-13| = 3$, $|10-13| = 3$, $|11-13| = 2$, $|30-13| = 17$.
    $$\sum |x_i - \bar{x}| = 5 + 4 + 3 + 3 + 2 + 17 = 34$$
    $$DM_{A'} = \frac{34}{6} = \frac{17}{3} \approx 5.6667\text{ min}$$
  * **Conclusión matemática:** La presencia de un valor extremo distorsiona fuertemente la media y la desviación media, pero no altera la mediana, demostrando la necesidad de articular medidas robustas y no robustas según el contexto de decisión.
