# Compilacion - Seminario I

Ejecutar desde la raiz del repositorio que contiene la carpeta ITESCA:

```powershell
.\scripts\latexmk-build.ps1 .\ITESCA\maestria-en-gestion-administrativa\seminario-i-mga\reporte-seminario-i-mga.tex
.\scripts\latexmk-build.ps1 .\ITESCA\maestria-en-gestion-administrativa\seminario-i-mga\presentacion-seminario-i-mga.tex
```

## Contrato de compilacion

- El único argumento obligatorio del script es la ruta del archivo `.tex`.
- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografía local de la materia vive en `seminario-i.bib`.
- Esta carpeta corresponde a la categoría tronco común MGA.
- El reporte base utiliza `reporte-seminario-i-plantilla-actividad.tex`; los reportes 1, 2, 3 y 6 cargan la réplica local `template.tex`. La presentación y la infografía son autocontenidas. Los emblemas oficiales residen en `ITESCA/assets-itesca/`.
- El núcleo y los 19 módulos replicados viven dentro de la materia. Se compilan con pdfLaTeX mediante latexmk; no requieren `fontspec`. No compilar plantillas ni versiones históricas como entregables.
- No se debe asumir una dependencia de `ITESCA/_shared/` mientras esa carpeta no exista.
