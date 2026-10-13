# Extractor de conceptos e ideas

Esta carpeta aloja la adaptación local del proyecto funcional `proyecto_2_fichador_azure` dentro de `Template-Informe`.

## Propósito

Concentrar en un solo lugar:
- el código del motor de extracción;
- los scripts de ejecución;
- la configuración de rutas para este repositorio;
- la documentación mínima de uso;
- la integración con Azure OpenAI y Anthropic Foundry para tareas remotas del motor.

## Qué se importó

Se importó la base funcional del proyecto de referencia:
- `run.py`
- `pyproject.toml`
- `requirements*.txt`
- `src/fichador/`

Esto incluye:
- lectura documental de PDF, DOCX, TXT y MD;
- preprocesamiento y fragmentación;
- parser de planeación;
- extracción de conceptos;
- motores de búsqueda local y semántica;
- construcción de fichas;
- exportación a múltiples formatos.

## Estrategia de adaptación adoptada

La adaptación ya no depende exclusivamente de Azure OpenAI para embeddings. Dado que el flujo probado del usuario funciona correctamente con `AnthropicFoundry` sobre un endpoint `/anthropic/`, el extractor ahora soporta un modo híbrido:

- `Anthropic Foundry` para normalización, depuración y enriquecimiento de conceptos por chat.
- `TF-IDF` local para recuperación de citas textuales.

Esta decisión evita bloquear el extractor por dependencias de embeddings remotos y mantiene la regla central del proyecto: las citas textuales deben salir de los documentos fuente.

Además, el flujo de planeación se reforzó con dos mejoras:

- lectura de PDF más estructurada mediante PyMuPDF por bloques;
- reconstrucción asistida de la planeación con Anthropic Foundry cuando la confianza del parser local sea baja.

## Uso previsto dentro de `Template-Informe`

El flujo esperado es:

1. Tomar una planeación de una materia.
2. Tomar la carpeta de libros o fuentes base de esa materia.
3. Ejecutar el motor para extraer conceptos e ideas.
4. Guardar las fichas resultantes en una carpeta de salida reutilizable.
5. Usar esas fichas como apoyo para redactar actividades, construir esquemas y sostener retroalimentación editorial.

## Estructura actual

```text
aulaTEX/extractor-conceptos-ideas/
├─ extractor.ev.example
├─ .gitignore
├─ README.md
├─ Manual-extractor-conceptos-ideas.md
├─ pyproject.toml
├─ requirements.txt
├─ requirements-azure.txt
├─ requirements-tfhub.txt
├─ run.py
├─ config/
├─ input/
├─ output/
├─ runners/
└─ src/
   └─ fichador/
```

## Configuración local

1. Copiar `extractor.ev.example` a `extractor.ev`.
2. Colocar, según el proveedor que se vaya a usar:
   - endpoint de Azure OpenAI, key y deployment;
   - o endpoint de Anthropic Foundry, key y deployment de chat.
3. Ajustar rutas de:
   - planeación;
   - fuentes de la materia;
   - salida editorial.

## Salidas que genera la adaptación

Además de las fichas clásicas, esta adaptación ya deja previstas salidas auxiliares para el trabajo editorial:

- `resumen_planeacion.json`
- `resumen_planeacion_local.json`
- `resumen_planeacion_anthropic.json`
- `conceptos_detectados.json`
- `ideas_detectadas.json`
- `trazabilidad_fuentes.json`
- `fichas_conceptos.md`
- `fichas_conceptos.xlsx`
- `fichas_conceptos.csv`
- `fichas_conceptos.json`
- `fichas_conceptos.docx`

## Integración prevista

- `src/`: módulos del motor adaptado.
- `config/`: rutas, parámetros y convenciones.
- `runners/`: scripts de ejecución por materia o por semana.
- `output/`: salidas temporales o de prueba del motor.

La salida estable y reutilizable del proyecto no debe quedarse aquí, sino publicarse en una ruta de trabajo definida por materia y semana dentro del repositorio editorial, por ejemplo en `salidas/fichas/<materia>/<semana>/`.

## Ejecución recomendada

### Configurar entorno

```powershell
.\runners\configurar_entorno.ps1
```

### Probar rutas y detección de fuentes

```powershell
.\runners\probar_configuracion.ps1
```

### Probar conexión con Azure OpenAI

```powershell
.\runners\probar_azure.ps1
```

### Probar conexión con Anthropic Foundry

```powershell
.\runners\probar_anthropic.ps1
```

### Ejecutar con la configuración de `extractor.ev`

```powershell
.\runners\ejecutar_desde_env.ps1
```

### Ejecutar cualquier planeación de forma genérica

```powershell
.\runners\ejecutar_planeacion.ps1 -Fuentes "<ruta-fuentes>" -Planeacion "<ruta-planeacion>" -Salida "<ruta-salida>"
```

### Validar o ejecutar varias materias y semanas en secuencia

```powershell
.\runners\ejecutar_unadm_secuencial.ps1 -Materias filosofia-del-derecho,redaccion-en-contextos-virtuales,etica-y-moral-juridica -Semanas 2,4,5,7,8 -SoloValidar
```

El script localiza la planeación disponible para cada semana, reutiliza `ejecutar_planeacion.ps1`, procesa una ejecución después de otra y omite con aviso las semanas faltantes.

### Ejecutar ejemplo con `Ética y Moral jurídica` usando Anthropic Foundry

```powershell
.\runners\ejecutar_etica_s8_anthropic.ps1
```

## Tratamiento de PDF y planeaciones

El lector de PDF ya usa `PyMuPDF` como base. La adaptación actual ya no se limita a `page.get_text("text")`, sino que reconstruye la página a partir de bloques ordenados. Esto reduce la pérdida de estructura en listas, encabezados y separaciones lógicas.

Cuando la planeación sigue llegando con estructura pobre o campos faltantes, el extractor puede invocar Anthropic Foundry para producir una versión estructurada complementaria. El resultado final se compone de:

- `resumen_planeacion_local.json`: lectura del parser local;
- `resumen_planeacion_anthropic.json`: reconstrucción del modelo;
- `resumen_planeacion.json`: versión final reconciliada.

## Siguiente etapa

Con esta base ya importada, el siguiente paso no es volver a copiar el proyecto, sino adaptar su comportamiento a las necesidades editoriales específicas de `Template-Informe`: clasificación por utilidad de redacción, vinculación con `.bib`, generación de fichas por semana y soporte a flujos de retroalimentación.
