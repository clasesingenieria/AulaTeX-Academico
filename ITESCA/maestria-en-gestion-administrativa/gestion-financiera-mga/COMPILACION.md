# Compilacion - Gestion Financiera

Ejecutar desde la raiz del repositorio que contiene la carpeta ITESCA:

```powershell
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\maestria-en-gestion-administrativa\\gestion-financiera-mga\\reporte-gestion-financiera-mga.tex
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\maestria-en-gestion-administrativa\\gestion-financiera-mga\\presentacion-gestion-financiera-mga.tex
```

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del archivo .tex.
- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local de la materia vive en gestion-financiera.bib.
- Esta carpeta corresponde a la categoria tronco comun MGA.
- La identidad institucional se hereda desde ITESCA/_shared/ y usa los assets oficiales descargados en ITESCA/assets-itesca/web/.
