# Presentación video del plan de negocios (Actividad 15 — Módulo 6555)

## Estado vigente y distinción de etapas (17/10/2026, 23:31)

| Etapa | Estado actual | Evidencia / Archivo |
| :--- | :--- | :--- |
| **1. Material documental (PDF)** | **Preparado** | [Presentación de 12 diapositivas](../../../presentacion-plan-de-negocios-Actividad-15-Video.pdf) y [Reporte con fundamentación y guion](../../../reporte-plan-de-negocios-Actividad-15-Guion-Video.pdf) |
| **2. Guion técnico temporizado y subtítulos** | **Preparado** | [Guion técnico 11:00 min](guion-tecnico-temporizado.md), [Manifiesto JSON](guion-tecnico-temporizado.json), [Subtítulos SRT](subtitulos-revisados.srt) y [Subtítulos VTT](subtitulos-revisados.vtt) |
| **3. Montaje visual base y automatización FFmpeg** | **Preparado (solo pista visual)** | [Pista visual 1080p de 11:00](montaje-video/pista-visual-diapositivas-11m00s.mp4), [Script de ensamble PiP](montaje-video/ensamblar_video_real.py) y [Verificación de montaje](montaje-video/verificacion-montaje.json) |
| **4. Video final con estudiante en cámara y voz** | **Pendiente (bloqueado por falta de grabación real)** | Requiere grabación real autorizada de imagen y voz de Martín Jonathan de la Cruz Muñoz (7–20 min; objetivo 10–12 min). No se usa avatar ni voz sintética. |
| **5. Publicación en YouTube** | **No publicado** | Requiere el video completo revisado y sesión autorizada en YouTube (propuesta: visibilidad **No listado**). |
| **6. Entrega en Moodle (id=6555)** | **PDF entregado; enlace de YouTube pendiente** | Estado verificado: **Enviado para calificar** con `presentacion-plan-de-negocios-Actividad-15-Video.pdf` (17/10/2026, 22:14). [Consulta actual sin secretos](evidencias/2026-10-17/consulta-actual/inspection.json) y [Recibo de envío previo](evidencias/2026-10-17/envio/6555-receipt.json). |

---

## Consulta autenticada del estado actual en Moodle (17/10/2026)

- **Módulo consultado:** `https://cursos3.e-itesca.edu.mx/mod/assign/view.php?id=6555` (curso 213, solo lectura mediante bóveda institucional AulaTeX, sin exponer secretos).
- **Estado de la entrega:** `Enviado para calificar` (Intento 1, `Sin calificar`).
- **Archivo actualmente entregado:** `presentacion-plan-de-negocios-Actividad-15-Video.pdf` (enviado el sábado 17 de octubre de 2026 a las 22:14, 1 hora y 44 minutos antes de la fecha límite de las 23:59; SHA-256 `ae111e54101994f046933d3d370d848ca6fb4d780ccb5d8601db15a0337a7d01`).
- **Opciones permitidas por el formulario de Moodle (`editsubmission`):** La actividad tiene habilitado únicamente el plugin de **Archivos enviados** (`assignsubmission_file`: hasta **20 archivos**, tamaño máximo **512 MB**) y **no tiene habilitado** campo de texto en línea (`assignsubmission_onlinetext = 0`).
- **Conservación de la entrega:** No se modificó, reemplazó ni eliminó el PDF entregado, ni se utilizaron comentarios de entrega como sustituto. Cuando estén listos el video y el enlace de YouTube verificado, se podrá agregar al área de archivos un documento/PDF con el enlace activo (o actualizar el paquete de archivos conservando `presentacion-plan-de-negocios-Actividad-15-Video.pdf`).

---

## Paquete de producción preparado

1. **Guion técnico temporizado ([guion-tecnico-temporizado.md](guion-tecnico-temporizado.md) / [guion-tecnico-temporizado.json](guion-tecnico-temporizado.json)):**
   - **Duración programada:** `11:00` (`660 s`), dentro del objetivo de `10–12 minutos` y del rango obligatorio de `7–20 minutos`, con `0 s` de silencios artificiales.
   - **Extensión y ritmo:** `1,459 palabras` distribuidas en 12 bloques sincronizados con las 12 diapositivas (`132.6 palabras/minuto`).
   - **Enfoque y rigor:** Discurso dirigido directamente a inversionistas, sin metadiscurso académico ni referencias al uso de IA o a la plataforma. Distingue expresamente entre datos observados (Censo INEGI 2020: `1,142,994` habitantes y `329,095` viviendas habitadas en Monterrey; autoría propia del logotipo confirmada el `23/09/2026`; precio publicado de impresión de `1,500 MXN` observado el `23/09/2026` por reconfirmar), escenarios/estimaciones de diseño (metas de `360` a `720` servicios y `240` a `480` clientes con `1.5` servicios/persona/año; capacidad hipotética de `900` servicios anuales; `20–40 minutos` de ejecución activa; resto del piloto publicitario por `3,520 MXN`), y validaciones pendientes (sondeo real de demanda de 22 preguntas, fichas comparables de 16 ítems de oferta, domicilio operativo, cotizaciones de equipo/local, precios, costos completos, punto de equilibrio y rentabilidad).

2. **Subtítulos revisados ([subtitulos-revisados.srt](subtitulos-revisados.srt) / [subtitulos-revisados.vtt](subtitulos-revisados.vtt)):**
   - `184` segmentos en español con ortografía, puntuación y cifras revisadas, balanceados en un máximo de dos líneas por subtítulo para lectura clara tanto en el contenedor MP4 como en YouTube.

3. **Diapositivas 1080p, encuadre del recuadro y pista visual base (`montaje-video/`):**
   - [Diapositivas 01 a 12 en 1920×1080 PNG](montaje-video/diapositivas-1080p/).
   - **Recuadro reservado para la cámara del estudiante:** `x = 1488..1872 px`, `y = 284..796 px` (`384×512 px` en relación 3:4, o `384×216 px` en 16:9 dentro de la misma franja derecha `x >= 1488 px`), comprobado programáticamente con **0 píxeles de texto, tablas o figuras cubiertos** en las 12 láminas. Véanse [guía de encuadre en diapositiva 1](montaje-video/guia-encuadre-diapositiva-01.png) y [guía de encuadre en diapositiva 10](montaje-video/guia-encuadre-diapositiva-10.png).
   - **Pista visual base ([pista-visual-diapositivas-11m00s.mp4](montaje-video/pista-visual-diapositivas-11m00s.mp4)):** Video H.264 `1920×1080` de `660.0 s` (`11:00`) con transiciones discretas de `0.35 s` y pista de subtítulos en español integrada (`mov_text`), SHA-256 `2fa8cbb46473abae84de5f5d8f6c6ac4f00bf5bcc08600707c4c185d2ddcaa64`. **Este archivo es únicamente la base visual de apoyo y no constituye el video final entregable.**

---

## Grabación y autorizaciones requeridas para finalizar

1. **Grabación real autorizada del estudiante (imagen y voz):**
   - Grabar en cámara y micrófono la lectura natural de los 12 bloques de [guion-tecnico-temporizado.md](guion-tecnico-temporizado.md) (objetivo: `10–12 minutos`; rango permitido: `7–20 minutos`), ya sea:
     - **Opción A (montaje automático con el paquete preparado):** Grabar únicamente la cámara y voz del estudiante (`grabacion-estudiante.mp4`) siguiendo los tiempos de la escaleta y ejecutar:
       ```powershell
       .\.venv\Scripts\python.exe ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga/referencias-plan-de-negocios/notas-plan-de-negocios/actividad-15-presentacion-video/montaje-video/ensamblar_video_real.py --grabacion ruta\a\grabacion-estudiante.mp4
       ```
     - **Opción B (grabación directa en Zoom, Meet u OBS):** Compartir `presentacion-plan-de-negocios-Actividad-15-Video.pdf` en pantalla completa, ubicar el recuadro de la cámara en el tercio derecho libre (`x >= 78%` del ancho, entre la barra superior de título y el pie de página) y exportar el archivo `.mp4`.
2. **Publicación en YouTube y confirmación de privacidad:**
   - Subir el video completo revisado y el archivo [subtitulos-revisados.srt](subtitulos-revisados.srt) a la cuenta de YouTube autorizada por el estudiante, seleccionando privacidad **No listado** (propuesta recomendada para que la docente pueda reproducirlo mediante el enlace sin indexarlo públicamente).
   - Verificar la reproducción del enlace en una ventana sin sesión activa.
3. **Incorporación del enlace en Moodle:**
   - Compartir el enlace verificado de YouTube y autorizar la actualización de la entrega en Moodle (agregando el documento con la liga de YouTube junto al archivo `presentacion-plan-de-negocios-Actividad-15-Video.pdf` ya enviado).