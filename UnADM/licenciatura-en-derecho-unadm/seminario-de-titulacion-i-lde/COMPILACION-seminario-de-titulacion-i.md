# Compilacion - Seminario de titulacion I

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\seminario-de-titulacion-i-lde\reporte-seminario-de-titulacion-i.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\seminario-de-titulacion-i-lde\presentacion-seminario-de-titulacion-i.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Seminario de titulacion I; Block=2; Credits=10; Type=Obligatoria seriada; Slug=seminario-de-titulacion-i; Semester=7}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.