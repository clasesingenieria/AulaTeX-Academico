# Compilacion - Contabilidad Financiera

Ejecutar desde la raiz del repositorio que contiene la carpeta ITESCA:

```powershell
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\ingenieria-en-sistemas-computacionales\\contabilidad-financiera-isc\\reporte-contabilidad-financiera-isc.tex
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\ingenieria-en-sistemas-computacionales\\contabilidad-financiera-isc\\presentacion-contabilidad-financiera-isc.tex
```

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del archivo .tex.
- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local de la materia vive en contabilidad-financiera.bib.
- Esta carpeta corresponde a la categoria tronco comun ISC.
- La identidad institucional se hereda desde ITESCA/_shared/ y usa los assets oficiales descargados en ITESCA/assets-itesca/web/.
