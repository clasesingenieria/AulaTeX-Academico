# AulaTeX

Suite local para coordinar edicion, investigacion, compilacion y evaluacion
editorial de plantillas academicas LaTeX.

## Lanzamiento

Desde la raiz del repositorio:

```powershell
.\scripts\aulatex.ps1
```

Modo CLI:

```powershell
.\scripts\aulatex.ps1 llm-env
.\scripts\aulatex.ps1 llm-check
.\scripts\aulatex.ps1 agent-patterns
.\scripts\aulatex.ps1 investigation --target .\UnADM\licenciatura-en-derecho-unadm\historia-del-derecho-en-mexico-lde --query "historia del derecho en mexico unadm programa analitico" --query "historia del derecho en mexico bibliografia recomendada"
.\scripts\aulatex.ps1 extractor --preview --target .\UnADM\licenciatura-en-derecho-unadm\historia-del-derecho-en-mexico-lde
.\scripts\aulatex.ps1 extractor --target .\UnADM\licenciatura-en-derecho-unadm\historia-del-derecho-en-mexico-lde --fuentes .\UnADM\licenciatura-en-derecho-unadm\historia-del-derecho-en-mexico-lde\referencias --planeacion .\UnADM\licenciatura-en-derecho-unadm\historia-del-derecho-en-mexico-lde\planeacion.txt --salida .\UnADM\licenciatura-en-derecho-unadm\historia-del-derecho-en-mexico-lde\extractor-aulatex --motor anthropicfoundry
.\scripts\aulatex.ps1 agent --target UnADM/licenciatura-en-derecho-unadm/historia-del-derecho-en-mexico-lde --action generar-actividad --activity 1
.\scripts\aulatex.ps1 compile .\UnADM\licenciatura-en-derecho-unadm\historia-del-derecho-en-mexico-lde\reporte-historia-del-derecho-en-mexico.tex
```

## Integracion LLM

AulaTeX usa un cliente HTTP propio en `scripts/aulatex/llm_bridge.py`.
Las credenciales se cargan desde `scripts/aulatex.env` antes de cada llamada.
Los motores disponibles son:

- `Auto (model-router)`
- `Claude Foundry`
- `GPT-Pro`
- `Codex`

`llm-env` muestra variables presentes/faltantes sin revelar secretos.
`llm-check` realiza una llamada HTTP real de verificacion por motor.
`llm-validate` comprueba la respuesta funcional de model-router por defecto y
devuelve JSON sin secretos; admite `--engine` para otros motores.
`llm-config` valida model-router y, si falla en una terminal interactiva, permite
corregir endpoint, API key y deployment o introducir el PIN maestro. Solo guarda
la configuración nueva tras validarla, con la API key cifrada. En Linux:

```bash
bash scripts/aulatex.sh llm-config
```

Consulta [la guía Linux](../../README-LINUX.md#validar-y-configurar-model-router)
para el alcance del PIN, el modo no interactivo y los límites de la prueba.

## Credenciales de plataformas por institución

En la interfaz gráfica, la pestaña **Plataformas** administra cuentas académicas
independientemente de las claves LLM de **Credenciales**:

1. Selecciona **Nueva**, elige o escribe una institución y asigna un nombre de
   plataforma/alias. Se admiten varias plataformas y cuentas por institución.
2. Introduce la URL HTTPS, el usuario y la contraseña. **Ejemplo ITESCA** completa
   únicamente institución, plataforma y `https://cursos3.e-itesca.edu.mx/login/index.php`;
   no contiene ni importa credenciales reales.
3. Introduce tu `AULATEX_MASTER_PIN` en el campo enmascarado y pulsa **Guardar cifrado**.
   Si el campo está vacío, se usa esa variable del entorno del proceso, si existe.
   Nunca se usa `secret.key` como alternativa ni se guarda el PIN en disco.
4. **Consultar** requiere el PIN y muestra solo ID de cuenta, institución, plataforma y sitio.
  Usa alias descriptivos para distinguir tus cuentas; el ID diferencia incluso filas con el mismo nombre.
   Selecciona una cuenta para editarla; usuario y contraseña no se precargan.
   Dejarlos vacíos conserva sus valores existentes. En una cuenta nueva ambos son obligatorios.
5. **Eliminar** solicita confirmación y el PIN. **Limpiar / bloquear** vacía campos
   y lista; también se limpian después de cinco minutos sin interacción en esta pestaña.
   Los campos sensibles se vacían después de cada operación, incluso si falla.

### Almacenamiento y seguridad

- Implementación: [platform_credentials.py](platform_credentials.py) y
  [platform_credentials_gui.py](platform_credentials_gui.py). Requiere `cryptography`,
  declarada en [requirements-linux-cli.txt](../requirements-linux-cli.txt).
  Si falta, solo se deshabilita esta pestaña: nunca se degrada a almacenamiento en claro.
- La ruta completa aparece al pie del formulario. Por defecto se guarda bajo
  `%LOCALAPPDATA%/AulaTeX/<identificador-del-workspace>/` en Windows, o
  `${XDG_DATA_HOME:-~/.local/share}/AulaTeX/<identificador-del-workspace>/` en Linux.
  No se almacena dentro del repositorio ni en sus corpus, memorias o manifiestos.
- Se cifra **todo el contenido**, incluidos usuario, contraseña y metadatos, con
  Fernet autenticado. La clave se deriva mediante PBKDF2-HMAC-SHA256 (600 000
  iteraciones), con salt aleatorio independiente del utilizado por las claves LLM.
  Solo versión, parámetros KDF, salt y ciphertext permanecen visibles en disco.
- Se cifra antes de crear cualquier temporal y se reemplaza el archivo de forma
  atómica. Un bloqueo exclusivo evita escrituras simultáneas de la aplicación.
  Si un cierre forzoso deja un bloqueo residual, cierra todas las instancias antes
  de retirar únicamente ese bloqueo, nunca la bóveda.
- Usa una **frase maestra larga y única**, no un PIN numérico corto: el cifrado no
  impide ataques offline contra contraseñas débiles. No existe recuperación del PIN.
  Conserva una copia cifrada de la bóveda fuera de Git y el PIN por separado.
  Al mover el repositorio cambia su identificador: usa la ruta mostrada para restaurar
  manualmente tu copia, con la aplicación cerrada.
- **Cambiar PIN** recifra únicamente esta bóveda y exige el PIN anterior y la
  confirmación del nuevo. No modifica las claves LLM ni el entorno. La rotación de
  secretos LLM tampoco cambia esta bóveda: coordina ambas rotaciones si quieres
  mantener una misma frase maestra. Las copias antiguas siguen usando el PIN anterior.
- La aplicación no conserva una clave descifrada entre operaciones. El borrado de
  campos no garantiza borrado físico de la memoria de Python. Un PIN exportado en
  el entorno seguirá disponible para el proceso aunque se pulse **Limpiar / bloquear**;
  para exigir entrada manual no lo exportes. Protege también tu sesión del sistema
  operativo; esta función no protege contra procesos maliciosos del mismo usuario.
- No se realiza inicio de sesión automático ni se envían datos a Telegram, al
  navegador o a motores LLM. Introduce secretos solo en el formulario local, nunca
  en el chat. Las credenciales existentes no se migran ni modifican automáticamente.

## Arquitectura agéntica unificada

AulaTeX conserva comandos especializados, pero el modelo mental recomendado es una fachada única:

```text
Motor inteligente
  -> decide campaña/lote y contratos
  -> usa LangGraph cuando hay ruteo por estado
  -> invoca agente, memoria, extractor, generación, revisión y compilación
  -> persiste memoria en `.memoria-aulatex`
```

Componentes principales:

- `AulaTeXAgent`: ejecuta tareas concretas sobre un nodo (`realizar-actividad`, `evaluar`, `generar-plantilla`).
- `IntelligentEngine`: orquesta campañas o lotes del repositorio.
- `ActivityMonitor`: cierra bucles de observación, reparación y reevaluación por actividad.
- `EditorialMemoryBuilder`: refuerza memoria editorial distribuida.
- `ConstructionBuilder`: crea/refuerza nodos con memoria fundacional, plan y maqueta.
- `AulaTeXLangChainAdapter`: adapta llamadas LLM cuando LangChain está disponible.
- `LangGraph`: backend opcional para nodos con ruteo y ciclos (`activity-monitor`, revisión y bibliografía).
- `EditorialContextProvider`: punto común de contexto para agente y generación.

`EditorialContextProvider` se encuentra en `scripts/aulatex/editorial_context.py` y combina:

- memoria distribuida y heredada;
- extractor y planeación;
- conceptos, ideas y trazabilidad;
- bibliografía local;
- referencias y planeaciones;
- señales TEX del nodo.

Prioridad de contexto:

```text
instrucciones locales > extractor > memoria distribuida > herencia > LLM
```

Guía de uso:

```powershell
# Actividad puntual con contexto editorial enriquecido
.\scripts\aulatex.ps1 agent --target <materia> --action realizar-actividad --activity 1 --run-extractor

# Bucle verificable con LangGraph
.\scripts\aulatex.ps1 activity-monitor --target <materia> --activity 1 --workflow-backend langgraph --run-extractor

# Campaña/lote del repositorio
.\scripts\aulatex.ps1 intelligent-engine --target . --backend langgraph

# Refuerzo de memoria distribuida
.\scripts\aulatex.ps1 editorial-memory --target <nodo> --build-level materia --propagation-mode local
```

## Propuesta: realizar-planeación

La especificación de [realizar-planeación](../../REALIZAR-PLANEACION.md) define una
acción hermana de `realizar-actividad` para construir una planeación académica de
una actividad desde redacciones, consignas, programas y rúbricas, sin exigir un TEX
previo. Incluye modos de normalización, propuesta y validación, trazabilidad por
campo, límites de herencia institucional y puntos de integración del motor.

**Es un contrato propuesto, no un comando disponible.** La implementación deberá
incorporar ejecutor y evaluador propios; no basta con registrar el nombre
`realizar-planeacion` ni aplicar el contrato editorial del producto estudiantil.

## Fase Investigación

La pestaña Investigación y el comando `investigation` consolidan la base de
conocimiento previa al extractor. La corrida combina contexto local del scope,
consultas web y memoria editorial heredada para producir:

- `investigacion-aulatex/base-conocimiento.json`
- `investigacion-aulatex/base-conocimiento.md`
- `investigacion-aulatex/fuentes-web.md`
- el `.bib` canónico del scope o uno sugerido si aún no existe
- `referencias-*/` cuando aplica
- `assets-*/` para institución o carrera cuando aplica
- `programa-analitico-*.md` para materia si aún no existe

El orden recomendado del flujo es:

1. construir memoria editorial;
2. consolidar investigación;
3. ejecutar el extractor;
4. generar, redactar y compilar.

## Adaptador del extractor

El subcomando `extractor` encapsula la ejecucion de
`scripts/extractor-conceptos-ideas/run.py` y deja una corrida trazable en:

```text
retroalimentacion-editorial/aulatex/extractor/runs/
```

La ejecucion queda normalizada con:

- `manifest.json`;
- `stdout.txt`;
- `stderr.txt`;
- verificacion de artefactos nucleares como `fichas_conceptos.json`,
  `conceptos_detectados.json`, `ideas_detectadas.json` y
  `trazabilidad_fuentes.json`.

La opcion `--preview` permite resolver scope, salida por defecto y comando
previsto sin lanzar el extractor.

## Ciclo agente

Cada ejecucion del agente crea una carpeta en:

```text
retroalimentacion-editorial/aulatex/runs/
```

El ciclo base es:

1. planificar con memoria compartida;
2. investigar el estado editorial del objetivo;
3. generar plantilla, actividad o propuesta;
4. materializar la propuesta cuando corresponde y compilar hasta dos `.tex` canonicos cuando se solicita;
5. validar el TEX actual, los resultados previos y la evidencia de compilacion;
6. criticar adversarialmente con la validacion anterior disponible.

Cada rol recibe memoria actualizada y los ultimos cinco resultados de etapas.
Los resultados extensos y los documentos que superan el limite de contexto se
marcan como truncados: no constituyen una revision completa.

### Garantias de realizar-actividad

- La generacion inicial no sustituye documentos ya redactados por ser breves o
  no contener diapositivas. Solo reemplaza contenido vacio o con marcas explicitas
  de construccion; monitor y optimizador pueden aplicar correcciones posteriores.
- La compilacion final exige exito del compilador y un PDF no anterior al TEX.
  Un PDF reciente no oculta errores; la ausencia de objetivos TEX es un fallo.
- La optimizacion solo informa exito si alcanza la calidad solicitada, no degrada
  el contrato y supera la auditoria semantica requerida. Agotar ciclos o estancarse
  por debajo del objetivo conserva el mejor estado, pero no devuelve exito.
- CLI y monitor visual usan un ciclo de monitor y optimizacion por convergencia
  de forma predeterminada. Esta conserva sus limites de 40 ciclos y 6 intentos
  consecutivos sin mejora. Los valores explicitos de ciclos siguen respetandose.
- La puntuacion de calidad y el consenso son indicadores internos; no sustituyen
  la revision academica de fuentes ni la inspeccion visual del PDF final.

El agente soporta dos modos de iteracion:

- `--cycle-mode stages`: modo corto. `--iterations` selecciona de 1 a 5 etapas del ciclo base.
- `--cycle-mode full`: modo intensivo. `--iterations N` ejecuta N ciclos completos de todos los roles. Por ejemplo, `--iterations 2 --cycle-mode full` ejecuta 10 llamadas LLM; `--iterations 100 --cycle-mode full` ejecuta 500 llamadas LLM si hay cinco roles activos.

Uso recomendado:

```powershell
# Prueba corta
.\scripts\aulatex.ps1 agent --target .\UnADM\licenciatura-en-derecho-unadm\filosofia-del-derecho-lde --action evaluar --iterations 2 --cycle-mode full --no-compile --no-extractor

# Corrida intensiva controlada
.\scripts\aulatex.ps1 agent --target .\UnADM\licenciatura-en-derecho-unadm\filosofia-del-derecho-lde --action realizar-actividad --activity 5 --iterations 100 --cycle-mode full --no-compile
```

Para corridas intensivas conviene usar primero `--no-compile` y `--extractor-probe` o `--no-extractor`, validar el estado, y luego activar herramientas costosas por lote.

La capa agentica vive en `scripts/aulatex/agentic_patterns.py` e incorpora:

- planificacion + memoria aumentada;
- registro de herramientas con invocacion segura;
- flujo con maquina de estados y auditoria;
- verificacion/validacion editorial;
- consenso multiagente con critico adversarial.

## Siguiente capa: agente con bucle real

La arquitectura actual ya cubre memoria editorial, investigacion, generacion y
evaluacion. El siguiente paso es cerrar el bucle operativo por actividad con un
estado persistido, decisiones explicitas y reevaluacion por artefactos.

El contrato propuesto para esa capa vive en:

```text
retroalimentacion-editorial/aulatex/agente-verdadero-contrato-operativo.md
```

La bitacora acumulada vive en:

```text
retroalimentacion-editorial/aulatex/bitacora.md
```
