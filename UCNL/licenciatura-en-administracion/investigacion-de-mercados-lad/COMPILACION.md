# Compilacion - Investigacion de mercados

Ejecutar siempre desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\investigacion-de-mercados-lad\reporte-investigacion-de-mercados.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\investigacion-de-mercados-lad\reporte-investigacion-de-mercados-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\investigacion-de-mercados-lad\presentacion-investigacion-de-mercados.tex
`

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del .tex.
- El \input{template} no se pasa como argumento. MiKTeX lo busca con TEXINPUTS, definido en .latexmkrc.
- En reportes, \input{template} debe resolver a ase/Plantilla-Informe/template.tex.
- El .bib no se pasa al script. Los reportes deben declarar \bibliography{investigacion-de-mercados}.
- BibTeX busca $(@{Tetramestre=5; Name=Investigacion de mercados; Folder=investigacion-de-mercados-lad; BibStem=investigacion-de-mercados; ReportStem=investigacion-de-mercados; PresentationStem=investigacion-de-mercados; Code=INV-MER}.BibStem).bib con BIBINPUTS.
- El estilo 
atnumurl.bst se resuelve con BSTINPUTS.
- El PDF final queda en esta misma carpeta, junto al .tex.
- Los auxiliares quedan en .build/latex y .build/latex/aux.

## Checklist del .tex

- Mantener el formato del reporte de la materia al crear nuevas actividades.
- Toda clave citada debe existir en $(@{Tetramestre=5; Name=Investigacion de mercados; Folder=investigacion-de-mercados-lad; BibStem=investigacion-de-mercados; ReportStem=investigacion-de-mercados; PresentationStem=investigacion-de-mercados; Code=INV-MER}.BibStem).bib.
