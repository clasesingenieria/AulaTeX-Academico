# Compilacion - Integridad en el servicio publico

Ejecutar desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\integridad-en-el-servicio-publico-lde\reporte-integridad-en-el-servicio-publico.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\integridad-en-el-servicio-publico-lde\presentacion-integridad-en-el-servicio-publico.tex
`

## Contrato de compilacion

- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local vive en $(@{Name=Integridad en el servicio publico; Block=1; Credits=8; Type=Obligatoria; Slug=integridad-en-el-servicio-publico; Semester=1}.Slug).bib.
- La identidad institucional usa img/departamentos/UnADM.pdf.
- La malla curricular base esta en UnADM/assets-unadm/malla-curricular-derecho-unadm.pdf.