# Compilación — Álgebra Lineal

Ejecutar desde la raíz del repositorio:

```powershell
.\aulaTEX\latexmk-build.ps1 .\UANL\ingeniero-agronomo\algebra-lineal\reporte-algebra-lineal-Actividad-1.tex
```

## Contrato

- Evidencia principal: `reporte-algebra-lineal-Actividad-1.tex`.
- Bibliografía: `algebra-lineal.bib`.
- Consigna: `planeaciones-algebra-lineal/consigna-Actividad-1.md`.
- Guía original: `planeaciones-algebra-lineal/originales-docentes/guia-Actividad-1-mapa-cognitivo.ppsx`.
- El PDF final se genera junto al archivo `.tex`.

## Segundo Laboratorio: Actividad 2

```powershell
.\aulaTEX\latexmk-build.ps1 .\UANL\ingeniero-agronomo\algebra-lineal\reporte-algebra-lineal-Actividad-2.tex -CleanMode none -gg
```

La opción `-gg` fuerza una reconstrucción del objetivo, descartando sus
auxiliares anteriores: el nombre Actividad 2 identificaba antes al PIA y sus
archivos auxiliares de BibLaTeX no corresponden al laboratorio. No borra los
originales docentes ni las notas conservadas.

Se conserva la fuente y el formato del laboratorio EJ25 existente. El cambio
de número y ubicación no constituye una revisión matemática ni una nueva
adaptación de su maquetación. Su DOCX y auxiliares previos se conservan bajo
las notas de la Actividad 2; el TEX y PDF canónicos están en la raíz.

## PIA: Actividad 3

Desde la raíz del repositorio:

```powershell
.\aulaTEX\latexmk-build.ps1 .\UANL\ingeniero-agronomo\algebra-lineal\reporte-algebra-lineal-Actividad-3.tex -CleanMode none
.\aulaTEX\latexmk-build.ps1 .\UANL\ingeniero-agronomo\algebra-lineal\reporte-algebra-lineal-Actividad-3-video.tex -CleanMode none
```

- La plantilla se resuelve mediante la configuración raíz de latexmk, como en la Actividad 1.
- El reporte usa BibLaTeX `style=apa`, Biber y la bibliografía local. El hook
	`file/config.tex/after` selecciona referencias `custom` antes de que la
	plantilla cargue paquetes; no se edita la configuración compartida.
- Los comandos `\citep` se conservan mediante la compatibilidad `natbib=true`
	de BibLaTeX; no se carga el paquete natbib en el reporte del PIA.
- La figura se genera con PGFPlots y `\usetikzlibrary{babel}`; no requiere Python.
- El reporte activa compresión PDF de objetos y flujos y conserva texto y ecuaciones vectoriales.
- Los PDF se generan junto a sus fuentes; los auxiliares quedan en `.build/latex/`.
- `-CleanMode none` evita que el compilador elimine auxiliares históricos de
	otros trabajos que ya estaban en la materia. No confundirlos con las entregas del PIA.
- La ficha del video se recompila después de completar la URL y los datos del equipo.

La bibliografía sigue APA 7; la portada y la maquetación conservan AulaTeX.
Esto no equivale a certificar cumplimiento total de formato APA ni aceptación
docente del editor LaTeX. Véanse los pendientes en las notas de integración.
