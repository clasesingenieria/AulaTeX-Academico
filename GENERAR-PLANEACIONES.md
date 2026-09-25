# Generar planeaciones: contrato de organización 1.0

Vigente desde 2026-09-22. Implementación: `scripts/aulatex/planning_layout.py`; comando CLI `generar-planeaciones`.

## Alcance implementado

Normaliza modelos JSON revisados con `activity` o `activities`, conservando requisitos, fuentes y metadatos aportados. Produce un par Markdown/JSON por actividad y un índice. No redacta objetivos con un LLM, descarga archivos, entra a Moodle, resuelve tareas ni acredita aprobación institucional. La generación pedagógica de `realizar-planeacion` sigue siendo una especificación distinta. La GUI no incorpora todavía un botón de esta acción.

## Distribución obligatoria

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

## Garantías y límites

- Rechazar IDs inseguros, actividades vacías, duplicados y salidas que escapen por enlaces simbólicos.
- Verificar conflictos de todo el lote antes de escribir. Salidas idénticas se reutilizan; diferentes se conservan y se informa conflicto. No hay `--force`.
- Rechazar campos de credenciales y enlaces con tokens conocidos. Este control no sustituye una revisión de privacidad de insumos arbitrarios.
- Preservar todos los campos aportados; no completar fechas, porcentajes, autorizaciones o fuentes ausentes.
- Crear carpetas de soporte no significa haber realizado extracción, notas o investigación.
- No hacer `git add`, commit o push automáticamente. Versionable significa que Git puede incorporar el artefacto, no que ya esté confirmado.

## Uso

Desde la raíz del repositorio:

```powershell
.\scripts\aulatex.ps1 generar-planeaciones 'ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga' --source 'ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga/planeaciones-generadas/2026-II/revision-2026-09-20/planeacion-curso.json'
```

Los modelos históricos no cambian de autoridad por normalizarlos. Para actualizar el contenido, revisar primero el modelo aportado; una salida existente diferente bloquea la escritura en lugar de sobrescribirla.

Si la carpeta de planeaciones ya tiene un índice por unidades, usar `--index-name INDICE-GENERADAS.md` para conservar su `README.md`. La opción sólo admite un nombre Markdown sin directorios y no puede coincidir con una planeación. No omite la protección contra sobrescrituras.

Pruebas: `scripts/test_planning_layout.py` (unittest, sin LLM ni acceso de red).