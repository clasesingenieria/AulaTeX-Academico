# Compilacion - Seminario de titulacion III

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\seminario-de-titulacion-iii-lde\reporte-seminario-de-titulacion-iii.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\seminario-de-titulacion-iii-lde\presentacion-seminario-de-titulacion-iii.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Seminario de titulacion III; Block=2; Credits=10; Type=Obligatoria seriada; Slug=seminario-de-titulacion-iii; Semester=8}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.