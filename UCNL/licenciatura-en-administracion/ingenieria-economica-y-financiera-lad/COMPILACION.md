# Compilacion - Ingenieria economica y financiera

Ejecutar siempre desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\ingenieria-economica-y-financiera-lad\reporte-ingenieria-economica-y-financiera.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\ingenieria-economica-y-financiera-lad\reporte-ingenieria-economica-y-financiera-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\ingenieria-economica-y-financiera-lad\presentacion-ingenieria-economica-y-financiera.tex
`

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del .tex.
- El \input{template} no se pasa como argumento. MiKTeX lo busca con TEXINPUTS, definido en .latexmkrc.
- En reportes, \input{template} debe resolver a ase/Plantilla-Informe/template.tex.
- El .bib no se pasa al script. Los reportes deben declarar \bibliography{ingenieria-economica-y-financiera}.
- BibTeX busca $(@{Tetramestre=7; Name=Ingenieria economica y financiera; Folder=ingenieria-economica-y-financiera-lad; BibStem=ingenieria-economica-y-financiera; ReportStem=ingenieria-economica-y-financiera; PresentationStem=ingenieria-economica-y-financiera; Code=ING-EFI}.BibStem).bib con BIBINPUTS.
- El estilo 
atnumurl.bst se resuelve con BSTINPUTS.
- El PDF final queda en esta misma carpeta, junto al .tex.
- Los auxiliares quedan en .build/latex y .build/latex/aux.

## Checklist del .tex

- Mantener el formato del reporte de la materia al crear nuevas actividades.
- Toda clave citada debe existir en $(@{Tetramestre=7; Name=Ingenieria economica y financiera; Folder=ingenieria-economica-y-financiera-lad; BibStem=ingenieria-economica-y-financiera; ReportStem=ingenieria-economica-y-financiera; PresentationStem=ingenieria-economica-y-financiera; Code=ING-EFI}.BibStem).bib.
