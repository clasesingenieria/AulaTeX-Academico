# Compilacion - Electiva Semestre 7 Bloque 2

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\electiva-semestre-7-bloque-2-lde\reporte-electiva-semestre-7-bloque-2.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\electiva-semestre-7-bloque-2-lde\presentacion-electiva-semestre-7-bloque-2.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Electiva Semestre 7 Bloque 2; Block=2; Credits=; Type=Electiva; Slug=electiva-semestre-7-bloque-2; Semester=7}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.