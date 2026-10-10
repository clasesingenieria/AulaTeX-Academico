# Antecedentes de los derechos humanos

Universidad Abierta y a Distancia de Mexico, Licenciatura en Derecho. Grupo 005; curso Moodle 3441; ciclo 2026-2, bloque 2, segun la planeacion del aula. No se infieren creditos ni ubicacion curricular adicionales.

## Estructura

- `referencias-antecedentes-de-los-derechos-humanos/`: documentos descargados del aula, bibliografia basica, normativa, planeacion y extracciones; `inventario-aula.json` enlaza cada descarga con su origen.
- [Planeacion S2](planeaciones-antecedentes-de-los-derechos-humanos/planeacion-S2.md): actividades 1 y 2, requisitos, calendario y riesgos.
- [Actividad local 1: foro diagnostico S1](reporte-antecedentes-de-los-derechos-humanos-Actividad-1.tex) y [PDF](reporte-antecedentes-de-los-derechos-humanos-Actividad-1.pdf).
- [Actividad local 2: resena critica S2](reporte-antecedentes-de-los-derechos-humanos-Actividad-2.tex) y [PDF](reporte-antecedentes-de-los-derechos-humanos-Actividad-2.pdf).
- [Participacion adicional del foro S2](participacion-foro-S2.md): texto conservado del borrador, no publicado. No es el foro diagnostico S1.

## Numeracion y fuentes

La numeracion de los archivos es LOCAL, acordada con el usuario: 1 = foro diagnostico anterior (semana 1), 2 = resena critica del video (semana 2). En Moodle la resena sigue denominada "Actividad 1: Resena Critica de Video", modulo 211993, y el foro adicional S2 "Actividad 2: Foro de participacion", modulo 211997. El numero local NO cambia el modulo al que debe entregarse ni la consigna oficial. El foro diagnostico S1 es el modulo 211991.

La resena cita directamente el video de Canal UNED; los tiempos de las citas corresponden al video, no al archivo SRT. La transcripcion de Subtitle Edit se conserva como apoyo interno, no como fuente bibliografica independiente. Los metadatos del video, el contraste con Unidad 1 y las ideas pertinentes del borrador previo se incorporaron al reporte; los borradores de resena MD/PDF reemplazados se retiraron. Las referencias docentes originales, los libros y las evidencias historicas no se eliminaron ni se renumeraron.

Compilacion desde la raiz del proyecto:

```powershell
.\scripts\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\antecedentes-de-los-derechos-humanos-lde\reporte-antecedentes-de-los-derechos-humanos-Actividad-1.tex
.\scripts\latexmk-build.ps1 .\UnADM\licenciatura-en-derecho-unadm\antecedentes-de-los-derechos-humanos-lde\reporte-antecedentes-de-los-derechos-humanos-Actividad-2.tex -lualatex
```

La resena requiere LuaLaTeX y Arial instalada en Windows; usa archivos de fuente de C:/Windows/Fonts. No ejecutar su compilacion con pdfLaTeX. Las evaluaciones historicas anteriores a esta reorganizacion conservan rutas antiguas y no certifican los documentos actuales.

## Estado

La resena local 2 fue reorganizada conforme al [contrato individual de la tecnica 37](planeaciones-antecedentes-de-los-derechos-humanos/CONTRATO-RESENA-VIDEO-S2.md), cotejado con el fasciculo 2 original (Resena, pp. 185-195). Contiene ficha audiovisual, titulo distinto al video, introduccion, cuerpo critico y recomendacion dentro de `resenabox`, con marco y contraste externos. PDF: cinco paginas, tres de contenido, siete referencias. Compilacion e inspeccion visual verificadas; no equivalen a calificacion docente ni acreditan observacion personal completa del video.

Las consignas de semana 2 fijan entrega ordinaria del 11 de octubre, 23:55, y extemporanea del 12 de octubre, 23:55. No asumir vigencia de la actividad 5 con fechas de julio/agosto ni usar autoevaluacion final como tarea actual. La resena integra tres fundamentaciones del video y contraste con Unidad 1; revisar personalmente las posturas y los fragmentos de transcripcion dudosos antes de entregar. No se hicieron intentos de examen ni se enviaron evidencias.

## Privacidad e integridad

La autenticacion se realiza mediante la boveda local de AulaTeX; nunca colocar usuario, contrasena o PIN en este directorio. Los documentos originales pueden contener datos de docentes: no redistribuir automaticamente. La asistencia de IA debe declararse y no sustituye la reflexion personal ni acredita conocimiento previo del estudiante.