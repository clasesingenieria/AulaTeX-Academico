# Compilacion - Taller de Base de Datos

Ejecutar desde la raiz del repositorio que contiene la carpeta ITESCA:

```powershell
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\ingenieria-en-sistemas-computacionales\\taller-de-base-de-datos-isc\\reporte-taller-de-base-de-datos-isc.tex
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\ingenieria-en-sistemas-computacionales\\taller-de-base-de-datos-isc\\presentacion-taller-de-base-de-datos-isc.tex
```

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del archivo .tex.
- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local de la materia vive en taller-de-base-de-datos.bib.
- Esta carpeta corresponde a la categoria tronco comun ISC.
- La identidad institucional se hereda desde ITESCA/_shared/ y usa los assets oficiales descargados en ITESCA/assets-itesca/web/.
