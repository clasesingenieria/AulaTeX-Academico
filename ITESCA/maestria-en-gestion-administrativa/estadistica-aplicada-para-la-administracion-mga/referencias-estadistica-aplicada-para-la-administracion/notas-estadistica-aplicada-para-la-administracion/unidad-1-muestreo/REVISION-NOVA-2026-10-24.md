# Revisión de investigación y extracción, 24/10/2026

Se rehízo la Actividad 2 conservando su nombre de archivo y la portada oficial. La comparación de las imágenes rasterizadas de la portada previa y la nueva fue idéntica píxel a píxel. El cuerpo mantiene cinco páginas incluidas portada y fuentes, Arial 12, interlineado 1.5 y justificación.

El desarrollo es una única sección temática. Incluye preparación conceptual, tres aplicaciones académicas del muestreo y una síntesis interpretativa natural antes de la sección independiente de conclusiones. El cierre integra postura razonada y transferencia a decisiones administrativas. Se añadió una cita conceptual visible a Holmes et al. (2023), ya presente en la bibliografía verificada; se confirmaron las tres referencias académicas requeridas.

La investigación ampliada queda en `../../../investigacion-aulatex/base-conceptual-unidad-1-revisada.md`: 3,072 palabras, con fuentes formales y distinción entre hallazgos, ejemplos hipotéticos e inferencias. Sirve también para fundamentar el reporte que incorpora la infografía original.

Se ejecutaron dos llamadas exitosas reales a Nova Pro, modelo `us.amazon.nova-pro-v1:0`, con terminación `end_turn`: investigación conceptual (37,302 tokens de entrada y 3,168 de salida) y extracción documental (74,049 de entrada y 7,019 de salida). Las respuestas originales, prompts, hashes y metadatos se conservan. Dos intentos anteriores fallaron por `ReadTimeoutError`; la configuración imponía 45 segundos. La solución amplió solo el timeout de este proceso a 300 segundos, sin modificar el entorno de credenciales ni cambiar de motor.

El cotejo encontró errores sustantivos del motor y los corrigió antes de usar sus resultados: precisión confundida con exactitud, autores incompletos, título inexacto, 28% confundido con tamaño de muestra, diseños mal clasificados y conceptos no sustentados. Los archivos canónicos contienen 24 fichas, 12 ideas y tres artículos revisados; los originales no se ocultaron ni se sustituyeron. No se declara revisión humana.

La [validación específica](validacion-actividad-2-2026-10-24.json) registra cinco páginas, familias Arial, tamaño equivalente a 12 puntos TeX, ausencia de desbordes y citas indefinidas, revisión visual de las cinco páginas con pdftoppm y promoción de copias idénticas a raíz y entregas. Permanece la advertencia heredada TS1 de la plantilla, sin sustitución visible de Arial en el cuerpo. El flujo documental no interactúa con Moodle; el estado del envío se documenta por el agente responsable de la plataforma.
