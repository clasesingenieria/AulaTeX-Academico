# Compilacion - Software aplicado a la ingenieria financiera

Ejecutar siempre desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\software-aplicado-a-la-ingenieria-financiera-lad\reporte-software-aplicado-a-la-ingenieria-financiera.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\software-aplicado-a-la-ingenieria-financiera-lad\reporte-software-aplicado-a-la-ingenieria-financiera-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\software-aplicado-a-la-ingenieria-financiera-lad\presentacion-software-aplicado-a-la-ingenieria-financiera.tex
`

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del .tex.
- El \input{template} no se pasa como argumento. MiKTeX lo busca con TEXINPUTS, definido en .latexmkrc.
- En reportes, \input{template} debe resolver a ase/Plantilla-Informe/template.tex.
- El .bib no se pasa al script. Los reportes deben declarar \bibliography{software-aplicado-a-la-ingenieria-financiera}.
- BibTeX busca $(@{Tetramestre=8; Name=Software aplicado a la ingenieria financiera; Folder=software-aplicado-a-la-ingenieria-financiera-lad; BibStem=software-aplicado-a-la-ingenieria-financiera; ReportStem=software-aplicado-a-la-ingenieria-financiera; PresentationStem=software-aplicado-a-la-ingenieria-financiera; Code=SOF-IIF}.BibStem).bib con BIBINPUTS.
- El estilo 
atnumurl.bst se resuelve con BSTINPUTS.
- El PDF final queda en esta misma carpeta, junto al .tex.
- Los auxiliares quedan en .build/latex y .build/latex/aux.

## Checklist del .tex

- Mantener el formato del reporte de la materia al crear nuevas actividades.
- Toda clave citada debe existir en $(@{Tetramestre=8; Name=Software aplicado a la ingenieria financiera; Folder=software-aplicado-a-la-ingenieria-financiera-lad; BibStem=software-aplicado-a-la-ingenieria-financiera; ReportStem=software-aplicado-a-la-ingenieria-financiera; PresentationStem=software-aplicado-a-la-ingenieria-financiera; Code=SOF-IIF}.BibStem).bib.
