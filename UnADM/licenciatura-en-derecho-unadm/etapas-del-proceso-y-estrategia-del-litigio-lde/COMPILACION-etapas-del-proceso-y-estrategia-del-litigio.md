# Compilacion - Etapas del proceso y estrategia del litigio

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\etapas-del-proceso-y-estrategia-del-litigio-lde\reporte-etapas-del-proceso-y-estrategia-del-litigio.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\etapas-del-proceso-y-estrategia-del-litigio-lde\presentacion-etapas-del-proceso-y-estrategia-del-litigio.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Etapas del proceso y estrategia del litigio; Block=2; Credits=8; Type=Obligatoria; Slug=etapas-del-proceso-y-estrategia-del-litigio; Semester=5}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.