# Seminario I: estado de documentos

Revisión estructural: 22 de septiembre de 2026. Preparación local no equivale a entrega en Moodle ni aprobación del anteproyecto.

| Documento | Fuente y producto | Alcance |
| --- | --- | --- |
| Encuadre de materia | [TEX](reporte-seminario-i-mga.tex), [PDF](reporte-seminario-i-mga.pdf) | Reporte base depurado, sin instrucciones de relleno ni citas de memoria editorial. |
| Actividad 1 | [TEX](reporte-seminario-i-Actividad-1.tex), [PDF](reporte-seminario-i-Actividad-1.pdf) | Contenido conservado; compilado con el núcleo local. |
| Actividad 2 | [TEX](reporte-seminario-i-Actividad-2.tex), [PDF](reporte-seminario-i-Actividad-2.pdf) | Contenido conservado; referencias manuales. |
| Actividad 3 | [TEX](reporte-seminario-i-Actividad-3.tex), [PDF](reporte-seminario-i-Actividad-3.pdf) | Contenido conservado; referencias manuales. |
| Actividad 4 | [TEX](reporte-seminario-i-Actividad-4.tex), [PDF](reporte-seminario-i-Actividad-4.pdf) | Infografía autocontenida. Se conserva su formato A4 horizontal, sin imponer formato de ensayo. |
| Actividad 6 | [TEX](reporte-seminario-i-Actividad-6.tex), [PDF](reporte-seminario-i-Actividad-6.pdf), [Word](entregas/Tarea6_DeLaCruzMunoz.docx) | PDF complementario; el Word requerido por la consigna se conserva sin cambios. |

## Estructura corregida

- [Núcleo local](template.tex) y [manifiesto de los módulos replicados](assets-seminario-i/plantilla/manifest.json): derivados del núcleo modular actualizado del repositorio, conservando autoría y licencia.
- [Base reutilizable de actividad](reporte-seminario-i-plantilla-actividad.tex): portada ITESCA, marca de agua, pie institucional, metadatos y contenido parametrizable. No compilar directamente.
- [Notas unificadas](referencias-seminario-i/notas-seminario-i/README.md): apuntes por unidad e histórico del reporte base anterior.
- [Referencias](referencias-seminario-i/README.md): materiales y guía breve oficial APA incorporados localmente.
- [Trece planeaciones normalizadas](planeaciones-seminario-i/INDICE-GENERADAS.md), sin reemplazar las fichas originales ni las planeaciones por unidad.
- [Inventario](estructura-aulatex.json) y [compilación](COMPILACION-seminario-i.md) actualizados.

## Límites académicos

Los datos personales o administrativos no aportados, la vigencia del calendario y la aprobación docente siguen pendientes; no se completan por inferencia. La guía APA descargada no es el manual completo ni sustituye automáticamente el recurso 2.1 del aula. Los originales históricos no se modifican para simular una revisión o entrega anterior.

## Verificación técnica del 22 de septiembre de 2026

- Reporte base y actividades 1, 2, 3 y 6 compilados con `latexmk` y pdfLaTeX usando el núcleo local. Registros finales sin errores, citas indefinidas ni cajas desbordadas.
- Portada del reporte base renderizada y revisada visualmente: logotipo oficial, marca de agua, pie institucional y datos académicos legibles.
- Inventario JSON y enlaces Markdown locales comprobados. Materiales y documentos sin exclusiones de Git.
- Réplica de 19 módulos verificada por SHA-256 contra el núcleo modular actualizado. La distribución antigua incompatible no se conserva como plantilla activa.
- No se recompilaron la infografía de la Actividad 4 ni la presentación, cuyos formatos autocontenidos no fueron modificados.