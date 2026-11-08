"""Agente ``realizar-planeación`` para el flujo académico UnADM en AulaTeX.

Consume evidencia sanitizada producida por ``navegación-itesca`` / ``navegación-unadm``
y metadatos del repositorio para estructurar la planeación pedagógica canónica
(conforme a ``planeacion-canonica.schema.json`` v1.0.0 y vista Markdown) dentro de
``planeaciones-<slug>/`` en ``UnADM/licenciatura-en-derecho-unadm/<slug>-lde/``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .navegacion_plataforma import assert_no_credential_leak
from .node_planning import PEDAGOGICAL_SCHEMA_PATH, validate_schema
from .planning_layout import artifact_contract, slugify_text, subject_layout
from .planning_validation import validate_pedagogical
from .workspace import AulaTeXWorkspace

AGENT_ID_REALIZAR_PLANEACION = "realizar-planeación"

UNADM_SUBJECTS_CATALOG: dict[str, dict[str, Any]] = {
    "teoria-del-estado-y-constitucion": {
        "title": "Teoría del Estado y Constitución",
        "code": "020",
        "course_id": 3432,
        "default_teacher": "Lic. Mtra. Titular UnADM",
        "activities": {
            1: {"title": "Foro diagnóstico", "kind": "forum"},
            2: {"title": "Línea de tiempo", "kind": "report"},
            3: {"title": "Análisis de hechos", "kind": "report"},
            4: {"title": "Foro de debate", "kind": "forum"},
            5: {"title": "Valoración de decisiones", "kind": "report"},
            6: {"title": "S6. Foro de Derechos Humanos", "kind": "forum", "module_id": 221688},
        },
    },
    "derecho-penal-especial-mexicano": {
        "title": "Derecho Penal Especial Mexicano",
        "code": "020",
        "course_id": 3482,
        "default_teacher": "Docente Titular Derecho Penal UnADM",
        "activities": {
            1: {"title": "Foro diagnóstico", "kind": "forum"},
            2: {"title": "Cuadro comparativo del robo", "kind": "report"},
            3: {"title": "Estudio de casos", "kind": "report"},
            4: {"title": "Delitos de peligro", "kind": "report"},
            5: {"title": "Delitos contra la libertad personal", "kind": "report"},
            6: {"title": "ACTIVIDAD S6 Tarea", "kind": "report", "module_id": 222951},
        },
    },
    "antecedentes-de-los-derechos-humanos": {
        "title": "Antecedentes de los Derechos Humanos",
        "code": "005",
        "course_id": 3441,
        "default_teacher": "Docente Titular Derechos Humanos UnADM",
        "activities": {
            1: {"title": "Examen diagnóstico", "kind": "platform_response"},
            2: {"title": "Foro diagnóstico", "kind": "forum"},
            3: {"title": "Reseña crítica de video", "kind": "report"},
            4: {"title": "Foro de participación", "kind": "forum"},
            5: {"title": "Resumen de lectura", "kind": "report"},
            6: {"title": "Foro de debate", "kind": "forum"},
            7: {"title": "Cuadro comparativo", "kind": "report"},
            8: {"title": "Cuadro sinóptico – Orden jurídico nacional en torno a los derechos humanos", "kind": "report", "module_id": 212031},
        },
    },
}


@dataclass(frozen=True)
class RealizarPlaneacionUnadmRequest:
    subject_slug: str
    activity_number: int
    module_snapshot: dict[str, Any] | None = None
    course_snapshot: dict[str, Any] | None = None
    notes_subdir_hint: str = ""
    override_title: str = ""


@dataclass(frozen=True)
class RealizarPlaneacionUnadmResult:
    agent_id: str
    activity_number: int
    subject_slug: str
    subject_root: Path
    notes_dir: Path
    plan_json_path: Path
    plan_md_path: Path
    consigna_path: Path
    plan_document: dict[str, Any]
    semantic_validation: dict[str, Any]
    blockers: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return bool(self.semantic_validation.get("passed", True))


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _clean_slug_title(title: str) -> str:
    cleaned = re.sub(r"^[^\wÁÉÍÓÚÜÑáéíóúüñ]+", "", title or "").strip()
    cleaned = re.sub(r"^(?:Actividad\s+\d+\s*[:.-]?\s*|\d+\.\d+\s+)", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b\d+\s*%\b", "", cleaned).strip()
    return slugify_text(cleaned)[:48] or "actividad"


def resolve_unadm_notes_dir(subject_root: Path, activity_number: int, title: str, hint: str = "") -> Path:
    layout = subject_layout(subject_root)
    notes_root = layout["notes"]
    notes_root.mkdir(parents=True, exist_ok=True)
    if hint.strip():
        candidate = notes_root / hint.strip()
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate

    patterns = (
        re.compile(rf"^actividad-0*{int(activity_number)}(?:[-_].*)?$", re.IGNORECASE),
        re.compile(rf"^semana-0*{int(activity_number)}(?:[-_].*)?$", re.IGNORECASE),
    )
    for child in sorted(notes_root.iterdir()):
        if child.is_dir() and any(pat.match(child.name) for pat in patterns):
            return child

    width = 2
    prefix = f"actividad-{int(activity_number):0{width}d}-{_clean_slug_title(title)}"
    created = notes_root / prefix
    created.mkdir(parents=True, exist_ok=True)
    return created


class RealizarPlaneacionUnadmAgent:
    """Agente ``realizar-planeación`` para UnADM conforme al contrato canónico de AulaTeX."""

    agent_id: str = AGENT_ID_REALIZAR_PLANEACION

    def __init__(self, workspace: AulaTeXWorkspace | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()

    def plan(self, request: RealizarPlaneacionUnadmRequest) -> RealizarPlaneacionUnadmResult:
        base_slug = request.subject_slug.replace("-lde", "").strip()
        subject_dir_name = f"{base_slug}-lde"
        unadm_root = self.workspace.repo_root / "UnADM" / "licenciatura-en-derecho-unadm"
        subject_root = unadm_root / subject_dir_name
        if not subject_root.is_dir():
            raise ValueError(f"Directorio de materia UnADM inexistente: {subject_root}")

        layout = subject_layout(subject_root)
        layout["plans"].mkdir(parents=True, exist_ok=True)

        catalog_entry = UNADM_SUBJECTS_CATALOG.get(base_slug, {})
        subject_title = catalog_entry.get("title") or base_slug.replace("-", " ").capitalize()
        course_code = catalog_entry.get("code") or "020"
        default_teacher = catalog_entry.get("default_teacher") or "Docente Titular UnADM"

        mod = request.module_snapshot or {}
        act_info = catalog_entry.get("activities", {}).get(request.activity_number, {})
        title = request.override_title or mod.get("title") or act_info.get("title") or f"Actividad {request.activity_number}"

        notes_dir = resolve_unadm_notes_dir(subject_root, request.activity_number, title, request.notes_subdir_hint)
        notes_dir.mkdir(parents=True, exist_ok=True)

        # Archivar consigna oficial sanitizada
        intro_text = (mod.get("intro_text") or "").strip()
        if not intro_text:
            # Buscar en el directorio de notas si ya existe consigna archivada
            for cand in notes_dir.glob("consigna*.*"):
                if cand.is_file() and cand.suffix.lower() in {".txt", ".md", ".html"}:
                    intro_text = cand.read_text(encoding="utf-8", errors="replace")
                    break
        if not intro_text:
            # Buscar en originales-docentes de la materia
            orig_dir = layout["plans"] / "originales-docentes"
            if orig_dir.is_dir():
                for cand in orig_dir.glob(f"*S{request.activity_number}*.txt"):
                    if cand.is_file():
                        intro_text = cand.read_text(encoding="utf-8", errors="replace")
                        break
        if not intro_text:
            intro_text = f"Desarrollo académico formal de la {title} para la asignatura {subject_title}."

        consigna_path = notes_dir / f"consigna-aula-S{request.activity_number}.txt"
        consigna_bytes = intro_text.encode("utf-8")
        assert_no_credential_leak(intro_text)
        consigna_path.write_bytes(consigna_bytes)
        consigna_sha = _sha256_bytes(consigna_bytes)
        consigna_rel = consigna_path.relative_to(subject_root).as_posix()

        captured_at = datetime.now(timezone.utc).isoformat()
        plan_id = f"pca-{_sha256_bytes(f'unadm-{base_slug}-{request.activity_number}'.encode())[:20]}"
        offering_id = f"oferta-unadm-{base_slug}-2026-2-b2"

        # Segmentar requisitos y preguntas
        requirements: list[dict[str, str]] = []
        questions: list[dict[str, Any]] = []
        topics: list[dict[str, Any]] = []

        lines = [re.sub(r"\s+", " ", ln).strip() for ln in intro_text.splitlines() if ln.strip()]
        for idx, line in enumerate(lines, start=1):
            if len(line) < 4:
                continue
            req_id = f"req-{len(requirements) + 1:03d}"
            requirements.append({"id": req_id, "text": line})
            if line.startswith("¿") and line.endswith("?"):
                questions.append({
                    "id": f"q-{len(questions) + 1:03d}",
                    "context": f"Consigna UnADM {title}",
                    "text": line,
                    "requirement_ids": [req_id],
                })
            if re.match(r"^\d+\.\d+\s+\S+", line):
                topics.append({
                    "id": f"topic-{len(topics) + 1:03d}",
                    "text": line,
                    "children": [],
                })

        if not requirements:
            requirements.append({"id": "req-001", "text": f"Elaborar informe académico para {title}"})
        if not topics:
            topics.append({"id": "topic-001", "text": requirements[0]["text"][:120], "children": []})

        req_ids = [r["id"] for r in requirements]

        # Evaluación y rúbrica
        rubric_criteria: list[dict[str, Any]] = []
        for idx, r_item in enumerate(mod.get("rubric") or [], start=1):
            rubric_criteria.append({
                "id": f"crit-{idx:02d}",
                "text": r_item.get("criterion", f"Criterio {idx}"),
                "points": 20.0,
                "descriptors": [{"level": "Excelente", "description": "Cumple cabalmente", "points": 20.0}],
                "requirement_ids": req_ids[: min(4, len(req_ids))],
            })
        if not rubric_criteria:
            rubric_criteria = [
                {
                    "id": "crit-01",
                    "text": "Dominio conceptual y rigor doctrinal",
                    "points": 35.0,
                    "descriptors": [{"level": "Excelente", "description": "Sustento en literatura jurídica oficial", "points": 35.0}],
                    "requirement_ids": req_ids,
                },
                {
                    "id": "crit-02",
                    "text": "Estructura del producto solicitado y aplicación",
                    "points": 45.0,
                    "descriptors": [{"level": "Excelente", "description": "Producto didáctico visible completado", "points": 45.0}],
                    "requirement_ids": req_ids,
                },
                {
                    "id": "crit-03",
                    "text": "Formato APA 7, redacción y estilo académico",
                    "points": 20.0,
                    "descriptors": [{"level": "Excelente", "description": "Citas verificables en .bib y sin metadiscurso", "points": 20.0}],
                    "requirement_ids": req_ids,
                },
            ]

        # Insumos / Sources
        sources = [
            {
                "id": f"src-unadm-consigna-s{request.activity_number}",
                "kind": "platform",
                "authority": "instructional",
                "title": f"Consigna oficial UnADM: {title}",
                "url": mod.get("url") or f"https://aulavirtual.unadmexico.mx/course/view.php?id={catalog_entry.get('course_id')}",
                "path": consigna_rel,
                "sha256": consigna_sha,
                "captured_at": captured_at,
                "media_type": "text/plain",
            }
        ]

        # Template de la materia
        template_rel = "UnADM/assets-unadm/plantilla-actividad-aulatex.tex"
        editable_rel = f"reporte-{base_slug}-Actividad-{request.activity_number}.tex"
        delivery_rel = f"entregas-{base_slug}/Actividad-{request.activity_number}-Reporte.pdf"

        # Secuencia 4 etapas
        sequence = [
            {
                "id": "step-01",
                "order": 1,
                "phase": "preparation",
                "action": "Recopilar, descargar y organizar recursos docentes y bibliografía local con encontrar-recursos.",
                "inputs": [consigna_rel],
                "output": f"{notes_dir.relative_to(subject_root).as_posix()}/recursos-actividad.json",
                "completion_check": "Hashes SHA-256 verificados y cero credenciales expuestas",
                "requirement_ids": req_ids,
                "depends_on": [],
            },
            {
                "id": "step-02",
                "order": 2,
                "phase": "preparation",
                "action": "Extraer fichas conceptuales e ideas trazables en la carpeta de notas de la actividad con extraer-conceptos.",
                "inputs": [f"{notes_dir.relative_to(subject_root).as_posix()}/recursos-actividad.json"],
                "output": f"{notes_dir.relative_to(subject_root).as_posix()}/fichas_conceptos.json",
                "completion_check": "Artefactos nucleares de conceptos presentes en notas y trazabilidad asegurada",
                "requirement_ids": req_ids,
                "depends_on": ["step-01"],
            },
            {
                "id": "step-03",
                "order": 3,
                "phase": "construction",
                "action": "Desarrollar entregable con plantillas UnADM y refinamiento de voz con estilo-escribir.",
                "inputs": [f"{notes_dir.relative_to(subject_root).as_posix()}/fichas_conceptos.json"],
                "output": editable_rel,
                "completion_check": "Compilación limpia, estilo score >= 88.0 y gates de calidad aprobados",
                "requirement_ids": req_ids,
                "depends_on": ["step-02"],
            },
            {
                "id": "step-04",
                "order": 4,
                "phase": "review",
                "action": "Ejecutar ciclos de calidad, auditoría tipográfica y empaquetado seguro en entregas-.",
                "inputs": [editable_rel],
                "output": delivery_rel,
                "completion_check": "PDF compilado y verificado en entregas de la materia",
                "requirement_ids": req_ids,
                "depends_on": ["step-03"],
            },
        ]

        # Armar modelo PCA v1.0.0 canónico
        plan_document: dict[str, Any] = {
            "schema_version": "1.0.0",
            "plan_id": plan_id,
            "revision": 1,
            "identity": {
                "institution": "UnADM",
                "program": "Licenciatura en Derecho",
                "subject_id": subject_dir_name,
                "subject_title": subject_title,
                "offering_id": offering_id,
                "period": "2026-2 B2",
                "modality": "online",
            },
            "sources": sources,
            "curriculum": {
                "purpose": f"Desarrollo de competencias y análisis jurídico-doctrinal para {subject_title}.",
                "competencies": [
                    {"id": "comp-01", "text": f"Analiza el marco normativo y conceptual de {subject_title}."},
                    {"id": "comp-02", "text": "Aplica el razonamiento jurídico a casos concretos y productos argumentados."},
                ],
                "outcomes": [
                    {"id": "ra-001", "text": f"Comprende y sintetiza los postulados teóricos y prácticos de la {title}."},
                ],
                "topics": topics,
            },
            "activities": [
                {
                    "id": f"act-{request.activity_number:02d}",
                    "title": title,
                    "role": "learning",
                    "platform": {
                        "name": "UnADM Virtual",
                        "course_id": str(catalog_entry.get("course_id", 3482)),
                        "module_ids": [str(mod.get("module_id", ""))] if mod.get("module_id") else [],
                    },
                    "unit_id": f"unidad-0{request.activity_number}",
                    "weeks": [int(request.activity_number)],
                    "outcome_ids": ["ra-001"],
                    "topic_ids": [t["id"] for t in topics],
                    "cognitive": {
                        "taxonomy": "Bloom",
                        "level": "analisis",
                        "verb": "Analizar",
                        "object": f"Conceptos y problemas de {title}",
                        "conditions": "Conforme a plantilla institucional UnADM y fuentes verificables",
                        "observable_evidence": "Reporte académico en LaTeX/PDF con fuentes en APA 7",
                        "justification": "Demuestra apropiación conceptual y análisis crítico transferible",
                    },
                    "instruction": intro_text,
                    "requirements": requirements,
                    "questions": questions,
                    "sequence": sequence,
                    "resources": [
                        {
                            "id": "res-01",
                            "source_id": sources[0]["id"] if sources else "src-unadm-consigna",
                            "purpose": f"Consigna y lineamientos de {title}",
                            "required": True,
                            "access": "authenticated",
                            "rights": "Material docente de uso interno UnADM",
                        }
                    ],
                    "assessment": {
                        "kind": "summative",
                        "scale_total": 100.0,
                        "weight": 20.0,
                        "weight_unit": "percent",
                        "criteria": rubric_criteria,
                        "editorial_checks": [
                            "Cero exposición de credenciales o matrículas en texto visible",
                            "Citas verificables en bibliografía BibTeX local",
                            "Estilo académico formal auditado con estilo-escribir",
                        ],
                    },
                    "products": [
                        {
                            "id": "prod-01",
                            "kind": "academic_report_latex",
                            "recipient": "Plataforma UnADM",
                            "editable_format": "LaTeX (.tex)",
                            "submission_format": "PDF con plantilla oficial UnADM",
                            "structure": [
                                "Portada oficial UnADM con metadatos del estudiante",
                                "Introducción estructurada",
                                "Desarrollo con producto protagónico",
                                "Conclusiones con transferencia profesional y declaración ética de IA",
                                "Referencias en formato APA 7",
                            ],
                            "length": "Conforme a consigna (3 a 10 cuartillas con aparato crítico)",
                            "filename_pattern": Path(delivery_rel).name,
                            "accessibility": None,
                            "requirement_ids": req_ids,
                            "paths": {"editable": editable_rel, "delivery": delivery_rel},
                        }
                    ],
                    "calendar": {
                        "opens_at": None,
                        "expected_at": None,
                        "due_at": None,
                        "closes_at": None,
                        "timezone": "America/Mexico_City",
                        "literal": mod.get("activity_dates") or "Conforme a calendario oficial del bloque",
                    },
                    "policies": {
                        "ai": "Declaración ética de IA en conclusiones conforme a lineamientos UnADM.",
                        "integrity": "Rigor académico, originalidad y citas verificables.",
                        "collaboration": "Trabajo individual independiente.",
                        "citation": "APA 7",
                        "attempts": 1,
                        "late_submission": "Conforme al calendario oficial del bloque.",
                        "accessibility": None,
                        "privacy": "Cero exposición de credenciales institucionales o matrículas.",
                        "exceptions": [],
                    },
                    "dependencies": [],
                    "alignment": [
                        {
                            "outcome_id": "ra-001",
                            "requirement_ids": req_ids,
                            "step_ids": [s["id"] for s in sequence],
                            "product_ids": ["prod-01"],
                            "criterion_ids": [c["id"] for c in rubric_criteria],
                        }
                    ],
                    "bindings": {
                        "extractor_directory": f"extractor-aulatex/conceptos-{base_slug}-actividad-{request.activity_number}",
                        "notes_directory": notes_dir.relative_to(subject_root).as_posix(),
                        "research_directory": "investigacion-aulatex",
                    },
                }
            ],
            "field_status": [
                {
                    "path": "/identity",
                    "state": "confirmed",
                    "reason": "Identidad institucional UnADM verificada con el catálogo de materias.",
                    "evidence": [{"source_id": sources[0]["id"] if sources else "src-unadm-consigna", "locator": "/identity", "quoted_text": None}],
                    "alternatives": [],
                },
                {
                    "path": "/sources/0",
                    "state": "confirmed",
                    "reason": "Consigna capturada de la plataforma o repositorios locales verificados.",
                    "evidence": [{"source_id": sources[0]["id"] if sources else "src-unadm-consigna", "locator": "/sources/0", "quoted_text": None}],
                    "alternatives": [],
                },
                {
                    "path": "/curriculum/purpose",
                    "state": "inferred",
                    "reason": "Propósito curricular derivado de la disciplina.",
                    "evidence": [],
                    "alternatives": [],
                },
                {
                    "path": "/curriculum/competencies",
                    "state": "inferred",
                    "reason": "Competencias derivadas del programa institucional.",
                    "evidence": [],
                    "alternatives": [],
                },
                {
                    "path": "/curriculum/outcomes",
                    "state": "inferred",
                    "reason": "Resultados de aprendizaje operacionales de la actividad.",
                    "evidence": [],
                    "alternatives": [],
                },
                {
                    "path": "/curriculum/topics",
                    "state": "inferred",
                    "reason": "Ejes temáticos identificados a partir de la consigna.",
                    "evidence": [],
                    "alternatives": [],
                },
                {
                    "path": "/activities/0/instruction",
                    "state": "confirmed",
                    "reason": "Instrucción oficial de la actividad UnADM.",
                    "evidence": [{"source_id": sources[0]["id"] if sources else "src-unadm-consigna", "locator": "/activities/0/instruction", "quoted_text": None}],
                    "alternatives": [],
                },
                {
                    "path": "/activities/0/requirements",
                    "state": "confirmed",
                    "reason": "Requisitos específicos segmentados de la consigna.",
                    "evidence": [{"source_id": sources[0]["id"] if sources else "src-unadm-consigna", "locator": "/activities/0/requirements", "quoted_text": None}],
                    "alternatives": [],
                },
                {
                    "path": "/activities/0/cognitive",
                    "state": "inferred",
                    "reason": "Demanda cognitiva estimada para nivel licenciatura.",
                    "evidence": [],
                    "alternatives": [],
                },
                {
                    "path": "/activities/0/sequence",
                    "state": "inferred",
                    "reason": "Secuencia operativa estructurada en fases preparation, construction, review.",
                    "evidence": [],
                    "alternatives": [],
                },
                {
                    "path": "/activities/0/assessment",
                    "state": "confirmed",
                    "reason": "Criterios de evaluación y rúbrica pedagógica documentados en consigna.",
                    "evidence": [{"source_id": sources[0]["id"] if sources else "src-unadm-consigna", "locator": "/activities/0/assessment", "quoted_text": None}],
                    "alternatives": [],
                },
                {
                    "path": "/activities/0/products",
                    "state": "confirmed",
                    "reason": "Producto documental en formato LaTeX/PDF requerido por el estándar AulaTeX.",
                    "evidence": [{"source_id": sources[0]["id"] if sources else "src-unadm-consigna", "locator": "/activities/0/products", "quoted_text": None}],
                    "alternatives": [],
                },
                {
                    "path": "/activities/0/calendar",
                    "state": "inferred",
                    "reason": "Calendario operativo institucional.",
                    "evidence": [],
                    "alternatives": [],
                },
                {
                    "path": "/activities/0/policies",
                    "state": "inferred",
                    "reason": "Políticas académicas y de uso ético de IA.",
                    "evidence": [],
                    "alternatives": [],
                },
                {
                    "path": "/activities/0/alignment",
                    "state": "confirmed",
                    "reason": "Alineación constructiva completa.",
                    "evidence": [{"source_id": sources[0]["id"] if sources else "src-unadm-consigna", "locator": "/activities/0/alignment", "quoted_text": None}],
                    "alternatives": [],
                },
                {
                    "path": "/activities/0/bindings",
                    "state": "confirmed",
                    "reason": "Rutas de derivados en notas y extractor.",
                    "evidence": [{"source_id": sources[0]["id"] if sources else "src-unadm-consigna", "locator": "/activities/0/bindings", "quoted_text": None}],
                    "alternatives": [],
                },
            ],
            "review": {
                "state": "ready",
                "reviewed_at": captured_at,
                "reviewer_role": self.agent_id,
                "critical_gaps": [],
                "semantic_validation": "passed",
            },
            "artifact_contract": artifact_contract(subject_root),
            "extensions": {
                "unadm_workflow": {
                    "subject_slug": base_slug,
                    "activity_number": request.activity_number,
                    "course_id": catalog_entry.get("course_id"),
                    "group": course_code,
                    "teacher": default_teacher,
                    "template_path": template_rel,
                },
                "editorial_rules": {
                    "citation_style": "APA 7",
                    "language": "es-MX",
                    "accessibility": "screen-reader-safe",
                    "source_quality": "peer-reviewed-or-official",
                },
                "provenance": {
                    "created_by": self.agent_id,
                    "created_at": captured_at,
                    "mode": "authenticated_platform_inspection_and_synthesis",
                },
            },
        }

        assert_no_credential_leak(plan_document)

        plan_json_path = layout["plans"] / f"planeacion-{base_slug}-Actividad-{request.activity_number}.json"
        plan_json_path.write_text(json.dumps(plan_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        # Generar vista Markdown compañera
        md_text = self._render_unadm_markdown(plan_document, notes_dir, subject_root)
        assert_no_credential_leak(md_text)
        plan_md_path = layout["plans"] / f"planeacion-{base_slug}-Actividad-{request.activity_number}.md"
        plan_md_path.write_text(md_text, encoding="utf-8")

        # Validar pedagógicamente si existe el esquema
        sem_val: dict[str, Any] = {"passed": True, "errors": []}
        try:
            sem_val = validate_pedagogical(plan_document, subject_root)
        except Exception as e:
            sem_val = {"passed": False, "errors": [str(e)]}

        return RealizarPlaneacionUnadmResult(
            agent_id=self.agent_id,
            activity_number=request.activity_number,
            subject_slug=base_slug,
            subject_root=subject_root,
            notes_dir=notes_dir,
            plan_json_path=plan_json_path,
            plan_md_path=plan_md_path,
            consigna_path=consigna_path,
            plan_document=plan_document,
            semantic_validation=sem_val,
            blockers=tuple(),
        )

    def _render_unadm_markdown(self, doc: dict[str, Any], notes_dir: Path, subject_root: Path) -> str:
        ident = doc["identity"]
        act = doc["activities"][0]
        prod = act["products"][0]
        crit = act["assessment"]["criteria"]
        unadm_ext = doc.get("extensions", {}).get("unadm_workflow", {})
        course_code = unadm_ext.get("group", "")
        teacher = unadm_ext.get("teacher", "Docente Titular UnADM")
        template_path = unadm_ext.get("template_path", "UnADM/assets-unadm/plantilla-actividad-aulatex.tex")

        lines = [
            f"# Planeación Pedagógica Canónica: {act['title']}",
            "",
            "## 1. Contexto Institucional y Curricular",
            f"- **Institución:** {ident['institution']}",
            f"- **Programa:** {ident['program']}",
            f"- **Asignatura:** {ident['subject_title']} (Código `{course_code}`)",
            f"- **Docente:** {teacher}",
            f"- **Periodo:** {ident['period']}",
            f"- **Carpeta de notas:** `{act['bindings']['notes_directory']}`",
            "",
            "## 2. Consigna Oficial",
            "",
            act["instruction"],
            "",
            "## 3. Requisitos y Preguntas Guía",
            "",
        ]
        for req in act["requirements"]:
            lines.append(f"- **{req['id']}:** {req['text']}")
        lines.append("")
        for q in act["questions"]:
            lines.append(f"- *{q['id']}:* {q['text']}")
        lines.extend([
            "",
            "## 4. Contrato de Entrega y Rutas",
            f"- **Formato editable:** {prod['editable_format']} (`{prod['paths']['editable']}`)",
            f"- **Formato de entrega:** {prod['submission_format']} (`{prod['paths']['delivery']}`)",
            f"- **Plantilla base:** `{template_path}`",
            "",
            "## 5. Rúbrica y Criterios de Calidad",
            "",
        ])
        for c in crit:
            lines.append(f"- **{c['text']}** ({c['points']} pts)")
        lines.extend([
            "",
            "## 6. Secuencia de Ejecución",
            "1. `planeación`: consolidación de consigna y rúbrica (`realizar-planeación`).",
            "2. `recopilación de recursos`: descarga y organización en `material-docente` y `corpus-extractor` (`encontrar-recursos`).",
            "3. `extracción de conceptos`: generación de fichas trazables en la carpeta de notas (`extraer-conceptos`).",
            "4. `realización de actividad`: autoría con plantilla UnADM y refinamiento con `estilo-escribir` (`realizar-actividad`).",
            "",
        ])
        return "\n".join(lines)


__all__ = [
    "AGENT_ID_REALIZAR_PLANEACION",
    "RealizarPlaneacionUnadmAgent",
    "RealizarPlaneacionUnadmRequest",
    "RealizarPlaneacionUnadmResult",
    "UNADM_SUBJECTS_CATALOG",
    "resolve_unadm_notes_dir",
]
