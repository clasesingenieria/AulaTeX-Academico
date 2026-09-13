# Auditoría de integridad — reporte con producto foro 3.2

**Fecha:** 13 de septiembre de 2026. **Actividad local:** 7. **Curso:** GGFG02, Fundamentos de Gestión Administrativa, ITESCA/MGA.

## Dictamen

**Cumplimiento documental verificado del reporte con producto foro.** Se corrigieron discrepancias de versión, referencias y maquetación. El PDF final tiene **6 páginas** y contiene **tres TXT extraíbles**, correspondientes a la intervención inicial y a las dos respuestas.

**No se acredita el cierre integral de `realizar-actividad` como ejecución del motor ni la entrega académica.** La elaboración y la extracción fueron curadas manualmente; no se ejecutaron el ciclo multiagente de AulaTeX, su observador, su puntuación contractual ni la integración de memoria en SQLite. No se publicaron mensajes en Moodle. No se asigna un «100 %» ni una calificación académica.

## Contratos contrastados

Rutas relativas a la raíz del repositorio:

- [Contrato general y contrato de foro](../../../scripts/aulatex/activity_contract.py): tres actos, centralidad del producto, fuentes verificables, cita textual, referencias por caja, cierre y declaración de IA.
- [Patrón maduro de foro](../../../base/latex/adaptadas/materias/tecnicas-didacticas-aprendizaje/100tecnicas-patrones-reales.json): reporte contenedor, `forobox`, TXT y adjunto mediante `attachfile`.
- [Contrato de extracción](../../../scripts/aulatex/extractor_adapter.py): cinco artefactos nucleares.
- [Consigna y destinos verificados](foro-participacion-Actividad-7.md): identificar dos fases, justificar y recomendar, responder a dos compañeros.

Se aplica la identidad ITESCA; no se traslada la paleta UnADM ni se interpreta la clave histórica `foro_diagnostico` como una consigna distinta. La exigencia de «publicado» se mantiene como condición de entrega, no se finge mediante el título de una caja.

## Matriz de comprobación

| Requisito | Evidencia y resultado |
|---|---|
| Introducción, desarrollo temático único y conclusiones | Tres secciones numeradas; preparación conceptual, producto y lectura como subsecciones del desarrollo. |
| Preguntas y postura | Tres puntos de la consigna en lista; diagnóstico como fase vulnerable, revisión como fase destacada, razones y recomendaciones. |
| Producto foro | Tres cajas independientes, con saludo, argumentos, pregunta de cierre y firma. |
| Dos respuestas reales | Destinos d615 y d619, consultados el 12-09; presentación de ideas sin nombre fuera de las cajas. No son modelos para interlocutores ficticios. |
| Cita textual | Pasaje de Canós Darós y colaboradores cotejado con la quinta página del PDF original; se documenta que no hay folio impreso. |
| Bibliografía | Tres claves únicas y citadas en el contenedor; APA con BibLaTeX/Biber. Cada caja incorpora todas sus fuentes citadas, con sangría francesa. |
| TXT frente a cajas | Igualdad literal tras normalizar exclusivamente comandos tipográficos, numeración, espacios y raya de rango. No se descartan palabras ni diferencias de contenido. |
| Adjuntos | `pdfdetach` identifica tres archivos; extracción a directorio temporal y comparación byte a byte con cada TXT original. |
| Botones | Tres llamadas a `foroCopyButton`, cada una con su TXT correcto; adjuntos extraíbles. El botón no copia automáticamente al portapapeles ni garantiza soporte en todos los visores web. |
| Conclusión | Página 5, completa en una página; postura, razón, consecuencia y transferencia profesional. |
| Declaración de IA | Nota al pie con GitHub Copilot y propósito real; no atribuye revisión personal concluida al estudiante. |
| PDF | Seis páginas; texto seleccionable, sin citas indefinidas, claves visibles ni marcadores pendientes. |
| Compilación | `latexmk`/pdfLaTeX y Biber; auxiliares aislados, PDF final junto al TEX. Registro final sin advertencias ni desbordes. |
| Revisión visual | Revisadas las páginas renderizadas; eliminada una página casi vacía antes de las conclusiones. Cajas largas continúan entre páginas sin recortes. |
| Trazabilidad | Cinco JSON de curación manual, manifiesto de la actividad, memoria local y este dictamen. No se afirma ingestión automática del motor. |

## Discrepancias corregidas

1. El Markdown ofrecía mensajes antiguos sin la cita textual, referencias ni firmas actuales. Ahora es un índice a los TXT canónicos y conserva solo consigna, fuentes y destinos.
2. La memoria y el manifiesto declaraban inexistentes tres claves bibliográficas y tres TXT ya creados. Se actualizó el estado y se separaron validación técnica, revisión personal y publicación.
3. El reporte previo era un respaldo de mensajes, no un contenedor de tres actos. Se reorganizó y se añadieron las tres cajas y los adjuntos.
4. Se sustituyó `apalike` por BibLaTeX-APA/Biber. Se corrigieron abreviaturas narrativas, la institución de Canós y el número de artículo de López.
5. La primera maquetación dejaba una página con un párrafo, y la siguiente solo dos líneas. Se compactó el espaciado de las cajas y se sintetizó la interpretación; el reporte definitivo ocupa seis páginas.

## Alcance y límites de la automatización

- [Verificador local reproducible](verificar-integridad-actividad-7.pl): ejecutado satisfactoriamente. Comprueba estructura, citas, fuentes, cajas/TXT, JSON, frescura, adjuntos y cierre. No ejecuta LLM ni publica contenido.
- No se ejecutó `activity-observe`: el código inspeccionado puede escoger otra BIB por orden alfabético en esta carpeta y no resuelve la bibliografía a partir del TEX. Además, su memoria usa SQLite y nombres calculados, no garantiza ingerir este archivo manual de memoria.
- No se utilizó `foro-producto --apply`: el transformador tiene supuestos de otras actividades y su comprobador APA no reconoce adecuadamente una fecha legítimamente desconocida (`s. f.`) ni expande las macros locales de referencias. No se modificó el motor para esta tarea.
- No se fabricaron puntuaciones, consensos de agentes, registros de publicación ni resultados de revisión personal.
- La declaración de autoría y las posturas propuestas deben ser revisadas y asumidas o modificadas por el estudiante.

## Paquete final

- [Reporte fuente](reporte-fundamentos-de-gestion-administrativa-Actividad-7.tex).
- [Reporte PDF](reporte-fundamentos-de-gestion-administrativa-Actividad-7.pdf).
- [Participación inicial](foro-participacion-Actividad-7.txt).
- [Respuesta 1](foro-respuesta-1-Actividad-7.txt).
- [Respuesta 2](foro-respuesta-2-Actividad-7.txt).
- [Manifiesto](estructura-actividad-7.json) y [memoria](.memoria-aulatex/memoria-actividad-7.json).
- [Extracción curada](extractor-aulatex/conceptos-fundamentos-de-gestion-administrativa-actividad-7/resumen_planeacion.json).

### Huellas SHA-256 del cierre

- TEX: `fc873b39a75a40f4c1c3386c8d58649d723c1b83d5647a0332da043b438be3c3`.
- PDF: `348cadb31e1298e90cfb0fa0c97798e9ab08644bdb664adda4fba078889c235a`.

Las huellas identifican esta versión, no futuras recompilaciones; los metadatos temporales del PDF pueden cambiar su hash aunque el contenido no cambie.

## Pendientes que no deben marcarse como cumplidos

1. Revisión y aprobación de fuentes, postura y mensajes por el estudiante.
2. Confirmar aceptación extemporánea del foro, cuyo vencimiento registrado es 31-08-2026, 23:59. No se extrapola el cierre de otros foros.
3. Publicar la intervención inicial y las dos respuestas, y conservar sus enlaces y fechas reales.
4. Si se requiere certificación del flujo automático completo de AulaTeX, ejecutar y verificar por separado su integración de memoria, observación y ciclo; este dictamen no los sustituye.