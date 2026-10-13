# Compilacion - Costos I

Ejecutar siempre desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\costos-i-lad\reporte-costos-I.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\costos-i-lad\reporte-costos-I-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\costos-i-lad\presentacion-costos.tex
`

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del .tex.
- El \input{template} no se pasa como argumento. MiKTeX lo busca con TEXINPUTS, definido en .latexmkrc.
- En reportes, \input{template} debe resolver a ase/Plantilla-Informe/template.tex.
- El .bib no se pasa al script. Los reportes deben declarar \bibliography{costos-I}.
- BibTeX busca $(@{Tetramestre=4; Name=Costos I; Folder=costos-i-lad; BibStem=costos-I; ReportStem=costos-I; PresentationStem=costos; Code=COS-I}.BibStem).bib con BIBINPUTS.
- El estilo 
atnumurl.bst se resuelve con BSTINPUTS.
- El PDF final queda en esta misma carpeta, junto al .tex.
- Los auxiliares quedan en .build/latex y .build/latex/aux.

## Checklist del .tex

- Mantener el formato del reporte de la materia al crear nuevas actividades.
- Toda clave citada debe existir en $(@{Tetramestre=4; Name=Costos I; Folder=costos-i-lad; BibStem=costos-I; ReportStem=costos-I; PresentationStem=costos; Code=COS-I}.BibStem).bib.
