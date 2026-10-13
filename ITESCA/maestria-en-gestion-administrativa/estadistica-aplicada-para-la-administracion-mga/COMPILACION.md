# Compilacion - Estadistica Aplicada para la Administracion

Ejecutar desde la raiz del repositorio que contiene la carpeta ITESCA:

```powershell
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\maestria-en-gestion-administrativa\\estadistica-aplicada-para-la-administracion-mga\\reporte-estadistica-aplicada-para-la-administracion-mga.tex
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\maestria-en-gestion-administrativa\\estadistica-aplicada-para-la-administracion-mga\\presentacion-estadistica-aplicada-para-la-administracion-mga.tex
```

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del archivo .tex.
- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local de la materia vive en estadistica-aplicada-para-la-administracion.bib.
- Esta carpeta corresponde a la categoria tronco comun MGA.
- La identidad institucional se hereda desde ITESCA/_shared/ y usa los assets oficiales descargados en ITESCA/assets-itesca/web/.
