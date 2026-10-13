# Compilacion - Derechos de la persona y familia

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derechos-de-la-persona-y-familia-lde\reporte-derechos-de-la-persona-y-familia.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derechos-de-la-persona-y-familia-lde\presentacion-derechos-de-la-persona-y-familia.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Derechos de la persona y familia; Block=1; Credits=8; Type=Obligatoria seriada; Slug=derechos-de-la-persona-y-familia; Semester=3}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.