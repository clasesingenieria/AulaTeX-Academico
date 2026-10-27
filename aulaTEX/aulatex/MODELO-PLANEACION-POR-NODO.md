# Planeacion por nodo AulaTeX

Version: `1.0.0-node`. Fecha: 2026-10-26.

## Estado de implementacion

El [esquema por nodo](planeacion-nodo.schema.json), el [lector y publicador](node_planning.py), la entrada opcional del [agente](agent.py) y el comando [planeacion-nodos](cli.py) estan implementados. La [preparacion de propagacion](preparacion-planeaciones-2026-10-26/propagacion-planeaciones.md) contiene 614 nodos: proyecto 1, instituciones 8, carreras 11, materias 294 y actividades 300. Su [JSON asociado](preparacion-planeaciones-2026-10-26/propagacion-planeaciones.json) contiene un borrador estructural por nodo, padres, destinos propuestos y revisiones existentes.

La preparacion inicial no publico borradores ni convirtio fuentes. La fase posterior de [conversion y cotejo local](CONVERSION-PLANEACIONES-2026-10-26.md) ya publico 317 conversiones y 30 nodos vinculados, todos needs_review. No se declara ningun borrador listo para ejecutar. Las 300 actividades son las reconocidas por el catalogo editorial mediante TEX/marcadores; se deben incorporar actividades de plataforma y modelos por modulo todavia sin nodo antes de acreditar cobertura academica completa.

## Nucleo y perfiles

Cada nodo tiene una planeacion propia. Se reutilizan las identidades de `EditorialScope`: el proyecto corresponde a `interinstitucional`; no se crea otro nodo paralelo llamado proyecto. La jerarquia admite materias directamente bajo una institucion cuando asi lo representa el catalogo: no se inventa una carrera intermedia.

| Nivel | Funcion de la planeacion | Campos propios del perfil |
| --- | --- | --- |
| Proyecto | Direccion editorial y gobernanza del conjunto | Proposito, principios editoriales, puertas de calidad, hoja de ruta e instituciones |
| Institucion | Contexto academico y normativo | Mision, politicas academicas, plataformas, marco de calendario, carreras y materias directas |
| Carrera | Articulacion curricular y progresion | Perfil de egreso, competencias, mapa curricular, progresion y materias |
| Materia | Organizacion didactica y ofertas | Proposito, resultados, unidades, estrategia de evaluacion, ofertas y actividades |
| Actividad | Ejecucion de una demanda concreta | ID de actividad y oferta, proposito operativo, productos y controles de finalizacion |

El nucleo comun contiene version, plan_id, revision, node, profile, editorial_rules, provenance, review y bindings. `node` preserva key, level, parent_key, relative_path y label del catalogo. El plan_id es determinista respecto de la key; la revision es inmutable. Un traslado o renombrado que altere la key necesita un mapa de alias y migracion: no se interpreta como continuidad automatica de identidad.

Las claves del perfil existen aunque el contenido no se conozca. `null` y listas vacias no acreditan inexistencia; la procedencia los marca como desconocidos o no aplicables con razon. Los enlaces a hijos enumeran relaciones del catalogo, no resultados de aprendizaje comprobados. La validacion de esquema controla tipos y perfil por nivel, no la verdad institucional de los datos.

## Perfil pedagogico

El [modelo PCA anterior](planeacion-canonica.schema.json) se conserva como contrato pedagogico de materia/oferta con actividades, preguntas, recursos, secuencia, rubrica, calendario y politicas. No se duplican esos detalles en los perfiles estrategicos.

Un nodo materia puede vincular una PCA completa. Un nodo actividad debe vincular explicitamente su PCA local mediante path, SHA-256 y activity_id. El lector comprueba materia, oferta y una sola coincidencia de actividad. La institucion o carrera no pueden vincular una PCA como consigna propia. La actividad no usa automaticamente la PCA del padre.

Las vinculaciones son relativas a la raiz del proyecto y no admiten salir de ella. Los bindings de padre fijan archivo y huella y deben corresponder al padre real del catalogo. Los originales se preservan; los planes derivados registran fuentes y estados por campo en PCA/provenance. Materiales de apoyo y notas no se convierten en autoridad sustantiva para el entregable.

## Herencia y conflictos

Solo `editorial_rules` se combina en sentido descendente, siguiendo bindings explicitos: citation_style, language, accessibility y source_quality. La regla mas local no nula prevalece; su origen se conserva. Una lista local reemplaza la lista heredada, no la concatena silenciosamente. Un `null` no borra la regla del padre. Si se requiere una excepcion normativa, documentarla y cotejarla; cambiar una preferencia editorial no constituye permiso docente.

No se heredan perfiles, competencias, consignas, preguntas, rubricas, puntajes, plazos, intentos, politicas de IA ni productos. Las politicas institucionales del perfil permanecen como contexto con procedencia: su aplicabilidad debe resolverse en la PCA de la actividad. No hay propagacion lateral automatica de consignas ni propagacion ascendente de resultados como si fueran requisitos. Conflictos docentes/estudiante se conservan y bloquean cuando afectan la ejecucion.

## Almacenamiento

Proyecto, institucion y carrera: `planeaciones-aulatex/canonicas/<plan_id>/r0001/planeacion.json` y `planeacion.md` dentro del nodo. Materia y actividad: la misma estructura bajo la carpeta de planes obtenida de `subject_layout()`. Las actividades que comparten carpeta de materia tienen distintos plan_id; no colisionan. El Markdown se genera del JSON y no debe editarse como segunda fuente normativa.

El publicador valida esquema, identidad, versionabilidad y preservacion. Repetir exactamente el mismo modelo es idempotente; cambiar una revision existente se rechaza antes de reemplazar archivos. Los consumidores seleccionan una ruta/revision explicita, nunca la ultima por orden alfabetico. El manifiesto de preparacion no es un indice de revisiones aprobadas.

## Integracion disponible

`agent --node-plan <ruta-relativa>` activa el lector antes del planificador, llamadas LLM o materializacion. Sin esa opcion, el flujo anterior permanece para compatibilidad durante la migracion. No se activa globalmente un nuevo contrato obligatorio sin convertir las fuentes.

Con planeacion explicita, el agente resuelve la identidad y la cadena de padres, verifica hashes y escribe `planeacion-resuelta.json` en su corrida. Agrega el contrato completo al contexto de los roles y registra la cadena en el manifiesto. Si hay PCA local, genera `planeacion-extractor.md` con encabezados compatibles y la suministra al adaptador del extractor. Esa proyeccion no es el contrato normativo ni una sustitucion de las preguntas completas.

Para `realizar-actividad`, el lector exige nodo de actividad existente, identidad coherente, revisiones `ready` y PCA local `ready`. Un archivo cuyo numero de actividad contradice el solicitado se rechaza. `ready` exige declaracion de validacion semantica satisfactoria y ausencia de faltantes criticos; el esquema no demuestra que el cotejo humano o institucional realmente se haya efectuado. La produccion debe permanecer deshabilitada hasta completar ese cotejo.

## Integracion siguiente

| Componente | Contrato que debe consumir en la siguiente fase |
| --- | --- |
| Motor inteligente de campañas | Indice de revisiones aprobadas por key/oferta; pasar la ruta exacta a AgentRequest.node_plan por objetivo, no un plan general a todas las actividades |
| Monitor y optimizador | Snapshot y cadena resuelta de la corrida; comparar requisitos por ID y no recuperar otra consigna desde nombres de archivos |
| Reanudacion por lotes | Fijar hashes antes de cada lote y rechazar reanudacion si cambian; el snapshot de una corrida no garantiza por si solo la estabilidad entre campañas |
| Conversores PDF/HTML/DOCX/texto | Preservar originales, tablas, preguntas y localizadores; mapear a PCA y al perfil del nodo; nunca marcar ready por mera extraccion |
| Validador semantico | Verificar referencias, cobertura por campo, alineacion, escalas, calendario, recursos, conflictos y aprobacion; no limitarse a leer semantic_validation=passed |
| Catalogo e indice | Descubrir actividades sin TEX/marcador, registrar IDs de plataforma/oferta y alias; evitar duplicados y nodos ficticios |

Estas integraciones de campañas, reanudacion y validacion academica exhaustiva estan definidas, no activadas globalmente. La conexion inicial al agente es operativa y opcional; no se presenta como migracion completa de todos los consumidores.

## Operacion y propagacion

Preparar en una carpeta nueva, sin publicar planeaciones:

```powershell
./aulaTEX/aulatex.ps1 planeacion-nodos --mode prepare --output ./tmp/preparacion-nueva
```

Validar o publicar un modelo por nodo revisado, con identidad exacta:

```powershell
./aulaTEX/aulatex.ps1 planeacion-nodos --mode validate --source <modelo.json> --scope-key <key>
./aulaTEX/aulatex.ps1 planeacion-nodos --mode publish --source <modelo.json> --scope-key <key>
```

`publish` registra archivos, no concede aprobacion ni envia productos. El esquema usa jsonschema, registrado en [requisitos del motor](../requirements-aulatex-langchain.txt).

Orden de propagacion: proyecto -> instituciones -> carreras -> materias -> actividades. Completar y cotejar cada perfil, resolver padres y fijar hashes; convertir la PCA por oferta/actividad; publicar revisiones; producir un indice de aprobadas; habilitar consumidores por materia piloto; solo despues ampliar campañas. Las materias directas de institucion siguen su padre real.

Condiciones para conversion masiva: identidad de actividad/oferta resuelta, recursos fuente preservados, conflictos registrados, preguntas completas, rubrica y calendario diferenciados, Markdown regenerable, original intacto y validacion satisfactoria. Los faltantes quedan pendientes en el manifiesto: no se llenan mediante invencion ni herencia de datos de otra actividad.

## Verificacion

Las [pruebas aisladas](../test_node_planning.py) cubren los cinco perfiles, preservacion e idempotencia, hashes de padres, identidad/oferta, herencia limitada, bloqueo de borradores antes de llamadas, manifiestos sin publicacion, materias directas y UAdeC. El conjunto focalizado ejecutado pasa 27 pruebas. Una prueba antigua del materializador espera inventario 1.0 frente al 2.0 actual; se separo de esa ejecucion y no se modifico su contrato para esta tarea.
