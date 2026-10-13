# Compilacion - Modificacion del comportamiento organizacional

Ejecutar siempre desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\modificacion-del-comportamiento-organizacional-lad\reporte-modificacion-del-comportamiento-organizacional.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\modificacion-del-comportamiento-organizacional-lad\reporte-modificacion-del-comportamiento-organizacional-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\modificacion-del-comportamiento-organizacional-lad\presentacion-modificacion-del-comportamiento-organizacional.tex
`

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del .tex.
- El \input{template} no se pasa como argumento. MiKTeX lo busca con TEXINPUTS, definido en .latexmkrc.
- En reportes, \input{template} debe resolver a ase/Plantilla-Informe/template.tex.
- El .bib no se pasa al script. Los reportes deben declarar \bibliography{modificacion-del-comportamiento-organizacional}.
- BibTeX busca $(@{Tetramestre=8; Name=Modificacion del comportamiento organizacional; Folder=modificacion-del-comportamiento-organizacional-lad; BibStem=modificacion-del-comportamiento-organizacional; ReportStem=modificacion-del-comportamiento-organizacional; PresentationStem=modificacion-del-comportamiento-organizacional; Code=MOD-ORG}.BibStem).bib con BIBINPUTS.
- El estilo 
atnumurl.bst se resuelve con BSTINPUTS.
- El PDF final queda en esta misma carpeta, junto al .tex.
- Los auxiliares quedan en .build/latex y .build/latex/aux.

## Checklist del .tex

- Mantener el formato del reporte de la materia al crear nuevas actividades.
- Toda clave citada debe existir en $(@{Tetramestre=8; Name=Modificacion del comportamiento organizacional; Folder=modificacion-del-comportamiento-organizacional-lad; BibStem=modificacion-del-comportamiento-organizacional; ReportStem=modificacion-del-comportamiento-organizacional; PresentationStem=modificacion-del-comportamiento-organizacional; Code=MOD-ORG}.BibStem).bib.
