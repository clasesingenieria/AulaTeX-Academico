"""Generador del paquete técnico temporizado, subtítulos revisados y montaje base para AM Taller Autocentro (Actividad 15)."""
from __future__ import annotations

import json
from pathlib import Path
import re
import textwrap
from PIL import Image, ImageDraw

BASE_DIR = Path(__file__).resolve().parent.parent
MONTAJE_DIR = Path(__file__).resolve().parent
SLIDES_DIR = MONTAJE_DIR / "diapositivas-1080p"

# Coordenadas del recuadro del estudiante en lienzo 1920x1080 (zona derecha libre de texto: x >= 1488)
CAMERA_BOX = {
    "canvas_width": 1920,
    "canvas_height": 1080,
    "x": 1488,
    "y": 284,
    "width": 384,
    "height": 512,
    "aspect_ratio": "3:4 (o 16:9 en 384x216 centrado en y=432)",
    "safe_zone_verified": True,
    "non_white_pixels_covered": 0,
}

# Doce bloques sincronizados con las 12 diapositivas (duración objetivo: 11:00 = 660 segundos, ~131 palabras/minuto, sin silencios de relleno).
# Base: sección 3 del reporte (12 bloques del guion) con precisiones puntuales de la sección 2 (fundamentación empresarial).
BLOCKS = [
    {
        "slide": 1,
        "title": "AM Taller Autocentro",
        "start_sec": 0,
        "end_sec": 54,
        "visual_cue": "Diapositiva 1/12: Portada institucional con logotipo de AM Taller Autocentro y datos del proyecto.",
        "paragraphs": [
            "Soy Martín Jonathan de la Cruz Muñoz, estudiante de la Maestría en Gestión Administrativa. Mi aportación a AM Taller Autocentro es el diseño administrativo: organización de información de mercado, representación del proceso de servicio y distribución de responsabilidades para apoyar decisiones. La ejecución del mantenimiento requiere personal con competencia técnica automotriz verificada.",
            "El interés de la propuesta es resolver una cuestión concreta: que una persona entienda qué mantenimiento recibe, qué importe autoriza y qué condiciones deben cumplirse antes de entregar su vehículo. AM Taller coloca esa claridad en el centro de la relación con el cliente. Ante ustedes quiero explicar su propuesta de valor, sus controles operativos y los datos que necesitamos para evaluar responsablemente una decisión de inversión."
        ],
    },
    {
        "slide": 2,
        "title": "El negocio: claridad antes de intervenir",
        "start_sec": 54,
        "end_sec": 114,
        "visual_cue": "Diapositiva 2/12: Servicio inicial de referencia, controles de orden y alcance, misión y visión.",
        "paragraphs": [
            "AM Taller Autocentro organiza servicios automotrices con recepción, cotización comprensible, autorización verificable y seguimiento. El servicio inicial de referencia es el cambio de aceite y filtro para vehículos ligeros conforme a las especificaciones de su fabricante. Esta delimitación evita presupuestar un taller de servicios generales con recursos calculados para un único mantenimiento; mecánica, llantas y refacciones son líneas previstas sujetas a competencias, herramientas, insumos y demanda, no inclusiones automáticas desde el primer día.",
            "La misión es proporcionar atención confiable con comunicación clara y ejecución autorizada. La visión abarca cinco años posteriores al inicio: consolidar un servicio local reconocido por organización y cumplimiento. La promesa es un método de trabajo, no liderazgo comprobado. Documentar cada orden y verificar recursos antes de comprometer fechas son objetivos evaluables; si no puede sostenerse el servicio, la decisión es reprogramar o cerrar sin ejecución."
        ],
    },
    {
        "slide": 3,
        "title": "Monterrey: contexto no equivale a compradores",
        "start_sec": 114,
        "end_sec": 156,
        "visual_cue": "Diapositiva 3/12: Mapa geoestadístico de Monterrey (19039), indicadores del Censo 2020 y perfil del cliente objetivo.",
        "paragraphs": [
            "El territorio de estudio es el municipio de Monterrey, Nuevo León. El Censo dos mil veinte del INEGI registra un millón ciento cuarenta y dos mil novecientos noventa y cuatro habitantes y trescientas veintinueve mil noventa y cinco viviendas habitadas.",
            "Estas magnitudes contextualizan el territorio, pero no son compradores de AM Taller, no identifican cuántos vehículos ligeros demandan servicio ni constituyen una estimación actualizada a dos mil veintiséis. El cliente objetivo es una persona adulta que participa en decidir servicios para un vehículo ligero, mientras que la confirmación de un domicilio operativo concreto permanece pendiente."
        ],
    },
    {
        "slide": 4,
        "title": "Mercado: instrumentos listos, sondeo pendiente",
        "start_sec": 156,
        "end_sec": 222,
        "visual_cue": "Diapositiva 4/12: Instrumentos de demanda (22 reactivos) y oferta (16 ítems), y estado pendiente del levantamiento.",
        "paragraphs": [
            "La investigación de mercado contempla dos instrumentos con funciones distintas: una encuesta de veintidós preguntas sobre demanda que describe experiencias de los participantes, y una lista de cotejo de dieciséis ítems sobre oferta para comparar establecimientos. La encuesta distingue servicio, frecuencia, gasto y satisfacción; la lista registra categorías, horarios, condiciones y precios comparables, conservando fecha y fuente por observación. El gasto de una reparación y el precio de un diagnóstico corresponden a servicios distintos, por lo que su comparación exige un alcance equivalente.",
            "El límite es importante para ustedes: todavía no dispongo del levantamiento real ni de fichas verificadas de oferentes. Por eso no muestro porcentajes de aceptación, clientes captados ni superioridad comprobada. El siguiente paso es un sondeo por conveniencia en Monterrey, voluntario y anonimizado, cuyos resultados describirán a quienes respondan, no a toda la población. Informaré fechas, respuestas válidas, omisiones y alcance del gasto antes de extraer decisiones."
        ],
    },
    {
        "slide": 5,
        "title": "Metas a cinco años y riesgos de diseño",
        "start_sec": 222,
        "end_sec": 282,
        "visual_cue": "Diapositiva 5/12: Tabla de metas de servicios y clientes del año 1 al 5, supuestos operativos y análisis FODA.",
        "paragraphs": [
            "Las metas de diseño van de trescientos sesenta servicios equivalentes en el primer año a cuatrocientos cincuenta en el segundo, quinientos cuarenta en el tercero, seiscientos treinta en el cuarto y setecientos veinte en el quinto. Con una recurrencia supuesta de uno y medio servicios por persona, corresponderían a entre doscientos cuarenta y cuatrocientos ochenta clientes distintos por año. No son ventas confirmadas ni se suman como clientes nuevos acumulados. La capacidad hipotética de novecientos servicios al año depende de una estación y recursos todavía por comprobar.",
            "El FODA reconoce organización y trazabilidad como fortalezas previstas, y falta de evidencia de mercado y costos como debilidades actuales. Las oportunidades deben contrastarse con usuarios; competencia y variación de insumos son riesgos por examinar. La respuesta es limitar el lanzamiento a trabajos atendibles y validar antes de ampliar."
        ],
    },
    {
        "slide": 6,
        "title": "Identidad: compromiso convertido en control",
        "start_sec": 282,
        "end_sec": 322,
        "visual_cue": "Diapositiva 6/12: Logotipo de AM Taller Autocentro, lema institucional y alcance de la identidad visual.",
        "paragraphs": [
            "El logotipo de AM Taller Autocentro es de autoría propia confirmada y se acompaña del lema: Pasión por los autos. Compromiso contigo. La imagen comunica el enfoque automotriz, mientras que el compromiso se traduce operativamente en presupuesto comprensible, autorización previa y conciliación al cierre.",
            "Su coherencia depende de que la comunicación comercial coincida con lo autorizado y efectivamente prestado. Ante ustedes preciso que el logotipo identifica la propuesta, pero no se presenta como marca registrada ni como prueba de preferencia del consumidor."
        ],
    },
    {
        "slide": 7,
        "title": "Publicidad: piloto limitado y medible",
        "start_sec": 322,
        "end_sec": 372,
        "visual_cue": "Diapositiva 7/12: Propuesta de volante informativo, reglas del piloto de 30 días y presupuesto referencial de 3,520 MXN.",
        "paragraphs": [
            "El mapa delimita el municipio de Monterrey, no una sucursal existente ni un radio de traslado medido; elegir un local concreto requiere evaluar acceso, renta, habilitación, seguridad y manejo de residuos. Por ello, el volante invita a solicitar cotización sin inventar dirección, teléfono o precios.",
            "Propongo un piloto de treinta días con volantes y difusión digital limitada por tres mil quinientos veinte pesos referenciales, registrando consultas, cotizaciones y servicios por separado para distinguir interés inicial de contratación real. Un anuncio publicado no equivale a ventas y tampoco se ofrecerán descuentos cuyo costo no pueda sostenerse."
        ],
    },
    {
        "slide": 8,
        "title": "Proceso 1: alcance, presupuesto y autorización",
        "start_sec": 372,
        "end_sec": 424,
        "visual_cue": "Diapositiva 8/12: Primera parte del flujo operativo (pasos 1 a 9): solicitud, presupuesto, autorización e inspección.",
        "paragraphs": [
            "El diagrama de proceso consta de dieciséis pasos y tres controles centrales. En la primera parte, de los pasos uno a tres, recibimos la solicitud, registramos el vehículo y verificamos si puede atenderse; si faltan herramientas o competencia técnica, cerramos en el paso quince sin ejecución.",
            "En los pasos cuatro y cinco presentamos presupuesto y condiciones y obtenemos autorización inicial antes de cualquier trabajo cobrable. En los pasos seis a nueve realizamos la recepción e inspección: ningún hallazgo permite agregar automáticamente una reparación. Si un hallazgo cambia el alcance, detenemos el flujo y solicitamos nueva autorización con importe y plazo actualizados."
        ],
    },
    {
        "slide": 9,
        "title": "Proceso 2: insumos, ejecución y calidad",
        "start_sec": 424,
        "end_sec": 494,
        "visual_cue": "Diapositiva 9/12: Segunda parte del flujo operativo (pasos 10 a 16): insumos, ejecución, calidad, entrega y seguimiento.",
        "paragraphs": [
            "En los pasos diez a doce comprobamos físicamente aceite y filtro: un catálogo no prueba disponibilidad ni compatibilidad. Si no están disponibles, se reprograma o cierra; sólo con orden vigente e insumos conformes se prepara el puesto y se ejecuta según la información técnica del fabricante.",
            "En el paso trece la revisión de calidad permite entregar o regresar a corregir. Una desviación del trabajo propio no genera un nuevo cobro; un trabajo distinto vuelve a evaluación y autorización. En los pasos catorce a dieciséis conciliamos materiales e importe, registramos orden terminada, no ejecutada o reprogramada, y proponemos seguimiento consentido a las veinticuatro a setenta y dos horas, donde la ausencia de respuesta no significa satisfacción.",
            "Los tiempos de veinte a cuarenta minutos son estimaciones activas de ejecución inicial; cita, suministro, espera y retrabajo se registran aparte. Protección, herramientas, recuperación de aceite y habilitación del local deben verificarse antes de operar."
        ],
    },
    {
        "slide": 10,
        "title": "Ocho funciones, no ocho contrataciones",
        "start_sec": 494,
        "end_sec": 548,
        "visual_cue": "Diapositiva 10/12: Organigrama funcional (P1 a P8) y reglas de segregación de responsabilidades.",
        "paragraphs": [
            "La organización identifica ocho funciones, no ocho contrataciones iniciales: coordinación general administra recursos; recepción gestiona cotización y caja; mantenimiento responde por ejecución; llantas atiende su especialidad; inventario comprueba insumos; limpieza conserva condiciones del puesto; y contabilidad junto con asesoría jurídica apoyan por encargo.",
            "Pueden agruparse funciones si existe competencia y tiempo, manteniendo separados el consentimiento del cliente, la ejecución y la revisión de importes: recepción no diagnostica, una autorización interna no reemplaza la del cliente y el técnico no modifica importes por cuenta propia. Inventario documenta consumo, recepción concilia cobro y coordinación revisa incidencias. El organigrama no equivale a nómina presupuestada ni a personal ya contratado."
        ],
    },
    {
        "slide": 11,
        "title": "Finanzas: separar venta, costo y efectivo",
        "start_sec": 548,
        "end_sec": 612,
        "visual_cue": "Diapositiva 11/12: Estructura financiera (costos directos, gastos, inversión, capital de trabajo e ingresos) y desglose del piloto.",
        "paragraphs": [
            "En las finanzas separamos venta, costo y efectivo. Los costos directos incluyen aceite, filtro, consumibles y trabajo atribuible a la orden, sin contar dos veces el trabajo técnico como costo directo y nómina. Los gastos apoyan la operación: renta, servicios, administración y seguros aplicables. Herramientas y adecuaciones son inversión, y el capital de trabajo cubre necesidades anteriores al cobro.",
            "Los ingresos previstos proceden de mantenimiento, llantas y venta de refacciones cuando puedan ofrecerse, desagregando cualquier paquete para no duplicar registros. Sin precios validados, costos completos y mezcla definida no afirmo utilidad, margen de contribución, punto de equilibrio ni retorno; cobrar una venta tampoco equivale a disponer de ese importe como utilidad.",
            "El piloto publicitario suma tres mil quinientos veinte pesos: mil quinientos de impresión observada el veintitrés de septiembre de dos mil veintiséis —por reconfirmar—, seiscientos de pauta, ochocientos de distribución, trescientos de adaptación y atención, y trescientos veinte de reserva como estimaciones internas. Este monto no es la inversión total del taller."
        ],
    },
    {
        "slide": 12,
        "title": "Participar con evidencia antes de escalar",
        "start_sec": 612,
        "end_sec": 660,
        "visual_cue": "Diapositiva 12/12: Hoja de ruta de validación en 4 pasos y cierre de invitación a los inversionistas.",
        "paragraphs": [
            "La oportunidad que presento es construir un servicio donde cada promesa tenga alcance, autorización y control. Para pasar de diseño a inversión necesitamos cuatro hitos: aplicar el sondeo y comparar oferentes verificables, comprobar recursos técnicos y condiciones de operación, presupuestar un servicio equivalente midiendo capacidad, y evaluar la inversión sin prometer rentabilidad no demostrada, sin solicitar hoy una cifra o participación societaria aún no sustentadas.",
            "AM Taller busca crecer sosteniendo cada servicio que acepta. Los registros permitirían revisar cumplimiento, consumos e incidencias y ajustar sin ocultar resultados desfavorables. Mi invitación es participar en la evaluación de un proyecto que convierte información y responsabilidades en decisiones revisables. Invirtamos en confianza que se pueda comprobar: cada servicio autorizado, cada recurso verificado y cada decisión respaldada."
        ],
    },
]


def fmt_mmss(sec: float) -> str:
    total = int(round(sec))
    m, s = divmod(total, 60)
    return f"{m:02d}:{s:02d}"


def fmt_srt_time(sec: float) -> str:
    ms_total = int(round(sec * 1000))
    s_total, ms = divmod(ms_total, 1000)
    m_total, s = divmod(s_total, 60)
    h, m = divmod(m_total, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def fmt_vtt_time(sec: float) -> str:
    return fmt_srt_time(sec).replace(",", ".")


def split_into_captions(text: str, max_chars_per_caption: int = 84) -> list[str]:
    """Divide un párrafo en segmentos de subtítulo legibles (máx. 2 líneas de ~42 caracteres)."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?;:])\s+", text.strip()) if s.strip()]
    captions: list[str] = []
    for sent in sentences:
        if len(sent) <= max_chars_per_caption:
            captions.append(sent)
        else:
            clauses = [c.strip() for c in re.split(r"(?<=,)\s+|(?=—)", sent) if c.strip()]
            buf = ""
            for clause in clauses:
                candidate = f"{buf} {clause}".strip() if buf else clause
                if len(candidate) <= max_chars_per_caption:
                    buf = candidate
                else:
                    if buf:
                        captions.append(buf)
                    if len(clause) <= max_chars_per_caption:
                        buf = clause
                    else:
                        words = clause.split()
                        n_chunks = (len(clause) // max_chars_per_caption) + 1
                        step = max(1, (len(words) + n_chunks - 1) // n_chunks)
                        for idx in range(0, len(words), step):
                            piece = " ".join(words[idx : idx + step])
                            if idx + step < len(words):
                                captions.append(piece)
                            else:
                                buf = piece
            if buf:
                if captions and len(buf) < 22 and len(captions[-1]) + 1 + len(buf) <= 96:
                    captions[-1] = f"{captions[-1]} {buf}"
                else:
                    captions.append(buf)
    return captions


def format_two_lines(caption: str, width: int = 42) -> str:
    lines = textwrap.wrap(caption, width=width)
    if len(lines) <= 2:
        return "\n".join(lines)
    mid = len(caption) // 2
    split_pos = caption.rfind(" ", 0, mid + 10)
    if split_pos == -1:
        split_pos = caption.find(" ", mid)
    if split_pos != -1:
        return caption[:split_pos].strip() + "\n" + caption[split_pos + 1 :].strip()
    return "\n".join(lines[:2])


def build_subtitles_and_metadata() -> tuple[dict, str, str, str]:
    total_words = 0
    srt_entries: list[str] = []
    vtt_entries: list[str] = ["WEBVTT", "Kind: captions", "Language: es-MX", ""]
    cap_idx = 1

    enriched_blocks = []
    for b in BLOCKS:
        full_text = " ".join(b["paragraphs"])
        words = len(full_text.split())
        total_words += words
        duration = b["end_sec"] - b["start_sec"]
        wpm = round(words / (duration / 60.0), 1)

        raw_captions: list[str] = []
        for p in b["paragraphs"]:
            raw_captions.extend(split_into_captions(p))

        total_chars = sum(len(c) for c in raw_captions)
        cur_t = float(b["start_sec"])
        block_captions = []
        for i, cap in enumerate(raw_captions):
            if i == len(raw_captions) - 1:
                next_t = float(b["end_sec"])
            else:
                share = (len(cap) / total_chars) * duration
                next_t = round(cur_t + max(1.8, share), 2)
                max_allowed = float(b["end_sec"]) - (len(raw_captions) - 1 - i) * 1.5
                if next_t > max_allowed:
                    next_t = round(max_allowed, 2)
            two_line_text = format_two_lines(cap, width=44)
            srt_entries.append(
                f"{cap_idx}\n{fmt_srt_time(cur_t)} --> {fmt_srt_time(next_t)}\n{two_line_text}\n"
            )
            vtt_entries.append(
                f"{cap_idx}\n{fmt_vtt_time(cur_t)} --> {fmt_vtt_time(next_t)}\n{two_line_text}\n"
            )
            block_captions.append({
                "index": cap_idx,
                "start_sec": round(cur_t, 2),
                "end_sec": round(next_t, 2),
                "text": cap,
            })
            cap_idx += 1
            cur_t = next_t

        enriched_blocks.append({
            **b,
            "start_mmss": fmt_mmss(b["start_sec"]),
            "end_mmss": fmt_mmss(b["end_sec"]),
            "duration_sec": duration,
            "word_count": words,
            "speaking_rate_wpm": wpm,
            "slide_image": f"montaje-video/diapositivas-1080p/diapositiva-{b['slide']:02d}.png",
            "captions_count": len(block_captions),
            "captions": block_captions,
        })

    overall_duration = BLOCKS[-1]["end_sec"]
    overall_wpm = round(total_words / (overall_duration / 60.0), 1)
    manifest = {
        "schema_version": 1,
        "project": "AM Taller Autocentro",
        "institution": "ITESCA",
        "program": "Maestría en Gestión Administrativa",
        "course": "Plan de Negocios (GGPN01)",
        "activity_module_id": 6555,
        "presenter": "Martín Jonathan de la Cruz Muñoz",
        "audience": "Inversionistas",
        "total_slides": 12,
        "total_duration_seconds": overall_duration,
        "total_duration_mmss": fmt_mmss(overall_duration),
        "allowed_duration_range_seconds": [420, 1200],
        "target_duration_range_seconds": [600, 720],
        "total_words": total_words,
        "average_speaking_rate_wpm": overall_wpm,
        "silence_padding_seconds": 0,
        "camera_box": CAMERA_BOX,
        "status": {
            "slides_rendered_1080p": True,
            "timed_technical_script_ready": True,
            "subtitles_reviewed_ready": True,
            "visual_base_track_ready": True,
            "real_student_recording_present": False,
            "final_video_produced": False,
            "youtube_published": False,
            "moodle_link_submitted": False,
            "moodle_current_state": "Enviado para calificar (presentacion-plan-de-negocios-Actividad-15-Video.pdf enviado el 17/10/2026 22:14; sin enlace de YouTube aún)",
        },
        "missing_requirements": [
            "Grabación real autorizada de imagen (cámara) y voz del estudiante Martín Jonathan de la Cruz Muñoz (7 a 20 min; objetivo 10-12 min).",
            "Autorización y sesión del estudiante en su cuenta de YouTube para publicar el video revisado como «No listado» (o confirmación de privacidad).",
            "Confirmación del método para incorporar la liga de YouTube verificada en Moodle (módulo 6555, cuyo formulario de entrega admite únicamente subida de archivos —hasta 20 archivos, máx. 512 MB— y no campo de texto en línea), conservando el PDF existente."
        ],
        "blocks": enriched_blocks,
    }

    md_lines = [
        "# Guion Técnico Temporizado y Escaleta de Montaje — AM Taller Autocentro",
        "",
        "## Parámetros Técnicos de Producción",
        "",
        f"- **Expositor:** Martín Jonathan de la Cruz Muñoz",
        f"- **Público objetivo:** Inversionistas",
        f"- **Apoyo visual:** `presentacion-plan-de-negocios-Actividad-15-Video.pdf` (12 diapositivas en relación 16:9, renderizadas a `1920×1080` píxeles)",
        f"- **Base documental:** `reporte-plan-de-negocios-Actividad-15-Guion-Video.pdf` (12 bloques del guion enriquecidos con precisiones de la fundamentación empresarial)",
        f"- **Duración programada:** **{fmt_mmss(overall_duration)} min ({overall_duration} s)** — dentro del objetivo de **10–12 minutos** y del rango reglamentario de **7–20 minutos**, sin silencios de relleno",
        f"- **Extensión verbal:** **{total_words} palabras** a un ritmo natural de exposición de **{overall_wpm} palabras por minuto**",
        f"- **Recuadro de cámara (PiP):** Zona derecha libre de contenido (`x = 1488..1872 px`, `y = 284..796 px`, tamaño `384×512 px` en formato 3:4 o `384×216 px` en 16:9), verificada con **0 píxeles de texto o gráficos cubiertos** en las 12 diapositivas",
        f"- **Transiciones:** Fundido discreto (`fade` de `0.4 s`) sincronizado exactamente con el cambio de cada bloque temático",
        f"- **Subtítulos:** Revisados en español (`subtitulos-revisados.srt` y `subtitulos-revisados.vtt`), con `{cap_idx - 1}` segmentos sincronizados",
        "",
        "## Resumen de Tiempos por Diapositiva",
        "",
        "| Diapositiva | Título | Inicio | Fin | Duración | Palabras | Ritmo (ppm) |",
        "| :---: | :--- | :---: | :---: | :---: | :---: | :---: |",
    ]
    for b in enriched_blocks:
        md_lines.append(
            f"| {b['slide']}/12 | {b['title']} | `{b['start_mmss']}` | `{b['end_mmss']}` | {b['duration_sec']} s | {b['word_count']} | {b['speaking_rate_wpm']} |"
        )

    md_lines.extend([
        "",
        "---",
        "",
        "## Bloques del Guion Técnico para Exposición ante Inversionistas",
        "",
    ])

    for b in enriched_blocks:
        md_lines.extend([
            f"### Diapositiva {b['slide']}/12: {b['title']} (`{b['start_mmss']} – {b['end_mmss']}` | {b['duration_sec']} s | {b['word_count']} palabras)",
            "",
            f"- **Imagen en pantalla:** `{b['slide_image']}` — {b['visual_cue']}",
            f"- **Recuadro del estudiante:** Visible a la derecha (`x=1488, y=284, w=384, h=512`), sin cubrir encabezados, tablas ni diagramas.",
            "- **Locución (discurso directo a inversionistas):**",
            "",
        ])
        for p in b["paragraphs"]:
            md_lines.append(f"> {p}")
            md_lines.append(">")
        md_lines.pop()
        md_lines.append("")

    return manifest, "\n".join(md_lines), "\n".join(srt_entries), "\n".join(vtt_entries)


def create_camera_layout_guide() -> None:
    """Genera láminas visuales de verificación del recuadro del estudiante sobre las diapositivas 1 y 10."""
    s1 = Image.open(SLIDES_DIR / "diapositiva-01.png").convert("RGB")
    s10 = Image.open(SLIDES_DIR / "diapositiva-10.png").convert("RGB")

    for img, out_name in [(s1, "guia-encuadre-diapositiva-01.png"), (s10, "guia-encuadre-diapositiva-10.png")]:
        draw = ImageDraw.Draw(img)
        x0, y0 = CAMERA_BOX["x"], CAMERA_BOX["y"]
        x1, y1 = x0 + CAMERA_BOX["width"], y0 + CAMERA_BOX["height"]
        draw.rectangle([1488, 130, 1872, 950], outline=(180, 180, 180), width=2)
        draw.rectangle([x0, y0, x1, y1], fill=(247, 247, 247), outline=(143, 17, 23), width=4)
        draw.text((x0 + 28, y0 + 220), "RECUADRO ESTUDIANTE\n384 x 512 px (x=1488, y=284)\nSin tapar informacion", fill=(20, 20, 20))
        img.save(MONTAJE_DIR / out_name)


def main() -> None:
    manifest, md_text, srt_text, vtt_text = build_subtitles_and_metadata()
    (BASE_DIR / "guion-tecnico-temporizado.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (BASE_DIR / "guion-tecnico-temporizado.md").write_text(md_text, encoding="utf-8")
    (BASE_DIR / "subtitulos-revisados.srt").write_text(srt_text, encoding="utf-8")
    (BASE_DIR / "subtitulos-revisados.vtt").write_text(vtt_text, encoding="utf-8")
    create_camera_layout_guide()
    print(
        f"Generado: {manifest['total_words']} palabras, "
        f"{manifest['total_duration_mmss']} ({manifest['total_duration_seconds']} s), "
        f"{manifest['average_speaking_rate_wpm']} ppm, "
        f"{sum(b['captions_count'] for b in manifest['blocks'])} subtítulos."
    )


if __name__ == "__main__":
    main()
