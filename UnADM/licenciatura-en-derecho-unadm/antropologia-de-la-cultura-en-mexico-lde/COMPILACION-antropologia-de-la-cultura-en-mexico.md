# Compilacion - Antropologia de la cultura en Mexico

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\antropologia-de-la-cultura-en-mexico-lde\reporte-antropologia-de-la-cultura-en-mexico.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\antropologia-de-la-cultura-en-mexico-lde\presentacion-antropologia-de-la-cultura-en-mexico.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Antropologia de la cultura en Mexico; Block=2; Credits=8; Type=Obligatoria; Slug=antropologia-de-la-cultura-en-mexico; Semester=4}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.