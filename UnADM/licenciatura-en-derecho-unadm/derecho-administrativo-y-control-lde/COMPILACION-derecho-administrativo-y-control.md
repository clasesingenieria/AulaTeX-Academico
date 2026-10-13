# Compilacion - Derecho administrativo y control

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derecho-administrativo-y-control-lde\reporte-derecho-administrativo-y-control.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derecho-administrativo-y-control-lde\presentacion-derecho-administrativo-y-control.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Derecho administrativo y control; Block=1; Credits=8; Type=Obligatoria; Slug=derecho-administrativo-y-control; Semester=6}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.