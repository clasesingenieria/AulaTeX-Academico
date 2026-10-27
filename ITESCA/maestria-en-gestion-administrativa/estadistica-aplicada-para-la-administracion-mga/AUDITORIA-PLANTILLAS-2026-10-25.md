# Elección de plantillas y cotejo contractual

> Estado previo a la revisión de resumen, índice y fusión. La [revisión vigente](REVISION-RESUMEN-FUSION-2026-10-25.md) actualiza páginas, declaración IA y producto activo; las decisiones anteriores sobre conservar inmutable la entrega se refieren a la versión previa. La comparación editorial con UnADM sigue como antecedente.

Revisión del 25 de octubre de 2026. Ámbito: las actividades 1–5 de Estadística aplicada para la administración, sus informes raíz, la lámina de infografía y las plantillas locales. Se conservan nombres, portadas y los cuatro archivos ya enviados a Moodle.

## Dictamen

La plantilla de póster del proyecto es una base apropiada para componer una infografía con bloques y columnas. Necesita una adaptación local: el ejemplo original usa dimensiones de congreso, datos de autores, universidades y conferencia ajenos a ITESCA. El hecho de usar esa plantilla no acredita por sí solo claridad, rigor ni cumplimiento de la consigna.

Para las entregas actuales, la lámina TikZ A3 es válida: la consigna permite formato libre, incluye los conceptos, tipos de muestreo, cálculo del tamaño y aplicaciones, y contiene tres referencias. Se conserva exactamente como fue enviada. El informe raíz la incorpora completa entre el fundamento conceptual y su interpretación. La alternativa de póster es material editable para comparación y reutilización; no sustituye automáticamente la entrega.

La elección general es: **informe con la plantilla ITESCA de clase article; producto visual como PDF independiente de póster cuando convenga; inclusión del producto en el desarrollo del informe**. Las clases article y beamer no se mezclan dentro de un mismo documento.

El [criterio local de selección](assets-estadistica-aplicada-para-la-administracion/seleccion-plantillas.json) publica esta elección por tipo de producto. Es una regla editorial documentada; no se presenta como una modificación automática del enrutador global de AulaTeX.

## Coincidencia adaptada con UnADM

Se compararon las versiones que cumplen el contrato vigente, especialmente:

- [Filosofía del Derecho, Actividad 2](../../../UnADM/licenciatura-en-derecho-unadm/filosofia-del-derecho-lde/reporte-filosofia-del-derecho-Actividad-2.tex): introducción, desarrollo temático con fundamentos, cuadro e interpretación, y conclusión con posición, razón y consecuencia.
- [Interaprendizaje, Actividad 1](../../../UnADM/licenciatura-en-derecho-unadm/interaprendizaje-en-ambientes-virtuales-lde/reporte-interaprendizaje-en-ambientes-virtuales-Actividad-1.tex): conceptos, cuestionario de cuatro columnas, lectura conjunta y cierre profesional.
- [Interaprendizaje, Actividad 2](../../../UnADM/licenciatura-en-derecho-unadm/interaprendizaje-en-ambientes-virtuales-lde/reporte-interaprendizaje-en-ambientes-virtuales-Actividad-2.tex): preparación conceptual, producto central y lectura posterior dentro de un mismo desarrollo.

La coincidencia está en el criterio editorial: problema → conceptos → producto → interpretación → postura y consecuencia. En Estadística se aplica a población, diseño muestral, incertidumbre, estimación y decisiones administrativas. Se conservan materia, docente, matrícula y portada propias de ITESCA; los ejemplos y enfoques jurídicos de UnADM no se trasladan como contenido estadístico.

La maestra histórica de Filosofía contiene apartados independientes de postura y otros ejemplos anteriores al contrato de tres tiempos. Por ello no se copia completa. El referente normativo es el [contrato vigente de AulaTeX](../../../aulaTEX/aulatex/activity_contract.py), junto con la consigna de cada tarea.

## Cotejo por actividad

| Actividad | Producto principal | Estructura y fundamento | Formato y evidencia |
| --- | --- | --- | --- |
| 1 | Infografía de muestreo | Introducción, desarrollo temático con conceptos, lámina original y lectura; conclusión razonada. | Informe raíz de 9 páginas con portada ITESCA; lámina A3 original de una página y tres fuentes. |
| 2 | Investigación sobre tres artículos | Marco conceptual, aplicaciones de Bradley, Barrero y Bloom, comparación y síntesis dentro del desarrollo; conclusión administrativa. | Cinco páginas incluidas portada y referencias; Arial 12, interlineado 1.5 y justificación. Portada conservada. |
| 3 | Investigación de estimación | Estimador y estimación, propiedades, puntual e intervalar, interpretación y transferencia administrativa. | Cinco páginas, portada conservada, Arial 12 y cuatro fuentes. |
| 4 | Ejercicios de distribuciones | Procedimientos e incisos dentro de un desarrollo; interpretación de resultados y supuestos explícitos. | Ocho páginas, portada conservada, Arial 12 e interlineado 1.5. La consigna no fija máximo de páginas. |
| 5 | Cuestionario de veinte reactivos | Marco conceptual, tabla horizontal No./Pregunta/Respuesta/Justificación, interpretación y conclusión. | Trece páginas; preguntas y respuestas literales, veinte justificaciones citadas y siete fuentes formales. |

Los cinco informes tienen exactamente tres secciones principales: Introducción, un desarrollo con título temático y Conclusiones. Las referencias forman el aparato documental. Los metadatos PDF de las cinco actividades incluyen título temático y `Actividad N - Estadística aplicada para la administración`. Las portadas no exponen módulos Moodle ni vencimientos.

El criterio de conclusión no se limita al encabezado final: cada desarrollo contiene una síntesis interpretativa natural y el cierre independiente agrega postura, razones y aplicación profesional. El póster o la tabla conserva protagonismo como producto; el marco conceptual lo prepara y la lectura posterior deriva sus implicaciones.

La investigación conceptual y la extracción de Nova Pro cuentan con resultados reales, fuentes y localizadores; se utiliza la versión revisada, no la salida cruda como autoridad. En el cuestionario se preserva el mapa reactivo → respuesta → fuente. La declaración de IA, cuando aparece, está en nota al pie; no se atribuye una revisión humana inexistente.

## Plantillas y rutas reales

El punto de entrada activo del informe es [la plantilla de actividad de la materia](reporte-estadistica-aplicada-para-la-administracion-plantilla-actividad.tex). Hereda [la maestra MGA de ITESCA](../reporte-itesca-mga.tex), que carga el núcleo `template` de `aulaTEX/base/Plantilla-Informe/`. Las referencias históricas a `ITESCA/_shared/` no describen la dependencia efectiva de estos informes en este checkout.

La ruta de póster integrada es `aulaTEX/base/latex/main_poster.tex` → `_template_poster_wrapper.tex` → `aulaTEX/base/Plantilla-Informe/template_poster.tex`. Utiliza beamer/beamerposter. La entrada `aulaTEX/base/entradas/main_poster.tex` carga el núcleo de informe y no es el modelo elegido para esta adaptación.

La configuración global del póster declara 65 × 82 cm y dos columnas. Una adaptación de Estadística debe fijar A3 vertical, jerarquía legible, colores y logotipo ITESCA, datos académicos correctos, referencias APA y una síntesis coherente con el muestreo. Esos ajustes deben ser locales; los originales del proveedor y las configuraciones de otras materias se conservan.

## Adaptación local de póster

Se preparó una [muestra A3 de muestreo](assets-estadistica-aplicada-para-la-administracion/poster/muestra-infografia-muestreo-alternativa.pdf) con el [adaptador reutilizable ITESCA](assets-estadistica-aplicada-para-la-administracion/poster/adaptador-poster-estadistica-itesca.tex), que carga el núcleo real de póster. Incluye diagrama TikZ, selección probabilística y no probabilística, cálculo de 385 respuestas y 482 invitaciones con sus supuestos, aplicaciones administrativas, síntesis, conclusión y tres referencias APA. La cabecera identifica materia, estudiante y docente; no requiere una portada independiente porque la consigna de la infografía no la solicita.

La [guía local](assets-estadistica-aplicada-para-la-administracion/poster/README.md) explica los hooks y las limitaciones de la integración. La muestra se identifica como alternativa local sin envío. Para usarla en un informe futuro, se compila por separado y se incorpora su PDF en el desarrollo; la portada oficial permanece en el informe ITESCA. El reporte raíz actual conserva su lámina original.

El [manifiesto de validación del póster](assets-estadistica-aplicada-para-la-administracion/poster/validacion-poster.json) confirma una página A3, carga del núcleo compartido, referencias y URLs completas, cálculos, límites de texto y revisión visual final. Los 96 archivos protegidos permanecen idénticos, incluidos los cinco reportes y los cuatro PDF enviados. La compilación no presenta desbordamientos, citas indefinidas ni caracteres ausentes. Conserva un aviso heredado de forma TS1 de Arial, registrado en el manifiesto; el cuerpo visible usa Arial y las fórmulas Latin Modern.

## Comprobaciones conservadas

- [Estructura, portadas y revisión visual](assets-estadistica-aplicada-para-la-administracion/validacion-estructura-reportes-2026-10-24.json).
- [Investigación de cinco páginas y cotejo Nova](referencias-estadistica-aplicada-para-la-administracion/notas-estadistica-aplicada-para-la-administracion/unidad-1-muestreo/validacion-actividad-2-2026-10-24.json).
- [Integridad y revisión visual del cuestionario](referencias-estadistica-aplicada-para-la-administracion/notas-estadistica-aplicada-para-la-administracion/cuestionario-2026-10-24/validacion-reporte.json).
- [Envíos efectivos y cotejo de las descargas](ENTREGAS-2026-10-24.md).

Las decisiones de composición se evalúan con el PDF renderizado y la rúbrica, además de comprobar estructura y compilación. La bibliografía manual de estas actividades y sus entradas `.bib` se mantienen concordantes; añadir una fuente a un archivo de bibliografía sin citarla visiblemente no basta.
