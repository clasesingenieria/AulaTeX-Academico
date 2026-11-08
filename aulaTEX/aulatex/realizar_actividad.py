"""Agente ``realizar-actividad`` para desarrollo, compilación y ciclos de calidad en AulaTeX.

Ejecuta la etapa final de la secuencia obligatoria:
``planeación`` -> ``recopilación y organización de recursos`` -> ``extracción de conceptos`` -> ``realización de actividades y ciclos de calidad``.

Responsabilidades verificadas:
1. Comprobar prerrequisitos aguas arriba (planeación canónica, ``recursos-actividad.json``
   y artefactos de ``conceptos/`` en la carpeta de notas de la actividad).
2. Materializar la plantilla de la materia cuando aún no exista fuente editable sin pisar trabajo existente.
3. Colaborar explícitamente con ``estilo-escribir`` sobre fuentes ``.tex`` (y ``.docx`` acumulativos)
   hasta alcanzar estilo aceptable sin hallazgos críticos.
4. Ejecutar compilación aislada con ``latexmk`` (vía ``AulaTeXWorkspace.compile_tex``),
   observación contractual con ``ActivityObserver``, auditoría tipográfica/geométrica en PDF
   con ``pymupdf``, generación de hoja de contacto visual PNG y promoción verificada a
   ``entregas-<slug>/`` cuando corresponda.
5. Respetar bloqueos operativos reales (p. ej. cuestionarios en línea de intento único
   protegidos en modo solo lectura) informándolos sin declarar completada la resolución en vivo.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
from typing import Any

from .activity_observer import ActivityObservationRequest, ActivityObserver
from .estilo_escribir import AGENT_ID_ESTILO_ESCRIBIR, EstiloEscribirAgent
from .extraer_conceptos import _core_artifacts_complete
from .mcp_lex import McpLexClient, audit_landscape_geometry, get_lex_client
from .navegacion_plataforma import assert_no_credential_leak
from .planning_layout import subject_layout
from .template_materializer import TemplateMaterializer
from .workspace import AulaTeXWorkspace

AGENT_ID_REALIZAR_ACTIVIDAD = "realizar-actividad"


@dataclass(frozen=True)
class RealizarActividadRequest:
    target: str
    activity_number: int
    plan_json_path: str | Path = ""
    delivery_source_tex: str | Path = ""
    delivery_target_rel: str = ""
    expected_delivery_pages: int | None = None
    expected_arial_pt: float | None = None
    docx_deliverable_rel: str = ""
    use_llm_style_refinement: bool = False
    style_engine: str = "Amazon Nova Pro"


@dataclass(frozen=True)
class PdfQualityReport:
    pdf_path: str
    page_count: int
    sha256: str
    unresolved_citations: bool
    operational_leak_hits: tuple[str, ...]
    overflow_spans_count: int
    fonts_detected: tuple[str, ...]
    arial_pt_ok: bool
    expected_pages_ok: bool
    contact_sheet_path: str
    passed: bool
    landscape_pages_detected: int = 0
    landscape_geometry_ok: bool = True
    landscape_headers_footers_suppressed: bool = True
    landscape_issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class RealizarActividadResult:
    agent_id: str
    run_id: str
    activity_number: int
    subject_root: Path
    ok: bool
    stage_status: str
    report_tex_path: Path
    report_pdf_path: Path | None
    delivery_artifact_path: Path | None
    style_results: tuple[dict[str, Any], ...]
    observer_evaluation: dict[str, Any]
    pdf_quality_reports: tuple[dict[str, Any], ...]
    docx_quality_report: dict[str, Any] | None
    blockers: tuple[dict[str, Any], ...]
    manifest_path: Path


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _audit_and_render_pdf(
    pdf_path: Path,
    *,
    repo_root: Path,
    label: str,
    expected_pages: int | None = None,
    expected_arial_pt: float | None = None,
) -> PdfQualityReport:
    import pymupdf
    from PIL import Image, ImageDraw

    qa_dir = repo_root / ".build" / "qa-itesca-workflow"
    qa_dir.mkdir(parents=True, exist_ok=True)

    fonts: set[str] = set()
    overflow_count = 0
    arial_sizes: list[float] = []
    full_text_chunks: list[str] = []

    with pymupdf.open(pdf_path) as doc:
        page_count = len(doc)
        cols = min(3, max(1, page_count))
        rows = math.ceil(page_count / cols)
        sheet = Image.new("RGB", (cols * 360, rows * 465), "#e5e7eb")

        for idx, page in enumerate(doc):
            txt = page.get_text("text") or ""
            full_text_chunks.append(txt)

            # Revisar geometría y tipografía desde la página 2 (cuerpo académico)
            if idx >= 1:
                for block in page.get_text("dict").get("blocks", []):
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            stext = (span.get("text") or "").strip()
                            if not stext:
                                continue
                            bbox = pymupdf.Rect(span["bbox"])
                            if bbox.x0 < -2.0 or bbox.x1 > page.rect.width + 4.0:
                                overflow_count += 1
                            fname = str(span.get("font") or "")
                            fonts.add(fname)
                            if "Arial" in fname and bbox.y1 < page.rect.height - 52:
                                arial_sizes.append(float(span.get("size") or 0.0))

            pix = page.get_pixmap(matrix=pymupdf.Matrix(1.1, 1.1))
            im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            im.thumbnail((340, 435))
            x = (idx % cols) * 360
            y = (idx // cols) * 465
            sheet.paste(im, (x + (360 - im.width) // 2, y + 4))
            ImageDraw.Draw(sheet).text((x + 8, y + 444), f"{label} p.{idx + 1}", fill="#111827")

        contact_path = qa_dir / f"{label}-contacto.png"
        sheet.save(contact_path)

    joined_text = "\n".join(full_text_chunks)
    assert_no_credential_leak(joined_text)

    unresolved = ("[?]" in joined_text) or ("(??)" in joined_text)
    leak_hits: list[str] = []
    for pat_label, pat in (
        ("modulo_moodle", re.compile(r"\bM[óo]dulo Moodle\b", re.I)),
        ("portal_itesca_url", re.compile(r"cursos3\.e-itesca\.edu\.mx", re.I)),
        ("actividad_local", re.compile(r"\bActividad local\s+\d+\b", re.I)),
    ):
        if pat.search(joined_text):
            leak_hits.append(pat_label)

    arial_pt_ok = True
    if expected_arial_pt is not None:
        if not arial_sizes:
            arial_pt_ok = False
        else:
            # Conversión TeX pt (72.27/in) -> PDF bp (72/in), o pt directo en fontspec
            target_bp = expected_arial_pt * 72.0 / 72.27
            dominant = sorted(arial_sizes)[len(arial_sizes) // 2]
            arial_pt_ok = (abs(dominant - target_bp) <= 0.35) or (abs(dominant - expected_arial_pt) <= 0.35)

    expected_pages_ok = (expected_pages is None) or (page_count == expected_pages)
    
    landscape_audit = audit_landscape_geometry(pdf_path)
    landscape_pages_detected = int(landscape_audit.get("landscape_pages_detected") or 0)
    landscape_geometry_ok = bool(landscape_audit.get("geometry_ok", True))
    landscape_headers_footers_suppressed = bool(landscape_audit.get("headers_footers_suppressed", True))
    landscape_issues = tuple(str(x) for x in landscape_audit.get("issues") or ())

    passed = (
        (not unresolved)
        and (not leak_hits)
        and (overflow_count == 0)
        and arial_pt_ok
        and expected_pages_ok
        and landscape_geometry_ok
        and landscape_headers_footers_suppressed
    )

    return PdfQualityReport(
        pdf_path=pdf_path.relative_to(repo_root).as_posix(),
        page_count=page_count,
        sha256=_sha256_file(pdf_path),
        unresolved_citations=unresolved,
        operational_leak_hits=tuple(leak_hits),
        overflow_spans_count=overflow_count,
        fonts_detected=tuple(sorted(fonts)),
        arial_pt_ok=arial_pt_ok,
        expected_pages_ok=expected_pages_ok,
        contact_sheet_path=contact_path.relative_to(repo_root).as_posix(),
        passed=passed,
        landscape_pages_detected=landscape_pages_detected,
        landscape_geometry_ok=landscape_geometry_ok,
        landscape_headers_footers_suppressed=landscape_headers_footers_suppressed,
        landscape_issues=landscape_issues,
    )


def _audit_docx_deliverable(docx_path: Path, style_agent: EstiloEscribirAgent, repo_root: Path) -> dict[str, Any]:
    from docx import Document

    doc = Document(docx_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    headings = [
        {"style": p.style.name if p.style else "", "text": p.text.strip()}
        for p in doc.paragraphs
        if p.text.strip() and p.style and ("Heading" in p.style.name or "Título" in p.style.name)
    ]
    joined = "\n".join(paragraphs)
    assert_no_credential_leak(joined)
    style_eval = style_agent.evaluate_plain_prose(joined)
    return {
        "docx_path": docx_path.relative_to(repo_root).as_posix(),
        "sha256": _sha256_file(docx_path),
        "size_bytes": docx_path.stat().st_size,
        "paragraph_count": len(paragraphs),
        "table_count": len(doc.tables),
        "section_count": len(doc.sections),
        "headings_count": len(headings),
        "style_evaluation": asdict(style_eval),
        "passed": style_eval.passed and len(paragraphs) >= 30,
    }


class RealizarActividadAgent:
    """Agente ``realizar-actividad`` coordinado con ``estilo-escribir`` y los validadores de AulaTeX."""

    agent_id: str = AGENT_ID_REALIZAR_ACTIVIDAD

    def __init__(
        self,
        workspace: AulaTeXWorkspace | None = None,
        style_agent: EstiloEscribirAgent | None = None,
        observer: ActivityObserver | None = None,
        materializer: TemplateMaterializer | None = None,
        lex_client: McpLexClient | None = None,
    ) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.lex_client = lex_client or get_lex_client()
        self.style_agent = style_agent or EstiloEscribirAgent(self.workspace, lex_client=self.lex_client)
        self.observer = observer or ActivityObserver(self.workspace)
        self.materializer = materializer or TemplateMaterializer(self.workspace)
        self.runs_root = self.workspace.feedback_root / "realizar-actividad" / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)

    def _verify_upstream_pipeline(self, subject_root: Path, slug: str, activity_number: int, plan_json_path: str | Path) -> tuple[Path, dict[str, Any], Path]:
        layout = subject_layout(subject_root)
        plan_path = (
            Path(plan_json_path).resolve()
            if str(plan_json_path).strip()
            else layout["plans"] / f"planeacion-{slug}-Actividad-{int(activity_number)}.json"
        )
        if not plan_path.is_file():
            raise FileNotFoundError(
                f"Bloqueo de secuencia: falta la planeación canónica ({plan_path}). Ejecuta primero realizar-planeación."
            )
        plan_doc = json.loads(plan_path.read_text(encoding="utf-8-sig"))
        act = plan_doc["activities"][0]
        notes_rel = act["bindings"].get("notes_directory")
        if not notes_rel:
            raise ValueError("Bloqueo de contrato: la planeación no declara bindings.notes_directory.")
        notes_dir = (subject_root / notes_rel).resolve()

        resources_manifest = notes_dir / "recursos-actividad.json"
        if not resources_manifest.is_file():
            raise FileNotFoundError(
                f"Bloqueo de secuencia: falta recursos-actividad.json ({resources_manifest}). Ejecuta primero encontrar-recursos."
            )

        concepts_dir = notes_dir / "conceptos"
        if not _core_artifacts_complete(concepts_dir):
            raise FileNotFoundError(
                f"Bloqueo de secuencia: faltan artefactos nucleares de conceptos en {concepts_dir}. Ejecuta primero extraer-conceptos."
            )
        return plan_path, plan_doc, notes_dir

    def _resolve_canonical_bib(self, subject_root: Path, slug: str) -> Path | None:
        preferred = subject_root / "referencias-estadistica-verificadas.bib"
        if preferred.is_file():
            return preferred
        candidate = subject_root / f"{slug}.bib"
        if candidate.is_file():
            return candidate
        bibs = sorted(subject_root.glob("*.bib"))
        return bibs[0] if bibs else None

    def run(self, request: RealizarActividadRequest) -> RealizarActividadResult:
        subject_root = self.workspace.resolve_target(request.target)
        layout = subject_layout(subject_root)
        slug = subject_root.name
        for suffix in ("-mga", "-lde", "-lae", "-iias"):
            if slug.endswith(suffix):
                slug = slug[: -len(suffix)]
                break

        _plan_path, plan_doc, _notes_dir = self._verify_upstream_pipeline(
            subject_root, slug, int(request.activity_number), request.plan_json_path
        )
        act = plan_doc["activities"][0]
        plan_blockers = list(((plan_doc.get("extensions") or {}).get("itesca_workflow") or {}).get("blockers") or [])
        is_live_quiz = any(b.get("code") == "live_quiz_attempt_protected" for b in plan_blockers)

        report_tex = subject_root / f"reporte-{slug}-Actividad-{int(request.activity_number)}.tex"
        if not report_tex.is_file():
            self.materializer.materialize_subject(
                subject_root,
                activity_number=int(request.activity_number),
                force=False,
            )
        if not report_tex.is_file():
            raise FileNotFoundError(
                f"No existe la plantilla/fuente editable requerida para la Actividad {request.activity_number}: {report_tex}"
            )

        bib_path = self._resolve_canonical_bib(subject_root, slug)
        style_results: list[dict[str, Any]] = []

        # 1) Colaboración de estilo en el reporte principal .tex
        main_style = self.style_agent.collaborate_on_tex(
            report_tex,
            bib_path=bib_path,
            apply=True,
            use_llm=request.use_llm_style_refinement,
            engine=request.style_engine,
        )
        style_results.append(
            {
                "role": AGENT_ID_ESTILO_ESCRIBIR,
                "artifact": report_tex.relative_to(self.workspace.repo_root).as_posix(),
                "before": asdict(main_style.before),
                "after": asdict(main_style.after),
                "applied_changes": list(main_style.applied_changes),
                "passed": main_style.after.passed,
            }
        )

        # Si existe versión compacta de entrega (ej. contenido-entrega.tex + version-entrega.tex), auditarla también
        delivery_tex_path: Path | None = None
        if str(request.delivery_source_tex).strip():
            delivery_tex_path = (
                Path(request.delivery_source_tex).resolve()
                if Path(request.delivery_source_tex).is_absolute()
                else (subject_root / request.delivery_source_tex).resolve()
            )
            companion_content = delivery_tex_path.parent / "contenido-entrega.tex"
            style_target_compact = companion_content if companion_content.is_file() else delivery_tex_path
            compact_style = self.style_agent.collaborate_on_tex(
                style_target_compact,
                bib_path=bib_path,
                apply=True,
                use_llm=request.use_llm_style_refinement,
                engine=request.style_engine,
            )
            style_results.append(
                {
                    "role": AGENT_ID_ESTILO_ESCRIBIR,
                    "artifact": style_target_compact.relative_to(self.workspace.repo_root).as_posix(),
                    "before": asdict(compact_style.before),
                    "after": asdict(compact_style.after),
                    "applied_changes": list(compact_style.applied_changes),
                    "passed": compact_style.after.passed,
                }
            )

        # 2) Compilación aislada del reporte principal con latexmk
        compile_main = self.workspace.compile_tex(report_tex, clean_mode="safe")
        if not compile_main.ok:
            raise RuntimeError(
                f"Fallo de compilación LaTeX en {report_tex.name} (rc={compile_main.returncode}):\n"
                f"{(compile_main.stdout or '')[-1800:]}\n{(compile_main.stderr or '')[-1800:]}"
            )
        report_pdf = report_tex.with_suffix(".pdf")
        if not report_pdf.is_file():
            raise FileNotFoundError(f"No se encontró el PDF compilado esperado: {report_pdf}")

        pdf_reports: list[PdfQualityReport] = [
            _audit_and_render_pdf(
                report_pdf,
                repo_root=self.workspace.repo_root,
                label=f"{slug}-act{int(request.activity_number):02d}-raiz",
                expected_pages=None,
                expected_arial_pt=None,
            )
        ]

        # 3) Compilación y promoción del entregable de plataforma (salvo cuestionario en vivo protegido)
        delivery_artifact_path: Path | None = None
        if not is_live_quiz:
            if delivery_tex_path is not None:
                compile_deliv = self.workspace.compile_tex(delivery_tex_path, clean_mode="safe")
                if not compile_deliv.ok:
                    raise RuntimeError(
                        f"Fallo de compilación en entregable compacto {delivery_tex_path.name} "
                        f"(rc={compile_deliv.returncode}):\n{(compile_deliv.stdout or '')[-1800:]}"
                    )
                built_deliv_pdf = delivery_tex_path.with_suffix(".pdf")
                target_rel = request.delivery_target_rel or f"{layout['deliveries'].name}/Actividad-{int(request.activity_number)}.pdf"
                delivery_artifact_path = (subject_root / target_rel).resolve()
                delivery_artifact_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(built_deliv_pdf, delivery_artifact_path)
                pdf_reports.append(
                    _audit_and_render_pdf(
                        delivery_artifact_path,
                        repo_root=self.workspace.repo_root,
                        label=f"{slug}-act{int(request.activity_number):02d}-entrega",
                        expected_pages=request.expected_delivery_pages,
                        expected_arial_pt=request.expected_arial_pt,
                    )
                )
            elif str(request.delivery_target_rel).strip():
                delivery_artifact_path = (subject_root / request.delivery_target_rel).resolve()
                delivery_artifact_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(report_pdf, delivery_artifact_path)
                pdf_reports.append(
                    _audit_and_render_pdf(
                        delivery_artifact_path,
                        repo_root=self.workspace.repo_root,
                        label=f"{slug}-act{int(request.activity_number):02d}-entrega",
                        expected_pages=request.expected_delivery_pages,
                        expected_arial_pt=request.expected_arial_pt,
                    )
                )

        # 4) Validación de entregable acumulativo Word (.docx) cuando aplique (ej. Seminario I)
        docx_report: dict[str, Any] | None = None
        if str(request.docx_deliverable_rel).strip():
            docx_candidate = (subject_root / request.docx_deliverable_rel).resolve()
            if not docx_candidate.is_file():
                raise FileNotFoundError(f"Entregable DOCX declarado no encontrado: {docx_candidate}")
            docx_report = _audit_docx_deliverable(docx_candidate, self.style_agent, self.workspace.repo_root)
            if delivery_artifact_path is None:
                delivery_artifact_path = docx_candidate

        # 5) Observación contractual de AulaTeX (ActivityObserver)
        obs_res = self.observer.observe(
            ActivityObservationRequest(
                target=str(subject_root),
                activity_number=int(request.activity_number),
                compile_check=False,
            )
        )
        observer_eval = json.loads(obs_res.evaluation_path.read_text(encoding="utf-8"))

        all_styles_ok = all(bool(item["passed"]) for item in style_results)
        all_pdfs_ok = all(rep.passed for rep in pdf_reports)
        docx_ok = True if docx_report is None else bool(docx_report["passed"])

        quality_ok = all_styles_ok and all_pdfs_ok and docx_ok
        if is_live_quiz:
            stage_status = "study_guide_verified_live_quiz_blocked" if quality_ok else "failed_quality_checks"
        else:
            stage_status = "completed_verified" if quality_ok else "failed_quality_checks"

        run_id = f"{self.workspace.timestamp()}-act{int(request.activity_number):02d}-realizar-actividad"
        run_dir = self.runs_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        manifest_payload: dict[str, Any] = {
            "run_id": run_id,
            "validated_at_utc": datetime.now(timezone.utc).isoformat(),
            "agent_id": self.agent_id,
            "subject": subject_root.relative_to(self.workspace.repo_root).as_posix(),
            "activity_number": int(request.activity_number),
            "activity_title": act.get("title"),
            "stage_status": stage_status,
            "quality_ok": quality_ok,
            "live_quiz_blocked": is_live_quiz,
            "blockers": plan_blockers,
            "report_tex": report_tex.relative_to(self.workspace.repo_root).as_posix(),
            "report_pdf": report_pdf.relative_to(self.workspace.repo_root).as_posix(),
            "delivery_artifact": (
                delivery_artifact_path.relative_to(self.workspace.repo_root).as_posix()
                if delivery_artifact_path is not None
                else None
            ),
            "style_collaboration": style_results,
            "pdf_quality_reports": [asdict(r) for r in pdf_reports],
            "docx_quality_report": docx_report,
            "activity_observer": {
                "run_id": obs_res.run_id,
                "evaluation_path": obs_res.evaluation_path.relative_to(self.workspace.repo_root).as_posix(),
                "readiness_score": observer_eval.get("readiness_score"),
                "next_action": observer_eval.get("next_action"),
            },
            "platform_submission_performed": False,
        }
        serialized = json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n"
        assert_no_credential_leak(serialized)
        manifest_path = run_dir / "manifest-realizar-actividad.json"
        manifest_path.write_text(serialized, encoding="utf-8")

        return RealizarActividadResult(
            agent_id=self.agent_id,
            run_id=run_id,
            activity_number=int(request.activity_number),
            subject_root=subject_root,
            ok=quality_ok,
            stage_status=stage_status,
            report_tex_path=report_tex,
            report_pdf_path=report_pdf,
            delivery_artifact_path=delivery_artifact_path,
            style_results=tuple(style_results),
            observer_evaluation=observer_eval,
            pdf_quality_reports=tuple(asdict(r) for r in pdf_reports),
            docx_quality_report=docx_report,
            blockers=tuple(plan_blockers),
            manifest_path=manifest_path,
        )


__all__ = [
    "AGENT_ID_REALIZAR_ACTIVIDAD",
    "PdfQualityReport",
    "RealizarActividadAgent",
    "RealizarActividadRequest",
    "RealizarActividadResult",
]
