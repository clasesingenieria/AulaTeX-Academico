# Compilacion - Seminario de titulacion II

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\seminario-de-titulacion-ii-lde\reporte-seminario-de-titulacion-ii.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\seminario-de-titulacion-ii-lde\presentacion-seminario-de-titulacion-ii.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Seminario de titulacion II; Block=1; Credits=10; Type=Obligatoria seriada; Slug=seminario-de-titulacion-ii; Semester=8}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.