> **Diagnóstico histórico anterior a las correcciones.** Consulta el [estado actualizado](CONTROL-CALIDAD-ENTREGA.md) y el [índice de versiones revisadas](ENTREGAS-REVISADAS.md).

# Revisión de calidad de las actividades de IIIEPE

Fecha: 13 de octubre de 2026. Estado revisado: archivos actuales en `actividades-plataforma`.

## Dictamen

Los trabajos constituyen una base de redacción y resolución útil, pero el conjunto **todavía no está listo para entrega**. La precisión matemática revisada es mayormente buena; las principales brechas son la suficiencia didáctica de las secuencias, la correspondencia con algunos apartados de plataforma, la evidencia de aplicación y la calidad visual de ciertos productos. Las presentaciones funcionan principalmente como guiones de exposición: requieren más representaciones, demostraciones y actividades para servir como material docente de maestría.

Esta revisión no asigna una calificación oficial. No permite valorar asistencia, desempeño oral, participación ni resultados de implementación, y no sustituye la evaluación de la figura docente.

## Alcance y evidencia

- Se revisaron las fuentes y los PDF de 21 reportes: 12 de Temas selectos y 9 de Fundamentos.
- Se inspeccionaron visualmente las páginas mediante hojas de contacto, con ampliación de los problemas de silueta y pies de página.
- Hay 21 fuentes de presentación y 20 PDF de presentación. La Actividad 10 de Temas selectos no generó PDF por un carácter Unicode no configurado.
- Se contrastaron consignas y recursos descargados de EVA, incluida la rúbrica para expositores, la Actividad 12 de Temas selectos y los lineamientos e instrumento del trabajo final de Fundamentos.
- No existen todavía entregables `.pptx` ni `.docx` en las nuevas carpetas de actividades. Los documentos Word de `recursos-plataforma` son instrucciones originales, no trabajos terminados.
- La matrícula confirmada está presente en los 21 reportes revisados y no aparece la matrícula anterior en ellos.

## Valoración por dimensión

| Dimensión | Valoración | Evidencia y límite |
|---|---|---|
| Precisión matemática | Buena en los ejemplos revisados | Las seis ecuaciones de la Actividad 5 tienen solución y comprobación coherentes; las medidas de la Actividad 6 y los cálculos de distancia son consistentes. No se afirma una certificación exhaustiva de cada inciso. |
| Correspondencia con consignas | Parcial | Varias fichas responden a los temas y recursos; la Actividad 8 de Fundamentos no tiene consigna desarrollada y su producto fue inferido. La numeración local agrupa algunos apartados distintos. |
| Profundidad pedagógica | Intermedia | Hay reflexión, apoyos y criterios, pero faltan instrumentos utilizables, tareas para estudiantes, tiempos y preguntas de seguimiento en varias secuencias. |
| Voz personal | Pertinente, poco diferenciada entre actividades | Se integra la trayectoria en formación técnica e ingenierías y el acercamiento humanista. Se repiten calibración, revisión y participación; faltan episodios concretos aportados por el docente cuando la consigna pide experiencia. |
| Fuentes y APA | Mejorable | Existe bibliografía y se reconocen autores en varias actividades. Faltan citas localizadas en algunos desarrollos y verificar metadatos de materiales de plataforma. La referencia de sugerencias metodológicas debe contrastarse con la indicación de cita de su portada, que remite a SEP 2022. |
| Identidad institucional | Conservada | Los reportes usan `\input{template}` y las funciones de portada de AulaTeX; las presentaciones conservan la paleta y el diseño Beamer de IIIEPE. |
| Calidad visual | Insuficiente en productos concretos | Hay superposición real en la silueta y en los pies de Fundamentos. Algunas tablas y referencias quedan aisladas en páginas muy vacías. Las diapositivas tienen poca variación y escasos recursos explicativos. |
| Suficiencia de entrega | Incompleta | Faltan formatos exigidos, una compilación, verificación final de algunos PDF y evidencia experimental donde corresponde. |

## Problemas que deben resolverse antes de entregar

1. **Silueta de identidad docente ilegible por superposición.** En Fundamentos 2, las fortalezas y áreas de oportunidad se cruzan; las necesidades y lecturas también. El problema aparece en reporte y presentación. Hay que redistribuir los bloques y volver a renderizar; ampliar únicamente el texto central no lo resuelve.
2. **Pies de página superpuestos en Fundamentos.** La materia larga se imprime a izquierda y derecha y cruza la marca central. Corregir las definiciones de pie conservando el estilo institucional.
3. **Presentación de Temas selectos 10 sin PDF.** El registro de compilación identifica `Δ` (U+0394) como carácter no configurado. La fórmula de distancia debe componerse además como ecuación real, con el radical aplicado a toda la expresión.
4. **Formatos exigidos pendientes.** La tarea de siete habilidades pide escrito en Word y el trabajo final de Fundamentos pide PowerPoint de 10 a 15 diapositivas. La presentación final en PDF sí tiene 15, pero un PDF no sustituye el `.pptx` requerido.
5. **Evidencia experimental pendiente.** Temas selectos 4 y 10 exigen mediciones; Temas selectos 11 incluye ejecución y calibración robótica. Los ejemplos están declarados como simulados o propuestos, lo cual es correcto, pero no satisface por sí mismo la parte física solicitada. No deben convertirse en resultados reales mediante cambios de redacción.
6. **Alineación pendiente en Fundamentos 8.** El apartado no desarrolla instrucciones; el análisis bioecológico es una propuesta razonable, no una respuesta cuya correspondencia esté verificada.
7. **Diferencia entre fuente y PDF.** El reporte de volumen todavía muestra `8imes5imes3` en lugar de `8 × 5 × 3`. La fuente fue corregida, pero el PDF revisado es anterior. El PDF de identidad también es anterior a su último ajuste. Se debe recompilar y revisar el resultado final.

## Mejoras académicas y didácticas prioritarias

### Reportes

- Desarrollar procedimientos representativos paso a paso. Varias tablas de fracciones y signos contienen expresión y resultado, aunque el encabezado promete procedimiento. Un resultado correcto no muestra todo el razonamiento esperado.
- Diferenciar una ficha resuelta del docente de una ficha que usarán los estudiantes. Para exposiciones, preparar consignas, espacios de registro, preguntas, ayudas graduadas y guía de respuestas separada.
- Materializar la evaluación formativa. Incluir listas de cotejo o rúbricas con indicadores observables, niveles, evidencia y acción de mejora; nombrar autoevaluación y coevaluación no basta.
- Añadir tiempos, materiales y criterios de cierre cuando se presenta una secuencia. Los cinco momentos están descritos en varias actividades, pero aún no constituyen siempre una planeación operativa.
- Integrar ejes articuladores con acciones explícitas y observables. La rúbrica para expositores reserva puntos a su integración práctica y a los instrumentos de evaluación.
- Reducir repeticiones de la misma conclusión sobre rigor técnico, participación y humanismo. Cada actividad debe mostrar una decisión propia ligada al contenido específico.
- Aportar ejemplos reales de práctica cuando el trabajo lo exige, sin inventar episodios ni resultados. El contexto profesional proporcionado permite situar la voz; no permite afirmar experiencias particulares no relatadas.
- Mejorar continuidad de tablas y referencias. Utilizar tablas que continúen con encabezados repetidos o páginas apaisadas cuando sea pertinente, evitando fragmentar cuadros en bloques que generan páginas muy vacías.

### Presentaciones

- Conservar la plantilla institucional, pero sustituir parte de las listas por representaciones del contenido: tiras de fracciones, balanza algebraica, desarrollos planos, comparación de volúmenes, tablas y gráficas.
- Añadir preguntas al grupo, una resolución guiada y un reto de transferencia. En su estado actual predominan resúmenes de lo que se propone hacer.
- Aumentar el tamaño útil de diagramas y evitar que una figura pequeña quede aislada en una diapositiva casi vacía.
- En proporcionalidad, incluir la gráfica de masa y alcance; actualmente se incorporó el boceto del lanzador, pero no la gráfica del reporte.
- En el trabajo final, mostrar una tabla y gráfica del modelo y una representación de los sistemas ecológicos; el contenido textual aborda los apartados, pero la explicación visual es débil.
- En las presentaciones de comparación y metodologías, incluir el cuadro solicitado o una versión legible del mismo; actualmente se describe la comparación en listas.

## Revisión por actividad

La numeración de Fundamentos es la organización local empleada para preparar los archivos; debe acompañarse siempre del enlace de plataforma incluido en cada carpeta.

| Materia y actividad | Fortaleza | Falta principal | Estado |
|---|---|---|---|
| Temas 1 · Conversión | Cobertura amplia y distinción entre decimal exacto y aproximación | Más demostración por pasos y apoyos visuales | Revisión académica y visual |
| Temas 2 · Suma y resta | Equivalencia y problemas contextualizados | Convertir parte del listado en explicación y ficha docente utilizable | Revisión académica y visual |
| Temas 3 · Operaciones y signos | Integra ambos recursos oficiales y distingue unidades | Muchas respuestas sin pasos; 12 páginas con tablas y referencias fragmentadas | Revisión académica y visual |
| Temas 4 · Proporcionalidad | Cuestiona correctamente supuestos y unidades del modelo | Mediciones reales y gráfica en presentación | Evidencia pendiente |
| Temas 5 · Ecuaciones | Seis soluciones comprobadas y ajustes ante rezago | Instrumento de evaluación concreto y mejor exposición visual | De los más sólidos, aún con ajustes |
| Temas 6 · Estadística | Igual media con distinta dispersión; interpretación coherente | Ficha para estudiantes, preguntas y evaluación operativa | De los más sólidos, aún con ajustes |
| Temas 7 · Geometría | Distingue altura, apotema y desarrollo | Más desarrollos completos y evidencia de construcción si se solicita | Ampliación didáctica |
| Temas 8 · Volumen | Fórmulas, despejes y factores de escala coherentes | PDF desactualizado y notación defectuosa; mayor apoyo geométrico | Corrección técnica necesaria |
| Temas 9 · Álgebra | Traducción y condiciones geométricas | Integrar el reto original también en el reporte y diversificar representaciones | Alineación y ampliación |
| Temas 10 · Distancia | Pitágoras y distancias correctas en el ejemplo | Presentación sin compilar y tres mediciones reales | Bloqueado para entrega completa |
| Temas 11 · Robótica | Explicita diferencia entre modelo y ejecución | El sistema es un ejemplo sustituto; faltan giros, código y pruebas documentadas | Revisión de consigna y evidencia |
| Temas 12 · Ensayo | Tesis personal y tres artículos recientes pertinentes | Mayor relación con sesiones concretas y resultados reales disponibles; comprobar formato final | Borrador avanzado |
| Fundamentos 1 · Diagnóstico | Responde los cuatro conceptos y sitúa la voz docente | Pie de página y concreción de algún ejemplo | Borrador cercano a revisión final |
| Fundamentos 2 · Identidad | Incluye silueta y necesidades de formación | Superposición grave y ejemplos reales de situaciones profesionales | Corrección visual y profundización |
| Fundamentos 3 · Sociedades | Doce argumentos y conclusión personal | Más contraste con la lectura y aplicaciones diferenciadas | De los más sólidos, aún con ajustes |
| Fundamentos 4 · Aprendizajes | Cuatro pilares correctamente diferenciados | Integrar tabla sin fragmentación y concretar una aplicación | Revisión académica y visual |
| Fundamentos 5 · Habilidades | Siete habilidades y mapa coherentes | Word obligatorio y conexión más concreta con práctica real | Formato pendiente |
| Fundamentos 6 · Comparación | Evita identificar toda evaluación nueva con NEM | Cuadro más legible y síntesis comparativa en las diapositivas | Revisión visual y didáctica |
| Fundamentos 7 · Metodologías | Diferencia proyectos, problemas, servicio e indagación | Consolidar cuadros, revisar metadatos SEP y mapear los apartados agrupados | Revisión de fuentes y presentación |
| Fundamentos 8 · Bioecología | Distingue sistemas de procesos y contexto | Consigna no desarrollada; no se puede certificar correspondencia | Alineación pendiente |
| Fundamentos 9 · Final | Atiende el proyecto por realizar y los sistemas ecológicos; 15 diapositivas | Falta PowerPoint; tabla, gráfica e instrumento concreto deben hacerse visibles | Entrega incompleta |

## Orden de corrección recomendado

1. Resolver archivos y formatos faltantes, correspondencia de consignas y sincronización fuente/PDF.
2. Reparar silueta, pies, notación y continuidad de tablas.
3. Fortalecer fichas, instrumentos de evaluación y presentaciones con contenido visual explicativo.
4. Integrar evidencias reales disponibles y completar la revisión de referencias.
5. Hacer una segunda verificación completa antes de declarar los trabajos listos.

## Archivos revisados

### temas-selectos-de-matematicas-I

- actividad-01-conversion-fracciones-decimales: [Consigna](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-01-conversion-fracciones-decimales/consigna-verificada.md) · [Reporte](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-01-conversion-fracciones-decimales/reporte.pdf) · [Presentación](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-01-conversion-fracciones-decimales/presentacion.pdf)
- actividad-02-suma-resta-fracciones: [Consigna](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-02-suma-resta-fracciones/consigna-verificada.md) · [Reporte](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-02-suma-resta-fracciones/reporte.pdf) · [Presentación](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-02-suma-resta-fracciones/presentacion.pdf)
- actividad-03-multiplicacion-division-y-signos: [Consigna](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-03-multiplicacion-division-y-signos/consigna-verificada.md) · [Reporte](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-03-multiplicacion-division-y-signos/reporte.pdf) · [Presentación](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-03-multiplicacion-division-y-signos/presentacion.pdf)
- actividad-04-proporcionalidad: [Consigna](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-04-proporcionalidad/consigna-verificada.md) · [Reporte](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-04-proporcionalidad/reporte.pdf) · [Presentación](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-04-proporcionalidad/presentacion.pdf)
- actividad-05-ecuaciones-lineales: [Consigna](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-05-ecuaciones-lineales/consigna-verificada.md) · [Reporte](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-05-ecuaciones-lineales/reporte.pdf) · [Presentación](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-05-ecuaciones-lineales/presentacion.pdf)
- actividad-06-estadistica: [Consigna](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-06-estadistica/consigna-verificada.md) · [Reporte](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-06-estadistica/reporte.pdf) · [Presentación](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-06-estadistica/presentacion.pdf)
- actividad-07-geometria: [Consigna](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-07-geometria/consigna-verificada.md) · [Reporte](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-07-geometria/reporte.pdf) · [Presentación](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-07-geometria/presentacion.pdf)
- actividad-08-volumen: [Consigna](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-08-volumen/consigna-verificada.md) · [Reporte](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-08-volumen/reporte.pdf) · [Presentación](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-08-volumen/presentacion.pdf)
- actividad-09-introduccion-algebra: [Consigna](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-09-introduccion-algebra/consigna-verificada.md) · [Reporte](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-09-introduccion-algebra/reporte.pdf) · [Presentación](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-09-introduccion-algebra/presentacion.pdf)
- actividad-10-distancia-cartesiana: [Consigna](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-10-distancia-cartesiana/consigna-verificada.md) · [Reporte](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-10-distancia-cartesiana/reporte.pdf)
- actividad-11-algebra-y-robotica: [Consigna](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-11-algebra-y-robotica/consigna-verificada.md) · [Reporte](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-11-algebra-y-robotica/reporte.pdf) · [Presentación](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-11-algebra-y-robotica/presentacion.pdf)
- actividad-12-reflexion-pedagogica: [Consigna](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-12-reflexion-pedagogica/consigna-verificada.md) · [Reporte](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-12-reflexion-pedagogica/reporte.pdf) · [Presentación](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/temas-selectos-de-matematicas-I/actividades-plataforma/actividad-12-reflexion-pedagogica/presentacion.pdf)

### fundamentos-para-la-enseñanza-y-el-aprendizaje-I

- actividad-01-diagnostico: [Consigna](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-01-diagnostico/consigna-verificada.md) · [Reporte](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-01-diagnostico/reporte.pdf) · [Presentación](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-01-diagnostico/presentacion.pdf)
- actividad-02-identidad-docente: [Consigna](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-02-identidad-docente/consigna-verificada.md) · [Reporte](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-02-identidad-docente/reporte.pdf) · [Presentación](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-02-identidad-docente/presentacion.pdf)
- actividad-03-sociedades-siglo-xxi: [Consigna](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-03-sociedades-siglo-xxi/consigna-verificada.md) · [Reporte](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-03-sociedades-siglo-xxi/reporte.pdf) · [Presentación](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-03-sociedades-siglo-xxi/presentacion.pdf)
- actividad-04-tipos-aprendizaje: [Consigna](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-04-tipos-aprendizaje/consigna-verificada.md) · [Reporte](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-04-tipos-aprendizaje/reporte.pdf) · [Presentación](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-04-tipos-aprendizaje/presentacion.pdf)
- actividad-05-siete-habilidades: [Consigna](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-05-siete-habilidades/consigna-verificada.md) · [Reporte](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-05-siete-habilidades/reporte.pdf) · [Presentación](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-05-siete-habilidades/presentacion.pdf)
- actividad-06-escuela-tradicional-nem: [Consigna](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-06-escuela-tradicional-nem/consigna-verificada.md) · [Reporte](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-06-escuela-tradicional-nem/reporte.pdf) · [Presentación](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-06-escuela-tradicional-nem/presentacion.pdf)
- actividad-07-metodologias-nem: [Consigna](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-07-metodologias-nem/consigna-verificada.md) · [Reporte](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-07-metodologias-nem/reporte.pdf) · [Presentación](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-07-metodologias-nem/presentacion.pdf)
- actividad-08-perspectiva-bioecologica: [Consigna](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-08-perspectiva-bioecologica/consigna-verificada.md) · [Reporte](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-08-perspectiva-bioecologica/reporte.pdf) · [Presentación](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-08-perspectiva-bioecologica/presentacion.pdf)
- actividad-09-trabajo-final: [Consigna](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-09-trabajo-final/consigna-verificada.md) · [Reporte](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-09-trabajo-final/reporte.pdf) · [Presentación](maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividades-plataforma/actividad-09-trabajo-final/presentacion.pdf)

