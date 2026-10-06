# Actividad 10: revisión documental y contractual

Fecha de preparación: 4 de octubre de 2026. Elaboración asistida por GitHub Copilot; no constituye evaluación docente ni entrega en Moodle.

## Producto principal

[Word acumulativo revisado](../../../entregas/Tarea10_DeLaCruzMunoz_Revision-2026-10-04.docx), con [PDF de consulta](../../../entregas/Tarea10_DeLaCruzMunoz_Revision-2026-10-04.pdf), 21 páginas. Conserva el texto de [Tarea 9 original](../../../entregas/Tarea9_DeLaCruzMunoz.docx) y añade tres párrafos de antecedentes y uno de delimitación administrativa. La [base de trabajo corregida](../../../anteproyecto/vtaxi-2026-09-28/base-T9-corregida-para-T10.docx) no es una entrega nueva ni modifica el archivo original. La versión inicial de T10 se conserva en [antes-retroalimentacion](antes-retroalimentacion/).

El [contenido estructurado](../../../anteproyecto/vtaxi-2026-09-28/actividad-10-revisada.json) conserva título, problema, preguntas y objetivo general. Los objetivos específicos 1 y 2 se precisan para vincular requisitos con procesos, responsabilidades y gestión documental; los objetivos 3 y 4 se conservan. Se añaden antecedentes científicos delimitados, indicadores propuestos y cinco fuentes de apoyo. Las correcciones se reproducen con [aplicar_retroalimentacion.py](aplicar_retroalimentacion.py).

## Retroalimentación docente incorporada

Consulta autenticada de siete actividades, solo lectura. Evidencia con fecha UTC y huellas: [inspection.json](../../../anteproyecto/evidencias/retroalimentacion-2026-10-04/inspection.json). Moodle incluye el comentario íntegro en un bloque oculto; se recuperó ese texto, no solo el resumen abreviado.

| Origen | Observación real | Aplicación o límite |
| --- | --- | --- |
| [T1](../../../anteproyecto/evidencias/retroalimentacion-2026-10-04/2877-consigna-estado.txt) | Utilizar portada institucional. | Se conserva portada institucional y datos completos. |
| [T2](../../../anteproyecto/evidencias/retroalimentacion-2026-10-04/2885-retroalimentacion-completa.txt) | Excelente trabajo; sin corrección concreta. | Se mantienen los criterios académicos y APA; no se inventan observaciones. |
| [T3](../../../anteproyecto/evidencias/retroalimentacion-2026-10-04/2886-retroalimentacion-completa.txt) | Número de control incompleto, antecedentes regionales cuando existan y revisión de referencias/DOI. | Matrícula 26130503 visible; doce DOI resueltos y títulos cotejados. No se traslada Cajeme/Sonora al objeto actual de Nuevo León. La búsqueda científica regional y reciente sigue abierta. |
| [T8](../../../anteproyecto/evidencias/retroalimentacion-2026-10-04/2908-retroalimentacion-completa.txt) | Mantener la gestión administrativa como objeto central; evitar predominio jurídico; fortalecer antecedentes específicos. | Ampliación crítica de antecedentes, aclaración del problema, objetivos 1–2 ajustados, procesos y responsables en la matriz, indicadores de cobertura, trazabilidad y cierre de observaciones. |
| T4 y T6 | No entregó/no envió actividad. | Son observaciones sobre envío, no correcciones de contenido. No se presentan como resueltas por generar documentos locales. |
| [T9](../../../anteproyecto/evidencias/retroalimentacion-2026-10-04/2909-consigna-estado.txt) | Sin calificar y sin comentario docente visible. | No se atribuye aprobación ni retroalimentación inexistente. |

T8 muestra 6,00/7,00 en el campo de calificación y 6.1/7.0 en el comentario: se conserva la discrepancia, sin corregirla ni inferir una nueva nota. Las indicaciones de la docente se tratan como retroalimentación, no como fuente científica de afirmaciones sobre compliance.

## Correspondencia con la rúbrica

| Requisito | Evidencia en Word/PDF acumulativo |
| --- | --- |
| Apartados 1 y 2 conservados (0.5 puntos del instrumento) | Páginas 3–11; texto original más cuatro ampliaciones declaradas. Comparación automatizada y huella del original aprobadas. |
| Un objetivo general congruente (2 puntos) | Apartado 3.1, página 12; mismo ámbito, variables y periodo de la pregunta general. |
| Entre tres y cinco específicos (3 puntos) | Cuatro objetivos en 3.2, página 12: identificar y clasificar, diagnosticar, examinar y proponer. |
| Matriz actualizada (1.5 puntos) | Anexo 1, páginas 18–20; título, problema, pregunta general, objetivo general y cuatro correspondencias específicas. |
| Covey actualizado (1 punto) | Anexo 2, página 21; problema y objetivo general íntegros en II Importante / No urgente. |
| Portada y formato | Institución, programa, LGAC, estudiante, matrícula 26130503, docente y fecha; carta, márgenes de una pulgada, Arial 11 y doble espacio del cuerpo. |
| Índice automático | Campo TOC nativo actualizado mediante Microsoft Word; página 2. |
| Referencias | Bibliografía previa preservada y material 3.3 incorporado; desambiguación institucional s. f.-a/s. f.-b; nota de IA como pie nativo. |

Los valores son los máximos de la rúbrica, no una calificación asignada al trabajo.

## Aplicación de AulaTeX

- Se consultaron el contrato `REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT`, el formato institucional, la memoria local, la memoria ascendente MGA y las decisiones de continuidad de T8/T9.
- La consigna particular exige el mismo Word acumulativo. La estructura genérica de tres actos se aplica únicamente al reporte LaTeX auxiliar: introducción, desarrollo con título temático y conclusiones. No se impone al anteproyecto.
- Se conservan los encabezados 4–9 sin inventar hipótesis, justificación, resultados o métodos concluidos. Su desarrollo corresponde a entregas posteriores.
- La matriz añade objetivos; procedimientos y productos son apoyos de verificabilidad propuestos localmente, no nuevas exigencias de la rúbrica.
- El reporte y la presentación comparten los mismos objetivos, preguntas, procedimientos y productos. Las fuentes sin fecha se identifican como tales, sin inventar años.
- No se imprimen bloques de módulo, vencimiento o identificadores operativos; las URLs bibliográficas a materiales del aula se mantienen por trazabilidad académica.
- Se utilizó el renderizador determinista existente de AulaTeX y los controles de conservación anteriores y posteriores a la actualización por Word. No se ejecutó el ciclo multiagente, `activity-observe`, un cálculo EMS ni una certificación integral del motor; no se atribuyen puntajes o recibos inexistentes.
- Los ajustes manuales finales del reporte y Beamer son identificación institucional, tipografía, referencias APA y rutas relativas. Regenerarlos desde el JSON requiere conservar esos ajustes de presentación.

## Mapa de soporte

| Afirmación o decisión | Fuente realmente consultada | Localizador y límite |
| --- | --- | --- |
| Objetivos claros, observables y verificables; específicos como metas parciales | [Material 3.3](../../../anteproyecto/vtaxi-2026-09-28/3.3-Formulacion-de-objetivos.pdf) | PDF completo de cuatro páginas; especialmente pp. 1–2. Se cita el material, no como lectura directa de los libros que enumera. |
| Continuidad del problema, preguntas y periodo | [T9](../../../entregas/Tarea9_DeLaCruzMunoz.docx) y [objetivos previos](../../../anteproyecto/vtaxi-2026-09-28/objetivos.json) | Comparación literal automatizada. No se altera el tema ni se presume aprobación del anteproyecto. |
| Distinguir taxis concesionados y transporte privado mediante ERT | [Ley conservada localmente](../../../referencias-seminario-i/vtaxi-2026-09-27/ley-movilidad-nl.txt) | Arts. 82–83 y 99–100. Revisión del corpus de 27/09/2026; no se afirma una reconsulta jurídica en línea al 04/10/2026. |
| ICET como institución formativa, no prueba de autorización de la aplicación | [Contenido institucional conservado](../../../referencias-seminario-i/vtaxi-2026-09-27/icet.txt) | Oferta de cursos de taxi y plataformas y descripción institucional. |
| Problema y objetivo general en Importante / No urgente | [Planeación de T10](../../../planeaciones-generadas/2026-II/revision-2026-09-15/planeacion-modulo-2910-tarea10-objetivos.md) y copia original de la consigna de 28/09/2026 | Exigencia didáctica expresa, no resultado de una lectura nueva de Covey ni afirmación sobre urgencia real de trámites. |
| Catálogo, diagnóstico, matriz de contraste y ruta | Contenido propuesto para el caso | Productos futuros de verificación, no documentos ya obtenidos ni requisitos atribuidos a una autoridad. |

La revisión inicial utilizó tres fuentes locales. Tras consultar T8 se añadieron Parker y Nielsen (2009), DOI 10.1177/0095399708328869, y Thelen (2018), DOI 10.1017/S1537592718001081. Sus metadatos y resúmenes editoriales están conservados en [referencias de retroalimentación](../../../referencias-seminario-i/actividad-10/retroalimentacion/). Solo se utilizaron afirmaciones contenidas en esos resúmenes; no se accedió al texto completo ni se revisaron sus bases de datos. Son antecedentes conceptuales específicos, no evidencia de vTaxi, de Nuevo León ni una actualización exhaustiva del estado del arte. Sus fechas no se contabilizan como sustitución de los diez estudios de T3.

[Verificación de doce DOI](../../../referencias-seminario-i/actividad-10/retroalimentacion/verificacion-dois.json): resolución y correspondencia de título aprobadas para diez referencias heredadas y dos nuevas. Crossref respondió inicialmente HTTP 429; se completó la comprobación mediante registros ya recuperados y negociación bibliográfica en doi.org. Este cotejo no equivale a releer los doce artículos ni a validar todos sus resultados.

## Evidencia técnica

[Recibo inicial](generacion.json), histórico de la versión de 19 páginas. [Generación con retroalimentación](generacion-retroalimentacion.json): original intacto, ampliaciones declaradas y conservación de la base corregida, referencias, geometría, franja institucional, encabezados, campos y nota nativa de IA. El PDF vigente de Word consta de 21 páginas. Las huellas finales actualizadas están en el manifiesto de validación, no en los recibos anteriores a formato y exportación.

Los originales no se modificaron. Se consultaron estados y comentarios de las siete actividades registradas, pero no se enviaron archivos, comentarios ni formularios al aula ni se alteró la calificación o el estado de entrega.

## Cierre de verificación local

[Validación final y huellas SHA-256](validacion-final.json), reproducible con [validar.py](validar.py): controles documentales aprobados, sin citas indefinidas ni desbordamientos en los registros finales. Objetivos completos y matrícula presentes en los tres PDF. [Reporte complementario](../../../reporte-seminario-i-Actividad-10.pdf): 12 páginas. [Presentación alineada](../../../presentacion-seminario-i-Actividad-10.pdf): 19 diapositivas. La revisión inicial examinó portadas, objetivos, matrices, Covey, cierre y referencias del reporte, y portada, índice, objetivos y anexos de Word. Tras las correcciones se revisaron las páginas modificadas de antecedentes, objetivos e indicadores y las diapositivas añadidas. No se atribuye revisión visual exhaustiva de todas las páginas.

El material docente y la consigna original tienen copias en [referencias de T10](../../../referencias-seminario-i/actividad-10/). La extracción de las cuatro páginas del PDF se conserva como salida determinista de PyMuPDF en `extractor-aulatex/conceptos-seminario-i-actividad-10/material-3.3-extraido.txt`; no equivale a ejecutar el extractor semántico multiagente.