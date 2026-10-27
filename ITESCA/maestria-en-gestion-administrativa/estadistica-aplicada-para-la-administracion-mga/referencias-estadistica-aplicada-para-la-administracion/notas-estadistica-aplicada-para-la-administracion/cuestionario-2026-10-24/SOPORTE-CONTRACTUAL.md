# Soporte del cuestionario de muestreo

Fecha de preparación: 24 de octubre de 2026. Este registro no acredita un intento ni una entrega en plataforma.

## Artefacto reservado

`reporte-estadistica-aplicada-para-la-administracion-Actividad-5.tex`, en la raíz de la materia. Título: **Muestreo y representatividad**. Subtítulo: **Actividad 5: Cuestionario**. Se conserva el fondo oficial y la identidad de la portada del reporte de investigación.

La fuente bloquea la compilación si falta `reactivos-validados.tex`. Los veinte reactivos proceden de `respuestas-validadas.json`, con texto literal, opciones, respuesta seleccionada, justificación y fuentes; no se generaron preguntas para llenar el formato. `construir_reporte_cuestionario.py` conserva ese JSON y produce `respuestas-soporte-editorial.json`, con fuentes y localizadores enriquecidos, además de las piezas TEX. Estas se copian a `assets-estadistica-aplicada-para-la-administracion/cuestionario/` para evitar el límite de longitud de rutas del ejecutable TeX en Windows.

## Contrato aplicable

- `aulaTEX/aulatex/activity_contract.py`, `REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT`: memoria previa, fuentes verificables, tres actos y pregunta/respuesta/justificación visibles; ningún identificador operativo de Moodle en el producto.
- Memoria ascendente `ITESCA/.memoria-aulatex/memoria-carrera-ITESCA__maestria-en-gestion-administrati--f379ecceff04.json`: marco conceptual previo y tabla horizontal de cuatro columnas: número, pregunta, respuesta y justificación. Cada fundamento relaciona la respuesta con el concepto y su fuente.
- Introducción: contexto administrativo y problema. Segundo acto: una sección de título temático, con marco conceptual y cuestionario como subsecciones; síntesis interpretativa al final. Conclusión: síntesis, juicio argumentado e implicación profesional, sin narrar el proceso de edición.
- El resultado o calificación solo se documentará si se confirma en evidencia real de plataforma. No se presume corrección por haber seleccionado una opción.

## Fuentes locales revisadas

| Clave bibliográfica | Localizador local | Soporte previsto y límites |
| --- | --- | --- |
| `holmesBusiness2023` | `../unidad-1-muestreo/holmesMuestreo2023.txt`, sección 1.2; archivo HTML en `../../articulos-muestreo/holmesMuestreo2023.html` | Muestreo aleatorio simple, estratificado, sistemático, conglomerados, conveniencia, error de muestreo y no respuesta. La igualdad de probabilidades de las muestras corresponde al aleatorio simple; no extenderla a todo diseño probabilístico. |
| `holmesBusiness2023`, sección 8.4 | `openstax-tamano-muestral.html` y `.txt`; https://openstax.org/books/introductory-business-statistics-2e/pages/8-4-calculating-the-sample-size-n-continuous-and-binary-random-variables | Tamaño de muestra para media/proporción, valor crítico normal, tolerancia, elección conservadora p=0.5 y redondeo hacia arriba. |
| `wackerly2010` | `../extracciones-libros/estadistica-matematica-con-aplicaciones--9b3812669eea.txt`; libro local con edición española cotejada en la bibliografía activa | Población, muestra, estadístico e inferencia. Confirmar página impresa específica al asignar soporte a cada reactivo real. |
| `nistHandbook` | `../unidad-1-muestreo/nistTamano.txt` | Tamaño para contrastes: significación, potencia y efecto detectable. No confundir su fórmula con precisión para estimar una proporción. |
| `bradley2021` | `../unidad-1-muestreo/bradley2021.txt`, apartados Comparing study designs y The Big Data Paradox | Cobertura, participación y diferencia entre volumen y representatividad. No inferir que las muestras pequeñas son universalmente mejores. |
| `bloom2024` | `../unidad-1-muestreo/bloom2024.txt`, apartados Location and set-up y Randomization | Diferencia entre selección institucional y asignación experimental; límites de generalización. |
| `statcanNoProb2021` | `statistics-canada-no-probabilistico.html` y `.txt`, apartados Quota sampling, Convenience or haphazard sampling y Snowball or network sampling | Fuente institucional consultada el 24/10/2026, modificada el 02/09/2021. Cuotas frente a estratificación, accesibilidad y referencia de contactos. URL: https://www150.statcan.gc.ca/n1/edu/power-pouvoir/ch13/nonprob/5214898-eng.htm . |
| `statcanProb2021` | `statistics-canada-probabilistico.html` y `.txt`, apartados Stratified sampling, Cluster sampling y Systematic sampling | Fuente institucional consultada el 24/10/2026, modificada el 02/09/2021. Diseños probabilísticos y uso de conglomerados ante dispersión geográfica para reducir desplazamientos. URL: https://www150.statcan.gc.ca/n1/edu/power-pouvoir/ch13/prob/5214899-eng.htm . |

Las siete claves están registradas en `cuestionario-fuentes-verificadas.bib`, bibliografía propia para evitar conflictos con las otras actividades en edición. La fuente formal de Statistics Canada confirma la distinción de cuotas del material del aula `../materiales-aula/2026-10-18/archivos/1745-1d6cdf095c3e.txt`, líneas 209--212.

Se cotejaron además las páginas legales de tres libros locales: Anderson, Sweeney y Williams (11.ª edición, 2012, ISBN 978-607-481-750-8; página 6 del PDF), Levin y Rubin (7.ª edición revisada, 2010, ISBN 978-607-442-905-3; página 6 del PDF) y Lind, Marchal y Wathen (15.ª edición, 2012, ISBN 978-607-15-0742-6; página 5 del PDF).

De Levin y Rubin se revisó el capítulo 6: página impresa 238 (PDF 256), clasificación de diseños; página 239 (PDF 257), muestreo aleatorio simple; página 241 (PDF 259), sistemático, estratificado y comienzo de conglomerados; página 267 (PDF 285), glosario. La página 241 distingue la probabilidad de cada elemento de la probabilidad de cada muestra y advierte la periodicidad del muestreo sistemático. El glosario simplifica la definición de muestreo probabilístico a oportunidades iguales, por lo que esa frase no se generaliza a diseños de probabilidades desiguales. Son apoyos posibles para reactivos concretos; no se añaden referencias nuevas sin uso visible.

## Verificación de los veinte reactivos

Se contrastaron las veinte selecciones con las opciones reales. Se preservan los matices de los reactivos 6 (la hipótesis nula no es un paso indispensable de toda encuesta), 9 (la igualdad individual no es definición suficiente del aleatorio simple), 14 y 15 (representatividad como objetivo evaluable) y 16 (aumentar n no elimina automáticamente el sesgo). El reactivo 18 se fundamenta en la dificultad de acceso, no solo en un tamaño poblacional pequeño.

El cierre del intento consta en `resultado-plataforma.json`. No hay calificación publicada al momento de la documentación: la revisión se habilitará según la fecha publicada por el aula. El cuerpo académico no contiene esos datos operativos ni presume una nota.

Compilación mediante `build(5)` del validador de unidad 1, usando `latexmk -norc -xelatex` y `TEXINPUTS` limitado a la plantilla. La búsqueda recursiva de todo ITESCA provocó una terminación de XeLaTeX con código 3221225477 y se descartó ese entorno.

Pendiente del cierre técnico: `validar_reporte_cuestionario.py`, renderización e inspección visual. La comprobación no presume aprobación por el simple hecho de compilar.
