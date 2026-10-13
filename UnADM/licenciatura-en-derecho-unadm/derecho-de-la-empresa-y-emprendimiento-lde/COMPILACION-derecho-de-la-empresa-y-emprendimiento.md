# Compilacion - Derecho de la empresa y emprendimiento

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derecho-de-la-empresa-y-emprendimiento-lde\reporte-derecho-de-la-empresa-y-emprendimiento.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derecho-de-la-empresa-y-emprendimiento-lde\presentacion-derecho-de-la-empresa-y-emprendimiento.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Derecho de la empresa y emprendimiento; Block=2; Credits=8; Type=Obligatoria; Slug=derecho-de-la-empresa-y-emprendimiento; Semester=6}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.