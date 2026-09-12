# AulaTeX-Academico

Entorno academico en LaTeX organizado por institucion, con una base comun de
plantillas Pizarror y puntos de entrada canonicos para reportes, actividades,
presentaciones y bibliografias.

## Ubuntu y VS Code Remote SSH

El entorno Linux se instala con `bash setup.sh --no-shell --skip-llm` e incluye
TeX Live completo de Ubuntu 24.04 y un entorno Python independiente de Windows.
`bash setup.sh --all --no-shell` añade extracción documental, multimedia,
bibliotecas IA, entrenamiento CPU y notebooks, sin descargar modelos ni configurar secretos.
Consulta [README-LINUX.md](README-LINUX.md) para instalación, compilación,
perfiles opcionales y uso de [AulaTeX-Linux.code-workspace](AulaTeX-Linux.code-workspace).

## Entrenamiento del motor inteligente

La ruta progresiva está en `notebooks/`, desde la verificación de la GPU hasta
la evaluación y publicación del adaptador. La lógica reutilizable vive en
`scripts/aulatex_training/`; los notebooks no duplican el motor editorial.

El modelo no es un único archivo que haga peticiones. El sistema desplegable
combina el modelo base, un adaptador LoRA, tokenizer/configuración y código de
inferencia. Git conserva código, configuración, pruebas y manifiestos pequeños.
Los corpus privados, checkpoints y pesos quedan en `data/private/`,
`checkpoints/` y `models/local/`, ignorados por Git; la copia canónica debe
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

- Automatizacion de compilacion y exportacion: `scripts/`.- Entrada recomendada para trabajo editorial: `scripts/aulatex.ps1`.

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
|---|---|---|
| Realizar o evaluar una actividad | `aulatex.ps1 agent --action realizar-actividad --activity N` | `AulaTeXAgent`, `EditorialContextProvider`, extractor opcional, LLMs |
| Bucle verificable de actividad | `aulatex.ps1 activity-monitor --activity N --workflow-backend langgraph` | `ActivityMonitor`, LangGraph, observer, revision, reparacion |
| Crear o reforzar nodos | `aulatex.ps1 generation ...` | `ConstructionBuilder`, memoria fundacional, contexto editorial |
| Reforzar memoria editorial | `aulatex.ps1 editorial-memory ...` | `EditorialMemoryBuilder`, `MemoryFusionEngine`, `.memoria-aulatex` |
| Campañas o lotes sobre el repo | `aulatex.ps1 intelligent-engine ...` | `IntelligentEngine`, contratos, ejecucion resumible |
| Extraer conceptos/referencias | `aulatex.ps1 extractor ...` | `ExtractorAdapter` |
| Comunicacion por bot | `bot-interfaz` con `/motor ...` | Planifica instruccion, muestra resumen, pide validacion y ejecuta `IntelligentEngine` solo tras confirmacion |

### Compatibilidad entre flujos

| Flujo | Productos duraderos que genera | Flujos que lo consumen |
|---|---|---|
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

La clase `scripts/aulatex/editorial_context.py` reune para cada nodo:

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

## Contratos de `realizar-actividad` (motor inteligente)

El motor inteligente `realizar-actividad` opera bajo un **contrato editorial explícito** definido en `scripts/aulatex/activity_contract.py` (`REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT`). Ese contrato se **propaga al prompt del agente** a través de `scripts/aulatex/incremental_detail_planner.py` (bloques `didactic_contract`, `structure_contract`, `layout_contract`, `bibliography_contract` y `_quality_rules()`), y se **evalúa** con `evaluate_activity_contract()` (consumido por `activity-observe` y `activity-monitor`).

> Propósito del contrato: tomar un nodo, carpeta o archivo de actividad y llevarlo desde memoria e insumos hasta TEX/PDF final validado mediante ciclos repetibles.

### Fases del pipeline (compromisos de proceso)

El pipeline se compromete a recorrer, en orden, estas fases:

| # | Fase | Compromiso |
|---|---|---|
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
|---|---|---|
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

> Ejecución masiva por lotes: para lanzar muchos ciclos de forma resistente a cuelgues, `scripts/act2-100ciclos-monitor.ps1` divide el trabajo en lotes con *watchdog* por lote y timeout de LLM configurable (`AULATEX_LLM_TIMEOUT_SECONDS`, `AULATEX_LLM_MAX_TOKENS`), registrando el progreso en `.aulatex-temp/`.

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
.\scripts\install-aulatex-deepagents.ps1
```

Para medir desempeño de forma explícita:

```powershell
.\scripts\aulatex.ps1 gui --diagnostics
```

```powershell
$env:AULATEX_ENABLE_DIAGNOSTIC_METRICS=1
.\scripts\aulatex.ps1 investigation --target .\UnADM\licenciatura-en-derecho-unadm\historia-del-derecho-en-mexico-lde --query "historia del derecho en mexico unadm programa analitico"
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
|-- base/
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
|-- retroalimentacion-editorial/
`-- scripts/
```

## Convenciones

- Reporte general: `reporte-<materia>.tex`.
- Actividad: `reporte-<materia>-Actividad-N.tex`.
- Presentacion: `presentacion-<materia>.tex`.
- Bibliografia local: `<materia>.bib`.
- Cuando una institucion tiene mas de un programa educativo, el nivel canonico se mueve a `institucion/carrera/materia`.

## Base Original

El proyecto conserva el nucleo tecnico de `Template-Informe` de Pablo Pizarro R.
en `base/Plantilla-Informe/`, junto con copias originales y adaptaciones
institucionales. Licencia base: MIT.

## Environment

Use `scripts/aulatex.env` o variables de entorno locales para configurar
proveedores. No publiques llaves reales en este archivo.

### PIN maestro y rotacion de claves

Los secretos de `scripts/aulatex.env` se guardan cifrados con prefijo `enc:`
(Fernet). La clave se deriva del PIN maestro `$env:AULATEX_MASTER_PIN` mediante
PBKDF2-SHA256 (480 000 iteraciones) sobre `scripts/secret.salt`. El PIN nunca se
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

Para cambiar el PIN, `scripts/rotate-pin.ps1` descifra los valores `enc:` con el
PIN actual, renueva el salt y vuelve a cifrarlos con el nuevo. Ambos PIN se piden
como `SecureString` y viajan por stdin, asi que no quedan en el historial. Si un
token no descifra, aborta sin escribir nada; ademas deja `aulatex.env.bak-rotate`
como respaldo. Renovar el salt invalida las claves derivadas del PIN anterior,
de modo que una copia vieja del `.env` deja de servir aunque se conozca ese PIN.

El minimo son 4 caracteres, pero por debajo de 16 (o si el PIN es solo numerico)
el script advierte, calcula el espacio de busqueda y exige escribir `ACEPTO`.

```powershell
.\scripts\rotate-pin.ps1            # PIN solo para la consola actual
.\scripts\rotate-pin.ps1 -Persist   # ademas lo guarda en la variable de usuario
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

`scripts/sync-keys.ps1` sustituye las claves del `.env` con las de tus
suscripciones. Recorre todas las suscripciones de `az account list`, inventaria
las cuentas de Cognitive Services y asocia cada variable `*_API_KEY` con la
cuenta cuyo host coincide con su `*_BASE_URL` o `*_ENDPOINT` hermano. El valor en
claro viaja solo por stdin: nunca por argv ni por el historial de PowerShell.

```powershell
# Inventario y plan, sin escribir nada
.\scripts\sync-keys.ps1 -WhatIf

# Sincroniza las claves vigentes (respalda el .env antes)
.\scripts\sync-keys.ps1

# Rotacion real: regenera key1 en Azure y sustituye
.\scripts\sync-keys.ps1 -Rotate

# Acotar a ciertas variables o suscripciones
.\scripts\sync-keys.ps1 -Name MODEL_ROUTER_API_KEY,CODEX_API_KEY
.\scripts\sync-keys.ps1 -Subscription 'Suscripcion Maury'

# AWS IAM (Polly). Sin -DeactivateOld la clave anterior sigue activa.
.\scripts\sync-keys.ps1 -IamUserName <usuario-iam> -DeactivateOld
```

Utilidades de `scripts/secrets_local.py`:

```powershell
python scripts\secrets_local.py encrypt aulatex.env       # cifra valores en claro
python scripts\secrets_local.py decrypt-env aulatex.env   # NOMBRE<TAB>valor
'<valor>' | python scripts\secrets_local.py set-value aulatex.env NOMBRE
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
# '<valor>' | python scripts\secrets_local.py set-value scripts\aulatex.env MODEL_ROUTER_API_KEY
# Después, cifra cualquier secreto en claro:
# python scripts\secrets_local.py encrypt scripts\aulatex.env

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

Los valores siguientes distinguen tres capas: límites teóricos declarados/configurados, límites probados por llamadas reales y límites operativos que usa AulaTeX para estabilizar la ejecución local. Las pruebas se ejecutaron el 2026-07-08 con `scripts/validar-limites-deployments.ps1`. Los artefactos principales están en `.aulatex-temp/deployment-limit-probe/runs/20260708-133615/`, con refinamientos en `20260708-163927`, `20260708-164136` y `20260708-164637`.

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

- `scripts/aulatex.env` fija `AULATEX_OPERATIVE_INPUT_TOKENS_*` y `AULATEX_MAX_OUTPUT_TOKENS_*` con los valores anteriores.
- `scripts/aulatex/llm_bridge.py` aplica `AULATEX_MAX_OUTPUT_TOKENS_<PREFIJO>` por motor antes de invocar el proveedor.
- `scripts/prueeba-lote-ejecucion-1.ps1` usa defaults actualizados para presupuestos DNA y salida de los motores principales.
- `0` o “no validada” en entrada probada significa que no se alcanzó éxito estable: la API falló por `rate_limit`, alta demanda o tamaño máximo permitido bajo carga antes de demostrar el límite duro del modelo.
- La salida probada indica que la API aceptó el valor de `max_output_tokens`; no implica que el modelo haya producido esa cantidad completa de tokens.
