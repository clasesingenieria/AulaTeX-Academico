# Compilacion - Estadistica Aplicada para la Administracion

Ejecutar desde la raiz del repositorio que contiene la carpeta ITESCA:

```powershell
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\maestria-en-gestion-administrativa\\estadistica-aplicada-para-la-administracion-mga\\reporte-estadistica-aplicada-para-la-administracion-mga.tex
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\maestria-en-gestion-administrativa\\estadistica-aplicada-para-la-administracion-mga\\presentacion-estadistica-aplicada-para-la-administracion-mga.tex
```

## Contrato de compilacion

## Punto de entrada activo

```powershell
.\aulaTEX\latexmk-build.ps1 .\ITESCA\maestria-en-gestion-administrativa\estadistica-aplicada-para-la-administracion-mga\reporte-estadistica-aplicada-para-la-administracion-encuadre.tex
```

Las actividades nuevas definen su contenido y cargan `reporte-estadistica-aplicada-para-la-administracion-plantilla-actividad.tex`, que hereda la maestra MGA. La bibliografia activa es `referencias-estadistica-verificadas.bib`. El reporte generico anterior se conserva como historico; no usar sus entradas editoriales como autoridad academica. No compilar la plantilla de actividad sola: requiere `estadisticacontenido`.

Arial 12, limites de paginas y cualquier formato especifico se verifican por actividad; Helvetica en la maestra no equivale a cumplir una exigencia literal de Arial.

- El unico argumento obligatorio del script es la ruta del archivo .tex.
- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local de la materia vive en estadistica-aplicada-para-la-administracion.bib.
- Esta carpeta corresponde a la categoria tronco comun MGA.
- La identidad institucional se hereda desde ITESCA/_shared/ y usa los assets oficiales descargados en ITESCA/assets-itesca/web/.
