"""Agente ``realizar-planeación`` para el flujo académico ITESCA en AulaTeX.

Consume evidencia sanitizada producida por ``navegación-itesca`` y metadatos
verificados del repositorio objetivo para generar y actualizar planeaciones
canónicas (``planeacion-canonica.schema.json`` + Markdown compañero) dentro de
``planeaciones-<slug>/``, separando explícitamente datos confirmados,
inferidos, pendientes o con bloqueo operativo.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

from .mcp_lex import McpLexClient, get_lex_client
from .navegacion_plataforma import assert_no_credential_leak
from .node_planning import PEDAGOGICAL_SCHEMA_PATH, validate_schema
from .planning_layout import artifact_contract, slugify_text, subject_layout
from .planning_validation import validate_pedagogical
from .workspace import AulaTeXWorkspace

AGENT_ID_REALIZAR_PLANEACION = "realizar-planeación"


@dataclass(frozen=True)
class RealizarPlaneacionRequest:
    target: str
    activity_number: int
    module_snapshot: dict[str, Any]
    related_feedback_snapshots: tuple[dict[str, Any], ...] = ()
    notes_subdir_hint: str = ""


@dataclass(frozen=True)
class RealizarPlaneacionResult:
    agent_id: str
    activity_number: int
    module_id: int
    subject_root: Path
    notes_dir: Path
    plan_json_path: Path
    plan_md_path: Path
    extractor_plan_path: Path
    consigna_path: Path
    semantic_validation: dict[str, Any]
    blockers: tuple[dict[str, Any], ...]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _clean_slug_title(title: str) -> str:
    cleaned = re.sub(r"^[^\wÁÉÍÓÚÜÑáéíóúüñ]+", "", title or "").strip()
    cleaned = re.sub(r"^(?:Tarea\s+\d+\s*[:.-]?\s*|\d+\.\d+\s+)", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b\d+\s*%\b", "", cleaned).strip()
    return slugify_text(cleaned)[:48] or "actividad"


def resolve_activity_notes_dir(subject_root: Path, activity_number: int, title: str, hint: str = "") -> Path:
    layout = subject_layout(subject_root)
    notes_root = layout["notes"]
    notes_root.mkdir(parents=True, exist_ok=True)
    if hint.strip():
        candidate = notes_root / hint.strip()
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    patterns = (
        re.compile(rf"^actividad-0*{int(activity_number)}(?:[-_].*)?$", re.IGNORECASE),
    )
    for child in sorted(notes_root.iterdir()):
        if child.is_dir() and any(pat.match(child.name) for pat in patterns):
            return child
    width = 2 if any(d.is_dir() and re.match(r"^actividad-0\d[-_]", d.name) for d in notes_root.iterdir()) else 1
    prefix = f"actividad-{int(activity_number):0{width}d}-{_clean_slug_title(title)}"
    created = notes_root / prefix
    created.mkdir(parents=True, exist_ok=True)
    return created


def _extract_tex_def(tex_text: str, macro: str) -> str | None:
    match = re.search(rf"\\def\\{re.escape(macro)}\{{([^}}]+)\}}", tex_text)
    if match:
        val = match.group(1).strip()
        if val and not val.startswith("\\"):
            return val
    return None


def _resolve_verified_subject_metadata(subject_root: Path, activity_number: int) -> dict[str, Any]:
    layout = subject_layout(subject_root)
    slug = subject_root.name
    for suffix in ("-mga", "-lde", "-lae", "-iias"):
        if slug.endswith(suffix):
            slug = slug[: -len(suffix)]
            break

    template_tex = subject_root / f"reporte-{slug}-plantilla-actividad.tex"
    tex_text = template_tex.read_text(encoding="utf-8", errors="replace") if template_tex.is_file() else ""

    subject_title = _extract_tex_def(tex_text, "itescacoursename") or slug.replace("-", " ").capitalize()
    course_code = _extract_tex_def(tex_text, "itescacoursecode")
    teacher = _extract_tex_def(tex_text, "itescateachingfigure")
    period = _extract_tex_def(tex_text, "itescaprogramperiod")
    program_name = _extract_tex_def(tex_text, "itescafacultyname")

    existing_json_path = layout["plans"] / f"planeacion-{slug}-Actividad-{int(activity_number)}.json"
    existing_doc: dict[str, Any] = {}
    if existing_json_path.is_file():
        try:
            existing_doc = json.loads(existing_json_path.read_text(encoding="utf-8-sig"))
        except Exception:
            existing_doc = {}

    plan_id = existing_doc.get("plan_id") or f"pca-{_sha256_bytes(f'{subject_root.name}-{activity_number}'.encode())[:20]}"
    revision = int(existing_doc.get("revision") or 0) + 1
    existing_identity = existing_doc.get("identity") or {}
    offering_id = existing_identity.get("offering_id") or f"oferta-{_sha256_bytes(subject_root.name.encode())[:16]}"

    return {
        "slug": slug,
        "subject_id": subject_root.name,
        "subject_title": existing_identity.get("subject_title") or subject_title,
        "program": existing_identity.get("program") or subject_root.parent.name,
        "program_name": program_name,
        "course_code": course_code,
        "teacher": teacher,
        "period": period,
        "plan_id": plan_id,
        "revision": revision,
        "offering_id": offering_id,
        "template_tex_rel": template_tex.relative_to(subject_root).as_posix() if template_tex.is_file() else None,
        "existing_extensions": existing_doc.get("extensions") if isinstance(existing_doc.get("extensions"), dict) else {},
    }


def _segment_requirements_and_questions(intro_text: str) -> tuple[list[dict[str, str]], list[dict[str, Any]], list[dict[str, Any]]]:
    lines = [re.sub(r"\s+", " ", ln.replace("\xa0", " ")).strip() for ln in (intro_text or "").splitlines()]
    lines = [ln for ln in lines if ln and ln.lower() not in {"instrucciones", "descripción", "recomendaciones", "click aquí"}]

    requirements: list[dict[str, str]] = []
    questions: list[dict[str, Any]] = []
    topics: list[dict[str, Any]] = []

    for idx, line in enumerate(lines, start=1):
        if len(line) < 4:
            continue
        req_id = f"req-{len(requirements) + 1:03d}"
        requirements.append({"id": req_id, "text": line})
        if line.startswith("¿") and line.endswith("?"):
            questions.append(
                {
                    "id": f"q-{len(questions) + 1:03d}",
                    "context": "Consigna ITESCA",
                    "text": line,
                    "requirement_ids": [req_id],
                }
            )
        if re.match(r"^\d+\.\d+\s+\S+", line):
            topics.append(
                {
                    "id": f"topic-{idx:03d}",
                    "text": line,
                    "children": [],
                }
            )

    if not requirements:
        requirements.append({"id": "req-001", "text": (intro_text or "Revisar consigna oficial").strip() or "Consigna oficial"})
    if not topics:
        topics.append({"id": "topic-001", "text": requirements[0]["text"][:120], "children": []})
    return requirements[:32], questions[:16], topics[:12]


def _parse_assessment(module_snapshot: dict[str, Any], req_ids: list[str]) -> tuple[dict[str, Any], bool]:
    """Extrae rúbrica/ponderación confirmada de la consigna o tabla Moodle."""
    intro = module_snapshot.get("intro_text") or ""
    sf = module_snapshot.get("submission_and_feedback") or {}
    moodle_rubric = sf.get("rubric") or []

    criteria: list[dict[str, Any]] = []
    if moodle_rubric:
        for idx, row in enumerate(moodle_rubric, start=1):
            descriptors = []
            max_pts = 0.0
            for lv in row.get("levels", []):
                m_pts = re.search(r"(\d+(?:[.,]\d+)?)", lv.get("score") or "")
                pts_val = float(m_pts.group(1).replace(",", ".")) if m_pts else 0.0
                max_pts = max(max_pts, pts_val)
                descriptors.append(
                    {
                        "level": lv.get("score") or f"Nivel {len(descriptors) + 1}",
                        "description": lv.get("definition") or "Descriptor docente",
                        "points": pts_val,
                    }
                )
            criteria.append(
                {
                    "id": f"crit-{idx:02d}",
                    "text": row.get("criterion") or f"Criterio {idx}",
                    "points": max_pts,
                    "descriptors": descriptors,
                    "requirement_ids": req_ids[: min(4, len(req_ids))],
                }
            )
    else:
        # Buscar tabla textual Criterio \t Indicador \t Puntos en intro_text (ej. Seminario I)
        in_table = False
        for raw_line in intro.splitlines():
            parts = [p.strip() for p in raw_line.split("\t") if p.strip()]
            if len(parts) >= 2 and parts[0].lower() == "criterio":
                in_table = True
                continue
            if in_table:
                if parts and parts[0].lower().startswith("total"):
                    break
                if len(parts) >= 3 and re.match(r"^\d+(?:[.,]\d+)?$", parts[-1]):
                    pts = float(parts[-1].replace(",", "."))
                    criteria.append(
                        {
                            "id": f"crit-{len(criteria) + 1:02d}",
                            "text": f"{parts[0]}: {parts[1]}",
                            "points": pts,
                            "descriptors": [{"level": "Máximo", "description": parts[1], "points": pts}],
                            "requirement_ids": req_ids[: min(4, len(req_ids))],
                        }
                    )

    weight_match = re.search(r"Valor\s*[:\t ]*(\d+(?:[.,]\d+)?)\s*%", intro, re.IGNORECASE)
    if not weight_match:
        weight_match = re.search(r"\b(\d+(?:[.,]\d+)?)\s*%", module_snapshot.get("title") or "")
    weight = float(weight_match.group(1).replace(",", ".")) if weight_match else None
    scale_total = round(sum(c["points"] for c in criteria if c["points"] is not None), 4) if criteria else None

    assessment = {
        "kind": "summative",
        "scale_total": scale_total if scale_total and scale_total > 0 else None,
        "weight": weight,
        "weight_unit": "percent" if weight is not None else None,
        "criteria": criteria,
        "editorial_checks": [
            "Sin exposición de credenciales ni metadatos operativos en entregables",
            "Citas verificables en bibliografía local y formato APA 7",
            "Colaboración de estilo con estilo-escribir y compilación limpia",
        ],
    }
    return assessment, bool(criteria or weight is not None)


def _infer_products(
    subject_slug: str,
    activity_number: int,
    module_snapshot: dict[str, Any],
    req_ids: list[str],
    layout: dict[str, Path],
    subject_root: Path,
) -> list[dict[str, Any]]:
    kind = module_snapshot.get("kind") or "assign"
    intro = module_snapshot.get("intro_text") or ""
    deliveries_rel = layout["deliveries"].relative_to(subject_root).as_posix()
    editable_rel = f"reporte-{subject_slug}-Actividad-{int(activity_number)}.tex"

    if kind == "quiz":
        return [
            {
                "id": "prod-01",
                "kind": "quiz_preparation_report",
                "recipient": "student_study_only",
                "editable_format": "LaTeX (.tex)",
                "submission_format": "Plataforma Moodle en línea (solo lectura para agentes)",
                "structure": ["Resumen y tabla de contenido", "Introducción", "Fundamentos y matriz de estudio", "Conclusiones y referencias"],
                "length": "Sin archivo en carpeta de entregas; cuestionario en línea de 1 intento",
                "filename_pattern": f"reporte-{subject_slug}-Actividad-{int(activity_number)}.pdf",
                "accessibility": None,
                "requirement_ids": req_ids,
                "paths": {"editable": editable_rel, "delivery": None},
            }
        ]

    if ".docx" in intro.lower() or "word" in intro.lower():
        delivery_rel = f"{deliveries_rel}/Tarea{int(activity_number)}_DeLaCruzMunoz.docx"
        return [
            {
                "id": "prod-01",
                "kind": "cumulative_word_and_latex_report",
                "recipient": "Moodle assignment",
                "editable_format": "Word (.docx) acumulativo + LaTeX (.tex) sincronizado",
                "submission_format": "DOCX único con apartados acumulados, Matriz de Consistencia y Círculo de Covey",
                "structure": [
                    "Portada institucional actualizada",
                    "Apartados acumulados corregidos 1 a 8 (incluyendo 8.1 a 8.5)",
                    "Referencias APA 7ª edición",
                    "Anexo 1: Matriz de Consistencia actualizada",
                    "Anexo 2: Círculo de Covey vigente",
                ],
                "length": "Documento acumulativo completo con apartado 8 desarrollado conforme a guía 3.8",
                "filename_pattern": f"Tarea{int(activity_number)}_DeLaCruzMunoz.docx",
                "accessibility": None,
                "requirement_ids": req_ids,
                "paths": {"editable": editable_rel, "delivery": delivery_rel},
            }
        ]

    is_arial_11 = bool(re.search(r"arial\s*11", intro, re.IGNORECASE))
    max_3_pages = bool(re.search(r"m[áa]ximo\s*3\s*(?:p[áa]ginas|cuartillas)", intro, re.IGNORECASE))
    deliv_suffix = "Investigacion-estimacion-intervalos.pdf" if is_arial_11 else "Ejercicios-estimacion-intervalos.pdf"
    delivery_rel = f"{deliveries_rel}/Actividad-{int(activity_number)}-{deliv_suffix}"
    length_spec = (
        "Máximo 3 cuartillas de cuerpo sin considerar portada y fuentes (Arial 11, interlineado 1.5, justificado)"
        if (is_arial_11 and max_3_pages)
        else "PDF completo de ejercicios resueltos con portada oficial (Arial 12, interlineado 1.5, justificado)"
    )
    return [
        {
            "id": "prod-01",
            "kind": "pdf_academic_deliverable",
            "recipient": "Moodle assignment",
            "editable_format": "LaTeX (.tex)",
            "submission_format": "PDF con portada oficial ITESCA",
            "structure": [
                "Portada oficial ITESCA",
                "Desarrollo estructurado conforme a consigna docente",
                "Fuentes académicas en formato APA 7",
            ],
            "length": length_spec,
            "filename_pattern": Path(delivery_rel).name,
            "accessibility": None,
            "requirement_ids": req_ids,
            "paths": {"editable": editable_rel, "delivery": delivery_rel},
        }
    ]


class RealizarPlaneacionAgent:
    """Agente ``realizar-planeación`` integrado al contrato canónico de AulaTeX."""

    agent_id: str = AGENT_ID_REALIZAR_PLANEACION

    def __init__(
        self,
        workspace: AulaTeXWorkspace | None = None,
        lex_client: McpLexClient | None = None,
    ) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.lex_client = lex_client or get_lex_client()

    def run(self, request: RealizarPlaneacionRequest) -> RealizarPlaneacionResult:
        subject_root = self.workspace.resolve_target(request.target)
        if not subject_root.is_dir():
            raise ValueError(f"Directorio de materia inexistente: {subject_root}")

        layout = subject_layout(subject_root)
        layout["plans"].mkdir(parents=True, exist_ok=True)

        mod = request.module_snapshot
        mid = int(mod["module_id"])
        title = str(mod.get("title") or f"Actividad {request.activity_number}").strip()
        meta = _resolve_verified_subject_metadata(subject_root, request.activity_number)
        notes_dir = resolve_activity_notes_dir(
            subject_root,
            request.activity_number,
            title,
            request.notes_subdir_hint,
        )

        # Archivar captura instruccional sanitizada en la carpeta de notas de la actividad
        captured_at = datetime.now(timezone.utc).isoformat()
        consigna_payload = (
            f"Curso: {meta['course_code'] or ''} - {meta['subject_title']}\n"
            f"Actividad plataforma: {title}\n"
            f"URL: {mod.get('url') or ''}\n"
            f"Fechas: {mod.get('activity_dates') or ''}\n\n"
            f"--- CONSIGNA ---\n{mod.get('intro_text') or ''}\n\n"
            f"--- ESTADO Y RÚBRICA ---\n{mod.get('full_main_text') or ''}\n"
        )
        assert_no_credential_leak(consigna_payload)
        consigna_path = notes_dir / f"consigna-itesca-{mid}.txt"
        consigna_bytes = consigna_payload.encode("utf-8")
        consigna_path.write_bytes(consigna_bytes)
        consigna_sha = _sha256_bytes(consigna_bytes)
        consigna_rel = consigna_path.relative_to(subject_root).as_posix()

        sources: list[dict[str, Any]] = [
            {
                "id": f"src-itesca-{mid}",
                "kind": "platform",
                "authority": "instructional",
                "title": f"Consigna autenticada ITESCA módulo {mid} ({title})",
                "url": mod.get("url"),
                "path": consigna_rel,
                "sha256": consigna_sha,
                "captured_at": captured_at,
                "media_type": "text/plain",
            }
        ]

        if meta["template_tex_rel"]:
            tpl_file = subject_root / meta["template_tex_rel"]
            sources.append(
                {
                    "id": "src-subject-template",
                    "kind": "other",
                    "authority": "editorial",
                    "title": tpl_file.name,
                    "url": None,
                    "path": meta["template_tex_rel"],
                    "sha256": _sha256_bytes(tpl_file.read_bytes()),
                    "captured_at": captured_at,
                    "media_type": "text/x-tex",
                }
            )

        feedback_summaries: list[dict[str, Any]] = []
        if request.related_feedback_snapshots:
            for fb_mod in request.related_feedback_snapshots:
                fb_mid = fb_mod.get("module_id")
                sf = fb_mod.get("submission_and_feedback") or {}
                fb_text = (sf.get("teacher_feedback_full") or "").strip()
                grade = (sf.get("status_table") or {}).get("Calificación", "")
                if fb_text:
                    feedback_summaries.append(
                        {
                            "module_id": fb_mid,
                            "title": fb_mod.get("title", ""),
                            "grade": grade,
                            "feedback": fb_text,
                        }
                    )
            if feedback_summaries:
                fb_path = notes_dir / "retroalimentacion-previa-itesca.json"
                fb_bytes = (json.dumps(feedback_summaries, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
                assert_no_credential_leak(feedback_summaries)
                fb_path.write_bytes(fb_bytes)
                sources.append(
                    {
                        "id": "src-prior-feedback",
                        "kind": "platform",
                        "authority": "instructional",
                        "title": "Retroalimentación docente previa verificada en ITESCA",
                        "url": None,
                        "path": fb_path.relative_to(subject_root).as_posix(),
                        "sha256": _sha256_bytes(fb_bytes),
                        "captured_at": captured_at,
                        "media_type": "application/json",
                    }
                )

        intro_text = (mod.get("intro_text") or "").strip()
        requirements, questions, topics = _segment_requirements_and_questions(intro_text)
        req_ids = [r["id"] for r in requirements]
        topic_ids = [t["id"] for t in topics]
        assessment, has_confirmed_assessment = _parse_assessment(mod, req_ids)
        products = _infer_products(meta["slug"], request.activity_number, mod, req_ids, layout, subject_root)
        prod_ids = [p["id"] for p in products]
        crit_ids = [c["id"] for c in assessment["criteria"]]

        sequence = [
            {
                "id": "step-01",
                "order": 1,
                "phase": "preparation",
                "action": "Recopilar, descargar y verificar recursos docentes y bibliografía local con encontrar-recursos.",
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
                "output": f"{notes_dir.relative_to(subject_root).as_posix()}/conceptos/fichas_conceptos.json",
                "completion_check": "Artefactos nucleares del extractor presentes en notas y sincronizados",
                "requirement_ids": req_ids,
                "depends_on": ["step-01"],
            },
            {
                "id": "step-03",
                "order": 3,
                "phase": "construction",
                "action": "Desarrollar entregable con plantillas institucionales y colaboración de estilo con estilo-escribir.",
                "inputs": [f"{notes_dir.relative_to(subject_root).as_posix()}/conceptos/fichas_conceptos.json"],
                "output": products[0]["paths"]["editable"],
                "completion_check": "Compilación limpia, contrato editorial en 100 y estilo aceptable",
                "requirement_ids": req_ids,
                "depends_on": ["step-02"],
            },
            {
                "id": "step-04",
                "order": 4,
                "phase": "review",
                "action": "Ejecutar ciclos de calidad, verificación tipográfica/visual y empaquetado local sin envío no autorizado.",
                "inputs": [products[0]["paths"]["editable"]],
                "output": products[0]["paths"]["delivery"] or products[0]["paths"]["editable"],
                "completion_check": "Validación estructural, numérica y visual aprobada",
                "requirement_ids": req_ids,
                "depends_on": ["step-03"],
            },
        ]

        resources_plan = [
            {
                "id": "res-consigna",
                "source_id": f"src-itesca-{mid}",
                "purpose": "Consigna, fechas y criterios oficiales publicados en ITESCA Virtual",
                "required": True,
                "access": "local",
                "rights": "Uso académico interno del estudiante inscrito",
            }
        ]
        if feedback_summaries:
            resources_plan.append(
                {
                    "id": "res-feedback-previo",
                    "source_id": "src-prior-feedback",
                    "purpose": "Observaciones docentes previas de atención obligatoria según rúbrica",
                    "required": True,
                    "access": "local",
                    "rights": "Uso académico interno",
                }
            )

        blockers: list[dict[str, Any]] = []
        quiz_state = mod.get("quiz_state") or {}
        if quiz_state.get("read_only_blocker"):
            blockers.append(dict(quiz_state["read_only_blocker"]))

        primary_ev = [
            {
                "source_id": f"src-itesca-{mid}",
                "locator": "consigna-itesca",
                "quoted_text": intro_text[:280] if intro_text else title,
            }
        ]

        field_status: list[dict[str, Any]] = [
            {
                "path": "/identity",
                "state": "confirmed" if meta["template_tex_rel"] else "inferred",
                "reason": "Identidad institucional verificada en plantilla canónica de la asignatura.",
                "evidence": (
                    [{"source_id": "src-subject-template", "locator": "macros-itesca", "quoted_text": meta["subject_title"]}]
                    if meta["template_tex_rel"]
                    else primary_ev
                ),
                "alternatives": [],
            },
            {
                "path": "/activities/0/instruction",
                "state": "confirmed",
                "reason": "Consigna extraída directamente de ITESCA Virtual en sesión de solo lectura.",
                "evidence": primary_ev,
                "alternatives": [],
            },
            {
                "path": "/activities/0/requirements",
                "state": "confirmed",
                "reason": "Requisitos segmentados línea por línea desde la consigna autenticada.",
                "evidence": primary_ev,
                "alternatives": [],
            },
            {
                "path": "/activities/0/questions",
                "state": "confirmed",
                "reason": "Preguntas explícitas extraídas literalmente del temario de la consigna.",
                "evidence": primary_ev,
                "alternatives": [],
            },
            {
                "path": "/activities/0/products",
                "state": "confirmed",
                "reason": "Formato y producto derivados de la sección Formato de entrega de la consigna.",
                "evidence": primary_ev,
                "alternatives": [],
            },
            {
                "path": "/activities/0/assessment",
                "state": "confirmed" if has_confirmed_assessment else "inferred",
                "reason": (
                    "Ponderación y criterios tomados de la consigna/rúbrica publicada en Moodle."
                    if has_confirmed_assessment
                    else "Sin rúbrica tabular desglosada en Moodle; se conserva verificación editorial."
                ),
                "evidence": primary_ev,
                "alternatives": [],
            },
        ]

        critical_gaps = [b["reason"] for b in blockers]
        role = "assessment" if mod.get("kind") == "quiz" else "learning"
        act_id = f"actividad-{int(request.activity_number)}"

        document: dict[str, Any] = {
            "schema_version": "1.0.0",
            "plan_id": meta["plan_id"],
            "revision": meta["revision"],
            "identity": {
                "institution": "ITESCA",
                "program": meta["program"],
                "subject_id": meta["subject_id"],
                "subject_title": meta["subject_title"],
                "offering_id": meta["offering_id"],
                "period": meta["period"] or "2026-II",
                "modality": "online",
            },
            "sources": sources,
            "curriculum": {
                "purpose": requirements[0]["text"],
                "competencies": [],
                "outcomes": [{"id": f"outcome-{mid}", "text": requirements[0]["text"]}],
                "topics": topics,
            },
            "activities": [
                {
                    "id": act_id,
                    "title": title,
                    "role": role,
                    "platform": {
                        "name": "Moodle ITESCA Virtual",
                        "course_id": str(mod.get("course_id") or ""),
                        "module_ids": [str(mid)],
                    },
                    "unit_id": "unidad-3",
                    "weeks": [],
                    "outcome_ids": [f"outcome-{mid}"],
                    "topic_ids": topic_ids,
                    "cognitive": {
                        "taxonomy": "Bloom revisada",
                        "level": "Analizar / Aplicar",
                        "verb": "Analizar y desarrollar",
                        "object": title,
                        "conditions": "Con apego a consigna oficial, bibliografía verificada y formato institucional ITESCA",
                        "observable_evidence": products[0]["filename_pattern"],
                        "justification": "Inferido editorialmente a partir de los verbos operativos de la consigna.",
                    },
                    "instruction": intro_text or title,
                    "requirements": requirements,
                    "questions": questions,
                    "sequence": sequence,
                    "resources": resources_plan,
                    "assessment": assessment,
                    "products": products,
                    "calendar": {
                        "opens_at": None,
                        "expected_at": None,
                        "due_at": None,
                        "closes_at": None,
                        "timezone": "America/Hermosillo",
                        "literal": mod.get("activity_dates") or None,
                    },
                    "policies": {
                        "ai": "Declaración obligatoria al pie en reportes AulaTeX; verificación autoral íntegra.",
                        "integrity": "Prohibido fabricar referencias, datos empíricos o aprobaciones externas.",
                        "collaboration": "Individual",
                        "citation": "APA 7ª edición",
                        "attempts": 1 if role == "assessment" else None,
                        "late_submission": None,
                        "accessibility": None,
                        "privacy": "Credenciales e identificadores de sesión excluidos de todo artefacto.",
                        "exceptions": [],
                    },
                    "dependencies": [],
                    "alignment": [
                        {
                            "outcome_id": f"outcome-{mid}",
                            "requirement_ids": req_ids,
                            "step_ids": [s["id"] for s in sequence],
                            "product_ids": prod_ids,
                            "criterion_ids": crit_ids,
                        }
                    ],
                    "bindings": {
                        "extractor_directory": f"extractor-aulatex/conceptos-{meta['slug']}-actividad-{int(request.activity_number)}",
                        "notes_directory": notes_dir.relative_to(subject_root).as_posix(),
                        "research_directory": "investigacion-aulatex",
                    },
                }
            ],
            "field_status": field_status,
            "review": {
                "state": "needs_review",
                "reviewed_at": captured_at,
                "reviewer_role": self.agent_id,
                "critical_gaps": critical_gaps,
                "semantic_validation": "not_run",
            },
            "artifact_contract": artifact_contract(subject_root),
            "extensions": {
                "itesca_workflow": {
                    "agent_id": self.agent_id,
                    "course_code": meta["course_code"],
                    "teacher": meta["teacher"],
                    "local_activity_number": int(request.activity_number),
                    "moodle_module_id": mid,
                    "instructional_attachments": mod.get("instructional_attachments") or [],
                    "related_links": mod.get("related_links") or [],
                    "prior_feedback_count": len(feedback_summaries),
                    "updated_at_utc": captured_at,
                }
            },
        }

        validate_schema(document, PEDAGOGICAL_SCHEMA_PATH)
        sem_val = validate_pedagogical(document, subject_root)
        document["review"]["semantic_validation"] = "passed" if sem_val["passed"] else "failed"
        validate_schema(document, PEDAGOGICAL_SCHEMA_PATH)
        assert_no_credential_leak(document)

        plan_json_path = layout["plans"] / f"planeacion-{meta['slug']}-Actividad-{int(request.activity_number)}.json"
        plan_md_path = layout["plans"] / f"planeacion-{meta['slug']}-Actividad-{int(request.activity_number)}.md"
        extractor_plan_path = notes_dir / f"planeacion-actividad-{int(request.activity_number)}-extractor.md"

        plan_json_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        md_text = self._render_markdown(document, meta, mod, feedback_summaries, sem_val)
        assert_no_credential_leak(md_text)
        plan_md_path.write_text(md_text, encoding="utf-8")
        extractor_plan_path.write_text(md_text, encoding="utf-8")

        return RealizarPlaneacionResult(
            agent_id=self.agent_id,
            activity_number=int(request.activity_number),
            module_id=mid,
            subject_root=subject_root,
            notes_dir=notes_dir,
            plan_json_path=plan_json_path,
            plan_md_path=plan_md_path,
            extractor_plan_path=extractor_plan_path,
            consigna_path=consigna_path,
            semantic_validation=sem_val,
            blockers=tuple(blockers),
        )

    def _render_markdown(
        self,
        document: dict[str, Any],
        meta: dict[str, Any],
        mod: dict[str, Any],
        feedback_summaries: list[dict[str, Any]],
        sem_val: dict[str, Any],
    ) -> str:
        act = document["activities"][0]
        prod = act["products"][0]
        lines = [
            f"# Planeación Académica — {act['title']}",
            "",
            "## 1. Identificación verificada",
            f"- **Institución:** ITESCA (`ITESCA Virtual`)",
            f"- **Programa:** {meta['program_name'] or document['identity']['program']}",
            f"- **Asignatura:** {meta['subject_title']} (`{meta['course_code'] or document['identity']['subject_id']}`)",
            f"- **Docente:** {meta['teacher'] or 'Por verificar en encuadre'}",
            f"- **Periodo:** {document['identity']['period']}",
            f"- **Actividad local:** Actividad {document['extensions']['itesca_workflow']['local_activity_number']} (Módulo Moodle `{mod['module_id']}`)",
            f"- **Calendario publicado:** `{(mod.get('activity_dates') or 'Sin fecha publicada').replace(chr(10), ' | ')}`",
            f"- **Validación semántica (`validate_pedagogical`):** `{'passed' if sem_val['passed'] else 'failed'}`",
            "",
            "## 2. Consigna oficial extraída (`extraido` / `confirmed`)",
            "",
            act["instruction"] or "",
            "",
            "## 3. Requisitos segmentados",
            "",
        ]
        for req in act["requirements"]:
            lines.append(f"- **{req['id']}:** {req['text']}")
        lines.extend(
            [
                "",
                "## 4. Contrato del entregable y rutas del proyecto",
                f"- **Tipo de producto:** `{prod['kind']}`",
                f"- **Formato editable:** {prod['editable_format']} (`{prod['paths']['editable']}`)",
                f"- **Formato de entrega:** {prod['submission_format']}",
                f"- **Ruta de entrega local:** `{prod['paths']['delivery'] or 'Solo reporte raíz (sin archivo en entregas)'}`",
                f"- **Extensión y tipografía:** {prod['length']}",
                f"- **Carpeta de notas de la actividad:** `{act['bindings']['notes_directory']}`",
                f"- **Carpeta de extracción sincronizada:** `{act['bindings']['extractor_directory']}`",
                "",
                "## 5. Criterios de evaluación y rúbrica",
                "",
            ]
        )
        if act["assessment"]["criteria"]:
            for crit in act["assessment"]["criteria"]:
                lines.append(f"- **{crit['text']}** ({crit['points']} pts)")
        else:
            lines.append(f"- Ponderación declarada: `{act['assessment']['weight'] or 'N/D'}%` (sin rúbrica tabular adicional en plataforma).")

        if feedback_summaries:
            lines.extend(["", "## 6. Observaciones docentes previas a integrar", ""])
            for fb in feedback_summaries:
                lines.append(f"### {fb['title']} (Calificación: `{fb['grade']}`)")
                lines.append(fb["feedback"])
                lines.append("")

        if document["review"]["critical_gaps"]:
            lines.extend(["", "## 7. Bloqueos y límites operativos declarados", ""])
            for gap in document["review"]["critical_gaps"]:
                lines.append(f"- **BLOQUEO:** {gap}")

        lines.extend(
            [
                "",
                "## 8. Secuencia de ejecución bajo coordinación `aulatex`",
                "1. `realizar-planeación`: consolidación de consigna, rúbrica y trazabilidad documental.",
                "2. `encontrar-recursos`: descarga autenticada y organización de adjuntos docentes y biblioteca verificada.",
                "3. `extraer-conceptos`: generación de conceptos e ideas en la carpeta de notas de la actividad.",
                "4. `realizar-actividad` + `estilo-escribir`: elaboración con plantillas institucionales, refinamiento de estilo y ciclos de calidad.",
                "",
            ]
        )
        return "\n".join(lines)


__all__ = [
    "AGENT_ID_REALIZAR_PLANEACION",
    "RealizarPlaneacionAgent",
    "RealizarPlaneacionRequest",
    "RealizarPlaneacionResult",
    "resolve_activity_notes_dir",
]
