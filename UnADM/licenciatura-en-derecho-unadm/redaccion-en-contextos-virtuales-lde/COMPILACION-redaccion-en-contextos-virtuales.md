# Compilacion - Redaccion en Contextos Virtuales

Ejecutar siempre desde la raiz del proyecto:

```powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\redaccion-en-contextos-virtuales\reporte-redaccion-en-contextos-virtuales.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\redaccion-en-contextos-virtuales\reporte-redaccion-en-contextos-virtuales-Actividad-5.tex
```

Para otra actividad, cambia solo el nombre del `.tex`.

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del `.tex`.
- El `\input{template}` no se pasa como argumento. MiKTeX lo busca con `TEXINPUTS`, definido en `.latexmkrc`.
- En esta arquitectura, `\input{template}` debe resolver a `aulaTEX/base/Plantilla-Informe/template.tex`.
- El `.bib` tampoco se pasa al script. Cada `.tex` debe declarar `\bibliography{redaccion-en-contextos-virtuales}`.
- BibTeX busca `redaccion-en-contextos-virtuales.bib` con `BIBINPUTS`, definido en `.latexmkrc`.
- El estilo normal es `natnumurl.bst`; si un archivo declara `\bibliographystyle{apalike}`, esa actividad usa ese estilo de forma local.
- El PDF final queda en esta misma carpeta, junto al `.tex`.
- Los auxiliares quedan en `.build/latex` y `.build/latex/aux`.

## Checklist del `.tex`

- Debe cargar `\input{template}` antes de `\begin{document}` cuando use la plantilla institucional.
- Toda clave citada con `\citep`, `\citet` o `\cite` debe existir en `redaccion-en-contextos-virtuales.bib`.
- No usar rutas antiguas como `referencias/materias/...` dentro de `\bibliography`.
