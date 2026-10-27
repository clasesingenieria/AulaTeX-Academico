# Compilación - Estadística aplicada para la administración

## Revisión vigente: investigación con fichas (25/10/2026)

La Actividad 2 tiene dos salidas: informe completo de 13 páginas en la raíz y versión de entrega de cinco páginas. Ambas conservan portada oficial, resumen, tabla de contenido, declaración IA y tres tiempos. Las fichas usan el formato local `assets-estadistica-aplicada-para-la-administracion/investigacion-articulos/formato-fichas.tex`; la entrega carga `contenido-entrega.tex` mediante `version-entrega.tex`.

Para compilar, validar y promover ambas versiones desde la raíz del repositorio:

```powershell
& .\.venv\Scripts\python.exe ITESCA/maestria-en-gestion-administrativa/estadistica-aplicada-para-la-administracion-mga/assets-estadistica-aplicada-para-la-administracion/investigacion-articulos/compilar_validar_investigacion.py --build --promote
```

El helper comprueba las tres secciones principales, las tres fichas, portada preservada, Arial 12, interlineado 1.5, citas, límites de texto, cálculos, fuentes y conservación de los demás PDF. Genera `assets-estadistica-aplicada-para-la-administracion/validacion-investigacion-fichas-2026-10-25.json` y contactos de páginas. Después de inspeccionar todos los renders de esa compilación:

```powershell
& .\.venv\Scripts\python.exe ITESCA/maestria-en-gestion-administrativa/estadistica-aplicada-para-la-administracion-mga/assets-estadistica-aplicada-para-la-administracion/investigacion-articulos/compilar_validar_investigacion.py --visual-reviewed
```

Sin opciones solo valida las versiones actuales. Este helper no envía archivos a Moodle. Para esta revisión de Actividad 2 se usa el helper dedicado; los comandos de revisión global que siguen documentan las versiones anteriores. Véase [el registro de investigación](REVISION-INVESTIGACION-FICHAS-2026-10-25.md).

## Antecedente: resumen, índice y fusión del 25/10/2026

El informe nuevo requiere `estadisticaresumen` y el contenido de tres tiempos. La plantilla carga `assets-estadistica-aplicada-para-la-administracion/preliminares-estadistica.tex`: resumen, índice paginado y declaración IA al pie. Las investigaciones de cinco páginas emplean preliminares compactos propios con el mismo contenido y criterios, sin reducir Arial 12 ni el interlineado 1.5.

La fusión se compila primero, de manera independiente, desde `assets-estadistica-aplicada-para-la-administracion/poster/infografia-muestreo-fusionada.tex`, con XeLaTeX y el mismo `TEXINPUTS` acotado del proyecto; su salida activa se copia a esa carpeta antes de compilar Actividad 1. Los auxiliares de la lámina usan `.build/latex/estadistica-poster-fusion`. Los siete informes se compilan en sus directorios `estadistica-act1` a `act5`, `encuadre` y `mga`.

Después de terminar las compilaciones:

```powershell
& .\.venv\Scripts\python.exe ITESCA/maestria-en-gestion-administrativa/estadistica-aplicada-para-la-administracion-mga/assets-estadistica-aplicada-para-la-administracion/validar_revision_final.py --promote
```

Sin `--promote`, solo verifica los PDF actuales. La marca `--visual-reviewed` requiere inspeccionar todos los renders del manifiesto vigente. La promoción actualiza la raíz y las cuatro copias de entrega; conserva portadas y la lámina fusionada como objetos PDF. Ningún validador publica en Moodle. Los comandos y explicaciones del 24/10 que siguen son antecedentes; el alias `validar_estructura_reportes.py` apunta al validador actual.


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

Las actividades nuevas definen su contenido y cargan `reporte-estadistica-aplicada-para-la-administracion-plantilla-actividad.tex`, que hereda la maestra MGA. La bibliografía activa es `referencias-estadistica-verificadas.bib`. El reporte genérico anterior se conserva como histórico; no usar sus entradas editoriales como autoridad académica. No compilar la plantilla de actividad sola: requiere `estadisticacontenido` o las cuatro piezas estructuradas descritas más abajo.

Arial 12, limites de paginas y cualquier formato especifico se verifican por actividad; Helvetica en la maestra no equivale a cumplir una exigencia literal de Arial.

- El unico argumento obligatorio del script es la ruta del archivo .tex.
- El PDF final queda en la misma carpeta del archivo fuente.
- La bibliografia local de la materia vive en estadistica-aplicada-para-la-administracion.bib.
- Esta carpeta corresponde a la categoria tronco comun MGA.
- La identidad institucional se hereda de `ITESCA/maestria-en-gestion-administrativa/reporte-itesca-mga.tex`, que carga el núcleo `template` de `aulaTEX/base/Plantilla-Informe/`. Se usan los assets oficiales de ITESCA. La ruta histórica `ITESCA/_shared/` no existe en este checkout.

## Unidad 1: compilación y auditoría verificadas

Desde la raíz del repositorio:

```powershell
& .\.venv\Scripts\python.exe ITESCA/maestria-en-gestion-administrativa/estadistica-aplicada-para-la-administracion-mga/assets-estadistica-aplicada-para-la-administracion/validar_unidad_1.py --build --promote
```

El [validador de la unidad 1](assets-estadistica-aplicada-para-la-administracion/validar_unidad_1.py) usa TeX Live 2026, latexmk y XeLaTeX, con auxiliares exclusivos por actividad y búsquedas de plantilla acotadas. `--promote` copia los PDF verificados a la raíz de materia y a entregas, comprobando igualdad SHA-256. Sin opciones solo audita los PDF ya compilados. No interactúa con Moodle.

Los documentos heredan la plantilla de materia mediante sus extensiones locales. Las referencias visibles están controladas en `thebibliography` para APA 7 y tienen entradas correspondientes en la bibliografía activa; al modificar fuentes hay que mantener ambas representaciones concordantes. No se modificó la plantilla maestra ni su estilo bibliográfico global.

Arial 12 de TeX se representa como aproximadamente 11.955 puntos PDF (conversión de unidades pt/bp), no como una reducción de tamaño para ganar espacio. Se verificaron Arial regular, cursiva y negrita en todas las páginas de cuerpo de la investigación. La advertencia heredada de forma TS1 queda registrada, sin sustitución visible de Arial en ese cuerpo.

La portada usa una copia idéntica del fondo oficial con ruta corta en assets: el motor no pudo cargarlo desde la ruta larga de notas en Windows. El Word original, las imágenes extraídas y sus evidencias se conservan sin modificaciones.


## Informes de tres tiempos y preservación de portadas (24 de octubre de 2026)

La plantilla acepta contenido completo o las piezas `estadisticaintroduccion`,
`estadisticadesarrollotitulo`, `estadisticadesarrollo` y `estadisticaconclusiones`.
Este último modo genera introducción, un único desarrollo de título temático y
conclusiones. La síntesis interpretativa del desarrollo se integra en su prosa;
la postura final reúne razón y consecuencia. Conceptos, producto y lectura son
subsecciones del segundo tiempo.

Actividad 1 en la raíz es un informe conceptual con portada institucional y la
infografía completa incluida a tamaño A3. La lámina de entrega conserva sus bytes
originales; `validar_unidad_1.py --promote` actualiza el informe de raíz sin
sobrescribir `entregas-estadistica-aplicada-para-la-administracion/Actividad-1-Infografia.pdf`.
El PDF y el TEX originales de la lámina permanecen en assets. El compilador
reinserta la página original como objeto PDF para evitar incluso la mínima
transformación de centrado introducida por pdfpages.

Tras compilar Actividades 1, 3, 4, encuadre y genérico en sus directorios exclusivos
`.build/latex/estadistica-{act1,act3,act4,encuadre,mga}`, ejecutar desde la raíz:

```powershell
& .\.venv\Scripts\python.exe ITESCA/maestria-en-gestion-administrativa/estadistica-aplicada-para-la-administracion-mga/assets-estadistica-aplicada-para-la-administracion/validar_estructura_reportes.py
```

El consolidador comprueba tres secciones, log, citas y límites de texto, restaura
las portadas existentes como páginas PDF completas, verifica igualdad de su
render, guarda contactos visuales en `.build/qa-estadistica`, actualiza los PDF de
raíz y los de entregas 3/4, y escribe `validacion-estructura-reportes-2026-10-24.json`.
No efectúa envíos. El respaldo histórico del genérico conserva literalmente sus
metadatos originales de portada; las referencias y el cuerpo ya son disciplinares.

## Alternativa local de póster A3 (25 de octubre de 2026)

El [adaptador de póster](assets-estadistica-aplicada-para-la-administracion/poster/README.md) reutiliza el núcleo `template_poster` y aplica identidad ITESCA, Arial, A3 vertical y referencias autor-año mediante hooks locales. Compila como Beamer independiente; su PDF puede incluirse en el desarrollo del informe article.

```powershell
& .\.venv\Scripts\python.exe ITESCA/maestria-en-gestion-administrativa/estadistica-aplicada-para-la-administracion-mga/assets-estadistica-aplicada-para-la-administracion/poster/compilar_validar_poster.py --build
```

Este comando solo trabaja con la alternativa en `assets/.../poster/`, auxiliares en `.build/latex/estadistica-poster-local` y render en `.build/qa-estadistica-poster`. Comprueba los hashes protegidos, el núcleo cargado, A3, límites de texto, URLs completas y cálculo de muestra. No actualiza los informes canónicos ni los archivos de entrega. La marca de revisión visual exige inspeccionar el PNG de la compilación actual antes de utilizar `--visual-reviewed`.
