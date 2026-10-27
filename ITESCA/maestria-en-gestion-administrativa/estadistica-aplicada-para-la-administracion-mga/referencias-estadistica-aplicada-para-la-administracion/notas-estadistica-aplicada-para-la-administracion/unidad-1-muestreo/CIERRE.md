# Cierre editorial: unidad 1, muestreo

Fecha local: 22/10/2026. Los registros técnicos usan UTC y pueden mostrar 23/10/2026. Alcance: tareas 1.1 y 1.2 del curso GGEA01, Moodle 209. No se inició el cuestionario ni se enviaron trabajos.

## Consigna y memoria

- Consulta autenticada de ambas tareas: [inspección](../materiales-aula/2026-10-22/inspection.json), [infografía](../materiales-aula/2026-10-22/1747-consigna-estado.txt) e [investigación](../materiales-aula/2026-10-22/1748-consigna-estado.txt). Ambas estaban sin envío y sin calificación; cierre publicado 25/10/2026, 23:00.
- Se consultaron el contrato `REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT`, el contrato de metadatos visibles de ITESCA, la memoria local de materia, la memoria ascendente de carrera y la memoria de trabajo de Estadística. Los antecedentes del reporte genérico no se usaron como evidencia de calidad de estos documentos.
- [Portada oficial](../materiales-aula/2026-10-22/DocumentoMGAVirtual-oficial.docx) y [verificación del enlace y hash](../materiales-aula/2026-10-22/portada.json). El vínculo se encuentra en `/mod_assign/intro/`, fuera del filtro del inspector general. El fondo extraído conserva los logotipos y diseño MGA Virtual; se añadieron título, asignatura, estudiante, matrícula, docente y fecha.
- La rúbrica de infografía repite un descriptor de fuentes dentro de aplicación administrativa. Se conservó el original sin corregirlo y se incluyeron aplicaciones administrativas y de mercado de todos modos.

## Productos

| Correspondencia | Fuente canónica | Producto |
| --- | --- | --- |
| Actividad 1 local = tarea 1.1, módulo 1747 | [TEX](../../../reporte-estadistica-aplicada-para-la-administracion-Actividad-1.tex) | [Infografía PDF](../../../entregas-estadistica-aplicada-para-la-administracion/Actividad-1-Infografia.pdf), una lámina A3 vertical, sin portada. |
| Actividad 2 local = tarea 1.2, módulo 1748 | [TEX](../../../reporte-estadistica-aplicada-para-la-administracion-Actividad-2.tex) | [Investigación PDF](../../../entregas-estadistica-aplicada-para-la-administracion/Actividad-2-Investigacion.pdf), cinco páginas carta incluida portada y referencias. |

No se creó una presentación porque las consignas no la solicitan. La presentación genérica de materia no es una presentación de estas actividades y no se alteró.

## Mapa de soporte

| Fuente formal | Evidencia consultada | Uso y límite |
| --- | --- | --- |
| Holmes, Illowsky y Dean (2023), *Introductory business statistics*, 2.ª ed. | [Muestreo, sec. 1.2](holmesMuestreo2023.txt); [proporciones, sec. 8.3](holmesProporcion2023.txt) | Definición, diseños, cobertura y fórmula aproximada del tamaño para estimar una proporción. No generalizar la igualdad de probabilidades a todos los diseños probabilísticos. |
| NIST y SEMATECH (2003), *e-Handbook of statistical methods*, sec. 7.2.4.2 | [Extracción](nistTamano.txt) | El tamaño para contrastes depende de significación, potencia y efecto detectable. No se usa la fórmula de prueba de hipótesis como si fuera la de precisión de una estimación. |
| Bradley et al. (2021), *Nature*, 600(7890), 695-700; DOI 10.1038/s41586-021-04198-4 | [Texto](bradley2021.txt), secciones *Comparing study designs*, *The Big Data Paradox in vaccine uptake*, *Methods* y tabla 1 | Delphi: aleatorio estratificado dentro de usuarios activos; Census: sistemático sobre direcciones contactables; Ipsos: reclutamiento probabilístico postal. Alrededor de 250000/75000/1000 respuestas por semana o ronda, según encuesta; sobreestimaciones de 17 y 14 puntos en mayo de 2021 respecto del referente CDC. El referente tiene incertidumbre, tratada por los autores; no implica superioridad universal de muestras pequeñas. |
| Barrero, Bloom y Davis (2023), *Journal of Economic Perspectives*, 37(4), 23-50; DOI 10.1257/jep.37.4.23 | [PDF publicado](../../articulos-muestreo/barrero2023.pdf); [extracción](barrero2023.txt), páginas impresas 23-24, figura 1 y notas | Encuestas de cortes repetidos, calibración por edad-sexo-educación-ingresos, restricciones poblacionales y ajustes por cambios de pregunta. El 28% se refiere a días remunerados en junio de 2023, no a empleados. No se inventa un único tamaño ni un muestreo aleatorio simple común a todas las fuentes. |
| Bloom, Han y Liang (2024), *Nature*, 630(8018), 920-925; DOI 10.1038/s41586-024-07500-2 | [XML completo](../../articulos-muestreo/bloom2024.xml); [texto](bloom2024.txt), *Location and set-up*, *Randomization*, *Employee attrition*, *Null results*, *Competing interests* | Dos divisiones seleccionadas por la empresa, 1612 elegibles, 518 voluntarios y 1094 no voluntarios; asignación por paridad de cumpleaños a tratamiento 792/control 820. Salidas 7.2%/4.8%, reducción de 2.4 puntos y un tercio relativo. Distinguir selección institucional y aleatorización; pruebas de equivalencia no prueban igualdad exacta; conflicto de interés declarado. |

Los tres artículos de la investigación fueron publicados el 08/12/2021, en otoño de 2023 y el 12/06/2024, respectivamente: todos dentro de los cinco años anteriores a la consulta. Los manuales solo sustentan la infografía; no sustituyen los tres artículos requeridos. Los materiales del aula sirven para consigna y trazabilidad, no como autoridad conceptual.

[Manifiesto de fuentes y hashes](fuentes.json). El mapa confirma y amplía la bibliografía activa con tres artículos; las cinco obras citadas entre ambos productos están registradas allí. Los resúmenes se redactaron en español sin copiar la prosa de los artículos.

## Aplicación del contrato

- Investigación: tres actos visibles, introducción, único desarrollo con título temático y tres subsecciones, y conclusiones en página propia. Las conclusiones integran comparación, juicio argumentado y transferencia administrativa. Referencias aparte.
- Infografía: se conserva el producto visual como núcleo. Introducción, desarrollo temático y conclusión caben en la misma lámina; la regla genérica de conclusión en página nueva cede al formato libre de infografía. La consigna excluye portada y menciona Canva como ejemplo, no como herramienta obligatoria; se elaboró en LaTeX/TikZ.
- Fuera del contenido visible quedaron IDs, URLs de entrega, fechas de cierre, técnica editorial y controles. Los títulos son temáticos; el número de actividad está en identificación y metadatos PDF.
- Arial 12, interlineado 1.5, justificación y extensión se aplicaron expresamente a la investigación, sin asumir que Helvetica los satisface. Se usó el fondo de la portada docente, no una portada genérica alternativa.
- Referencias APA controladas con `thebibliography`, citas autor-año y punto y coma entre fuentes múltiples; entradas correspondientes en la bibliografía activa. Las modificaciones futuras deben mantener la concordancia entre referencias visibles y `.bib`.
- Redacción y revisión asistidas por GitHub Copilot; no se atribuye una revisión humana del estudiante que aún no ocurrió. No se añadió declaración visible de IA porque la consigna no la exige; no se declara calificación, consenso de motores ni puntuación EMS no medida.

## Validación y revisión adversarial

La [auditoría reproducible](../../../assets-estadistica-aplicada-para-la-administracion/validar_unidad_1.py) verificó ambos PDF frescos, una y cinco páginas, presencia de identificación y referencias, ausencia de metadatos operativos y marcadores pendientes, límites físicos del texto, seis hashes de fuentes y copias de entrega idénticas. [Resultados](validacion.json).

- Cálculo independiente: `ceil(1.96^2 * 0.5 * 0.5 / 0.05^2) = 385`; con respuesta prevista de 80%, `ceil(385/0.8) = 482`. Son supuestos de ejemplo, no datos levantados. Las invitaciones planificadas no garantizan el número final ni eliminan el sesgo de no respuesta.
- Todo el texto del cuerpo de investigación usa Arial regular, cursiva o negrita. Tamaño extraído: 11.955 puntos PDF, equivalente a 12 puntos TeX. Se conserva la advertencia no crítica TS1 de la plantilla: no aparecen otras familias en el texto del reporte.
- Sin errores críticos, citas indefinidas, desbordes Overfull/Underfull ni caracteres ausentes. Las ecuaciones de la infografía usan fuentes matemáticas, apropiadas para el formato libre.
- Revisión visual de las seis páginas con `pdftoppm`: fondo oficial y datos legibles, sin páginas vacías ni texto fuera de página. Se corrigió un solapamiento en la nota del cálculo y se volvió a renderizar. Las referencias finales fueron revisadas tras ajustar la sangría.
- Se examinó el riesgo de confundir tamaño con representatividad, aleatorización con muestreo, porcentaje con puntos porcentuales y proporción de días con proporción de personas. Esas distinciones quedaron explícitas.

Estado final: **preparados y validados para revisión del estudiante, no enviados**. El criterio docente de puntualidad y cualquier calificación dependen del envío efectivo y la evaluación del aula; no pueden darse por cumplidos solo por generar el PDF.