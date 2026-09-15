# Contrato propuesto: realizar-planeación

Fecha: 2026-09-15. Versión de la especificación: 0.1. Estado: **propuesta documental, no implementada**.

Nombre visible: **realizar-planeación**. Identificador técnico propuesto: `realizar-planeacion`.

## 1. Dictamen y alcance

Es viable construir una planeación para una actividad concreta de cualquier institución a partir de una redacción, consigna, programa, rúbrica y otros documentos proporcionados. Las planeaciones UnADM ofrecen una estructura de referencia, **no una política universal ni una fuente para completar datos de otra institución**.

La premisa requiere un matiz: otras instituciones del repositorio sí tienen consignas, rúbricas y carpetas de planeaciones; lo que no siempre existe es un documento integrado y homogéneo. La acción debe cubrir tanto esa integración como la propuesta de componentes ausentes.

La primera versión se limita a **una actividad**, que puede tener varios productos, sesiones o dependencias. No genera por defecto el programa completo, todas las actividades de una materia ni una planeación semestral. Unidad, semana y curso son contexto; no son sinónimos de actividad.

| Concepto | Responsabilidad |
| --- | --- |
| `realizar-planeacion` | Diseñar o normalizar propósito, secuencia, evidencias, evaluación, recursos y condiciones de una actividad. |
| `realizar-actividad` | Elaborar la respuesta o producto solicitado al estudiante. |
| Plan del motor | Ordenar operaciones de memoria, extracción, generación y validación. |
| Plan editorial de construcción | Organizar nodos, memoria fundacional y maquetas; no equivale a una planeación didáctica. |

**Resultado esperado:** una planeación derivada, trazable y revisable; nunca un documento presentado como emitido o aprobado por la institución sin evidencia de ello.

## 2. Evidencia del repositorio

Revisión estática de código, consignas y extracciones textuales existentes. No se consultaron plataformas educativas ni se verificaron visualmente los PDF originales. Una extracción o nota local no acredita por sí sola vigencia, fidelidad al original ni aprobación docente.

| Caso | Evidencia observada | Consecuencia para el diseño |
| --- | --- | --- |
| UnADM, Seguridad Social S7 | [Planeación extraída](UnADM/licenciatura-en-derecho-unadm/derecho-a-la-seguridad-social-lde/planeaciones-derecho-a-la-seguridad-social/Planificacion%20de%20actividades%20S7%20-%20Derecho%20a%20la%20seguridad%20social.txt#L144-L274): objetivo, contenidos, cuadro sinóptico, recursos, tiempo y entrega. | Base para la estructura pedagógica; valores particulares no transferibles. |
| UnADM, Interaprendizaje S7 | [Actividad colaborativa](UnADM/licenciatura-en-derecho-unadm/interaprendizaje-en-ambientes-virtuales-lde/planeaciones-interaprendizaje-en-ambientes-virtuales/Planificacion%20de%20actividades%20S7%20-%20Interaprendizaje%20en%20ambientes%20v.txt#L280-L440): cero puntos, Teams, aviso y continuidad en semanas posteriores. | Separar obligatoriedad, puntuación, evidencia, canal de entrega y aviso. |
| UnADM, extracciones imperfectas | [Resumen derivado con advertencias](UnADM/licenciatura-en-derecho-unadm/derecho-a-la-seguridad-social-lde/extractor-aulatex/conceptos-derecho-a-la-seguridad-social-actividad-5/resumen_planeacion.json#L145-L166). | Los datos extraídos necesitan localizador, revisión y conflictos explícitos. |
| ITESCA, mapa conceptual | [Consigna](ITESCA/maestria-en-gestion-administrativa/fundamentos-de-gestion-administrativa-mga/referencias-fundamentos-de-gestion-administrativa/actividad-2-mapa-conceptual-consigna.md#L1-L29): actividad local 2, identificador del aula 1.2, individual, PDF y 5 %. | Identificadores distintos; conservar porcentaje sin inventar su base si no está documentada. |
| ITESCA, Seminario I | [Consigna de formato institucional](ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/planeaciones-seminario-i/unidad-2/actividad-06-formato-institucional.md#L1-L44): Word y puntuación de unidad. | El PDF de la planeación no cambia el formato de la evidencia exigida. |
| UANL, responsabilidad social | [Consigna](UANL/ingeniero-agronomo/responsabilidad-social-y-desarrollo-sustentable/planeaciones-responsabilidad-social-y-desarrollo-sustentable/consigna-Actividad-1.md#L3-L59): cuadro, diapositivas y escalas de evaluación distintas. | Admitir varios productos y separar rúbrica de ponderación. |
| IIIEPE, fundamentos I | [Consigna](IIIEPE/maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/actividad-2-consigna.md#L1-L15): tres reportes dentro de un informe, sin fecha ni ponderación en esa entrada. | No inventar calendario ni peso; una actividad puede contener subproductos. |

### Estado técnico actual

- El precedente es `REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT` en [scripts/aulatex/activity_contract.py](scripts/aulatex/activity_contract.py#L6-L260): declara entradas, fases, compuertas y reglas. La nueva acción debe tener contrato y evaluador propios.
- [scripts/aulatex/intelligent_engine.py](scripts/aulatex/intelligent_engine.py#L13-L35) admite memoria editorial y realización de actividad, **no** realización de planeaciones. Su inventario se basa en TEX existentes; no basta con agregar una etiqueta.
- [scripts/extractor-conceptos-ideas/src/fichador/planeacion_parser.py](scripts/extractor-conceptos-ideas/src/fichador/planeacion_parser.py#L10-L42) aporta tema, objetivo, técnica y actividad, pero no un modelo completo de calendario, rúbrica y procedencia por requisito.
- [scripts/aulatex/construction.py](scripts/aulatex/construction.py#L67-L80) recibe texto y un documento; su propósito es construir nodos editoriales, no esta nueva salida académica.
- [scripts/interfaz/interfaz/intelligent_dispatch.py](scripts/interfaz/interfaz/intelligent_dispatch.py#L390-L399) sustituye acciones de agente desconocidas por `realizar-actividad`. Esa ruta debe corregirse antes de admitir el nuevo nombre: una solicitud de planeación no debe terminar resolviendo una actividad.

## 3. Alternativas y recomendación

| Alternativa | Ventaja | Límite | Decisión |
| --- | --- | --- | --- |
| Copiar una planeación UnADM y reemplazar nombres | Poco trabajo inicial. | Arrastra políticas, objetivos, calendarios y rúbricas ajenos. | Descartar como mecanismo de generación. |
| Agregar instrucciones a `realizar-actividad` | Reutiliza el circuito existente. | Confunde planeación con respuesta; hereda reglas de tres actos y reflexión que no corresponden. | Reutilizar servicios, no el contrato ni su evaluación. |
| Acción hermana con modelo estructurado y perfiles | Separa responsabilidades y permite validación determinista. | Requiere nuevo ejecutor e integración de entradas sin TEX. | **Recomendada para la primera versión.** |
| Planeador de curso/unidad completo | Permitiría coordinar muchas actividades. | Amplía calendario, pesos y dependencias fuera de la solicitud puntual. | Evolución posterior, con otro alcance explícito. |

## 4. Contrato normativo de la acción

En esta especificación, **DEBE**, **NO DEBE** y **PUEDE** describen compromisos de la futura implementación, no capacidades disponibles hoy.

### 4.1 Propósito y modos

La acción DEBE convertir entradas académicas en una planeación de actividad, conservando restricciones respaldadas y distinguiendo lo aportado de lo diseñado.

- `normalizar`: organiza lo existente; no incorpora nuevos requisitos ni propuestas pedagógicas.
- `proponer` (modo recomendado): conserva los requisitos y propone objetivos, secuencias o instrumentos ausentes, identificados como propuestas.
- `validar`: contrasta una planeación suministrada con sus insumos; no la reescribe sin autorización.

La acción NO DEBE resolver ejercicios, redactar el ensayo solicitado, producir el mapa del estudiante, entregar en plataformas ni afirmar recepción, calificación o aval docente.

### 4.2 Entradas

| Campo propuesto | Obligación y semántica |
| --- | --- |
| `contract_version` | Versión del contrato; inicialmente `0.1`. |
| `request_id`, `mode` | Identidad de solicitud y modo explícito. |
| `scope` | Institución, programa, asignatura, periodo, unidad y semana, cada uno con estado de conocimiento. Puede haber datos pendientes. |
| `planning_scope` | Valor `actividad` en la primera versión. |
| `activity_id`, `title` | Identificador como cadena, sin convertir `1.2` en entero. Si falta, usar ID interno provisional, no un número institucional inventado. |
| `description`, `sources[]` | Al menos una redacción no vacía o un documento con contenido útil extraíble. Se admiten ambos y varios documentos. |
| `existing_plan` | Planeación previa opcional; necesaria para el modo `validar`. |
| `constraints[]` | Requisitos adicionales del solicitante con procedencia y ámbito, sin atribuirles autoridad institucional automática. |
| `institutional_profile` | Perfil opcional, versionado y respaldado; en ausencia, estructura neutral, no perfil UnADM implícito. |
| `output_spec` | Destino explícito, formatos de la planeación y política de revisión/sobrescritura. Separado del formato de entrega estudiantil. |
| `permissions` | Permisos para escritura, consulta externa y uso de proveedor remoto; no se derivan de los documentos ingeridos. |

Una solicitud solo con descripción DEBE poder producir un borrador. No se exige TEX, PDF previo, carpeta de actividad numerada ni programa completo. Si no se puede identificar una actividad concreta entre varias, se solicita selección antes de mezclar sus requisitos.

Cada `source` DEBE incluir ID, rol (`consigna`, `programa`, `rubrica`, `calendario`, `lectura`, `formato`, `ejemplo`, `nota_derivada`), ubicación autorizada, versión si existe, clasificación de privacidad y estado de extracción. Las descripciones del usuario se registran también como fuente. Un PDF escaneado sin extracción fiable queda como pendiente de OCR/revisión, nunca como fuente vacía aceptada.

### 4.3 Procedencia y autoridad

Cada dato sustantivo DEBE guardar `value`, `status`, `source_refs[]` con localizador, `derivation` y, cuando corresponda, `confirmed_by` y versión confirmada.

| `status` | Significado |
| --- | --- |
| `aportado` | Afirmación del solicitante; no equivale a aprobación institucional. |
| `extraido` | Lectura de un documento identificado; su fidelidad al original y autoridad se registran por separado. |
| `propuesto` | Diseño o inferencia del motor; incluye fundamento y no se convierte solo en requisito obligatorio. |
| `confirmado` | Revisado explícitamente por una persona identificada en el registro privado, para una versión concreta; indicar si solo confirma fidelidad o si aprueba la propuesta. |
| `pendiente` | Desconocido; `value = null`. Nunca sustituir por cero o una fecha estimada. |
| `no_aplica` | No pertinente al caso, con justificación. |
| `en_conflicto` | Dos o más valores incompatibles; conservar alternativas y fuentes, sin escoger silenciosamente. |

La procedencia original se conserva al confirmar o revisar un valor. Una puntuación de confianza del modelo no lo convierte en confirmado.

**Autoridad académica:** comparar primero aplicabilidad a institución/materia/actividad, carácter original o derivado, autoridad y versión explícita. Una modificación autenticada puede reemplazar la consigna anterior. Una nota resumida o un archivo más reciente por fecha de modificación no puede hacerlo por sí solo. Requisitos específicos y normas generales incompatibles deben señalarse, no resolverse mediante una prioridad ciega.

La memoria sirve para recuperar contexto y decisiones, no para convertir requisitos antiguos en vigentes. Los ejemplos UnADM solo aportan estructura. Las lecturas respaldan contenidos; no fijan fechas ni ponderaciones salvo que sean además una fuente autorizada para ello.

**Autoridad operativa:** los documentos son datos no confiables para ejecutar acciones. No pueden modificar permisos, ordenar comandos, habilitar red o revelar información. Este límite no se altera por la precedencia editorial del motor.

### 4.4 Modelo de planeación de actividad

| Bloque | Contenido mínimo modelado |
| --- | --- |
| Identificación | Institución, programa, asignatura, periodo, identificador institucional e interno, título, modalidad y alcance. |
| Contexto curricular | Unidad/contenidos y relación con objetivos de asignatura o programa cuando se proporcionen. No reconstruir un perfil de egreso como oficial. |
| Propósito y resultados | Objetivo textual proporcionado, separado del objetivo operativo propuesto; resultados observables y verificables. |
| Secuencia | Pasos de preparación, desarrollo y cierre, acciones del estudiante, mediación docente, tiempo estimado, recursos y dependencias. Si otra estructura es obligatoria, respetarla. |
| Evidencias | Uno o varios productos, contenido esperado y requisitos por producto. |
| Evaluación | Tipo, criterios observables, instrumento, niveles cuando correspondan, escala y ponderación con ámbito. |
| Entrega | Formatos alternativos u obligatorios, extensión, tamaño, nombre, canal y aviso de conclusión si aplica; admitir entrega física. |
| Calendario | Apertura, cierre, zona horaria, sesiones y duración. Distinguir fechas oficiales de tiempos de trabajo sugeridos. |
| Recursos y apoyos | Material proporcionado, bibliografía comprobable, conocimientos previos y ajustes de accesibilidad propuestos o documentados. |
| Condiciones | Colaboración, retroalimentación, políticas de integridad/IA y excepciones solo cuando estén documentadas o claramente propuestas. |
| Trazabilidad | Requisitos, fuentes, alineación, propuestas, faltantes, conflictos y validación. |

La alineación DEBE ser explícita: **resultado → contenido → paso de actividad → evidencia → criterio**. Se permiten relaciones muchos-a-muchos. Un objetivo sin evidencia observable, o un criterio sin relación con la tarea, se señala y se corrige o justifica.

**Evaluación:** separar `instrument_max_score`, pesos internos de criterios y `activity_weight` con unidad y ámbito (`actividad`, `unidad`, `curso` o desconocido). Solo comprobar suma a 100 cuando la escala sea porcentual y el conjunto esté completo. No exigir que una actividad aislada sume el curso entero. Cero puntos es válido y no implica que la actividad sea opcional. Una lista de cotejo puede ser más pertinente que una rúbrica; no imponer rúbrica universal. Si falta ponderación oficial, puede proponerse un instrumento diagnóstico sin adjudicarle peso oficial.

**Calendario:** verificar apertura ≤ cierre únicamente cuando ambos estén disponibles. No inferir semana a partir del número de actividad ni zona horaria a partir de la institución. Los tiempos estimados deben concordar con los pasos y la carga informada; su carácter propuesto permanece visible.

### 4.5 Fases del proceso

| Fase | Compromiso | Salida verificable |
| --- | --- | --- |
| `resolve_request` | Delimitar actividad, modo, destino y permisos. | Solicitud normalizada o necesidad de aclaración. |
| `load_context` | Consultar reglas locales y memoria pertinente, sin contaminación entre instituciones. | Contexto aplicable y descartes justificados. |
| `ingest_sources` | Inventariar, filtrar datos sensibles y extraer originales sin modificarlos. | Inventario y extracciones con localizadores. |
| `normalize_requirements` | Clasificar requisitos, versiones, vacíos y contradicciones. | Matriz de requisitos y conflictos. |
| `build_alignment` | Relacionar objetivos, contenidos, evidencias y criterios. | Matriz de alineación. |
| `design_sequence` | En modo `proponer`, diseñar únicamente lo ausente o autorizado. | Secuencia y propuestas fundamentadas. |
| `design_assessment` | Preservar instrumento aportado o proponer uno pertinente. | Criterios, escala y ponderación separadas. |
| `validate_plan` | Verificaciones estructurales, aritméticas, documentales y revisión pedagógica. | Compuertas con evidencia y severidad. |
| `render_plan` | Generar vistas consistentes desde el mismo modelo. | Documento legible y, si se solicita, exportación validada. |
| `review_and_finalize` | Corregir con límites y registrar confirmaciones humanas. | Versión final técnica o borrador con pendientes. |
| `offer_handoff` | Ofrecer una consigna estructurada al flujo de actividad, sin ejecutarlo automáticamente. | Paquete de transferencia ligado a versión. |

El ciclo de mejora DEBE tener límites configurables de iteraciones, tiempo y presupuesto, salida temprana al validar y cierre por falta de progreso. Propuesta inicial: máximo tres iteraciones automáticas; los conflictos de autoridad se consultan a la persona, no se intentan resolver mediante más llamadas al modelo. Agotar el límite no significa aprobar.

### 4.6 Compuertas y estados de salida

| Compuerta | Condición |
| --- | --- |
| `input_sufficiency` | Actividad delimitada y al menos un insumo útil; caso contrario, solicitud incompleta. |
| `source_traceability` | Todo requisito obligatorio tiene fuente y localizador; toda inferencia está rotulada. |
| `institutional_isolation` | No se importan identidad, sanciones, políticas, fechas o pesos de ejemplos ajenos. |
| `pedagogical_alignment` | Objetivo, pasos, evidencia y criterios son congruentes y realizables. |
| `assessment_consistency` | Escalas y ponderaciones coherentes en su ámbito, sin confundir desconocido con cero. |
| `schedule_consistency` | Sin fechas contradictorias ni tiempos incompatibles presentados como viables. |
| `delivery_fidelity` | Se conservan productos, formatos, canales y restricciones documentadas. |
| `source_integrity` | Sin referencias inventadas ni extracciones dudosas presentadas como verificadas. |
| `privacy` | Sin secretos, PII ni fragmentos privados en logs, manifiestos o muestras versionadas. |
| `artifact_consistency` | Documento y modelo coinciden; exportación solicitada válida y correspondiente a esta versión. |

Los resultados por compuerta son `cumple`, `no_cumple` o `no_aplica` justificado. Faltantes y dudas deben producir hallazgos explícitos, no aprobación implícita. Un promedio de calidad alto NO DEBE compensar un bloqueo crítico.

- `solicitud_incompleta`: no se identifica una actividad o no hay contenido útil.
- `borrador`: planeación útil, con propuestas o datos pendientes claramente visibles.
- `requiere_aclaracion`: conflicto de requisito crítico, actividad ambigua o aprobación humana necesaria para continuar.
- `validada_tecnicamente`: todas las compuertas aplicables satisfechas, sin bloqueos ni propuestas críticas pendientes; los desconocidos no críticos se justifican.
- `fallida`: error técnico no resuelto; se conservan diagnóstico seguro y último borrador válido, si existe.

La validación técnica NO es aprobación docente. La revisión humana y el eventual aval institucional se registran por separado con su alcance y evidencia. Fechas o pesos desconocidos pueden permitir un borrador; no siempre bloquean una planeación pedagógica. Sí bloquean afirmar un calendario o una ponderación definitivos, y cualquier operación posterior que dependa de esos valores.

### 4.7 Salidas, visibilidad y preservación

La primera versión debe entregar un modelo JSON y una planeación Markdown. TEX/PDF y DOCX se proponen como exportaciones posteriores explícitas; no anunciar soporte hasta disponer de renderizador y pruebas. La planeación puede describir un entregable Word aunque ella misma se publique en Markdown.

Salidas lógicas separadas:

1. Planeación normalizada con versión y procedencia por campo.
2. Documento legible: identificación, objetivo, secuencia, recursos, evidencias, evaluación y entrega.
3. Matrices de requisitos y alineación.
4. Relación de propuestas, faltantes y conflictos.
5. Informe de validación y manifiesto técnico mínimo.

Los objetivos, técnicas, pasos y criterios **sí son contenido visible** de una planeación. No aplicar la regla de ocultar criterios didácticos ni la estructura de tres actos de `realizar-actividad`. El título puede decir “Planeación de actividad”. No copiar declaraciones de IA que atribuyan análisis humano no verificado; cumplir la política aplicable y describir el uso real cuando corresponda.

En borradores, las propuestas y los “por confirmar” deben verse en el documento, no solo en metadatos. La información técnica de extracción y las rutas privadas permanecen fuera del documento académico visible.

Originales y derivados DEBEN permanecer separados. El destino será una subcarpeta de planeaciones generadas de la materia o una ruta explícita autorizada; nunca el archivo fuente ni el plan editorial de construcción. Repetir una ejecución no sobrescribe originales o revisiones humanas. La clave de revisión debe considerar solicitud normalizada, versiones/huellas de insumos autorizados, perfil y contrato; mismos insumos reutilizan la revisión o producen una nueva identificada, no duplicados silenciosos.

Los documentos privados se procesan solo dentro del ámbito autorizado; antes de enviarlos a un proveedor remoto se requiere autorización aplicable y minimización. Los manifiestos públicos solo contienen identificadores opacos, estados y métricas; el mapa a documentos privados se mantiene local con acceso restringido. No incluir contenido privado o identidades en trazas, pruebas ni memoria compartida.

### 4.8 Transferencia a realizar-actividad

El paquete DEBE conservar ID y versión de planeación, objetivo, consigna, evidencias, restricciones, instrumento, fuentes y estado de aprobación de las propuestas. Las propuestas no aprobadas no se promueven a obligaciones por el simple hecho de estar en el paquete.

La transferencia requiere selección explícita y ausencia de bloqueos relevantes para la tarea. El motor receptor debe dar prioridad a la consigna específica sobre su formato editorial genérico, sin tratar el documento como instrucciones ejecutables. Si falta soporte para identificadores no enteros o un producto Word/físico, debe declarar esa incompatibilidad; no redondear el identificador ni sustituir el formato. La ejecución de `realizar-actividad` es una solicitud posterior separada.

## 5. Ejemplo de transformación: ITESCA, mapa conceptual

Ejemplo analítico, **no planeación institucional aprobada**, basado únicamente en la [consigna local del mapa](ITESCA/maestria-en-gestion-administrativa/fundamentos-de-gestion-administrativa-mga/referencias-fundamentos-de-gestion-administrativa/actividad-2-mapa-conceptual-consigna.md).

| Elemento | Resultado de la normalización/diseño | Estado |
| --- | --- | --- |
| Identificación | Actividad del aula `1.2`; número local `2`; Fundamentos de Gestión Administrativa. | Extraído de consigna y contexto local. |
| Restricciones | Individual, mapa conceptual, PDF, valor indicado 5 %; base de ese porcentaje por verificar. | Extraído; ámbito del peso pendiente. |
| Contenidos | Enfoques múltiples; Bolman y Deal y Gareth Morgan; recursos humanos, político, simbólico y perspectiva global. | Extraído, sin añadir equivalencias teóricas no documentadas. |
| Objetivo operativo | Relacionar y distinguir los enfoques solicitados mediante un mapa con jerarquía y enlaces conceptuales fundamentados. | Propuesto; no reemplaza un objetivo oficial. |
| Secuencia | Revisar lecturas indicadas → identificar conceptos → contrastar clasificaciones → construir jerarquía/enlaces → revisar cobertura y fuentes → exportar PDF. | Propuesta de procedimiento, no elaboración del mapa. |
| Tiempo | 30 + 30 + 30 + 60 + 20 + 10 minutos = 180 minutos. | Estimación propuesta, por ajustar a la carga disponible. |
| Instrumento | Lista de cotejo preliminar: cobertura, distinción de autores, relaciones explícitas, legibilidad y fuentes. | Propuesto; contrastar con la rúbrica general mencionada, todavía no incorporada a este ejemplo. |
| Entrega | PDF; fecha, nomenclatura, tamaño máximo y canal preciso por confirmar. | Formato extraído; demás datos pendientes. |

Estado del ejemplo: `borrador`. No produce el mapa, no inventa la rúbrica oficial y no transfiere calendario ni sanciones de UnADM. La mención de una rúbrica en una consigna no equivale a haber leído y validado sus criterios.

## 6. Integración propuesta en motor-inteligente

No se habilita ningún comando con este documento. Los nombres de módulos nuevos son responsabilidades propuestas, no archivos existentes ni API publicada.

| Componente existente | Cambio requerido |
| --- | --- |
| [scripts/aulatex/intelligent_engine.py](scripts/aulatex/intelligent_engine.py) | Registrar la acción y su despacho; incorporar solicitudes basadas en insumos sin TEX; separar inventario de planeaciones y productos; mantener acciones predeterminadas existentes. |
| [scripts/aulatex/cli.py](scripts/aulatex/cli.py) | Añadir acción, modo, descripción, documentos repetibles, perfil y salida; ID de actividad como cadena. Unificar alias visible acentuado con el identificador ASCII. |
| [scripts/motor-inteligente-monitor.ps1](scripts/motor-inteligente-monitor.ps1) | Ampliar validaciones y traslado de parámetros; permitir seleccionar la nueva acción también en previsualización. |
| [scripts/interfaz/interfaz/intelligent_dispatch.py](scripts/interfaz/interfaz/intelligent_dispatch.py) | Reconocer la intención y rechazar acciones desconocidas; no convertirlas en `realizar-actividad`. |
| [scripts/aulatex/gui.py](scripts/aulatex/gui.py) | Formulario de insumos, actividad y modo; mostrar propuestas, faltantes y confirmaciones antes de transferir. |
| [scripts/aulatex/extractor_adapter.py](scripts/aulatex/extractor_adapter.py) | Seleccionar documentos explícitos, admitir carpetas anidadas y separar originales, notas y productos; evitar usar el entregable como autoridad de su propia consigna. |
| [scripts/aulatex/editorial_context.py](scripts/aulatex/editorial_context.py) | Contexto específico de planeación con procedencia por requisito y aislamiento institucional. |
| [scripts/aulatex/activity_contract.py](scripts/aulatex/activity_contract.py) | Mantener contrato de actividad; consumir transferencia validada sin imponer al planeador reglas de producto estudiantil. |

Responsabilidades nuevas propuestas: `PlanningRequest`/`PlanningResult`, `REALIZAR_PLANEACION_PIPELINE_CONTRACT`, `PlanningBuilder` y `PlanningObserver`, con esquema versionado y validadores deterministas independientes de la opinión del modelo. Las llamadas al modelo deberán reutilizar `AulaTeXLLMClient`; las operaciones frágiles, los mecanismos seguros de la suite.

Previsualizar significa describir acciones, permisos y destinos sin ejecutar generación, red ni escritura de productos. Si se conserva el comportamiento actual de guardar un manifiesto, la interfaz debe avisarlo; no denominarlo “solo lectura”. Los comandos propuestos y ejecutados deben derivar de la misma solicitud normalizada.

## 7. Casos de aceptación de la futura implementación

Estas son pruebas **por implementar**, no resultados de pruebas ejecutadas.

| Caso | Resultado exigido |
| --- | --- |
| Descripción sin TEX ni número institucional | Borrador de una actividad con ID provisional y procedencia de la descripción. |
| Descripción insuficiente o varias actividades ambiguas | Solicitud de aclaración, sin mezclar ni inventar. |
| Planeación UnADM ponderada | Conservación de requisitos, tiempos y escala documentados. |
| Actividad colaborativa de cero puntos | Conservación de cero, colaboración y dependencias; no descartarla como opcional. |
| ITESCA con ID `1.2` | Preservar ID del aula y número interno por separado. |
| Word obligatorio o entrega física | Mantener la evidencia exigida, independientemente del formato de la planeación. |
| IIIEPE sin fecha/peso | Datos pendientes explícitos; secuencia propuesta sin calendario ni peso inventados. |
| Rúbrica de 100 y peso de 5 % | Escalas distintas y ámbito registrado; no sumarlas ni confundirlas. |
| Conflicto entre consigna y calendario | Bloqueo de la fecha definitiva hasta resolución documentada. |
| PDF ilegible o extracción de tabla dudosa | Estado de extracción pendiente/fallido y revisión, no validación vacía. |
| Documento con instrucciones para ejecutar comandos | Tratarlo como datos; no cambiar permisos ni realizar acciones. |
| Datos personales en fuente de ejemplo | No copiarlos a otra institución, al proveedor sin permiso ni a logs. |
| Reejecución o revisión humana previa | Preservación de originales, historial e identidad de versiones. |
| CLI, monitor e interfaz | Mismo modo e insumos; ninguna ruta cae accidentalmente en realización de actividad. |
| Exportación solicitada que falla | No declarar paquete completo ni usar un PDF anterior como resultado nuevo. |
| Propuesta crítica pendiente con calidad alta | Mantener borrador/bloqueo; nunca aprobar por promedio. |

Las pruebas unitarias deben utilizar entradas sintéticas o anonimizadas; los ejemplos reales sirven para revisión local autorizada, no para copiar documentos privados a fixtures.

## 8. Entrega por etapas

1. **Esta entrega — análisis y contractualización:** documento estable, evidencia, alternativas, reglas y criterios de aceptación. Sin modificaciones operativas.
2. **MVP — contrato ejecutable:** esquema versionado, modelos, validadores, ingesta de texto/Markdown y de formatos adicionales solo con extracción comprobada; JSON + Markdown para una actividad. Pruebas sin LLM/red.
3. **Integración — ejecución real:** constructor, revisión pedagógica, despacho del motor, CLI, monitor e interfaz; pruebas de extremo a extremo con proveedores simulados y regresión de `realizar-actividad`.
4. **Exportación y transferencia:** renderizadores probados, validación del archivo generado, aprobación versionada y consumo explícito por el flujo de actividad.
5. **Ampliación futura:** planeaciones de unidad/curso y perfiles institucionales, después de validar la actividad puntual.

**Criterio de cierre:** anunciar `realizar-planeacion` como disponible únicamente cuando existan ejecutor, validación y pruebas de integración. Publicar un contrato en un manifiesto o aceptar el nombre en una lista no implementa la capacidad.
