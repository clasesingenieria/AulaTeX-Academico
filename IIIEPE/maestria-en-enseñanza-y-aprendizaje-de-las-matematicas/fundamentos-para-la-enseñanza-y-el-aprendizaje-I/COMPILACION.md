# Compilacion - Fundamentos para la Enseñanza y el Aprendizaje I

Ejecutar siempre desde la raiz del proyecto:

```powershell
.\aulaTEX\latexmk-build.ps1 ".\IIIEPE\maestria-en-enseñanza-y-aprendizaje-de-las-matematicas\fundamentos-para-la-enseñanza-y-el-aprendizaje-I\reporte-fundamentos-para-la-enseñanza-y-el-aprendizaje-I.tex"
.\aulaTEX\latexmk-build.ps1 ".\IIIEPE\maestria-en-enseñanza-y-aprendizaje-de-las-matematicas\fundamentos-para-la-enseñanza-y-el-aprendizaje-I\reporte-fundamentos-para-la-enseñanza-y-el-aprendizaje-I-Actividad-1.tex"
.\aulaTEX\latexmk-build.ps1 ".\IIIEPE\maestria-en-enseñanza-y-aprendizaje-de-las-matematicas\fundamentos-para-la-enseñanza-y-el-aprendizaje-I\presentacion-fundamentos-para-la-enseñanza-y-el-aprendizaje.tex"
```

## Contrato de compilación

- El único argumento obligatorio del script es la ruta del `.tex`.
- El `\input{template}` no se pasa como argumento. MiKTeX lo busca con `TEXINPUTS`, definido en `.latexmkrc`.
- En reportes, `\input{template}` debe resolver a `aulaTEX/base/Plantilla-Informe/template.tex`.
- El `.bib` no se pasa al script. Los reportes deben declarar `\bibliography{fundamentos-para-la-enseñanza-y-el-aprendizaje-I}`.
- BibTeX busca `fundamentos-para-la-enseñanza-y-el-aprendizaje-I.bib` con `BIBINPUTS`.
- El estilo `natnumurl.bst` se resuelve con `BSTINPUTS`.
- El PDF final queda en esta misma carpeta, junto al `.tex`.
- Los auxiliares quedan en `.build/latex` y `.build/latex/aux-files`.
- La lectura de la Actividad 1 se conserva como `referencias/Scott-2015-El-futuro-del-aprendizaje-I.pdf`.

## Checklist del `.tex`

- Mantener el formato del reporte de la materia al crear nuevas actividades.
- Toda clave citada debe existir en `fundamentos-para-la-enseñanza-y-el-aprendizaje-I.bib`.
- El mapa conceptual debe contener jerarquía, palabras de enlace y relaciones significativas.
