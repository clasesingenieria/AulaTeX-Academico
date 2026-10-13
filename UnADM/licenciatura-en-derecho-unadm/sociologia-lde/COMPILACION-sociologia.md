# Compilacion - Sociologia

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\sociologia-lde\reporte-sociologia.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\sociologia-lde\presentacion-sociologia.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Sociologia; Block=1; Credits=8; Type=Obligatoria; Slug=sociologia; Semester=3}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.