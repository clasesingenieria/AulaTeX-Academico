# Compilacion - Etica y responsabilidad social

Ejecutar siempre desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\etica-y-responsabilidad-social-lad\reporte-etica-y-responsabilidad-social.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\etica-y-responsabilidad-social-lad\reporte-etica-y-responsabilidad-social-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\etica-y-responsabilidad-social-lad\presentacion-etica-y-responsabilidad-social.tex
`

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del .tex.
- El \input{template} no se pasa como argumento. MiKTeX lo busca con TEXINPUTS, definido en .latexmkrc.
- En reportes, \input{template} debe resolver a ase/Plantilla-Informe/template.tex.
- El .bib no se pasa al script. Los reportes deben declarar \bibliography{etica-y-responsabilidad-social}.
- BibTeX busca $(@{Tetramestre=3; Name=Etica y responsabilidad social; Folder=etica-y-responsabilidad-social-lad; BibStem=etica-y-responsabilidad-social; ReportStem=etica-y-responsabilidad-social; PresentationStem=etica-y-responsabilidad-social; Code=ETI-RSO}.BibStem).bib con BIBINPUTS.
- El estilo 
atnumurl.bst se resuelve con BSTINPUTS.
- El PDF final queda en esta misma carpeta, junto al .tex.
- Los auxiliares quedan en .build/latex y .build/latex/aux.

## Checklist del .tex

- Mantener el formato del reporte de la materia al crear nuevas actividades.
- Toda clave citada debe existir en $(@{Tetramestre=3; Name=Etica y responsabilidad social; Folder=etica-y-responsabilidad-social-lad; BibStem=etica-y-responsabilidad-social; ReportStem=etica-y-responsabilidad-social; PresentationStem=etica-y-responsabilidad-social; Code=ETI-RSO}.BibStem).bib.
