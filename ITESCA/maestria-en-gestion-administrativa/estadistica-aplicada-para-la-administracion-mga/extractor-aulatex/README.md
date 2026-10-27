# Extracciones Conceptuales e Investigación por Actividad (`extractor-aulatex`)

Esta carpeta contiene las **22 corridas de extracción conceptual e investigación en tres tiempos** ejecutadas con **Amazon Nova Pro** (`AulaTeXLLMClient`, modelo `us.amazon.nova-pro-v1:0`) sobre el corpus bibliográfico focalizado de cada actividad (`Actividad 1` a `Actividad 22`).

El estado global y por etapa de los 22 trabajos se persiste en tiempo real en [`estado-trabajos-extraccion.json`](estado-trabajos-extraccion.json) y se visualiza mediante la GUI de extracción por actividad:

```powershell
.\.venv\Scripts\python.exe aulaTEX\extractor-conceptos-ideas\run.py --gui
```

## Carpetas de Extracción por Actividad

| Act. | Carpeta en `extractor-aulatex` | Espejo en `referencias-.../conceptos-...` | Espejo en `notas-.../actividad-XX` |
| :---: | :--- | :--- | :--- |
| 1 a 22 | `conceptos-estadistica-aplicada-para-la-administracion-actividad-<N>/` | `../referencias-estadistica-aplicada-para-la-administracion/conceptos-estadistica-aplicada-para-la-administracion/actividad-<NN>-<slug>/` | `../referencias-estadistica-aplicada-para-la-administracion/notas-estadistica-aplicada-para-la-administracion/actividad-<NN>-<slug>/conceptos/` y `/investigacion/` |

Cada carpeta de actividad contiene:
- `fichas_conceptos.md`, `fichas_conceptos.json`, `fichas_conceptos.csv`, `fichas_conceptos.xlsx`, `fichas_conceptos.docx`
- `conceptos_detectados.json`
- `ideas_detectadas.json`
- `trazabilidad_fuentes.json`
- `resumen_planeacion.json` y `resumen_planeacion_local.json`
- `investigacion_nova_pro.json` y `sintesis_tres_tiempos_nova_pro.md`
- `manifest.json`

Se preserva además la carpeta histórica [`conceptos-estadistica-unidad-1-nova`](conceptos-estadistica-unidad-1-nova/manifest.json).
