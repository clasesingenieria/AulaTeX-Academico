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

## Tarea 6: formato APA e índice automatizado (Linux)

Fuente principal: [reporte-seminario-i-Actividad-6.tex](reporte-seminario-i-Actividad-6.tex).
PDF final: [reporte-seminario-i-Actividad-6.pdf](reporte-seminario-i-Actividad-6.pdf).

Desde la raíz del repositorio:

```bash
bash scripts/latexmk-build.sh ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/reporte-seminario-i-Actividad-6.tex
```

La fuente utiliza la plantilla compartida y el [contenido de la actividad](tarea6/contenido-actividad-6.tex). Las dos imágenes están conservadas localmente y no es necesaria una descarga para compilar. Las cinco referencias se presentan manualmente, como en las actividades 2 y 3; el índice, las listas de objetos y las referencias cruzadas se resuelven con las pasadas de latexmk.

El [control de la versión LaTeX](tarea6/validar_latex.py) verifica errores, desbordamientos, entradas de índice, referencias cruzadas y separación de numeración entre preliminares y cuerpo. Véase el [resultado de validación](tarea6/validacion/verificacion-latex.json).

El [Word para Moodle](entregas/Tarea6_DeLaCruzMunoz.docx) se conserva sin cambios: el PDF institucional no sustituye el requisito de índice automatizado en Word.

## Contrato de compilación

- El único argumento obligatorio del script es la ruta del archivo `.tex`.
- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografía local de la materia vive en `seminario-i.bib`.
- La Actividad 2 es autocontenida para reproducir el formato APA solicitado; sus referencias se presentan manualmente.
- Cada PDF de actividad debe quedar junto a su `.tex`; `entregas/` conserva solo copias para el aula.
- Esta carpeta corresponde a la categoría tronco común MGA.
- Los puntos de entrada actuales contienen la configuración institucional y usan los recursos de `ITESCA/assets-itesca/`.
- No se debe asumir una dependencia de `ITESCA/_shared/` mientras esa carpeta no exista.
