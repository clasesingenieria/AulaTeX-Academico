# Compilacion - Etica y Moral Juridica

Ejecutar siempre desde la raiz del proyecto:

```powershell
.\aulaTEX\latexmk-build.ps1 .\UnADM\etica-y-moral-juridica\reporte-etica-y-moral-juridica.tex
.\aulaTEX\latexmk-build.ps1 .\UnADM\etica-y-moral-juridica\reporte-etica-y-moral-juridica-Actividad-5.tex
```

Para otra actividad, cambia solo el nombre del `.tex`.

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del `.tex`.
- El `\input{template}` no se pasa como argumento. MiKTeX lo busca con `TEXINPUTS`, definido en `.latexmkrc`.
- En esta arquitectura, `\input{template}` debe resolver a `aulaTEX/base/Plantilla-Informe/template.tex`.
- El `.bib` tampoco se pasa al script. Cada `.tex` debe declarar `\bibliography{etica-y-moral-juridica}`.
- BibTeX busca `etica-y-moral-juridica.bib` con `BIBINPUTS`, definido en `.latexmkrc`.
- El estilo `natnumurl.bst` se resuelve con `BSTINPUTS`.
- El PDF final queda en esta misma carpeta, junto al `.tex`.
- Los auxiliares quedan en `.build/latex` y `.build/latex/aux`.

## Checklist del `.tex`

- Debe cargar `\input{template}` antes de `\begin{document}`.
- Debe conservar el formato local de la materia: portada, resumen si aplica, indice y secciones institucionales.
- Toda clave citada con `\citep` o `\citet` debe existir en `etica-y-moral-juridica.bib`.
- No usar rutas antiguas como `referencias/materias/...` dentro de `\bibliography`.
