"""Catálogo contractual de las 100 Técnicas Didácticas (UnADM, 2023).

Este módulo declara, para cada una de las 100 técnicas de la colección
"100 Técnicas Didácticas de Enseñanza y Aprendizaje" (UnADM, 2023), un
CONTRATO DE PRODUCTO que el motor-inteligente usa para preservar la forma
visible solicitada por la consigna y darle protagonismo dentro del documento.

Diseño
------
1. FAMILIAS de producto (``PRODUCT_FAMILIES``): agrupan técnicas que comparten
   la misma lógica de materialización (visual-jerárquico, tabular, temporal,
   escrito-argumentativo, oral-participativo, etc.). Cada familia aporta reglas
   compartidas (estructura de tres actos, layout, criterios de cierre) para no
   repetir texto en las 100 técnicas.
2. CATÁLOGO base (``_CATALOG_BASE``): los 100 registros mínimos tomados del
   catálogo LaTeX local (No., nombre oficial, nivel cognitivo Anderson &
   Krathwohl, familia, forma de producto, elementos visibles obligatorios y
   aliases de detección).
3. CONTRATOS DETALLADOS (``_DETAILED_CONTRACTS``): las técnicas que ya tenían
   reglas ricas y validadas en producción (mapa conceptual, cuadro comparativo,
   cuestionario, estudio de casos, foro) conservan su contrato completo; se
   fusionan por encima de la base.

El diccionario final exportado es ``TECHNIQUE_CONTRACTS`` (id canónico ->
contrato ya fusionado con su familia). ``activity_contract.py`` lo re-exporta
como ``DIDACTIC_TECHNIQUE_CONTRACTS`` para no romper importaciones existentes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# 1) Familias de producto: reglas compartidas por tipo de materialización.
# ---------------------------------------------------------------------------

# Regla transversal: aplica a TODAS las técnicas, se herede o no de la familia.
# Medida sobre los PDF del repo: el pie izquierdo arranca en x=72pt y el bloque
# derecho (\coursecode + \coursename) en x=395.2pt. Pasar de ~62 caracteres
# solapa ambos bloques (Garantías A6 llegaba a x=433.4: 38pt de invasión).
METADATA_LENGTH_RULE = (
    "PIE DE PÁGINA: la plantilla compone el pie izquierdo con \\documentsubtitle y, si está vacío, con "
    "\\documenttitle; a la derecha imprime \\coursecode + \\coursename. Ambos bloques van en la MISMA línea y "
    "NO se recortan solos. RANGO OBLIGATORIO para \\documentsubtitle (o \\documenttitle cuando no hay subtítulo): "
    "entre 28 y 68 caracteres contando espacios. Pasando de 68 los bloques se SOLAPAN; por debajo de 28 el pie "
    "queda pobre y desaprovecha el ancho. El subtítulo debe ACOTAR el objeto del trabajo, no repetir el título ni "
    "reducirse a una etiqueta. Si el título temático necesita más extensión, dejarlo completo en \\documenttitle: "
    "es el SUBTÍTULO, no el título, lo que viaja al pie. Verificación objetiva: el bloque izquierdo del pie no debe "
    "rebasar x=395pt en carta vertical."
)

PRODUCT_FAMILIES: dict[str, dict[str, Any]] = {
    "visual_jerarquico": {
        "label": "Producto visual jerárquico (mapas, esquemas, árboles, redes)",
        "materialization": "Construir con TikZ jerárquico o radial. Jerarquizar del concepto raíz a subconceptos, con conectores etiquetados donde aplique. Escalar con \\resizebox para llenar la página sin desbordar; usar landscape si el ancho lo exige.",
        "structure_rule": "Tres actos: Introducción, un Desarrollo con título temático (NO 'Desarrollo') y Conclusiones. El producto visual es el NÚCLEO del desarrollo: el texto lo prepara antes (marco breve) y lo interpreta después (lectura de ramas/relaciones).",
        "layout_rule": "El diagrama va en su propia página (landscape si es ancho), con su caption. No dejar media página en blanco antes del diagrama: llenar con la guía de lectura o iniciar la sección con \\clearpage.",
        "closure_rule": "La conclusión inicia con \\clearpage, integra síntesis y postura personal; la declaración de uso de IA se liga como \\footnote a una frase oportuna.",
    },
    "tabular": {
        "label": "Producto tabular (cuadros, matrices, tablas comparativas)",
        "materialization": "Construir con longtable/tabular; usar landscape, footnotesize, tabcolsep y arraystretch cuando el contenido sea amplio. Encabezados claros, filas completas y una guía de lectura de columnas.",
        "structure_rule": "Tres actos: Introducción, Desarrollo con título temático y Conclusiones. La tabla/cuadro es el NÚCLEO del desarrollo: marco breve antes, análisis derivado (semejanzas/diferencias) después.",
        "layout_rule": "La tabla va en landscape en su propia página, con la tabla y su caption juntos en una sola página. Compactar con \\arraystretch<=1.2 y caption en \\footnotesize. No dejar hueco antes del salto a landscape.",
        "closure_rule": "El análisis derivado y la postura se cierran en la conclusión (\\clearpage, preferentemente una página). Declaración de IA como \\footnote.",
    },
    "temporal": {
        "label": "Producto temporal (líneas de tiempo, cronologías)",
        "materialization": "Construir con TikZ: línea horizontal con hitos alternados arriba/abajo, fecha + evento breve + causa/consecuencia. Cronología ilustrada admite iconos.",
        "structure_rule": "Tres actos. La línea de tiempo es el NÚCLEO del desarrollo: contexto antes, lectura histórica (tendencias, rupturas, continuidades) después.",
        "layout_rule": "La línea va en su propia página (landscape si abarca muchos hitos), con caption. No dejar hueco antes del diagrama.",
        "closure_rule": "Conclusión con \\clearpage e interpretación histórica propia. Declaración de IA como \\footnote.",
    },
    "diagrama_relacional": {
        "label": "Producto diagramático relacional (Venn, Gowin, flujo, procesos)",
        "materialization": "Construir con TikZ (shapes.geometric, flechas Stealth). Rombos para decisiones, rectángulos para acciones, círculos para conjuntos, V para Gowin. Etiquetar relaciones.",
        "structure_rule": "Tres actos. El diagrama es el NÚCLEO del desarrollo: marco/planteamiento antes, lectura del diagrama (qué muestra cada zona/paso) después.",
        "layout_rule": "El diagrama va en su propia página, con caption. No dejar hueco previo.",
        "closure_rule": "Conclusión con \\clearpage y postura. Declaración de IA como \\footnote.",
    },
    "cuantitativo": {
        "label": "Producto cuantitativo (histograma, gráfico estadístico)",
        "materialization": "Construir con pgfplots/tikzpicture. Declarar variable, fuente, escala y unidades. PROHIBIDO inventar cifras: sin datos confiables no se usa gráfico como decoración.",
        "structure_rule": "Tres actos. El gráfico es el NÚCLEO del desarrollo: definición de datos y método antes, lectura del dato (qué informa) después.",
        "layout_rule": "El gráfico va con caption y fuente citada; no dejar hueco previo.",
        "closure_rule": "Conclusión con \\clearpage e interpretación del dato. Declaración de IA como \\footnote.",
    },
    "escrito_expositivo": {
        "label": "Producto escrito expositivo (resumen, informe, reporte, monografía, artículo, reseña)",
        "materialization": "Documento en prosa con estructura: introducción con problema, desarrollo con fuentes y análisis, conclusión con postura, referencias APA 7. La voz convierte información en criterio; evitar texto enciclopédico.",
        "structure_rule": "Tres actos con títulos temáticos. El desarrollo integra marco, análisis y aplicación en una sola sección cuyo título nombra el tema.",
        "layout_rule": "No requiere TikZ salvo figuras. Cuidar densidad de página y saltos limpios.",
        "closure_rule": "Conclusión con \\clearpage, síntesis y postura (posición, razón, consecuencia). Declaración de IA como \\footnote.",
    },
    "escrito_argumentativo": {
        "label": "Producto escrito argumentativo (ensayo, suasoria, artículo de opinión)",
        "materialization": "Texto con tesis clara, argumentos con evidencia citada, contraargumento y refutación, cierre con postura. Cada párrafo cumple una función: presentar, explicar, comparar, valorar o concluir.",
        "structure_rule": "Tres actos: introducción con tesis, desarrollo argumentativo (una sección temática), conclusión que reafirma la postura.",
        "layout_rule": "Prosa; figuras solo si aportan. Saltos limpios y densidad adecuada.",
        "closure_rule": "Conclusión con \\clearpage que reafirma la tesis. Declaración de IA como \\footnote.",
    },
    "sintesis_lectura": {
        "label": "Producto de síntesis de lectura (reporte de lectura, sumillado, exegética, sesión bibliográfica)",
        "materialization": "Demostrar comprensión del texto fuente: tesis, argumentos, conceptos clave, límites y lectura personal. Citar correctamente; no sustituir por paráfrasis superficial.",
        "structure_rule": "Tres actos. El desarrollo identifica tesis y argumentos del texto y agrega lectura crítica.",
        "layout_rule": "Prosa o ficha estructurada; puede usar tabla para fichas por fuente.",
        "closure_rule": "Conclusión con \\clearpage y valoración propia. Declaración de IA como \\footnote.",
    },
    "oral_participativo": {
        "label": "Producto oral/participativo materializado por escrito (foro, debate, panel, mesa redonda, simposio)",
        "materialization": "Materializar como bloque de participación (sourcecode/listings o tcolorbox) que reproduce literalmente lo publicado/expuesto: apertura, postura con evidencia citada, y cierre que invita al diálogo. El texto debe ser seleccionable y copiable en el PDF.",
        "structure_rule": "Tres actos. La participación publicada es el NÚCLEO del desarrollo, como subsección: marco/preguntas guía antes, lectura breve después.",
        "layout_rule": "Bloque con breaklines para texto largo, sin numerar líneas de continuación. Cada participación en una sola línea lógica del fuente.",
        "apa_citation_rule": "La participación debe integrar al menos una cita textual (entrecomillada) con referencia APA 7 dentro del propio bloque; al final, apartado 'Referencias' con sangría francesa listando todas las fuentes citadas en el bloque.",
        "closure_rule": "Conclusión con \\clearpage, síntesis y postura. Declaración de IA como \\footnote.",
    },
    "argumentativo_estructurado": {
        "label": "Producto argumentativo estructurado (controversia, discusión de gabinete, análisis y consensos)",
        "materialization": "Estructurar posturas: tesis, antítesis y síntesis; o acuerdos y disensos en matriz. Cada postura con evidencia y su valoración.",
        "structure_rule": "Tres actos. El desarrollo confronta posturas y deriva una síntesis argumentada.",
        "layout_rule": "Puede combinar prosa y tabla de posturas.",
        "closure_rule": "Conclusión con \\clearpage y postura razonada. Declaración de IA como \\footnote.",
    },
    "analisis_caso": {
        "label": "Producto de análisis de caso/hechos (estudio de casos, análisis de hechos, noticia falsa)",
        "materialization": "Distinguir hecho, interpretación, norma/principio, problema y solución. Trabajar con hechos verificables; contrastar fuentes cuando aplique.",
        "structure_rule": "Tres actos: hechos y problema en el planteamiento, análisis con criterios en el desarrollo, resolución en la conclusión.",
        "layout_rule": "Prosa estructurada; puede apoyarse en tabla de hechos-causas-consecuencias.",
        "closure_rule": "Conclusión con \\clearpage, postura y consecuencia. Declaración de IA como \\footnote.",
    },
    "instrumento_recoleccion": {
        "label": "Producto de recolección (entrevista, encuesta, consulta pública, grupos focales)",
        "materialization": "Declarar objetivo, participantes, instrumento (guion/cuestionario), resultados y análisis. Materializar el instrumento y una matriz o gráfica de hallazgos.",
        "structure_rule": "Tres actos: objetivo y método antes, instrumento y resultados en el desarrollo, hallazgos en la conclusión.",
        "layout_rule": "Instrumento en tabla/lista; resultados en tabla o gráfica con fuente.",
        "closure_rule": "Conclusión con \\clearpage y hallazgos interpretados. Declaración de IA como \\footnote.",
    },
    "reactivo_evaluativo": {
        "label": "Producto de reactivos (cuestionario, preguntas dirigidas, examen práctico, preguntas y premios)",
        "materialization": "Conservar reactivos, respuestas y justificaciones en tabla compacta o lista estructurada; no transformar en ensayo salvo consigna expresa.",
        "structure_rule": "Tres actos. El banco de reactivos es el NÚCLEO del desarrollo con su título; marco integrado en la misma sección.",
        "layout_rule": "Tabla/lista compacta; longtable si es extenso.",
        "closure_rule": "Conclusión con \\clearpage, análisis propio y postura. Declaración de IA como \\footnote.",
    },
    "reflexivo_bitacora": {
        "label": "Producto reflexivo/bitácora (diario de aprendizaje, journal, SQA, portafolio)",
        "materialization": "Mostrar trayectoria y reflexión sobre el proceso, no acumulación. SQA usa tabla sé/quiero/aprendí; portafolio usa índice de evidencias con explicación de cada una.",
        "structure_rule": "Tres actos. El desarrollo muestra evidencias/entradas con reflexión de aprendizaje.",
        "layout_rule": "Tabla o lista estructurada; portafolio con índice.",
        "closure_rule": "Conclusión con \\clearpage, aprendizaje y correcciones. Declaración de IA como \\footnote.",
    },
    "comunicativo_visual": {
        "label": "Producto comunicativo visual (cartel, afiche, anuncio, fotomontaje, historieta)",
        "materialization": "Si la entrega es PDF, construir con TikZ (cartel/afiche/viñetas). Definir objetivo, público, mensaje central, jerarquía visual y fuentes. No saturar de texto.",
        "structure_rule": "Tres actos. La pieza comunicativa es el NÚCLEO del desarrollo: encuadre antes, lectura del mensaje después.",
        "layout_rule": "La pieza en su propia página con caption; no saturar ni dejar hueco previo.",
        "closure_rule": "Conclusión con \\clearpage y justificación del diseño. Declaración de IA como \\footnote.",
    },
    "audiovisual_guion": {
        "label": "Producto audiovisual con guion (videocápsula, documentales, social media, reportaje, visitas 360)",
        "materialization": "Materializar guion + storyboard/secuencia; si hay video, incluir enlace, captura y justificación. Definir objetivo, público y mensaje.",
        "structure_rule": "Tres actos. El guion/storyboard es el NÚCLEO del desarrollo: planteamiento antes, lectura del recorrido después.",
        "layout_rule": "Guion en bloque estructurado; storyboard en tabla o figura.",
        "closure_rule": "Conclusión con \\clearpage y justificación. Declaración de IA como \\footnote.",
    },
    "dramatizacion_simulacion": {
        "label": "Producto de dramatización/simulación (juego de roles, sociodrama, simulación, juego de negocios, taller)",
        "materialization": "Materializar por escrito: problema, roles, reglas, escena/dinámica, decisiones, resultados y reflexión.",
        "structure_rule": "Tres actos. El guion/dinámica es el NÚCLEO del desarrollo: contexto antes, resultados y aprendizaje después.",
        "layout_rule": "Guion estructurado; tabla de roles/decisiones cuando aplique.",
        "closure_rule": "Conclusión con \\clearpage, resultados y aprendizaje. Declaración de IA como \\footnote.",
    },
    "estrategia_cognitiva": {
        "label": "Producto de estrategia cognitiva (Feynman, mnemotecnia, Scamper, pensamiento analógico, heurística de Bruner, autoexplicación, ejemplificación, atributos, práctica distribuida, estudio intercalado, instrucción personalizada)",
        "materialization": "Materializar la estrategia como secuencia o matriz explícita (p. ej. Scamper: sustituir/combinar/adaptar; Feynman: explicación simple + prueba; analogía: origen->destino). Mostrar el procedimiento, no solo el resultado.",
        "structure_rule": "Tres actos. La aplicación de la estrategia es el NÚCLEO del desarrollo: concepto antes, transferencia/prueba después.",
        "layout_rule": "Tabla, secuencia o lista clasificada según la estrategia.",
        "closure_rule": "Conclusión con \\clearpage y valoración del método. Declaración de IA como \\footnote.",
    },
    "colaborativo_proyecto": {
        "label": "Producto colaborativo/proyecto (trabajo cooperativo, proyectos colaborativos, socioaprendizaje, rompecabezas, tablón de anuncios, Phillips 66, diálogos simultáneos, pensamiento de diseño)",
        "materialization": "Materializar plan de roles/evidencias, o el producto integrado por piezas. Pensamiento de diseño usa fases empatizar-definir-idear-prototipar-evaluar.",
        "structure_rule": "Tres actos. El plan o producto integrado es el NÚCLEO del desarrollo.",
        "layout_rule": "Tabla de roles/evidencias o secuencia de fases.",
        "closure_rule": "Conclusión con \\clearpage y aprendizaje colaborativo. Declaración de IA como \\footnote.",
    },
    "creativo_narrativo": {
        "label": "Producto creativo/narrativo (poesía lírica, fábula, descripción de personaje, testimonio)",
        "materialization": "Materializar el producto creativo y acompañarlo de una reflexión que lo vincule al contenido temático. Fábula con moraleja; descripción con perfil estructurado.",
        "structure_rule": "Tres actos. El producto creativo es el NÚCLEO del desarrollo: encuadre antes, reflexión temática después.",
        "layout_rule": "Texto creativo en bloque; reflexión en prosa.",
        "closure_rule": "Conclusión con \\clearpage y vínculo con el aprendizaje. Declaración de IA como \\footnote.",
    },
    "expositivo_oral": {
        "label": "Producto expositivo oral con soporte (exposición oral, demostración silenciosa)",
        "materialization": "Materializar guion de exposición o secuencia visual de la demostración: objetivo, puntos clave, apoyos y cierre.",
        "structure_rule": "Tres actos. El guion/secuencia es el NÚCLEO del desarrollo.",
        "layout_rule": "Guion estructurado; secuencia en figura o lista.",
        "closure_rule": "Conclusión con \\clearpage y síntesis. Declaración de IA como \\footnote.",
    },
    "analisis_textual": {
        "label": "Producto de análisis textual (análisis de contenido, estructuras textuales, análisis de tergiversación)",
        "materialization": "Materializar matriz de análisis: unidad de texto, idea, función y crítica; o afirmación/evidencia/corrección para tergiversación.",
        "structure_rule": "Tres actos. La matriz de análisis es el NÚCLEO del desarrollo.",
        "layout_rule": "Tabla/matriz de análisis; landscape si es amplia.",
        "closure_rule": "Conclusión con \\clearpage y lectura crítica. Declaración de IA como \\footnote.",
    },
}


# ---------------------------------------------------------------------------
# 2) Catálogo base: los 100 registros (fuente: catálogo LaTeX local UnADM 2023).
#    Campos: (id, no, nombre_oficial, nivel, familia, product_form,
#             required_visible_elements, aliases)
# ---------------------------------------------------------------------------

_CATALOG_BASE: tuple[tuple[Any, ...], ...] = (
    ("cuadro_comparativo", 1, "Cuadro comparativo", "Sintetizar", "tabular", "Longtable o matriz TikZ", ("título", "encabezados", "filas", "criterio de lectura"), ("cuadro comparativo", "cuadro", "tabla", "longtable", "tabular")),
    ("cuadro_sinoptico", 2, "Cuadro sinóptico", "Sintetizar", "visual_jerarquico", "Árbol jerárquico TikZ", ("tema central", "categorías", "subcategorías", "detalles"), ("cuadro sinóptico", "cuadro sinoptico", "sinóptico", "sinoptico")),
    ("cuestionario", 3, "Cuestionario", "Explicar", "reactivo_evaluativo", "Tabla de preguntas/respuestas", ("pregunta", "respuesta", "justificación"), ("cuestionario", "diagnóstico", "diagnostico", "reactivo")),
    ("debate", 4, "Debate", "Aplicar", "oral_participativo", "Guion argumentativo", ("postura", "argumentos", "contraargumentos", "cierre"), ("debate",)),
    ("diagrama_de_gowin", 5, "Diagrama de Gowin", "Aplicar", "diagrama_relacional", "Diagrama V en TikZ", ("pregunta central", "teoría", "evidencia", "conclusión"), ("gowin", "diagrama de gowin", "uve heurística", "uve heuristica")),
    ("ejemplificacion", 6, "Ejemplificación", "Explicar", "estrategia_cognitiva", "Tabla concepto-ejemplo-aplicación", ("concepto", "ejemplo", "aplicación"), ("ejemplificación", "ejemplificacion")),
    ("entrevista", 7, "Entrevista", "Aplicar", "instrumento_recoleccion", "Guion y matriz de hallazgos", ("objetivo", "guion", "hallazgos"), ("entrevista",)),
    ("esquema", 8, "Esquema", "Sintetizar", "visual_jerarquico", "Cajas jerárquicas TikZ", ("tema", "partes", "relaciones"), ("esquema",)),
    ("glosario_colaborativo", 9, "Glosario colaborativo", "Explicar", "tabular", "Tabla término-definición-fuente", ("término", "definición propia", "fuente", "ejemplo"), ("glosario", "glosario colaborativo")),
    ("historieta", 10, "Historieta", "Recordar", "comunicativo_visual", "Viñetas TikZ o guion", ("viñetas", "secuencia", "mensaje"), ("historieta", "cómic", "comic")),
    ("informe", 11, "Informe", "Sintetizar", "escrito_expositivo", "Documento con secciones", ("introducción", "desarrollo", "conclusión", "referencias"), ("informe",)),
    ("linea_de_tiempo", 12, "Línea de tiempo", "Sintetizar", "temporal", "Timeline TikZ", ("hitos", "fechas", "eventos", "lectura histórica"), ("línea de tiempo", "linea de tiempo", "timeline", "cronología", "cronologia")),
    ("mapa_conceptual", 13, "Mapa conceptual", "Sintetizar", "visual_jerarquico", "Nodos y conectores TikZ", ("conceptos", "relaciones", "lectura explicativa"), ("mapa conceptual",)),
    ("panel_de_discusion", 14, "Panel de discusión", "Aplicar", "oral_participativo", "Tabla de posturas", ("panelistas", "posturas", "síntesis"), ("panel de discusión", "panel de discusion", "panel")),
    ("pensamiento_de_diseno", 15, "Pensamiento de diseño", "Recordar", "colaborativo_proyecto", "Fases empatizar-definir-idear-prototipar-evaluar", ("empatizar", "definir", "idear", "prototipar", "evaluar"), ("pensamiento de diseño", "design thinking", "pensamiento de diseno")),
    ("phillips_66", 16, "Phillips 66", "Aplicar", "colaborativo_proyecto", "Matriz grupo-idea-síntesis", ("grupos", "ideas", "síntesis"), ("phillips 66", "phillips66")),
    ("resumen", 17, "Resumen", "Recordar", "escrito_expositivo", "Texto breve estructurado", ("idea principal", "ideas clave", "síntesis"), ("resumen",)),
    ("simulacion", 18, "Simulación", "Construir", "dramatizacion_simulacion", "Escenario, variables y resultados", ("escenario", "variables", "resultados"), ("simulación", "simulacion")),
    ("sociodrama", 19, "Sociodrama", "Aplicar", "dramatizacion_simulacion", "Guion de escenas", ("roles", "escenas", "reflexión"), ("sociodrama",)),
    ("trabajo_cooperativo", 20, "Trabajo cooperativo", "Aplicar", "colaborativo_proyecto", "Plan de roles y evidencias", ("roles", "tareas", "evidencias"), ("trabajo cooperativo", "aprendizaje cooperativo")),
    ("analisis_de_contenido", 21, "Análisis de contenido", "Analizar", "analisis_textual", "Matriz texto-idea-función-crítica", ("texto", "idea", "función", "crítica"), ("análisis de contenido", "analisis de contenido")),
    ("analisis_de_tergiversacion_textual", 22, "Análisis de tergiversación textual", "Analizar", "analisis_textual", "Tabla afirmación/evidencia/corrección", ("afirmación", "evidencia", "corrección"), ("tergiversación", "tergiversacion", "análisis de tergiversación")),
    ("analisis_y_consensos", 23, "Análisis y consensos", "Analizar", "argumentativo_estructurado", "Matriz de acuerdos y disensos", ("acuerdos", "disensos", "síntesis"), ("análisis y consensos", "analisis y consensos", "consensos")),
    ("autoexplicacion", 24, "Autoexplicación", "Explicar", "estrategia_cognitiva", "Secuencia pregunta-respuesta-criterio", ("pregunta", "respuesta", "criterio"), ("autoexplicación", "autoexplicacion")),
    ("cronologia_ilustrada", 25, "Cronología ilustrada", "Construir", "temporal", "Línea de tiempo con iconos", ("hitos", "iconos", "eventos", "lectura"), ("cronología ilustrada", "cronologia ilustrada")),
    ("estructuras_textuales", 26, "Estructuras textuales", "Analizar", "analisis_textual", "Mapa de estructura argumentativa", ("estructura", "argumentos", "relaciones"), ("estructuras textuales",)),
    ("estudio_de_caso", 27, "Estudio de casos", "Explicar", "analisis_caso", "Hechos-problema-norma-solución", ("hechos", "análisis", "conclusión"), ("estudio de caso", "estudio de casos", "análisis de caso", "analisis de caso", "análisis de casos")),
    ("exposicion_oral", 28, "Exposición oral", "Aplicar", "expositivo_oral", "Guion o diapositivas", ("objetivo", "puntos clave", "cierre"), ("exposición oral", "exposicion oral")),
    ("foro", 29, "Foro", "Aplicar", "oral_participativo", "Entrada, réplica y cierre", ("preguntas guía", "respuesta", "participación textual publicada", "cierre"), ("foro", "foro diagnóstico", "foro diagnostico", "participación en foro", "participacion en foro")),
    ("grupos_de_discusion", 30, "Grupos de discusión", "Aplicar", "oral_participativo", "Matriz de aportaciones", ("participantes", "aportaciones", "síntesis"), ("grupos de discusión", "grupos de discusion")),
    ("grupos_focales", 31, "Grupos focales", "Explicar", "instrumento_recoleccion", "Guion y síntesis de hallazgos", ("guion", "participantes", "hallazgos"), ("grupos focales", "grupo focal", "focus group")),
    ("mapa_de_cajas", 32, "Mapa de cajas", "Sintetizar", "visual_jerarquico", "Cajas agrupadas TikZ", ("cajas", "agrupaciones", "relaciones"), ("mapa de cajas",)),
    ("mapa_mental", 33, "Mapa mental", "Explicar", "visual_jerarquico", "Nodos radiales TikZ", ("idea central", "ramas", "subramas"), ("mapa mental",)),
    ("monografia", 34, "Monografía", "Explicar", "escrito_expositivo", "Documento de investigación", ("introducción", "desarrollo", "conclusión", "referencias"), ("monografía", "monografia")),
    ("preguntas_y_premios", 35, "Preguntas y premios", "Recordar", "reactivo_evaluativo", "Banco de reactivos", ("preguntas", "respuestas", "puntaje"), ("preguntas y premios",)),
    ("reporte_de_lectura_general", 36, "Reporte de lectura general", "Explicar", "sintesis_lectura", "Ficha de lectura ampliada", ("tesis", "argumentos", "lectura personal"), ("reporte de lectura", "reporte de lectura general")),
    ("resena", 37, "Reseña", "Sintetizar", "sintesis_lectura", "Valoración crítica breve", ("descripción", "valoración", "postura"), ("reseña", "resena")),
    ("rompecabezas", 38, "Rompecabezas", "Construir", "colaborativo_proyecto", "Integración por piezas", ("piezas", "integración", "producto"), ("rompecabezas", "jigsaw")),
    ("sumillado", 39, "Sumillado", "Sintetizar", "sintesis_lectura", "Texto con notas marginales", ("texto fuente", "sumillas", "síntesis"), ("sumillado", "sumilla")),
    ("testimonio", 40, "Testimonio", "Recordar", "creativo_narrativo", "Entrevista y relato analizado", ("relato", "análisis", "vínculo temático"), ("testimonio",)),
    ("consulta_publica", 41, "Consulta pública", "Aplicar", "instrumento_recoleccion", "Instrumento y matriz de resultados", ("instrumento", "resultados", "análisis"), ("consulta pública", "consulta publica")),
    ("controversia_estructurada", 42, "Controversia estructurada", "Analizar", "argumentativo_estructurado", "Tesis, antítesis y síntesis", ("tesis", "antítesis", "síntesis"), ("controversia estructurada", "controversia")),
    ("debate_publico", 43, "Debate público", "Aplicar", "oral_participativo", "Guion de argumentación", ("postura", "argumentos", "réplica", "cierre"), ("debate público", "debate publico")),
    ("diagrama_de_venn", 44, "Diagrama de Venn", "Analizar", "diagrama_relacional", "Círculos TikZ", ("conjuntos", "intersección", "diferencias"), ("diagrama de venn", "venn")),
    ("diario_de_aprendizaje", 45, "Diario de aprendizaje", "Recordar", "reflexivo_bitacora", "Bitácora reflexiva", ("entradas", "reflexión", "aprendizaje"), ("diario de aprendizaje", "bitácora de aprendizaje")),
    ("discusion_de_gabinete", 46, "Discusión de gabinete", "Analizar", "argumentativo_estructurado", "Tabla de roles y decisiones", ("roles", "posturas", "decisiones"), ("discusión de gabinete", "discusion de gabinete")),
    ("documentales", 47, "Documentales", "Explicar", "audiovisual_guion", "Guion audiovisual", ("objetivo", "guion", "fuentes"), ("documental", "documentales")),
    ("encuesta_interactiva", 48, "Encuesta interactiva", "Aplicar", "instrumento_recoleccion", "Instrumento y gráfica", ("instrumento", "resultados", "gráfica"), ("encuesta interactiva", "encuesta")),
    ("ensayo", 49, "Ensayo", "Construir", "escrito_argumentativo", "Texto argumentativo", ("tesis", "argumentos", "postura"), ("ensayo",)),
    ("estudio_de_noticia_falsa", 50, "Estudio de noticia falsa", "Analizar", "analisis_caso", "Verificación y contraste de fuentes", ("afirmación", "verificación", "contraste"), ("noticia falsa", "estudio de noticia falsa", "fake news")),
    ("exegetica", 51, "Exegética", "Recordar", "sintesis_lectura", "Interpretación textual guiada", ("texto", "interpretación", "contexto"), ("exegética", "exegetica", "exégesis", "exegesis")),
    ("fabula", 52, "Fábula", "Recordar", "creativo_narrativo", "Narración con moraleja", ("narración", "moraleja", "vínculo temático"), ("fábula", "fabula")),
    ("heuristica_de_bruner", 53, "Heurística de Bruner", "Analizar", "estrategia_cognitiva", "Ruta descubrimiento-concepto", ("descubrimiento", "concepto", "transferencia"), ("heurística de bruner", "heuristica de bruner", "bruner")),
    ("histograma", 54, "Histograma", "Analizar", "cuantitativo", "Gráfico de frecuencias", ("variable", "frecuencias", "fuente", "lectura"), ("histograma",)),
    ("pensamiento_analogico", 55, "Pensamiento analógico", "Aplicar", "estrategia_cognitiva", "Analogía y transferencia", ("origen", "destino", "transferencia"), ("pensamiento analógico", "pensamiento analogico", "analogía", "analogia")),
    ("poesia_lirica", 56, "Poesía lírica", "Construir", "creativo_narrativo", "Producto creativo con reflexión", ("poema", "recursos", "reflexión"), ("poesía lírica", "poesia lirica", "poema")),
    ("sesion_bibliografica", 57, "Sesión bibliográfica", "Analizar", "sintesis_lectura", "Fichas por fuente", ("fuentes", "fichas", "síntesis"), ("sesión bibliográfica", "sesion bibliografica")),
    ("sqa", 58, "SQA", "Recordar", "reflexivo_bitacora", "Tabla sé-quiero-aprendí", ("sé", "quiero saber", "aprendí"), ("sqa", "s q a", "sé quiero aprendí")),
    ("suasoria", 59, "Suasoria", "Aplicar", "escrito_argumentativo", "Discurso persuasivo", ("tesis", "argumentos persuasivos", "cierre"), ("suasoria",)),
    ("tablon_de_anuncios", 60, "Tablón de anuncios", "Sintetizar", "colaborativo_proyecto", "Muro informativo o tablero", ("mensajes", "categorías", "síntesis"), ("tablón de anuncios", "tablon de anuncios", "muro")),
    ("afiche", 61, "Afiche", "Explicar", "comunicativo_visual", "Cartel breve en TikZ", ("mensaje central", "jerarquía visual", "fuentes"), ("afiche",)),
    ("analisis_de_hechos", 62, "Análisis de hechos", "Analizar", "analisis_caso", "Contexto-datos-tiempo-sitio-factores-síntesis", ("contexto", "clasificación de datos", "tiempo", "sitio", "factores", "síntesis"), ("análisis de hechos", "analisis de hechos")),
    ("anuncio_publicitario", 63, "Anuncio publicitario", "Explicar", "comunicativo_visual", "Pieza persuasiva", ("mensaje", "público", "persuasión"), ("anuncio publicitario", "anuncio")),
    ("atributos", 64, "Atributos", "Explicar", "estrategia_cognitiva", "Tabla de cualidades", ("objeto", "atributos", "valoración"), ("atributos", "lista de atributos")),
    ("diagrama_de_flujo", 65, "Diagrama de flujo", "Sintetizar", "diagrama_relacional", "Flujo TikZ", ("inicio", "pasos", "decisiones", "fin"), ("diagrama de flujo", "flujograma", "flowchart")),
    ("dialogos_simultaneos", 66, "Diálogos simultáneos", "Aplicar", "colaborativo_proyecto", "Guion de interacción", ("parejas", "diálogo", "síntesis"), ("diálogos simultáneos", "dialogos simultaneos", "cuchicheo")),
    ("feynman", 67, "Feynman", "Explicar", "estrategia_cognitiva", "Explicación simple y prueba", ("concepto", "explicación simple", "prueba"), ("feynman", "técnica feynman")),
    ("grafico_estadistico", 68, "Gráfico estadístico", "Analizar", "cuantitativo", "Gráfico con fuente", ("variable", "datos", "fuente", "lectura"), ("gráfico estadístico", "grafico estadistico", "gráfica")),
    ("lluvia_de_ideas_dirigida", 69, "Lluvia de ideas dirigida", "Explicar", "colaborativo_proyecto", "Mapa radial o lista clasificada", ("tema", "ideas", "clasificación"), ("lluvia de ideas", "brainstorming", "lluvia de ideas dirigida")),
    ("mapa_semantico", 70, "Mapa semántico", "Sintetizar", "visual_jerarquico", "Red de significados TikZ", ("concepto", "campos", "relaciones"), ("mapa semántico", "mapa semantico")),
    ("mapeo_de_procesos", 71, "Mapeo de procesos", "Analizar", "diagrama_relacional", "Proceso entrada-salida", ("entrada", "proceso", "control", "salida"), ("mapeo de procesos", "mapa de procesos")),
    ("mesa_redonda_con_interrogador", 72, "Mesa redonda con interrogador", "Aplicar", "oral_participativo", "Matriz de preguntas/posturas", ("preguntas", "posturas", "síntesis"), ("mesa redonda", "mesa redonda con interrogador")),
    ("mnemotecnia", 73, "Mnemotecnia", "Recordar", "estrategia_cognitiva", "Reglas de memoria", ("contenido", "regla mnemotécnica", "aplicación"), ("mnemotecnia", "regla mnemotécnica", "regla mnemotecnica")),
    ("portafolio_de_evidencias_digital", 74, "Portafolio de evidencias digital", "Construir", "reflexivo_bitacora", "Índice de evidencias", ("índice", "evidencias", "reflexión"), ("portafolio", "portafolio de evidencias", "portafolio digital")),
    ("redes_conceptuales", 75, "Redes conceptuales", "Sintetizar", "visual_jerarquico", "Grafo TikZ", ("nodos", "relaciones", "lectura"), ("redes conceptuales", "red conceptual")),
    ("reporte_de_investigacion", 76, "Reporte de investigación", "Explicar", "escrito_expositivo", "Documento con método", ("problema", "método", "resultados", "conclusión"), ("reporte de investigación", "reporte de investigacion", "reporte investigativo", "investigación documental", "investigacion documental", "reporte académico", "reporte academico", "informe de investigación", "informe de investigacion")),
    ("simposio", 77, "Simposio", "Aplicar", "oral_participativo", "Programa y síntesis", ("ponencias", "programa", "síntesis"), ("simposio",)),
    ("socioaprendizaje", 78, "Socioaprendizaje", "Aplicar", "colaborativo_proyecto", "Comunidad y evidencias", ("comunidad", "interacción", "evidencias"), ("socioaprendizaje", "aprendizaje social", "wiki", "wiki colaborativa", "wiki de la plataforma", "contribución a la wiki", "contribucion a la wiki", "participación en wiki", "participacion en wiki")),
    ("tuits", 79, "Tuits", "Sintetizar", "audiovisual_guion", "Microargumentos", ("mensaje breve", "hashtags", "síntesis"), ("tuits", "tweet", "microblogging")),
    ("valoracion_de_decisiones", 80, "Valoración de decisiones", "Analizar", "tabular", "Matriz ponderada", ("alternativas", "criterios", "pesos", "decisión"), ("valoración de decisiones", "valoracion de decisiones", "matriz de decisión")),
    ("articulo", 81, "Artículo", "Analizar", "escrito_expositivo", "Texto con tesis y fuentes", ("tesis", "desarrollo", "fuentes"), ("artículo", "articulo")),
    ("cartel", 82, "Cartel", "Explicar", "comunicativo_visual", "Cartel TikZ", ("mensaje central", "jerarquía visual", "fuentes"), ("cartel", "póster", "poster")),
    ("demostracion_silenciosa", 83, "Demostración silenciosa", "Aplicar", "expositivo_oral", "Secuencia visual", ("pasos", "secuencia", "resultado"), ("demostración silenciosa", "demostracion silenciosa")),
    ("descripcion_de_un_personaje", 84, "Descripción de un personaje", "Aplicar", "creativo_narrativo", "Perfil estructurado", ("personaje", "rasgos", "análisis"), ("descripción de un personaje", "descripcion de un personaje")),
    ("estudio_intercalado", 85, "Estudio intercalado", "Aplicar", "estrategia_cognitiva", "Plan de estudio espaciado", ("temas", "intercalado", "calendario"), ("estudio intercalado", "intercalado")),
    ("examen_practico", 86, "Examen práctico", "Aplicar", "reactivo_evaluativo", "Evidencia de ejecución", ("tarea", "ejecución", "evidencia"), ("examen práctico", "examen practico")),
    ("fotomontaje_digital", 87, "Fotomontaje digital", "Construir", "comunicativo_visual", "Composición visual justificada", ("composición", "mensaje", "justificación"), ("fotomontaje", "fotomontaje digital")),
    ("instruccion_personalizada", 88, "Instrucción personalizada", "Analizar", "estrategia_cognitiva", "Ruta de aprendizaje individual", ("diagnóstico", "ruta", "seguimiento"), ("instrucción personalizada", "instruccion personalizada")),
    ("journal_digital", 89, "Journal digital", "Construir", "reflexivo_bitacora", "Bitácora digital", ("entradas", "reflexión", "evidencias"), ("journal digital", "journal", "diario digital", "diario_digital")),
    ("juego_de_negocios", 90, "Juego de negocios", "Analizar", "dramatizacion_simulacion", "Simulación estratégica", ("escenario", "decisiones", "resultados"), ("juego de negocios", "business game")),
    ("juego_de_roles", 91, "Juego de roles", "Aplicar", "dramatizacion_simulacion", "Guion de roles", ("roles", "escena", "reflexión"), ("juego de roles", "role play", "roleplay")),
    ("practica_distribuida", 92, "Práctica distribuida", "Aplicar", "estrategia_cognitiva", "Calendario de práctica", ("temas", "sesiones", "calendario"), ("práctica distribuida", "practica distribuida")),
    ("preguntas_dirigidas", 93, "Preguntas dirigidas", "Construir", "reactivo_evaluativo", "Banco de preguntas guía", ("preguntas guía", "objetivo", "respuestas esperadas"), ("preguntas dirigidas",)),
    ("proyectos_colaborativos", 94, "Proyectos colaborativos", "Construir", "colaborativo_proyecto", "Plan de proyecto", ("objetivo", "roles", "entregables"), ("proyectos colaborativos", "proyecto colaborativo", "abp")),
    ("reportaje", 95, "Reportaje", "Construir", "audiovisual_guion", "Investigación narrativa", ("tema", "investigación", "narrativa"), ("reportaje",)),
    ("scamper", 96, "Scamper", "Recordar", "estrategia_cognitiva", "Matriz sustituir-combinar-adaptar", ("sustituir", "combinar", "adaptar", "modificar", "otros usos", "eliminar", "reordenar"), ("scamper",)),
    ("social_media", 97, "Social media", "Aplicar", "audiovisual_guion", "Estrategia de publicación", ("objetivo", "contenido", "calendario"), ("social media", "redes sociales", "medios sociales", "medios_sociales")),
    ("taller", 98, "Taller", "Aplicar", "dramatizacion_simulacion", "Secuencia de actividades", ("objetivo", "actividades", "productos"), ("taller",)),
    ("videocapsula", 99, "Videocápsula", "Sintetizar", "audiovisual_guion", "Guion y storyboard", ("guion", "storyboard", "mensaje"), ("videocápsula", "videocapsula", "cápsula de video")),
    ("visitas_guiadas_virtuales_360", 100, "Visitas guiadas virtuales 360", "Construir", "audiovisual_guion", "Guion, secuencia y recorrido", ("guion", "secuencia", "recorrido"), ("visitas guiadas", "visita virtual 360", "recorrido 360")),
)


# ---------------------------------------------------------------------------
# 3) Contratos detallados (reglas ricas validadas en producción). Se fusionan
#    por encima de la base + familia. Aquí van SOLO las técnicas que requieren
#    reglas propias más finas que las de su familia.
# ---------------------------------------------------------------------------

_DETAILED_CONTRACTS: dict[str, dict[str, Any]] = {
    "analisis_de_hechos": {
        "materialization": (
            "Informe de hechos verificables: contexto y problema; clasificacion de datos por actores y documentos; "
            "tiempo y sitio de los acontecimientos; factores sociales y politicos; interpretacion contrastada y "
            "alternativas historicas justificadas; sintesis de consecuencias. Separar expresamente evidencia, "
            "inferencia e hipotesis contrafactual; no atribuir causalidad o recepcion intelectual solo por semejanza."
        ),
        "structure_rule": (
            "Tres actos: introduccion con acontecimiento, lugar, periodo y problema; un desarrollo de titulo tematico "
            "que ordena datos, tiempo, sitio y factores, confronta interpretaciones y examina alternativas; "
            "conclusiones con sintesis de hechos, postura critica y consecuencias. Los seis elementos oficiales "
            "se integran, no se imponen seis secciones ni un numero fijo de casos."
        ),
        "layout_rule": "Informe en prosa con subtitulos breves cuando ayuden; tabla opcional, nunca sustituto del analisis.",
        "evidence_rule": (
            "Citar documentos primarios y estudios comprobados con numerales/capitulos/paginas cuando corresponda; "
            "declarar cuando la evidencia no permite afirmar influencia directa, intenciones o desenlaces alternativos."
        ),
    },
    "cuestionario": {
        "visible_style_rule": "No explicar en el texto visible que 'esta actividad' usa una técnica; si hace falta, dejar el criterio de organización o herramienta didáctica como comentario TEX y hablar del tema o del cuestionario.",
        "structure_rule": "Integrar contexto y problema en la introducción; si el producto es cuestionario, Desarrollo debe contener el cuestionario con su título y el marco conceptual debe integrarse dentro de la misma sección; nivel cognitivo aplicado va comentado salvo consigna expresa.",
        "closure_rule": "Integrar análisis propio y postura personal en la conclusión, con posición, razón y consecuencia.",
    },
    "mapa_conceptual": {
        "depth_rule": (
            "Un mapa conceptual sólido no puede ser esquelético: exige raíz + ramas del contenido temático + varios niveles de "
            "profundidad (subconceptos, subtipos, ejemplos, fundamentos y consecuencias). Cada rama debe tener al menos 3-4 conceptos; "
            "cubrir explícitamente todos los subtemas de la planeación sin omitir ninguno."
        ),
        "relations_rule": (
            "Las flechas deben llevar proposiciones de enlace explícitas (conectores como 'se rige por', 'se hace efectivo con', "
            "'se clasifica en') y deben existir relaciones cruzadas entre ramas que evidencien interdependencia."
        ),
        "graphic_rule": (
            "Construir el diagrama con TikZ jerárquico. Apilar subconceptos DEBAJO de la cola de cada rama (below= del último nodo), "
            "nunca encimarlos a la derecha ni con posiciones absolutas que desborden. Escalar el diagrama con \\resizebox{!}{0.80\\textheight} "
            "dentro de un entorno landscape para llenar la página sin desbordar; NO usar \\resizebox{\\linewidth}{!} porque desborda en alto."
        ),
        "structure_rule": (
            "Cuerpo en TRES actos: Introducción, un Desarrollo con título temático (NO 'Desarrollo') y Conclusiones. El mapa conceptual es el "
            "NÚCLEO del acto de desarrollo y todo gravita a su alrededor. Orden: (a) preparación conceptual-teórica que conduce al mapa, "
            "(b) el diagrama en su propia página landscape como pieza protagónica, (c) lectura y desarrollo de las ramas tras el diagrama."
        ),
        "three_act_gravity_rule": (
            "El desarrollo NO se fragmenta en varias secciones \\section: marco conceptual, mapa y análisis son subsecciones de una sola sección "
            "de desarrollo cuyo título nombra el tema. El producto (mapa conceptual) manda: el texto lo prepara antes y lo interpreta después."
        ),
        "no_gap_rule": (
            "PROHIBIDO dejar media página o más en blanco justo antes del diagrama landscape. Verificar con pdftoppm que no quede una página "
            "semivacía antes del mapa ni una página landscape vacía extra."
        ),
        "apa_ia_rule": (
            "Rúbrica de mapa conceptual exige citación APA 7 y, si se usó IA, declaración de uso de IA conforme a lineamientos UnADM. "
            "Las referencias APA y la declaración de IA NO deben amontonarse al pie del diagrama: van en la sección de Referencias del final."
        ),
        "closure_rule": (
            "La conclusión inicia con \\clearpage en su propia página y ocupa preferentemente una sola página; integra síntesis, análisis propio "
            "y postura personal. La declaración de uso de IA puede ligarse como \\footnote a una frase oportuna de la conclusión."
        ),
    },
    "cuadro_comparativo": {
        "visible_style_rule": "El criterio de organización de la tabla y la herramienta didáctica deben quedar comentados si son guía editorial; el texto visible debe entrar directo al tema sin metadiscurso.",
        "structure_rule": (
            "Cuerpo en TRES actos: Introducción, un Desarrollo con título temático (NO 'Desarrollo') y Conclusiones. La tabla/cuadro es el NÚCLEO del "
            "acto de desarrollo. Orden: (a) marco conceptual-teórico breve que prepara la tabla, (b) la tabla en su página landscape como pieza "
            "protagónica, (c) semejanzas y diferencias u otro análisis derivado DESPUÉS de la tabla."
        ),
        "three_act_gravity_rule": (
            "El desarrollo NO se fragmenta en varias secciones \\section: marco conceptual, tabla y análisis (semejanzas/diferencias) son subsecciones "
            "de una sola sección de desarrollo cuyo título nombra el tema."
        ),
        "layout_rule": (
            "El cuadro/tabla va en orientación horizontal (landscape) en su PROPIA página, con la tabla y su caption juntos en una sola página landscape. "
            "No anteponer \\clearpage al \\begin{landscape}. Compactar con \\arraystretch<=1.2 y caption en \\footnotesize."
        ),
        "no_gap_rule": (
            "PROHIBIDO dejar media página o más en blanco justo antes del cuadro. Verificar visualmente con pdftoppm el flujo de páginas."
        ),
        "closure_rule": "El análisis derivado de la tabla y la postura personal se cierran en la conclusión. La conclusión inicia con \\clearpage y ocupa preferentemente una sola página; la declaración de uso de IA se liga como \\footnote.",
    },
    "foro": {
        "visible_style_rule": (
            "No explicar en el texto visible que 'esta actividad' usa la técnica foro ni describir la ficha de las 100 técnicas didácticas; "
            "esa trazabilidad va como comentario TEX. El texto visible habla del tema y del diálogo, no del proceso editorial."
        ),
        "structure_rule": (
            "Cuerpo en TRES actos: (1) Introducción, (2) una única sección de Desarrollo con título temático (NO 'Desarrollo' ni 'Participación en el foro') "
            "y (3) Conclusiones. El PRODUCTO —la participación textual publicada— es el NÚCLEO del desarrollo y va como SUBsección. Orden: (a) marco/encuadre "
            "que conduce a las preguntas guía, (b) respuestas a las preguntas guía, (c) la participación textual publicada como subsección protagónica y su lectura."
        ),
        "three_act_gravity_rule": (
            "El desarrollo NO se fragmenta en varias secciones \\section: marco, preguntas guía, participación publicada y su lectura son subsecciones de una "
            "sola sección de desarrollo cuyo título nombra el tema del foro."
        ),
        "forum_participation_block_rule": (
            "La participación publicada debe materializarse como un BLOQUE de código textual (entorno sourcecode de la plantilla, o listings) que reproduzca "
            "literalmente lo publicado: apertura, respuesta a las preguntas guía y cierre con al menos una pregunta al grupo. Cada respuesta/párrafo es UNA sola "
            "línea lógica en el fuente; el bloque hace breaklines pero NO numera las líneas de continuación. El contenido debe ser SELECCIONABLE Y COPIABLE en el PDF."
        ),
        "apa_citation_rule": (
            "REGLA HOMOGÉNEA PARA TODO FORO: la participación publicada DEBE integrar al menos UNA cita TEXTUAL (entrecomillada) de una fuente formal, con su "
            "referencia APA 7 dentro del propio bloque del foro, con formato (Apellido, Año, p.~N). Al final del bloque, un apartado 'Referencias' con sangría "
            "francesa lista TODAS las fuentes citadas en ese bloque. PROHIBIDO usar un ítem del tipo 'Ejemplo de cita en formato APA': la cita se usa, no se enuncia."
        ),
        "feedback_block_rule": (
            "Cuando el foro pida retroalimentación a otra persona, esa retroalimentación publicada se materializa en su PROPIO bloque, separado del de la "
            "participación propia. Antes del bloque de retroalimentación, un breve párrafo presenta —sin nombre, por privacidad académica— la idea a la que se responde."
        ),
        "closure_rule": (
            "La conclusión integra síntesis, análisis propio y postura personal. Inicia SIEMPRE con \\clearpage inmediatamente antes de la \\section, de modo que "
            "arranque en una PÁGINA NUEVA y ocupe preferentemente una sola página. La declaración de uso de IA se liga como \\footnote, nunca como \\section."
        ),
    },
    # Ficha oficial: Fascículo 4, pp. 173-183. Los 5 elementos esenciales y los
    # 9 pasos de construcción provienen literalmente de esa fuente.
    "reporte_de_investigacion": {
        "visible_style_rule": (
            "No explicar en el texto visible que 'esta actividad' usa la técnica reporte de investigación ni describir la ficha "
            "de las 100 técnicas; esa trazabilidad va como comentario TEX. El texto visible habla del problema investigado, del "
            "procedimiento seguido y de los hallazgos, nunca del proceso editorial."
        ),
        "container_absorption_rule": (
            "REGLA CRÍTICA: el reporte de investigación NO se anida dentro del reporte de actividad ni se encierra en un recuadro. La ficha "
            "describe un documento AUTÓNOMO, pero aquí actúa como PRODUCTO alojado en el reporte-plantilla de la materia. PROHIBIDO crear una "
            "sección llamada 'Reporte de investigación', igual que un resumen (#17) no lleva sección 'Resumen'. Contraste: foro o reseña SÍ van "
            "en recuadro (forobox/resenabox) porque son piezas publicadas ajenas al documento; el reporte de investigación no lo es."
        ),
        "template_mapping_rule": (
            "Los 9 pasos de construcción de la ficha se REPARTEN entre plantilla y producto; los que la plantilla ya resuelve SE DESCARTAN para "
            "no duplicarlos: portada (paso 1) la da \\templatePortrait con \\documenttitle y \\authortable; índice (paso 2) lo da \\templateIndex; "
            "referencias (paso 9) las da \\bibliography. NO se rehacen a mano dentro del cuerpo. Quedan a cargo del producto los pasos 3 a 8: "
            "introducción, marco referencial, metodología, resultados, discusión y conclusiones."
        ),
        "structure_rule": (
            "El producto se aloja en el ACTO DE DESARROLLO del esqueleto de tres actos que ya usa la materia. Reparto: el elemento (1) "
            "Introducción de la ficha coincide con la \\section{Introducción} del reporte y el elemento (5) Conclusiones coincide con su "
            "\\section{Conclusión} —no se duplican—; los elementos (2) Metodología, (3) Hallazgos y (4) Análisis y discusión son SUBSECCIONES "
            "de una única sección de desarrollo cuyo título nombra el TEMA investigado. Así están los cinco contenidos sin un documento dentro "
            "de otro. Solo si la consigna exige literalmente los rótulos IMRyD se elevan a \\section."
        ),
        "three_act_gravity_rule": (
            "El NÚCLEO son Hallazgos + Análisis y discusión: ahí gravita el documento. La Metodología los prepara y las Conclusiones los "
            "cierran. El marco teórico va como subsección breve y NO debe crecer hasta desplazar a los hallazgos: si el marco ocupa más que "
            "hallazgos y discusión juntos, el producto degeneró en monografía. La sección de desarrollo lleva el título del TEMA investigado, "
            "nunca la etiqueta 'Desarrollo' ni 'Reporte de investigación'."
        ),
        "metadiscourse_rule": (
            "El texto visible NUNCA anuncia el formato ('en el presente reporte de investigación se expondrá...'). Entra directo al problema. "
            "La trazabilidad con la técnica va como comentario TEX. Tampoco se rotula el índice con los cinco elementos si los títulos "
            "temáticos ya los cubren: el lector debe ver un documento académico, no un formulario relleno."
        ),
        "method_rule": (
            "La Metodología declara explícitamente y en este orden: tipo de investigación (documental, de campo, mixta), técnicas e "
            "instrumentos, fases de trabajo, fuentes consultadas con criterio de selección, y procedimiento de análisis. Debe ser "
            "CONGRUENTE con los objetivos y el marco teórico. PROHIBIDO inventar datos empíricos, encuestas o entrevistas no realizadas: "
            "sin trabajo de campo real el tipo es 'documental' y las fuentes son la literatura y la normativa."
        ),
        "results_rule": (
            "Los Hallazgos describen los resultados de forma sintética y objetiva, ordenados en cuadros, tablas o diagramas cuando el "
            "volumen lo justifique, estableciendo comparaciones o correlaciones. REGLA de la ficha: no repetir en el texto la evidencia "
            "que ya muestra la tabla. Los hallazgos NO son una lista de fuentes ni un resumen de abstracts."
        ),
        "discussion_rule": (
            "Análisis y discusión es subsección PROPIA y no repite lo dicho en Hallazgos. Explica la congruencia de los resultados con las "
            "preguntas de investigación, los objetivos, la hipótesis y la postura teórica; señala coincidencias y discrepancias con otras "
            "investigaciones, y declara las limitaciones y las preguntas sin contestar."
        ),
        "hypothesis_rule": (
            "La Introducción debe enunciar una hipótesis o conjetura de trabajo explícita y objetivos verificables. Las Conclusiones "
            "deben indicar SI SE CUMPLIERON o no los objetivos propuestos: ese cierre es requisito de la ficha, no retórica opcional."
        ),
        "layout_rule": (
            "Prosa académica con rigor formal. Admite tablas, gráficos o infografías de síntesis en Hallazgos; la tabla es auxiliar, "
            "no el núcleo —el reporte no es un cuadro comparativo—. El índice se activa con \\templateIndex, que ya lo genera desde los "
            "títulos: no transcribirlo a mano. Saltos de página limpios entre actos."
        ),
        "closure_rule": (
            "Las Conclusiones inician con \\clearpage; resumen resultados y aportaciones, declaran implicaciones y limitaciones, "
            "indican si se cumplieron los objetivos y proponen recomendaciones para investigaciones posteriores. La postura personal "
            "cierra el argumento. La declaración de uso de IA se liga como \\footnote, nunca como \\section."
        ),
        "apa_citation_rule": (
            "REGLA: al menos 5 fuentes formales (libros, artículos, normativa, estadística oficial) citadas APA 7 e integradas al hilo "
            "argumentativo, no amontonadas al final. Las citas textuales llevan página: (Apellido, Año, p.~N). Las referencias van en "
            "\\bibliography{<materia>}, nunca en thebibliography manual. La ficha exige que TODA fuente citada aparezca en referencias."
        ),
        "build_steps_official": (
            "Pasos de la ficha y quién los resuelve. YA LOS DA LA PLANTILLA (no rehacer): 1. Portada -> \\templatePortrait; "
            "2. Índice -> \\templateIndex; 9. Referencias -> \\bibliography. A CARGO DEL PRODUCTO: "
            "3. Introducción (antecedentes, problema, hipótesis, objetivos, contexto y motivación); "
            "4. Marco referencial o teórico (referentes del campo disciplinar; admite citas, tablas y gráficos); "
            "5. Metodología congruente con objetivos y marco; 6. Resultados sintéticos y objetivos; "
            "7. Discusión (relación con preguntas, objetivos e hipótesis; limitaciones); "
            "8. Conclusiones y recomendaciones (indicar si se cumplieron los objetivos)."
        ),
    },
}


# ---------------------------------------------------------------------------
# 4) Fusión: base + familia + detalle -> contrato final por técnica.
# ---------------------------------------------------------------------------

# Reglas de familia que se heredan al contrato de cada técnica (si el contrato
# detallado no las sobreescribe). Solo se heredan claves de guía editorial.
_FAMILY_INHERITED_KEYS = (
    "materialization",
    "structure_rule",
    "layout_rule",
    "closure_rule",
    "apa_citation_rule",
)


def _build_contracts() -> dict[str, dict[str, Any]]:
    contracts: dict[str, dict[str, Any]] = {}
    for entry in _CATALOG_BASE:
        (tech_id, no, nombre, nivel, familia, product_form,
         required_elements, aliases) = entry
        family = PRODUCT_FAMILIES.get(familia, {})
        contract: dict[str, Any] = {
            "catalogo_no": no,
            "nombre_oficial": nombre,
            "nivel": nivel,
            "familia": familia,
            "familia_label": family.get("label", ""),
            "product_form": product_form,
            "aliases": tuple(aliases),
            "required_visible_elements": tuple(required_elements),
            "preservation_rule": (
                f"Si el producto solicitado es «{nombre}», conservar su forma visible característica "
                f"({', '.join(required_elements)}) y su nivel cognitivo ({nivel}); no transformarlo en otro producto "
                f"salvo que la consigna lo pida. {family.get('materialization', '')}"
            ),
        }
        # Heredar reglas de familia.
        for key in _FAMILY_INHERITED_KEYS:
            if key in family:
                contract[key] = family[key]
        # Fusionar detalle específico por encima.
        detail = _DETAILED_CONTRACTS.get(tech_id, {})
        contract.update(detail)
        # Transversal: ninguna técnica puede sobreescribirla.
        contract["metadata_length_rule"] = METADATA_LENGTH_RULE
        contracts[tech_id] = contract
    return contracts


def _load_official_overrides() -> dict[str, dict[str, Any]]:
    """Carga los overrides oficiales (fascículos + web) si existen.

    El archivo lo genera ``didactic_enricher.run()``. Si no existe o está
    corrupto, se degrada con gracia devolviendo un diccionario vacío para no
    romper la carga base del catálogo.
    """
    overrides_path = (
        Path(__file__).resolve().parents[2]
        / "aulaTEX/base" / "latex" / "adaptadas" / "materias"
        / "tecnicas-didacticas-aprendizaje" / "100tecnicas-overrides.json"
    )
    try:
        import json

        data = json.loads(overrides_path.read_text(encoding="utf-8"))
        return data.get("overrides", {}) if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _apply_overrides(contracts: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Superpone la evidencia oficial sobre cada contrato base."""
    overrides = _load_official_overrides()
    for tech_id, official in overrides.items():
        if tech_id not in contracts:
            continue
        block = {k: v for k, v in official.items() if not k.startswith("_")}
        contracts[tech_id]["official_contract"] = block
        # Elevar la regla de preservación oficial al nivel superior si existe.
        if official.get("preservation_rule_official"):
            contracts[tech_id]["preservation_rule_official"] = official["preservation_rule_official"]
        if official.get("build_steps"):
            contracts[tech_id]["build_steps"] = official["build_steps"]
    return contracts


def _load_json_overlay(filename: str, root_key: str) -> dict[str, dict[str, Any]]:
    """Carga un JSON de overlay (construcción, etc.) degradando con gracia."""
    path = (
        Path(__file__).resolve().parents[2]
        / "aulaTEX/base" / "latex" / "adaptadas" / "materias"
        / "tecnicas-didacticas-aprendizaje" / filename
    )
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get(root_key, {}) if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _apply_construction(contracts: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Superpone el contrato de construcción TikZ/LaTeX + rúbrica de puntuación.

    Lo genera ``didactic_builder_consolidator.run()``. Aporta a cada técnica:
    ``construction_contract`` (tikz_pattern, scoring_rubric, integración con
    realizar-actividad). Se eleva ``tikz_pattern`` y ``scoring_rubric`` al nivel
    superior para que el planner los exponga directamente al motor.
    """
    construction = _load_json_overlay("100tecnicas-construccion.json", "construccion")
    for tech_id, block in construction.items():
        if tech_id not in contracts:
            continue
        clean = {k: v for k, v in block.items() if not k.startswith("_")}
        contracts[tech_id]["construction_contract"] = clean
        if clean.get("tikz_pattern"):
            contracts[tech_id]["tikz_pattern"] = clean["tikz_pattern"]
        if clean.get("scoring_rubric"):
            contracts[tech_id]["scoring_rubric"] = clean["scoring_rubric"]
    return contracts


def _apply_real_patterns(contracts: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Superpone patrones CURADOS desde actividades REALES ya entregadas.

    Tienen PRIORIDAD sobre las plantillas genéricas/LLM porque están probados en
    producción (compilados y entregados). Se guardan en ``real_pattern`` y su
    skeleton reemplaza el de ``tikz_pattern`` para que el motor use el patrón real.
    """
    real = _load_json_overlay("100tecnicas-patrones-reales.json", "patrones")
    # La wiki NO es una técnica del catálogo de 100: es una herramienta de trabajo
    # colaborativo en plataforma. Su patrón (wikibox) se propaga a las técnicas
    # ANFITRIONAS que se materializan en wiki, para que realizar-actividad lo tenga
    # disponible cuando la consigna use una wiki (p. ej. Socioaprendizaje S3).
    _WIKI_HOST_TECHNIQUES = (
        "socioaprendizaje",
        "glosario_colaborativo",
        "trabajo_cooperativo",
        "proyectos_colaborativos",
    )
    for tech_id, pattern in real.items():
        targets = _WIKI_HOST_TECHNIQUES if tech_id == "wiki" else (tech_id,)
        for target in targets:
            if target not in contracts:
                continue
            _overlay_real_pattern(contracts, target, pattern)
    return contracts


def _overlay_real_pattern(
    contracts: dict[str, dict[str, Any]], tech_id: str, pattern: dict[str, Any]
) -> None:
    """Superpone un patrón real sobre el contrato de una técnica concreta."""
    contracts[tech_id]["real_pattern"] = pattern
    tikz = dict(contracts[tech_id].get("tikz_pattern", {}))
    if pattern.get("skeleton"):
        tikz["skeleton"] = pattern["skeleton"]
    if pattern.get("packages"):
        tikz["packages"] = pattern["packages"]
    if pattern.get("rules"):
        tikz["rules"] = pattern["rules"]
    if pattern.get("macro_tarjeta"):
        tikz["macro"] = pattern["macro_tarjeta"]
    tikz["source"] = "actividad_real"
    tikz["fuente_real"] = pattern.get("fuente_real", {})
    contracts[tech_id]["tikz_pattern"] = tikz
    # Añadir criterios de puntuación extra del patrón real a la rúbrica.
    if pattern.get("scoring_extra"):
        rubric = dict(contracts[tech_id].get("scoring_rubric", {}))
        considers = list(rubric.get("consideraciones_para_puntuar", []))
        for extra in pattern["scoring_extra"]:
            if extra not in considers:
                considers.append(extra)
        rubric["consideraciones_para_puntuar"] = considers
        contracts[tech_id]["scoring_rubric"] = rubric


def _apply_activity_products(contracts: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Adjunta a cada técnica los PRODUCTOS de actividad reales que la usan.

    Lo genera ``productos_actividad.run()`` (inventario escaneado del repo). Cada
    técnica recibe ``activity_products`` (lista de {archivo, titulo, actividad}) para
    que el motor conozca ejemplos reales entregados de esa técnica.
    """
    inventory = _load_json_overlay("productos-actividad.json", "por_tecnica")
    for tech_id, items in inventory.items():
        if tech_id not in contracts:
            continue
        contracts[tech_id]["activity_products"] = items
        contracts[tech_id]["activity_products_count"] = len(items)
    return contracts


TECHNIQUE_CONTRACTS: dict[str, dict[str, Any]] = _apply_activity_products(
    _apply_real_patterns(_apply_construction(_apply_overrides(_build_contracts())))
)


# Mapa de identificadores legacy -> id canónico vigente.
LEGACY_TECHNIQUE_ID_ALIASES: dict[str, str] = {
    "cuestionario_diagnostico": "cuestionario",
    "tabla_didactica": "cuadro_comparativo",
    "foro_diagnostico": "foro",
    # La "wiki" es la HERRAMIENTA/soporte de plataforma con que se materializa la
    # TÉCNICA Socioaprendizaje (#53 planeación / #78 catálogo). Son lo mismo: el
    # producto wiki (wikibox) ES el socioaprendizaje. Se resuelven al mismo id.
    "wiki": "socioaprendizaje",
}


def canonical_technique_id(technique_id: str) -> str:
    """Normaliza un identificador de técnica al ID canónico vigente."""
    if technique_id in TECHNIQUE_CONTRACTS:
        return technique_id
    return LEGACY_TECHNIQUE_ID_ALIASES.get(technique_id, technique_id)


def get_technique_contract(technique_id: str) -> dict[str, Any]:
    """Obtiene el contrato de una técnica resolviendo IDs legacy."""
    return TECHNIQUE_CONTRACTS.get(canonical_technique_id(technique_id), {})
