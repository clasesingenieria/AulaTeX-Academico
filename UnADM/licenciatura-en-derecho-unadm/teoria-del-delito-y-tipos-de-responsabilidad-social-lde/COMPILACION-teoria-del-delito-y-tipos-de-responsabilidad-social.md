# Compilacion - Teoria del delito y tipos de responsabilidad social

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\teoria-del-delito-y-tipos-de-responsabilidad-social-lde\reporte-teoria-del-delito-y-tipos-de-responsabilidad-social.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\teoria-del-delito-y-tipos-de-responsabilidad-social-lde\presentacion-teoria-del-delito-y-tipos-de-responsabilidad-social.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Teoria del delito y tipos de responsabilidad social; Block=2; Credits=8; Type=Obligatoria; Slug=teoria-del-delito-y-tipos-de-responsabilidad-social; Semester=4}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.