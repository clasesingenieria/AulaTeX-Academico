# investigacion-aulatex

Análisis y evidencias de investigación. Este índice no acredita trabajo de campo ni resultados.

Material académico versionable dentro de la materia.
# Investigación conceptual de muestreo

La base utilizable es [la versión revisada](base-conceptual-unidad-1-revisada.md), con 3,072 palabras, doce apartados conceptuales y aplicaciones de tres artículos académicos. Se refleja en `base-conocimiento.md` y `base-conocimiento.json`.

La fase conceptual y la extracción se ejecutaron realmente con **Amazon Nova Pro** mediante `AulaTeXLLMClient.call`, sin cambiar de motor. El [manifiesto](manifest-nova-unidad-1.json) conserva modelo, estado, uso y rutas; los prompts y respuestas originales están en `nova-pro-unidad-1-2026-10-24-r3/`. Los dos primeros intentos fallaron por el timeout de 45 segundos y permanecen registrados; el tercero amplió únicamente el timeout del proceso a 300 segundos. No se modificó el archivo de credenciales.

La salida cruda `base-conceptual-unidad-1-nova.md` **no es una autoridad ni la versión final**. El cotejo corrigió precisión/exactitud, definiciones demasiado generales, localizadores y errores en clasificación de estudios. La sección 1.1 de OpenStax se recuperó como apoyo editorial adicional para definiciones; no se afirma que se enviara a Nova en esta corrida.

La bibliografía formal existente se confirmó: Holmes et al. (2023), NIST/SEMATECH y los artículos de Bradley et al. (2021), Barrero et al. (2023) y Bloom et al. (2024). No se agregaron referencias inventadas. Los tres artículos se publicaron dentro de los cinco años anteriores al 24/10/2026.

Reproducción desde raíz: ejecutar `assets-estadistica-aplicada-para-la-administracion/investigar_extraer_nova_unidad1.py` con el Python del entorno; después, `revisar_extraccion_nova_unidad1.py`. El primer script reutiliza respuestas exitosas ya conservadas cuando el prompt coincide; el segundo materializa el cotejo editorial sin alterar los originales.

