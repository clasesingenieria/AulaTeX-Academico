# Productos didácticos y voz de S5

La técnica principal es Simulación, catálogo local número 18. El escenario es la atención de tres fichas por un auxiliar jurídico; no se inventan diligencias realizadas, testimonios nuevos, expedientes reales ni resultados periciales. Sus decisiones y resultados son encuadramientos preliminares y diligencias propuestas. La reflexión final retoma una ficha y explica la reserva necesaria.

La investigación guiada es el procedimiento documental: leer unidad y normas, localizar elementos, contrastar fuentes actuales, distinguir hechos de inferencias y decidir provisionalmente. No existe una técnica independiente denominada «investigación guiada» en el catálogo local de cien registros. No se renombra como técnica de valoración de decisiones de S4.

El cuadro comparativo (número 1) materializa la **tabla de investigación**. El estudio de casos (número 27) aporta la secuencia hechos–problema–norma–solución de las fichas. El informe (número 11) es el continente breve de los hallazgos y la conclusión. El reporte de investigación (número 76) aporta profundidad documental —pregunta, método, hallazgos e interpretación— integrada en la plantilla, sin insertar otro documento ni una sección llamada «Reporte de investigación». Esta combinación complementa la técnica docente y conserva sus productos específicos; los números son identificadores del catálogo local, distintos de los números web.

| Producto | Forma visible y contenido verificable | Base del catálogo |
|---|---|---|
| Tabla de investigación | Cinco filas de figuras; cuatro columnas exactas: **Figura delictiva / Ley y artículo / Conducta descrita / Elemento que la diferencia**. Secuestro incluye una circunstancia modificativa; precisar ley especial y preceptos derogados si corresponde. | Cuadro comparativo: tabla, conceptos y categorías; investigación, selección, contraste y revisión. |
| Tres fichas | Una caja por ficha, con tabla interna de cuatro columnas exactas: **Hechos conocidos / Elementos legales identificados / Datos que faltan / Posible figura y fundamento**. Dos supuestos de ficha 1 y de ficha 3 se mantienen separados en filas. Breve razonamiento natural interpreta la diferencia sin repetir las celdas. | Simulación: escenario, variables, decisiones y resultados; estudio de casos: hechos, análisis y conclusión. |
| Informe y conclusión personal | Introducción temática, un desarrollo temático con marco conceptual, tabla y fichas, conclusión de cinco a siete líneas dedicada a una ficha. Clasificación preliminar, fundamento consultado y dato indispensable faltante. | Informe y reporte de investigación como contenedor; no añadir ensayo, guion de audiencia ni expediente real. |

La consigna específica fija figuras por filas y cuatro columnas; prevalece sobre el patrón genérico de cuadro comparativo que suele colocar objetos en columnas. La orientación vertical resulta admisible si las cuatro columnas son legibles: el producto es una tabla jurídica breve dentro de la simulación y no un cuadro horizontal autónomo. La fidelidad no se mide por añadir columnas ajenas a la consigna.

## Voz editorial

Se consultan memoria institucional UnADM, memoria de materia y reportes S3–S4. En S3 la conclusión comienza «Considero que el encuadramiento debe tratarse como una hipótesis revisable» y exige prueba de elementos antes de condenar. S4 prioriza protección de personas vulnerables y distingue intervención urgente de condena. La pauta inferida es: lenguaje directo; prudencia probatoria; interés superior y derechos de víctimas; control del poder punitivo; diligencias concretas; hipótesis revisables. No se atribuyen vivencias, convicciones ni experiencias profesionales no proporcionadas.

La conclusión usa primera persona sobria —«Considero», «Daría prioridad», «no confirmaría»— con posición, razón y consecuencia. Debe elegir una ficha y reservar la clasificación cuando falte el elemento decisivo. No habla de haber realizado una actividad, de la técnica aplicada, del puntaje o del proceso editorial. La declaración transparente de ChatGPT es una nota al pie ligada al cierre: apoyo en organización y borrador, revisión crítica y responsabilidad académica del autor; no afirmar que el texto fue exclusivamente humano.

## Evidencia

Los contratos completos consultados, sin alteración, quedan en `revisiones/tecnicas-productos-S5.json`. Proceden de `aulaTEX/aulatex/didactic_catalog.py`, con ficha oficial local de los fascículos UnADM y patrones de construcción. La técnica principal está expresamente indicada en la planificación docente, p. 4.

## Cotejo del fascículo original y discrepancia del catálogo

Se verificó la ficha **Simulación** en el fascículo 1 de *100 Técnicas Didácticas de Enseñanza y Aprendizaje*, pp. impresas 197–207 (físicas 198–208). Su estructura verdadera es planeación de objetivos, selección del modelo y modelado. Los pasos son: planear; seleccionar o diseñar; organizar; modelar la simulación; efectuarla; evaluar; retroalimentar. En S5 corresponden a objetivo y legislación, modelo de tres fichas diseñado por la docente, procedimiento de cinco preguntas, ejemplo de encierro de la consigna, solución de tres fichas, cotejo de encuadramientos y conclusión sobre una ficha. No se declara que se haya participado en una audiencia, realizado diligencias o recibido retroalimentación docente inexistente.

El catálogo local devuelve correctamente el nombre y la definición de Simulación, pero sus campos `official_structure`, `build_steps` y derivados contienen por error texto de la ficha **Juego de roles**. Los contratos copiados en JSON se conservan íntegros; no se corrigen ni se usan esos campos contaminados para imponer personajes o escenas no solicitadas. Prevalecen la planificación docente y el fascículo primario. La discrepancia queda documentada sin modificar motores ni puntuadores. Evidencia: `revisiones/cotejo-fasciculo-simulacion.json` y `revisiones/Simulacion-fasciculo1-pp197-207.txt`.
