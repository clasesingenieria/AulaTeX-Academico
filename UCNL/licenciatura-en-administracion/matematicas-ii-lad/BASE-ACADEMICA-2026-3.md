# Base académica: Matemáticas II

Curso 20328, grupo C, periodo 2026-3. Consulta autenticada: 23/09/2026.

## Referencias

[0 originales del aula y catálogo revisado](referencias-matematicas-ii/BASE-REFERENCIAS-2026-3.md). [Bibliografía verificada](referencias-verificadas-2026-3.bib). [Notas de revisión](referencias-matematicas-ii/notas-matematicas-ii/revision-base-2026-09-23.md).

Temario disciplinar pendiente: la tabla publicada tiene los temas vacíos salvo exámenes.

La programación tiene fechas de enero a abril y temas vacíos. No se deduce si el curso corresponde a cálculo, álgebra o matemáticas financieras. OpenStax se incorpora sólo como repaso general provisional; requiere validación de pertinencia por el docente. Los cuestionarios no se abrieron.

## Plantillas

- [Reporte](reporte-matematicas-ii-plantilla-2026-3.tex)
- [Ficha de actividad](actividad-matematicas-ii-plantilla-2026-3.tex)
- [Presentación](presentacion-matematicas-ii-plantilla-2026-3.tex)
- [Configuración del grupo](config-materia-2026-3.tex)

Las plantillas usan las bases compartidas UCNL, Arial, interlineado 1.5 y APA con Biber. Es un formato editorial adaptable, no una norma oficial inferida. Matrícula y docente quedan por confirmar. No se copiaron identificadores de ITESCA ni UAS. Los textos entre corchetes deben completarse; no se reemplazan por mensajes de refuerzo ficticio.

## Compilación

Desde la raíz del repositorio:

```powershell
.\scripts\latexmk-build.ps1 UCNL/licenciatura-en-administracion/matematicas-ii-lad/reporte-matematicas-ii-plantilla-2026-3.tex -CleanMode none -xelatex
.\scripts\latexmk-build.ps1 UCNL/licenciatura-en-administracion/matematicas-ii-lad/actividad-matematicas-ii-plantilla-2026-3.tex -CleanMode none -xelatex
.\scripts\latexmk-build.ps1 UCNL/licenciatura-en-administracion/matematicas-ii-lad/presentacion-matematicas-ii-plantilla-2026-3.tex -CleanMode none -xelatex
```

Conservar originales, citas y límites. Esta base no resuelve actividades, ejecuta evaluaciones ni acredita envíos. Los archivos históricos se preservan; sus bibliografías de refuerzo no se incorporan a la nueva bibliografía. Versionable no significa publicado ni permiso de redistribución. [Manifiesto](base-academica-2026-3.json).
