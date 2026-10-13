# Compilacion - Diseno de Interfaz

Ejecutar desde la raiz del repositorio que contiene la carpeta ITESCA:

```powershell
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\ingenieria-en-sistemas-computacionales\\diseno-de-interfaz-isc\\reporte-diseno-de-interfaz-isc.tex
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\ingenieria-en-sistemas-computacionales\\diseno-de-interfaz-isc\\presentacion-diseno-de-interfaz-isc.tex
```

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del archivo .tex.
- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local de la materia vive en diseno-de-interfaz.bib.
- Esta carpeta corresponde a la categoria especialidad software ISC.
- La identidad institucional se hereda desde ITESCA/_shared/ y usa los assets oficiales descargados en ITESCA/assets-itesca/web/.
