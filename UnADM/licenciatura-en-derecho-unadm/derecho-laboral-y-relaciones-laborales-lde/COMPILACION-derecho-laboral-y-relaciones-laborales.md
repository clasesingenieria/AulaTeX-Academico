# Compilacion - Derecho laboral y relaciones laborales

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derecho-laboral-y-relaciones-laborales-lde\reporte-derecho-laboral-y-relaciones-laborales.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derecho-laboral-y-relaciones-laborales-lde\presentacion-derecho-laboral-y-relaciones-laborales.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Derecho laboral y relaciones laborales; Block=1; Credits=8; Type=Obligatoria; Slug=derecho-laboral-y-relaciones-laborales; Semester=7}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.