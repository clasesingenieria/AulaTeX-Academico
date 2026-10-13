# Compilacion - Derecho fiscal y tributario

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derecho-fiscal-y-tributario-lde\reporte-derecho-fiscal-y-tributario.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derecho-fiscal-y-tributario-lde\presentacion-derecho-fiscal-y-tributario.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Derecho fiscal y tributario; Block=1; Credits=8; Type=Obligatoria; Slug=derecho-fiscal-y-tributario; Semester=6}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.