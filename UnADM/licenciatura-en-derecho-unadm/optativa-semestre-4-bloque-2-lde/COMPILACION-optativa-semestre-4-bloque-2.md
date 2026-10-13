# Compilacion - Optativa Semestre 4 Bloque 2

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\optativa-semestre-4-bloque-2-lde\reporte-optativa-semestre-4-bloque-2.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\optativa-semestre-4-bloque-2-lde\presentacion-optativa-semestre-4-bloque-2.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Optativa Semestre 4 Bloque 2; Block=2; Credits=6; Type=Optativa; Slug=optativa-semestre-4-bloque-2; Semester=4}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.