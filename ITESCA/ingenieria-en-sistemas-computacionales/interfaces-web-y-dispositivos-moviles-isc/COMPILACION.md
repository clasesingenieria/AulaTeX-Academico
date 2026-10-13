# Compilacion - Interfaces Web y Dispositivos Moviles

Ejecutar desde la raiz del repositorio que contiene la carpeta ITESCA:

```powershell
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\ingenieria-en-sistemas-computacionales\\interfaces-web-y-dispositivos-moviles-isc\\reporte-interfaces-web-y-dispositivos-moviles-isc.tex
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\ingenieria-en-sistemas-computacionales\\interfaces-web-y-dispositivos-moviles-isc\\presentacion-interfaces-web-y-dispositivos-moviles-isc.tex
```

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del archivo .tex.
- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local de la materia vive en interfaces-web-y-dispositivos-moviles.bib.
- Esta carpeta corresponde a la categoria especialidad produccion multimedia ISC.
- La identidad institucional se hereda desde ITESCA/_shared/ y usa los assets oficiales descargados en ITESCA/assets-itesca/web/.
