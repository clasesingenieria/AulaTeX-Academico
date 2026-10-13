# Compilacion - Derecho civil

Ejecutar siempre desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\derecho-civil-lad\reporte-derecho-civil.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\derecho-civil-lad\reporte-derecho-civil-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\derecho-civil-lad\presentacion-derecho-civil.tex
`

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del .tex.
- El \input{template} no se pasa como argumento. MiKTeX lo busca con TEXINPUTS, definido en .latexmkrc.
- En reportes, \input{template} debe resolver a ase/Plantilla-Informe/template.tex.
- El .bib no se pasa al script. Los reportes deben declarar \bibliography{derecho-civil}.
- BibTeX busca $(@{Tetramestre=3; Name=Derecho civil; Folder=derecho-civil-lad; BibStem=derecho-civil; ReportStem=derecho-civil; PresentationStem=derecho-civil; Code=DER-CIV}.BibStem).bib con BIBINPUTS.
- El estilo 
atnumurl.bst se resuelve con BSTINPUTS.
- El PDF final queda en esta misma carpeta, junto al .tex.
- Los auxiliares quedan en .build/latex y .build/latex/aux.

## Checklist del .tex

- Mantener el formato del reporte de la materia al crear nuevas actividades.
- Toda clave citada debe existir en $(@{Tetramestre=3; Name=Derecho civil; Folder=derecho-civil-lad; BibStem=derecho-civil; ReportStem=derecho-civil; PresentationStem=derecho-civil; Code=DER-CIV}.BibStem).bib.
