# Compilacion - Presupuestos con enfoque gerencial

Ejecutar siempre desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\presupuestos-con-enfoque-gerencial-lad\reporte-presupuestos-con-enfoque-gerencial.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\presupuestos-con-enfoque-gerencial-lad\reporte-presupuestos-con-enfoque-gerencial-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\presupuestos-con-enfoque-gerencial-lad\presentacion-presupuestos-con-enfoque-gerencial.tex
`

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del .tex.
- El \input{template} no se pasa como argumento. MiKTeX lo busca con TEXINPUTS, definido en .latexmkrc.
- En reportes, \input{template} debe resolver a ase/Plantilla-Informe/template.tex.
- El .bib no se pasa al script. Los reportes deben declarar \bibliography{presupuestos-con-enfoque-gerencial}.
- BibTeX busca $(@{Tetramestre=6; Name=Presupuestos con enfoque gerencial; Folder=presupuestos-con-enfoque-gerencial-lad; BibStem=presupuestos-con-enfoque-gerencial; ReportStem=presupuestos-con-enfoque-gerencial; PresentationStem=presupuestos-con-enfoque-gerencial; Code=PRE-GER}.BibStem).bib con BIBINPUTS.
- El estilo 
atnumurl.bst se resuelve con BSTINPUTS.
- El PDF final queda en esta misma carpeta, junto al .tex.
- Los auxiliares quedan en .build/latex y .build/latex/aux.

## Checklist del .tex

- Mantener el formato del reporte de la materia al crear nuevas actividades.
- Toda clave citada debe existir en $(@{Tetramestre=6; Name=Presupuestos con enfoque gerencial; Folder=presupuestos-con-enfoque-gerencial-lad; BibStem=presupuestos-con-enfoque-gerencial; ReportStem=presupuestos-con-enfoque-gerencial; PresentationStem=presupuestos-con-enfoque-gerencial; Code=PRE-GER}.BibStem).bib.
