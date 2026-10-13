# Compilacion - Derecho penal especial mexicano

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derecho-penal-especial-mexicano-lde\reporte-derecho-penal-especial-mexicano.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derecho-penal-especial-mexicano-lde\presentacion-derecho-penal-especial-mexicano.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Derecho penal especial mexicano; Block=2; Credits=8; Type=Obligatoria; Slug=derecho-penal-especial-mexicano; Semester=2}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.