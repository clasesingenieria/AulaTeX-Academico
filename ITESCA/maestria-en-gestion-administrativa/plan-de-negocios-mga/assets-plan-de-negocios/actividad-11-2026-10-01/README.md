# Fuentes de la Actividad 11 de AM Taller

Fecha: 1 de octubre de 2026. El documento combina diagrama y tabla de un proceso propuesto de cambio de aceite y filtro. `proceso.json` contiene los 16 pasos y sus transiciones.

## Regeneración

1. Ejecutar `generar_diagrama.py` con Python, ReportLab y las fuentes Arial de Windows. Produce `flujo-vectorial.pdf` (dos páginas).
2. Rasterizar ese PDF con `pdftoppm -png -r 240 flujo-vectorial.pdf flujo` para obtener `flujo-1.png` y `flujo-2.png`.
3. Ejecutar `generar_documento.py` con python-docx. Conserva la portada de la actividad 10 y genera el nuevo Word de la actividad 11 sin modificar el original.
4. Ejecutar `exportar_word.ps1 -Paths <ruta-al-Word>` mediante PowerShell con Microsoft Word instalado. Actualiza campos, guarda el Word y exporta el PDF completo.
5. Tras revisar el PDF completo, extraer las páginas 1, 3 y 4 para la versión gráfica; las páginas 1, 2, 5, 6, 7, 8 y 9 para la redactada. Esas selecciones corresponden a la revisión de nueve páginas del 01/10/2026; deben revisarse si cambia la paginación.

Los PDF finales de ambas versiones fueron enviados a Moodle. No regenerarlos después del envío sin registrar una revisión nueva, porque cambiaría la correspondencia con los comprobantes de entrega. [Evidencia](../../referencias-plan-de-negocios/actividad-11-2026-10-01/README.md).
