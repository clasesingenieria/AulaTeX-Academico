# Compilacion - Seminario I

Ejecutar desde la raiz del repositorio que contiene la carpeta ITESCA:

```powershell
.\\scripts\\latexmk-build.ps1 .\\ITESCA\\maestria-en-gestion-administrativa\\seminario-i-mga\\reporte-seminario-i-mga.tex
.\\scripts\\latexmk-build.ps1 .\\ITESCA\\maestria-en-gestion-administrativa\\seminario-i-mga\\presentacion-seminario-i-mga.tex
.\\scripts\\latexmk-build.ps1 .\\ITESCA\\maestria-en-gestion-administrativa\\seminario-i-mga\\reporte-seminario-i-Actividad-1.tex
.\\scripts\\latexmk-build.ps1 .\\ITESCA\\maestria-en-gestion-administrativa\\seminario-i-mga\\reporte-seminario-i-Actividad-2.tex
```

## Tarea 4: infografía (Linux)

Desde la raíz del repositorio:

```bash
bash scripts/latexmk-build.sh ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/reporte-seminario-i-Actividad-4.tex
```

Fuente autocontenida con TikZ y el logotipo institucional local. Las referencias se presentan manualmente con las ediciones verificadas. Produce dos páginas A4 horizontales: portada y una página de infografía. Control, semestre y fecha vigente requieren confirmación antes de entregar; consultar [la revisión](notas/unidad-2/revision-actividad-04.md).

## Contrato de compilación

- El único argumento obligatorio del script es la ruta del archivo `.tex`.
- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografía local de la materia vive en `seminario-i.bib`.
- La Actividad 2 es autocontenida para reproducir el formato APA solicitado; sus referencias se presentan manualmente.
- Cada PDF de actividad debe quedar junto a su `.tex`; `entregas/` conserva solo copias para el aula.
- Esta carpeta corresponde a la categoría tronco común MGA.
- Los puntos de entrada actuales contienen la configuración institucional y usan los recursos de `ITESCA/assets-itesca/`.
- No se debe asumir una dependencia de `ITESCA/_shared/` mientras esa carpeta no exista.
