# Compilacion - Historia del Derecho en Mexico

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\historia-del-derecho-en-mexico-lde\reporte-historia-del-derecho-en-mexico.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\historia-del-derecho-en-mexico-lde\presentacion-historia-del-derecho-en-mexico.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Historia del Derecho en Mexico; Block=1; Credits=8; Type=Obligatoria; Slug=historia-del-derecho-en-mexico; Semester=1}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.