# Compilacion - Principios Electricos y Aplicaciones Digitales

Ejecutar desde la raiz del repositorio que contiene la carpeta ITESCA:

```powershell
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\ingenieria-en-sistemas-computacionales\\principios-electricos-y-aplicaciones-digitales-isc\\reporte-principios-electricos-y-aplicaciones-digitales-isc.tex
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\ingenieria-en-sistemas-computacionales\\principios-electricos-y-aplicaciones-digitales-isc\\presentacion-principios-electricos-y-aplicaciones-digitales-isc.tex
```

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del archivo .tex.
- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local de la materia vive en principios-electricos-y-aplicaciones-digitales.bib.
- Esta carpeta corresponde a la categoria tronco comun ISC.
- La identidad institucional se hereda desde ITESCA/_shared/ y usa los assets oficiales descargados en ITESCA/assets-itesca/web/.
