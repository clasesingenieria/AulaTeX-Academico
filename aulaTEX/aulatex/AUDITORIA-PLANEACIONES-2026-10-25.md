# Auditoria de planeaciones y propuesta interinstitucional

Fecha: 2026-10-25. Estado: propuesta para adopcion, no migracion ejecutada.

## Dictamen

El repositorio cuenta con una convencion de carpetas y varias normalizaciones utiles, pero no con un contrato semantico unico consumido de extremo a extremo. Renombrar PDFs no resuelve la identidad de las actividades, la integridad de sus consignas ni la coherencia entre extractor, produccion y evaluacion. Se recomienda conservar los originales y generar una planeacion canonica JSON, independiente de la institucion, con una vista Markdown derivada y vinculaciones explicitas.

## Hallazgos prioritarios

| Prioridad | Hallazgo y evidencia | Riesgo | Medida propuesta |
| --- | --- | --- | --- |
| Alta | [planning_layout.py](planning_layout.py#L104) genera JSON y Markdown por `activity.id`; [extractor_adapter.py](extractor_adapter.py#L249) busca PDF/MD/TXT/DOCX por nombres, no JSON. | El modelo generado no es una entrada estructurada del extractor. El Markdown contiene bloques JSON, no necesariamente encabezados reconocibles. | Un lector canonico compartido; proyeccion compatible explicita mientras se migra. |
| Alta | [extractor_adapter.py](extractor_adapter.py#L249) equipara patrones de actividad y semana, recorre solo el primer nivel de `planeaciones*` y admite el target como ultimo recurso. | Una semana con varias actividades, un PDF multisemana o un reporte pueden convertirse en la consigna equivocada. Los originales anidados no se buscan ahi. | Resolver por materia, periodo y activity_id; rechazar ambiguedad; nunca usar el producto como su propia consigna. |
| Alta | [act2-100ciclos-monitor.ps1](../act2-100ciclos-monitor.ps1#L24) fija Activity=2 y un target cuyo nombre termina en Actividad-1. | Discordancia de identidad en la configuracion predeterminada. No se afirma que una ejecucion haya modificado el archivo equivocado. | Comprobar coincidencia entre actividad, producto y planeacion antes del primer lote. |
| Alta | [planeacion_parser.py](../extractor-conceptos-ideas/src/fichador/planeacion_parser.py#L29) representa temas, actividad y criterios como texto/listas; [document_reader.py](../extractor-conceptos-ideas/src/fichador/document_reader.py#L216) no lee JSON y devuelve texto vacio ante ciertos errores. | Se pierde estructura de preguntas, rubricas, plazos, dependencias y procedencia; un fallo de lectura puede parecer ausencia de informacion. | Importacion con errores tipificados, preservacion de estructura y validacion de completitud. |
| Media | [planeacion-S3-estructurada.md](../../UnADM/licenciatura-en-derecho-unadm/derecho-penal-especial-mexicano-lde/planeaciones-derecho-penal-especial-mexicano/planeacion-S3-estructurada.md) conserva conflictos, pero remite los hechos y preguntas completos al PDF. | El resumen es util para conceptos, pero insuficiente para ejecutar sin volver a la fuente. | Incorporar preguntas/casos completos o un recurso estructurado obligatorio, verificable por huella y localizador. |
| Media | [planeacion-S3-normalizada.md](../../UnADM/licenciatura-en-derecho-unadm/teoria-del-estado-y-constitucion-lde/planeaciones-teoria-del-estado-y-constitucion/planeacion-S3-normalizada.md) distingue instrucciones docentes, decisiones del estudiante y formatos discordantes. | Si se fusionan sin procedencia, una preferencia editorial puede presentarse como autorizacion docente. | Estado por campo, conflictos pendientes y excepciones con alcance y autoridad explicitos. |
| Media | [planeacion-modulo-49859.json](../../UAS/licenciatura-en-contaduria-uas/derecho-mercantil/planeaciones-derecho-mercantil/planeacion-modulo-49859.json) usa `1.0-uas-planeacion`, objetivos propuestos y contrato de artefactos 1.0 con entregas en `.`. | Mezcla de versiones; un foro de dudas no implica producto obligatorio. | Migrar sin inventar obligatoriedad, conservar propuestas como inferencias y recalcular rutas con el contrato 1.1. |
| Media | [intelligent_engine.py](intelligent_engine.py#L355) pasa target y numero al agente sin fijar una revision de planeacion; [activity_observer.py](activity_observer.py#L121) carga el resumen desde carpetas candidatas. | No queda garantizada por esas rutas una misma revision de consigna durante todos los ciclos. | Fijar id, revision y SHA-256; invalidar resultados derivados cuando cambie el contrato. |
| Media | 16 carpetas de mecatronica UANL conservan `-imtc`; [planning_layout.py](planning_layout.py#L12) lo elimina. | La ruta canonica calculada no coincide con el nombre existente. | Registrar alias de ubicacion y migracion trazable; no renombrar automaticamente. |

## Cobertura local

Inventario recursivo de las ocho instituciones proporcionadas. Cada archivo se conto una sola vez si un componente de su ruta comienza con `planeaciones`; se incluyeron originales anidados. Los conteos son de archivos, no de actividades ni de planeaciones aprobadas.

| Institucion | Carpetas planeaciones* | Archivos unicos | Formatos observados | Candidatos fuera de esas carpetas |
| --- | ---: | ---: | --- | ---: |
| IIIEPE | 0 | 0 | Ninguno en esas carpetas | 2 |
| ITESCA | 21 | 191 | JSON 82; MD 108; TXT 1 | 93 |
| tecnmNL | 0 | 0 | Ninguno en esas carpetas | 1 |
| UAdeC | 8 | 16 | MD 16 | 0 |
| UANL | 22 | 135 | DOCX 7; HTML 3; JSON 12; MD 27; PDF 18; PNG 34; PPSX 2; TXT 31; gitkeep 1 | 92 |
| UAS | 3 | 86 | JSON 34; MD 52 | 2 |
| UCNL | 7 | 39 | JSON 6; MD 24; PDF 9 | 1 |
| UnADM | 9 | 79 | JSON 1; MD 11; PDF 58; TXT 9 | 57 |
| Total | 70 | 546 | Materiales heterogeneos, incluidos indices y auxiliares | 248 |

Los candidatos externos se identificaron por `plan.md`, `programa-analitico*.md` o `planeacion*.(md|json|txt|pdf)` sin distinguir mayusculas. Pueden ser planes institucionales, indices o derivados: no equivalen a 248 consignas faltantes. La ausencia de carpetas no acredita ausencia de planeacion: IIIEPE y tecnmNL tienen candidatos externos.

El [inventario detallado](inventario-planeaciones-2026-10-25.json) contiene 794 registros unicos con SHA-256, ubicacion observada, ruta canonica esperada cuando puede inferirse, IDs declaradas en JSON y estado de cotejo. Clasificacion local: 425 archivos con ubicacion coherente, 105 derivados en `planeaciones-generadas`, 16 en rutas con alias/discrepancia y 248 candidatos externos. Hay nueve grupos de contenido identico; no se eliminaron duplicados. Los JSON examinados no presentaron errores de lectura/sintaxis, lo que no acredita conformidad pedagogica ni semantica.

El [auditor reproducible](../auditar-planeaciones.ps1) imprime JSON por defecto y solo escribe si recibe `-Output`; rechaza sobrescribir una auditoria previa. No incluye texto privado, URLs ni credenciales. Se usa, por ejemplo, con `./aulaTEX/auditar-planeaciones.ps1 -Output ./tmp/auditoria-planeaciones-nueva.json`. La materia observada se infiere por ubicacion; el campo `binding_state` permanece `pendiente_cotejo` en todos los registros. El inventario incorpora auxiliares y candidatos, no certifica cada entrada como una planeacion.

UnADM: Filosofia del Derecho e Interaprendizaje tienen fuentes PDF por semana; Interaprendizaje incluye TXT y contenidos de clase junto a las planeaciones. Teoria del Estado conserva un PDF S2-S3, y Penal originales docentes anidados. UAS e ITESCA ya ofrecen modelos por modulo; no conviene desechar esa informacion. UAdeC presenta consignas Markdown para preparacion de ingreso: el modelo debe admitir autoestudio, no solo tareas calificables. UANL agrega documentos, capturas y extracciones de plataforma. UCNL mezcla PDFs y modelos generados.

### Limites de la auditoria

Se inspeccionaron nombres y ubicaciones de todos los archivos de esas carpetas, y muestras de contenido y rutas de consumo. No se cotejo cada pagina de los 85 PDFs del inventario ni cada consigna contra la plataforma autenticada. No se certifica la vinculacion individual de las 546 entradas ni la vigencia actual de calendarios, notas o entregas. No se consultaron cuentas, ejecutaron examenes, iniciaron ciclos LLM ni modificaron originales.

La comprobacion exhaustiva posterior debe producir una fila por actividad: materia, periodo, id interno, id de plataforma, fuente y localizador, SHA-256, planeacion/revision, productos vinculados y estado `verificado`, `ambiguo`, `huerfano`, `sin_fuente` o `pendiente_cotejo`. Un indice o un PDF existente no permite marcar una actividad como verificada.

## Modelo Propuesto

Nombre: **Planeacion Canonica AulaTeX (PCA)**, version semantica `1.0.0`, estado de adopcion propuesto. Es un contrato de informacion, no un formato exclusivo de UnADM ni una plantilla de reporte. Su esquema esta en [planeacion-canonica.schema.json](planeacion-canonica.schema.json) y su ejemplo ficticio en [planeacion-canonica.ejemplo.json](planeacion-canonica.ejemplo.json).

### Unidad y jerarquia

Una planeacion corresponde a una materia y una oferta/periodo; contiene una o varias actividades. La jerarquia es institucion > programa > materia > oferta > unidad/bloque > actividad > producto. Semana, unidad y modulo son referencias independientes. Una actividad puede tener varios productos; un recurso puede sustentar varias actividades; dos modulos pueden servir el mismo PDF sin ser la misma actividad. Los IDs deben ser estables, no posiciones en una lista.

La identidad de plataforma es la tupla plataforma + course_id + module_id; no solo un numero. La identidad editorial incluye materia + oferta + activity_id. No derivar ninguna de ellas del nombre del archivo. El `plan_id` permanece estable entre revisiones; `revision` aumenta cuando cambia contenido normativo. Cambios incompatibles de estructura aumentan la version mayor del esquema.

### Diccionario de informacion

| Bloque | Informacion necesaria | Regla pedagogica/procedimental |
| --- | --- | --- |
| Identidad | Institucion, programa, materia, oferta, titulo, IDs, unidad, semanas, modalidad y rol | Periodo desconocido es `null`, nunca el anio inferido del archivo. Autoestudio y actividad de apoyo son roles validos. |
| Fuentes | Tipo, autoridad, URL saneada, archivo original, hash, fecha de captura, formato y localizadores | Conservar PDF/HTML/texto original; no confundir fuente de consigna con autoridad academica sustantiva. |
| Curriculo | Proposito, competencias, resultados de aprendizaje y temario jerarquico | Preservar la formulacion docente; separar la operacionalizacion propuesta. |
| Cognicion | Taxonomia identificada, nivel, verbo, objeto, condiciones y evidencia observable | No inferir nivel solo por un verbo. Justificar demanda real y guardar inferencia como tal. Admitir marcos distintos de Bloom. |
| Consigna | Texto integro, requisitos atomicos, preguntas/casos, restricciones y recursos obligatorios | No sustituir preguntas por resumen. Relacionar cada requisito con fuente, pasos y productos. |
| Secuencia | Orden, fase, accion, insumos, salida, verificacion y dependencias | Preparacion, construccion y revision con criterios de finalizacion observables; no instrucciones vagas de "hacer la actividad". |
| Alineacion | Relaciones resultado -> requisito -> paso -> producto -> criterio | Toda demanda evaluada debe ser trazable; no agregar una demanda por gusto editorial. |
| Evaluacion | Tipo diagnostico/formativo/sumativo/no evaluable, escala, ponderacion, criterios y descriptores | Rubrica docente separada de controles editoriales. Sin ponderacion conocida, `null`, no cero. |
| Productos | Tipo, destinatario, formato editable y de entrega, estructura, extension, nombre y accesibilidad | Foro puede ser texto publicable; examen/SCORM no se transforma automaticamente en informe LaTeX. |
| Calendario | Apertura, fecha esperada, vencimiento, cierre, zona y texto literal | Fechas independientes; no traducir "fecha esperada" a cierre tecnico. Preservar HC como literal si falta zona IANA confirmada. |
| Recursos | Referencias disciplinares, apoyos, casos, multimedia, derechos y necesidades de acceso | Notas y materiales de apoyo no se citan como autoridad en entregables. Recursos restringidos no se redistribuyen. |
| Politicas | IA, integridad, colaboracion, citas, intentos, tardanza, privacidad y accesibilidad | Mantener excepciones por actividad; no imponer investigacion a un diagnostico que la prohibe. |
| Vinculaciones | Rutas relativas de plan, originales, extractor, notas, investigacion y productos | Usar `subject_artifact_contract()`; plan_id/revision/hash en manifiestos derivados. |
| Calidad | Estado por campo, evidencia, faltantes, conflictos y revision humana | Completitud documental, preparacion para ejecutar y calidad editorial son controles distintos. |

### Datos ausentes y procedencia

Las claves nucleares siempre existen. Un escalar desconocido es `null`; una lista vacia significa que no hay elementos registrados, no que el bloque no aplique. `field_status` usa JSON Pointer RFC 6901 y declara `confirmed`, `inferred`, `unknown`, `not_applicable` o `conflict`. Toda confirmacion exige una evidencia con source_id y localizador; una inferencia requiere justificacion. Un bloque vacio/desconocido debe tener estado explicito. La ausencia de la clave es un error estructural.

Un estado de bloque puede cubrir descendientes cuando su razon distingue explicitamente las ausencias o propuestas que contiene; un estado mas especifico prevalece. No heredar `confirmed` a datos ausentes, ni mezclar confirmado e inferido bajo una etiqueta comun. El validador semantico debe expandir esa cobertura por campo antes de calcular completitud.

Ejemplo: `/activities/0/calendar/closes_at = null` con estado `unknown` no autoriza entregas fuera de plazo. Una rubrica inexistente se marca `unknown`; `not_applicable` necesita razon, como un foro de apoyo sin evaluacion. La revision humana puede validar una interpretacion sin convertirla en enunciado docente confirmado.

Los conflictos conservan valores y fuentes en `alternatives`; no se eliminan al fusionar. Una actualizacion docente verificada puede resolverlos; una preferencia del estudiante no la sustituye. Las excepciones registran autoridad, alcance, motivo y evidencia. Ninguna puntuacion editorial sustituye la nota docente.

### Formato humano

La vista Markdown se genera del JSON, nunca se mantiene como segunda verdad. Orden: identificacion y vigencia; proposito y resultados; temario; demanda cognitiva; consigna completa; recursos; secuencia numerada; productos; rubrica; calendario y politicas; alineacion; pendientes/conflictos; trazabilidad. Debe mostrar claramente dato docente, propuesta editorial y dato no documentado.

PDF es una exportacion opcional para lectura, no la entrada normativa del motor. El formato de entrega sigue la consigna institucional; la planeacion no aparece en el cuerpo del entregable ni introduce metadiscurso en abstract, desarrollo o foro.

### Ubicacion

Dentro de `planeaciones-<slug>/`, preservar archivos existentes y agregar `canonicas/<plan_id>/r<revision>/planeacion.json` y su vista `planeacion.md`. El indice de materia registra revisiones vigentes por oferta y actividad, originales y alias historicos. No seleccionar "el ultimo" por orden alfabetico o fecha de modificacion.

Las rutas de notas, entregas, referencias y extractor provienen del contrato 1.1; esta propuesta no modifica ese contrato. Un registro de vinculaciones debe resolver cada producto a activity_id, resultado de aprendizaje y requisitos, y cada extraccion a su plan_id/revision/hash. No deduplicar actividades por hash: solo deduplicar el almacenamiento de fuentes conservando todos sus localizadores de plataforma.

## Importacion y consumo

1. Capturar en solo lectura PDF, DOCX, HTML o instrucciones simples; conservar original, fecha, huella y URL sin credenciales. No iniciar intentos, SCORM/H5P ni publicaciones para obtener consignas.
2. Extraer preservando tablas, numerales, preguntas y localizadores. Para PDF escaneado usar OCR y cotejo visual; texto vacio o tablas rotas son incidencias, no informacion ausente confirmada.
3. Identificar materia/oferta/actividades por contexto verificado. Segmentar PDFs multisemana y fuentes multimodulo sin fusionar actividades distintas.
4. Mapear al nucleo PCA. Registrar texto literal y derivaciones por separado. Marcar faltantes, conflictos e inferencias, incluso cuando la entrada sea solo una instruccion breve.
5. Validar esquema, referencias, alineacion, integridad de recursos y reglas semanticas. Cotejar contenido critico contra la fuente antes de habilitar produccion.
6. Publicar revision inmutable y vista humana; conservar revision anterior. Actualizar indice solo cuando la validacion correspondiente sea satisfactoria.
7. Resolver explicitamente actividad y revision; entregar una proyeccion de lectura a cada modulo, nunca pedirle que vuelva a adivinar la planeacion.

| Consumidor | Proyeccion necesaria | Cambio de integracion propuesto |
| --- | --- | --- |
| Extractor de conceptos | Temas/subtemas, resultados, conceptos explicitos, demanda cognitiva, preguntas, recursos y fuentes disciplinares | Cargar JSON estructurado; mantener origen de conceptos. Para compatibilidad, generar encabezados `Tema`, `Objetivo`, `Tecnica didactica`, `Actividad`, `Aprendizajes`, `Conceptos clave`, `Criterios de evaluacion` y `Referencias` que reconoce el parser actual. No usar esta proyeccion reducida para decidir entregas. |
| realizar-actividad | Consigna completa, producto, secuencia, alineacion, criterios, calendario, politicas y pendientes | PlanLoader/ResolvedPlan compartido; bloquear identidad ambigua o contenido critico faltante; seleccionar capacidades segun producto. |
| Observador/optimizador | Matriz de requisitos, productos, criterios y hashes del plan y recursos | Medir cobertura por ID y evidencia, ademas de calidad editorial; distinguir rubric_score de editorial_score. |
| Ciclos monitorizados | plan_id, revision, activity_id, SHA-256 y condiciones de parada | Comprobar contrato antes de cada lote; no cambiar revision silenciosamente al reanudar. |
| Importadores institucionales | Campos propios de plataforma y sus localizadores | Adaptadores de entrada; diferencias institucionales van en datos/extensiones, no en ramas particulares del consumidor. |

La lectura actual del extractor tampoco soporta TEX en `read_any_text_file()`, aunque el adaptador lo admite en algunos candidatos: no habilitar TEX como consigna sin un lector definido. `resumen_planeacion.json` es un derivado, no la planeacion canonica. Las proyecciones deben conservar una referencia a su revision de origen y declarar las omisiones.

## Reglas de validacion

El JSON Schema adjunto valida estructura y tipos, no verdad documental ni preparacion para ejecutar. Las siguientes comprobaciones requieren un validador semantico en la futura integracion:

1. IDs unicos dentro de su alcance; enlaces a fuentes, resultados, requisitos, recursos, pasos, criterios y productos existentes; JSON Pointers de estado resolubles.
2. Materia/oferta/actividad/target coherentes y revision soportada. Varias coincidencias bloquean; no hay fallback al reporte.
3. Estados completos para datos `null`, bloques vacios y datos criticos. Confirmaciones con evidencia; inferencias con razon; conflictos con alternativas y resolucion trazable.
4. Consigna y preguntas completas, recursos obligatorios disponibles/verificados y requisitos cubiertos por productos o por acciones no documentales explicitas.
5. Alineacion pedagogica verificable; una actividad diagnostica o de apoyo puede no requerir todos los enlaces, con justificacion explicita. No inventar competencias o rubricas para completar celdas.
6. Rubrica consistente con su escala. Sumar pesos solo dentro de la misma escala y unidad; comparar contra el total documentado, no siempre contra 100.
7. Calendario con zona verificada antes de convertir a UTC; orden temporal coherente donde proceda. Cierre desconocido impide envio automatico, pero no necesariamente lectura o elaboracion local.
8. Rutas relativas seguras dentro de la materia, fuentes y productos existentes cuando corresponda; hashes coincidentes, sin secretos ni datos personales innecesarios.
9. Cambios de consigna/criterios invalidan derivados afectados. Reanudacion exige la misma huella o nuevo ciclo autorizado y documentado.
10. Autorizar elaboracion no autoriza envio. Revision `ready` nunca concede acceso a publicar, responder evaluaciones o modificar la plataforma.

## Adopcion gradual

Primera fase: acordar vocabulario, granularidad e identidad; revisar esquema/ejemplo. Segunda: piloto de Filosofia e Interaprendizaje (PDF), Penal/Teoria del Estado (conflictos y multisemana), UAS/ITESCA (plataforma/JSON), UANL (recursos mixtos), UCNL (evaluaciones interactivas) y UAdeC/IIIEPE/tecnmNL (autoestudio/programa analitico). Tercera: lector y validador compartidos, proyecciones y pruebas aisladas. Cuarta: migracion por materia, con registro de vinculaciones y cotejo critico. Quinta: habilitar ciclos solo para revisiones validadas y medir cobertura.

Pruebas de aceptacion: mismo contrato para todas las instituciones; PDF multisemana no mezcla consignas; varias actividades por semana no colisionan; un archivo con sufijo historico resuelve por alias; diagnostico conserva prohibicion de investigar; foro de dudas no se vuelve obligatorio; rubrica de 15 puntos no se normaliza arbitrariamente; preguntas completas sobreviven importacion/exportacion; cambio de fuente detiene reanudacion; ningun dato inferido aparece como docente; ningun envio ocurre por importar una planeacion.

Indicadores: porcentaje de actividades con identidad resuelta, requisitos con evidencia, cobertura de alineacion, recursos verificados, conflictos criticos pendientes y derivados con revision fijada. Medir sobre actividades inventariadas, no sobre numero de PDFs o puntuacion global del motor.

## Entregables de esta auditoria

Se agregan este dictamen, un esquema estructural, un ejemplo ficticio, el auditor local y su inventario detallado; se enlazan desde el indice del proyecto. El lector canonico, el validador semantico, la migracion y el cotejo individual autenticado quedan propuestos, no implementados. No se declara ninguna planeacion real lista para ejecutar por la sola existencia del ejemplo o del esquema.
