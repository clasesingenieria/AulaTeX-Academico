# Compilacion - Derecho de la responsabilidad civil y danos

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derecho-de-la-responsabilidad-civil-y-danos-lde\reporte-derecho-de-la-responsabilidad-civil-y-danos.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\derecho-de-la-responsabilidad-civil-y-danos-lde\presentacion-derecho-de-la-responsabilidad-civil-y-danos.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Derecho de la responsabilidad civil y danos; Block=1; Credits=8; Type=Obligatoria; Slug=derecho-de-la-responsabilidad-civil-y-danos; Semester=6}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.