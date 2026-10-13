# Compilacion - Seguridad industrial y prevencion de riesgos laborales

Ejecutar siempre desde la raiz del proyecto:

`powershell
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\seguridad-industrial-y-prevencion-de-riesgos-laborales-lad\reporte-seguridad-industrial-y-prevencion-de-riesgos-laborales.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\seguridad-industrial-y-prevencion-de-riesgos-laborales-lad\reporte-seguridad-industrial-y-prevencion-de-riesgos-laborales-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\licenciatura-en-administracion\seguridad-industrial-y-prevencion-de-riesgos-laborales-lad\presentacion-seguridad-industrial-y-prevencion-de-riesgos-laborales.tex
`

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del .tex.
- El \input{template} no se pasa como argumento. MiKTeX lo busca con TEXINPUTS, definido en .latexmkrc.
- En reportes, \input{template} debe resolver a ase/Plantilla-Informe/template.tex.
- El .bib no se pasa al script. Los reportes deben declarar \bibliography{seguridad-industrial-y-prevencion-de-riesgos-laborales}.
- BibTeX busca $(@{Tetramestre=9; Name=Seguridad industrial y prevencion de riesgos laborales; Folder=seguridad-industrial-y-prevencion-de-riesgos-laborales-lad; BibStem=seguridad-industrial-y-prevencion-de-riesgos-laborales; ReportStem=seguridad-industrial-y-prevencion-de-riesgos-laborales; PresentationStem=seguridad-industrial-y-prevencion-de-riesgos-laborales; Code=SEG-RLA}.BibStem).bib con BIBINPUTS.
- El estilo 
atnumurl.bst se resuelve con BSTINPUTS.
- El PDF final queda en esta misma carpeta, junto al .tex.
- Los auxiliares quedan en .build/latex y .build/latex/aux.

## Checklist del .tex

- Mantener el formato del reporte de la materia al crear nuevas actividades.
- Toda clave citada debe existir en $(@{Tetramestre=9; Name=Seguridad industrial y prevencion de riesgos laborales; Folder=seguridad-industrial-y-prevencion-de-riesgos-laborales-lad; BibStem=seguridad-industrial-y-prevencion-de-riesgos-laborales; ReportStem=seguridad-industrial-y-prevencion-de-riesgos-laborales; PresentationStem=seguridad-industrial-y-prevencion-de-riesgos-laborales; Code=SEG-RLA}.BibStem).bib.
