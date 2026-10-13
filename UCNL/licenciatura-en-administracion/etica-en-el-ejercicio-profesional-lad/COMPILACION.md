# Compilacion - Etica en el ejercicio profesional

Ejecutar siempre desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\etica-en-el-ejercicio-profesional-lad\reporte-etica-en-el-ejercicio-profesional.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\etica-en-el-ejercicio-profesional-lad\reporte-etica-en-el-ejercicio-profesional-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\etica-en-el-ejercicio-profesional-lad\presentacion-etica-en-el-ejercicio-profesional.tex
`

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del .tex.
- El \input{template} no se pasa como argumento. MiKTeX lo busca con TEXINPUTS, definido en .latexmkrc.
- En reportes, \input{template} debe resolver a ase/Plantilla-Informe/template.tex.
- El .bib no se pasa al script. Los reportes deben declarar \bibliography{etica-en-el-ejercicio-profesional}.
- BibTeX busca $(@{Tetramestre=7; Name=Etica en el ejercicio profesional; Folder=etica-en-el-ejercicio-profesional-lad; BibStem=etica-en-el-ejercicio-profesional; ReportStem=etica-en-el-ejercicio-profesional; PresentationStem=etica-en-el-ejercicio-profesional; Code=ETI-EEP}.BibStem).bib con BIBINPUTS.
- El estilo 
atnumurl.bst se resuelve con BSTINPUTS.
- El PDF final queda en esta misma carpeta, junto al .tex.
- Los auxiliares quedan en .build/latex y .build/latex/aux.

## Checklist del .tex

- Mantener el formato del reporte de la materia al crear nuevas actividades.
- Toda clave citada debe existir en $(@{Tetramestre=7; Name=Etica en el ejercicio profesional; Folder=etica-en-el-ejercicio-profesional-lad; BibStem=etica-en-el-ejercicio-profesional; ReportStem=etica-en-el-ejercicio-profesional; PresentationStem=etica-en-el-ejercicio-profesional; Code=ETI-EEP}.BibStem).bib.
