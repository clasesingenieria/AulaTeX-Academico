# Compilacion - Derecho constitucional

Ejecutar siempre desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\derecho-constitucional-lad\reporte-derecho-constitucional.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\derecho-constitucional-lad\reporte-derecho-constitucional-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\derecho-constitucional-lad\presentacion-derecho-constitucional.tex
`

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del .tex.
- El \input{template} no se pasa como argumento. MiKTeX lo busca con TEXINPUTS, definido en .latexmkrc.
- En reportes, \input{template} debe resolver a ase/Plantilla-Informe/template.tex.
- El .bib no se pasa al script. Los reportes deben declarar \bibliography{derecho-constitucional}.
- BibTeX busca $(@{Tetramestre=2; Name=Derecho constitucional; Folder=derecho-constitucional-lad; BibStem=derecho-constitucional; ReportStem=derecho-constitucional; PresentationStem=derecho-constitucional; Code=DER-CON}.BibStem).bib con BIBINPUTS.
- El estilo 
atnumurl.bst se resuelve con BSTINPUTS.
- El PDF final queda en esta misma carpeta, junto al .tex.
- Los auxiliares quedan en .build/latex y .build/latex/aux.

## Checklist del .tex

- Mantener el formato del reporte de la materia al crear nuevas actividades.
- Toda clave citada debe existir en $(@{Tetramestre=2; Name=Derecho constitucional; Folder=derecho-constitucional-lad; BibStem=derecho-constitucional; ReportStem=derecho-constitucional; PresentationStem=derecho-constitucional; Code=DER-CON}.BibStem).bib.
