# Compilacion - Direccion de marketing

Ejecutar siempre desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\direccion-de-marketing-lad\reporte-direccion-de-marketing.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\direccion-de-marketing-lad\reporte-direccion-de-marketing-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\direccion-de-marketing-lad\presentacion-direccion-de-marketing.tex
`

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del .tex.
- El \input{template} no se pasa como argumento. MiKTeX lo busca con TEXINPUTS, definido en .latexmkrc.
- En reportes, \input{template} debe resolver a ase/Plantilla-Informe/template.tex.
- El .bib no se pasa al script. Los reportes deben declarar \bibliography{direccion-de-marketing}.
- BibTeX busca $(@{Tetramestre=7; Name=Direccion de marketing; Folder=direccion-de-marketing-lad; BibStem=direccion-de-marketing; ReportStem=direccion-de-marketing; PresentationStem=direccion-de-marketing; Code=DIR-MKT}.BibStem).bib con BIBINPUTS.
- El estilo 
atnumurl.bst se resuelve con BSTINPUTS.
- El PDF final queda en esta misma carpeta, junto al .tex.
- Los auxiliares quedan en .build/latex y .build/latex/aux.

## Checklist del .tex

- Mantener el formato del reporte de la materia al crear nuevas actividades.
- Toda clave citada debe existir en $(@{Tetramestre=7; Name=Direccion de marketing; Folder=direccion-de-marketing-lad; BibStem=direccion-de-marketing; ReportStem=direccion-de-marketing; PresentationStem=direccion-de-marketing; Code=DIR-MKT}.BibStem).bib.
