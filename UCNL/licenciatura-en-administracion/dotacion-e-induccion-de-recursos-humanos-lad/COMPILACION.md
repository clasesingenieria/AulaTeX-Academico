# Compilacion - Dotacion e induccion de recursos humanos

Ejecutar siempre desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\dotacion-e-induccion-de-recursos-humanos-lad\reporte-dotacion-e-induccion-de-recursos-humanos.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\dotacion-e-induccion-de-recursos-humanos-lad\reporte-dotacion-e-induccion-de-recursos-humanos-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\dotacion-e-induccion-de-recursos-humanos-lad\presentacion-dotacion-e-induccion-de-recursos-humanos.tex
`

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del .tex.
- El \input{template} no se pasa como argumento. MiKTeX lo busca con TEXINPUTS, definido en .latexmkrc.
- En reportes, \input{template} debe resolver a ase/Plantilla-Informe/template.tex.
- El .bib no se pasa al script. Los reportes deben declarar \bibliography{dotacion-e-induccion-de-recursos-humanos}.
- BibTeX busca $(@{Tetramestre=7; Name=Dotacion e induccion de recursos humanos; Folder=dotacion-e-induccion-de-recursos-humanos-lad; BibStem=dotacion-e-induccion-de-recursos-humanos; ReportStem=dotacion-e-induccion-de-recursos-humanos; PresentationStem=dotacion-e-induccion-de-recursos-humanos; Code=DOT-IRH}.BibStem).bib con BIBINPUTS.
- El estilo 
atnumurl.bst se resuelve con BSTINPUTS.
- El PDF final queda en esta misma carpeta, junto al .tex.
- Los auxiliares quedan en .build/latex y .build/latex/aux.

## Checklist del .tex

- Mantener el formato del reporte de la materia al crear nuevas actividades.
- Toda clave citada debe existir en $(@{Tetramestre=7; Name=Dotacion e induccion de recursos humanos; Folder=dotacion-e-induccion-de-recursos-humanos-lad; BibStem=dotacion-e-induccion-de-recursos-humanos; ReportStem=dotacion-e-induccion-de-recursos-humanos; PresentationStem=dotacion-e-induccion-de-recursos-humanos; Code=DOT-IRH}.BibStem).bib.
