# Cierre editorial: unidad 2

Fecha de elaboración: 23/10/2026. Curso GGEA01, Moodle 209. Alcance: dos tareas escritas; no se enviaron archivos ni se iniciaron cuestionarios.

## Correspondencia y consignas

| Tarea | Fuente editable | Entrega |
| --- | --- | --- |
| 2.1 Investigación documental y aplicada, 1754 | [Actividad 3](../../../reporte-estadistica-aplicada-para-la-administracion-Actividad-3.tex) | [PDF de investigación](../../../entregas-estadistica-aplicada-para-la-administracion/Actividad-3-Investigacion-estimacion.pdf) |
| 2.2 Ejercicios, 1755 | [Actividad 4](../../../reporte-estadistica-aplicada-para-la-administracion-Actividad-4.tex) | [PDF de ejercicios](../../../entregas-estadistica-aplicada-para-la-administracion/Actividad-4-Ejercicios-distribuciones.pdf) |

La [inspección autenticada](../materiales-aula/2026-10-23/inspection.json) confirma ambas tareas sin envío y cierre el 01/11/2026 a las 23:00. La fecha de apertura de 2.2 aparece como 20/10/2025; se conserva sin corregir el dato original. La investigación aborda estimación aunque Moodle la ubica en Distribuciones muestrales; se respeta su consigna.

El [manifiesto de enlaces](../materiales-aula/2026-10-23/enlaces-intro.json) conserva URL y SHA-256 del [PDF original de ejercicios](../materiales-aula/2026-10-23/1755-adjunto-1.pdf) y de la [portada oficial de 2.1](../materiales-aula/2026-10-23/1754-adjunto-1.docx). El original de ejercicios tiene tres páginas físicas (portadilla y dos páginas numeradas). El fondo `word/media/image1.png` coincide por SHA-256 con el asset institucional utilizado. En 2.2 solo se encontró el enlace de ejercicios; se reutiliza la portada institucional comprobada en la materia.

## Contrato AulaTeX

Se consultaron el contrato `REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT`, la memoria de la materia, la memoria institucional ITESCA y el cierre previo de muestreo. Se conservan las plantillas institucionales y los archivos previos. La numeración local continúa después de los dos reportes de la unidad 1; no representa intentos de cuestionarios.

- Investigación: cinco páginas carta incluyendo portada y referencias; definición de estimador y estimación; insesgamiento, eficiencia y consistencia con ejemplos; estimación puntual e intervalar; confianza y margen de error; interpretación sin cálculo del intervalo de ventas; consecuencias administrativas.
- Ejercicios: cinco bloques, con 4 + 2 + 4 + 2 + 8 respuestas. Se conservan datos e incisos, con enunciados resumidos fielmente y original íntegro en notas.
- Ambos: cuerpo tripartito con desarrollo temático único; introducción con problema, conclusión con posición razonada y transferencia profesional; referencias APA con sangría francesa y citas visibles.
- Arial 12 de TeX (aproximadamente 11.955 puntos PDF), interlineado 1.5 y texto justificado. Portadas con título de 16 puntos y datos de 12; pies de página de 10 puntos; ordinal de edición en superíndice.
- IDs, vencimientos y decisiones de ejecución permanecen en notas, no en los PDF. No se agrega presentación, pues no la exige ninguna de estas dos consignas.
- No se atribuye aprobación docente, puntuación EMS ni ejecución del motor multiactor: el cierre acredita controles locales reproducibles y revisión editorial directa.

## Mapa de soporte

Se confirma suficiencia de tres fuentes formales distintas, ya presentes en la [bibliografía activa](../../../referencias-estadistica-verificadas.bib). Se amplía el corpus con capítulos específicos, sin duplicar entradas ni inventar referencias. Los cinco archivos utilizados y sus hashes están en [fuentes.json](fuentes.json). Las dos tareas no son cuestionarios extensos: el segundo producto aplica reiteradamente los mismos modelos en cinco bloques; sus incisos cuentan además con comprobación numérica independiente.

| Afirmación o respuesta | Soporte y comprobación |
| --- | --- |
| Estimación puntual e intervalar y diferencia entre media individual y muestral | Holmes, Illowsky y Dean (2023), capítulos 7 y 8; [capítulo 7](fuente-1.txt), [capítulo 8](fuente-2.txt). |
| Confianza, margen de error e interpretación del intervalo de ventas | NIST/SEMATECH, apartado 1.3.5.2; [texto archivado](fuente-3.txt). No confundir intervalo de la media con predicción individual. |
| Insesgamiento y eficiencia relativa de la media | Linealidad de esperanza y suma de varianzas de observaciones independientes: media de cuatro tiene varianza poblacional/4; usar solo la primera conserva la varianza poblacional. Cotejo complementario con Penn State STAT 415, Lesson 2, secciones 2.1 y 2.2: https://online.stat.psu.edu/stat415/Lesson02.html, consultado el 23/10/2026. No se cuenta como cuarta fuente exigida. |
| Consistencia de la media | Con media común y varianza finita, su insesgamiento y varianza poblacional/n implican por Chebyshev que la probabilidad de error mayor que una tolerancia fija tiende a cero. La comparación de errores estándar para 100 y 400 registros se comprueba en el validador. |
| Sesgo de selección y límites de muestras grandes | Bradley et al. (2021), artículo íntegro preservado en unidad 1, reutilizado sin duplicar el original; hash verificado. |
| Ejercicio 1, incisos a-d | Enumeración de los 16 pares ordenados equiprobables con reposición; media 9, varianza poblacional 20 y varianza de las medias 10. |
| Ejercicio 2, a-b | NIST, distribución binomial, [texto archivado](fuente-4.txt); X ≥ 12 y X ≤ 8. SciPy contrastado con suma explícita mediante coeficientes combinatorios. |
| Ejercicio 3, a-d | Distribución de media normal, error estándar 15 h. Normalidad añadida como supuesto explícito, no como hecho del enunciado. |
| Ejercicio 4, a-b | Binomial con p = 0.46; mayoría estricta: X ≥ 101 y X ≥ 501. Modelo independiente o aproximación para población grande; sin tamaño del electorado no se calcula hipergeométrica. |
| Ejercicio 5, ocho incisos | Normalidad expresa del enunciado; desviación 29 lb para individuos y 29/raíz(n) para medias. SciPy contrastado con `statistics.NormalDist`. |

Los datos de pesos se tratan como supuestos del ejercicio, no como afirmación vigente sobre la población ni como verificación del National Health Survey. Los ejemplos de compras de la investigación son simulados y se identifican así. El intervalo de ventas se interpreta sin reconstruir una muestra inexistente.

## Validación y revisión visual

El [validador](../../../assets-estadistica-aplicada-para-la-administracion/validar_unidad_2.py) reutiliza la función de compilación existente. Los [cálculos](calculos-verificados.json) conservan precisión completa; los PDF redondean probabilidades a seis decimales. La auditoría exige que esas probabilidades exactas, aproximadas y normales aparezcan en el texto extraído del PDF.

Se revisaron visualmente las doce páginas renderizadas: portadas, cuadros, párrafos, pies y referencias legibles, sin solapamientos observados. No hay desbordes, caracteres ausentes ni citas indefinidas en los logs. Persisten advertencias heredadas TS1/Arial; la extracción tipográfica confirma únicamente Arial regular, negrita e itálica en el cuerpo. No se afirma que el log esté libre de toda advertencia.

Comando desde la raíz, con el entorno Python del repositorio:

```powershell
& .\.venv\Scripts\python.exe ITESCA/maestria-en-gestion-administrativa/estadistica-aplicada-para-la-administracion-mga/assets-estadistica-aplicada-para-la-administracion/validar_unidad_2.py --build --archive-sources --promote
```

La [auditoría final](validacion.json) registra hashes de los PDF y las copias de entrega. Los cuestionarios 1.3 y 2.3 no se abrieron ni respondieron en este trabajo. Las siguientes tareas escritas del índice son 3.1 y 3.2; no se consideran realizadas por este cierre.