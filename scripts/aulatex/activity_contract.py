from __future__ import annotations

from typing import Any


REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT = {
    "intent": "realizar-actividad",
    "purpose": "Tomar un nodo, carpeta o archivo de actividad y llevarlo desde memoria e insumos hasta TEX/PDF final validado mediante ciclos repetibles.",
    "inputs": {
        "target": "archivo TEX, carpeta de materia o nodo de actividad",
        "activity_number": "número de actividad cuando aplica",
        "local_sources": "notas, PDF, Markdown, planeación, programa de asignatura, referencias, bibliografía y memorias editoriales locales",
        "online_sources": "fuentes institucionales, normativas, académicas o web verificables; obligatorias cuando las respuestas del cuestionario no estén sustentadas por corpus local suficiente",
        "answered_questionnaire": "reactivos, respuestas correctas y justificaciones; deben validarse contra fuentes locales sólidas o fuentes en línea verificables antes de consolidarse en TEX/PDF",
        "editorial_memory_nodes": "memoria local, ascendente y nodos editoriales relacionados; deben consultarse antes de redactar o corregir",
        "engines": "motores LLM configurados para planificar, investigar, redactar, evaluar y criticar",
    },
    "phases": [
        {
            "id": "discover_node",
            "goal": "Resolver scope editorial, TEX canónico, bibliografía, PDF esperado, memoria local y fuentes de referencia.",
            "outputs": ("scope", "target_tex", "target_pdf", "bib", "memory_bundle", "source_inventory"),
        },
        {
            "id": "build_editorial_memory",
            "goal": "Construir, refrescar y consultar memoria editorial local, ascendente y nodos relacionados antes de redactar.",
            "actions": ("editorial-memory local", "editorial-memory ascendente", "recuperación de nodos hermanos", "resumen de reglas del nodo"),
        },
        {
            "id": "ingest_sources",
            "goal": "Extraer e incorporar notas, programas, PDF, Markdown, referencias locales y memoria editorial; buscar fuentes externas cuando falte sustento formal.",
            "actions": ("extractor", "pdftotext si hay PDF", "investigation local", "investigation online", "normalización de corpus"),
        },
        {
            "id": "validate_questionnaire_inputs",
            "goal": "Validar reactivos, respuestas y justificaciones del cuestionario contra fuentes locales sólidas o fuentes en línea verificables antes de consolidar la redacción.",
            "actions": ("contrastar respuestas con bibliografía local", "consultar fuentes institucionales/académicas si falta sustento", "marcar respuestas dudosas", "actualizar .bib con fuentes verificables"),
            "outputs": ("validated_answers", "source_support_map", "unresolved_or_doubtful_answers"),
        },
        {
            "id": "detect_contracts",
            "goal": "Detectar técnica didáctica, formato solicitado, criterios de entrega, rúbrica, subject/título y bibliografía mínima.",
            "outputs": ("didactic_contract", "delivery_contract", "bibliography_contract", "heading_contract"),
        },
        {
            "id": "draft_or_repair_content",
            "goal": "Crear o mejorar el TEX conservando la técnica didáctica y elevando rigor, fuentes y redacción.",
            "actions": ("agent realizar-actividad", "activity-revise --apply", "bibliography-repair --apply"),
        },
        {
            "id": "evaluate_quality",
            "goal": "Observar contrato de actividad, trazabilidad, cobertura conceptual, citas, redacción, formato y coherencia jurídica/académica.",
            "actions": ("activity-observe --compile-check", "quality gates", "crítica adversarial"),
        },
        {
            "id": "compile_and_repair",
            "goal": "Compilar PDF, clasificar errores, reparar bibliografía o LaTeX y verificar frescura del PDF.",
            "actions": ("latexmk-build", "compilation-repair", "bibliography-repair"),
        },
        {
            "id": "repeat_until_pass",
            "goal": "Repetir memoria, extracción, redacción, evaluación y compilación hasta aprobar criterios o agotar ciclos.",
            "stop_conditions": ("activity_contract.passed", "pdf_fresh", "sin citas indefinidas", "sin placeholders", "consensus_score suficiente"),
        },
        {
            "id": "align_report_and_presentation",
            "goal": "Cuando existan reporte y presentación de la misma actividad, alinear la presentación con el reporte: reflejar conceptos, profundidad, fuentes y conclusión, conservando el estilo Beamer institucional y añadiendo una diapositiva de referencias APA y declaración de IA si aplica.",
            "actions": ("comparar reporte vs presentación", "actualizar diapositivas desfasadas", "espejar estructura y fuentes", "compilar presentación", "verificar visualmente"),
            "outputs": ("presentacion_alineada", "presentacion_pdf"),
        },
        {
            "id": "promote_artifacts",
            "goal": "Persistir TEX, PDF, .bib, extractor, memoria, manifiestos, reportes y bitácora de decisión.",
            "outputs": ("tex_final", "pdf_final", "memory", "manifest", "quality_report"),
        },
    ],
    "quality_gates": {
        "memory": "memoria local, ascendente y nodos editoriales relacionados consultados antes de redactar o corregir",
        "sources": "fuentes locales incorporadas y fuentes formales citables cuando haya afirmaciones sustantivas",
        "questionnaire_validation": "si hay cuestionario resuelto, cada respuesta y justificación debe estar contrastada con bibliografía local sólida o fuentes en línea verificables; respuestas dudosas se marcan o se corrigen antes de compilar",
        "online_validation": "si el corpus local no sustenta una respuesta, ejecutar investigación en línea con fuentes institucionales, académicas, normativas o editoriales confiables y materializarlas en .bib",
        "didactic_format": "la forma visible del producto respeta cuestionario, foro, caso, mapa, tabla u otro contrato",
        "headings": "título sin Actividad #; subtítulo compacto; subject/equivalente = Actividad # - Materia",
        "bibliography": "todas las citas visibles tienen entrada .bib, no hay entradas inventadas y el número de referencias aumenta cuando el corpus previo no sostiene todas las respuestas",
        "visible_citations": "las fuentes nuevas deben aparecer como citas visibles en introducción, marco conceptual, tabla o conclusión; no basta con agregar entradas al .bib",
        "reference_growth": "si realizar-actividad valida cuestionarios o afirmaciones sustantivas, debe incrementar o confirmar explícitamente el mapa de soporte bibliográfico: mínimo 3 fuentes sólidas para actividad simple y mínimo 5 para cuestionarios extensos, salvo memoria local suficiente documentada",
        "content": "sin placeholders, con contexto/problema integrado en introducción, análisis propio integrado en conclusión, postura personal integrada en conclusión y transferencia profesional",
        "visible_style": "sin metadiscurso de ejecución: no hablar de 'esta actividad', 'producto solicitado', 'se presenta' o 'la técnica usada' como narrador externo; hablar del tema, problema, concepto, cuestionario, caso o tabla según corresponda",
        "organization_notes": "el criterio de organización, técnica didáctica, herramienta didáctica, nivel cognitivo aplicado o trazabilidad metodológica debe quedar comentado en TEX cuando no sea parte solicitada del producto visible",
        "three_part_structure": "el cuerpo visible se organiza en TRES actos: (1) Introducción, (2) una única sección de Desarrollo y (3) Conclusiones. No fragmentar el desarrollo en varias secciones de primer nivel: el marco conceptual, el producto solicitado y su análisis son SUBsecciones de la misma sección de desarrollo. El marco conceptual, las semejanzas/diferencias u otros apoyos NO son secciones \\section independientes.",
        "introduction": "la introducción absorbe contexto y problema; evitar una subsección visible separada 'Contexto y problema' salvo consigna expresa",
        "development_section": "el segundo acto (desarrollo) NO debe titularse 'Desarrollo': lleva un título cosmético y descriptivo del TEMA (p. ej. 'Clasificación de los tipos de seguro', no 'Desarrollo'). Dentro de él se organizan como subsecciones: preparación conceptual -> producto solicitado (mapa/tabla/cuadro) -> análisis derivado. El producto solicitado es el NÚCLEO protagónico de este acto.",
        "product_centric_gravity": "el producto solicitado (mapa conceptual, cuadro, tabla, esquema) tiene protagonismo imperativo dentro del desarrollo: el texto GRAVITA a su alrededor, antes preparándolo (marco conceptual que conduce a él) y después interpretándolo (lectura, semejanzas/diferencias, implicaciones). El protagonismo es del TEMA y del producto, no de la etiqueta 'desarrollo' ni de metadiscurso.",
        "conclusion": "la conclusión integra síntesis, análisis propio, postura personal, razón y consecuencia; evitar secciones visibles separadas de 'Análisis propio' o 'Postura personal' salvo consigna expresa",
        "ai_declaration": "la declaración de uso de inteligencia artificial, cuando exista, se materializa como \\footnote ligada a una frase oportuna del documento (por defecto de la conclusión), NUNCA como \\section/\\section* ni como bloque separado; debe indicar herramienta y propósito (organizar ideas, revisar redacción) y afirmar que no sustituyó el análisis propio",
        "compile": "PDF existe, está fresco y no presenta errores críticos ni citas indefinidas",
        "report_presentation_alignment": "cuando existan reporte y presentación de la misma actividad, la presentación debe reflejar el contenido, la profundidad, los conceptos, las fuentes y la conclusión del reporte, con estilo Beamer institucional y una diapositiva final de referencias APA y declaración de IA si el reporte la incluye",
    },
    "source_validation_rules": {
        "questionnaire_answers": (
            "Todo cuestionario resuelto requiere mapa de soporte: reactivo -> respuesta -> fuente local o fuente en línea verificable. "
            "No basta con respuestas autogeneradas, memoria interna ni entradas .bib sin citas visibles."
        ),
        "visible_reference_growth": (
            "Cuando se valida información, el TEX final debe mostrar el incremento: citas visibles en el cuerpo y nuevas claves en .bib. "
            "Si no se agregan fuentes nuevas, debe existir memoria local suficiente y verificable que justifique no hacerlo."
        ),
        "local_first_online_when_needed": (
            "Priorizar bibliografía, programa, notas y memorias editoriales locales; si no alcanzan para validar, buscar fuentes en línea sólidas "
            "y registrarlas en .bib con citas visibles en TEX."
        ),
        "editorial_memory_first": (
            "Antes de redactar, consultar nodos de memoria editorial local, ascendente y relacionados para heredar reglas, tono, fuentes y decisiones previas."
        ),
        "no_unsupported_answers": "No consolidar respuestas dudosas sin marcarlas, corregirlas o respaldarlas con fuente verificable.",
    },
    "visible_text_rules": {
        "itesca_operational_metadata": (
            "En entregables ITESCA no imprimir bloques 'Actividad local', 'Módulo Moodle', IDs de plataforma ni "
            "'Vencimiento publicado' en portada, cuerpo, encabezados o pies. Conservar el número académico/local "
            "como 'Actividad N' en la identificación y el subject. IDs, URLs de entrega y vencimientos se mantienen "
            "en planeaciones, manifiestos y registros internos. No eliminar citas pertinentes a recursos del aula "
            "ni confundir la fecha de elaboración con el vencimiento. Revisar el texto extraído del PDF y el Word."
        ),
        "avoid_metadiscourse": (
            "En el cuerpo final no narrar el proceso de elaboración ni mencionar la palabra 'Actividad' como sujeto del análisis; "
            "en su lugar hablar del tema, problema, concepto, cuestionario, caso, tabla o fenómeno estudiado."
        ),
        "comment_organization_criteria": (
            "El criterio de organización, la técnica didáctica aplicada, la herramienta didáctica y la trazabilidad editorial se conservan como comentarios TEX "
            "si sirven al motor o a la memoria, pero no deben aparecer como sección visible salvo que la consigna lo pida."
        ),
        "fold_context_into_introduction": (
            "El contexto y el problema se integran en la introducción; no crear una subsección visible 'Contexto y problema' "
            "salvo instrucción expresa de la consigna."
        ),
        "comment_cognitive_level": (
            "El nivel cognitivo aplicado es guía metodológica para el motor y debe quedar comentado en TEX, no como subsección visible, "
            "salvo que la consigna lo pida expresamente."
        ),
        "questionnaire_as_development": (
            "Si el producto es cuestionario, la sección Desarrollo debe titular y contener directamente el cuestionario. "
            "El marco conceptual se integra dentro de esa sección como apoyo breve o comentario, no como bloque visible separado."
        ),
        "three_part_body": (
            "Estructurar el cuerpo visible en tres actos: Introducción, Desarrollo y Conclusiones. El desarrollo es UNA sola sección "
            "(no varias \\section de primer nivel); marco conceptual, producto solicitado y análisis van como subsecciones dentro de ella."
        ),
        "development_title_cosmetic": (
            "El título del acto de desarrollo debe ser descriptivo del tema, no la palabra 'Desarrollo'. Ejemplos válidos: "
            "'Clasificación de los tipos de seguro', 'Marco y clasificación de los derechos humanos'. El nombre nombra el fenómeno, no la etiqueta didáctica."
        ),
        "product_centric_development": (
            "Dar protagonismo imperativo al producto solicitado (mapa conceptual, cuadro, tabla, esquema) dentro del desarrollo. "
            "El desarrollo gravita a su alrededor: ANTES lo prepara (marco conceptual-teórico que conduce al producto) y DESPUÉS lo interpreta "
            "(lectura del producto, semejanzas y diferencias, implicaciones). El énfasis recae en el tema y en el producto, no en la etiqueta ni en el metadiscurso."
        ),
        "fold_analysis_into_conclusion": (
            "El análisis propio y la postura personal se integran en la conclusión mediante posición, razón y consecuencia; "
            "no crear secciones visibles independientes de análisis propio o postura personal salvo instrucción expresa."
        ),
        "prefer_theme_language": "Usar 'el tema', 'el problema', 'el cuestionario', 'la tabla', 'el caso' o el nombre del concepto antes que 'la actividad'.",
    },
    "compilation_rules": {
        "orphan_bbl": (
            "Si las citas salen como [?] o no aparece la lista de referencias, revisar si existe un .bbl HUÉRFANO y VACÍO junto al .tex "
            "(latexmk lo marca como 'Foreign .bbl' y no lo regenera). Solución: borrar el .bbl y .aux huérfanos y recompilar con "
            "latexmk -bibtex, asegurando TEXINPUTS y BIBINPUTS con la carpeta de la materia."
        ),
        "extractor_deps": (
            "El extractor scripts/extractor-conceptos-ideas requiere en el .venv: scikit-learn, pandas, pymupdf, python-docx, openpyxl, "
            "numpy, python-dotenv y anthropic. Ante ModuleNotFoundError, instalar la dependencia faltante."
        ),
        "extractor_env": (
            "El adaptador del extractor debe cargar scripts/aulatex.env y exportar PYTHONUTF8=1 al subproceso para heredar credenciales "
            "Foundry y evitar UnicodeEncodeError en Windows (cp1252)."
        ),
        "encoding_safety": (
            "NUNCA editar archivos .tex con PowerShell (Set-Content / -replace): corrompe la codificación UTF-8 (mojibake doble). "
            "Usar siempre herramientas de edición que preserven UTF-8. Si ocurre mojibake, reparar con reemplazos dirigidos "
            "(Ã¡->á, Âº->º, â€\"->—) por Python, no re-decodificando todo el archivo."
        ),
        "build_command": (
            "Para builds con bibliografía y múltiples pasadas estables: cmd /c \"latexmk -f -pdf -bibtex -interaction=nonstopmode "
            "-output-directory=.build\\latex\\aux <src>\" con TEXINPUTS='.;<repo>\\base\\Plantilla-Informe;<carpeta-materia>;' y "
            "BIBINPUTS='<carpeta-materia>;'; luego copiar el PDF de .build\\latex\\aux al destino."
        ),
        "page_control": (
            "Usar \\clearpage para forzar que una sección (p. ej. Conclusión) inicie en su propia página. El entorno landscape siempre "
            "abre página nueva: compactar el contenido previo para evitar huecos."
        ),
        "no_gap_before_visual_deliverable": (
            "PROHIBIDO dejar un hueco grande (media página o más en blanco) inmediatamente antes de un entregable visual en landscape "
            "(tabla, cuadro comparativo, mapa conceptual, esquema). Como el entorno landscape abre página nueva, el texto que lo precede "
            "no debe quedar a media página. Estrategias en orden de preferencia: (1) enriquecer con contenido útil el bloque previo "
            "—p. ej. una guía de lectura de columnas/ramas o la metodología de construcción— hasta llenar la página; (2) iniciar la "
            "sección del entregable en página nueva con \\clearpage para que el hueco quede al final de la sección anterior y no entre "
            "el título y la tabla; (3) en caso extremo, ajustar la redacción del texto colindante para equilibrar el llenado. Verificar "
            "SIEMPRE con pdftoppm que no quede una página semivacía antes del entregable ni una página landscape vacía extra."
        ),
        "landscape_single_page": (
            "Tabla/caption o diagrama/leyenda de un entregable visual deben caber JUNTOS en UNA sola página landscape. Si el caption o la "
            "leyenda se desbordan a una segunda página landscape (dejando la primera casi vacía), compactar: \\arraystretch<=1.2, caption "
            "en \\footnotesize pegado con \\\\[0.3cm], y evitar \\vspace*{\\fill} superior e inferior simultáneos que empujan a 2 páginas. "
            "No anteponer \\clearpage a \\begin{landscape} porque pdflscape ya inserta el salto y se generaría una página landscape vacía."
        ),
        "conclusion_single_page": (
            "La conclusión inicia con \\clearpage y debe ocupar preferentemente una sola página, sin arrastrar contenido a una página extra "
            "casi vacía. La declaración de uso de IA se liga como \\footnote a una frase oportuna de la conclusión (no como bloque separado "
            "ni amontonada al pie de una tabla)."
        ),
        "verify_visually": (
            "Verificar el resultado renderizando páginas a PNG (pdftoppm) e inspeccionando el diagrama, no solo el returncode de compilación."
        ),
    },
    "iterative_improvement_rules": {
        "avoid_full_cycle_agent": (
            "Para MEJORAR incrementalmente contenido (agregar conceptos/relaciones) NO usar 'agent --cycle-mode full' con muchos ciclos: "
            "no es observable (guarda todo al final) y es vulnerable a cuelgues de red sin timeout (puede colgarse horas)."
        ),
        "prefer_observable_monitor": (
            "Preferir un bucle observable: activity-monitor (escribe por ciclo, aplica parches verificables, compila y cierra temprano si "
            "pasa el contrato) o un orquestador dedicado que en cada ciclo llame al LLM con timeout, integre el aporte, compile y revierta si rompe."
        ),
        "monitor_note": (
            "activity-monitor NO agrega conceptos nuevos (sus parches son deterministas: placeholders, criterios, bibliografía). Para "
            "enriquecer con razonamiento LLM se requiere un orquestador que pida subconceptos nuevos en JSON, deduplique contra lo existente "
            "y apile con tope por rama para no saturar el layout."
        ),
        "tex_target_priority": (
            "Al observar una actividad con reporte y presentación, priorizar el TEX de reporte (reporte-*) sobre la presentación al resolver "
            "el objetivo, porque el orden alfabético pondría 'presentacion-' primero."
        ),
    },
    "report_presentation_alignment_rules": {
        "principle": (
            "El reporte (reporte-*.tex) es la fuente de verdad; la presentación (presentacion-*.tex) debe reflejar su contenido y nivel de "
            "profundidad. Cuando el reporte se enriquece (más conceptos, principios, fuentes), la presentación debe actualizarse para no quedar desfasada."
        ),
        "content_parity": (
            "Cada eje/tema desarrollado en el reporte debe tener al menos una diapositiva que lo cubra con el mismo nivel de detalle esencial: "
            "conceptos clave, subconceptos relevantes, fundamentos normativos y ejemplos jurídicos verificables."
        ),
        "structure_mirror": (
            "La presentación debe reflejar la estructura del reporte: propósito/objetivo, metodología (si aplica), desarrollo por ejes, conclusión "
            "y una diapositiva final de Referencias (APA 7) más la declaración de uso de IA cuando el reporte la incluya."
        ),
        "style_rule": (
            "Conservar el estilo Beamer institucional (paleta UnADM, frametitle, footline). Usar bloques y columnas para condensar; una idea "
            "central por diapositiva; negritas para conceptos clave; sin saturar de texto."
        ),
        "consistency_checks": (
            "Verificar que fuentes citadas, principios (universalidad, interdependencia, indivisibilidad, progresividad, no regresión) y "
            "conceptos jurídicos (pro persona, interpretación conforme, control de convencionalidad, amparo, etc.) coincidan entre reporte y presentación."
        ),
        "compile_note": (
            "La presentación Beamer se compila con el mismo flujo latexmk (TEXINPUTS con la plantilla); verificar el número de diapositivas y "
            "revisar visualmente que no haya desbordes."
        ),
    },
    "recommended_cycle": (
        "editorial-memory local/ascendente/relacionada -> investigation con queries bibliográficas -> extractor/investigation local -> "
        "validación de cuestionario -> investigation online si falta sustento -> expansión .bib + citas visibles -> "
        "agent realizar-actividad -> activity-observe -> activity-revise/bibliography-repair -> latexmk-build -> repetir hasta aprobar"
    ),
}


# Contratos históricos validados en producción. Sus claves (cuestionario_diagnostico,
# tabla_didactica, foro_diagnostico) NO existen en el catálogo de 100 técnicas y siguen
# usándose en memorias y manifiestos, por eso se conservan y se superponen al catálogo.
_LEGACY_TECHNIQUE_CONTRACTS = {
    "cuestionario_diagnostico": {
        "aliases": ("cuestionario", "diagnóstico", "diagnostico", "reactivo"),
        "required_visible_elements": ("pregunta", "respuesta", "justificación"),
        "preservation_rule": "Si el insumo es cuestionario, el desarrollo visible debe conservar reactivos, respuestas y justificaciones en tabla compacta o lista estructurada; no debe transformarse en ensayo salvo que la consigna lo pida.",
        "visible_style_rule": "No explicar en el texto visible que 'esta actividad' usa una técnica; si hace falta, dejar el criterio de organización o herramienta didáctica como comentario TEX y hablar del tema o del cuestionario.",
        "structure_rule": "Integrar contexto y problema en la introducción; si el producto es cuestionario, Desarrollo debe contener el cuestionario con su título y el marco conceptual debe integrarse dentro de la misma sección; nivel cognitivo aplicado va comentado salvo consigna expresa.",
        "closure_rule": "Integrar análisis propio y postura personal en la conclusión, con posición, razón y consecuencia.",
    },
    "estudio_de_caso": {
        "aliases": ("caso", "estudio de caso", "situación", "situacion"),
        "required_visible_elements": ("hechos", "análisis", "conclusión"),
        "preservation_rule": "Si el insumo es caso, conservar hechos relevantes, actores, problema y resolución argumentada.",
    },
    "mapa_conceptual": {
        "aliases": ("mapa conceptual", "conceptos", "diagrama"),
        "required_visible_elements": ("conceptos", "relaciones", "lectura explicativa"),
        "preservation_rule": "Si el producto es mapa conceptual, conservar jerarquía, relaciones y explicación breve de lectura.",
        "depth_rule": (
            "Un mapa conceptual sólido no puede ser esquelético: exige raíz + ramas del contenido temático + varios niveles de "
            "profundidad (subconceptos, subtipos, ejemplos jurídicos, fundamentos normativos y consecuencias). Cada rama debe tener "
            "al menos 3-4 conceptos; cubrir explícitamente todos los subtemas de la planeación (p. ej. antecedentes, generaciones, "
            "concepto, principios y garantías) sin omitir ninguno."
        ),
        "relations_rule": (
            "Las flechas deben llevar proposiciones de enlace explícitas (conectores como 'se rige por', 'se hace efectivo con', "
            "'se clasifica en') y deben existir relaciones cruzadas entre ramas que evidencien interdependencia e indivisibilidad."
        ),
        "graphic_rule": (
            "Construir el diagrama con TikZ jerárquico. Apilar subconceptos DEBAJO de la cola de cada rama (below= del último nodo), "
            "nunca encimarlos a la derecha ni con posiciones absolutas que desborden. Escalar el diagrama con \\resizebox{!}{0.80\\textheight} "
            "dentro de un entorno landscape para llenar la página sin desbordar; NO usar \\resizebox{\\linewidth}{!} porque desborda en alto."
        ),
        "structure_rule": (
            "Cuerpo en TRES actos: Introducción, un Desarrollo con título temático (NO 'Desarrollo') y Conclusiones. El mapa conceptual es el "
            "NÚCLEO del acto de desarrollo y todo gravita a su alrededor. Orden dentro del desarrollo: (a) preparación conceptual-teórica que conduce "
            "al mapa (marco/metodología breve), (b) el diagrama en su propia página landscape como pieza protagónica, (c) lectura y desarrollo de las ramas "
            "tras el diagrama. La preparación va ANTES del mapa; el análisis va DESPUÉS. El énfasis es del tema y del mapa, no de la etiqueta 'desarrollo'."
        ),
        "three_act_gravity_rule": (
            "El desarrollo NO se fragmenta en varias secciones \\section: marco conceptual, mapa y análisis son subsecciones de una sola sección de desarrollo "
            "cuyo título nombra el tema. El producto (mapa conceptual) manda: el texto lo prepara antes y lo interpreta después, dándole protagonismo imperativo."
        ),
        "no_gap_rule": (
            "PROHIBIDO dejar media página o más en blanco justo antes del diagrama landscape. Si la metodología o el texto previo no llena "
            "la página, ampliarlo con la explicación de la lectura del mapa o iniciar la sección con \\clearpage; en caso extremo, ajustar "
            "la redacción colindante. Verificar con pdftoppm que no quede una página semivacía antes del mapa ni una página landscape vacía extra."
        ),
        "apa_ia_rule": (
            "Rúbrica de mapa conceptual exige citación APA 7 y, si se usó IA, declaración de uso de IA conforme a lineamientos UnADM. "
            "Las referencias APA y la declaración de IA NO deben amontonarse al pie del diagrama: van en la sección de Referencias del final "
            "(la declaración de IA como sección propia antes de \\bibliography, o como \\footnote ligada a una frase oportuna de la conclusión)."
        ),
        "closure_rule": (
            "La conclusión inicia con \\clearpage en su propia página y ocupa preferentemente una sola página; integra síntesis, análisis propio "
            "y postura personal. La declaración de uso de IA puede ligarse como \\footnote a una frase oportuna de la conclusión."
        ),
    },
    "resumen": {
        "aliases": ("resumen", "resumen investigativo", "síntesis", "sintesis", "resumen de lectura"),
        "required_visible_elements": ("introducción", "desarrollo", "conclusión"),
        "preservation_rule": (
            "Si el producto es resumen (#17, familia escrito-expositivo), conservar los 3 ELEMENTOS OFICIALES del fascículo: (1) INTRODUCCIÓN "
            "que aborda de manera general el tema a resumir, (2) DESARROLLO como parte medular donde se explican con palabras propias las ideas "
            "principales del texto base, (3) CONCLUSIÓN que cierra con una síntesis de las ideas presentadas. El resumen es un TEXTO NUEVO con "
            "lenguaje y estilo propio, no una copia abreviada."
        ),
        "texto_nuevo_rule": (
            "El resumen NO es un recorte del original: es un texto nuevo producido a partir del texto fuente. PROHIBIDAS las frases literales "
            "del original salvo cita textual explícita y justificada. El lenguaje debe ser propio, en prosa y en TERCERA PERSONA, con unidad "
            "textual (introduce, desarrolla y concluye lo que comunica)."
        ),
        "extension_rule": (
            "Regla de proporción (Cervera et al., 2006, citados en Arenas et al., 2014): un buen resumen representa entre UN TERCIO y UNA "
            "QUINTA PARTE del original. Extenderse demasiado revela poca capacidad de síntesis y repetición de ideas. La brevedad es criterio "
            "de calidad, no defecto."
        ),
        "seis_pasos_rule": (
            "Los 7 pasos del fascículo estructuran el trabajo: (1) lectura del texto fuente, (2) subrayar suprimiendo lo irrelevante o "
            "repetitivo, (3) seleccionar la información esencial, (4) generalizar sustituyendo conceptos parecidos por uno más general, "
            "(5) integrar construyendo proposiciones conceptualmente nuevas, (6) redactar según el objetivo definido, (7) cuidar la escritura "
            "y revisar. Los pasos son método de trabajo; NO deben aparecer como andamiaje visible salvo que la planeación lo pida."
        ),
        "estilo_rule": (
            "Frases cortas; sin expresiones ambiguas; sin superlativos ni adjetivos innecesarios; sin abreviaturas o acrónimos salvo los muy "
            "conocidos; sin referencias particulares a gráficos o imágenes. Los párrafos guardan relación con el tema general y mantienen "
            "conexión lógica entre sí."
        ),
        "fundamento_normativo_rule": (
            "Cuando el contenido es jurídico, cada afirmación sustantiva se ancla en su FUNDAMENTO NORMATIVO EXACTO (artículo, fracción, "
            "párrafo, inciso) con las abreviaturas de un texto normativo, y se respalda con cita APA de la fuente doctrinal o institucional."
        ),
        "structure_rule": (
            "Cuerpo en TRES actos que coinciden con los 3 elementos oficiales del resumen: Introducción, un Desarrollo con título temático "
            "(NO 'Desarrollo') y Conclusiones. El desarrollo se organiza en subsecciones temáticas que siguen la estructura del texto base, "
            "no en una lista de pasos metodológicos."
        ),
        "closure_rule": (
            "La conclusión sintetiza las ideas presentadas e integra postura propia. La declaración de uso de IA se liga como \\footnote a una "
            "frase oportuna, nunca como \\section."
        ),
    },
    "mapa_semantico": {
        "aliases": ("mapa semántico", "mapa semantico", "mapa semántico", "red semántica", "red semantica", "campo semántico", "campo semantico"),
        "required_visible_elements": ("tema central", "conceptos", "palabras enlace"),
        "preservation_rule": (
            "Si el producto es mapa semántico (#70, familia visual-jerárquica homóloga al mapa conceptual), conservar los 3 ELEMENTOS "
            "OFICIALES: (1) tema central (nodo raíz), (2) conceptos/ideas principales jerarquizados de lo general a lo particular, (3) "
            "PALABRAS ENLACE sobre las líneas que especifican la relación. Sin palabras enlace no es mapa semántico. Reutiliza el patrón "
            "TikZ del mapa conceptual (estilos ms*/mc*, landscape, \\resizebox) organizado por CAMPOS SEMÁNTICOS en layout radial."
        ),
        "visible_style_rule": (
            "El criterio de organización y la herramienta didáctica van comentados si son guía editorial; el texto visible entra directo al "
            "tema sin metadiscurso. El mapa se acompaña de una metodología breve (6 pasos) antes y una lectura del mapa después."
        ),
        "campos_semanticos_rule": (
            "A diferencia del mapa conceptual (proposiciones encadenadas), el mapa semántico organiza por CAMPOS SEMÁNTICOS alrededor de un "
            "TEMA CENTRAL: raíz al centro-arriba y campos en disposición RADIAL/abanico (below left/below right a distancias crecientes), con "
            "sus conceptos debajo. Impacto visual de 'un pantallazo del tema': layout radial equilibrado, no columnas largas."
        ),
        "palabras_enlace_rule": (
            "Cada línea (raíz->campo y campo->concepto) DEBE llevar su PALABRA ENLACE explícita (etiqueta itálica sobre la flecha: 'se "
            "clasifican en', 'comprende', 'se funda en', 'se garantiza con'). Las palabras enlace son un elemento OFICIAL obligatorio del "
            "mapa semántico y su ausencia lo invalida."
        ),
        "fundamento_constitucional_rule": (
            "REGLA JURÍDICA (cuando el contenido es normativo): CADA concepto debe correlacionarse con su FUNDAMENTO CONSTITUCIONAL EXACTO "
            "—artículo, fracción, párrafo, inciso o numeral— con las abreviaturas normativas (p.ej. 'art.~1.º, párr.~3.º CPEUM'). El "
            "fundamento va dentro del nodo concepto o como palabra enlace 'se funda en'. Suele ser el eje de la rúbrica."
        ),
        "structure_rule": (
            "Cuerpo en TRES actos: Introducción, un Desarrollo con título temático (NO 'Desarrollo') y Conclusiones. El mapa semántico es el "
            "NÚCLEO del desarrollo: (a) metodología breve (6 pasos) que prepara el mapa, (b) el diagrama en su propia página landscape, (c) "
            "lectura/interpretación del mapa después. El énfasis es del tema y del mapa."
        ),
        "layout_optimizer_rule": (
            "OBLIGATORIO tras generar/editar el mapa: partir de un layout RELATIVO agrupado por campos (radial) y correr el optimizador "
            "(aulatex mapa-layout <tex> --write) que resuelve solapes y coloca las palabras enlace anti-empalme. Escalar con "
            "\\resizebox{!}{0.80\\textheight} en landscape. Verificar el render (view_image); el mapa y su caption caben en la misma página."
        ),
        "no_gap_rule": (
            "PROHIBIDO dejar media página o más en blanco antes del diagrama landscape. Llenar el bloque previo con la metodología/lectura o "
            "usar \\clearpage. Verificar con pdftoppm que no quede página semivacía antes del mapa ni página landscape vacía extra."
        ),
        "closure_rule": (
            "La conclusión inicia con \\clearpage en su propia página; integra síntesis y postura personal sobre lo representado. La "
            "declaración de uso de IA se liga como \\footnote a una frase oportuna, nunca como \\section."
        ),
    },
    "tabla_didactica": {
        # "cuadro comparativo" pertenece a la técnica #1 del catálogo; aquí solo
        # quedan los alias genéricos de tabla.
        "aliases": ("tabla", "cuadro", "longtable", "tabular"),
        "required_visible_elements": ("título", "encabezados", "filas", "criterio de lectura"),
        "preservation_rule": "Si la técnica usa tabla o cuadro, conservar estructura tabular visible con título/caption, encabezados claros, filas completas y una lectura breve; usar longtable, landscape, scriptsize, tabcolsep y arraystretch cuando el contenido sea amplio.",
        "visible_style_rule": "El criterio de organización de la tabla y la herramienta didáctica deben quedar comentados si son guía editorial; el texto visible debe entrar directo al tema sin metadiscurso.",
        "structure_rule": (
            "Cuerpo en TRES actos: Introducción, un Desarrollo con título temático (NO 'Desarrollo') y Conclusiones. La tabla/cuadro es el NÚCLEO del "
            "acto de desarrollo. Orden dentro del desarrollo: (a) marco conceptual-teórico breve que prepara y da sentido a la tabla, (b) la tabla en su "
            "página landscape como pieza protagónica, (c) semejanzas y diferencias u otro análisis derivado DESPUÉS de la tabla. Contexto y problema van en "
            "la introducción; nivel cognitivo aplicado va comentado salvo consigna expresa."
        ),
        "three_act_gravity_rule": (
            "El desarrollo NO se fragmenta en varias secciones \\section: marco conceptual, tabla y análisis (semejanzas/diferencias) son subsecciones de una "
            "sola sección de desarrollo cuyo título nombra el tema. El producto (cuadro/tabla) manda: el texto lo prepara antes y lo interpreta después."
        ),
        "layout_rule": (
            "El cuadro/tabla va en orientación horizontal (landscape) en su PROPIA página, con la tabla y su caption juntos en una sola "
            "página landscape. La sección que introduce la tabla NO debe quedar a media página dejando un hueco antes del salto a landscape: "
            "llenar ese bloque con una guía de lectura de las columnas (qué informa cada una y cómo contrastarlas) o iniciar la sección con "
            "\\clearpage; en caso extremo, ajustar la redacción del texto colindante. No anteponer \\clearpage al \\begin{landscape}. "
            "Compactar con \\arraystretch<=1.2 y caption en \\footnotesize para que quepan tabla y caption en una sola página."
        ),
        "no_gap_rule": (
            "PROHIBIDO dejar media página o más en blanco justo antes del cuadro. Verificar visualmente con pdftoppm el flujo de páginas: "
            "la página previa al landscape debe estar razonablemente llena y no debe existir una página landscape vacía extra."
        ),
        "closure_rule": "El análisis derivado de la tabla y la postura personal se cierran en la conclusión, no en secciones visibles separadas salvo consigna expresa. La conclusión inicia con \\clearpage y ocupa preferentemente una sola página; la declaración de uso de IA se liga como \\footnote a una frase oportuna de la conclusión.",
    },
    "foro_diagnostico": {
        "aliases": ("foro", "foro diagnóstico", "foro diagnostico", "participación en foro", "participacion en foro"),
        "required_visible_elements": ("preguntas guía", "respuesta", "participación textual publicada", "cierre"),
        "preservation_rule": "Si el producto es foro diagnóstico, conservar preguntas guía y respuestas compactas sin convertirlo en ensayo extenso.",
        "visible_style_rule": (
            "No explicar en el texto visible que 'esta actividad' usa la técnica foro ni describir la ficha de las 100 técnicas didácticas; "
            "esa trazabilidad va como comentario TEX. El texto visible habla del tema y del diálogo, no del proceso editorial."
        ),
        "structure_rule": (
            "Cuerpo en TRES actos: (1) Introducción, (2) una única sección de Desarrollo con título temático (NO 'Desarrollo' ni 'Participación en el foro') "
            "y (3) Conclusiones. El PRODUCTO solicitado del foro —la participación textual publicada— es el NÚCLEO del acto de desarrollo y va como SUBsección "
            "dentro de esa única sección, no como \\section de primer nivel. Orden dentro del desarrollo: (a) breve marco/encuadre que conduce a las preguntas guía, "
            "(b) las respuestas a las preguntas guía, (c) la participación textual publicada en el foro como subsección protagónica (bloque de código verbatim/listings) "
            "y su lectura breve."
        ),
        "three_act_gravity_rule": (
            "El desarrollo NO se fragmenta en varias secciones \\section: marco, preguntas guía, participación publicada y su lectura son subsecciones de una sola "
            "sección de desarrollo cuyo título nombra el tema del foro. El producto (la participación publicada) manda: el texto lo prepara antes y lo interpreta después."
        ),
        "forum_participation_block_rule": (
            "La participación publicada en el foro debe materializarse como un BLOQUE de código textual (entorno sourcecode de la plantilla, o listings con estilo propio "
            "cuando el documento no cargue la plantilla) que reproduzca literalmente lo que se publica: encuadre/apertura, respuesta a la pregunta detonante o preguntas guía, "
            "y un cierre que invite al diálogo entre pares con al menos una pregunta al grupo. El bloque debe seguir la estructura de la técnica foro (apertura, participación, "
            "coordinación, cierre). REQUISITOS DE FORMATO: cada respuesta/párrafo es UNA sola línea lógica en el fuente (una entrada por número); el bloque hace ajuste de línea "
            "(breaklines) para el texto largo pero NO numera las líneas de continuación del ajuste (si se usa numeración, numbers=left con numberstyle que solo marque la línea de origen, "
            "no las envueltas). El contenido del bloque debe ser SELECCIONABLE Y COPIABLE en el PDF (evitar literate/mapeos de caracteres que rompan el copiado; preferir fuente con "
            "soporte de copia como \\ttfamily estándar o inputenc utf8 con extendedchars)."
        ),
        "apa_citation_rule": (
            "REGLA HOMOGÉNEA PARA TODO FORO: la participación publicada DEBE integrar al menos UNA cita TEXTUAL (entrecomillada) de una fuente formal, con su "
            "referencia APA 7 dentro del propio bloque del foro. La cita textual va incrustada de forma orgánica en la respuesta que corresponda —no como 'ejemplo de cita' ni "
            "como metadiscurso— con el formato (Apellido, Año, p.~N) inmediatamente después de las comillas de cierre. Al final del bloque del foro, tras el cierre y la firma, se "
            "reproduce un apartado titulado 'Referencia' (o 'Referencias' si son varias) con sangría francesa (\\hangindent), tal como se publicaría en el foro. "
            "COBERTURA COMPLETA: el apartado de referencias del forobox debe listar TODAS las fuentes citadas dentro de ESE forobox (cada \\citep{...} y cada cita textual), no solo la "
            "que aparece en formato textual; una sola cita textual es suficiente para el requisito de 'cita textual', pero toda fuente mencionada debe tener su entrada APA 7 en el "
            "apartado de referencias, ordenada alfabéticamente. Cada forobox (participación y, si existe, retroalimentación) lleva su PROPIO apartado de referencias con las fuentes que "
            "cita ese bloque. Esta cita+referencias forma parte de la reproducción literal de lo publicado y es independiente de la bibliografía general del documento; puede o no tener "
            "entrada .bib. PROHIBIDO usar un ítem del tipo 'Ejemplo de cita en formato APA' como reactivo de la lista: la cita se usa, no se enuncia."
        ),
        "feedback_block_rule": (
            "Cuando el foro pida además retroalimentación a la participación de otra persona, esa retroalimentación publicada también se materializa en su PROPIO forobox "
            "(caja del foro), separado del forobox de la participación propia, para reflejar que es contenido publicado en el hilo. Antes del forobox de retroalimentación, un breve "
            "párrafo en prosa presenta —sin nombre, por privacidad académica— la idea a la que se responde. Dentro del forobox de retroalimentación se cierra con una pregunta dirigida "
            "a quien participó."
        ),
        "closure_rule": (
            "La conclusión integra síntesis, análisis propio y postura personal (posición, razón y consecuencia); no crear secciones visibles separadas de análisis o postura. "
            "La conclusión inicia SIEMPRE con \\clearpage inmediatamente antes de la \\section, de modo que arranque en una PÁGINA NUEVA por sí sola y ocupe preferentemente una sola página, sin quedar pegada al bloque de participación del foro. "
            "La declaración de uso de IA se liga como \\footnote a una frase oportuna de la conclusión, nunca como \\section."
        ),
    },
}


def _merge_technique_contracts() -> dict[str, Any]:
    """Catálogo de 100 técnicas + contratos legacy superpuestos.

    Antes solo se exponían las 7 técnicas legacy, así que el motor no podía
    reconocer las otras 93 (entre ellas reporte_de_investigacion).

    Las legacy se insertan PRIMERO a propósito: la detección por alias desempata
    por orden de inserción, y alias compartidos ("cuestionario", "foro") deben
    seguir resolviendo a la clave legacy que ya usan memorias y manifiestos.
    """
    try:
        from .didactic_catalog import TECHNIQUE_CONTRACTS
    except ImportError:  # ejecución como script suelto
        from didactic_catalog import TECHNIQUE_CONTRACTS  # type: ignore[no-redef]

    merged: dict[str, Any] = {}
    for tech_id, legacy in _LEGACY_TECHNIQUE_CONTRACTS.items():
        base = dict(TECHNIQUE_CONTRACTS.get(tech_id, {}))
        base.update(legacy)
        merged[tech_id] = base
    for tech_id, contract in TECHNIQUE_CONTRACTS.items():
        merged.setdefault(tech_id, dict(contract))
    return merged


DIDACTIC_TECHNIQUE_CONTRACTS = _merge_technique_contracts()

ACTIVITY_1_CONTRACT = {
    "required": {
        "objective": True,
        "instruction_source": True,
        "didactic_technique": True,
        "didactic_format_preserved": True,
        "output_format": True,
        "bibliography": True,
        "traceability": True,
        "evaluation_criteria": True,
        "final_reflection": True,
        "ai_declaration_footnote": True,
    },
    "acceptable_ranges": {
        "sections_min": 3,
        "sections_max": 8,
        "bibliography_entries_min": 3,
        "visible_citations_min": 3,
        "questionnaire_bibliography_entries_min": 5,
        "concepts_min": 5,
    },
    "didactic_techniques": DIDACTIC_TECHNIQUE_CONTRACTS,
}


def evaluate_activity_contract(state: dict[str, Any]) -> dict[str, Any]:
    signals = state.get("signals", {})
    observed = state.get("observed_state", {})
    required_checks = {
        "objective": bool(signals.get("objective_present") or signals.get("extractor_objective_present")),
        "instruction_source": bool(signals.get("purpose_present") or signals.get("extractor_planeacion_present")),
        "didactic_technique": bool(
            signals.get("didactic_technique_present")
            or signals.get("questionnaire_detected")
            or signals.get("case_study_detected")
            or signals.get("product_visual_detected")
            or signals.get("extractor_verbs_count", 0) > 0
        ),
        "didactic_format_preserved": bool(
            signals.get("questionnaire_contract_satisfied")
            or signals.get("table_contract_satisfied")
            or (not signals.get("questionnaire_detected") and signals.get("didactic_technique_present"))
            or signals.get("product_visual_detected")
        ),
        "output_format": bool(state.get("target_tex")) and bool(signals.get("product_visual_detected") or state.get("target_pdf")),
        "bibliography": bool(observed.get("bibliography_ready")) and int(signals.get("cited_keys_count", 0)) >= ACTIVITY_1_CONTRACT["acceptable_ranges"]["bibliography_entries_min"],
        "visible_citations": int(signals.get("cited_keys_count", 0)) >= ACTIVITY_1_CONTRACT["acceptable_ranges"]["visible_citations_min"],
        "questionnaire_sources_min": (not signals.get("questionnaire_detected")) or int(signals.get("cited_keys_count", 0)) >= ACTIVITY_1_CONTRACT["acceptable_ranges"]["questionnaire_bibliography_entries_min"],
        "traceability": bool(observed.get("extractor_ready")) and int(signals.get("cited_keys_count", 0)) >= 3,
        "evaluation_criteria": bool(signals.get("evaluation_criteria_present") or signals.get("extractor_criteria_count", 0) > 0),
        "final_reflection": bool(signals.get("conclusion_present")),
        # La declaración de uso de IA, cuando exista, debe ir como \footnote ligada a
        # una frase oportuna (por defecto de la conclusión), NO como sección/bloque
        # separado. Si no hay declaración de IA, el check no penaliza.
        "ai_declaration_footnote": (
            (not bool(signals.get("ai_declaration_present")))
            or (
                bool(signals.get("ai_declaration_as_footnote"))
                and not bool(signals.get("ai_declaration_as_section"))
            )
        ),
    }
    range_checks = {
        "sections_range": ACTIVITY_1_CONTRACT["acceptable_ranges"]["sections_min"]
        <= int(signals.get("sections_count", 0))
        <= ACTIVITY_1_CONTRACT["acceptable_ranges"]["sections_max"],
        "concepts_min": int(signals.get("extractor_concepts_count", 0)) >= ACTIVITY_1_CONTRACT["acceptable_ranges"]["concepts_min"],
        # El cuerpo visible no debe contener metadiscurso de ejecución ni residuos de
        # flujos antiguos (p. ej. 'Refuerzo editorial Ciclo A', 'La Actividad N',
        # 'Esta actividad', 'el producto solicitado'). Si el observer no provee la
        # señal (None), el check no penaliza.
        "no_metadiscourse": len(signals.get("metadiscourse_hits") or []) == 0,
    }
    all_checks = {**required_checks, **range_checks}
    required_hits = sum(1 for ok in required_checks.values() if ok)
    score = round(100 * sum(1 for ok in all_checks.values() if ok) / max(1, len(all_checks)), 2)
    findings = [
        _contract_finding(name)
        for name, ok in all_checks.items()
        if not ok
    ]
    passed = score >= 80 and required_hits >= 6 and range_checks["sections_range"]
    return {
        "score": score,
        "passed": passed,
        "required_hits": required_hits,
        "required_total": len(required_checks),
        "checks": all_checks,
        "required_checks": required_checks,
        "range_checks": range_checks,
        "findings": findings,
        "contract": ACTIVITY_1_CONTRACT,
    }


def _contract_finding(name: str) -> str:
    messages = {
        "objective": "Falta objetivo pedagógico verificable en TEX o planeación.",
        "instruction_source": "No hay evidencia suficiente de consigna o propósito instruccional.",
        "didactic_technique": "No se detecta con claridad la técnica didáctica o el producto esperado.",
        "didactic_format_preserved": "La técnica didáctica detectada no se preserva en el desarrollo; por ejemplo, un cuestionario debe conservar pregunta, respuesta y justificación.",
        "output_format": "No se detecta un formato de salida consistente para la actividad.",
        "bibliography": "La bibliografía no cumple el mínimo contractual.",
        "visible_citations": "Las fuentes no aparecen como citas visibles suficientes en el cuerpo del TEX.",
        "questionnaire_sources_min": "El cuestionario resuelto no alcanza el mínimo de fuentes citadas para validar respuestas y justificaciones.",
        "traceability": "La trazabilidad entre actividad, citas y extractor es insuficiente.",
        "evaluation_criteria": "No se detectan criterios de evaluación o entrega suficientemente explícitos.",
        "final_reflection": "No se detecta cierre argumentativo o conclusión final.",
        "ai_declaration_footnote": "La declaración de uso de IA debe ir como \\footnote ligada a una frase oportuna (por ejemplo de la conclusión), no como sección o bloque separado.",
        "sections_range": "La estructura de secciones queda fuera del rango contractual.",
        "concepts_min": "La cobertura conceptual extraída está por debajo del mínimo contractual.",
        "no_metadiscourse": "El cuerpo visible contiene metadiscurso de ejecución o residuos de flujos antiguos (p. ej. 'Refuerzo editorial Ciclo A', 'La Actividad N', 'Esta actividad'); deben eliminarse o pasar a comentario TEX.",
    }
    return messages.get(name, f"Incumplimiento contractual: {name}.")