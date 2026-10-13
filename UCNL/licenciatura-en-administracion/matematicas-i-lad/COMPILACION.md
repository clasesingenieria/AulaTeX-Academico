# Compilacion - Matematicas I

Ejecutar siempre desde la raiz del proyecto:

```powershell
.\aulaTEX\latexmk-build.ps1 .\UCNL\matematicas-I\reporte-matematicas-I.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\matematicas-I\reporte-matematicas-I-Actividad-1.tex
.\aulaTEX\latexmk-build.ps1 .\UCNL\matematicas-I\presentacion-matematicas.tex
```

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del `.tex`.
- El `\input{template}` no se pasa como argumento. MiKTeX lo busca con `TEXINPUTS`, definido en `.latexmkrc`.
- En reportes, `\input{template}` debe resolver a `aulaTEX/base/Plantilla-Informe/template.tex`.
- El `.bib` no se pasa al script. Los reportes deben declarar `\bibliography{matematicas-I}`.
- BibTeX busca `matematicas-I.bib` con `BIBINPUTS`.
- El estilo `natnumurl.bst` se resuelve con `BSTINPUTS`.
- El PDF final queda en esta misma carpeta, junto al `.tex`.
- Los auxiliares quedan en `.build/latex` y `.build/latex/aux`.

## Checklist del `.tex`

- Mantener el formato del reporte de la materia al crear nuevas actividades.
- Toda clave citada debe existir en `matematicas-I.bib`.
