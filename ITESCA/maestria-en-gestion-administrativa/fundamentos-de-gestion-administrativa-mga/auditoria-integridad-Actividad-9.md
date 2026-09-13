# Auditoría de integridad y contratos — Actividad 9 / Foro 4.2

**Fecha:** 13 de septiembre de 2026. **Dictamen: integridad documental verificada después de corregir divergencias; cumplimiento integral de `realizar-actividad` NO aprobado.** Esta revisión sustituye cualquier interpretación de «sin avisos APA» como certificación completa del flujo.

## 1. Resultados separados

| Dimensión | Resultado | Evidencia y límite |
|---|---|---|
| Integridad PDF/TXT | **3 de 3 verificadas** | Comparación del texto realmente extraído de cada caja frente al TXT; se normalizan espacios, puntuación, mayúsculas y tipografía, conservando letras, cifras y orden. No es identidad tipográfica ni certificación de significado. |
| Adjuntos del PDF | **3 de 3 idénticos byte a byte** | Extracción a directorio temporal y comparación con los TXT canónicos. |
| Compilación | **Correcta** | PDF de siete páginas recompilado; registro final sin errores, advertencias, citas indefinidas ni desbordamientos. |
| Formato de foro | **Estructura local satisfecha** | Tres actos; tres preguntas respondidas; tres cajas; referencias propias y firmas; dos réplicas contextualizadas; cierre interrogativo; conclusión en página nueva. |
| Verificador APA específico | **Sin avisos** | `_check_forum_apa_citation` comprueba patrones, presencia de referencias y cantidades; no certifica APA completa ni compara textos. |
| Observador completo | **NO aprobado: 77,25/100** | `passed=false`; siguiente acción `run-extractor`. No es una calificación académica. |
| Subcontrato heurístico | **80/100; `passed=true`** | Aprueba por umbral aunque fallan objetivo detectable, trazabilidad y mínimo de conceptos extraídos. Su aprobación no anula el fallo del observador completo. |
| Video y validación personal | **No acreditados** | Las fuentes alternativas no sustituyen el video obligatorio ni la revisión del estudiante. |
| Publicación | **No realizada durante este trabajo** | Cierre previamente verificado en Moodle; no se volvió a probar publicación en esta auditoría. No se modificaron permisos ni se marcó finalización. |

Evaluación ejecutada y persistida:
- [Estado observado](auditoria-actividad-9/observer/20260913-175006-activity-09-observer/estado-agente.json).
- [Evaluación completa](auditoria-actividad-9/observer/20260913-175006-activity-09-observer/evaluacion.json).
- [Acciones recomendadas](auditoria-actividad-9/observer/20260913-175006-activity-09-observer/acciones-recomendadas.md).

Se ejecutó `ActivityObserver.observe` con `compile_check=False`: la compilación se verificó por separado con `latexmk`, `pdflatex` y BibTeX. No se afirma haber ejecutado el agente generador ni todas las fases del flujo. Las lecturas de páginas del foro pertenecen a la verificación previa documentada; esta auditoría trabajó con los artefactos locales.

## 2. Hallazgos corregidos

1. **Divergencia de contenido:** la caja situaba la cita de Sánchez al final de la frase y el TXT al inicio. Se unificó la cita narrativa. El TXT añadía «Hallazgos principales» en la referencia del WEF sin que figurara en la caja; se retiró esa diferencia.
2. **Orden de las citas:** las obras de OpenStax aparecían como `2019b,a` en PDF y `2019b, 2019a` en TXT. Se ordenaron como `2019a, b`, con la agrupación que renderiza `natbib`.
3. **Uniformidad de títulos:** se armonizó el uso de mayúsculas de las referencias del aporte y su adjunto.
4. **Versión ambigua:** [la variante de réplicas en Markdown](foro-replicas-personalizadas-Actividad-9.md) contenía argumentos distintos y todavía se ofrecía para publicar. Se marcó expresamente como histórica y sustituida, conservando su contenido. Solo son canónicas las réplicas TXT enlazadas abajo.
5. **Declaración de IA:** se identificó GitHub Copilot y su propósito. No se añadió la afirmación no comprobada de que el apoyo no sustituyó el análisis propio; se explicitó la validación personal pendiente.
6. **Verificación insuficiente:** se añadió [un verificador reproducible de integridad](verificar-integridad-actividad-9.py) que contrasta el PDF real, no solo el fuente ni la lista de adjuntos. Se probó también que detecta una alteración simulada de palabras sin modificar el PDF original.

## 3. Brechas que impiden certificar el contrato completo

### Flujo y trazabilidad de AulaTeX

- **Extractor específico ausente:** faltan fichas, conceptos, ideas, trazabilidad y resumen de planeación verificables para Actividad 9. El observador detectó esa carencia y solicitó `run-extractor`. No se crearon archivos vacíos ni señales artificiales para aprobarlo.
- **Detalles editoriales del nodo:** el observador advierte que no hay `editing_details` persistidos para el nodo resuelto. Las memorias generales y de otras actividades no sustituyen un registro específico vigente.
- **Objetivo y conceptos:** fallan `objective` y `concepts_min`. La ausencia de señales extraídas no significa que el reporte carezca de contenido conceptual; significa que no existe evidencia estructurada suficiente para esos controles.
- **Presentación:** no se identificó una presentación de Actividad 9 que deba alinearse. No se trasladaron requisitos de otras actividades.

### Formato y revisión humana

- **APA general:** las cajas tienen referencias manuales con sangría francesa, pero la bibliografía general usa `plainnat`; no es un estilo APA 7. Queda pendiente homogeneizar ese formato si se busca conformidad APA integral del reporte. La correspondencia de las seis claves con la bibliografía sí se comprobó.
- **Declaración de IA:** la ubicación y herramienta están documentadas. La afirmación contractual «no sustituyó el análisis propio» requiere confirmación del estudiante; no debe incorporarse solo para satisfacer un detector.
- **Plantilla institucional:** la documentación institucional habla de herencia compartida y la documentación local permite reportes autónomos. Se conservó el diseño ITESCA existente; no se certifica herencia de plantilla ni se impusieron fuentes/interlineados provenientes de otras consignas.
- **Lectura requerida y participación:** el video completo sigue sin acreditarse y las tres intervenciones siguen sin publicación propia comprobada. Los enlaces a hilos de compañeros son destinos/contexto, no acuses propios.

## 4. Fuentes y pruebas realizadas

- Releídos el contrato general, el contrato específico de foro, el transformador y el observador actuales, además de memoria editorial local y ascendente. El observador tenía cambios de trabajo preexistentes: se ejecutó esa versión, sin modificarla.
- Cita de Jimenez-Lopez et al. (2020) recotejada con la **página impresa 82**, segunda página del PDF académico local. Se verificó la secuencia citada, no solo la existencia de la entrada bibliográfica.
- Seis claves citadas encontradas en la bibliografía local; no se utilizan las entradas editoriales provisionales como sustento.
- Inspección visual del aporte, sus referencias, conclusión y bibliografía general después de recompilar. Las páginas restantes mantienen sus cajas y se verificaron mediante extracción de texto.
- Prueba positiva del verificador: aprobación de tres cajas y tres adjuntos. Prueba negativa: sustitución simulada de una palabra en la extracción PDF detectada como diferencia. No se alteraron mensajes del foro ni archivos de compañeros.

## 5. Artefactos canónicos y huellas de esta revisión

- [Reporte TEX](reporte-fundamentos-de-gestion-administrativa-Actividad-9.tex).
- [PDF de siete páginas](reporte-fundamentos-de-gestion-administrativa-Actividad-9.pdf).
- [Aportación inicial](foro-participacion-Actividad-9.txt).
- [Réplica 1](foro-replica-1-Actividad-9.txt).
- [Réplica 2](foro-replica-2-Actividad-9.txt).

SHA-256 del PDF auditado: `5e0bcd6cc8cc4cd0deb01ee0f40dc6502f955d69ec89dba0a37b36c6e95c85e7`.

SHA-256 del TEX auditado: `e59b28527a887bebdd568603396180e521e259d60bd16bf9f4ea804923a4d92e`.

El verificador calcula nuevamente las huellas de los cinco artefactos y comprueba frescura respecto del TEX, bibliografía y adjuntos. Cualquier edición o recompilación posterior puede invalidar estas huellas y exige repetir la comprobación. No se efectuaron commits ni se revirtieron cambios ajenos.

## 6. Orden recomendado para el cierre posterior

1. Resolver extracción y trazabilidad reales de Actividad 9; persistir planeación y detalles editoriales con fuentes verificables, no copiar los de otra actividad.
2. Homogeneizar la bibliografía general y aclarar la excepción de plantilla autónoma.
3. Completar la revisión del video y la validación personal del contenido y de la declaración de IA.
4. Reejecutar observador e integridad, conservando ambos resultados y sin interpretar un umbral parcial como cierre integral.
5. Publicar únicamente si el foro se reabre o existe una alternativa autorizada; conservar los tres acuses reales antes de registrar participación realizada.