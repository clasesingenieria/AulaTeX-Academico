# notas-telegram

Bot de Telegram para recibir texto o audio, transcribirlo y convertirlo en una nota Markdown limpia con conceptos clave para base de conocimiento.

Las notas y sus derivados Markdown dentro de `data/notes/` estan pensados para versionarse en Git. El resto de `data/` sigue siendo salida local no versionada.

## Flujo

1. Telegram recibe texto, nota de voz o audio.
2. Si es audio, se descarga en `data/audio/` y se transcribe con Azure Speech.
3. El texto crudo o el contenido de un documento se envia a Azure OpenAI para generar:
   - titulo breve usable como nombre clave;
   - redaccion limpia o nota-resumen sintetica si la entrada es un documento;
   - conceptos clave con definicion;
   - terminos relacionados.
4. La nota se guarda en `data/notes/YYYY-MM-DD/`.
5. La nota base incluye una seccion `Procesamientos derivados` con enlaces relativos a los Markdown de `Explicar`, `Sugerencias`, `Investigar` y `Dialectica`.
6. Cada derivado se guarda como un `.md` hermano de la nota base cuando se genera desde Telegram o GUI.
7. Se actualizan `index.md` del dia e `index.json` global.

## Contrato de salida

La fuente canonica de todos los entregables es siempre el Markdown local guardado en `data/notes/`.

Reglas:

1. Primero se guarda la nota base local.
2. Desde esa nota local se derivan los entregables visibles o reutilizables.
3. Los derivados `Explicar`, `Sugerencias`, `Investigar` y `Dialectica` tambien se guardan primero como Markdown local.
4. Audio, portapapeles y envios a Telegram se filtran desde esos Markdown locales, nunca desde una copia paralela del texto en memoria.

Orden del pipeline:

1. Entrada de texto, audio o documento.
2. Analisis y redaccion de la nota base.
3. Guardado de la nota local en `data/notes/YYYY-MM-DD/`.
4. Copia al portapapeles de la redaccion limpia filtrada desde la nota local.
5. Envio del texto visible de la nota a Telegram.
6. Envio del Markdown filtrado de la nota a Telegram.
7. Presentacion de botones y estados.
8. Generacion paralela de derivados.
9. Guardado local de cada derivado.
10. Entrega de derivados a Telegram en orden estable: `Explicar`, `Sugerencias`, `Investigar`, `Dialectica`.
11. Filtrado por canal a partir del derivado local cuando se reproduce, copia o envia.

Contrato de redaccion para derivados:

- El modelo debe responder con estas secciones conceptuales: `Nucleo`, `Desarrollo`, `Accionables`, `Evidencias y supuestos`, `Sintesis breve`.
- Si el modelo devuelve encabezados legacy como `Resumen ejecutivo`, `Hallazgos clave`, `Acciones recomendadas para profundizar`, `Preguntas abiertas` o `Sintesis final`, el guardado local los normaliza a las cinco secciones canonicas sin recortar arbitrariamente la prosa.
- El Markdown local del derivado conserva la version mas rica y estable para versionado.
- El prompt ya no usa ratios de compactacion por canal. En su lugar exige secciones autosuficientes, sin recapitulaciones internas ni frases dependientes del encabezado para entenderse.

Contrato de filtrado por canal:

- Portapapeles de nota base: solo `Nota limpia`.
- Audio de nota base: titulo, `Nota limpia` y un resumen corto de conceptos si aporta valor.
- Markdown de Telegram para nota base: cuerpo de la nota sin frontmatter ni `Procesamientos derivados`.
- Telegram para derivados: conserva `Nucleo`, `Desarrollo`, `Accionables` y `Sintesis breve`; elimina metadata y rotulos editoriales redundantes.
- Audio para derivados: parte del mismo Markdown local, elimina metadata, encabezados de seccion y anexos metodologicos, y convierte listas a frases pronunciables.
- Portapapeles para derivados: parte del mismo Markdown local, elimina metadata, encabezados de seccion, anexos metodologicos y rotulos editoriales como `Integracion operativa`, `Regla practica` o `Pregunta abierta`.
- Las omisiones ya no se hacen por porcentaje de texto sino por reglas estructurales y expresiones regulares sobre el Markdown local.

El frontmatter de cada nota se mantiene deliberadamente corto:

```yaml
id: "YYYYMMDDHHMMSS"
title: "HH:MM - Titulo en formato oracion"
key: "titulo_en_formato_oracion"
created_at: "..."
tags:
  - "concepto principal"
related_terms:
  - "termino relacionado"
```

Las definiciones de conceptos quedan en el cuerpo de la nota, no como metadata.

Ejemplo de derivados generados para una nota `20260703_101530_mi_idea.md`:

```text
20260703_101530_mi_idea.md
20260703_101530_mi_idea.explain.md
20260703_101530_mi_idea.suggest.md
20260703_101530_mi_idea.research.md
20260703_101530_mi_idea.dialectic.md
```

## Variables de entorno

```env
TELEGRAM_BOT_TOKEN=
NOTES_DIR=data/notes
AUDIO_STORAGE_DIR=data/audio
BOT_MODE=polling

AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=
AZURE_SPEECH_LANGUAGE=es-MX

# LLM para analisis/generacion: azure-openai, codex, gpt-pro, model-router/auto o claude-foundry.
LLM_PROVIDER=azure-openai

AZURE_OPENAI_ENDPOINT=https://TU-RECURSO.openai.azure.com/
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_CHAT_DEPLOYMENT=
# Tambien se acepta AZURE_OPENAI_DEPLOYMENT_NAME, compatible con Bedrock-prueba.
AZURE_OPENAI_DEPLOYMENT_NAME=
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_CONTEXT_WINDOW_TOKENS=1050000
AZURE_OPENAI_MAX_INPUT_TOKENS=922000
AZURE_OPENAI_MAX_OUTPUT_TOKENS=128000
# Opcional: override legacy solo para research; si no se define, usa el maximo global de salida.
RESEARCH_MAX_TOKENS=128000

# Transcripcion: speech, realtime o auto.
TRANSCRIPTION_PROVIDER=auto
AZURE_OPENAI_REALTIME_ENDPOINT=https://TU-RECURSO.services.ai.azure.com
AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME=gpt-realtime
AZURE_OPENAI_REALTIME_API_KEY=
AZURE_OPENAI_REALTIME_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe
```

Tambien se acepta `NOTES_OUTPUT_DIR` como alias de `NOTES_DIR`.

Si usas Azure AI Foundry con endpoint `openai/v1`, puedes poner las credenciales en `notas.env` o `credenciales.env`. La carga se hace en este orden: `.env`, `notas.env` y finalmente `credenciales.env`, por lo que `credenciales.env` tiene prioridad.

La variable `LLM_PROVIDER` selecciona el bloque activo:

```env
# Auto / model-router
LLM_PROVIDER=model-router
MODEL_ROUTER_BASE_URL=https://TU-RECURSO.services.ai.azure.com/openai/v1/chat/completions
MODEL_ROUTER_API_KEY=
MODEL_ROUTER_CHAT_DEPLOYMENT=model-router
MODEL_ROUTER_API_VERSION=2025-11-18

# GPT-Pro
LLM_PROVIDER=gpt-pro
GPT_PRO_BASE_URL=https://TU-RECURSO.services.ai.azure.com/openai/v1/responses
GPT_PRO_API_KEY=
GPT_PRO_CHAT_DEPLOYMENT=gpt-5.4-pro
GPT_PRO_API_VERSION=2026-03-05

# Codex
LLM_PROVIDER=codex
CODEX_BASE_URL=https://TU-RECURSO.services.ai.azure.com/openai/v1/responses
CODEX_API_KEY=
CODEX_CHAT_DEPLOYMENT=gpt-5.3-codex
CODEX_API_VERSION=2026-02-24

# Claude Foundry
LLM_PROVIDER=claude-foundry
ANTHROPIC_FOUNDRY_BASE_URL=https://TU-RECURSO.services.ai.azure.com/anthropic
ANTHROPIC_FOUNDRY_API_KEY=
ANTHROPIC_FOUNDRY_CHAT_DEPLOYMENT=claude-opus-4-8
ANTHROPIC_FOUNDRY_API_VERSION=2023-06-01
```

`LLM_PROVIDER=auto` es alias de `model-router`. Los bloques OpenAI-compatible usan Responses API o Chat Completions segun el sufijo del endpoint. Claude Foundry usa la Anthropic Messages API en `/anthropic/v1/messages`.

Tambien se aceptan aliases legacy para `azure-openai`: `AZURE_EXISTING_AIPROJECT_ENDPOINT` o `AZURE_ENDPOINT` como endpoint, y `AZURE_API_KEY` como API key.

## Resultados de benchmark LLM

Corrida de referencia hecha el 2026-07-08 sobre 5 notas reales del repositorio, usando el prompt operativo del bot con la accion `explain` y topes maximos por proveedor. Esta seccion refleja la rerun mas reciente, despues de confirmar que el deployment de Claude Foundry ya estaba operativo.

Topes usados en esta corrida:

- `codex`: `128000`
- `gpt-pro`: `128000`
- `model-router`: `128000`
- `claude-foundry`: `128000`

Resumen de la corrida en este entorno:

| Proveedor | Exitos | Estructura completa | Latencia media | Salida media |
| --- | --- | --- | --- | --- |
| `codex` | 5/5 | 5/5 | 10.71 s | 724 palabras |
| `gpt-pro` | 5/5 | 5/5 | 140.68 s | 1453 palabras |
| `model-router` | 5/5 | 5/5 | 37.51 s | 1172 palabras |
| `claude-foundry` | 5/5 | 5/5 | 32.28 s | 809 palabras |

Ranking de calidad heuristica sobre salidas completas capturadas en esa misma corrida:

| Ranking | Proveedor | Puntaje medio | Cobertura de conceptos | Cobertura relacionada | Concision |
| --- | --- | --- | --- | --- | --- |
| 1 | `claude-foundry` | 91.28 | 0.779 | 0.792 | 1.00 |
| 2 | `model-router` | 88.98 | 0.879 | 0.742 | 0.76 |
| 3 | `codex` | 86.53 | 0.639 | 0.738 | 1.00 |
| 4 | `gpt-pro` | 80.75 | 0.693 | 0.796 | 0.60 |

Lectura operativa:

- `claude-foundry` quedo 5/5 en estabilidad y obtuvo el mejor puntaje de calidad heuristica en `explain`, con mejor equilibrio entre cobertura y concision que el resto en esa accion.
- `model-router` quedo segundo en calidad en `explain`, pero siguio siendo competitivo, especialmente por cobertura de conceptos.
- `codex` sigue siendo el mas rapido y muy estable, pero con menor cobertura conceptual media que Claude y model-router.
- `gpt-pro` mantuvo 5/5, pero siguio siendo el mas lento y el menos conciso del grupo operativo.

Barrido multiaccion adicional (`suggest`, `research`, `dialectic`):

| Accion | Ganador por calidad | Puntaje medio |
| --- | --- | --- |
| `explain` | `claude-foundry` | 91.28 |
| `suggest` | `gpt-pro` | 81.66 |
| `research` | `codex` | 89.79 |
| `dialectic` | `model-router` | 84.99 |

Promedio global de calidad heuristica entre las 4 acciones evaluadas:

| Ranking global | Proveedor | Promedio |
| --- | --- | --- |
| 1 | `model-router` | 85.45 |
| 2 | `codex` | 84.86 |
| 3 | `claude-foundry` | 84.36 |
| 4 | `gpt-pro` | 81.21 |

Lectura global:

- `model-router` no gana `explain`, pero queda primero en el promedio total y se mantiene arriba o muy cerca del primero segun la accion.
- `claude-foundry` destaca en `explain`, pero no se sostuvo como mejor opcion al ampliar la evaluacion a `suggest`, `research` y `dialectic`.
- `codex` tuvo el mejor resultado en `research` y mantuvo gran estabilidad con la menor latencia media del grupo.
- `gpt-pro` gano `suggest`, pero siguio penalizado por verbosidad y latencia.

Decision de default actual:

- Dado que el barrido multiaccion deja a `model-router` por encima del resto en promedio global, el `LLM_PROVIDER` por defecto del entorno activo y del ejemplo de configuracion queda en `model-router`.
- Para derivados automaticos, el bot usa el mejor proveedor por accion segun la evaluacion: `explain` -> `claude-foundry`, `suggest` -> `gpt-pro`, `research` -> `codex`, `dialectic` -> `model-router`.
- Esos cuatro derivados se generan en paralelo para reducir tiempo total, pero se envian a Telegram en orden estable: `Explicar`, `Sugerencias`, `Investigar`, `Dialectica`.

Estado separado de `azure-openai`:

- No forma parte de esta matriz final porque el deployment actual responde `The requested operation is unsupported.` para este benchmark. El problema ya no es carga de variables, sino compatibilidad de endpoint/deployment con esta operacion.

Estos resultados son dependientes de la configuracion activa en `notas.env`, del deployment asociado a cada proveedor y del tipo de prompt evaluado. No deben leerse como ranking universal. Tampoco validan saturacion real del contexto maximo de entrada: las 5 notas usadas estan muy por debajo de 200k, 400k o 1M tokens.

Para repetir la medicion o cambiar notas/accion:

```powershell
c:/Users/delaCruz/Documents/notas-telegram/.venv/Scripts/python.exe aulaTEX/evaluate_llms_on_notes.py --providers codex gpt-pro model-router claude-foundry --action explain --provider-max-tokens codex=128000 gpt-pro=128000 model-router=128000 claude-foundry=128000
```

Para recalcular el ranking de calidad sobre salidas completas:

```powershell
c:/Users/delaCruz/Documents/notas-telegram/.venv/Scripts/python.exe aulaTEX/analyze_llm_quality.py logs/monitoring/llm_benchmark_max_limits_raw_recheck_20260708.json --output logs/monitoring/llm_benchmark_max_limits_raw_recheck_20260708_quality.json
```

Reportes generados en esta corrida:

- `logs/monitoring/llm_benchmark_max_limits_raw_recheck_20260708.json`
- `logs/monitoring/llm_benchmark_max_limits_raw_recheck_20260708_quality.json`

Reportes multiaccion adicionales:

- `logs/monitoring/llm_benchmark_suggest_raw_20260708.json`
- `logs/monitoring/llm_benchmark_suggest_raw_20260708_quality.json`
- `logs/monitoring/llm_benchmark_research_raw_20260708.json`
- `logs/monitoring/llm_benchmark_research_raw_20260708_quality.json`
- `logs/monitoring/llm_benchmark_dialectic_raw_20260708.json`
- `logs/monitoring/llm_benchmark_dialectic_raw_20260708_quality.json`

Reportes anteriores, utiles solo para comparar el efecto del tope artificial de 3000 tokens:

- `logs/monitoring/llm_benchmark_max_limits_20260708.json`
- `logs/monitoring/llm_benchmark_full_20260708.json`
- `logs/monitoring/llm_benchmark_azure_claude_20260708.json`
- `logs/monitoring/llm_benchmark_recheck_20260708.json`

## Instalacion

```powershell
./interfaz-telegram.ps1 -BootstrapOnly
```

Ese comando crea o reutiliza la .venv local de bot-interfaz en `bot-interfaz/.venv` e instala `requirements.txt` sin depender de la `.venv` raiz del repositorio.

Tambien puedes instalar manualmente dentro de esa venv local:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Motor editorial

El comando `/motor` y el prefijo `motor:` ahora soportan tres modos de ejecucion sobre AulaTeX:

- `intelligent-engine`: planificacion e inventario de campanas o lotes.
- `agent`: ejecucion puntual de `generar-plantilla`, `generar-actividad` o `realizar-actividad`.
- `activity-monitor`: ciclos repetidos de observacion, revision, extractor y compilacion.

Ejemplos:

```text
/motor planifica UCNL/licenciatura-en-administracion/administracion-i-lad actividad 1
/motor realiza la actividad 1 de UCNL/licenciatura-en-administracion/administracion-i-lad con extractor y 4 iteraciones
/motor monitorea UCNL/licenciatura-en-administracion/administracion-i-lad actividad 1 hasta pasar con backend classic
```

Tambien necesitas `ffmpeg` disponible en el `PATH` para convertir los audios de Telegram antes de transcribirlos.

### Proveedor de transcripcion

Por defecto se usa Azure Speech (`TRANSCRIPTION_PROVIDER=speech`). Si quieres que la transcripcion use GPT Realtime por su mayor discernimiento contextual, configura:

```env
TRANSCRIPTION_PROVIDER=realtime
AZURE_OPENAI_REALTIME_ENDPOINT=https://TU-RECURSO.services.ai.azure.com
AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME=gpt-realtime
AZURE_OPENAI_REALTIME_API_KEY=
AZURE_OPENAI_REALTIME_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe
```

Tambien puedes usar `TRANSCRIPTION_PROVIDER=auto` para intentar GPT Realtime primero y volver a Azure Speech si falla la sesion realtime. El audio se convierte con `ffmpeg` a PCM16 mono 24 kHz para enviarlo por WebSocket a Realtime.

## Ejecucion

```powershell
./notas-telegram.ps1
```

### Interfaz grafica local (GUI)

Tambien puedes abrir una interfaz local para capturar texto, audio o documento y generar notas con el mismo pipeline:

```powershell
$env:NOTAS_GUI_MODE='1'
./notas-telegram.ps1
```

O de forma mas simple:

```powershell
./notas-telegram.ps1 -Gui
```

La variable de entorno solo aplica a la terminal actual. Si abres otra terminal o reinicias VS Code, debes volver a definirla.

```powershell
$env:NOTAS_GUI_MODE='1'
./notas-telegram.ps1
```

La GUI usa una vista compacta de trabajo: texto libre arriba, controles de audio/documento/generacion debajo y una lista de resultados en tarjetas compactas.

La lista incluye 5 procesamientos:

- Nota guardada
- Explicar
- Sugerencias
- Investigar
- Dialectica

Cada tarjeta muestra:

- chip de estado (`Listo`, `Procesando`, `Pendiente`, `Error`);
- nombre del procesamiento;
- vista previa de dos lineas;
- botones `Play`, `Pause`, `Stop` cuando hay audio generado;
- boton `Ver`.

Al seleccionar una tarjeta se abre un panel flotante reutilizable sin empujar el resto de la interfaz. El panel muestra el contenido completo con scroll y acciones para reproducir audio, copiar, guardar como Markdown o cerrar.

Atajos de la GUI:

- `Alt+Enter`: generar nota desde la caja de texto libre;
- `Ctrl+1` a `Ctrl+5`: abrir la tarjeta correspondiente;
- `Alt+1` a `Alt+5`: reproducir el audio de la tarjeta correspondiente;
- `Espacio`: reproducir/pausar la tarjeta abierta;
- `C`: copiar el contenido del panel flotante abierto;
- `Esc`: cerrar el panel flotante.

El lector de documentos soporta `.pdf`, `.txt`, `.md` y `.docx`.

Cuando la entrada es un documento, la nota resultante busca ser una sintesis util y no demasiado extensa, con un objetivo aproximado de unos 3 minutos de lectura. Esa nota sintetizada alimenta luego las mismas acciones: `Explicar`, `Sugerencias`, `Investigar` y `Dialectica`.

En Telegram tambien puedes adjuntar documentos compatibles y el bot los procesara como nota-resumen.

En la GUI, esos cuatro resultados tambien se guardan como Markdown derivados de la nota base, igual que en Telegram.

La reproduccion de audio dentro de la GUI usa `pygame-ce`, importado como `pygame` (sin abrir reproductor externo).

Si `pygame-ce` no inicializa en tu equipo, la GUI aplica fallback automatico a reproductor externo del sistema para que `Play` siga funcionando y muestra la causa en el estado de la tarjeta.
Los audios generados por la GUI se conservan por tarjeta en `data/audio/gui/*_latest.mp3` durante la sesion activa.

Para detenerlo:

```powershell
./detener-notas-bot.ps1
```

Los scripts evitan levantar dos instancias locales del bot con polling. El bot guarda el PID en `data/notas-bot.pid` y escribe logs en `data/logs/`.

## Acciones sobre notas

Despues de guardar una nota, el bot ofrece acciones rapidas:

- `Explicar`
- `Sugerencias`
- `Investigar`
- `Dialectica`

La accion `Investigar` reutiliza la logica rescatada del prototipo para ampliar un tema con:

- resumen ejecutivo;
- hallazgos clave;
- implicaciones practicas;
- preguntas abiertas;
- acciones recomendadas para profundizar.

Si el tema requiere datos actuales o fuentes externas, la respuesta lo indica y sugiere que consultas conviene verificar aparte.

Cada vez que generas una de estas acciones, el sistema guarda un archivo Markdown derivado junto a la nota original y actualiza la seccion de enlaces dentro de la nota base.

## Audio de respuesta opcional

El bot puede reenviar cada respuesta textual tambien como audio usando AWS Polly.
La integracion se tomo de forma minima desde `upgrade/aws-polly-epub-to-m4a`.

Variables relevantes:

```env
TELEGRAM_REPLY_AUDIO_ENABLED=true
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
POLLY_VOICE_ID=Andres
POLLY_ENGINE=generative
POLLY_LANGUAGE_CODE=es-MX
POLLY_SAMPLE_RATE=24000
POLLY_MAX_CHARS=2500
POLLY_TTS_WORKERS=12
```

`POLLY_TTS_WORKERS` controla cuantas llamadas a Polly se ejecutan en paralelo al convertir chunks de texto a MP3. El valor por defecto es `12`; el merge final conserva el orden original de los fragmentos.

Comportamiento:

- primero se envia el texto al usuario;
- despues se envia la misma salida en uno o varios audios cortos;
- si Polly falla, el bot conserva la respuesta en texto y no rompe el flujo.

## Manejo de archivos generados

El directorio `data/` contiene artefactos de ejecucion local y esta excluido del versionado por `.gitignore`. Las notas, audios, documentos temporales y trazas de monitoreo se manejan asi:

| Tipo | Ruta | Persistencia local | Archivos temporales | Versionado |
| --- | --- | ---: | --- | ---: |
| Codigo fuente | `src/` | Si | No | Si |
| Pruebas | `tests/` | Si | No | Si |
| Documentacion y configuracion no secreta | `README.md`, `docs/`, `requirements.txt`, `pytest.ini` | Si | No | Si |
| Notas generadas | `data/notes/YYYY-MM-DD/*.md` | Si | No | Si |
| Derivados Markdown (`Explicar`, `Sugerencias`, `Investigar`, `Dialectica`) | `data/notes/YYYY-MM-DD/*.explain.md`, `*.suggest.md`, `*.research.md`, `*.dialectic.md` | Si | No | Si |
| Indices de notas | `data/notes/YYYY-MM-DD/index.md`, `data/notes/index.json` | Si | No | Si |
| Documentos recibidos por Telegram | `data/audio/documents/` | No, se borran al finalizar | Si: copia descargada del PDF/TXT/MD/DOCX | No |
| Audio recibido por Telegram | `data/audio/*` | No, se borra si el flujo termina bien | Si: copia descargada del audio entrante | No |
| Audio TTS del bot | `data/audio/tts/` | No si el envio termina bien | Si: fragmentos Polly y MP3 fusionado antes de enviarlo | No |
| Respuestas largas en Markdown | `data/audio/responses/` | No si el envio termina bien | Si: `.md` creado cuando el texto supera el limite de Telegram | No |
| Acciones `Explicar`, `Sugerencias`, `Investigar`, `Dialectica` | Telegram, GUI y `data/notes/` | Si, como Markdown derivado | Si: MP3 TTS y `.md` temporal de respuesta larga en Telegram | Si |
| Boton `Play` de acciones | Telegram | No como archivo local permanente | Si: MP3 TTS de cada accion antes de enviarlo | No |
| Audios de la GUI | `data/audio/gui/*_latest.mp3` | Si, durante la sesion local | Si: MP3 inicial de TTS antes de copiarlo a `*_latest.mp3` | No |
| Monitoreo de PDF | `data/monitoring/pdf_pipeline_probe_*.json` | Si | Si: PDFs sinteticos en `data/monitoring/notas_pdf_probe_*/` | No |
| Logs y PID | `data/logs/`, `data/notas-bot.pid` | Si mientras corre o para diagnostico | Si: PID y logs de ejecucion | No |
| Entorno y secretos locales | `.venv/`, `.env`, `credenciales.env`, `notas.env` | Si | No | No debe versionarse |

> Importante: `notas.env` contiene credenciales locales y debe mantenerse fuera de Git. Si aparece como archivo no rastreado, no lo agregues al repositorio.

`data/notes/` ya no se ignora en `.gitignore`, para que puedas versionar la nota base, sus derivados y los indices. El resto de `data/` sigue excluido.

## Pruebas

```powershell
python -m pytest -q
```

### Prueba monitoreada de PDF

Para validar el pipeline de documentos con trazas controladas puedes ejecutar:

```powershell
python aulaTEX/monitor_pdf_pipeline.py --pdf RUTA\A\tu-archivo.pdf
```

El script guarda un JSON de diagnóstico en `data/monitoring/pdf_pipeline_probe_*.json` con tiempos de extracción, intento de PDF directo sobre Responses API, validez del JSON devuelto y resumen final.

Si quieres una prueba sintética sin depender de un PDF externo:

```powershell
python aulaTEX/monitor_pdf_pipeline.py --from-text data/monitoring/probe_roma_input.txt
```

La logica rescatada del prototipo funcional quedo documentada en `docs/bedrock-prueba-migracion.md`; el pipeline funcional vive en `src/`.
