# Compilacion - Desarrollo de las Organizaciones Sustentables

Ejecutar desde la raiz del repositorio que contiene la carpeta ITESCA:

```powershell
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\maestria-en-gestion-administrativa\\desarrollo-de-las-organizaciones-sustentables-mga\\reporte-desarrollo-de-las-organizaciones-sustentables-mga.tex
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\maestria-en-gestion-administrativa\\desarrollo-de-las-organizaciones-sustentables-mga\\presentacion-desarrollo-de-las-organizaciones-sustentables-mga.tex
```

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del archivo .tex.
- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local de la materia vive en desarrollo-de-las-organizaciones-sustentables.bib.
- Esta carpeta corresponde a la categoria tronco comun MGA.
- La identidad institucional se hereda desde ITESCA/_shared/ y usa los assets oficiales descargados en ITESCA/assets-itesca/web/.
