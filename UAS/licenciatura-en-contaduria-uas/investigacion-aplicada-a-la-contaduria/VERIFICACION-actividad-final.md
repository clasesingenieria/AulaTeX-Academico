# Corrección de formato del reporte final UAS

Fecha: 13 de septiembre de 2026.

## Alcance y patrón de referencia

Se corrigió el formato independiente de la primera versión. El reporte final
carga ahora la misma plantilla compartida que el reporte de Actividad 1 de la
asignatura: `base/Plantilla-Informe/template.tex`, con `\templatePortrait`,
`\templatePagecfg`, `\templateIndex` y `\templateFinalcfg`.
No se modificaron la plantilla global ni los demás reportes.

## Comprobaciones

| Elemento | Corrección o verificación |
|---|---|
| Portada | Estilo 1 de la plantilla, encabezado institucional, logo FCA-UAS existente, título central y tabla de autores. Escudo FCA como marca de agua al 12 % de opacidad, solo en la primera página; comprobado mediante renderizado e inventario de imágenes del PDF. |
| Integrantes | Los cinco autores del texto suministrado; acentuación de Martín y Martínez corregida. |
| Datos académicos | Investigación aplicada a la contaduría; Dra. Nadia Aileen Valdez Acosta; grupo 103, corroborados en el aula durante la revisión. No se copió el grupo 101 del reporte modelo. |
| Lugar y fecha | Culiacán, Sinaloa; septiembre de 2026. |
| Tipografía | Arial real de 12 pt en el cuerpo, con regular, negrita y cursiva incrustadas. Los títulos conservan los tamaños jerárquicos de la plantilla. |
| Estructura | Resumen, Abstract, Introducción, 1. Objetivo general, 2. Marco teórico y conceptual, 3. Método, 4. Resultados, 5. Discusión, 6. Conclusiones, 7. Referencias. |
| Discusión | Incorporado el párrafo solicitado que comienza con «En relación con la materialización de las operaciones facturadas», con citas automáticas de Rico-Martínez et al. (2023), Arrona Moreno et al. (2022) y Rico Martínez et al. (2024). Texto completo comprobado en la página numerada 8, página 10 del PDF. Se conserva la grafía del autor de 2024 registrada en su referencia. |
| Conclusiones | Párrafo introductorio y cinco conclusiones numeradas. |
| Bibliografía | Ocho referencias citadas en el cuerpo; APA con Biber y biblatex-apa. Autores OpenStax y resumen del IASB corregidos conforme a los archivos consultados. |
| Paginación | Portada sin número visible; índice romano; cuerpo arábigo. Pies de 9 pt con subtítulo y materia en una sola línea, también en el índice. Espacio mínimo antes del último párrafo de Resultados y de la actualización normativa en Discusión para evitar cortes; protección de viudas y huérfanas. |
| Geometría | Recalculada después de cargar la plantilla para evitar que LuaLaTeX recorte el pie. Verificación visual de portada e índice. |
| PDF | 13 páginas, carta, 449 419 bytes (aproximadamente 449 KB); inferior al límite de 2 MB de la consigna. |
| Compilación | LuaLaTeX + Biber mediante `compilar-actividad-final.sh`; auxiliares aislados. Sin citas indefinidas ni cajas desbordadas. |
| Ubicación | PDF final junto al TEX. La copia en `.build` de la materia se actualiza para no conservar el enlace anterior con contenido obsoleto. |

## Observaciones técnicas y de alcance

- La plantilla emite un aviso de sustitución `TS1/Arial`; `pdffonts` confirma
  que las fuentes usadas e incrustadas en el PDF son Arial, Arial Bold y Arial
  Italic. No hay caracteres faltantes reportados ni recortes en la portada.
- La estructura explícita de ponencia solicitada prevalece sobre el esquema
  genérico de tres actos de AulaTeX. Se mantienen método, resultados y discusión
  separados; no se transforma la ponencia en otra técnica didáctica.
- Se trata de la plantilla UAS utilizada en este repositorio, no de una
  certificación de un formato universitario oficial distinto.
- Esta verificación de corrección no representa una calificación docente ni
  una revisión jurídica profesional. No se realizó envío a Moodle.