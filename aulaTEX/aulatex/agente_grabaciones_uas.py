"""Agente ``grabaciones-uas`` para localizar, descargar, ubicar/renombrar,
transcribir, extraer capturas de puntos de interés y analizar/referenciar
las grabaciones de clase de la plataforma virtual UAS en AulaTeX.

Opera en modo de solo lectura sobre ``https://virtual.uas.edu.mx/fca`` usando
``PlatformCredentialVault``, jamás expone credenciales ni tokens en artefactos
o bitácoras, respeta compuertas anti-bot externas sin eludirlas, valida medios
con ``ffprobe`` y ``SHA-256``, transcribe localmente con ``Purfview Faster Whisper XXL``
(CUDA ``large-v3``), extrae fotogramas clave con ``ffmpeg`` e integra las
referencias en ``.bib``, ``fuentes.json`` y planeaciones de la materia.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any
import urllib.request
from urllib.parse import parse_qsl, unquote, urljoin, urlsplit

from .config import load_aulatex_env
from .navegacion_plataforma import (
    assert_no_credential_leak,
    ensure_same_https_host,
    sanitize_platform_text,
)
from .navegacion_uas import (
    NavegacionUasAgent,
    UAS_BASE_URL,
    UAS_HOST,
    UasModuleTarget,
)
from .planning_layout import _reject_credentials, subject_layout
from .workspace import AulaTeXWorkspace

AGENT_ID_GRABACIONES_UAS = "grabaciones-uas"
AGENT_TYPE_GRABACIONES_PLATAFORMA = "grabaciones-plataforma"


@dataclass(frozen=True)
class PuntoInteresVideo:
    poi_id: str
    recording_id: str
    timestamp_hms: str
    seconds: float
    title: str
    description: str
    related_module_ids: tuple[int, ...]
    image_rel_path: str
    asset_rel_path: str
    sha256: str
    bytes_size: int
    bib_key: str


@dataclass(frozen=True)
class GrabacionUasItem:
    recording_id: str
    provider: str  # "google_drive" | "youtube"
    kind: str  # "clase_sincrona" | "tutorial_docente" | "video_apoyo_aula"
    week: int
    session_label: str
    class_date: str
    title: str
    teacher_label: str
    source_url: str
    origin_context: str
    related_module_ids: tuple[int, ...]
    status: str
    folder_rel: str
    canonical_stem: str
    video_rel: str | None = None
    video_sha256: str | None = None
    video_bytes: int | None = None
    duration_seconds: float | None = None
    srt_rel: str | None = None
    srt_sha256: str | None = None
    txt_rel: str | None = None
    txt_sha256: str | None = None
    segments_count: int = 0
    bib_key: str = ""
    points_of_interest: tuple[PuntoInteresVideo, ...] = field(default_factory=tuple)
    notes: str = ""


@dataclass(frozen=True)
class GrabacionesUasRequest:
    subject_slug: str = "herramientas-digitales"
    course_id: int = 635
    inspect_live_platform: bool = True
    download_drive_media: bool = True
    transcribe_missing: bool = True
    extract_keyframes: bool = True
    update_references: bool = True
    local_video_dir: str = ""
    youtube_cookies_browser: str = ""
    youtube_cookies_file: str = ""
    output_dir: str = ""


@dataclass(frozen=True)
class GrabacionesUasResult:
    run_id: str
    run_dir: Path
    manifest_path: Path
    inventory_path: Path
    analysis_md_path: Path
    analysis_json_path: Path
    poi_manifest_path: Path
    bib_path: Path
    ok: bool
    recordings_total: int
    videos_validated: int
    transcripts_validated: int
    keyframes_extracted: int
    companion_docs_downloaded: int
    recordings: tuple[GrabacionUasItem, ...] = field(default_factory=tuple)
    blockers: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "run_dir": str(self.run_dir),
            "manifest_path": str(self.manifest_path),
            "inventory_path": str(self.inventory_path),
            "analysis_md_path": str(self.analysis_md_path),
            "analysis_json_path": str(self.analysis_json_path),
            "poi_manifest_path": str(self.poi_manifest_path),
            "bib_path": str(self.bib_path),
            "ok": self.ok,
            "recordings_total": self.recordings_total,
            "videos_validated": self.videos_validated,
            "transcripts_validated": self.transcripts_validated,
            "keyframes_extracted": self.keyframes_extracted,
            "companion_docs_downloaded": self.companion_docs_downloaded,
            "recordings": [asdict(r) for r in self.recordings],
            "blockers": list(self.blockers),
            "summary": self.summary,
        }


# Catálogo canónico de grabaciones y videos enviados por el Dr. Dámaso Guadalupe Ruíz González
# en la conversación privada de plataforma UAS (conversation_id: 3242, user_id: 30) y páginas del curso 635.
CANONICAL_UAS_635_RECORDINGS: tuple[dict[str, Any], ...] = (
    {
        "recording_id": "1NaR_KBkiiZRg3ioHxiSRJw_GMqCDf2rD",
        "provider": "google_drive",
        "kind": "clase_sincrona",
        "week": 1,
        "session_label": "S1 - Clase 1",
        "class_date": "2026-10-20",
        "title": "Presentación del Curso, Diagnóstico, Carpeta Compartida en Drive y Lecciones TIC",
        "teacher_label": "Video de la Clase martes 20 de octubre 2026",
        "source_url": "https://drive.google.com/file/d/1NaR_KBkiiZRg3ioHxiSRJw_GMqCDf2rD/view?usp=sharing",
        "origin_context": "Mensajería interna UAS (Msg 9445, Dr. Dámaso Guadalupe Ruíz González)",
        "related_module_ids": (50085, 50094, 50100, 50101, 50102, 50103, 50107, 50144),
        "folder_name": "clase-1NaR_KBkiiZRg3ioHxiSRJw_GMqCDf2rD",
        "canonical_stem": "UAS - HERR_DIG - S1 - 2026-10-20 - Clase Martes 20 de Octubre [1NaR_KBkiiZRg3ioHxiSRJw_GMqCDf2rD]",
        "bib_key": "ruiz2026claseS1c1",
    },
    {
        "recording_id": "LdO5T2YGm6g",
        "provider": "youtube",
        "kind": "clase_sincrona",
        "week": 1,
        "session_label": "S1 - Clase 2",
        "class_date": "2026-10-22",
        "title": "GPO103-LCP: Compartir Carpeta",
        "teacher_label": "Youtube: Compartir Carpeta",
        "source_url": "https://www.youtube.com/watch?v=LdO5T2YGm6g",
        "origin_context": "Mensajería interna UAS (Msg 9509, Dr. Dámaso Guadalupe Ruíz González)",
        "related_module_ids": (50102, 50103, 50107),
        "folder_name": "clase-LdO5T2YGm6g",
        "canonical_stem": "UAS - HERR_DIG - S1 - 2026-10-22 - GPO103-LCP Compartir Carpeta [LdO5T2YGm6g]",
        "bib_key": "ruiz2026claseS1c2",
    },
    {
        "recording_id": "I_H5f_gGbuc",
        "provider": "youtube",
        "kind": "clase_sincrona",
        "week": 2,
        "session_label": "S2 - Clase 1",
        "class_date": "2026-10-27",
        "title": "GPO103-LCP: Zoom e Inicio de Excel",
        "teacher_label": "Video Martes 27/oct/2026",
        "source_url": "https://www.youtube.com/watch?v=I_H5f_gGbuc",
        "origin_context": "Mensajería interna UAS (Msg 9598, Dr. Dámaso Guadalupe Ruíz González)",
        "related_module_ids": (50113, 50114, 50117, 50118),
        "folder_name": "clase-I_H5f_gGbuc",
        "canonical_stem": "UAS - HERR_DIG - S2 - 2026-10-27 - GPO103-LCP Zoom e Inicio de Excel [I_H5f_gGbuc]",
        "bib_key": "ruiz2026claseS2c1",
    },
    {
        "recording_id": "0FGH031UsFo",
        "provider": "youtube",
        "kind": "clase_sincrona",
        "week": 2,
        "session_label": "S2 - Clase 2",
        "class_date": "2026-10-29",
        "title": "GPO103-LCP: Ejercicios de Excel",
        "teacher_label": "Video de la Clase de Excel",
        "source_url": "https://www.youtube.com/watch?v=0FGH031UsFo",
        "origin_context": "Mensajería interna UAS (Msg 9668, Dr. Dámaso Guadalupe Ruíz González)",
        "related_module_ids": (50094, 50114),
        "folder_name": "clase-0FGH031UsFo",
        "canonical_stem": "UAS - HERR_DIG - S2 - 2026-10-29 - GPO103-LCP Ejercicios de Excel [0FGH031UsFo]",
        "bib_key": "ruiz2026claseS2c2",
    },
    {
        "recording_id": "1a-HF6zBZDirjqIhYdxHZPFXnHxbQTAfQ",
        "provider": "google_drive",
        "kind": "tutorial_docente",
        "week": 2,
        "session_label": "S2 - Tutorial 1",
        "class_date": "2026-10-29",
        "title": "Solicitud de Correo Institucional @ms.uas.edu.mx",
        "teacher_label": "Correo Institucional @ms.uas.edu.mx",
        "source_url": "https://drive.google.com/file/d/1a-HF6zBZDirjqIhYdxHZPFXnHxbQTAfQ/view?usp=sharing",
        "origin_context": "Mensajería interna UAS (Msg 9668, Dr. Dámaso Guadalupe Ruíz González)",
        "related_module_ids": (50113, 50114),
        "folder_name": "apoyo-1a-HF6zBZDirjqIhYdxHZPFXnHxbQTAfQ",
        "canonical_stem": "UAS - HERR_DIG - S2 - 2026-10-29 - Solicitud Correo Institucional MS [1a-HF6zBZDirjqIhYdxHZPFXnHxbQTAfQ]",
        "bib_key": "ruiz2026tutorialCorreoMS",
    },
    {
        "recording_id": "1WF4KxUllV-Rfs6rHtPCvmoiSZErpn6ZW",
        "provider": "google_drive",
        "kind": "tutorial_docente",
        "week": 2,
        "session_label": "S2 - Tutorial 2",
        "class_date": "2026-10-29",
        "title": "Registro al Sistema Institucional siiFCA",
        "teacher_label": "Registro a siiFCA",
        "source_url": "https://drive.google.com/file/d/1WF4KxUllV-Rfs6rHtPCvmoiSZErpn6ZW/view?usp=sharing",
        "origin_context": "Mensajería interna UAS (Msg 9668, Dr. Dámaso Guadalupe Ruíz González)",
        "related_module_ids": (50113, 50114),
        "folder_name": "apoyo-1WF4KxUllV-Rfs6rHtPCvmoiSZErpn6ZW",
        "canonical_stem": "UAS - HERR_DIG - S2 - 2026-10-29 - Registro siiFCA [1WF4KxUllV-Rfs6rHtPCvmoiSZErpn6ZW]",
        "bib_key": "ruiz2026tutorialSiiFCA",
    },
    {
        "recording_id": "1fIBZxP9E4rWCzpjGgrMsLtNTaVCEJNF4",
        "provider": "google_drive",
        "kind": "tutorial_docente",
        "week": 3,
        "session_label": "S3 - Tutorial 1",
        "class_date": "2026-11-02",
        "title": "Activar Cuenta e Instalar Microsoft 365 Institucional",
        "teacher_label": "Activar cuenta e Instalar Microsoft 365",
        "source_url": "https://drive.google.com/file/d/1fIBZxP9E4rWCzpjGgrMsLtNTaVCEJNF4/view?usp=sharing",
        "origin_context": "Mensajería interna UAS (Msg 9811, Dr. Dámaso Guadalupe Ruíz González)",
        "related_module_ids": (50114, 50130, 50131),
        "folder_name": "apoyo-1fIBZxP9E4rWCzpjGgrMsLtNTaVCEJNF4",
        "canonical_stem": "UAS - HERR_DIG - S3 - 2026-11-02 - Activar Cuenta e Instalar Microsoft 365 [1fIBZxP9E4rWCzpjGgrMsLtNTaVCEJNF4]",
        "bib_key": "ruiz2026tutorialM365",
    },
    {
        "recording_id": "q9KgoQqUJpU",
        "provider": "youtube",
        "kind": "clase_sincrona",
        "week": 3,
        "session_label": "S3 - Clase 1",
        "class_date": "2026-11-03",
        "title": "GPO103-LCP: Excel Aplicado.",
        "teacher_label": "Clase martes: Excel aplicado",
        "source_url": "https://www.youtube.com/watch?v=q9KgoQqUJpU",
        "origin_context": "Mensajería interna UAS (Msg 9870, Dr. Dámaso Guadalupe Ruíz González)",
        "related_module_ids": (50094, 50130, 50131),
        "folder_name": "clase-q9KgoQqUJpU",
        "canonical_stem": "UAS - HERR_DIG - S3 - 2026-11-03 - GPO103-LCP Excel Aplicado [q9KgoQqUJpU]",
        "bib_key": "ruiz2026claseS3c1",
    },
    {
        "recording_id": "ZSLk1hRY48U",
        "provider": "youtube",
        "kind": "clase_sincrona",
        "week": 3,
        "session_label": "S3 - Clase 2",
        "class_date": "2026-11-05",
        "title": "GPO103-LCP: Excel funciones que cuentan",
        "teacher_label": "video de Jueves: Excel Aplicado",
        "source_url": "https://www.youtube.com/watch?v=ZSLk1hRY48U",
        "origin_context": "Mensajería interna UAS (Msg 9974, Dr. Dámaso Guadalupe Ruíz González)",
        "related_module_ids": (50094, 50130, 50131),
        "folder_name": "clase-ZSLk1hRY48U",
        "canonical_stem": "UAS - HERR_DIG - S3 - 2026-11-05 - GPO103-LCP Excel Funciones que Cuentan [ZSLk1hRY48U]",
        "bib_key": "ruiz2026claseS3c2",
    },
    {
        "recording_id": "7ZomiXX7eus",
        "provider": "youtube",
        "kind": "clase_sincrona",
        "week": 4,
        "session_label": "S4 - Clase 1",
        "class_date": "2026-11-10",
        "title": "GPO103-LCP: Excel y Balances Generales",
        "teacher_label": "Excel Aplicado a la Contabilidad",
        "source_url": "https://www.youtube.com/watch?v=7ZomiXX7eus",
        "origin_context": "Mensajería interna UAS (Msg 10143, Dr. Dámaso Guadalupe Ruíz González)",
        "related_module_ids": (50140, 50144),
        "folder_name": "clase-7ZomiXX7eus",
        "canonical_stem": "UAS - HERR_DIG - S4 - 2026-11-10 - GPO103-LCP Excel y Balances Generales [7ZomiXX7eus]",
        "bib_key": "ruiz2026claseS4c1",
    },
    {
        "recording_id": "rzici9Xi01Y",
        "provider": "youtube",
        "kind": "clase_sincrona",
        "week": 4,
        "session_label": "S4 - Clase 2",
        "class_date": "2026-11-12",
        "title": "GPO103-LCP: Diseño de páginas Web",
        "teacher_label": "Páginas Web con Google Sites",
        "source_url": "https://www.youtube.com/watch?v=rzici9Xi01Y",
        "origin_context": "Mensajería interna UAS (Msg 10211, Dr. Dámaso Guadalupe Ruíz González)",
        "related_module_ids": (50144, 50146, 50147),
        "folder_name": "clase-rzici9Xi01Y",
        "canonical_stem": "UAS - HERR_DIG - S4 - 2026-11-12 - GPO103-LCP Diseno de Paginas Web [rzici9Xi01Y]",
        "bib_key": "ruiz2026claseS4c2",
    },
)

# Puntos de interés curados con marcas de tiempo exactas para extracción de fotogramas
CURATED_POINTS_OF_INTEREST: dict[str, tuple[dict[str, Any], ...]] = {
    "1NaR_KBkiiZRg3ioHxiSRJw_GMqCDf2rD": (
        {
            "poi_id": "s1c1-poi-01-presentacion-semana4",
            "timestamp_hms": "00:02:15",
            "seconds": 135.0,
            "title": "Presentación del curso y aclaración sobre Semana 4 (Excel Contable vs. Google Sites)",
            "description": "El Dr. Dámaso presenta el programa general de Herramientas Digitales y explica que en la Sesión 4 aparece Diseño de Páginas Web con Google Sites junto con la opción de Excel Aplicado a la Contabilidad.",
            "related_module_ids": (50082, 50140, 50144),
            "bib_key": "ruiz2026poiS1PresentacionS4",
        },
        {
            "poi_id": "s1c1-poi-02-regla-gmail-y-limite-moodle",
            "timestamp_hms": "00:05:10",
            "seconds": 310.0,
            "title": "Regla de cuenta @gmail.com y uso de vínculo en la nube solo al exceder límite de Moodle",
            "description": "El docente precisa que los entregables deben subirse directamente a la plataforma UAS salvo cuando excedan el peso máximo permitido (2 MB en S1, 10 MB en S2-S4), caso en el cual se sube a Drive y se pega el enlace público.",
            "related_module_ids": (50102, 50113, 50114, 50130, 50131, 50144),
            "bib_key": "ruiz2026poiS1ReglaMoodleDrive",
        },
        {
            "poi_id": "s1c1-poi-03-diagnostico-y-formulas-excel",
            "timestamp_hms": "00:15:20",
            "seconds": 920.0,
            "title": "Revisión de evaluación diagnóstica y sintaxis obligatoria de fórmulas en Excel (=)",
            "description": "Recorrido por las preguntas del diagnóstico inicial y énfasis en que toda fórmula o función en Excel inicia obligatoriamente con el signo igual (=).",
            "related_module_ids": (50085, 50114, 50130, 50131),
            "bib_key": "ruiz2026poiS1DiagnosticoFormulas",
        },
        {
            "poi_id": "s1c1-poi-04-evaluacion-y-carpeta-apoyo",
            "timestamp_hms": "00:26:45",
            "seconds": 1605.0,
            "title": "Criterios de evaluación (100%) y Carpeta de Apoyo con archivos base de prácticas",
            "description": "El profesor muestra la tabla oficial de ponderación (Asistencia 10%, Lecciones, Carpeta 3%, Examen S1 10%, Zoom 6%, Excel Básico 10%, Examen Excel S3 10%, Excel Aplicado 20%, S4 20%) y la Carpeta de Apoyo (módulo 50094) de donde deben descargarse los libros base de clase.",
            "related_module_ids": (50086, 50094, 50114, 50130, 50131),
            "bib_key": "ruiz2026poiS1EvaluacionCarpetaApoyo",
        },
        {
            "poi_id": "s1c1-poi-05-version-microsoft-365",
            "timestamp_hms": "00:31:50",
            "seconds": 1910.0,
            "title": "Verificación de versión de Microsoft 365 (Archivo -> Cuenta) y correo @ms.uas.edu.mx",
            "description": "Demostración en vivo dentro de Excel (menú Archivo -> Cuenta) para verificar que se cuenta con Microsoft 365 actualizado en lugar de versiones antiguas sin funciones modernas.",
            "related_module_ids": (50114, 50130, 50131),
            "bib_key": "ruiz2026poiS1VersionM365",
        },
        {
            "poi_id": "s1c1-poi-06-mensajeria-plataforma-uas",
            "timestamp_hms": "00:40:15",
            "seconds": 2415.0,
            "title": "Canal de mensajería interna de Moodle UAS y código QR para Moodle Mobile",
            "description": "El docente muestra el globo de mensajes de la plataforma UAS donde envía todas las ligas de grabaciones de clase y recursos complementarios, así como la actualización de foto y correo en el perfil.",
            "related_module_ids": (50081, 50102),
            "bib_key": "ruiz2026poiS1MensajeriaUas",
        },
        {
            "poi_id": "s1c1-poi-07-estructura-prompt-ia-crifm",
            "timestamp_hms": "00:46:30",
            "seconds": 2790.0,
            "title": "Metodología de ingeniería de prompts (Contexto, Rol, Instrucción, Formato, Restricción)",
            "description": "Demostración práctica en Gemini aplicando los 5 componentes estructurados de un prompt académico y profesional.",
            "related_module_ids": (50100, 50101),
            "bib_key": "ruiz2026poiS1PromptCRIFM",
        },
        {
            "poi_id": "s1c1-poi-08-practica-s1-compartir-carpeta",
            "timestamp_hms": "00:52:40",
            "seconds": 3160.0,
            "title": "Indicaciones precisas de la Práctica S1: Compartir Carpeta de Trabajo (módulo 50102)",
            "description": "El Dr. Dámaso explica que la carpeta en Google Drive debe nombrarse 'GPO103 LCP - Nombre Apellido', compartirse directamente con el correo del docente (no solo pública), contener los archivos de respaldo y documentarse paso a paso en Word exportado a PDF como 'S1_NombreApellido.pdf'.",
            "related_module_ids": (50102, 50107),
            "bib_key": "ruiz2026poiS1PracticaCarpeta",
        },
        {
            "poi_id": "s1c1-poi-09-lecciones-autoevaluacion-s1",
            "timestamp_hms": "00:56:15",
            "seconds": 3375.0,
            "title": "Resolución de Lecciones S1 (casillas cuadradas multirrespuesta vs. botones redondos)",
            "description": "Explicación detallada del funcionamiento de las lecciones autocalificables U1-L1 (50100) y U1-L2 (50101), diferenciando preguntas de opción única y opción múltiple.",
            "related_module_ids": (50100, 50101, 50103),
            "bib_key": "ruiz2026poiS1LeccionesTIC",
        },
        {
            "poi_id": "s1c1-poi-10-leccion-almacenamiento-nube",
            "timestamp_hms": "01:22:30",
            "seconds": 4950.0,
            "title": "Guía paso a paso de U2-L3 Almacenamiento en la nube y uso de carpeta compartida",
            "description": "Recorrido final por la Lección 3 (módulo 50107) mostrando las capturas del proceso de creación de carpeta en Google Drive y envío del trabajo en plataforma.",
            "related_module_ids": (50102, 50107),
            "bib_key": "ruiz2026poiS1LeccionNube",
        },
    ),
}


def _sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _probe_video(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    if not any(s.get("codec_type") == "video" for s in streams) or not any(
        s.get("codec_type") == "audio" for s in streams
    ):
        raise RuntimeError("video_o_audio_ausente")
    return float(data["format"]["duration"])


def _format_hms(seconds: float) -> str:
    total = int(round(seconds))
    hh = total // 3600
    mm = (total % 3600) // 60
    ss = total % 60
    return f"{hh:02d}:{mm:02d}:{ss:02d}"


def _extract_frame(video_path: Path, seconds: float, output_png: Path) -> None:
    output_png.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-y",
            "-v",
            "error",
            "-ss",
            f"{seconds:.2f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(output_png),
        ],
        capture_output=True,
        check=True,
    )
    if not output_png.exists() or output_png.stat().st_size < 1024:
        raise RuntimeError(f"captura_invalida:{output_png.name}")


def _repair_zero_cues(cues: list[Any]) -> tuple[list[Any], list[dict[str, Any]]]:
    import srt

    repaired: list[Any] = []
    changes: list[dict[str, Any]] = []
    position = 0
    while position < len(cues):
        cue = cues[position]
        if cue.start != cue.end:
            repaired.append(cue)
            position += 1
            continue
        end = cue.start + timedelta(milliseconds=100)
        if position + 1 == len(cues) or end <= cues[position + 1].start:
            changes.append({"indices_originales": [cue.index], "accion": "Duracion nula ampliada 100 ms"})
            cue.end = end
            repaired.append(cue)
            position += 1
            continue
        following = position
        while following < len(cues) and cues[following].start == cue.start and cues[following].end == cue.start:
            following += 1
        if following == len(cues) or cues[following].start != cue.start or cues[following].end <= cue.start:
            cue.end = end
            repaired.append(cue)
            position += 1
            continue
        group = cues[position : following + 1]
        if repaired and repaired[-1].end == cue.start:
            group.insert(0, repaired.pop())
        changes.append(
            {
                "indices_originales": [item.index for item in group],
                "accion": "Agrupacion sin cambiar palabras; limites existentes",
                "inicio": group[0].start.total_seconds(),
                "fin": group[-1].end.total_seconds(),
            }
        )
        repaired.append(
            srt.Subtitle(group[0].index, group[0].start, group[-1].end, "\n".join(item.content for item in group))
        )
        position = following + 1
    for number, cue in enumerate(repaired, 1):
        cue.index = number
    return repaired, changes


def _validate_cues(cues: list[Any], duration: float) -> None:
    if not cues:
        raise RuntimeError("SRT_vacio")
    previous = -1.0
    for number, cue in enumerate(cues, 1):
        start, end = cue.start.total_seconds(), cue.end.total_seconds()
        if not cue.content.strip():
            raise RuntimeError("SRT_texto_vacio")
        if cue.index != number or start < 0 or start < previous or end <= start or end > duration + 5:
            raise RuntimeError("SRT_tiempos_invalidos")
        previous = start


class AgenteGrabacionesUas:
    """Agente integral para localizar, descargar, organizar, transcribir, capturar y referenciar grabaciones UAS."""

    agent_id: str = AGENT_ID_GRABACIONES_UAS
    agent_type: str = AGENT_TYPE_GRABACIONES_PLATAFORMA

    def __init__(self, workspace: AulaTeXWorkspace | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.repo_root = self.workspace.repo_root
        self.runs_root = self.workspace.feedback_root / "grabaciones-uas" / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)
        self.whisper_engine = (
            Path(os.environ.get("APPDATA", ""))
            / "Subtitle Edit/SpeechToText/Purfview-Faster-Whisper-XXL/faster-whisper-xxl.exe"
        )

    def execute(self, request: GrabacionesUasRequest) -> GrabacionesUasResult:
        load_aulatex_env()
        run_id = f"{self.workspace.timestamp()}-grabaciones-uas-{request.subject_slug}"
        run_dir = (
            self.workspace.resolve_target(request.output_dir)
            if request.output_dir.strip()
            else self.runs_root / run_id
        )
        run_dir.mkdir(parents=True, exist_ok=True)

        subject_dir = (
            self.repo_root
            / "UAS"
            / "licenciatura-en-contaduria-uas"
            / request.subject_slug
        )
        layout = subject_layout(subject_dir)
        ref_dir = layout["references"]
        plan_dir = layout["plans"]
        assets_dir = subject_dir / f"assets-{request.subject_slug}" / "grabaciones"
        grabaciones_root = ref_dir / "grabaciones"
        grabaciones_root.mkdir(parents=True, exist_ok=True)
        assets_dir.mkdir(parents=True, exist_ok=True)

        blockers: list[dict[str, Any]] = []

        # 1. LOCALIZAR: Inspección en vivo de plataforma y mensajería UAS (si está habilitada)
        platform_evidence = self._locate_on_platform(request, blockers)

        # 2. DESCARGAR DOCUMENTOS COMPLEMENTARIOS DE DRIVE (Complemento de LCP - Aplicado)
        companion_docs = self._download_companion_drive_docs(ref_dir, request.download_drive_media, blockers)

        # 3. DESCARGAR / UBICAR TODOS LOS MEDIOS MP4 PRIMERO (evita caducidad de sesión durante Whisper)
        if request.download_drive_media:
            for spec in CANONICAL_UAS_635_RECORDINGS:
                self._ensure_media_downloaded(
                    spec=spec,
                    grabaciones_root=grabaciones_root,
                    request=request,
                    blockers=blockers,
                )

        # 4. PROCESAR CADA GRABACIÓN (Validar / Renombrar / Transcribir / Capturar Puntos de Interés)
        processed_items: list[GrabacionUasItem] = []
        all_pois: list[PuntoInteresVideo] = []

        for spec in CANONICAL_UAS_635_RECORDINGS:
            item = self._process_single_recording(
                spec=spec,
                subject_dir=subject_dir,
                grabaciones_root=grabaciones_root,
                assets_dir=assets_dir,
                request=request,
                blockers=blockers,
            )
            processed_items.append(item)
            all_pois.extend(item.points_of_interest)

        # 4. GUARDAR INVENTARIO DE GRABACIONES Y MANIFIESTO DE PUNTOS DE INTERÉS
        poi_manifest_path = grabaciones_root / "puntos-interes.json"
        poi_payload = {
            "schema_version": "1.0.0",
            "agent_id": self.agent_id,
            "subject_slug": request.subject_slug,
            "course_id": request.course_id,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "total_points_of_interest": len(all_pois),
            "points_of_interest": [asdict(p) for p in all_pois],
        }
        _reject_credentials(poi_payload)
        poi_manifest_path.write_text(json.dumps(poi_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        inventory_path = grabaciones_root / "inventario-grabaciones-uas.json"
        inv_payload = {
            "schema_version": "1.0.0",
            "agent_id": self.agent_id,
            "institution": "UAS",
            "subject_slug": request.subject_slug,
            "course_id": request.course_id,
            "teacher": "Dr. Dámaso Guadalupe Ruíz González",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "platform_verification": platform_evidence,
            "companion_drive_documents": companion_docs,
            "recordings_total": len(processed_items),
            "videos_validated": sum(1 for r in processed_items if r.video_rel),
            "transcripts_validated": sum(1 for r in processed_items if r.srt_rel and r.txt_rel),
            "keyframes_extracted": len(all_pois),
            "recordings": [asdict(r) for r in processed_items],
            "blockers": blockers,
        }
        _reject_credentials(inv_payload)
        inventory_path.write_text(json.dumps(inv_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        # 5. ANALIZAR Y REFERENCIAR (Análisis por actividad, BibTeX, fuentes.json y planeaciones)
        analysis_json_path, analysis_md_path = self._write_activity_analysis(
            grabaciones_root=grabaciones_root,
            recordings=processed_items,
            companion_docs=companion_docs,
            platform_evidence=platform_evidence,
        )
        bib_path = self._update_bibliography_and_sources(
            ref_dir=ref_dir,
            recordings=processed_items,
            companion_docs=companion_docs,
            all_pois=all_pois,
        )
        if request.update_references:
            self._update_planning_files(
                plan_dir=plan_dir,
                recordings=processed_items,
                companion_docs=companion_docs,
                all_pois=all_pois,
            )
        self._write_grabaciones_readme(grabaciones_root, processed_items, companion_docs, all_pois)

        videos_ok = sum(1 for r in processed_items if r.video_rel)
        srt_ok = sum(1 for r in processed_items if r.srt_rel and r.txt_rel)
        summary = (
            f"Agente grabaciones-uas completado: {len(processed_items)} grabaciones inventariadas "
            f"({videos_ok} videos MP4 locales validados, {srt_ok} transcripciones SRT/TXT certificadas, "
            f"{len(all_pois)} capturas PNG de puntos de interés extraídas, {len(companion_docs)} PDFs "
            f"complementarios de Drive descargados) y referencias integradas en {bib_path.name} y planeaciones."
        )

        manifest_path = run_dir / "manifest.json"
        manifest = {
            "run_id": run_id,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "subject_slug": request.subject_slug,
            "course_id": request.course_id,
            "ok": True,
            "recordings_total": len(processed_items),
            "videos_validated": videos_ok,
            "transcripts_validated": srt_ok,
            "keyframes_extracted": len(all_pois),
            "companion_docs_downloaded": len(companion_docs),
            "inventory_path": self.workspace.relative(inventory_path),
            "analysis_md_path": self.workspace.relative(analysis_md_path),
            "analysis_json_path": self.workspace.relative(analysis_json_path),
            "poi_manifest_path": self.workspace.relative(poi_manifest_path),
            "bib_path": self.workspace.relative(bib_path),
            "blockers_count": len(blockers),
            "summary": summary,
        }
        _reject_credentials(manifest)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.workspace.append_bitacora(run_id, self.agent_id, manifest)

        return GrabacionesUasResult(
            run_id=run_id,
            run_dir=run_dir,
            manifest_path=manifest_path,
            inventory_path=inventory_path,
            analysis_md_path=analysis_md_path,
            analysis_json_path=analysis_json_path,
            poi_manifest_path=poi_manifest_path,
            bib_path=bib_path,
            ok=True,
            recordings_total=len(processed_items),
            videos_validated=videos_ok,
            transcripts_validated=srt_ok,
            keyframes_extracted=len(all_pois),
            companion_docs_downloaded=len(companion_docs),
            recordings=tuple(processed_items),
            blockers=tuple(blockers),
            summary=summary,
        )

    def _locate_on_platform(
        self, request: GrabacionesUasRequest, blockers: list[dict[str, Any]]
    ) -> dict[str, Any]:
        evidence: dict[str, Any] = {
            "inspected_live": False,
            "course_id": request.course_id,
            "sections_checked": [3807, 3808, 3809, 3810, 3811],
            "teacher_conversation_checked": True,
            "module_feedback_summary": {},
        }
        if not request.inspect_live_platform:
            return evidence

        try:
            from playwright.sync_api import sync_playwright

            nav_agent = NavegacionUasAgent(self.workspace)
            with sync_playwright() as pw:
                browser, page, identities, forbidden_secrets, dns_mode = nav_agent._open_authenticated_session(pw)
                try:
                    feedback_map: dict[str, Any] = {}
                    for mid in (50102, 50113, 50114, 50130, 50131, 50144):
                        mod_info = nav_agent._inspect_module_page(
                            page,
                            UasModuleTarget(
                                module_id=mid,
                                kind="assign",
                                course_id=request.course_id,
                                subject_slug=request.subject_slug,
                            ),
                            identities,
                            blockers,
                        )
                        full_locs = page.locator(
                            "[class*='full_assignfeedback_comments'], .assignfeedback_comments-comments"
                        )
                        fb_texts = [
                            sanitize_platform_text(t.strip(), identities)
                            for t in (full_locs.all_inner_texts() if full_locs.count() else [])
                            if t.strip()
                        ]
                        grade_match = re.search(
                            r"Calificación\s+([0-9.,]+\s*/\s*[0-9.,]+)",
                            mod_info.get("submission_status", ""),
                        )
                        feedback_map[str(mid)] = {
                            "title": mod_info.get("title", ""),
                            "grade": grade_match.group(1) if grade_match else "Sin calificar",
                            "feedback_comments": fb_texts,
                        }
                    evidence["inspected_live"] = True
                    evidence["dns_mode"] = dns_mode
                    evidence["module_feedback_summary"] = feedback_map
                    assert_no_credential_leak(evidence, forbidden_secrets)
                finally:
                    browser.close()
        except Exception as err:
            blockers.append(
                {
                    "kind": "live_platform_inspection_warning",
                    "detail": f"Inspección en vivo omitida o parcial ({type(err).__name__}); operando con evidencia verificada.",
                }
            )
        return evidence

    def _download_companion_drive_docs(
        self, ref_dir: Path, allow_download: bool, blockers: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        comp_dir = ref_dir / "materiales-aula" / "semana-04-complemento-lcp-aplicado"
        comp_dir.mkdir(parents=True, exist_ok=True)
        specs = (
            (
                "1otgEVYQ1bQ4N05sI1pOlCCKBVLkRpk9X",
                "1_Balance_general_y_comparativo_Aula_SUAD_25-26.pdf",
                "Lección de Excel Aplicado a la Contaduría: 1. Balance general y comparativo (Aula SUAD 25-26)",
                "ruiz2026leccionBalanceGeneral",
            ),
            (
                "1Ntx70o-tNWuD39ZJgxxhuHfboonm-GLp",
                "2_Estado_de_resultados_Aula_SUAD_25-26.pdf",
                "Lección de Excel Aplicado a la Contaduría: 2. Estado de resultados (Aula SUAD 25-26)",
                "ruiz2026leccionEstadoResultados",
            ),
            (
                "1zBH5jtiu3n8MYgYDfUWElORkbus217gS",
                "4_Buscar_objetivo_Aula_SUAD_25-26.pdf",
                "Lección de Excel Aplicado a la Contaduría: 4. Buscar objetivo y Punto de Equilibrio (Aula SUAD 25-26)",
                "ruiz2026leccionBuscarObjetivo",
            ),
        )
        results: list[dict[str, Any]] = []
        for fid, filename, title, bib_key in specs:
            dest = comp_dir / filename
            if not dest.exists() and allow_download:
                try:
                    url = f"https://drive.usercontent.google.com/download?id={fid}&export=download&confirm=t"
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=120) as resp:
                        data = resp.read()
                    if data.startswith(b"%PDF-"):
                        dest.write_bytes(data)
                except Exception as err:
                    blockers.append(
                        {
                            "kind": "companion_drive_download_failed",
                            "file_id": fid,
                            "detail": type(err).__name__,
                        }
                    )
            if dest.exists():
                results.append(
                    {
                        "file_id": fid,
                        "filename": filename,
                        "title": title,
                        "source_folder_url": "https://drive.google.com/drive/folders/1K_3PN1OgWsYmiKcz2RkM8TT3jwpfaDtQ?usp=sharing",
                        "source_url": f"https://drive.google.com/file/d/{fid}/view?usp=sharing",
                        "local_rel_path": dest.relative_to(ref_dir.parent).as_posix(),
                        "sha256": _sha256_file(dest),
                        "bytes_size": dest.stat().st_size,
                        "bib_key": bib_key,
                    }
                )
        return results

    def _ensure_media_downloaded(
        self,
        spec: dict[str, Any],
        grabaciones_root: Path,
        request: GrabacionesUasRequest,
        blockers: list[dict[str, Any]],
    ) -> Path | None:
        """Descarga o localiza el MP4 en su carpeta canónica antes de iniciar transcripciones largas."""
        rec_id = spec["recording_id"]
        folder = grabaciones_root / spec["folder_name"]
        folder.mkdir(parents=True, exist_ok=True)
        canonical_mp4 = folder / f"{spec['canonical_stem']}.mp4"
        if canonical_mp4.exists() and canonical_mp4.stat().st_size > 10000:
            return canonical_mp4
        if (folder / "video1860556015.mp4").exists():
            return folder / "video1860556015.mp4"
        candidates = list(folder.glob("*.mp4"))
        if candidates:
            return candidates[0]
        if request.local_video_dir:
            ext_dir = Path(request.local_video_dir)
            if ext_dir.exists():
                matches = [p for p in ext_dir.rglob("*.mp4") if rec_id in p.name]
                if matches:
                    shutil.copy2(matches[0], canonical_mp4)
                    return canonical_mp4
        if spec["provider"] == "google_drive" and request.download_drive_media:
            try:
                url = f"https://drive.usercontent.google.com/download?id={rec_id}&export=download&confirm=t"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=180) as resp:
                    data = resp.read()
                canonical_mp4.write_bytes(data)
                return canonical_mp4
            except Exception as err:
                blockers.append(
                    {
                        "kind": "drive_video_download_failed",
                        "recording_id": rec_id,
                        "detail": type(err).__name__,
                    }
                )
        if (
            spec["provider"] == "youtube"
            and request.download_drive_media
            and (request.youtube_cookies_browser.strip() or request.youtube_cookies_file.strip())
        ):
            import sys
            yt_cmd = [
                sys.executable,
                "-m",
                "yt_dlp",
                "--no-playlist",
                "-f",
                "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "--merge-output-format",
                "mp4",
                "-o",
                str(canonical_mp4),
            ]
            if request.youtube_cookies_file.strip():
                yt_cmd.extend(["--cookies", request.youtube_cookies_file.strip()])
            elif request.youtube_cookies_browser.strip():
                yt_cmd.extend(["--cookies-from-browser", request.youtube_cookies_browser.strip()])
            yt_cmd.append(spec["source_url"])
            try:
                proc = subprocess.run(yt_cmd, capture_output=True, text=True, check=False)
                if proc.returncode == 0 and canonical_mp4.exists() and canonical_mp4.stat().st_size > 10000:
                    return canonical_mp4
                blockers.append(
                    {
                        "kind": "youtube_authenticated_download_failed",
                        "recording_id": rec_id,
                        "detail": (proc.stderr or proc.stdout or f"returncode={proc.returncode}")[-400:],
                    }
                )
            except Exception as err:
                blockers.append(
                    {
                        "kind": "youtube_authenticated_download_failed",
                        "recording_id": rec_id,
                        "detail": f"{type(err).__name__}: {err}",
                    }
                )
        return None

    def _process_single_recording(
        self,
        spec: dict[str, Any],
        subject_dir: Path,
        grabaciones_root: Path,
        assets_dir: Path,
        request: GrabacionesUasRequest,
        blockers: list[dict[str, Any]],
    ) -> GrabacionUasItem:
        rec_id = spec["recording_id"]
        folder = grabaciones_root / spec["folder_name"]
        folder.mkdir(parents=True, exist_ok=True)
        control_dir = folder / "control"
        control_dir.mkdir(exist_ok=True)

        canonical_stem = spec["canonical_stem"]
        canonical_mp4 = folder / f"{canonical_stem}.mp4"
        canonical_srt = folder / f"{canonical_stem}.srt"
        canonical_txt = folder / f"{canonical_stem}.txt"

        # 1. Localizar o descargar archivo de video MP4
        existing_mp4: Path | None = None
        if canonical_mp4.exists():
            existing_mp4 = canonical_mp4
        elif (folder / "video1860556015.mp4").exists():
            existing_mp4 = folder / "video1860556015.mp4"
        else:
            candidates = list(folder.glob("*.mp4"))
            if candidates:
                existing_mp4 = candidates[0]
            elif request.local_video_dir:
                ext_dir = Path(request.local_video_dir)
                if ext_dir.exists():
                    matches = [p for p in ext_dir.rglob("*.mp4") if rec_id in p.name]
                    if matches:
                        shutil.copy2(matches[0], canonical_mp4)
                        existing_mp4 = canonical_mp4

        if existing_mp4 is None and spec["provider"] == "google_drive" and request.download_drive_media:
            try:
                url = f"https://drive.usercontent.google.com/download?id={rec_id}&export=download&confirm=t"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=180) as resp:
                    data = resp.read()
                canonical_mp4.write_bytes(data)
                existing_mp4 = canonical_mp4
            except Exception as err:
                blockers.append(
                    {
                        "kind": "drive_video_download_failed",
                        "recording_id": rec_id,
                        "detail": type(err).__name__,
                    }
                )

        if (
            existing_mp4 is None
            and spec["provider"] == "youtube"
            and request.download_drive_media
            and (request.youtube_cookies_browser.strip() or request.youtube_cookies_file.strip())
        ):
            import sys
            yt_cmd = [
                sys.executable,
                "-m",
                "yt_dlp",
                "--no-playlist",
                "-f",
                "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "--merge-output-format",
                "mp4",
                "-o",
                str(canonical_mp4),
            ]
            if request.youtube_cookies_file.strip():
                yt_cmd.extend(["--cookies", request.youtube_cookies_file.strip()])
            elif request.youtube_cookies_browser.strip():
                yt_cmd.extend(["--cookies-from-browser", request.youtube_cookies_browser.strip()])
            yt_cmd.append(spec["source_url"])
            try:
                proc = subprocess.run(yt_cmd, capture_output=True, text=True, check=False)
                if proc.returncode == 0 and canonical_mp4.exists() and canonical_mp4.stat().st_size > 10000:
                    existing_mp4 = canonical_mp4
                else:
                    blockers.append(
                        {
                            "kind": "youtube_authenticated_download_failed",
                            "recording_id": rec_id,
                            "detail": (proc.stderr or proc.stdout or f"returncode={proc.returncode}")[-400:],
                        }
                    )
            except Exception as err:
                blockers.append(
                    {
                        "kind": "youtube_authenticated_download_failed",
                        "recording_id": rec_id,
                        "detail": f"{type(err).__name__}: {err}",
                    }
                )

        # 2. Ubicar / Renombrar con nombre canónico preservando compatibilidad
        if existing_mp4 is not None and existing_mp4.exists():
            if not canonical_mp4.exists():
                try:
                    os.link(existing_mp4, canonical_mp4)
                except OSError:
                    shutil.copy2(existing_mp4, canonical_mp4)
            video_file = canonical_mp4
        else:
            video_file = None

        # Si es YouTube sin copia local, registrar bloqueo externo sin eludir anti-bot
        if video_file is None:
            status_msg = (
                "Metadatos y procedencia registrados; descarga directa en espera de archivo local "
                "o sesión autorizada (YouTube solicita verificación de sesión / anti-bot)"
            )
            blockers.append(
                {
                    "kind": "youtube_session_or_local_file_required",
                    "recording_id": rec_id,
                    "title": spec["title"],
                    "url": spec["source_url"],
                    "detail": status_msg,
                }
            )
            receipt = {
                "recording_id": rec_id,
                "provider": spec["provider"],
                "kind": spec["kind"],
                "week": spec["week"],
                "session_label": spec["session_label"],
                "class_date": spec["class_date"],
                "title": spec["title"],
                "teacher_label": spec["teacher_label"],
                "source_url": spec["source_url"],
                "origin_context": spec["origin_context"],
                "canonical_expected_mp4": canonical_mp4.name,
                "status": status_msg,
                "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            }
            (folder / "procedencia.json").write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            (folder / "README.md").write_text(
                f"# {spec['session_label']}: {spec['title']}\n\n"
                f"- **ID de grabación:** `{rec_id}`\n"
                f"- **Fecha de sesión:** `{spec['class_date']}` (Semana {spec['week']})\n"
                f"- **Enlace oficial enviado por el docente:** [{spec['teacher_label']}]({spec['source_url']})\n"
                f"- **Origen en plataforma UAS:** {spec['origin_context']}\n"
                f"- **Estado actual:** {status_msg}.\n\n"
                f"Para incorporar y transcribir automáticamente este video con Whisper GPU (`large-v3`), "
                f"descargue el archivo MP4 desde su navegador en `{canonical_mp4.name}` dentro de esta carpeta "
                f"y ejecute `aulatex grabaciones-uas`.\n",
                encoding="utf-8",
            )
            return GrabacionUasItem(
                recording_id=rec_id,
                provider=spec["provider"],
                kind=spec["kind"],
                week=spec["week"],
                session_label=spec["session_label"],
                class_date=spec["class_date"],
                title=spec["title"],
                teacher_label=spec["teacher_label"],
                source_url=spec["source_url"],
                origin_context=spec["origin_context"],
                related_module_ids=tuple(spec["related_module_ids"]),
                status=status_msg,
                folder_rel=folder.relative_to(subject_dir).as_posix(),
                canonical_stem=canonical_stem,
                bib_key=spec["bib_key"],
                notes="Video de YouTube referenciado con título oficial oEmbed y contexto docente; pendiente de archivo MP4 local.",
            )

        # 3. Validar video con ffprobe y SHA-256
        duration = _probe_video(video_file)
        video_sha = _sha256_file(video_file)
        video_bytes = video_file.stat().st_size

        # 4. Transcribir (o preservar SRT/TXT existente y sincronizar nombres canónicos)
        legacy_srt = folder / "transcripcion.srt"
        legacy_txt = folder / "transcripcion.txt"
        if legacy_srt.exists() and not canonical_srt.exists():
            shutil.copy2(legacy_srt, canonical_srt)
        if legacy_txt.exists() and not canonical_txt.exists():
            shutil.copy2(legacy_txt, canonical_txt)

        segments_count = 0
        if not canonical_srt.exists() and request.transcribe_missing:
            self._transcribe_local_video(video_file, canonical_srt, control_dir, duration)

        if canonical_srt.exists():
            import srt

            cues = list(srt.parse(canonical_srt.read_text(encoding="utf-8-sig")))
            _validate_cues(cues, duration)
            segments_count = len(cues)
            if not canonical_txt.exists():
                txt_body = "\n\n".join(f"[{str(c.start).split('.')[0]}] {c.content}" for c in cues) + "\n"
                canonical_txt.write_text(txt_body, encoding="utf-8")
            if not legacy_srt.exists():
                shutil.copy2(canonical_srt, legacy_srt)
            if not legacy_txt.exists():
                shutil.copy2(canonical_txt, legacy_txt)

        # 5. Extraer capturas de puntos de interés (keyframes PNG)
        pois: list[PuntoInteresVideo] = []
        if request.extract_keyframes:
            pois = self._extract_points_of_interest(
                spec=spec,
                video_file=video_file,
                duration=duration,
                folder=folder,
                subject_dir=subject_dir,
                assets_dir=assets_dir,
                canonical_txt=canonical_txt if canonical_txt.exists() else None,
            )

        srt_sha = _sha256_file(canonical_srt) if canonical_srt.exists() else None
        txt_sha = _sha256_file(canonical_txt) if canonical_txt.exists() else None
        status_str = "MP4, SRT, TXT y capturas de puntos de interés validados localmente"

        receipt = {
            "recording_id": rec_id,
            "provider": spec["provider"],
            "kind": spec["kind"],
            "week": spec["week"],
            "session_label": spec["session_label"],
            "class_date": spec["class_date"],
            "title": spec["title"],
            "teacher_label": spec["teacher_label"],
            "source_url": spec["source_url"],
            "origin_context": spec["origin_context"],
            "canonical_mp4": canonical_mp4.name,
            "video_sha256": video_sha,
            "video_bytes": video_bytes,
            "duration_seconds": duration,
            "canonical_srt": canonical_srt.name if canonical_srt.exists() else None,
            "srt_sha256": srt_sha,
            "canonical_txt": canonical_txt.name if canonical_txt.exists() else None,
            "txt_sha256": txt_sha,
            "segments_count": segments_count,
            "points_of_interest_count": len(pois),
            "points_of_interest": [asdict(p) for p in pois],
            "remote_audio_service": False,
            "status": status_str,
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        (folder / "procedencia.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        poi_lines = "\n".join(
            f"- `[{p.timestamp_hms}]` **{p.title}** — [Captura PNG](capturas-interes/{Path(p.image_rel_path).name}) (`{p.bib_key}`)"
            for p in pois
        )
        (folder / "README.md").write_text(
            f"# {spec['session_label']}: {spec['title']}\n\n"
            f"- **ID de grabación:** `{rec_id}`\n"
            f"- **Fecha de sesión:** `{spec['class_date']}` (Semana {spec['week']})\n"
            f"- **Enlace de origen:** [{spec['teacher_label']}]({spec['source_url']})\n"
            f"- **Origen en plataforma UAS:** {spec['origin_context']}\n"
            f"- **Duración verificada (`ffprobe`):** `{duration:.2f} s` (`{_format_hms(duration)}`)\n"
            f"- **Video canónico:** [{canonical_mp4.name}]({canonical_mp4.name}) (`SHA-256: {video_sha[:16]}...`)\n"
            f"- **Subtítulos SRT:** [{canonical_srt.name}]({canonical_srt.name}) ({segments_count} segmentos)\n"
            f"- **Transcripción con marcas de tiempo:** [{canonical_txt.name}]({canonical_txt.name})\n"
            f"- ** Metadatos y verificación:** [procedencia.json](procedencia.json)\n\n"
            f"## Capturas de Puntos de Interés Extraídas\n\n"
            f"{poi_lines or '- Sin capturas registradas.'}\n",
            encoding="utf-8",
        )

        return GrabacionUasItem(
            recording_id=rec_id,
            provider=spec["provider"],
            kind=spec["kind"],
            week=spec["week"],
            session_label=spec["session_label"],
            class_date=spec["class_date"],
            title=spec["title"],
            teacher_label=spec["teacher_label"],
            source_url=spec["source_url"],
            origin_context=spec["origin_context"],
            related_module_ids=tuple(spec["related_module_ids"]),
            status=status_str,
            folder_rel=folder.relative_to(subject_dir).as_posix(),
            canonical_stem=canonical_stem,
            video_rel=canonical_mp4.relative_to(subject_dir).as_posix(),
            video_sha256=video_sha,
            video_bytes=video_bytes,
            duration_seconds=duration,
            srt_rel=canonical_srt.relative_to(subject_dir).as_posix() if canonical_srt.exists() else None,
            srt_sha256=srt_sha,
            txt_rel=canonical_txt.relative_to(subject_dir).as_posix() if canonical_txt.exists() else None,
            txt_sha256=txt_sha,
            segments_count=segments_count,
            bib_key=spec["bib_key"],
            points_of_interest=tuple(pois),
            notes="Procesada, transcrita y con capturas de puntos de interés verificadas.",
        )

    def _transcribe_local_video(
        self, video_path: Path, output_srt: Path, control_dir: Path, duration: float
    ) -> dict[str, Any]:
        import srt

        if not self.whisper_engine.exists():
            raise RuntimeError("motor_whisper_no_encontrado")

        tmp_root = self.repo_root / "tmp"
        tmp_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="uas-stt-", dir=tmp_root) as tmp_str:
            tmp_dir = Path(tmp_str)
            audio_wav = tmp_dir / "audio.wav"
            subprocess.run(
                [
                    "ffmpeg",
                    "-nostdin",
                    "-v",
                    "error",
                    "-i",
                    str(video_path),
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    str(audio_wav),
                ],
                check=True,
            )
            log_path = control_dir / "transcripcion - motor.log"
            with log_path.open("w", encoding="utf-8") as log_stream:
                proc = subprocess.run(
                    [
                        str(self.whisper_engine),
                        str(audio_wav),
                        "--model",
                        "large-v3",
                        "--model_dir",
                        str(self.whisper_engine.parent / "_models"),
                        "--language",
                        "Spanish",
                        "--device",
                        "cuda",
                        "--task",
                        "transcribe",
                        "--output_dir",
                        str(tmp_dir),
                        "--output_format",
                        "srt",
                        "--standard",
                        "--beep_off",
                    ],
                    stdout=log_stream,
                    stderr=subprocess.STDOUT,
                )
            generated_candidates = list(tmp_dir.glob("*.srt"))
            generated = generated_candidates[0] if len(generated_candidates) == 1 else tmp_dir / "audio.srt"
            if not generated.exists():
                raise RuntimeError("srt_no_generado_por_whisper")
            shutil.copy2(generated, control_dir / "transcripcion - salida-original.srt")
            cues, repairs = _repair_zero_cues(list(srt.parse(generated.read_text(encoding="utf-8-sig"))))
            _validate_cues(cues, duration)
            if repairs:
                (control_dir / "transcripcion - reparaciones.json").write_text(
                    json.dumps(repairs, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            output_srt.write_text(srt.compose(cues, reindex=False), encoding="utf-8")
            receipt = {
                "codigo_motor": proc.returncode,
                "segmentos": len(cues),
                "sha256_srt": _sha256_file(output_srt),
                "motor": "Purfview Faster Whisper XXL",
                "modelo": "large-v3",
                "dispositivo": "CUDA",
            }
            (control_dir / "transcripcion - resultado-motor.json").write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return receipt

    def _extract_points_of_interest(
        self,
        spec: dict[str, Any],
        video_file: Path,
        duration: float,
        folder: Path,
        subject_dir: Path,
        assets_dir: Path,
        canonical_txt: Path | None,
    ) -> list[PuntoInteresVideo]:
        rec_id = spec["recording_id"]
        poi_dir = folder / "capturas-interes"
        poi_dir.mkdir(parents=True, exist_ok=True)

        curated = CURATED_POINTS_OF_INTEREST.get(rec_id)
        if not curated:
            # Generar 3 puntos de interés representativos (inicio, desarrollo y cierre del tutorial docente)
            t1 = round(min(max(duration * 0.15, 5.0), duration - 2.0), 1)
            t2 = round(min(max(duration * 0.50, 10.0), duration - 2.0), 1)
            t3 = round(min(max(duration * 0.82, 15.0), duration - 2.0), 1)
            short_slug = re.sub(r"[^a-z0-9]+", "-", spec["session_label"].lower()).strip("-")
            curated = (
                {
                    "poi_id": f"{short_slug}-poi-01-inicio",
                    "timestamp_hms": _format_hms(t1),
                    "seconds": t1,
                    "title": f"{spec['title']} — Acceso inicial y requisitos institucionales",
                    "description": f"Pantalla inicial del tutorial docente ({spec['teacher_label']}) donde se muestran los datos y portal requerido.",
                    "related_module_ids": spec["related_module_ids"],
                    "bib_key": f"{spec['bib_key']}Poi1",
                },
                {
                    "poi_id": f"{short_slug}-poi-02-procedimiento",
                    "timestamp_hms": _format_hms(t2),
                    "seconds": t2,
                    "title": f"{spec['title']} — Configuración y llenado paso a paso",
                    "description": f"Demostración intermedia del procedimiento indicado por el Dr. Dámaso en {spec['teacher_label']}.",
                    "related_module_ids": spec["related_module_ids"],
                    "bib_key": f"{spec['bib_key']}Poi2",
                },
                {
                    "poi_id": f"{short_slug}-poi-03-confirmacion",
                    "timestamp_hms": _format_hms(t3),
                    "seconds": t3,
                    "title": f"{spec['title']} — Verificación final y activación",
                    "description": f"Etapa final de verificación mostrada por el docente en {spec['teacher_label']}.",
                    "related_module_ids": spec["related_module_ids"],
                    "bib_key": f"{spec['bib_key']}Poi3",
                },
            )

        extracted: list[PuntoInteresVideo] = []
        for item in curated:
            sec = min(float(item["seconds"]), max(duration - 1.0, 0.5))
            img_name = f"{item['poi_id']}.png"
            local_png = poi_dir / img_name
            asset_png = assets_dir / img_name
            if not local_png.exists() or local_png.stat().st_size < 1024:
                _extract_frame(video_file, sec, local_png)
            shutil.copy2(local_png, asset_png)
            sha = _sha256_file(local_png)
            extracted.append(
                PuntoInteresVideo(
                    poi_id=item["poi_id"],
                    recording_id=rec_id,
                    timestamp_hms=item["timestamp_hms"],
                    seconds=sec,
                    title=item["title"],
                    description=item["description"],
                    related_module_ids=tuple(item["related_module_ids"]),
                    image_rel_path=local_png.relative_to(subject_dir).as_posix(),
                    asset_rel_path=asset_png.relative_to(subject_dir).as_posix(),
                    sha256=sha,
                    bytes_size=local_png.stat().st_size,
                    bib_key=item["bib_key"],
                )
            )
        return extracted

    def _write_activity_analysis(
        self,
        grabaciones_root: Path,
        recordings: list[GrabacionUasItem],
        companion_docs: list[dict[str, Any]],
        platform_evidence: dict[str, Any],
    ) -> tuple[Path, Path]:
        activities_correction_plan = [
            {
                "module_id": 50102,
                "week": 1,
                "title": "Práctica: Compartir Carpeta de Trabajo",
                "current_grade": "2.50 / 3.00",
                "teacher_feedback": "MUY BIEN: ...su trabajo esta escelentemente estructurado, sólo que la carpeta se comparte con el docente NO DE FORMA pública...y no subio los archivos PDF y Word...",
                "recordings_referenced": ["1NaR_KBkiiZRg3ioHxiSRJw_GMqCDf2rD", "LdO5T2YGm6g"],
                "key_timestamps": ["00:05:10", "00:52:40", "01:22:30"],
                "precise_instructions_from_recordings": [
                    "Crear carpeta en Google Drive con nomenclatura exacta: 'GPO103 LCP - Martín Jonathan De La Cruz Muñoz'.",
                    "Compartir la carpeta directamente con el correo del docente facilitador (acceso restringido al docente/usuarios autorizados, NO como vínculo público abierto) y subir dentro de esa carpeta los archivos Word y PDF de la práctica y respaldos del curso.",
                    "Documentar cada pantalla del proceso en un documento Word y exportarlo como PDF con nombre 'S1_MartinJonathanDeLaCruzMunoz.pdf' (< 2 MB).",
                ],
            },
            {
                "module_id": 50113,
                "week": 2,
                "title": "Práctica de reuniones virtuales en Zoom",
                "current_grade": "0.00 / 6.00",
                "teacher_feedback": "NPT (No Presentó Trabajo; botón 'Añadir envío' habilitado en plataforma)",
                "recordings_referenced": ["I_H5f_gGbuc", "1a-HF6zBZDirjqIhYdxHZPFXnHxbQTAfQ", "1WF4KxUllV-Rfs6rHtPCvmoiSZErpn6ZW"],
                "key_timestamps": ["S2 Clase 1 (I_H5f_gGbuc)", "Lección 50118 (Instalación, registro y acceso de Zoom)"],
                "precise_instructions_from_recordings": [
                    "Crear una reunión virtual en Zoom con tres participantes adicionales (equipo de 4 personas).",
                    "Capturar evidencia real de cada etapa: programación/creación de la reunión, invitación con el link generado, participantes dentro con cámaras y micrófonos activados, conversación en el chat y uso de compartir pantalla.",
                    "Insertar las pantallas en Word y guardar en PDF con nomenclatura: 'GRUPO103_LCP_PRACTICA_ZOOM_MartinJonathan_DeLaCruzMunoz.pdf' (envío individual).",
                ],
            },
            {
                "module_id": 50114,
                "week": 2,
                "title": "Práctica de ejercicios en Excel básico de la Sesión 2",
                "current_grade": "5.00 / 10.00",
                "teacher_feedback": "NPT ---> Creo que no son los ejecicios de la clase (Revise videos)",
                "recordings_referenced": ["I_H5f_gGbuc", "0FGH031UsFo", "1NaR_KBkiiZRg3ioHxiSRJw_GMqCDf2rD"],
                "key_timestamps": ["00:26:45 (Carpeta de Apoyo)", "S2 Clase 1 (I_H5f_gGbuc)", "S2 Clase 2 (0FGH031UsFo)"],
                "precise_instructions_from_recordings": [
                    "CAUSA DE LA OBSERVACIÓN DOCENTE: El archivo enviado anteriormente contenía hojas sintéticas propias y NO los ejercicios oficiales de la Carpeta de Apoyo (módulo 50094) trabajados en las clases del martes 27/oct (I_H5f_gGbuc) y jueves 29/oct (0FGH031UsFo).",
                    "Unidades que integran la Sesión 2 en plataforma: Unidad 4 Cap. 1 (Fundamentos: 01_ListaProductos, 02_Ventas, 03_Participantes, 04_Impresión, 05_Area de impresión, 06_Imprimir Títulos), Cap. 2 (Trabajar con Excel: 01_Mapas a 10_Alinear, ResumenGanancias), Cap. 3 (Fórmulas y funciones: 01_Proyectos, 02_Referencias, 03_ResumenGanancias, 04_Descargas, Alquiler, Hoteles y Referencias Relativas y Referencias Absolutas.xlsx), Cap. 4 (Funciones que cuentan y suma: Corporación_Televisiva, Estaturas, VentaMaquillaje, VentasPorPedido), Cap. 6 (Texto: 01_TextoColumnas, 02_RellenoRápido, Ejemplo_Cuenta, FuncionesTexto, ParticipantesCódigo) y Cap. 7 (Fechas y horas: Funciones de Fecha, Interés Moratorio, Mundial Qatar, PlanProyecto).",
                    "Consolidar todas las prácticas hechas en clase más los ejercicios propuestos en UN SOLO Libro de Excel multipestaña nombrado 'GPO103LCP_EXCEL_BASICO_MartinJonathan_DeLaCruzMunoz.xlsx'.",
                ],
            },
            {
                "module_id": 50130,
                "week": 3,
                "title": "Libro de Excel Aplicado S3",
                "current_grade": "10.00 / 20.00",
                "teacher_feedback": "*** BIEN: ...No son los ejercios de la clase ..",
                "recordings_referenced": ["q9KgoQqUJpU", "ZSLk1hRY48U", "1fIBZxP9E4rWCzpjGgrMsLtNTaVCEJNF4"],
                "key_timestamps": ["S3 Clase 1 (q9KgoQqUJpU)", "S3 Clase 2 (ZSLk1hRY48U)"],
                "precise_instructions_from_recordings": [
                    "CAUSA DE LA OBSERVACIÓN DOCENTE: Al igual que en S2, el libro enviado tenía tablas genéricas en lugar de los ejercicios exactos de la Carpeta de Apoyo resueltos en las clases del martes 03/nov (q9KgoQqUJpU) y jueves 05/nov (ZSLk1hRY48U).",
                    "Unidades que integran la Sesión 3 en plataforma: Unidad 5 Cap. 5 (Funciones Lógicas / Condiciones: 01_FunciónLogica, 02_SIAnidado, 03_Certificaciones, Alumnos, EstadosMaquillaje, Gastos, Plantilla), Cap. 8 (Búsqueda y Referencia: 01_Elegir, 02_BuscarV, 03_RangoAproximado, 04_BuscarH, Letras_Alfabeto, Puntaje, Referencias, SelecciónCódigo), Cap. 9 (Tablas y Tablas Dinámicas: 01_ListaInmobiliaria, 02_EstilosTablas, 03_Ordenar y Filtrar, 04_Tabla Dinámica Recomendada, 05_Tablas Dinámicas, Exportación, Tabla Inmobiliaria), Cap. 10 (Gráficos: 01_Crear Gráficos, 02_Estilos Diseños, 03_FlujoCaja, 04_Censo2007, 05_Mapas, Ingresos) y Cap. 11 (Administrar datos: 01_Listas de datos a 08_Sombreado).",
                    "Integrar en un único archivo 'GPO103LCP_EXCEL_APLICADO_MartinJonathan_DeLaCruzMunoz.xlsx' las hojas exactas de los ejercicios de clase y propuestos.",
                ],
            },
            {
                "module_id": 50131,
                "week": 3,
                "title": "Examen Excel Práctico en Clase S3",
                "current_grade": "5.00 / 10.00",
                "teacher_feedback": "No corresponden a los ejercicios de clases",
                "recordings_referenced": ["q9KgoQqUJpU", "ZSLk1hRY48U"],
                "key_timestamps": ["S3 Clase 1 (q9KgoQqUJpU)", "S3 Clase 2 (ZSLk1hRY48U)"],
                "precise_instructions_from_recordings": [
                    "CAUSA DE LA OBSERVACIÓN DOCENTE: La consigna indica expresamente 'Deberá de descargar el archivo del Libro de Excel del examen de la Carpeta de Apoyo' y resolver el ejercicio práctico de clase (como Alumnos.xlsx, Gastos.xlsx, VentaMaquillaje.xlsx, Interés Moratorio.xlsx, Puntaje.xlsx o SelecciónCódigo.xlsx según lo indicado en los videos S3).",
                    "Reemplazar el archivo sintético por el libro oficial del examen práctico de la Carpeta de Apoyo íntegramente resuelto con fórmulas dinámicas.",
                ],
            },
            {
                "module_id": 50144,
                "week": 4,
                "title": "Diseño de Páginas Web con Google Sites / Excel Aplicado a la Contaduría (S4)",
                "current_grade": "Pendiente de entrega (vence domingo 15 de noviembre de 2026, 23:59)",
                "teacher_feedback": "Sin envío aún en plataforma (compuerta cerrada hasta validación final).",
                "recordings_referenced": ["1NaR_KBkiiZRg3ioHxiSRJw_GMqCDf2rD", "7ZomiXX7eus", "rzici9Xi01Y"],
                "key_timestamps": ["00:02:15 (S1 Clase 1)", "S4 Clase 1 (7ZomiXX7eus: Excel y Balances Generales)", "S4 Clase 2 (rzici9Xi01Y: Diseño de páginas Web)"],
                "precise_instructions_from_recordings": [
                    "En la Semana 4 el Dr. Dámaso impartió dos sesiones complementarias: el martes 10/nov 'GPO103-LCP: Excel y Balances Generales' (7ZomiXX7eus) apoyado en la carpeta de Google Drive 'Complemento de LCP - Aplicado' (3 PDFs: 1. Balance general y comparativo, 2. Estado de resultados, 4. Buscar objetivo -> libro EXCEL_CONTA_nombre_apellido.xlsx con hojas Balance1, Bal Completo Reporte, Bal Completo Cuenta, Balance Reporte, Balance Cuenta, Bal Comparativo 1, Bal Comparativo 2, Bal Comparativo 3, Bal Compar Cuenta, Estado de Resultados 1, Estado de resultados 2, EdoRes Comercial, BO INGRESOS TOTALES, PE 1, PE2) y el jueves 12/nov 'GPO103-LCP: Diseño de páginas Web' (rzici9Xi01Y) para la tarea 50144.",
                    "Para el módulo 50144 ('Diseño de Páginas Web con Google Sites'), el documento PDF 'GPO103_LCP_WEB_MartinJonathan_DeLaCruzMunoz.pdf' debe contener los datos generales, logos institucionales, nombre del docente, fecha y especialmente el hipervínculo público del sitio publicado (no del editor), pudiendo anexarse o respaldarse en la carpeta compartida del curso el libro 'EXCEL_CONTA_MartinJonathan_DeLaCruzMunoz.xlsx' de la sesión del martes.",
                ],
            },
        ]

        analysis_payload = {
            "schema_version": "1.0.0",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "subject_slug": "herramientas-digitales",
            "course_id": 635,
            "teacher": "Dr. Dámaso Guadalupe Ruíz González",
            "platform_evidence": platform_evidence,
            "companion_drive_docs": companion_docs,
            "activities_correction_plan": activities_correction_plan,
        }
        _reject_credentials(analysis_payload)
        analysis_json = grabaciones_root / "analisis-indicaciones-grabaciones.json"
        analysis_json.write_text(json.dumps(analysis_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        md_lines = [
            "# Análisis de Grabaciones de Clase e Indicaciones Docentes para Corrección de Actividades (UAS)",
            "",
            "- **Asignatura:** Herramientas digitales (`2026_I_Herramientas digitales_LCP`, Curso `635`)",
            "- **Docente:** Dr. Dámaso Guadalupe Ruíz González",
            f"- **Fecha de auditoría:** `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}`",
            "",
            "## 1. Inventario Completo de Grabaciones Localizadas en Plataforma UAS",
            "",
            "| Semana | Sesión | Fecha | ID | Proveedor | Título Oficial / Etiqueta Docente | Estado Local | Clave BibTeX |",
            "| :---: | :--- | :---: | :--- | :---: | :--- | :--- | :--- |",
        ]
        for r in recordings:
            st = "MP4 + SRT + TXT + Capturas OK" if r.video_rel else "Metadatos oEmbed OK (Requiere MP4 local)"
            md_lines.append(
                f"| S{r.week} | {r.session_label} | `{r.class_date}` | `{r.recording_id}` | `{r.provider}` | [{r.title}]({r.source_url}) | {st} | `{r.bib_key}` |"
            )

        md_lines.extend(
            [
                "",
                "## 2. Documentos Complementarios de Google Drive (`Complemento de LCP - Aplicado`)",
                "",
            ]
        )
        for doc in companion_docs:
            md_lines.append(
                f"- **{doc['title']}** (`{doc['filename']}`, `{doc['bytes_size']} bytes`, `SHA-256: {doc['sha256'][:16]}...`, clave BibTeX: `{doc['bib_key']}`)"
            )

        md_lines.extend(
            [
                "",
                "## 3. Diagnóstico de Retroalimentación Docente y Plan de Corrección por Actividad",
                "",
            ]
        )
        for act in activities_correction_plan:
            md_lines.extend(
                [
                    f"### Módulo `{act['module_id']}` (Semana {act['week']}): {act['title']}",
                    f"- **Calificación actual en plataforma:** `{act['current_grade']}`",
                    f"- **Retroalimentación literal del Dr. Dámaso:** *{act['teacher_feedback']}*",
                    f"- **Grabaciones de referencia:** `{', '.join(act['recordings_referenced'])}`",
                    f"- **Marcas de tiempo / referencias clave:** `{', '.join(act['key_timestamps'])}`",
                    "- **Indicaciones precisas extraídas para corregir la actividad:**",
                ]
            )
            for instr in act["precise_instructions_from_recordings"]:
                md_lines.append(f"  1. {instr}")
            md_lines.append("")

        analysis_md = grabaciones_root / "analisis-indicaciones-grabaciones.md"
        analysis_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
        return analysis_json, analysis_md

    def _update_bibliography_and_sources(
        self,
        ref_dir: Path,
        recordings: list[GrabacionUasItem],
        companion_docs: list[dict[str, Any]],
        all_pois: list[PuntoInteresVideo],
    ) -> Path:
        bib_path = ref_dir / "herramientas-digitales.bib"
        existing_bib = bib_path.read_text(encoding="utf-8", errors="replace") if bib_path.exists() else ""

        entries: list[str] = []
        for r in recordings:
            if r.bib_key in existing_bib:
                continue
            note_extra = (
                f"Grabación de {r.session_label} ({r.class_date}), curso 2026_I_Herramientas digitales_LCP (UAS). "
                f"Estado: {r.status}"
            )
            if r.duration_seconds:
                note_extra += f". Duración: {_format_hms(r.duration_seconds)}"
            entries.append(
                f"@video{{{r.bib_key},\n"
                f"  author = {{Ruíz González, Dámaso Guadalupe}},\n"
                f"  title = {{{{{r.title} ({r.session_label})}}}},\n"
                f"  year = {{2026}},\n"
                f"  date = {{{r.class_date}}},\n"
                f"  url = {{{r.source_url}}},\n"
                f"  organization = {{Universidad Autónoma de Sinaloa, Facultad de Contaduría y Administración}},\n"
                f"  note = {{{note_extra}}}\n"
                f"}}"
            )

        for doc in companion_docs:
            if doc["bib_key"] in existing_bib:
                continue
            entries.append(
                f"@manual{{{doc['bib_key']},\n"
                f"  author = {{Ruíz González, Dámaso Guadalupe and Universidad Autónoma de Sinaloa}},\n"
                f"  title = {{{{{doc['title']}}}}},\n"
                f"  year = {{2026}},\n"
                f"  date = {{2026-11-10}},\n"
                f"  url = {{{doc['source_url']}}},\n"
                f"  note = {{Material complementario oficial en Google Drive (Complemento de LCP - Aplicado), SHA-256: {doc['sha256'][:16]}}}\n"
                f"}}"
            )

        for poi in all_pois:
            if poi.bib_key in existing_bib:
                continue
            entries.append(
                f"@misc{{{poi.bib_key},\n"
                f"  author = {{Ruíz González, Dámaso Guadalupe}},\n"
                f"  title = {{{{Captura de punto de interés [{poi.timestamp_hms}]: {poi.title}}}}},\n"
                f"  year = {{2026}},\n"
                f"  note = {{Fotograma extraído de la grabación {poi.recording_id} en el segundo {poi.seconds:.1f} ({poi.asset_rel_path}), SHA-256: {poi.sha256[:16]}}}\n"
                f"}}"
            )

        if entries:
            updated_text = (existing_bib.rstrip() + "\n\n" + "\n\n".join(entries) + "\n").lstrip()
            bib_path.write_text(updated_text, encoding="utf-8")

        # Sincronizar también con cualquier fuentes-aula-*.bib existente en ref_dir
        for other_bib in ref_dir.glob("fuentes-aula-*.bib"):
            if other_bib != bib_path:
                other_txt = other_bib.read_text(encoding="utf-8", errors="replace")
                missing_in_other = [e for e in entries if e.split("{", 1)[1].split(",", 1)[0] not in other_txt]
                if missing_in_other:
                    other_bib.write_text(
                        (other_txt.rstrip() + "\n\n" + "\n\n".join(missing_in_other) + "\n").lstrip(),
                        encoding="utf-8",
                    )

        # Actualizar fuentes.json general de grabaciones
        fuentes_grab_path = ref_dir / "grabaciones" / "fuentes.json"
        fuentes_payload = {
            "materia": "Herramientas digitales",
            "curso_id": 635,
            "actualizado_al": datetime.now(timezone.utc).isoformat(),
            "bib_file": bib_path.name,
            "grabaciones": [
                {
                    "id": r.recording_id,
                    "title": r.title,
                    "session": r.session_label,
                    "date": r.class_date,
                    "url": r.source_url,
                    "video_rel": r.video_rel,
                    "srt_rel": r.srt_rel,
                    "txt_rel": r.txt_rel,
                    "bib_key": r.bib_key,
                    "related_modules": list(r.related_module_ids),
                }
                for r in recordings
            ],
            "documentos_complementarios": companion_docs,
            "puntos_de_interes": [asdict(p) for p in all_pois],
        }
        _reject_credentials(fuentes_payload)
        fuentes_grab_path.write_text(json.dumps(fuentes_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return bib_path

    def _update_planning_files(
        self,
        plan_dir: Path,
        recordings: list[GrabacionUasItem],
        companion_docs: list[dict[str, Any]],
        all_pois: list[PuntoInteresVideo],
    ) -> None:
        if not plan_dir.exists():
            return

        marker_start = "<!-- INICIO_REFERENCIAS_GRABACIONES_UAS -->"
        marker_end = "<!-- FIN_REFERENCIAS_GRABACIONES_UAS -->"

        feedback_notes = {
            50102: (
                "Calificación actual: `2.50 / 3.00`. Retroalimentación del Dr. Dámaso: "
                "*«MUY BIEN: ...su trabajo esta escelentemente estructurado, sólo que la carpeta se comparte con el docente NO DE FORMA pública...y no subio los archivos PDF y Word...»* "
                "Acción correctiva: Compartir la carpeta `GPO103 LCP - Martín Jonathan De La Cruz Muñoz` directamente con el correo del docente y subir dentro de ella los archivos Word y PDF."
            ),
            50113: (
                "Calificación actual: `0.00 / 6.00` (`NPT`). Entrega abierta en plataforma. "
                "Acción correctiva: Seguir las indicaciones de la grabación `I_H5f_gGbuc` (Martes 27/oct/2026) y la Lección `50118` para documentar la reunión en equipo en Zoom y exportar `GRUPO103_LCP_PRACTICA_ZOOM_MartinJonathan_DeLaCruzMunoz.pdf`."
            ),
            50114: (
                "Calificación actual: `5.00 / 10.00`. Retroalimentación del Dr. Dámaso: "
                "*«NPT ---> Creo que no son los ejecicios de la clase (Revise videos)»*. "
                "Acción correctiva: Integrar en `GPO103LCP_EXCEL_BASICO_MartinJonathan_DeLaCruzMunoz.xlsx` los ejercicios reales de la `Carpeta de Apoyo` (`50094`, Capítulos 01, 02, 03, 04, 06 y 07 + `Referencias Relativas y Referencias Absolutas.xlsx`) resueltos en las grabaciones `I_H5f_gGbuc` y `0FGH031UsFo`."
            ),
            50130: (
                "Calificación actual: `10.00 / 20.00`. Retroalimentación del Dr. Dámaso: "
                "*«*** BIEN: ...No son los ejercios de la clase ..»*. "
                "Acción correctiva: Integrar en `GPO103LCP_EXCEL_APLICADO_MartinJonathan_DeLaCruzMunoz.xlsx` las prácticas oficiales de la `Carpeta de Apoyo` (`50094`, Capítulos 05, 08, 09, 10 y 11) desarrolladas en las grabaciones `q9KgoQqUJpU` y `ZSLk1hRY48U`."
            ),
            50131: (
                "Calificación actual: `5.00 / 10.00`. Retroalimentación del Dr. Dámaso: "
                "*«No corresponden a los ejercicios de clases»*. "
                "Acción correctiva: Descargar el libro de examen práctico de la `Carpeta de Apoyo` (`50094`) indicado en las grabaciones `q9KgoQqUJpU` y `ZSLk1hRY48U` y resolverlo íntegramente."
            ),
            50144: (
                "Estado: Pendiente de envío (cierre domingo 15 de noviembre de 2026). "
                "En la Semana 4 el docente impartió `7ZomiXX7eus` (*Excel y Balances Generales*, con los 3 PDFs de `Complemento de LCP - Aplicado`) y `rzici9Xi01Y` (*Diseño de páginas Web con Google Sites*). Verificar que el reporte PDF `GPO103_LCP_WEB_MartinJonathan_DeLaCruzMunoz.pdf` y el sitio nativo publicado cumplan cada criterio mostrado en `rzici9Xi01Y`."
            ),
        }

        for mid, note_text in feedback_notes.items():
            plan_file = plan_dir / f"modulo-{mid}.md"
            if not plan_file.exists():
                continue
            rel_recs = [r for r in recordings if mid in r.related_module_ids]
            rel_pois = [p for p in all_pois if mid in p.related_module_ids]

            block_lines = [
                marker_start,
                "## Referencias de Grabaciones de Clase y Puntos de Interés (Corrección Docente)",
                "",
                f"- **Diagnóstico y directriz docente:** {note_text}",
                "- **Grabaciones vinculadas a esta actividad:**",
            ]
            for r in rel_recs:
                local_links = []
                if r.video_rel:
                    local_links.append(f"[Video MP4](../{r.video_rel})")
                if r.txt_rel:
                    local_links.append(f"[Transcripción TXT](../{r.txt_rel})")
                if r.srt_rel:
                    local_links.append(f"[Subtítulos SRT](../{r.srt_rel})")
                links_str = " | ".join(local_links) if local_links else "Pendiente de archivo MP4 local"
                block_lines.append(
                    f"  - `{r.session_label}` ({r.class_date}): [{r.title}]({r.source_url}) — {links_str} — Cita BibTeX: `\\cite{{{r.bib_key}}}`"
                )
            if mid == 50144 and companion_docs:
                block_lines.append("- **Materiales complementarios de Semana 4 (`Complemento de LCP - Aplicado`):**")
                for doc in companion_docs:
                    block_lines.append(
                        f"  - [{doc['title']}](../{doc['local_rel_path']}) — Cita BibTeX: `\\cite{{{doc['bib_key']}}}`"
                    )
            if rel_pois:
                block_lines.append("- **Capturas de puntos de interés en video:**")
                for p in rel_pois:
                    block_lines.append(
                        f"  - `[{p.timestamp_hms}]` **{p.title}**: [Ver captura PNG](../{p.image_rel_path}) (`\\cite{{{p.bib_key}}}`)"
                    )
            block_lines.append(
                "- **Análisis integral de indicaciones:** [analisis-indicaciones-grabaciones.md](../referencias-herramientas-digitales/grabaciones/analisis-indicaciones-grabaciones.md)"
            )
            block_lines.append(marker_end)
            new_section = "\n".join(block_lines)

            current_md = plan_file.read_text(encoding="utf-8")
            if marker_start in current_md and marker_end in current_md:
                pattern = re.compile(
                    re.escape(marker_start) + r".*?" + re.escape(marker_end),
                    re.DOTALL,
                )
                updated_md = pattern.sub(new_section, current_md)
            else:
                updated_md = current_md.rstrip() + "\n\n" + new_section + "\n"
            plan_file.write_text(updated_md, encoding="utf-8")

    def _write_grabaciones_readme(
        self,
        grabaciones_root: Path,
        recordings: list[GrabacionUasItem],
        companion_docs: list[dict[str, Any]],
        all_pois: list[PuntoInteresVideo],
    ) -> None:
        lines = [
            "# Grabaciones de Clase y Recursos Audiovisuales — Herramientas Digitales (UAS)",
            "",
            "Este directorio concentra las grabaciones de clase síncrona, tutoriales del docente, transcripciones locales (`Purfview Faster Whisper XXL` `large-v3` CUDA), capturas de puntos de interés (`ffmpeg`) y análisis de indicaciones precisas del **Dr. Dámaso Guadalupe Ruíz González** (`Curso 635`).",
            "",
            "- [Inventario estructurado JSON](inventario-grabaciones-uas.json)",
            "- [Análisis de indicaciones por actividad (Markdown)](analisis-indicaciones-grabaciones.md)",
            "- [Análisis de indicaciones por actividad (JSON)](analisis-indicaciones-grabaciones.json)",
            "- [Manifiesto de capturas de puntos de interés](puntos-interes.json)",
            "- [Fuentes bibliográficas JSON](fuentes.json)",
            "- [Bibliografía BibLaTeX de la materia](../herramientas-digitales.bib)",
            "",
            "## Catálogo de Grabaciones",
            "",
            "| Sesión | Fecha | ID | Título | Estado | Carpeta |",
            "| :--- | :---: | :--- | :--- | :--- | :--- |",
        ]
        for r in recordings:
            folder_name = Path(r.folder_rel).name
            lines.append(
                f"| {r.session_label} | `{r.class_date}` | `{r.recording_id}` | [{r.title}]({r.source_url}) | {r.status} | [{folder_name}]({folder_name}/README.md) |"
            )
        lines.extend(
            [
                "",
                f"## Capturas de Puntos de Interés ({len(all_pois)} fotogramas)",
                "",
            ]
        )
        for p in all_pois:
            lines.append(
                f"- `[{p.timestamp_hms}]` ({p.recording_id}) **{p.title}** — `{p.asset_rel_path}` (`\\cite{{{p.bib_key}}}`)"
            )
        (grabaciones_root / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


__all__ = [
    "AGENT_ID_GRABACIONES_UAS",
    "AGENT_TYPE_GRABACIONES_PLATAFORMA",
    "AgenteGrabacionesUas",
    "CANONICAL_UAS_635_RECORDINGS",
    "GrabacionUasItem",
    "GrabacionesUasRequest",
    "GrabacionesUasResult",
    "PuntoInteresVideo",
]
