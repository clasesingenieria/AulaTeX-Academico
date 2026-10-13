# Compilacion - Tecnica legislativa

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\tecnica-legislativa-lde\reporte-tecnica-legislativa.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\tecnica-legislativa-lde\presentacion-tecnica-legislativa.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Tecnica legislativa; Block=1; Credits=8; Type=Obligatoria; Slug=tecnica-legislativa; Semester=7}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.