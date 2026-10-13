# Compilacion - Estrategias de promocion

Ejecutar siempre desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\estrategias-de-promocion-lad\reporte-estrategias-de-promocion.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\estrategias-de-promocion-lad\reporte-estrategias-de-promocion-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\estrategias-de-promocion-lad\presentacion-estrategias-de-promocion.tex
`

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del .tex.
- El \input{template} no se pasa como argumento. MiKTeX lo busca con TEXINPUTS, definido en .latexmkrc.
- En reportes, \input{template} debe resolver a ase/Plantilla-Informe/template.tex.
- El .bib no se pasa al script. Los reportes deben declarar \bibliography{estrategias-de-promocion}.
- BibTeX busca $(@{Tetramestre=7; Name=Estrategias de promocion; Folder=estrategias-de-promocion-lad; BibStem=estrategias-de-promocion; ReportStem=estrategias-de-promocion; PresentationStem=estrategias-de-promocion; Code=EST-PRO}.BibStem).bib con BIBINPUTS.
- El estilo 
atnumurl.bst se resuelve con BSTINPUTS.
- El PDF final queda en esta misma carpeta, junto al .tex.
- Los auxiliares quedan en .build/latex y .build/latex/aux.

## Checklist del .tex

- Mantener el formato del reporte de la materia al crear nuevas actividades.
- Toda clave citada debe existir en $(@{Tetramestre=7; Name=Estrategias de promocion; Folder=estrategias-de-promocion-lad; BibStem=estrategias-de-promocion; ReportStem=estrategias-de-promocion; PresentationStem=estrategias-de-promocion; Code=EST-PRO}.BibStem).bib.
