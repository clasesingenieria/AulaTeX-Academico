# Reporte de lectura S1: memoria editorial y soporte

Fecha: 27 de septiembre de 2026. Alcance: redacción y PDF de apoyo para transcripción manuscrita; no entrega en plataforma.

## Insumos y reglas consultados antes de redactar

- Consigna del usuario y `planeaciones-derecho-mercantil/planeacion-modulo-49871.json`.
- `README.md` del repositorio y `scripts/aulatex/activity_contract.py`, contrato `REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT`.
- `.memoria-aulatex/memoria-institucion-UAS--0b2c7475ec34.json` y `UAS/memoria-fundacional.json`: identidad, no invención, trazabilidad, fuentes locales y compilación reproducible.
- Memoria local: README, COMPILACION, manifiesto y notas de revisión de la materia. Nodo relacionado: reporte S1 y base institucional de Investigación aplicada a la contaduría, para los datos de estudiante, matrícula, grupo y lugar. Asesor confirmado expresamente por el usuario: Wilder Alfredo Angulo.
- Plantilla visual solicitada `reporte-derecho-mercantil.pdf` y su base compartida `UAS/plantilla-actividad-uas.tex`. Se conservan portada, logos, Arial 12, color y márgenes de 2.54 cm. Se ajusta únicamente el espaciado del cuerpo para la extensión pedida.

## Lectura y localizadores

El PDF proporcionado contiene 106 páginas escaneadas, correspondientes a las páginas impresas 3 a 108. Regla de localización: página impresa = página del visor PDF + 2. Se extrajo OCR en español de todo el fragmento y se cotejaron visualmente pasajes fundamentales. El OCR contiene ruido de subrayados y debe cotejarse con el facsímil al reutilizar citas literales.

La página `Lecturas_S1`, módulo 49867, conservada en `referencias-derecho-mercantil/consulta-aula-2026-09-22.json`, identifica a Eduardo García Máynez y las páginas 3 a 108. El fragmento no incluye portada editorial ni fecha: se usa **s. f.**, sin inventar edición o editorial. UAS figura como sitio de acceso, no como autora del libro.

| Subtema | Sustento en páginas impresas | Síntesis validada |
|---|---|---|
| Antecedentes históricos | 52-53 | Costumbre anterior a legislación; diferenciación de reglas; recopilaciones de Justiniano; escritura medieval; codificación y seguridad jurídica. |
| Acepciones | 36-40 | Objetivo/subjetivo; vigente/positivo según terminología del autor; derecho natural y justicia intrínseca. |
| Fuentes | 51-52 | Formales, reales e históricas; legislación como proceso y ley como resultado. |
| Normas jurídicas | 15, 21-22, 82-83 | Bilateralidad, exterioridad predominante, coercibilidad y heteronomía; normas genéricas e individualizadas. |
| Estado | 97-98, 108 | Población, territorio, poder y organización constitucional; relación entre poder y orden jurídico. |
| Conclusiones | Relación argumentativa con los cinco ejes | Aplicación propuesta a la contaduría, sin atribuir al autor un caso contable inexistente. |

## Decisiones contractuales

1. Técnica conservada: reporte de lectura con cinco subtemas; tres secciones principales (introducción, sección temática y conclusiones). Los cinco incisos son subsecciones de la sección temática. No se convierte en cuestionario, cuadro o presentación.
2. Bibliografía: una obra es suficiente porque la consigna asigna expresamente ese fragmento y sostiene los cinco ejes. Se documenta la excepción prevista por `reference_growth` para corpus local suficiente. No se inventan dos fuentes adicionales para satisfacer los umbrales genéricos de un observador automático. Cinco citas visibles remiten a una entrada real en `.bib`.
3. Extensión: se interpreta una a dos cuartillas como cuerpo del reporte, con portada adicional conforme a «añadir una portada». Referencias en la segunda cuartilla. Se exceptúa el salto de página propio de conclusiones de informes largos para respetar el máximo específico.
4. No se actualizan las normas históricas citadas en el libro como si fueran legislación vigente. El reporte es conceptual y no reproduce artículos ni reglas procesales que requieran actualización normativa.
5. Declaración de IA breve y veraz en nota al pie de la conclusión; no se afirma una revisión personal no realizada por el estudiante.
6. El borrador previo `reporte-actividad1-derecho-mercantil.tex` y los archivos existentes en `actividades/` se conservan. El nuevo punto de entrada es `reporte-derecho-mercantil-Actividad-1.tex`.
7. No hay presentación de esta actividad que alinear; la presentación genérica de la materia sigue siendo una plantilla.

## Estado de entrega

La redacción digital no satisface por sí sola el requisito «puño y letra». El estudiante debe revisar la síntesis, escribir el cuerpo personalmente en una o dos cuartillas, digitalizarlo, añadir la portada y comprobar el tamaño final antes de enviarlo. No se usó tipografía manuscrita para simular ese cumplimiento. La extensión del manuscrito depende del tamaño de letra y espaciado; el PDF sirve como distribución orientativa.

Validación técnica y visual del PDF: registrar en `validacion-final.json` tras compilar. La compilación y la revisión editorial no acreditan envío ni calificación.
