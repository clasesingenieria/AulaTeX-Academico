# Compilacion - Plan de Negocios

Ejecutar desde la raiz del repositorio que contiene la carpeta ITESCA:

```powershell
.\\scripts\\latexmk-build.ps1 .\\ITESCA\\maestria-en-gestion-administrativa\\plan-de-negocios-mga\\reporte-plan-de-negocios-mga.tex
.\\scripts\\latexmk-build.ps1 .\\ITESCA\\maestria-en-gestion-administrativa\\plan-de-negocios-mga\\presentacion-plan-de-negocios-mga.tex
```

Los reportes de actividades usan la plantilla institucional local y deben compilarse con XeLaTeX:

```powershell
.\scripts\latexmk-build.ps1 .\ITESCA\maestria-en-gestion-administrativa\plan-de-negocios-mga\reporte-plan-de-negocios-Actividad-6534-Foro-Bienvenida.tex -xelatex
.\scripts\latexmk-build.ps1 .\ITESCA\maestria-en-gestion-administrativa\plan-de-negocios-mga\reporte-plan-de-negocios-Actividad-6545-Imagen-Empresa.tex -xelatex
```

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del archivo .tex.
- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local de la materia vive en plan-de-negocios.bib.
- Esta carpeta corresponde a la categoria LGAC gestion economica y financiera de las organizaciones.
- La identidad institucional se hereda desde ITESCA/_shared/ y usa los assets oficiales descargados en ITESCA/assets-itesca/web/.
- `pdflatex` no puede compilar documentos que cargan `fontspec`; usar `-xelatex` o `-lualatex` según su preámbulo.
