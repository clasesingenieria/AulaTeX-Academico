# Compilacion - Estadistica descriptiva

Ejecutar siempre desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\estadistica-descriptiva-lad\reporte-estadistica-descriptiva.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\estadistica-descriptiva-lad\reporte-estadistica-descriptiva-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\estadistica-descriptiva-lad\presentacion-estadistica-descriptiva.tex
`

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del .tex.
- El \input{template} no se pasa como argumento. MiKTeX lo busca con TEXINPUTS, definido en .latexmkrc.
- En reportes, \input{template} debe resolver a ase/Plantilla-Informe/template.tex.
- El .bib no se pasa al script. Los reportes deben declarar \bibliography{estadistica-descriptiva}.
- BibTeX busca $(@{Tetramestre=6; Name=Estadistica descriptiva; Folder=estadistica-descriptiva-lad; BibStem=estadistica-descriptiva; ReportStem=estadistica-descriptiva; PresentationStem=estadistica-descriptiva; Code=EST-DES}.BibStem).bib con BIBINPUTS.
- El estilo 
atnumurl.bst se resuelve con BSTINPUTS.
- El PDF final queda en esta misma carpeta, junto al .tex.
- Los auxiliares quedan en .build/latex y .build/latex/aux.

## Checklist del .tex

- Mantener el formato del reporte de la materia al crear nuevas actividades.
- Toda clave citada debe existir en $(@{Tetramestre=6; Name=Estadistica descriptiva; Folder=estadistica-descriptiva-lad; BibStem=estadistica-descriptiva; ReportStem=estadistica-descriptiva; PresentationStem=estadistica-descriptiva; Code=EST-DES}.BibStem).bib.
