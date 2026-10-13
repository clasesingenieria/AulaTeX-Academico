# Compilacion - Mecanismos alternativos de resolucion de conflictos

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\mecanismos-alternativos-de-resolucion-de-conflictos-lde\reporte-mecanismos-alternativos-de-resolucion-de-conflictos.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\mecanismos-alternativos-de-resolucion-de-conflictos-lde\presentacion-mecanismos-alternativos-de-resolucion-de-conflictos.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Mecanismos alternativos de resolucion de conflictos; Block=1; Credits=8; Type=Obligatoria; Slug=mecanismos-alternativos-de-resolucion-de-conflictos; Semester=5}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.