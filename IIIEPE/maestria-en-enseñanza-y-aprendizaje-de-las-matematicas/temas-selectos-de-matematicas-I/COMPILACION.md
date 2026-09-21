# Compilacion - Temas Selectos de Matematicas I

Ejecutar siempre desde la raiz del proyecto:

```powershell
$materia = '.\IIIEPE\maestria-en-enseñanza-y-aprendizaje-de-las-matematicas\temas-selectos-de-matematicas-I'

# Reporte general y actividades
.\scripts\latexmk-build.ps1 "$materia\reporte-temas-selectos-de-matematicas-I.tex"
.\scripts\latexmk-build.ps1 "$materia\reporte-temas-selectos-de-matematicas-I-Actividad-1.tex"
.\scripts\latexmk-build.ps1 "$materia\reporte-temas-selectos-de-matematicas-I-Actividad-2.tex"
.\scripts\latexmk-build.ps1 "$materia\reporte-temas-selectos-de-matematicas-I-Actividad-3.tex"

# Presentacion general y actividades
.\scripts\latexmk-build.ps1 "$materia\presentacion-temas-selectos-de-matematicas.tex"
.\scripts\latexmk-build.ps1 "$materia\presentacion-temas-selectos-de-matematicas-Actividad-1.tex"
.\scripts\latexmk-build.ps1 "$materia\presentacion-temas-selectos-de-matematicas-Actividad-2.tex"
.\scripts\latexmk-build.ps1 "$materia\presentacion-temas-selectos-de-matematicas-Actividad-3.tex"
```

Cada fuente `.tex` tiene un PDF homonimo en la misma carpeta. Compila solo
las fuentes cuyo PDF no exista o haya quedado anterior al `.tex`.

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del `.tex`.
- El `\input{template}` no se pasa como argumento. MiKTeX lo busca con `TEXINPUTS`, definido en `.latexmkrc`.
- En reportes, `\input{template}` debe resolver a `base/Plantilla-Informe/template.tex`.
- El `.bib` no se pasa al script. El reporte maestro declara `\bibliography{temas-selectos-de-matematicas-I,bibliografia-unadm}`.
- BibTeX busca `temas-selectos-de-matematicas-I.bib` en esta carpeta y `bibliografia-unadm.bib` en `UnADM/`.
- El estilo `natnumurl.bst` se resuelve con `BSTINPUTS`.
- El PDF final queda en esta misma carpeta, junto al `.tex`.
- Los auxiliares quedan en `.build/latex` y `.build/latex/aux`.

## Checklist del `.tex`

- Mantener el formato del reporte de la materia al crear nuevas actividades.
- Toda clave citada debe existir en `temas-selectos-de-matematicas-I.bib` o `UnADM/bibliografia-unadm.bib`.
- No declarar bibliografias inexistentes como `IIIEPE`.
