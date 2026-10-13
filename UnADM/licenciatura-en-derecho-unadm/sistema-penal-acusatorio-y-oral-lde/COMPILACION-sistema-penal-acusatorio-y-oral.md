# Compilacion - Sistema penal acusatorio y oral

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\sistema-penal-acusatorio-y-oral-lde\reporte-sistema-penal-acusatorio-y-oral.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\sistema-penal-acusatorio-y-oral-lde\presentacion-sistema-penal-acusatorio-y-oral.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Sistema penal acusatorio y oral; Block=2; Credits=8; Type=Obligatoria; Slug=sistema-penal-acusatorio-y-oral; Semester=5}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.