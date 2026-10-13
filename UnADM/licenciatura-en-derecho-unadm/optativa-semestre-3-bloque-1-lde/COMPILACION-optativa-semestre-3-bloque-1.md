# Compilacion - Optativa Semestre 3 Bloque 1

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\optativa-semestre-3-bloque-1-lde\reporte-optativa-semestre-3-bloque-1.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\optativa-semestre-3-bloque-1-lde\presentacion-optativa-semestre-3-bloque-1.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Optativa Semestre 3 Bloque 1; Block=1; Credits=6; Type=Optativa; Slug=optativa-semestre-3-bloque-1; Semester=3}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.