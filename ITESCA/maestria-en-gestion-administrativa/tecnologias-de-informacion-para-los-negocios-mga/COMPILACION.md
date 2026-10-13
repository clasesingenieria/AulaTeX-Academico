# Compilacion - Tecnologias de Informacion para los Negocios

Ejecutar desde la raiz del repositorio que contiene la carpeta ITESCA:

```powershell
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\maestria-en-gestion-administrativa\\tecnologias-de-informacion-para-los-negocios-mga\\reporte-tecnologias-de-informacion-para-los-negocios-mga.tex
.\\aulaTEX\\latexmk-build.ps1 .\\ITESCA\\maestria-en-gestion-administrativa\\tecnologias-de-informacion-para-los-negocios-mga\\presentacion-tecnologias-de-informacion-para-los-negocios-mga.tex
```

## Contrato de compilacion

- El unico argumento obligatorio del script es la ruta del archivo .tex.
- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local de la materia vive en tecnologias-de-informacion-para-los-negocios.bib.
- Esta carpeta corresponde a la categoria LGAC gestion economica y financiera de las organizaciones.
- La identidad institucional se hereda desde ITESCA/_shared/ y usa los assets oficiales descargados en ITESCA/assets-itesca/web/.
