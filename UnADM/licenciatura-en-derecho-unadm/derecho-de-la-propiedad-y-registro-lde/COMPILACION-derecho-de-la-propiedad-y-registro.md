# Compilacion - Derecho de la propiedad y registro

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derecho-de-la-propiedad-y-registro-lde\reporte-derecho-de-la-propiedad-y-registro.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derecho-de-la-propiedad-y-registro-lde\presentacion-derecho-de-la-propiedad-y-registro.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Derecho de la propiedad y registro; Block=1; Credits=8; Type=Obligatoria; Slug=derecho-de-la-propiedad-y-registro; Semester=7}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.