# Compilacion - Propiedad industrial

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\propiedad-industrial-lde\reporte-propiedad-industrial.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\propiedad-industrial-lde\presentacion-propiedad-industrial.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Propiedad industrial; Block=1; Credits=8; Type=Obligatoria; Slug=propiedad-industrial; Semester=5}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.