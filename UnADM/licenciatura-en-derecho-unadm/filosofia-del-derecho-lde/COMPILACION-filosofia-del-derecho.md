# Compilacion - Filosofia del Derecho

Ejecutar siempre desde la raiz del proyecto:

```powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\filosofia-del-derecho\reporte-filosofia-del-derecho.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\filosofia-del-derecho\reporte-filosofia-del-derecho-Actividad-5.tex
```

Para otra actividad, cambia solo el nombre del `.tex`.

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del `.tex`.
- El `\input{template}` no se pasa como argumento. MiKTeX lo busca con `TEXINPUTS`, definido en `.latexmkrc`.
- En esta arquitectura, `\input{template}` debe resolver a `aulaTEX/base/Plantilla-Informe/template.tex`.
- El `.bib` tampoco se pasa al script. Cada `.tex` debe declarar `\bibliography{filosofia-del-derecho}`.
- BibTeX busca `filosofia-del-derecho.bib` con `BIBINPUTS`, definido en `.latexmkrc`.
- El estilo `natnumurl.bst` se resuelve con `BSTINPUTS`.
- El PDF final queda en esta misma carpeta, junto al `.tex`.
- Los auxiliares quedan en `.build/latex` y `.build/latex/aux`.

## Checklist del `.tex`

- Debe cargar `\input{template}` antes de `\begin{document}`.
- Debe conservar el formato local de la materia: Helvetica, `abstractd`, `\templatePortrait`, `\templatePagecfg`, `\templateIndex` y `\templateFinalcfg`.
- Toda clave citada con `\citep` o `\citet` debe existir en `filosofia-del-derecho.bib`.
- No usar rutas antiguas como `referencias/materias/...` dentro de `\bibliography`.
