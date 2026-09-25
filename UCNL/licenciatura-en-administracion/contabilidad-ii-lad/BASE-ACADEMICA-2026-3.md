# Base académica: Contabilidad II

Curso 20308, grupo G, periodo 2026-3. Consulta autenticada: 23/09/2026.

## Referencias

[6 originales del aula y catálogo revisado](referencias-contabilidad-ii/BASE-REFERENCIAS-2026-3.md). [Bibliografía verificada](referencias-verificadas-2026-3.bib). [Notas de revisión](referencias-contabilidad-ii/notas-contabilidad-ii/revision-base-2026-09-23.md).

Normatividad financiera, operaciones especiales, activos, pasivos, capital e instrumentos financieros.

Hay seis PDF T1, T2, T3, T4, T5 y T7. T4 tiene encabezados con caracteres alterados en su capa de texto: cotejar el PDF antes de citar. La referencia Wals (2000) aparece en eLibro, pero no se accedió al libro. Los resúmenes didácticos no sustituyen las NIF vigentes; no se verificó su exactitud normativa íntegra. H5P no ejecutado.

## Plantillas

- [Reporte](reporte-contabilidad-ii-plantilla-2026-3.tex)
- [Ficha de actividad](actividad-contabilidad-ii-plantilla-2026-3.tex)
- [Presentación](presentacion-contabilidad-ii-plantilla-2026-3.tex)
- [Configuración del grupo](config-materia-2026-3.tex)

Las plantillas usan las bases compartidas UCNL, Arial, interlineado 1.5 y APA con Biber. Es un formato editorial adaptable, no una norma oficial inferida. Matrícula y docente quedan por confirmar. No se copiaron identificadores de ITESCA ni UAS. Los textos entre corchetes deben completarse; no se reemplazan por mensajes de refuerzo ficticio.

## Compilación

Desde la raíz del repositorio:

```powershell
.\scripts\latexmk-build.ps1 UCNL/licenciatura-en-administracion/contabilidad-ii-lad/reporte-contabilidad-ii-plantilla-2026-3.tex -CleanMode none -xelatex
.\scripts\latexmk-build.ps1 UCNL/licenciatura-en-administracion/contabilidad-ii-lad/actividad-contabilidad-ii-plantilla-2026-3.tex -CleanMode none -xelatex
.\scripts\latexmk-build.ps1 UCNL/licenciatura-en-administracion/contabilidad-ii-lad/presentacion-contabilidad-ii-plantilla-2026-3.tex -CleanMode none -xelatex
```

Conservar originales, citas y límites. Esta base no resuelve actividades, ejecuta evaluaciones ni acredita envíos. Los archivos históricos se preservan; sus bibliografías de refuerzo no se incorporan a la nueva bibliografía. Versionable no significa publicado ni permiso de redistribución. [Manifiesto](base-academica-2026-3.json).
