# Compilacion - Derecho financiero y bancario

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derecho-financiero-y-bancario-lde\reporte-derecho-financiero-y-bancario.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derecho-financiero-y-bancario-lde\presentacion-derecho-financiero-y-bancario.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Derecho financiero y bancario; Block=2; Credits=8; Type=Obligatoria; Slug=derecho-financiero-y-bancario; Semester=3}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.