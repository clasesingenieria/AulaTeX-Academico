# Compilacion - Administracion de emprendedores

Ejecutar siempre desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\administracion-de-emprendedores-lad\reporte-administracion-de-emprendedores.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\administracion-de-emprendedores-lad\reporte-administracion-de-emprendedores-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\administracion-de-emprendedores-lad\presentacion-administracion-de-emprendedores.tex
`

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del .tex.
- El \input{template} no se pasa como argumento. MiKTeX lo busca con TEXINPUTS, definido en .latexmkrc.
- En reportes, \input{template} debe resolver a ase/Plantilla-Informe/template.tex.
- El .bib no se pasa al script. Los reportes deben declarar \bibliography{administracion-de-emprendedores}.
- BibTeX busca $(@{Tetramestre=9; Name=Administracion de emprendedores; Folder=administracion-de-emprendedores-lad; BibStem=administracion-de-emprendedores; ReportStem=administracion-de-emprendedores; PresentationStem=administracion-de-emprendedores; Code=ADM-EMP}.BibStem).bib con BIBINPUTS.
- El estilo 
atnumurl.bst se resuelve con BSTINPUTS.
- El PDF final queda en esta misma carpeta, junto al .tex.
- Los auxiliares quedan en .build/latex y .build/latex/aux.

## Checklist del .tex

- Mantener el formato del reporte de la materia al crear nuevas actividades.
- Toda clave citada debe existir en $(@{Tetramestre=9; Name=Administracion de emprendedores; Folder=administracion-de-emprendedores-lad; BibStem=administracion-de-emprendedores; ReportStem=administracion-de-emprendedores; PresentationStem=administracion-de-emprendedores; Code=ADM-EMP}.BibStem).bib.
