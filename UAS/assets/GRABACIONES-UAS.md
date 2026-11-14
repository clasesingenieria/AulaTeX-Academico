# Auditoría y Trazabilidad Canónica de Grabaciones UAS (Moodle FCA)

**Fecha de actualización:** `2026-11-14` | **Agente responsable:** `RecordingsTranscriptionAgent` (`aulatex`)

## 1. Resumen Ejecutivo por Curso en Moodle FCA (`virtual.uas.edu.mx/fca`)

| Curso ID | Asignatura (`slug`) | Docente Titular | Páginas Aula Consultadas | Videos de Apoyo Externo | Grabaciones de Clase del Grupo | Estado de Transcripción y Evidencia Visual |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **`635`** | `herramientas-digitales` (`2026_I_Herramientas digitales_LCP`) | Dr. Dámaso Guadalupe Ruíz González | 45 páginas + Mensajería (`conv=3242`) | 3 manuales PDF en Drive (`Complemento de LCP - Aplicado`) | **11 sesiones identificadas** (4 `.mp4` en Drive descargados localmente + 7 enlaces de clase en YouTube) | **4/4 MP4 locales transcritos (`SRT` + `TXT`)**, `0.00 s` de desfase, **16 capturas PNG** en `capturas-clase/` |
| **`632`** | `derecho-mercantil` (`2026_I_Derecho mercantil_LCP`) | Docente titular en plataforma FCA | 51 páginas (`HTTP 200`) | **16 videos de apoyo externo** (`Videos_S1` a `Videos_S4`: Carbonell, Lifeder, EBC, etc.) | `0` sesiones grabadas del grupo confirmadas en el aula | Inventario de apoyos externos verificado (`verificacion-grabaciones-2026-10-12.json`) |
| **`634`** | `investigacion-aplicada-a-la-contaduria` (`2026_I_INV_APLIC_CONT_LCP`) | Docente titular en plataforma FCA | 48 páginas (`HTTP 200`) | **1 video externo** (`f5k6Df-MUr0`, 2019) + **1 lista TEDx** (`id=50060`) | `0` sesiones grabadas del grupo confirmadas en el aula | Inventario de apoyos externos verificado (`verificacion-grabaciones-2026-10-12.json`) |

---

## 2. Validación de Trazabilidad y Sincronización Temporal en `herramientas-digitales` (Curso `635`)

### 2.1 Grabación Principal Canónica (`clase-1NaR_KBkiiZRg3ioHxiSRJw_GMqCDf2rD`)
- **Ruta canónica:** `licenciatura-en-contaduria-uas/herramientas-digitales/referencias-herramientas-digitales/grabaciones/clase-1NaR_KBkiiZRg3ioHxiSRJw_GMqCDf2rD/`
- **Archivo de video (`video1860556015.mp4`):** `576,107,859 bytes` (`549.42 MiB`), duración exacta `ffprobe`: `5137.52 s` (`01:25:37.520`), `SHA-256`: `216e0a8eda11aa5fa78479600def35bb457fafcb460583047ce14e9a465a8b2d`.
- **Subtítulos (`transcripcion.srt`):** `164,295 bytes` (`160.44 KiB`), `2,084` segmentos numerados (`00:00:01,020` a `01:25:37,030`), `SHA-256`: `3319dc3dfde28c5304ab44a8e9e9ed4416dcf75e5a12f0fb2232c17c03e88c7a`.
- **Texto continuo (`transcripcion.txt`):** `109,132 bytes` (`106.57 KiB`), `SHA-256`: `c028eff5f5627cdf0fdb30139963d54e08c2a98a8274bd217f1485ae3029ee23`.
- **Auditoría de sincronización temporal (`validate_srt_alignment`):**
  - Segmentos con duración nula o negativa: **`0`** (el segmento `#965` en `00:42:51,380` fue reparado preventivamente ampliando `+100 ms` a `00:42:51,480`, documentado en `control/transcripcion - reparaciones.json`).
  - Segmentos fuera de orden o con traslape temporal: **`0`**.
  - Diferencia entre fin del último subtítulo (`5137.03 s`) y duración total del contenedor MP4 (`5137.52 s`): **`0.49 s`** (sin desfasamiento de tiempos).

### 2.2 Grabaciones de Apoyo en Vivo (Google Drive -> Local MP4 + SRT + TXT)
1. **S2 - Solicitud de Correo Institucional `@ms.uas.edu.mx` y Práctica Zoom (`1a-HF6zBZDirjqIhYdxHZPFXnHxbQTAfQ`):** `36.99 MB`, `561.20 s` (`00:09:21`), `212` bloques SRT (`0` traslapes).
2. **S2 - Registro al Sistema Institucional `siiFCA` (`1WF4KxUllV-Rfs6rHtPCvmoiSZErpn6ZW`):** `51.75 MB`, `1027.32 s` (`00:17:07`), `408` bloques SRT (`0` traslapes).
3. **S3 - Activación de Cuenta e Instalación de Microsoft 365 (`1fIBZxP9E4rWCzpjGgrMsLtNTaVCEJNF4`):** `155.19 MB`, `2279.05 s` (`00:37:59`), `981` bloques SRT (`0` traslapes).

### 2.3 Evidencia Visual Extraída (`capturas-clase/`)
- Se extrajeron **16 fotogramas `.png`** mediante `FFmpeg` en los timestamps exactos dictados por el docente y se almacenaron en:
  `licenciatura-en-contaduria-uas/herramientas-digitales/referencias-herramientas-digitales/notas-herramientas-digitales/materiales-aula/capturas-clase/`
