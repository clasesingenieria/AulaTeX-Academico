# Conversion y cotejo local de planeaciones

Fecha: 2026-10-26. Estado: cotejo local por actividad y segmentaciones Penal S3-S5 publicados; monitor diagnostico ejecutado, habilitacion editorial bloqueada por evidencia pendiente.

## Cotejo vigente por actividad

El [cotejo-r3](conversion-planeaciones-2026-10-26/cotejo-r3/cotejo-actividades.md) y su [JSON](conversion-planeaciones-2026-10-26/cotejo-r3/cotejo-actividades.json) revisan 371 registros pedagogicos contenidos en las 317 conversiones del lote inicial. Los registros no son actividades institucionales unicas: hay fuentes alternativas y documentos multisemana. De esos registros, 224 permanecen sin segmentar, ninguno pasa todos los controles y el indice contiene cero nodos aprobados para ejecutar.

El lote proyecto-r4 y los cotejos-r1/r2 se conservan intactos. El cotejo-r3 selecciona explicitamente S3 r0002, S4 r0003 y S5 r0003, sin elegir automaticamente la revision mas nueva de ninguna otra fuente.

### Primer avance documental

Penal S3 dispone de [JSON r0002](../../UnADM/licenciatura-en-derecho-unadm/derecho-penal-especial-mexicano-lde/planeaciones-derecho-penal-especial-mexicano/importaciones/pca-59835c6a72ea8aba5dfc/r0002/planeacion.json), [Markdown derivado](../../UnADM/licenciatura-en-derecho-unadm/derecho-penal-especial-mexicano-lde/planeaciones-derecho-penal-especial-mexicano/importaciones/pca-59835c6a72ea8aba5dfc/r0002/planeacion.md) y [cotejo local](../../UnADM/licenciatura-en-derecho-unadm/derecho-penal-especial-mexicano-lde/planeaciones-derecho-penal-especial-mexicano/importaciones/pca-59835c6a72ea8aba5dfc/r0002/cotejo-local.json): cinco casos con sus hechos, quince preguntas, siete requisitos y siete criterios que suman quince puntos. La instruccion integra las paginas 6-8; la rubrica se coteja con la pagina 10. Se preservan los originales y sus huellas.

La revision sigue needs_review. El conflicto de extension conserva dos alternativas y evidencia separada: ocho cuartillas incluyendo identificacion y referencias segun la figura docente, frente a ocho paginas solo de cuerpo segun la preferencia editorial. El recurso PDF 216749 no se usa como ID de tarea ni el numero de semana como numero local de actividad. Quedan pendientes la correspondencia con nodo/oferta, recursos obligatorios, vigencia de plataforma y cotejo visual de la rubrica. No se produjo una aprobacion academica ni un envio.

### Ampliacion S4 y S5

| Semana | Revision JSON | Segmentacion | Rubrica | Estado |
| --- | --- | --- | --- | --- |
| S4 | [r0003](../../UnADM/licenciatura-en-derecho-unadm/derecho-penal-especial-mexicano-lde/planeaciones-derecho-penal-especial-mexicano/importaciones/pca-4dd40f72de8af2db1526/r0003/planeacion.json) | Tres casos y seis preguntas; tabla juridica, decision de cinco a siete lineas y PDF individual | Seis criterios, total 10 | needs_review |
| S5 | [r0003](../../UnADM/licenciatura-en-derecho-unadm/derecho-penal-especial-mexicano-lde/planeaciones-derecho-penal-especial-mexicano/importaciones/pca-3057c47ded95b7ad2de1/r0003/planeacion.json) | Tres fichas; cinco preguntas de procedimiento aplicadas a cada ficha, quince registros; columnas docentes preservadas | Siete filas suman 17, total impreso 15; dos filas Informe juridico conservadas | needs_review |

Cada revision tiene planeacion.md y cotejo-local.json junto al JSON; sus revisiones anteriores siguen intactas. S4 conserva tres alternativas de longitud: cuatro cuartillas incluyendo portada/referencias, seis segun observaciones y cuatro de cuerpo segun preferencia editorial. S5 conserva cuatro incluyendo portada/referencias, ocho segun observaciones y cuatro de cuerpo segun preferencia editorial. Ninguna alternativa editorial se eleva a confirmacion docente. S5 conserva el bloqueo rubric_total_mismatch; no se fusiona la fila repetida para aparentar conformidad.

El script de cotejo admite --week 3, --week 4 y --week 5. Los PDF completos y hashes originales permanecen preservados; la segmentacion no acredita fidelidad visual de tablas ni actualidad de los modulos.

### Publicacion y piloto

El publicador admite revisiones needs_review o ready y conserva JSON, Markdown y cotejo en una revision inmutable. Una revision ready requiere esquema valido, fecha y rol de revision, evidencia archivada y validacion semantica sin bloqueos. Cambiar solamente la etiqueta no habilita ejecucion. La vista Markdown refleja el estado real del JSON.

El [piloto-r2](conversion-planeaciones-2026-10-26/piloto-r2/campana-piloto.md) y su [JSON](conversion-planeaciones-2026-10-26/piloto-r2/campana-piloto.json) estan blocked para ejecucion editorial: cero actividades admitidas y monitor editorial desactivado. La etapa diagnostica observe_only esta habilitada. El piloto-r1 anterior se conserva. El valor inicial es una actividad y un ciclo; el limite del modo piloto es cinco actividades y dos ciclos. Ampliarlo exige una decision explicita y evidencia de los resultados, no una promocion automatica.

El [monitor-r1](conversion-planeaciones-2026-10-26/monitor-r1/monitor-planeaciones.md) y su [JSON](conversion-planeaciones-2026-10-26/monitor-r1/monitor-planeaciones.json) registran una instantanea diagnostica efectivamente ejecutada: 371 registros observados, 371 con bloqueos y cero cambios de hallazgos respecto al cotejo-r3. Revalida hashes y evidencia local, sin llamadas LLM, compilacion, parches ni envios. Es una instantanea bajo demanda, no un servicio continuo en segundo plano; nuevas observaciones requieren una salida nueva. El diagnostico no aprueba actividades aunque un registro llegue a quedar sin hallazgos.

La ejecucion explicita del piloto revalida indice, identidad, cadena y hashes antes de crear un monitor; ante el primer bloqueo detiene el lote. No aplica parches, no repara bibliografia, no ejecuta extractor ni realiza envios a plataforma. El monitor recibe --node-plan, archiva la PCA resuelta y usa su proyeccion cuando el extractor se habilita expresamente fuera de este piloto. Estos controles deterministas no certifican autorias, OCR/tablas o vigencia de plataforma por si solos.

Comandos disponibles, desde la raiz del proyecto:

```powershell
./aulaTEX/aulatex.ps1 cotejar-planeaciones --batch aulaTEX/aulatex/conversion-planeaciones-2026-10-26/proyecto-r4 --output tmp/cotejo-nuevo
./aulaTEX/aulatex.ps1 publicar-revision-planeacion --scope-key <materia-exacta> --source <PCA-revisada.json>
./aulaTEX/aulatex.ps1 campana-planeaciones --review <cotejo-actividades.json> --output tmp/piloto-nuevo --max-activities 1 --max-cycles 1
./aulaTEX/aulatex.ps1 monitor-planeaciones --review <cotejo-actividades.json> --output tmp/monitor-nuevo
./aulaTEX/aulatex.ps1 ejecutar-campana-planeaciones --campaign <campana-piloto.json> --output tmp/ejecucion-nueva
```

--revision permite seleccionar una PCA publicada para el nuevo cotejo, conservando plan_id y materia del lote. El nodo listo debe publicarse y seleccionarse explicitamente mediante planeacion-nodos; no se promueven sus padres pendientes por existir una consigna segmentada. Las carpetas de salida deben ser nuevas. El ejecutor rechaza el piloto-r2 actual porque esta bloqueado para ejecucion editorial.

Verificacion: 26 pruebas aisladas de nodos, publicacion, segmentacion y piloto; admision de fixture validado, rechazo de fuente cambiada antes de crear monitor, piloto vacio bloqueado, deteccion diagnostica de hash cambiado, preservacion de preguntas y rubrica S4/S5, fallback clasico sin accion indefinida e idempotencia de S3 r0002 comprobada. La admision editorial positiva se probo con un monitor simulado, no con llamadas LLM reales ni plataformas.

La suite ampliada de planeaciones ejecuto 42 pruebas: 41 pasaron y una fallo en test_planning_layout.py, test_materializer_uses_same_layout_and_preserves_existing_files. Espera schema_version 1.0 y TemplateMaterializer produce 2.0. El materializador y esa prueba no se modificaron en este trabajo; no se corrigio este desfase ajeno al flujo de cotejo. Los 14 enlaces locales del informe existen y los archivos Python modificados no presentan diagnosticos del editor.

## Resultado inicial preservado

El lote vigente es [proyecto-r4](conversion-planeaciones-2026-10-26/proyecto-r4/resultado-conversion.md), con [manifiesto JSON](conversion-planeaciones-2026-10-26/proyecto-r4/resultado-conversion.json), [indice de nodos](conversion-planeaciones-2026-10-26/proyecto-r4/indice-planeaciones.json) y [cola de cotejo por actividad](conversion-planeaciones-2026-10-26/proyecto-r4/cola-cotejo.json). Los lotes anteriores se conservan como historial, no como seleccion automatica de revisiones vigentes.

| Indicador | Resultado |
| --- | ---: |
| Materias inspeccionadas en el catalogo | 294 |
| Materias con fuentes reconocidas y convertidas | 36 |
| Conversiones de fuentes locales | 317 |
| Fallos tecnicos pendientes del lote final | 0 |
| Indices auxiliares omitidos | 1 |
| Planeaciones de nodo publicadas | 30 |
| Actividades con vinculacion documental unica publicada | 25 |
| Actividades en cola sin vinculacion explicita | 275 |
| Actividades reconocidas en el catalogo | 300 |
| Planeaciones aprobadas para ejecutar | 0 |

Una conversion no equivale a una actividad: un PDF puede abarcar varias semanas, y una materia puede conservar JSON y Markdown de la misma consigna. No se deduplicaron actividades por huella ni se eligio una consigna por semejanza de titulo. Las conversiones incluyen fuentes alternativas y documentos aun sin segmentar.

| Institucion | Conversiones | Observacion |
| --- | ---: | --- |
| ITESCA | 120 | Modelos JSON, Markdown y variante documental anterior; un indice separado |
| UAdeC | 16 | Consignas locales de preparacion; no se inventan evaluaciones de plataforma |
| UANL | 20 | Fuentes locales con contenidos pendientes de segmentacion |
| UAS | 65 | Modelos por modulo y textos asociados; propuestas diferenciadas |
| UCNL | 30 | Rutas preparatorias y otras fuentes; no se elevan a tareas oficiales |
| UnADM | 66 | PDFs y derivados; originales y localizadores por pagina preservados |
| IIIEPE y tecnmNL | 0 | Sin entradas reconocidas en carpetas de planeaciones; no significa ausencia de programas o fuentes externas |

## Implementacion

El [conversor](planning_conversion.py) admite JSON, PDF, DOCX, HTML y texto. Reconoce modelos con activity/activities, variantes documentales antiguas y rutas preparatorias no oficiales. Los indices se registran como auxiliares. No lee cuentas institucionales, inicia examenes, publica foros ni realiza envios.

Cada conversion conserva el JSON de origen completo o los bloques textuales con localizadores. PDF se extrae por pagina; DOCX por bloques del cuerpo; HTML elimina scripts y conserva texto; Markdown/TXT conserva el texto completo. El original binario permanece intacto. La extraccion textual no acredita fidelidad visual de tablas ni sustituye OCR/revision cuando el PDF carece de texto.

El nucleo PCA contiene identidad editorial, requisitos registrados, objetivos y temas explicitamente aportados, secuencia propuesta, productos, calendario literal, procedencia y faltantes. Lo no mapeado permanece en extensions.conversion.source_payload; no se elimina para adaptar el modelo. Un objetivo propuesto sigue siendo inferido; una rubrica general no se convierte en rubrica especifica; la fecha esperada no se convierte en cierre.

El offering_id generado es una identidad editorial interna, no un ID de oferta acreditado por la institucion. Cuando falta periodo, se registra como pendiente. Los documentos sin segmentar reciben un ID de fuente, no un numero inventado de actividad o modulo. Se conserva la necesidad de distinguir semanas, actividades y productos.

Las revisiones PCA se publican en `planeaciones-{slug}/importaciones/{plan_id}/rNNNN/` con planeacion.json, planeacion.md y cotejo-local.json. El ID depende de materia y ruta de origen; cambios en contenido o conversion incrementan revision. No se sobrescriben versiones anteriores ni originales. El Markdown se regenera del JSON.

## Vinculaciones publicadas

Solo se publican nodos de actividad cuando el modelo original documenta el numero local y la correspondencia es unica. Las 25 vinculaciones publicadas corresponden a Plan de Negocios y Fundamentos de Gestion Administrativa de ITESCA; se publicaron tambien sus padres para conservar cadenas completas, sumando 30 nodos. Todos permanecen needs_review.

Cada nodo fija path y SHA-256 de su padre y de la PCA vinculada. El indice aprobado esta vacio y las actividades restantes aparecen en la cola como pending_source_mapping. No se asignan consignas de UAS, UCNL o UnADM por similitud de nombres ni por equiparar numero de semana con actividad.

Los perfiles de padres publicados son estructuras pendientes, no nuevos programas institucionales aprobados. No heredan consignas, rubricas o fechas hacia las actividades. La disponibilidad de una cadena no habilita ejecucion.

## Validacion semantica

El [validador](planning_validation.py) comprueba esquema, IDs duplicadas, referencias a fuentes y requisitos, JSON Pointers, conflictos registrados, archivos y hashes, evidencia para consignas, cobertura de alineacion, productos, coherencia de la suma de rubrica y recursos obligatorios disponibles. Registra incidencias por codigo y localizador, sin divulgar contenidos privados en mensajes de error.

El lector exige estas comprobaciones antes de ejecutar una PCA marcada ready; cambiar solamente ready/semantic_validation en el JSON ya no evita los bloqueos. Una fuente local derivada no acredita autoria docente: la instruccion requiere evidencia de autoridad archivada para pasar la comprobacion. Los estados de revision y la declaracion humana siguen siendo necesarios, no sustitutos de las verificaciones.

Este validador es una primera puerta determinista, no una certificacion academica exhaustiva. No verifica automaticamente autorias contra la plataforma, fidelidad visual de tablas/OCR, todas las interpretaciones juridicas ni vigencia de calendarios. No resuelve conflictos docentes por inferencia. No se genero ninguna aprobacion automatica.

## Verificacion ejecutada

Las [19 pruebas aisladas](../test_node_planning.py) pasan. Cubren esquema por nivel, preservacion e idempotencia, revisiones nuevas, evidencia insuficiente, IDs/referencias/rubricas, fuentes JSON/texto/PDF, conservacion de paginas, variantes antiguas, cadenas de nodo y cola de cotejo sin vinculos inventados.

El cotejo del lote verifico las 317 huellas de fuentes originales, los hashes de los nodos publicados y sus bindings. Todos los resultados permanecen needs_review y el indice tiene cero aprobadas. No se consultaron plataformas para acreditar vigencia actual.

## Operacion

Para repetir un lote en una carpeta nueva:

```powershell
./aulaTEX/aulatex.ps1 convertir-planeaciones --output ./tmp/conversion-nueva --publish-node-bindings
```

Puede limitarse con --target a una institucion, carrera o materia. Los resultados existentes no se sobrescriben. El publicador reutiliza revisiones identicas o crea nuevas cuando cambian fuente o conversion.

## Bloqueos y siguiente cotejo

La habilitacion global de campañas permanece bloqueada. Primero se deben segmentar los documentos por actividad real, incorporar preguntas/casos y rubricas completas, documentar ID de modulo y oferta, resolver el origen de propuestas y confirmar fechas/politicas aplicables. Las 275 actividades sin correspondencia explicita requieren ese trabajo, no una asignacion automatica.

Prioridad documental: UnADM Filosofia e Interaprendizaje (PDF por semana), Penal y Teoria del Estado (casos y documentos multisemana), UAS (ID de modulo frente a nodo local), UCNL (ruta preparatoria frente a evaluacion oficial), UANL (fuentes mixtas), y programas analiticos fuera de planeaciones en IIIEPE/tecnmNL. El indice de aprobadas solo se llenara despues del cotejo; no se ejecutara una campaña por existir un PDF o una conversion.
