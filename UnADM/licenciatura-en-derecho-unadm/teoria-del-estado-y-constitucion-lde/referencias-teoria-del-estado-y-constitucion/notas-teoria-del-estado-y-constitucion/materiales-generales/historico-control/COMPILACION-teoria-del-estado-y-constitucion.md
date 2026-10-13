# Compilacion - Teoria del Estado y Constitucion

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\teoria-del-estado-y-constitucion-lde\reporte-teoria-del-estado-y-constitucion.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\teoria-del-estado-y-constitucion-lde\presentacion-teoria-del-estado-y-constitucion.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Teoria del Estado y Constitucion; Block=2; Credits=8; Type=Obligatoria; Slug=teoria-del-estado-y-constitucion; Semester=2}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.