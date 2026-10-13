# Compilacion - Electiva Semestre 8 Bloque 1

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\electiva-semestre-8-bloque-1-lde\reporte-electiva-semestre-8-bloque-1.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\electiva-semestre-8-bloque-1-lde\presentacion-electiva-semestre-8-bloque-1.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Electiva Semestre 8 Bloque 1; Block=1; Credits=; Type=Electiva; Slug=electiva-semestre-8-bloque-1; Semester=8}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.