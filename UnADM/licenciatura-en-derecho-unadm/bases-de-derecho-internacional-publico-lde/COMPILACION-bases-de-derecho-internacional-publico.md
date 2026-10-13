# Compilacion - Bases de derecho internacional publico

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\bases-de-derecho-internacional-publico-lde\reporte-bases-de-derecho-internacional-publico.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\bases-de-derecho-internacional-publico-lde\presentacion-bases-de-derecho-internacional-publico.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Bases de derecho internacional publico; Block=1; Credits=8; Type=Obligatoria; Slug=bases-de-derecho-internacional-publico; Semester=4}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.