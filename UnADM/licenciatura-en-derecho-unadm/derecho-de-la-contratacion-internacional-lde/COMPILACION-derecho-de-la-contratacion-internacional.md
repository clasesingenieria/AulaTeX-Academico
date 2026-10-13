# Compilacion - Derecho de la contratacion internacional

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derecho-de-la-contratacion-internacional-lde\reporte-derecho-de-la-contratacion-internacional.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derecho-de-la-contratacion-internacional-lde\presentacion-derecho-de-la-contratacion-internacional.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Derecho de la contratacion internacional; Block=2; Credits=8; Type=Obligatoria; Slug=derecho-de-la-contratacion-internacional; Semester=6}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.