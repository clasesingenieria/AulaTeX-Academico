# AulaTeX-Academico

Entorno academico en LaTeX organizado por institucion, con una base comun de
plantillas Pizarror y puntos de entrada canonicos para reportes, actividades,
presentaciones y bibliografias.

La raiz conserva fuentes de ejemplo: [bibliografia](AulaTeX-Academico.bib),
[reporte](reporte-AulaTeX-Academico.tex),
[reporte de la actividad 1](reporte-AulaTeX-Academico-Actividad-1.tex),
[presentacion](presentacion-AulaTeX-Academico.tex) y
[presentacion de la actividad 1](presentacion-AulaTeX-Academico-Actividad-1.tex).

## Ubuntu y VS Code Remote SSH

El entorno Linux se instala con `bash setup.sh --no-shell --skip-llm` e incluye
TeX Live completo de Ubuntu 24.04 y un entorno Python independiente de Windows.
`bash setup.sh --all --no-shell` añade extracción documental, multimedia,
bibliotecas IA, entrenamiento CPU y notebooks, sin descargar modelos ni configurar secretos.
Consulta la [guía Linux](#guia-linux) para instalación, compilación,
perfiles opcionales y uso de [.vscode/AulaTeX-Linux.code-workspace](.vscode/AulaTeX-Linux.code-workspace).

## Entrenamiento del motor inteligente

La ruta progresiva está en `aulaTEX/notebooks/`, desde la verificación de la GPU hasta
la evaluación y publicación del adaptador. La lógica reutilizable vive en
`aulaTEX/aulatex_training/`; los notebooks no duplican el motor editorial.

El modelo no es un único archivo que haga peticiones. El sistema desplegable
combina el modelo base, un adaptador LoRA, tokenizer/configuración y código de
inferencia. Git conserva código, configuración, pruebas y manifiestos pequeños.
Los corpus privados, checkpoints y pesos quedan en `aulaTEX/data/private/`,
`checkpoints/` y `aulaTEX/models/local/`, ignorados por Git; la copia canónica debe
publicarse en S3 con versionado y cifrado.

Orden recomendado:

1. `00_entorno_y_gpu.ipynb`
2. `01_inventario_privacidad.ipynb`
3. `02_construccion_corpus.ipynb`
4. `03_analisis_y_splits.ipynb`
5. `04_reward_model.ipynb`
6. `05_sft_lora_generador.ipynb`
7. `06_evaluacion_exportacion.ipynb`

La estación A10G ejecuta pruebas y LoRA/QLoRA; para QLoRA se prefiere WSL2 o
Linux si `bitsandbytes` no funciona en Windows nativo. Nunca se copian secretos
a notebooks, datasets, salidas ni manifiestos.

## Flujo Principal

- Automatizacion de compilacion y exportacion: `aulaTEX/`.- Entrada recomendada para trabajo editorial: `aulaTEX/aulatex.ps1`.

### Interfaz de escritorio

Inicia la GUI con `./aulaTEX/aulatex.ps1`. Reinicia la ventana si ya estaba
abierta antes de actualizar el código.

- **Proyecto:** selecciona un nodo y pulsa **Usar selección** para aplicar su
  contexto a Investigación, Generación, Memoria y al objetivo del agente.
- **Investigación:** configura fuentes y consultas; los resultados se separan
  en Plan, Conocimiento, Métricas opcionales y Ejecución.
- **Producción:** reúne Generar, Revisar / ejecutar y Compilar. Los modos
  Revisar archivos y Ejecutar agente muestran únicamente sus opciones aplicables.
- **Memoria:** conserva la construcción, propagación y fijación de reglas,
  con vistas separadas para plan, memoria y ejecución.
- **Asistente:** mantiene sesiones persistentes. El texto del chat no ejecuta
  compilaciones. `/listar-tex` y `/explorar` son consultas locales de solo lectura.

El menú **Herramientas** contiene el extractor y la comprobación de proveedores.
**Configuración** separa proveedores IA de cuentas institucionales; ambas
pantallas conservan sus almacenes originales. **Ayuda** contiene la arquitectura.
Estas ventanas se construyen solo al abrirlas. El catálogo editorial se obtiene
en segundo plano y se comparte entre las pantallas; **Actualizar proyecto** lo relee.

**Vista > Resolución** permite elegir 980×640, 1180×760, 1366×768, 1600×900 o
1920×1080, ajustar al monitor actual, maximizar o restaurar el tamaño inicial.
Los tamaños se limitan al área disponible de pantalla y conservan el escalado
DPI del sistema. Estos ajustes no cambian la resolución física del monitor.

La bóveda institucional exige una frase maestra o la selección explícita de
**Usar PIN del entorno**. **Bloquear** limpia los campos y desactiva ese uso en
la ventana, sin borrar ni modificar la variable de entorno del proceso.
Los presets de plataformas contienen únicamente nombres y URLs públicas.

**Resultados** permite abrir el último archivo o carpeta existente de cada tarea.
La barra inferior identifica trabajos activos. No se permite cerrar la suite o
aplicar otro contexto mientras hay tareas registradas en curso; las cancelaciones
editoriales siguen siendo cooperativas y esperan a que termine la llamada activa.

Pruebas de GUI aisladas, sin credenciales ni llamadas reales a modelos:

```powershell
./.venv/Scripts/python.exe -m pytest aulaTEX/aulatex/tests/test_gui_workflows.py aulaTEX/aulatex/tests/test_platform_credentials_gui.py aulaTEX/aulatex/tests/test_platform_credentials.py -q
```

## Catalogo y proteccion de plantillas

**Herramientas > Plantillas y alineación** permite consultar candidatos por
materia, discrepancias de manifiestos y temporales. La consulta se ejecuta en
segundo plano, sin modelos ni acceso a plataformas.

El [registro de selección](aulaTEX/base/catalogos/seleccion-plantillas-aulatex.json) declara
entradas preferidas por materia y tipo: `report`, `presentation` y `activity`.
Las selecciones iniciales corresponden a adaptadores documentados de seis
materias de UCNL, las dos de UAS y Plan de Negocios de ITESCA. Las demás materias
permanecen pendientes de revisión, sin elegir automáticamente por nombre.

En la GUI, selecciona un candidato y pulsa **Declarar plantilla**. Tras confirmar,
se actualiza únicamente el registro mediante reemplazo atómico. No se transforma
el documento ni se cambian datos académicos. Declarar una plantilla no acredita
compilación ni habilita nuevos renderizadores institucionales.

```powershell
./aulaTEX/aulatex.ps1 catalogo-plantillas
./aulaTEX/aulatex.ps1 catalogo-plantillas --export
```

La segunda orden actualiza la [auditoría de plantillas](#auditoria-de-plantillas-y-temporales) y
[catálogo de plantillas](aulaTEX/base/catalogos/catalogo-plantillas-aulatex.json), con huellas
SHA-256, candidatos, dependencias literales y selecciones. Los indicios de motor
y bibliografía proceden del archivo inspeccionado; no prueban la configuración
efectiva de todas sus dependencias. Imágenes, macros dinámicas y compilación se
validan por separado. Los manifiestos históricos se informan, no se reescriben.

El materializador existente es específico de Derecho de UnADM y rechaza otros
programas antes de escribir. Conserva archivos existentes por defecto; el agente
ya no fuerza su sobrescritura al pedir `generar-plantilla`. Las otras instituciones
mantienen sus adaptadores, sin una regeneración genérica con identidad UnADM.

El árbol editorial, el mapa y el inventario comparten la clasificación de nodos.
Se incluye tecnmNL y se excluyen carpetas de apoyo y vacías sin declaración;
un marcador explícito de materia permite registrar una materia aún vacía.

La auditoría de `.tmp*`, `tmp`, `.build` y `.aulatex-temp` registra volúmenes,
estado en Git y comprobantes reconocibles por nombre. Compara estos comprobantes
con copias institucionales del mismo nombre mediante SHA-256. No abre sesiones
web, no publica su contenido y nunca borra archivos, ni siquiera duplicados.
La ausencia de coincidencia no demuestra que un comprobante sea único.

## Arquitectura y compatibilidad de flujos agénticos AulaTeX

AulaTeX combina flujos especializados que pueden cooperar si intercambian productos duraderos del workspace. La regla general es no depender de logs temporales como fuente de verdad: los resultados reutilizables deben materializarse en TEX, BIB, referencias, `extractor-aulatex/` o `.memoria-aulatex/`.

```text
Intencion del usuario
  -> AulaTeX CLI/GUI
  -> Motor inteligente / Agente AulaTeX
  -> LangGraph cuando hay ruteo y ciclos
  -> LangChain adapter para llamadas LLM
  -> Herramientas locales: extractor, memoria, revision, bibliografia, compilacion
  -> Productos duraderos: TEX, BIB, referencias, extractor-aulatex, .memoria-aulatex
```

### Como elegir el flujo

| Necesidad | Comando recomendado | Internamente usa |
| --- | --- | --- |
| Realizar o evaluar una actividad | `aulatex.ps1 agent --action realizar-actividad --activity N` | `AulaTeXAgent`, `EditorialContextProvider`, extractor opcional, LLMs |
| Bucle verificable de actividad | `aulatex.ps1 activity-monitor --activity N --workflow-backend langgraph` | `ActivityMonitor`, LangGraph, observer, revision, reparacion |
| Crear o reforzar nodos | `aulatex.ps1 generation ...` | `ConstructionBuilder`, memoria fundacional, contexto editorial |
| Reforzar memoria editorial | `aulatex.ps1 editorial-memory ...` | `EditorialMemoryBuilder`, `MemoryFusionEngine`, `.memoria-aulatex` |
| Campañas o lotes sobre el repo | `aulatex.ps1 intelligent-engine ...` | `IntelligentEngine`, contratos, ejecucion resumible |
| Extraer conceptos/referencias | `aulatex.ps1 extractor ...` | `ExtractorAdapter` |
| Comunicacion por bot | `bot-interfaz` con `/motor ...` | Planifica instruccion, muestra resumen, pide validacion y ejecuta `IntelligentEngine` solo tras confirmacion |

### Compatibilidad entre flujos

| Flujo | Productos duraderos que genera | Flujos que lo consumen |
| --- | --- | --- |
| `extractor` | `extractor-aulatex/*.json`, conceptos, ideas, trazabilidad, planeacion | `agent`, `activity-monitor`, `editorial-memory`, `EditorialContextProvider` |
| `editorial-memory` | `.memoria-aulatex/*.json`, reglas, ADN editorial, conceptos reforzados | `agent`, `generation`, `intelligent-engine`, `activity-monitor` |
| `generation` | memoria fundacional, `plan.md`, `maqueta.tex`, estructura de nodo | `agent`, `editorial-memory`, `extractor`, `activity-monitor` |
| `agent` | TEX generado o revisado, reportes de ejecucion, compilacion opcional | `activity-monitor`, `editorial-memory`, compilacion, revision posterior |
| `activity-monitor` | observacion, evaluacion, parches, planes de reparacion | `agent`, `editorial-memory`, `intelligent-engine` |
| `intelligent-engine` | campañas, contratos, parches, reportes y ejecuciones por lote | todos, si materializa cambios en archivos o `.memoria-aulatex` |
| `bot-interfaz` | instrucciones validadas por el usuario hacia `IntelligentEngine` | `intelligent-engine`, auditoria humana previa a ejecucion |

Regla practica:

```text
Si un flujo produce algo util, debe materializarlo en TEX/BIB/referencias/extractor-aulatex/.memoria-aulatex.
Entonces los demas flujos pueden reutilizarlo.
```

Los logs en `.aulatex-temp/` son auditoria y depuracion; no son la memoria final.

### Mapa de integracion recomendado

```text
generation
  -> crea estructura base, memoria fundacional, plan y maqueta
  -> editorial-memory
      -> consolida .memoria-aulatex
      -> extractor
          -> produce conceptos, ideas, trazabilidad y planeacion
          -> agent
              -> realiza actividad o genera TEX con contexto editorial
              -> activity-monitor
                  -> observa, evalua, repara y reevalua
                  -> editorial-memory
                      -> absorbe lo aprendido en memoria distribuida
                      -> intelligent-engine
                          -> orquesta campañas o lotes sobre muchos nodos
                          -> bot-interfaz
                              -> recibe instrucciones, muestra plan y pide validacion humana
```

Este orden no es obligatorio, pero evita perdida de aprendizaje: primero se crean productos duraderos, luego se refuerza memoria, despues se ejecutan actividades y finalmente se reabsorbe lo aprendido.

### Pieza comun: `EditorialContextProvider`

La clase `aulaTEX/aulatex/editorial_context.py` reune para cada nodo:

- memoria distribuida y heredada;
- artefactos del extractor (`conceptos`, `ideas`, `trazabilidad`, `planeacion`);
- bibliografia `.bib` local;
- referencias y planeaciones locales;
- señales TEX (`\\section`, `\\subsection`, `\\frametitle`);
- rutas de `.memoria-aulatex` disponibles.

El agente y la generacion descendente consumen este contexto antes de llamar a los LLMs. La prioridad operativa es:

```text
instrucciones locales > extractor > memoria distribuida > herencia > LLM
```

### Backends y responsabilidades

- `classic`: flujo Python directo con condicionales explicitos.
- `langgraph`: ruteo por grafo para ciclos de observacion, revision, reparacion y evaluacion.
- `langchain`: adaptador de llamada LLM; no sustituye al grafo ni al agente.
- `AulaTeXAgent`: ejecuta tareas concretas sobre un nodo.
- `IntelligentEngine`: orquesta campañas y lotes.
- `EditorialMemoryBuilder`: convierte productos duraderos en memoria distribuida.
- `bot-interfaz`: interfaz de comunicacion que pide confirmacion antes de ejecutar el motor inteligente.

Los artefactos temporales viven en `.aulatex-temp/`. La memoria persistente por nodo vive en carpetas `.memoria-aulatex/` distribuidas en el workspace.

## Propuesta de `realizar-planeacion` (motor inteligente)

La [contractualización de realizar-planeación](#contrato-realizar-planeacion) analiza las
planeaciones UnADM y las consignas de otras instituciones para diseñar una
planeación de **actividad concreta** desde descripciones y documentos de entrada.
Define procedencia por requisito, propuestas y faltantes, secuencia, evaluación,
compuertas e integración futura con `realizar-actividad`.

**Estado: propuesta documental; la acción todavía no está implementada.** No
resuelve la actividad ni hereda fechas, ponderaciones o políticas de UnADM a otras
instituciones.

## Contratos de `realizar-actividad` (motor inteligente)

El motor inteligente `realizar-actividad` opera bajo un **contrato editorial explícito** definido en `aulaTEX/aulatex/activity_contract.py` (`REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT`). Ese contrato se **propaga al prompt del agente** a través de `aulaTEX/aulatex/incremental_detail_planner.py` (bloques `didactic_contract`, `structure_contract`, `layout_contract`, `bibliography_contract` y `_quality_rules()`), y se **evalúa** con `evaluate_activity_contract()` (consumido por `activity-observe` y `activity-monitor`).

> Propósito del contrato: tomar un nodo, carpeta o archivo de actividad y llevarlo desde memoria e insumos hasta TEX/PDF final validado mediante ciclos repetibles.

### Fases del pipeline (compromisos de proceso)

El pipeline se compromete a recorrer, en orden, estas fases:

| # | Fase | Compromiso |
| --- | --- | --- |
| 1 | `discover_node` | Resolver scope editorial, TEX canónico, `.bib`, PDF esperado, memoria local y fuentes de referencia. |
| 2 | `build_editorial_memory` | Construir, refrescar y consultar memoria editorial local, ascendente y de nodos relacionados **antes de redactar**. |
| 3 | `ingest_sources` | Extraer e incorporar notas, programas, PDF, Markdown y referencias locales; buscar fuentes externas cuando falte sustento formal. |
| 4 | `validate_questionnaire_inputs` | Validar reactivos, respuestas y justificaciones contra fuentes locales sólidas o fuentes en línea verificables. |
| 5 | `detect_contracts` | Detectar técnica didáctica, formato solicitado, criterios de entrega, rúbrica, subject/título y bibliografía mínima. |
| 6 | `draft_or_repair_content` | Crear o mejorar el TEX **conservando la técnica didáctica** y elevando rigor, fuentes y redacción. |
| 7 | `evaluate_quality` | Observar contrato de actividad, trazabilidad, cobertura conceptual, citas, redacción, formato y coherencia. |
| 8 | `compile_and_repair` | Compilar PDF, clasificar errores, reparar bibliografía o LaTeX y verificar frescura del PDF. |
| 9 | `repeat_until_pass` | Repetir memoria, extracción, redacción, evaluación y compilación hasta aprobar criterios o agotar ciclos. |
| 10 | `align_report_and_presentation` | Cuando existan reporte y presentación, alinear la presentación con el reporte (contenido, profundidad, fuentes, conclusión). |
| 11 | `promote_artifacts` | Persistir TEX, PDF, `.bib`, extractor, memoria, manifiestos, reportes y bitácora de decisión. |

### Compuertas de calidad (quality gates)

El TEX/PDF final debe satisfacer estas compuertas antes de darse por aprobado:

- **memory**: memoria local, ascendente y relacionada consultada antes de redactar o corregir.
- **sources** / **online_validation**: fuentes locales incorporadas y fuentes formales citables; si el corpus local no basta, investigar en línea y materializar en `.bib`.
- **questionnaire_validation**: cada respuesta y justificación de un cuestionario contrastada con bibliografía sólida.
- **didactic_format**: la forma visible respeta la técnica solicitada (cuestionario, foro, caso, **mapa**, **tabla/cuadro**, etc.).
- **headings**: título sin “Actividad #”; subtítulo compacto; `subject` = `Actividad # - Materia`.
- **bibliography** / **visible_citations** / **reference_growth**: toda cita visible tiene entrada `.bib`; sin entradas inventadas; las fuentes nuevas aparecen como citas visibles; mínimo 3 fuentes (5 para cuestionarios extensos).
- **content**: sin placeholders; contexto/problema en la introducción; análisis y postura propios en la conclusión.
- **visible_style**: sin metadiscurso de ejecución (no hablar de “esta actividad”, “producto solicitado”, “se presenta”); hablar del tema.
- **three_part_structure**: cuerpo visible en **tres actos** — Introducción, un único Desarrollo y Conclusiones; el marco conceptual, el producto y su análisis son **subsecciones** del desarrollo.
- **development_section**: el acto de desarrollo **NO se titula “Desarrollo”**, sino con un título temático descriptivo (p. ej. “Clasificación de los tipos de seguro”).
- **product_centric_gravity**: el producto solicitado (mapa/cuadro/tabla) tiene **protagonismo imperativo**; el texto gravita a su alrededor (lo prepara antes, lo interpreta después).
- **introduction** / **conclusion**: la introducción absorbe contexto y problema; la conclusión integra síntesis, análisis y postura (sin secciones separadas de “Análisis propio”).
- **ai_declaration**: la declaración de uso de IA, cuando exista, va como `\footnote` ligada a una frase oportuna (por defecto de la conclusión), **nunca** como `\section` ni bloque separado.
- **compile**: PDF existe, está fresco, sin errores críticos ni citas indefinidas.
- **report_presentation_alignment**: reporte y presentación coherentes en contenido, profundidad, fuentes y conclusión.

### Reglas de texto visible

- **avoid_metadiscourse** / **prefer_theme_language**: hablar del tema, problema, concepto, cuestionario, caso o tabla, no de “la actividad”.
- **fold_context_into_introduction**: contexto y problema dentro de la introducción, sin subsección “Contexto y problema”.
- **comment_organization_criteria** / **comment_cognitive_level**: criterio de organización, técnica y nivel cognitivo van como comentarios TEX, no como secciones visibles.
- **three_part_body**: cuerpo en tres actos; desarrollo en una sola sección con subsecciones.
- **development_title_cosmetic**: el título del desarrollo nombra el fenómeno, no la etiqueta didáctica.
- **product_centric_development**: dar protagonismo imperativo al producto; prepararlo antes e interpretarlo después.
- **fold_analysis_into_conclusion**: análisis propio y postura integrados en la conclusión.

### Reglas de compilación y maquetado

- **build_command** / **orphan_bbl**: usar `latexmk -f -pdf -bibtex` con `TEXINPUTS`/`BIBINPUTS`; borrar `.bbl`/`.aux` huérfanos si las citas salen como `[?]`.
- **encoding_safety**: nunca editar `.tex` con PowerShell (`Set-Content`/`-replace`): corrompe UTF-8; usar herramientas que preserven la codificación.
- **page_control** / **no_gap_before_visual_deliverable**: usar `\clearpage` para forzar secciones en su página; prohibido dejar media página o más en blanco antes de un entregable visual en landscape.
- **landscape_single_page**: tabla/caption o diagrama/leyenda deben caber juntos en **una** página landscape (`\arraystretch<=1.2`, caption `\footnotesize`); no anteponer `\clearpage` a `\begin{landscape}`.
- **conclusion_single_page**: la conclusión inicia con `\clearpage` y ocupa preferentemente una sola página.
- **verify_visually**: verificar el resultado renderizando páginas a PNG con `pdftoppm`, no solo el código de retorno.

### Contratos por técnica didáctica

`DIDACTIC_TECHNIQUE_CONTRACTS` fija reglas específicas según el producto detectado (por alias en la planeación):

| Técnica | Alias | Compromiso clave |
| --- | --- | --- |
| `cuestionario_diagnostico` | cuestionario, diagnóstico, reactivo | Conservar pregunta, respuesta y justificación; el Desarrollo contiene el cuestionario con su título. |
| `estudio_de_caso` | caso, estudio de caso, situación | Conservar hechos, actores, problema y resolución argumentada. |
| `mapa_conceptual` | mapa conceptual, conceptos, diagrama | Mapa no esquelético (raíz + ramas + niveles); TikZ jerárquico en landscape; el mapa es el **núcleo** del desarrollo. |
| `tabla_didactica` | tabla, cuadro, cuadro comparativo | Estructura tabular con caption y criterio de lectura; landscape en su propia página; la tabla es el **núcleo** del desarrollo. |
| `foro_diagnostico` | foro, foro diagnóstico | Conservar preguntas guía y respuestas compactas, sin convertirlo en ensayo. |

Para `mapa_conceptual` y `tabla_didactica` rige además `three_act_gravity_rule`: el desarrollo no se fragmenta en varias `\section`; marco, producto y análisis son subsecciones de una sola sección temática y el producto manda (se prepara antes y se interpreta después).

### Modo monitor y ciclos de optimización

Existen dos formas de ejecutar los ciclos, con compromisos distintos:

- **`agent --action realizar-actividad --cycle-mode full --iterations N`**: N ciclos completos de los cinco roles (planificar, investigar, generar, validar, criticar). ⚠️ Según `iterative_improvement_rules.avoid_full_cycle_agent`, este modo **no es observable** (guarda todo al final) y es **vulnerable a cuelgues de red sin timeout**; no se recomienda para muchos ciclos de mejora incremental.
- **`activity-monitor --activity N --max-cycles M --workflow-backend langgraph`** (recomendado): bucle **observable** que escribe por ciclo, aplica parches verificables (bibliografía, revisión, compilación), reevalúa el contrato y **cierra temprano** si aprueba (`prefer_observable_monitor`).

Compromisos de los ciclos de optimización (`iterative_improvement_rules`):

- **avoid_full_cycle_agent**: no usar `agent --cycle-mode full` con muchos ciclos para mejorar contenido incrementalmente.
- **prefer_observable_monitor**: preferir `activity-monitor` o un orquestador con timeout por llamada.
- **monitor_note**: `activity-monitor` **no agrega conceptos nuevos** (sus parches son deterministas: placeholders, criterios, bibliografía); para enriquecer con razonamiento LLM se requiere un orquestador que pida subconceptos en JSON, deduplique y apile con tope por rama.
- **tex_target_priority**: al observar una actividad con reporte y presentación, priorizar el TEX de reporte (`reporte-*`).

> Ejecución masiva por lotes: para lanzar muchos ciclos de forma resistente a cuelgues, `aulaTEX/act2-100ciclos-monitor.ps1` divide el trabajo en lotes con *watchdog* por lote y timeout de LLM configurable (`AULATEX_LLM_TIMEOUT_SECONDS`, `AULATEX_LLM_MAX_TOKENS`), registrando el progreso en `.aulatex-temp/`.

### Reglas de validación de fuentes

- **editorial_memory_first**: consultar memoria editorial local, ascendente y relacionada antes de redactar.
- **local_first_online_when_needed**: priorizar corpus local; recurrir a fuentes en línea sólidas solo si no alcanza, y registrarlas en `.bib` con citas visibles.
- **questionnaire_answers** / **visible_reference_growth**: todo cuestionario resuelto requiere mapa reactivo → respuesta → fuente; el crecimiento de referencias debe ser visible en el cuerpo y en `.bib`.
- **no_unsupported_answers**: no consolidar respuestas dudosas sin marcarlas, corregirlas o respaldarlas.

### Contrato de aprobación de la actividad (`ACTIVITY_1_CONTRACT`)

`evaluate_activity_contract()` verifica elementos requeridos y rangos aceptables:

- **Requeridos**: objetivo, fuente de instrucción, técnica didáctica, formato didáctico preservado, formato de salida, bibliografía, trazabilidad, criterios de evaluación, reflexión final y declaración de IA como `\footnote`.
- **Rangos**: secciones 3–8; mínimo 3 entradas `.bib` y 3 citas visibles (5 para cuestionarios extensos); mínimo 5 conceptos.

### Ciclo recomendado

```text
editorial-memory (local/ascendente/relacionada)
  -> investigation (queries bibliográficas)
  -> extractor / investigation local
  -> validación de cuestionario
  -> investigation online (si falta sustento)
  -> expansión .bib + citas visibles
  -> agent realizar-actividad
  -> activity-observe
  -> activity-revise / bibliography-repair
  -> latexmk-build
  -> repetir hasta aprobar el contrato
```

```powershell
.\aulaTEX\install-aulatex-deepagents.ps1
```

Para medir desempeño de forma explícita:

```powershell
.\aulaTEX\aulatex.ps1 gui --diagnostics
```

```powershell
$env:AULATEX_ENABLE_DIAGNOSTIC_METRICS=1
.\aulaTEX\aulatex.ps1 investigation --target .\UnADM\licenciatura-en-derecho-unadm\historia-del-derecho-en-mexico-lde --query "historia del derecho en mexico unadm programa analitico"
Remove-Item Env:AULATEX_ENABLE_DIAGNOSTIC_METRICS
```

Cada carpeta de materia tiene un `COMPILACION.md` con el comando exacto, el
`.bib` esperado y el contrato de compilacion. Regla central: al script solo se
le pasa el `.tex`; `\input{template}` se resuelve con `TEXINPUTS` y
`\bibliography{...}` se resuelve con `BIBINPUTS`, ambos definidos en
`.latexmkrc`.

## Estructura Canonica

```text
AulaTeX-Academico/
|-- README.md
|-- aulaTEX/base/
|   |-- cwl-docs/
|   |-- Export-Subtemmplate/
|   |-- Plantilla-Informe/
|   |-- latex/
|   |-- Professional-CV/
|   |-- Template-Articulo/
|   |-- Template-Auxiliares/
|   |-- Template-Controles/
|   |-- Templates-Informe/
|   |-- Template-Informe-master/
|   |-- Template-latex.github.io/
|   |-- Template-Poster/
|   |-- Template-Presentacion/
|   |-- Template-Reporte/
|   `-- Template-Tesis/
|-- UnADM/
|   |-- bibliografia-unadm.bib
|   |-- reporte-unadm.tex
|   |-- presentacion-unadm.tex
|   |-- referencias-unadm/
|   |-- redaccion-en-contextos-virtuales/
|   |-- etica-y-moral-juridica/
|   `-- filosofia-del-derecho/
|-- UCNL/
|   |-- bibliografia-ucnl.bib
|   |-- reporte-ucnl.tex
|   |-- presentacion-ucnl.tex
|   |-- referencias-ucnl/
|   |-- administracion-I/
|   |-- contabilidad-I/
|   |-- curso-inductivo/
|   |-- desarrollo-sustentable/
|   |-- ingles-I/
|   |-- matematicas-I/
|   `-- microeconomia/
|-- IIIEPE/
|   |-- temas-selectos-de-matematicas-I/
|   `-- fundamentos-para-la-enseñanza-y-el-aprendizaje-I/
|-- ITESCA/
|   |-- ingenieria-en-sistemas-computacionales/
|   |   |-- bibliografia-itesca-isc.bib
|   |   |-- reporte-itesca-isc.tex
|   |   |-- presentacion-itesca-isc.tex
|   |   |-- referencias-itesca-isc/
|   |   `-- primer-ingreso/
|   `-- maestria-en-gestion-administrativa/
|       |-- bibliografia-itesca-mga.bib
|       |-- reporte-itesca-mga.tex
|       |-- presentacion-itesca-mga.tex
|       |-- referencias-itesca-mga/
|       `-- primer-ingreso/
`-- aulaTEX/
  `-- retroalimentacion-editorial/
    `-- aulatex/
```

## Convenciones

- Reporte general: `reporte-<materia>.tex`.
- Actividad: `reporte-<materia>-Actividad-N.tex`.
- Presentacion: `presentacion-<materia>.tex`.
- Bibliografia local: `<materia>.bib`.
- Cuando una institucion tiene mas de un programa educativo, el nivel canonico se mueve a `institucion/carrera/materia`.

## Base Original

El proyecto conserva el nucleo tecnico de `Template-Informe` de Pablo Pizarro R.
en `aulaTEX/base/Plantilla-Informe/`, junto con copias originales y adaptaciones
institucionales. Licencia base: MIT.

## Environment

Use `aulaTEX/aulatex.env` o variables de entorno locales para configurar
proveedores. No publiques llaves reales en este archivo.

### PIN maestro y rotacion de claves

Los secretos de `aulaTEX/aulatex.env` se guardan cifrados con prefijo `enc:`
(Fernet). La clave se deriva del PIN maestro `$env:AULATEX_MASTER_PIN` mediante
PBKDF2-SHA256 (480 000 iteraciones) sobre `aulaTEX/secret.salt`. El PIN nunca se
escribe en disco; el salt y `secret.key` estan en `.gitignore`.

> Como este repositorio es publico y los blobs `enc:` si se versionan, el PIN es
> lo unico que protege las claves de Azure. Usa una frase larga, no cuatro
> digitos: un PIN numerico corto se agota por fuerza bruta pese al PBKDF2.
> Evita tambien escribirlo en linea de comandos, porque queda en el historial de
> PSReadLine.

```powershell
# Sesion actual
$env:AULATEX_MASTER_PIN = '<pin>'

# Persistente para el usuario (opcional)
[Environment]::SetEnvironmentVariable('AULATEX_MASTER_PIN', '<pin>', 'User')
```

Para cambiar el PIN, `aulaTEX/rotate-pin.ps1` descifra los valores `enc:` con el
PIN actual, renueva el salt y vuelve a cifrarlos con el nuevo. Ambos PIN se piden
como `SecureString` y viajan por stdin, asi que no quedan en el historial. Si un
token no descifra, aborta sin escribir nada; ademas deja `aulatex.env.bak-rotate`
como respaldo. Renovar el salt invalida las claves derivadas del PIN anterior,
de modo que una copia vieja del `.env` deja de servir aunque se conozca ese PIN.

El minimo son 4 caracteres, pero por debajo de 16 (o si el PIN es solo numerico)
el script advierte, calcula el espacio de busqueda y exige escribir `ACEPTO`.

```powershell
.\aulaTEX\rotate-pin.ps1            # PIN solo para la consola actual
.\aulaTEX\rotate-pin.ps1 -Persist   # ademas lo guarda en la variable de usuario
```

`setup.bat` incluye un asistente para configurar uno o varios LLM. El flujo es:
**modo → LLMs → PIN → credenciales → validación**. La opción «Conservar» termina
sin pedir PIN. En los modos Azure CLI y manual, el PIN y las API keys se capturan
como entrada oculta; cada clave se cifra antes de escribirla. Si se elige
únicamente `model-router`, activa `AULATEX_MODEL_ROUTER_ONLY=1` automáticamente.

```powershell
.\setup.bat                 # instala y abre el asistente LLM
.\setup.bat --llm-only      # solo PIN/endpoints/deployments/claves
.\setup.bat --skip-llm      # instala sin asistente interactivo
.\setup.bat --no-shell --configure-llm  # automatización con configuración explícita
```

`aulaTEX/sync-keys.ps1` sustituye las claves del `.env` con las de tus
suscripciones. Recorre todas las suscripciones de `az account list`, inventaria
las cuentas de Cognitive Services y asocia cada variable `*_API_KEY` con la
cuenta cuyo host coincide con su `*_BASE_URL` o `*_ENDPOINT` hermano. El valor en
claro viaja solo por stdin: nunca por argv ni por el historial de PowerShell.

```powershell
# Inventario y plan, sin escribir nada
.\aulaTEX\sync-keys.ps1 -WhatIf

# Sincroniza las claves vigentes (respalda el .env antes)
.\aulaTEX\sync-keys.ps1

# Rotacion real: regenera key1 en Azure y sustituye
.\aulaTEX\sync-keys.ps1 -Rotate

# Acotar a ciertas variables o suscripciones
.\aulaTEX\sync-keys.ps1 -Name MODEL_ROUTER_API_KEY,CODEX_API_KEY
.\aulaTEX\sync-keys.ps1 -Subscription 'Suscripcion Maury'

# AWS IAM (Polly). Sin -DeactivateOld la clave anterior sigue activa.
.\aulaTEX\sync-keys.ps1 -IamUserName <usuario-iam> -DeactivateOld
```

Utilidades de `aulaTEX/secrets_local.py`:

```powershell
python aulaTEX\secrets_local.py encrypt aulatex.env       # cifra valores en claro
python aulaTEX\secrets_local.py decrypt-env aulatex.env   # NOMBRE<TAB>valor
'<valor>' | python aulaTEX\secrets_local.py set-value aulatex.env NOMBRE
```

Requisitos: `az login` y `aws configure` previos.

```env
# Opcion compatible OpenAI/Azure v1 preferida por este repo:
OPENAI_BASE_URL=https://example-resource.openai.azure.com/openai/v1/
OPENAI_API_KEY=<your-openai-or-azure-openai-key>
OPENAI_VIDEO_MODEL=sora-2
OPENAI_AUDIO_MODEL=gpt-4o-mini-tts

# Opcion experimental de GPT Realtime para una futura integracion interactiva.
# No la usa el pipeline actual de narracion offline y no debe sobrescribir
# OPENAI_BASE_URL / OPENAI_API_KEY.
AZURE_OPENAI_REALTIME_ENDPOINT=https://example-resource.services.ai.azure.com
AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME=gpt-realtime
AZURE_OPENAI_REALTIME_API_KEY=<your-realtime-key>

# Opcion Azure clasica:
AZURE_ENDPOINT=https://example-resource.services.ai.azure.com/api/projects/example-project
AZURE_API_KEY=<your-azure-ai-key>
AZURE_OPENAI_DEPLOYMENT_NAME=sora-2
AZURE_OPENAI_AUDIO_MODEL=gpt-4o-mini-tts

AZURE_ENV_NAME=example-env
AZURE_LOCATION=swedencentral
AZURE_SUBSCRIPTION_ID=00000000-0000-0000-0000-000000000000
AZURE_EXISTING_AIPROJECT_ENDPOINT=https://example-resource.openai.azure.com/openai/v1/
AZURE_EXISTING_AIPROJECT_RESOURCE_ID=/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/example-rg/providers/Microsoft.CognitiveServices/accounts/example-resource/projects/example-project
AZURE_EXISTING_RESOURCE_ID=/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/example-rg/providers/Microsoft.CognitiveServices/accounts/example-resource
AZD_ALLOW_NON_EMPTY_FOLDER=true

# GPT-Pro
GPT_PRO_BASE_URL=https://example-resource.services.ai.azure.com/openai/v1/responses
GPT_PRO_API_KEY=<your-gpt-pro-key>
GPT_PRO_CHAT_DEPLOYMENT=gpt-5.4-pro
GPT_PRO_API_VERSION=2026-03-05

# Claude Foundry
ANTHROPIC_FOUNDRY_BASE_URL=https://example-resource.services.ai.azure.com/anthropic
ANTHROPIC_FOUNDRY_API_KEY=<your-anthropic-foundry-key>
ANTHROPIC_FOUNDRY_CHAT_DEPLOYMENT=claude-opus-4-8
ANTHROPIC_FOUNDRY_API_VERSION=2023-06-01

# Configuracion para traduccion de libros y generacion de audio
AZURE_TRANSLATOR_KEY=<your-translator-key>
AZURE_TRANSLATOR_REGION=eastus
AZURE_TRANSLATOR_ENDPOINT=https://example-translator.cognitiveservices.azure.com/

# Glosario opcional
# TB_BOOKS_TERMINOLOGY_FILE=terminology/glossary.json

# Robustez / rendimiento
TB_BOOKS_TRANSLATION_WORKERS=12
TB_BOOKS_TRANSLATOR_MAX_RETRIES=6
TB_BOOKS_TRANSLATOR_BACKOFF=1
TB_BOOKS_TRANSLATOR_MAX_BACKOFF=30
TB_BOOKS_TRANSLATOR_TIMEOUT=90

# Amazon Polly / audio M4A
TTS_PROVIDER=polly
AWS_ACCESS_KEY_ID=<your-aws-access-key-id>
AWS_SECRET_ACCESS_KEY=<your-aws-secret-access-key>
AWS_REGION=us-east-1
POLLY_VOICE_ID=Andres
POLLY_ENGINE=generative
POLLY_LANGUAGE_CODE=es-MX
POLLY_SAMPLE_RATE=24000
VOICE_RATE=114%
VOICE_VOLUME=+1.14dB
MAX_CHARS=2500
POLLY_WORKERS=12
POLLY_MAX_TPS=6
POLLY_MAX_RETRIES=6
POLLY_RETRY_BASE_DELAY=1
POLLY_RETRY_MAX_DELAY=30
OUTPUT_BITRATE=128k
FFMPEG_PARALLEL_JOBS=4
FFMPEG_GROUP_SIZE=512

# Azure Speech / audio M4A (usado si TTS_PROVIDER=azure)
AZURE_SPEECH_KEY=<your-speech-key>
AZURE_SPEECH_REGION=eastus
AZURE_SPEECH_LANGUAGE=es-MX
AZURE_SPEECH_VOICE=es-MX-JorgeNeural
AZURE_SPEECH_STYLE=chat
AZURE_SPEECH_STYLE_DEGREE=0.9
AZURE_SPEECH_RATE=1.10
AZURE_SPEECH_PITCH=-1
AZURE_SPEECH_VOLUME=110

# FFMPEG_PATH=D:\ruta\a\ffmpeg.exe

# Motor LLM para semantic-safe, validacion y pruebas
TB_BOOKS_LLM_REVIEW_ENGINE=Codex
TB_BOOKS_LLM_VALIDATION_ENABLED=1
TB_BOOKS_LLM_VALIDATION_TIMEOUT=45
TB_BOOKS_LLM_VALIDATION_MAX_TOKENS=220
TB_BOOKS_LLM_VALIDATION_TEMPERATURE=0

# Auto (model-router)
# Endpoint de inferencia del recurso, no el endpoint /api/projects/... del proyecto.
MODEL_ROUTER_BASE_URL=https://example-resource.services.ai.azure.com/openai/v1/chat/completions
MODEL_ROUTER_API_KEY=<your-model-router-key>
MODEL_ROUTER_CHAT_DEPLOYMENT=model-router
MODEL_ROUTER_API_VERSION=2025-11-18

# Modo de deployment único: evita cualquier fallback o rotación hacia otros LLM.
AULATEX_MODEL_ROUTER_ONLY=1
AULATEX_LLM_ENGINE="Auto (model-router)"
AULATEX_LLM_PROVIDER=model-router
LLM_PROVIDER=model-router
TB_BOOKS_LLM_REVIEW_ENGINE="Auto (model-router)"
# Debe respetar el máximo real del deployment; el valor conservador validado es 32768.
AULATEX_LLM_MAX_TOKENS=32768

# La clave se puede ingresar sin exponerla en argv ni en el historial:
# '<valor>' | python aulaTEX\secrets_local.py set-value aulaTEX\aulatex.env MODEL_ROUTER_API_KEY
# Después, cifra cualquier secreto en claro:
# python aulaTEX\secrets_local.py encrypt aulaTEX\aulatex.env

# Codex
CODEX_BASE_URL=https://example-resource.services.ai.azure.com/openai/v1/responses
CODEX_API_KEY=<your-codex-key>
CODEX_CHAT_DEPLOYMENT=gpt-5.3-codex
CODEX_API_VERSION=2026-02-24
```

## Deployments validados para límites

```json
      {
        "id": "gpt-5.4-pro",
        "name": "gpt-5.4-pro",
        "url": "https://carlosmauriciocarvajalcoronado-4.services.ai.azure.com/openai/v1/responses",
        "maxInputTokens": 922000,
        "maxOutputTokens": 128000,
      },
      {
        "id": "model-router",
        "name": "model-router",
        "url": "https://carlosmauriciocarvajalcoronado-4.services.ai.azure.com/openai/v1/chat/completions",
        "maxInputTokens": 1015808,
        "maxOutputTokens": 32768
      },
      {
        "id": "Mistral-Large-3",
        "name": "Mistral-Large-3",
        "url": "https://carlosmauriciocarvajalcoronado-4.services.ai.azure.com/openai/v1/chat/completions",
        "maxInputTokens": 126976,
        "maxOutputTokens": 4096
      },
      {
        "id": "gpt-chat-latest",
        "name": "gpt-chat-latest",
        "url": "https://carlosmauriciocarvajalcoronado-4.services.ai.azure.com/openai/v1/responses",
        "maxInputTokens": 72000,
        "maxOutputTokens": 128000,
      },
      {
        "id": "DeepSeek-V4-Pro",
        "name": "DeepSeek-V4-Pro",
        "url": "https://carlosmauriciocarvajalcoronado-4.services.ai.azure.com/openai/v1/chat/completions",
        "maxInputTokens": 872000,
        "maxOutputTokens": 128000
      },
      {
        "id": "gpt-5.3-codex",,
        "maxInputTokens": 272000,
        "maxOutputTokens": 128000,
      }
```

## Límites de tokens y tiempo de espera

Los valores siguientes distinguen tres capas: límites teóricos declarados/configurados, límites probados por llamadas reales y límites operativos que usa AulaTeX para estabilizar la ejecución local. Las pruebas se ejecutaron el 2026-07-08 con `aulaTEX/validar-limites-deployments.ps1`. Los artefactos principales están en `.aulatex-temp/deployment-limit-probe/runs/20260708-133615/`, con refinamientos en `20260708-163927`, `20260708-164136` y `20260708-164637`.

### Deployments validados

| Deployment | Endpoint | Entrada teórica/configurada | Salida teórica/configurada |
| --- | --- | ---: | ---: |
| `gpt-5.4-pro` | `responses` | `922,000` | `128,000` |
| `model-router` | `chat/completions` | `1,015,808` | `32,768` |
| `Mistral-Large-3` | `chat/completions` | `126,976` | `4,096` |
| `gpt-chat-latest` | `responses` | `72,000` | `128,000` |
| `DeepSeek-V4-Pro` | `chat/completions` | `872,000` | `128,000` |
| `gpt-5.3-codex` | `responses` | `272,000` | `128,000` |

### Resultados probados y límites operativos

| Deployment | Entrada probada | Latencia entrada | Salida probada solicitada | Salida observada | Latencia salida | Límite operativo establecido |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `gpt-5.4-pro` | `138,300` | `41,378 ms` | no validada por `rate_limit` | `0` | `0 ms` | entrada `138,300`; salida `8,192` conservadora. |
| `model-router` | `253,951` | `13,258 ms` | `29,491` | `1,161` | `58,515 ms` | entrada `253,951`; salida `29,491`. |
| `Mistral-Large-3` | no validada por alta demanda | `0 ms` | `4,096` | `607` | `49,334 ms` | entrada deshabilitada para lotes largos; salida `4,096`. |
| `gpt-chat-latest` | `72,000` | `6,006 ms` | `128,000` | `443` | `3,987 ms` | entrada `72,000`; salida `128,000`. |
| `DeepSeek-V4-Pro` | no validada por alta demanda | `0 ms` | `128,000` | `8,815` | `114,011 ms` | entrada deshabilitada para lotes largos; salida `128,000`, con latencia alta. |
| `gpt-5.3-codex` | `265,200` | `2,660 ms` | `128,000` | `341` | `3,430 ms` | entrada `265,200`; salida `128,000`. |

### Configuración operativa del workspace

- `aulaTEX/aulatex.env` fija `AULATEX_OPERATIVE_INPUT_TOKENS_*` y `AULATEX_MAX_OUTPUT_TOKENS_*` con los valores anteriores.
- `aulaTEX/aulatex/llm_bridge.py` aplica `AULATEX_MAX_OUTPUT_TOKENS_<PREFIJO>` por motor antes de invocar el proveedor.
- `aulaTEX/prueeba-lote-ejecucion-1.ps1` usa defaults actualizados para presupuestos DNA y salida de los motores principales.
- `0` o “no validada” en entrada probada significa que no se alcanzó éxito estable: la API falló por `rate_limit`, alta demanda o tamaño máximo permitido bajo carga antes de demostrar el límite duro del modelo.
- La salida probada indica que la API aceptó el valor de `max_output_tokens`; no implica que el modelo haya producido esa cantidad completa de tokens.

## Guia Linux

AulaTeX en Ubuntu 24.04 (CPU / Remote SSH)

Esta adaptación es local: no crea VMs, no despliega servicios y no configura
credenciales. Está orientada a Ubuntu 24.04 x86_64, Python 3.12 del sistema y
TeX Live **completo de la distribución**, no al instalador upstream de TeX Live.
La estación r7i.4xlarge actual es CPU, no GPU. Reserva el volumen persistente de 200 GiB para
el repositorio, el entorno y los datos; no dependas del NVMe efímero para conservarlos.
TeX Live ocupa varios GB y la generación de formatos puede tardar bastante.
Los modelos/datasets opcionales consumen espacio adicional; comprobar espacio libre.

### Instalación

Desde la raíz del repositorio, con acceso a los repositorios Ubuntu/PyPI:

```bash
df -h . /
bash setup.sh --help
bash setup.sh --no-shell --skip-llm
```

Para instalar todos los perfiles Linux de extracción, multimedia, IA, entrenamiento
CPU y notebooks, sin descargar modelos ni configurar proveedores:

```bash
bash setup.sh --all --no-shell
```

El bootstrap instala mediante apt: texlive-full, latexmk, biber, perl,
ghostscript, poppler-utils, Python/venv/Tk, compiladores, git/git-lfs, fuentes,
certificados y shellcheck. Puede pedir sudo para apt; **no ejecutes todo el
setup con sudo**, para no crear archivos del repositorio propiedad de root.
No configura Git LFS ni descarga objetos LFS automáticamente.

Si la VM ya tiene apt preparado:

```bash
bash setup.sh --skip-system --no-shell --skip-llm
```

`--skip-system` no instala ni comprueba todos los paquetes apt: su preparación
queda a cargo del administrador. Deben existir al menos Python >=3.12 con venv
y pip; para compilar, TeX Live completo y latexmk. La receta VS Code usa `python`,
por lo que se necesita `python-is-python3` o Python en el PATH de VS Code remoto.

Reejecutar el setup reutiliza .venv-linux sin borrarlo. pip puede actualizar
herramientas y resolver versiones dentro de los rangos declarados; no es un
lockfile reproducible bit a bit. .venv y sus dos archivos versionados de Windows
no se modifican. `--no-shell` evita abrir una consola; sin esa opción solo se abre
en una terminal interactiva, sin modificar perfiles Bash del usuario.

### Núcleo y perfiles opcionales

- [aulaTEX/requirements-linux-cli.txt](aulaTEX/requirements-linux-cli.txt):
  requests y los tres adaptadores LangChain importados obligatoriamente por la
  arquitectura actual. Aunque sean SDKs de IA, instalarlos no configura ni llama
  modelos. No incluye audio, GUI de terceros, PyWin32, CUDA ni entrenamiento.
- [aulaTEX/requirements-linux-llm.txt](aulaTEX/requirements-linux-llm.txt):
  integraciones opcionales LangChain/LangGraph/deepagents, cifrado y tokenizador.
- [aulaTEX/requirements-linux-training.txt](aulaTEX/requirements-linux-training.txt):
  preparación/entrenamiento local; PyTorch se instala antes desde el índice CPU.
  No usa los requisitos Windows/interfaz ni instala SDKs de despliegue de nube.
- [aulaTEX/requirements-linux-documents.txt](aulaTEX/requirements-linux-documents.txt):
  reutiliza los requisitos del extractor (PyMuPDF, DOCX, pandas, NumPy,
  OpenPyXL y scikit-learn) y añade pypdf y Pillow.
- [aulaTEX/requirements-linux-notebooks.txt](aulaTEX/requirements-linux-notebooks.txt):
  JupyterLab, ipykernel, ipywidgets y cliente Jupyter. Registra el kernel de usuario
  `aulatex-linux` con el intérprete de este entorno; no inicia un servidor Jupyter.
- `--with-media`: instala FFmpeg/FFprobe, Inkscape y Pandoc desde Ubuntu. Con
  `--skip-system` comprueba que los ejecutables existan y falla si falta alguno.

```bash
bash setup.sh --skip-system --no-shell --with-llm
bash setup.sh --skip-system --no-shell --skip-llm --with-training
bash setup.sh --no-shell --with-documents --with-media --with-notebooks
```

Los perfiles pueden combinarse; `--all` activa los cinco perfiles opcionales.
`--skip-llm` es incompatible con `--with-llm` y con `--all`. Omitir un perfil no desinstala
paquetes que se hayan instalado previamente. `--skip-llm` es una opción de
instalación, **no un cortafuegos** que desactive los subcomandos IA del programa.
IA requiere credenciales válidas, no configuradas por este bootstrap. No copies
secretos a Git ni los imprimas para diagnosticar. El entrenamiento de modelos
grandes en CPU puede ser impráctico; no se garantiza QLoRA/CUDA ni se descarga
ningún modelo automáticamente.

PyTorch se obtiene exclusivamente del índice CPU oficial. El bootstrap verifica
que no esté compilado para CUDA/ROCm y escribe una restricción de su versión exacta
en `.venv-linux/torch-cpu-constraints.txt` para la resolución conjunta de los demás
paquetes. Si otro requisito no es compatible, pip falla en lugar de sustituirlo
silenciosamente por una variante GPU. Esto no fija todas las versiones del entorno.
No se instalan controladores, CUDA, bitsandbytes ni servicios públicos.

El perfil notebooks puede usarse sin entrenamiento. En VS Code, instala la
extensión Jupyter en el host remoto y selecciona **AulaTeX Linux (CPU)**. Cambiar
la ubicación del repositorio exige volver a ejecutar el perfil para actualizar
la ruta registrada del kernel.

### Pruebas funcionales de los perfiles

```bash
.venv-linux/bin/python aulaTEX/verify_linux_flows.py --all
.venv-linux/bin/python aulaTEX/verify_linux_flows.py --documents --media
```

El verificador genera archivos sintéticos en directorios temporales: PDF, DOCX,
XLSX, PNG, audio WAV, SVG y Markdown. Comprueba lectura/exportación y TF-IDF.
El entrenamiento crea un GPT-2 diminuto desde configuración, hace un paso de
backpropagation CPU y guarda/recarga sus pesos; no usa `from_pretrained` ni
descarga modelos. Notebooks comprueba el intérprete registrado y ejecuta `6 * 7`
en un kernel temporal limitado a localhost, que se cierra al terminar.
No se crean notebooks `.ipynb`, se leen secretos ni se modifican documentos reales.
La salida JSON informa versiones y comprobaciones; un fallo devuelve código 1.

Las pruebas usan cachés temporales y modo offline de Hugging Face; esos ajustes
no equivalen a un cortafuegos del sistema. No prueban credenciales ni flujos de
proveedores, todos los scripts PowerShell, ni rendimiento de modelos grandes.
Instalar Inkscape no convierte automáticamente la receta TikZ Windows a Linux.

### CLI sin interfaz gráfica

```bash
bash aulaTEX/aulatex.sh
bash aulaTEX/aulatex.sh --help
bash aulaTEX/aulatex.sh agent-patterns
bash aulaTEX/aulatex.sh compile reporte-AulaTeX-Academico.tex
```

El lanzador usa [aulaTEX/aulatex_agent.py](aulaTEX/aulatex_agent.py), reenvía
argumentos sin perder espacios y ejecuta desde la raíz. Sin argumentos muestra
ayuda; no abre GUI. La GUI se importa únicamente al pedirla explícitamente
(el comportamiento predeterminado Windows se conserva). No uses `gui` en una
sesión SSH sin servidor gráfico; Remote SSH no proporciona escritorio remoto.
No se ha adaptado toda la automatización PowerShell, extractores, exportación
TikZ ni entrenamiento/cloud a Linux.

#### Validar y configurar model-router

La carga del archivo de configuración no demuestra que la API key sea válida.
Para validar el LLM y corregir su configuración si falla, sin PowerShell ni GUI:

```bash
bash aulaTEX/aulatex.sh llm-config
```

El asistente primero prueba `Auto (model-router)`. Si falla, permite introducir
**endpoint HTTPS, deployment y API key**, desbloquear las claves actuales mediante
el PIN maestro, reintentar o cancelar. El PIN y la API key se solicitan con entrada
oculta; nunca se pasan como argumentos ni se imprimen. No pegues secretos en el chat.

Los datos nuevos se prueban en memoria y solo se guardan cuando el LLM devuelve
el marcador esperado. La API key se cifra **antes** de escribir, con reemplazo
atómico y permisos `0600`. Se preservan los otros perfiles y comentarios. Si hay
otros secretos cifrados que deban conservarse, el PIN debe poder descifrarlos; el
asistente no rota ni sustituye su salt. Una clave antigua de model-router dañada
sí puede reemplazarse. Si el archivo cambia durante la edición, se aborta el
guardado para no sobrescribir esa modificación.

Se admite la raíz del recurso Azure, `/openai/v1`, `/v1` o la URL completa de
`chat/completions`/`responses`. Una URL antigua de deployments conserva su
`api-version` y se actualiza con el deployment introducido.

**El PIN introducido en el asistente no se exporta a la terminal padre.** Para
usar las credenciales cifradas en otras ejecuciones desde la misma terminal,
define primero el PIN en Bash sin mostrarlo ni guardarlo en el historial:

```bash
read -r -s -p "PIN maestro de AulaTeX: " AULATEX_MASTER_PIN
printf '\n'
export AULATEX_MASTER_PIN
bash aulaTEX/aulatex.sh llm-config
```

Para automatización o comprobación sin modificaciones:

```bash
bash aulaTEX/aulatex.sh llm-config --non-interactive
bash aulaTEX/aulatex.sh llm-validate
bash aulaTEX/aulatex.sh llm-validate --configure-on-failure
```

`llm-validate` usa model-router por defecto y conserva `--engine` para los otros
motores. `--configure-on-failure` habilita el asistente solo para model-router.
Sin TTY o con `--non-interactive` no se solicitan datos. La salida final es JSON
sin secretos, con código `0` solo si la validación fue exitosa y `1` si falla o
se cancela. El asistente interactivo añade menús antes del JSON.

Estas pruebas **sí llaman al proveedor** y pueden consumir cuota: envían un prompt
mínimo, sin documentos del proyecto, en un único intento sin fallback ni
redirecciones, con 32 tokens de salida y timeout de 45 segundos por defecto.
Se pueden ajustar con `--max-tokens` (16–128) y `--timeout-seconds` (mínimo 5).
El bootstrap, la ayuda y la compilación siguen sin validar ni configurar LLM.

### Compilación y códigos de salida

```bash
bash aulaTEX/latexmk-build.sh reporte-AulaTeX-Academico.tex
bash aulaTEX/latexmk-build.sh "materia con espacios/main.tex" --clean-mode none
python3 aulaTEX/latexmk_build.py reporte-AulaTeX-Academico.tex
```

El wrapper resuelve rutas desde el cwd de quien lo invoca o desde la raíz;
acepta rutas absolutas internas al repositorio y el nombre sin extensión que
envía LaTeX Workshop. Después cambia a la raíz y carga explícitamente
[.latexmkrc](.latexmkrc), sin cargar otros archivos rc del usuario.
Los paths TeX/Bib incluyen también el directorio del documento.

Cada documento usa un directorio propio bajo .build/latex, identificado por el
nombre y un hash de su ruta relativa; dos main.tex de materias distintas no
comparten auxiliares. Se copia el PDF junto al TeX **solo si latexmk termina
correctamente y existe el PDF generado**. Un fallo conserva el PDF final anterior:
su existencia no demuestra que la última compilación haya funcionado.

- `none` y `safe` conservan auxiliares/logs para compilación incremental y diagnóstico.
- `full` limpia solamente los archivos del directorio de build de ese documento.
- Nunca se barren otras materias ni se eliminan residuos junto a las fuentes.
- Se conserva el código de latexmk; argumentos/documento inválido: 2;
  ejecutable ausente: 127; éxito sin PDF: 1.
- `AulaTeXWorkspace.compile_tex()` limita el tiempo (360 segundos por defecto)
  y en POSIX mata el grupo del proceso y sus hijos al expirar; devuelve 124.
  El wrapper directo y la receta VS Code no añaden timeout propio.
- No ejecutes dos compilaciones simultáneas del **mismo** documento.
- Scripts antiguos que buscan logs en el directorio compartido Windows necesitan
  adaptación adicional. Los logs Linux están en el directorio aislado.
- Los scripts no habilitan shell-escape de forma global. Algunos documentos
  pueden necesitar fuentes externas, rutas corregidas por mayúsculas/minúsculas,
  o configuraciones especiales que TeX Live completo no resuelve por sí solo.

### VS Code Remote SSH

1. Conecta a la VM ya preparada usando la extensión Remote - SSH del equipo local.
2. Abre [.vscode/AulaTeX-Linux.code-workspace](.vscode/AulaTeX-Linux.code-workspace) en la ventana
   remota. Instala Python y LaTeX Workshop en el host remoto si VS Code lo solicita.
3. El workspace Linux selecciona .venv-linux. Si VS Code conserva una selección
   anterior, ejecuta **Python: Select Interpreter** y elige el Python de ese entorno.
   No cambies .venv de Windows. Para Windows sigue abriendo la carpeta habitual.
4. Las terminales Linux nuevas usan Bash con el entorno Linux en PATH; los perfiles
   Windows no cambian. Estas terminales no cargan .bashrc (`--norc`).
5. Usa la receta **AulaTeX: latexmk -> PDF junto al tex**. El dispatcher estándar
   [aulaTEX/latexmk_build.py](aulaTEX/latexmk_build.py) elige PowerShell en Windows
   o Bash en Linux, sin importar el stack IA. VS Code abre el PDF junto al TeX.

La receta TikZ PDF/SVG/PNG conserva el script Windows; en Linux devuelve un error
explícito (2). Para un documento TikZ completo usa la receta PDF, no la exportación.
El dispatcher requiere Python en PATH también en Windows (disponible tras el
setup Windows; si VS Code estaba abierto, reinícialo para actualizar PATH).

### Verificación offline

```bash
python3 --version
latexmk -v
pdflatex --version
kpsewhich article.cls
perl -MFile::Spec -e 'print "Perl OK\n"'
pdftotext -v
git lfs version
bash -n setup.sh aulaTEX/aulatex.sh aulaTEX/latexmk-build.sh
shellcheck setup.sh aulaTEX/aulatex.sh aulaTEX/latexmk-build.sh
.venv-linux/bin/python -m pip check
bash aulaTEX/aulatex.sh --help
.venv-linux/bin/python -m pip install 'pytest>=8,<10'
.venv-linux/bin/python -m pytest aulaTEX/tests/test_linux_support.py -q -p no:cacheprovider --tb=short
bash aulaTEX/latexmk-build.sh reporte-AulaTeX-Academico.tex
```

La instalación de pytest necesita PyPI o un wheelhouse preparado; la suite en sí
es offline. Usa documentos sintéticos en temporales, simula latexmk/pip y omite
apt para probar argumentos, códigos de error, aislamiento y reejecución. Los tests de
CLI real bloquean apertura de secretos, red y Tk. Los tests de proceso comprueban
el grupo POSIX con mocks; no sustituyen la prueba real en la VM. La comprobación
final con un documento del repositorio sí requiere TeX Live y sus recursos.

Validación inicial del 12 de septiembre de 2026: 33 pruebas enfocadas aprobadas tanto
en Windows/Git Bash como en Ubuntu 24.04/Python 3.12. ShellCheck, `pip check`
y la auditoría de dpkg pasan en Ubuntu. Se instaló `texlive-full` de Ubuntu
(TeX Live 2023), incluidos XeTeX, LuaTeX, fuentes extra y Biber.
Se compilaron el reporte raíz (5 páginas), `UnADM/reporte-unadm.tex` con la
plantilla compartida (4 páginas) y la presentación raíz (7 páginas).
El perfil `--with-llm` también se instaló y pasó `pip check` y la misma suite.
No se configuraron credenciales, invocaron proveedores ni instalaron modelos
de entrenamiento. La portada del reporte se renderizó y revisó visualmente.

#### Perfiles completos instalados y comprobados

Validación posterior del mismo día en la VM Ubuntu: `bash setup.sh --all --no-shell`
terminó correctamente, al igual que su repetición con `--skip-system`.
Pasaron las **102 pruebas** del bootstrap/verificador y las 12 comprobaciones
funcionales reales del verificador. `pip check`, ShellCheck y auditoría dpkg sin errores.
Una compilación limpia posterior volvió a producir el reporte PDF de 5 páginas.

Versiones comprobadas (inventario de esa ejecución, no lockfile completo):

| Perfil | Versiones |
| --- | --- |
| Documentos | PyMuPDF 1.28.2, pypdf 6.18.1, python-docx 1.2.0, pandas 2.3.3, OpenPyXL 3.1.5, scikit-learn 1.9.1, Pillow 12.3.0 |
| Entrenamiento CPU | torch 2.14.0+cpu, transformers 4.57.6, peft 0.20.0, trl 0.29.1, datasets 5.0.1 |
| Notebooks | JupyterLab 4.6.3, ipykernel 7.3.0, jupyter-client 8.10.0 |
| Multimedia | FFmpeg 6.1.1, Inkscape 1.2.2, Pandoc 3.1.3 |

El kernel `aulatex-linux` ejecutó correctamente una celda temporal y fue cerrado.
Se instaló la extensión Jupyter en el VS Code remoto. Quedaron unos 171 GiB libres.
El entorno previo y los manifiestos se respaldaron en
`/home/ubuntu/.cache/aulatex-bootstrap-9jpJenpR` antes de instalar.
No se descargaron modelos preentrenados ni se configuraron credenciales de proveedores.

## Programa analitico Aulatex

Programa analitico editorial - Aulatex Academico

### Encuadre institucional

Asignatura de la Licenciatura en Derecho de la UnADM ubicada en semestre 2, bloque 1.
Tipo: Obligatoria. Creditos: 8.

### Proposito de realizacion

Transformar cada consigna en un producto juridico verificable: problema, fundamento, analisis, evidencia, postura y cierre profesional.

### Ejes de trabajo

1. Marco constitucional y normativo de la materia.
2. Instituciones, sujetos y problemas juridicos relevantes.
3. Aplicacion practica en contexto mexicano.

### Bibliografia base

La bibliografia local se concentra en `AulaTeX-Academico.bib` y debe ampliarse solo con fuentes verificadas.

## Contrato generar planeaciones

Generar planeaciones: contrato de organización 1.0

Vigente desde 2026-09-22. Implementación: `aulaTEX/aulatex/planning_layout.py`; comando CLI `generar-planeaciones`.

### Alcance implementado

Normaliza modelos JSON revisados con `activity` o `activities`, conservando requisitos, fuentes y metadatos aportados. Produce un par Markdown/JSON por actividad y un índice. No redacta objetivos con un LLM, descarga archivos, entra a Moodle, resuelve tareas ni acredita aprobación institucional. La generación pedagógica de `realizar-planeacion` sigue siendo una especificación distinta. La GUI no incorpora todavía un botón de esta acción.

### Distribución obligatoria

Patrón observado en Filosofía del Derecho, Garantías Constitucionales y Derecho a la Seguridad Social de UnADM; se reutiliza la estructura, no sus consignas ni identidades.

| Artefacto | Ruta relativa a la materia |
| --- | --- |
| Planeación y modelo | `planeaciones-<materia>/planeacion-modulo-<id>.md` y `.json` |
| Originales, libros, consignas y manifiestos | `referencias-<materia>/`, con subcarpetas por tipo o revisión |
| Notas | `referencias-<materia>/notas-<materia>/`, por unidad o actividad |
| Imágenes y logotipos | `assets-<materia>/` |
| Extracciones y fichas | `extractor-aulatex/` |
| Análisis e investigación | `investigacion-aulatex/` |
| Reportes, presentaciones, PDF, Word, bibliografía y plantilla local | Raíz de la materia |

Todos los materiales académicos deben ser versionables. No se generan `.gitignore`, no se usan `data/private` ni temporales como destino final y no se confunde versionado con permiso de redistribución pública. Las exclusiones de credenciales, cookies, tokens y claves permanecen. El comando comprueba reglas Git cuando el destino pertenece a un repositorio; fuera de Git sólo verifica la estructura, no asegura seguimiento de archivos.

### Garantías y límites

- Rechazar IDs inseguros, actividades vacías, duplicados y salidas que escapen por enlaces simbólicos.
- Verificar conflictos de todo el lote antes de escribir. Salidas idénticas se reutilizan; diferentes se conservan y se informa conflicto. No hay `--force`.
- Rechazar campos de credenciales y enlaces con tokens conocidos. Este control no sustituye una revisión de privacidad de insumos arbitrarios.
- Preservar todos los campos aportados; no completar fechas, porcentajes, autorizaciones o fuentes ausentes.
- Crear carpetas de soporte no significa haber realizado extracción, notas o investigación.
- No hacer `git add`, commit o push automáticamente. Versionable significa que Git puede incorporar el artefacto, no que ya esté confirmado.

### Uso

Desde la raíz del repositorio:

```powershell
.\aulaTEX\aulatex.ps1 generar-planeaciones 'ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga' --source 'ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga/planeaciones-generadas/2026-II/revision-2026-09-20/planeacion-curso.json'
```

Los modelos históricos no cambian de autoridad por normalizarlos. Para actualizar el contenido, revisar primero el modelo aportado; una salida existente diferente bloquea la escritura en lugar de sobrescribirla.

Si la carpeta de planeaciones ya tiene un índice por unidades, usar `--index-name INDICE-GENERADAS.md` para conservar su `README.md`. La opción sólo admite un nombre Markdown sin directorios y no puede coincidir con una planeación. No omite la protección contra sobrescrituras.

Pruebas: `aulaTEX/test_planning_layout.py` (unittest, sin LLM ni acceso de red).

## Contrato realizar planeacion

Contrato propuesto: realizar-planeación

Fecha: 2026-09-15. Versión de la especificación: 0.1. Estado: **propuesta documental, no implementada**.

Nombre visible: **realizar-planeación**. Identificador técnico propuesto: `realizar-planeacion`.

### 1. Dictamen y alcance

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

### 2. Evidencia del repositorio

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

#### Estado técnico actual

- El precedente es `REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT` en [aulaTEX/aulatex/activity_contract.py](aulaTEX/aulatex/activity_contract.py#L6-L260): declara entradas, fases, compuertas y reglas. La nueva acción debe tener contrato y evaluador propios.
- [aulaTEX/aulatex/intelligent_engine.py](aulaTEX/aulatex/intelligent_engine.py#L13-L35) admite memoria editorial y realización de actividad, **no** realización de planeaciones. Su inventario se basa en TEX existentes; no basta con agregar una etiqueta.
- [aulaTEX/extractor-conceptos-ideas/src/fichador/planeacion_parser.py](aulaTEX/extractor-conceptos-ideas/src/fichador/planeacion_parser.py#L10-L42) aporta tema, objetivo, técnica y actividad, pero no un modelo completo de calendario, rúbrica y procedencia por requisito.
- [aulaTEX/aulatex/construction.py](aulaTEX/aulatex/construction.py#L67-L80) recibe texto y un documento; su propósito es construir nodos editoriales, no esta nueva salida académica.
- [aulaTEX/interfaz/interfaz/intelligent_dispatch.py](aulaTEX/interfaz/interfaz/intelligent_dispatch.py#L390-L399) sustituye acciones de agente desconocidas por `realizar-actividad`. Esa ruta debe corregirse antes de admitir el nuevo nombre: una solicitud de planeación no debe terminar resolviendo una actividad.

### 3. Alternativas y recomendación

| Alternativa | Ventaja | Límite | Decisión |
| --- | --- | --- | --- |
| Copiar una planeación UnADM y reemplazar nombres | Poco trabajo inicial. | Arrastra políticas, objetivos, calendarios y rúbricas ajenos. | Descartar como mecanismo de generación. |
| Agregar instrucciones a `realizar-actividad` | Reutiliza el circuito existente. | Confunde planeación con respuesta; hereda reglas de tres actos y reflexión que no corresponden. | Reutilizar servicios, no el contrato ni su evaluación. |
| Acción hermana con modelo estructurado y perfiles | Separa responsabilidades y permite validación determinista. | Requiere nuevo ejecutor e integración de entradas sin TEX. | **Recomendada para la primera versión.** |
| Planeador de curso/unidad completo | Permitiría coordinar muchas actividades. | Amplía calendario, pesos y dependencias fuera de la solicitud puntual. | Evolución posterior, con otro alcance explícito. |

### 4. Contrato normativo de la acción

En esta especificación, **DEBE**, **NO DEBE** y **PUEDE** describen compromisos de la futura implementación, no capacidades disponibles hoy.

#### 4.1 Propósito y modos

La acción DEBE convertir entradas académicas en una planeación de actividad, conservando restricciones respaldadas y distinguiendo lo aportado de lo diseñado.

- `normalizar`: organiza lo existente; no incorpora nuevos requisitos ni propuestas pedagógicas.
- `proponer` (modo recomendado): conserva los requisitos y propone objetivos, secuencias o instrumentos ausentes, identificados como propuestas.
- `validar`: contrasta una planeación suministrada con sus insumos; no la reescribe sin autorización.

La acción NO DEBE resolver ejercicios, redactar el ensayo solicitado, producir el mapa del estudiante, entregar en plataformas ni afirmar recepción, calificación o aval docente.

#### 4.2 Entradas

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

#### 4.3 Procedencia y autoridad

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

#### 4.4 Modelo de planeación de actividad

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

#### 4.5 Fases del proceso

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

#### 4.6 Compuertas y estados de salida

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

#### 4.7 Salidas, visibilidad y preservación

La primera versión debe entregar un modelo JSON y una planeación Markdown. TEX/PDF y DOCX se proponen como exportaciones posteriores explícitas; no anunciar soporte hasta disponer de renderizador y pruebas. La planeación puede describir un entregable Word aunque ella misma se publique en Markdown.

Salidas lógicas separadas:

1. Planeación normalizada con versión y procedencia por campo.
2. Documento legible: identificación, objetivo, secuencia, recursos, evidencias, evaluación y entrega.
3. Matrices de requisitos y alineación.
4. Relación de propuestas, faltantes y conflictos.
5. Informe de validación y manifiesto técnico mínimo.

Los objetivos, técnicas, pasos y criterios **sí son contenido visible** de una planeación. No aplicar la regla de ocultar criterios didácticos ni la estructura de tres actos de `realizar-actividad`. El título puede decir “Planeación de actividad”. No copiar declaraciones de IA que atribuyan análisis humano no verificado; cumplir la política aplicable y describir el uso real cuando corresponda.

En borradores, las propuestas y los “por confirmar” deben verse en el documento, no solo en metadatos. La información técnica de extracción y las rutas privadas permanecen fuera del documento académico visible.

Originales y derivados DEBEN permanecer separados dentro de la materia. El contrato de organización vigente es [GENERAR-PLANEACIONES.md](#contrato-generar-planeaciones): planeaciones en `planeaciones-<materia>/`, materiales en `referencias-<materia>/`, notas en su subcarpeta `notas-<materia>/`, recursos gráficos en `assets-<materia>/` y entregables finales en la raíz. No desviar material académico a `data/private`, temporales o carpetas globales ni añadir exclusiones Git. Credenciales y secretos nunca son artefactos académicos. Repetir una ejecución no sobrescribe originales o revisiones humanas; mismos insumos reutilizan la salida y una revisión distinta requiere resolver el conflicto explícitamente.

Los documentos privados se procesan solo dentro del ámbito autorizado; antes de enviarlos a un proveedor remoto se requiere autorización aplicable y minimización. Los manifiestos públicos solo contienen identificadores opacos, estados y métricas; el mapa a documentos privados se mantiene local con acceso restringido. No incluir contenido privado o identidades en trazas, pruebas ni memoria compartida.

#### 4.8 Transferencia a realizar-actividad

El paquete DEBE conservar ID y versión de planeación, objetivo, consigna, evidencias, restricciones, instrumento, fuentes y estado de aprobación de las propuestas. Las propuestas no aprobadas no se promueven a obligaciones por el simple hecho de estar en el paquete.

La transferencia requiere selección explícita y ausencia de bloqueos relevantes para la tarea. El motor receptor debe dar prioridad a la consigna específica sobre su formato editorial genérico, sin tratar el documento como instrucciones ejecutables. Si falta soporte para identificadores no enteros o un producto Word/físico, debe declarar esa incompatibilidad; no redondear el identificador ni sustituir el formato. La ejecución de `realizar-actividad` es una solicitud posterior separada.

### 5. Ejemplo de transformación: ITESCA, mapa conceptual

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

### 6. Integración propuesta en motor-inteligente

No se habilita ningún comando con este documento. Los nombres de módulos nuevos son responsabilidades propuestas, no archivos existentes ni API publicada.

| Componente existente | Cambio requerido |
| --- | --- |
| [aulaTEX/aulatex/intelligent_engine.py](aulaTEX/aulatex/intelligent_engine.py) | Registrar la acción y su despacho; incorporar solicitudes basadas en insumos sin TEX; separar inventario de planeaciones y productos; mantener acciones predeterminadas existentes. |
| [aulaTEX/aulatex/cli.py](aulaTEX/aulatex/cli.py) | Añadir acción, modo, descripción, documentos repetibles, perfil y salida; ID de actividad como cadena. Unificar alias visible acentuado con el identificador ASCII. |
| [aulaTEX/motor-inteligente-monitor.ps1](aulaTEX/motor-inteligente-monitor.ps1) | Ampliar validaciones y traslado de parámetros; permitir seleccionar la nueva acción también en previsualización. |
| [aulaTEX/interfaz/interfaz/intelligent_dispatch.py](aulaTEX/interfaz/interfaz/intelligent_dispatch.py) | Reconocer la intención y rechazar acciones desconocidas; no convertirlas en `realizar-actividad`. |
| [aulaTEX/aulatex/gui.py](aulaTEX/aulatex/gui.py) | Formulario de insumos, actividad y modo; mostrar propuestas, faltantes y confirmaciones antes de transferir. |
| [aulaTEX/aulatex/extractor_adapter.py](aulaTEX/aulatex/extractor_adapter.py) | Seleccionar documentos explícitos, admitir carpetas anidadas y separar originales, notas y productos; evitar usar el entregable como autoridad de su propia consigna. |
| [aulaTEX/aulatex/editorial_context.py](aulaTEX/aulatex/editorial_context.py) | Contexto específico de planeación con procedencia por requisito y aislamiento institucional. |
| [aulaTEX/aulatex/activity_contract.py](aulaTEX/aulatex/activity_contract.py) | Mantener contrato de actividad; consumir transferencia validada sin imponer al planeador reglas de producto estudiantil. |

Responsabilidades nuevas propuestas: `PlanningRequest`/`PlanningResult`, `REALIZAR_PLANEACION_PIPELINE_CONTRACT`, `PlanningBuilder` y `PlanningObserver`, con esquema versionado y validadores deterministas independientes de la opinión del modelo. Las llamadas al modelo deberán reutilizar `AulaTeXLLMClient`; las operaciones frágiles, los mecanismos seguros de la suite.

Previsualizar significa describir acciones, permisos y destinos sin ejecutar generación, red ni escritura de productos. Si se conserva el comportamiento actual de guardar un manifiesto, la interfaz debe avisarlo; no denominarlo “solo lectura”. Los comandos propuestos y ejecutados deben derivar de la misma solicitud normalizada.

### 7. Casos de aceptación de la futura implementación

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

### 8. Entrega por etapas

1. **Esta entrega — análisis y contractualización:** documento estable, evidencia, alternativas, reglas y criterios de aceptación. Sin modificaciones operativas.
2. **MVP — contrato ejecutable:** esquema versionado, modelos, validadores, ingesta de texto/Markdown y de formatos adicionales solo con extracción comprobada; JSON + Markdown para una actividad. Pruebas sin LLM/red.
3. **Integración — ejecución real:** constructor, revisión pedagógica, despacho del motor, CLI, monitor e interfaz; pruebas de extremo a extremo con proveedores simulados y regresión de `realizar-actividad`.
4. **Exportación y transferencia:** renderizadores probados, validación del archivo generado, aprobación versionada y consumo explícito por el flujo de actividad.
5. **Ampliación futura:** planeaciones de unidad/curso y perfiles institucionales, después de validar la actividad puntual.

**Criterio de cierre:** anunciar `realizar-planeacion` como disponible únicamente cuando existan ejecutor, validación y pruebas de integración. Publicar un contrato en un manifiesto o aceptar el nombre en una lista no implementa la capacidad.

## Compilacion Aulatex

Compilacion - Aulatex Academico

Distribucion oficial en Windows: **TeX Live 2026**, instalada en
`C:\texlive\2026`, con el esquema `scheme-full` y `latexmk`.
El script `aulaTEX/latexmk-build.ps1` (tambien usado por las recetas de
LaTeX Workshop) selecciona esta instalacion explicitamente y antepone sus
binarios al `PATH` para usar los motores y la bibliografia de la misma
distribucion. No cambia automaticamente a MiKTeX ni a TeX Live 2025.
El compilador Python `compile_contract_tex` usa la misma distribucion por
defecto; conserva su parametro `latexmk` para pruebas con otra ruta explicita.
Linux conserva su seleccion de herramientas mediante `PATH`.

Comandos desde la raiz del repositorio:

```powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\AulaTeX-Academico\reporte-AulaTeX-Academico.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\AulaTeX-Academico\reporte-AulaTeX-Academico-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\AulaTeX-Academico\presentacion-AulaTeX-Academico.tex
```

Validaciones:

- `\input{template}` debe resolver a la plantilla compartida.
- El archivo `.bib` local debe contener toda fuente citada.
- La salida final debe conservar portada institucional UnADM, desarrollo,
  producto solicitado, conclusion y bibliografia.

<!-- AULATEX_CATALOG_START -->

## Auditoria de plantillas y temporales

Inventario de solo lectura. No acredita compilacion, vigencia docente ni entrega.

| Institucion | Materias | Con candidatos | Con seleccion declarada |
| --- | ---: | ---: | ---: |
| IIIEPE | 2 | 2 | 0 |
| ITESCA | 83 | 82 | 1 |
| UANL | 93 | 90 | 0 |
| UAS | 2 | 2 | 2 |
| UCNL | 55 | 54 | 6 |
| UnADM | 46 | 45 | 0 |
| tecnmNL | 1 | 1 | 0 |

### Discrepancias

- no_template_candidates: UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde
- no_template_candidates: UCNL/licenciatura-en-administracion/administracion-de-operaciones-t8-lad
- no_template_candidates: UANL/ingenieria-en-administracion-y-sistemas/metodologia-de-la-programacion
- no_template_candidates: UANL/ingeniero-agronomo/biologia-celular
- no_template_candidates: UANL/ingeniero-agronomo/responsabilidad-social-y-desarrollo-sustentable
- no_template_candidates: ITESCA/maestria-en-gestion-administrativa/seminario-i-mga
- unversioned_manifest: IIIEPE/maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/estructura-aulatex.json
- missing_declared_path: IIIEPE/maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/estructura-aulatex.json -> IIIEPE/maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/referencias-fundamentos-para-la-enseñanza-y-el-aprendizaje-I
- missing_declared_path: IIIEPE/maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/estructura-aulatex.json -> IIIEPE/maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/planeaciones-fundamentos-para-la-enseñanza-y-el-aprendizaje-I
- missing_declared_path: IIIEPE/maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/estructura-aulatex.json -> IIIEPE/maestria-en-enseñanza-y-aprendizaje-de-las-matematicas/fundamentos-para-la-enseñanza-y-el-aprendizaje-I/assets-fundamentos-para-la-enseñanza-y-el-aprendizaje-I
- unversioned_manifest: ITESCA/maestria-en-gestion-administrativa/fundamentos-de-gestion-administrativa-mga/estructura-aulatex.json
- missing_declared_path: ITESCA/maestria-en-gestion-administrativa/fundamentos-de-gestion-administrativa-mga/estructura-aulatex.json -> ITESCA/maestria-en-gestion-administrativa/fundamentos-de-gestion-administrativa-mga/presentacion-fundamentos-de-gestion-administrativa-Actividad-2.tex
- unversioned_manifest: ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/estructura-aulatex.json
- missing_declared_path: ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/estructura-aulatex.json -> ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/programa-analitico-seminario-i.md
- missing_declared_path: ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/estructura-aulatex.json -> ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/reporte-seminario-i-mga.tex
- missing_declared_path: ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/estructura-aulatex.json -> ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/reporte-seminario-i-mga.pdf
- missing_declared_path: ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/estructura-aulatex.json -> ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/presentacion-seminario-i-mga.tex
- missing_declared_path: ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/estructura-aulatex.json -> ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/reporte-seminario-i-plantilla-actividad.tex
- missing_declared_path: ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/estructura-aulatex.json -> ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/template.tex
- missing_declared_path: ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/estructura-aulatex.json -> ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/planeaciones-seminario-i/INDICE-GENERADAS.md
- missing_declared_path: ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/estructura-aulatex.json -> ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/planeaciones-seminario-i/modelo-generacion-2026-09-22.json
- missing_declared_path: ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/estructura-aulatex.json -> ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/anteproyecto
- missing_declared_path: ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/estructura-aulatex.json -> ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/planeaciones-generadas
- unversioned_manifest: tecnmNL/ingeniero-industrial/inferencial-i/estructura-aulatex.json
- unversioned_manifest: UANL/ingeniero-agronomo/algebra-lineal/estructura-aulatex.json
- unversioned_manifest: UANL/ingeniero-agronomo/calculo-integral/estructura-aulatex.json
- unversioned_manifest: UANL/ingeniero-agronomo/responsabilidad-social-y-desarrollo-sustentable/estructura-aulatex.json
- missing_declared_path: UANL/ingeniero-agronomo/responsabilidad-social-y-desarrollo-sustentable/estructura-aulatex.json -> UANL/ingeniero-agronomo/responsabilidad-social-y-desarrollo-sustentable/extractor-aulatex
- unversioned_manifest: UAS/licenciatura-en-contaduria-uas/derecho-mercantil/estructura-aulatex.json
- unversioned_manifest: UAS/licenciatura-en-contaduria-uas/investigacion-aplicada-a-la-contaduria/estructura-aulatex.json
- unversioned_manifest: UnADM/licenciatura-en-derecho-unadm/derecho-a-la-seguridad-social-lde/estructura-aulatex.json
- missing_declared_path: UnADM/licenciatura-en-derecho-unadm/derecho-a-la-seguridad-social-lde/estructura-aulatex.json -> UnADM/licenciatura-en-derecho-unadm/derecho-a-la-seguridad-social-lde/assets-derecho-a-la-seguridad-social
- unversioned_manifest: UnADM/licenciatura-en-derecho-unadm/filosofia-del-derecho-lde/estructura-aulatex.json
- missing_declared_path: UnADM/licenciatura-en-derecho-unadm/filosofia-del-derecho-lde/estructura-aulatex.json -> UnADM/licenciatura-en-derecho-unadm/filosofia-del-derecho-lde/assets-filosofia-del-derecho
- unversioned_manifest: UnADM/licenciatura-en-derecho-unadm/garantias-constitucionales-lde/estructura-aulatex.json
- missing_declared_path: UnADM/licenciatura-en-derecho-unadm/garantias-constitucionales-lde/estructura-aulatex.json -> UnADM/licenciatura-en-derecho-unadm/garantias-constitucionales-lde/assets-garantias-constitucionales
- unversioned_manifest: UnADM/licenciatura-en-derecho-unadm/interaprendizaje-en-ambientes-virtuales-lde/estructura-aulatex.json
- missing_declared_path: UnADM/licenciatura-en-derecho-unadm/interaprendizaje-en-ambientes-virtuales-lde/estructura-aulatex.json -> UnADM/licenciatura-en-derecho-unadm/interaprendizaje-en-ambientes-virtuales-lde/assets-interaprendizaje-en-ambientes-virtuales

### Temporales

No se autoriza borrado automatico, ni siquiera cuando existe una copia.

- .aulatex-temp: 0 archivos; 0 registrados en Git; 0 evidencias requieren revision.

### Limites

- No compilation or academic validation performed.
- Candidate names do not establish current or official status.
- Graphics, dynamic TeX paths and system package resolution are not validated.
- Temporary evidence matching uses identical filenames and SHA-256; absence of a match does not prove uniqueness.

Detalle verificable: aulaTEX/base/catalogos/catalogo-plantillas-aulatex.json. Seleccion explicita: aulaTEX/base/catalogos/seleccion-plantillas-aulatex.json.

<!-- AULATEX_CATALOG_END -->
