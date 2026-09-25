# Base académica: Administración II

Curso 20297, grupo D, periodo 2026-3. Consulta autenticada: 23/09/2026.

## Referencias

[8 originales del aula y catálogo revisado](referencias-administracion-ii/BASE-REFERENCIAS-2026-3.md). [Bibliografía verificada](referencias-verificadas-2026-3.bib). [Notas de revisión](referencias-administracion-ii/notas-administracion-ii/revision-base-2026-09-23.md).

Integración de personal, evaluación del desempeño, cambio, motivación, liderazgo, equipos, comunicación y control.

La programación contiene fechas de febrero a abril de 2026 que no se adoptan como calendario vigente de 2026-3. Las presentaciones visibles abarcan capítulos 11 a 16; el libro contiene capítulos posteriores. No se ejecutó SCORM.

## Plantillas

- [Reporte](reporte-administracion-ii-plantilla-2026-3.tex)
- [Ficha de actividad](actividad-administracion-ii-plantilla-2026-3.tex)
- [Presentación](presentacion-administracion-ii-plantilla-2026-3.tex)
- [Configuración del grupo](config-materia-2026-3.tex)

Las plantillas usan las bases compartidas UCNL, Arial, interlineado 1.5 y APA con Biber. Es un formato editorial adaptable, no una norma oficial inferida. Matrícula y docente quedan por confirmar. No se copiaron identificadores de ITESCA ni UAS. Los textos entre corchetes deben completarse; no se reemplazan por mensajes de refuerzo ficticio.

## Compilación

Desde la raíz del repositorio:

```powershell
.\scripts\latexmk-build.ps1 UCNL/licenciatura-en-administracion/administracion-ii-lad/reporte-administracion-ii-plantilla-2026-3.tex -CleanMode none -xelatex
.\scripts\latexmk-build.ps1 UCNL/licenciatura-en-administracion/administracion-ii-lad/actividad-administracion-ii-plantilla-2026-3.tex -CleanMode none -xelatex
.\scripts\latexmk-build.ps1 UCNL/licenciatura-en-administracion/administracion-ii-lad/presentacion-administracion-ii-plantilla-2026-3.tex -CleanMode none -xelatex
```

Conservar originales, citas y límites. Esta base no resuelve actividades, ejecuta evaluaciones ni acredita envíos. Los archivos históricos se preservan; sus bibliografías de refuerzo no se incorporan a la nueva bibliografía. Versionable no significa publicado ni permiso de redistribución. [Manifiesto](base-academica-2026-3.json).
