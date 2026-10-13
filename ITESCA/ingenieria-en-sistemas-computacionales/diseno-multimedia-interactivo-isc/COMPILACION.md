# Compilacion - Diseno Multimedia Interactivo

Ejecutar desde la raiz del repositorio que contiene la carpeta ITESCA:

```powershell
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\ingenieria-en-sistemas-computacionales\\diseno-multimedia-interactivo-isc\\reporte-diseno-multimedia-interactivo-isc.tex
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\ingenieria-en-sistemas-computacionales\\diseno-multimedia-interactivo-isc\\presentacion-diseno-multimedia-interactivo-isc.tex
```

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del archivo .tex.
- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local de la materia vive en diseno-multimedia-interactivo.bib.
- Esta carpeta corresponde a la categoria especialidad produccion multimedia ISC.
- La identidad institucional se hereda desde ITESCA/_shared/ y usa los assets oficiales descargados en ITESCA/assets-itesca/web/.
