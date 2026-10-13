# Compilacion - Planeacion de estados financieros

Ejecutar siempre desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\planeacion-de-estados-financieros-lad\reporte-planeacion-de-estados-financieros.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\planeacion-de-estados-financieros-lad\reporte-planeacion-de-estados-financieros-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\planeacion-de-estados-financieros-lad\presentacion-planeacion-de-estados-financieros.tex
`

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del .tex.
- El \input{template} no se pasa como argumento. MiKTeX lo busca con TEXINPUTS, definido en .latexmkrc.
- En reportes, \input{template} debe resolver a ase/Plantilla-Informe/template.tex.
- El .bib no se pasa al script. Los reportes deben declarar \bibliography{planeacion-de-estados-financieros}.
- BibTeX busca $(@{Tetramestre=8; Name=Planeacion de estados financieros; Folder=planeacion-de-estados-financieros-lad; BibStem=planeacion-de-estados-financieros; ReportStem=planeacion-de-estados-financieros; PresentationStem=planeacion-de-estados-financieros; Code=PLA-EFI}.BibStem).bib con BIBINPUTS.
- El estilo 
atnumurl.bst se resuelve con BSTINPUTS.
- El PDF final queda en esta misma carpeta, junto al .tex.
- Los auxiliares quedan en .build/latex y .build/latex/aux.

## Checklist del .tex

- Mantener el formato del reporte de la materia al crear nuevas actividades.
- Toda clave citada debe existir en $(@{Tetramestre=8; Name=Planeacion de estados financieros; Folder=planeacion-de-estados-financieros-lad; BibStem=planeacion-de-estados-financieros; ReportStem=planeacion-de-estados-financieros; PresentationStem=planeacion-de-estados-financieros; Code=PLA-EFI}.BibStem).bib.
