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

## Unidad 1: compilación y auditoría verificadas

Desde la raíz del repositorio:

```powershell
& .\.venv\Scripts\python.exe ITESCA/maestria-en-gestion-administrativa/estadistica-aplicada-para-la-administracion-mga/assets-estadistica-aplicada-para-la-administracion/validar_unidad_1.py --build --promote
```

El [validador de la unidad 1](assets-estadistica-aplicada-para-la-administracion/validar_unidad_1.py) usa TeX Live 2026, latexmk y XeLaTeX, con auxiliares exclusivos por actividad y búsquedas de plantilla acotadas. `--promote` copia los PDF verificados a la raíz de materia y a entregas, comprobando igualdad SHA-256. Sin opciones solo audita los PDF ya compilados. No interactúa con Moodle.

Los documentos heredan la plantilla de materia mediante sus extensiones locales. Las referencias visibles están controladas en `thebibliography` para APA 7 y tienen entradas correspondientes en la bibliografía activa; al modificar fuentes hay que mantener ambas representaciones concordantes. No se modificó la plantilla maestra ni su estilo bibliográfico global.

Arial 12 de TeX se representa como aproximadamente 11.955 puntos PDF (conversión de unidades pt/bp), no como una reducción de tamaño para ganar espacio. Se verificaron Arial regular, cursiva y negrita en todas las páginas de cuerpo de la investigación. La advertencia heredada de forma TS1 queda registrada, sin sustitución visible de Arial en ese cuerpo.

La portada usa una copia idéntica del fondo oficial con ruta corta en assets: el motor no pudo cargarlo desde la ruta larga de notas en Windows. El Word original, las imágenes extraídas y sus evidencias se conservan sin modificaciones.
