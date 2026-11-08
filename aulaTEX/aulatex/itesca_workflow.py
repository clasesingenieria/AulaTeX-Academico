"""Orquestador ``aulatex`` para el flujo académico ITESCA en AulaTeX-Academico.

Coordina bajo ``aulatex`` los agentes especializados y la secuencia obligatoria:
1. Generación/verificación de plantillas y nodos editoriales (``aulatex``).
2. Navegación autenticada de solo lectura en ITESCA Virtual (``navegación-itesca``,
   del tipo ``navegación-plataforma``) sin exponer credenciales en archivos ni bitácoras.
3. ``realizar-planeación`` -> planeación canónica desde evidencia verificada de ITESCA.
4. ``encontrar-recursos`` -> localización, descarga y organización de recursos.
5. ``extraer-conceptos`` -> procesamiento de recursos y generación de conceptos en la
   carpeta de notas correspondiente a cada actividad.
6. ``realizar-actividad`` + ``estilo-escribir`` -> desarrollo con plantillas y ciclos de calidad.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .editorial_memory import EditorialMemoryStore
from .encontrar_recursos import (
    AGENT_ID_ENCONTRAR_RECURSOS,
    EncontrarRecursosAgent,
    EncontrarRecursosRequest,
)
from .estilo_escribir import AGENT_ID_ESTILO_ESCRIBIR, EstiloEscribirAgent
from .extraer_conceptos import (
    AGENT_ID_EXTRAER_CONCEPTOS,
    ExtraerConceptosAgent,
    ExtraerConceptosRequest,
)
from .incremental_detail_planner import DetailPlannerRequest, IncrementalDetailPlanner
from .mcp_lex import McpLexClient, get_lex_client
from .navegacion_itesca import (
    AGENT_ID_NAVEGACION_ITESCA,
    ItescaNavigationRequest,
    NavegacionItescaAgent,
)
from .navegacion_plataforma import AGENT_TYPE_NAVEGACION_PLATAFORMA, assert_no_credential_leak
from .realizar_actividad import (
    AGENT_ID_REALIZAR_ACTIVIDAD,
    RealizarActividadAgent,
    RealizarActividadRequest,
)
from .realizar_planeacion import (
    AGENT_ID_REALIZAR_PLANEACION,
    RealizarPlaneacionAgent,
    RealizarPlaneacionRequest,
)
from .template_materializer import TemplateMaterializer
from .workspace import AulaTeXWorkspace

ORCHESTRATOR_ID_AULATEX = "aulatex"
PIPELINE_STAGE_ORDER: tuple[str, ...] = (
    "planeacion",
    "recopilacion_y_organizacion_de_recursos",
    "extraccion_de_conceptos",
    "realizacion_de_actividades_y_ciclos_de_calidad",
)


@dataclass(frozen=True)
class ItescaActivitySpec:
    subject_target: str
    activity_number: int
    moodle_module_id: int
    moodle_course_id: int
    notes_subdir_hint: str = ""
    prior_feedback_module_ids: tuple[int, ...] = ()
    extra_resource_urls: tuple[str, ...] = ()
    delivery_source_tex: str = ""
    delivery_target_rel: str = ""
    expected_delivery_pages: int | None = None
    expected_arial_pt: float | None = None
    docx_deliverable_rel: str = ""


DEFAULT_ITESCA_ACTIVE_SPECS: tuple[ItescaActivitySpec, ...] = (
    ItescaActivitySpec(
        subject_target="ITESCA/maestria-en-gestion-administrativa/estadistica-aplicada-para-la-administracion-mga",
        activity_number=7,
        moodle_module_id=1761,
        moodle_course_id=209,
        notes_subdir_hint="actividad-07-investigacion-estimacion-intervalos",
        delivery_source_tex="assets-estadistica-aplicada-para-la-administracion/investigacion-estimacion-intervalos/version-entrega.tex",
        delivery_target_rel="entregas-estadistica-aplicada-para-la-administracion/Actividad-7-Investigacion-estimacion-intervalos.pdf",
        expected_delivery_pages=5,
        expected_arial_pt=11.0,
    ),
    ItescaActivitySpec(
        subject_target="ITESCA/maestria-en-gestion-administrativa/estadistica-aplicada-para-la-administracion-mga",
        activity_number=8,
        moodle_module_id=1762,
        moodle_course_id=209,
        notes_subdir_hint="actividad-08-ejercicios-estimacion-intervalos",
        delivery_target_rel="entregas-estadistica-aplicada-para-la-administracion/Actividad-8-Ejercicios-estimacion-intervalos.pdf",
        expected_arial_pt=12.0,
    ),
    ItescaActivitySpec(
        subject_target="ITESCA/maestria-en-gestion-administrativa/estadistica-aplicada-para-la-administracion-mga",
        activity_number=9,
        moodle_module_id=1763,
        moodle_course_id=209,
        notes_subdir_hint="actividad-09-evaluacion-estimacion-intervalos",
    ),
    ItescaActivitySpec(
        subject_target="ITESCA/maestria-en-gestion-administrativa/seminario-i-mga",
        activity_number=15,
        moodle_module_id=2915,
        moodle_course_id=215,
        notes_subdir_hint="actividad-15-metodos-o-procedimientos",
        prior_feedback_module_ids=(2912, 2913, 2914),
        extra_resource_urls=("https://cursos3.e-itesca.edu.mx/mod/resource/view.php?id=2902",),
        docx_deliverable_rel="entregas-seminario-i/Tarea15_DeLaCruzMunoz.docx",
    ),
)


@dataclass(frozen=True)
class ItescaWorkflowRequest:
    specs: tuple[ItescaActivitySpec, ...] = DEFAULT_ITESCA_ACTIVE_SPECS
    snapshot_path: str | Path = ""
    stages: tuple[str, ...] = PIPELINE_STAGE_ORDER
    download_from_platform: bool = True
    extractor_motors: tuple[str, ...] = ("novapro", "tfidf")
    force_reextract_concepts: bool = False
    sync_editorial_nodes: bool = True
    use_llm_style_refinement: bool = False


@dataclass(frozen=True)
class ItescaWorkflowResult:
    orchestrator_id: str
    run_id: str
    run_dir: Path
    manifest_path: Path
    report_path: Path
    ok: bool
    snapshot_path: Path | None
    activities: tuple[dict[str, Any], ...]
    global_blockers: tuple[dict[str, Any], ...] = field(default_factory=tuple)


class AulaTeXItescaOrchestrator:
    """Orquestador ``aulatex`` que gobierna el flujo ITESCA de extremo a extremo."""

    orchestrator_id: str = ORCHESTRATOR_ID_AULATEX

    def __init__(
        self,
        workspace: AulaTeXWorkspace | None = None,
        nav_agent: NavegacionItescaAgent | None = None,
        planner_agent: RealizarPlaneacionAgent | None = None,
        resources_agent: EncontrarRecursosAgent | None = None,
        concepts_agent: ExtraerConceptosAgent | None = None,
        style_agent: EstiloEscribirAgent | None = None,
        activity_agent: RealizarActividadAgent | None = None,
        lex_client: McpLexClient | None = None,
    ) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.lex_client = lex_client or get_lex_client()
        self.editorial_memory = EditorialMemoryStore(self.workspace)
        self.detail_planner = IncrementalDetailPlanner(self.workspace, self.editorial_memory)
        self.template_materializer = TemplateMaterializer(self.workspace)
        self.nav_agent = nav_agent or NavegacionItescaAgent(self.workspace, lex_client=self.lex_client)
        if self.nav_agent.agent_type != AGENT_TYPE_NAVEGACION_PLATAFORMA:
            raise ValueError(
                f"Contrato inválido: {self.nav_agent.agent_id} debe ser de tipo {AGENT_TYPE_NAVEGACION_PLATAFORMA}."
            )
        self.planner_agent = planner_agent or RealizarPlaneacionAgent(self.workspace, lex_client=self.lex_client)
        self.resources_agent = resources_agent or EncontrarRecursosAgent(
            self.workspace,
            nav_agent=self.nav_agent,
            lex_client=self.lex_client,
        )
        self.concepts_agent = concepts_agent or ExtraerConceptosAgent(self.workspace, lex_client=self.lex_client)
        self.style_agent = style_agent or EstiloEscribirAgent(self.workspace, lex_client=self.lex_client)
        self.activity_agent = activity_agent or RealizarActividadAgent(
            self.workspace,
            style_agent=self.style_agent,
            materializer=self.template_materializer,
            lex_client=self.lex_client,
        )
        self.runs_root = self.workspace.feedback_root / "itesca-workflow" / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)

    def _validate_stage_sequence(self, requested_stages: tuple[str, ...]) -> tuple[str, ...]:
        indices = []
        for st in requested_stages:
            if st not in PIPELINE_STAGE_ORDER:
                raise ValueError(f"Etapa desconocida '{st}'. Permitidas: {PIPELINE_STAGE_ORDER}")
            indices.append(PIPELINE_STAGE_ORDER.index(st))
        if indices != sorted(indices):
            raise ValueError(
                f"Orden de etapas inválido {requested_stages}; debe respetar estrictamente {PIPELINE_STAGE_ORDER}."
            )
        return requested_stages

    def _load_or_capture_snapshot(
        self,
        request: ItescaWorkflowRequest,
    ) -> tuple[Path | None, dict[str, Any] | None, list[dict[str, Any]]]:
        blockers: list[dict[str, Any]] = []
        if str(request.snapshot_path).strip():
            snap_file = Path(request.snapshot_path).resolve()
            if not snap_file.is_file():
                blockers.append(
                    {
                        "code": "missing_navigation_snapshot",
                        "agent": AGENT_ID_NAVEGACION_ITESCA,
                        "detail": f"No existe el snapshot indicado: {snap_file}",
                    }
                )
                return None, None, blockers
            raw = snap_file.read_text(encoding="utf-8")
            assert_no_credential_leak(raw)
            return snap_file, json.loads(raw), blockers

        course_ids = tuple(sorted({s.moodle_course_id for s in request.specs}))
        mod_ids: set[int] = set()
        for spec in request.specs:
            mod_ids.add(spec.moodle_module_id)
            mod_ids.update(spec.prior_feedback_module_ids)

        try:
            nav_result = self.nav_agent.inspect(
                ItescaNavigationRequest(
                    course_ids=course_ids,
                    module_ids=tuple(sorted(mod_ids)),
                )
            )
            raw = nav_result.snapshot_path.read_text(encoding="utf-8")
            assert_no_credential_leak(raw)
            return nav_result.snapshot_path, json.loads(raw), blockers
        except Exception as exc:
            blockers.append(
                {
                    "code": "platform_navigation_blocked",
                    "agent": AGENT_ID_NAVEGACION_ITESCA,
                    "detail": f"{type(exc).__name__}: {exc}",
                }
            )
            return None, None, blockers

    def run(self, request: ItescaWorkflowRequest | None = None) -> ItescaWorkflowResult:
        req = request or ItescaWorkflowRequest()
        ordered_stages = self._validate_stage_sequence(req.stages)

        run_id = f"{self.workspace.timestamp()}-itesca-workflow"
        run_dir = self.runs_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        snapshot_path, snapshot_doc, global_blockers = self._load_or_capture_snapshot(req)
        modules_by_id: dict[int, dict[str, Any]] = {}
        if snapshot_doc is not None:
            raw_mods = snapshot_doc.get("modules")
            if isinstance(raw_mods, dict):
                for k, mod in raw_mods.items():
                    try:
                        modules_by_id[int(k)] = mod
                    except ValueError:
                        pass
            elif isinstance(raw_mods, list):
                for mod in raw_mods:
                    if mod.get("module_id") is not None:
                        modules_by_id[int(mod["module_id"])] = mod

        activity_records: list[dict[str, Any]] = []
        overall_ok = len(global_blockers) == 0

        # Sincronización previa de nodos editoriales a nivel materia bajo coordinación de aulatex
        synced_subjects: set[str] = set()

        for spec in req.specs:
            subject_root = self.workspace.resolve_target(spec.subject_target)
            subject_rel = subject_root.relative_to(self.workspace.repo_root).as_posix()

            # 0) Coordinación de plantillas y nodos editoriales por aulatex
            self.template_materializer.materialize_subject(
                subject_root,
                activity_number=spec.activity_number,
                force=False,
            )
            if req.sync_editorial_nodes and subject_rel not in synced_subjects:
                self.detail_planner.run(
                    DetailPlannerRequest(
                        target=str(subject_root),
                        activity_number=spec.activity_number,
                        output=str(run_dir / f"nodos-{subject_root.name}"),
                        max_scopes=6,
                        persist_memory=True,
                    )
                )
                synced_subjects.add(subject_rel)

            rec: dict[str, Any] = {
                "subject": subject_rel,
                "activity_number": spec.activity_number,
                "moodle_module_id": spec.moodle_module_id,
                "stages_executed": {},
                "blockers": [],
                "ok": False,
            }

            if global_blockers:
                rec["blockers"].extend(global_blockers)
                activity_records.append(rec)
                overall_ok = False
                continue

            mod_snap = modules_by_id.get(spec.moodle_module_id)
            if mod_snap is None:
                rec["blockers"].append(
                    {
                        "code": "missing_module_in_snapshot",
                        "agent": AGENT_ID_NAVEGACION_ITESCA,
                        "detail": f"El módulo Moodle {spec.moodle_module_id} no aparece en el snapshot verificado.",
                    }
                )
                activity_records.append(rec)
                overall_ok = False
                continue

            prior_snaps = tuple(
                modules_by_id[mid] for mid in spec.prior_feedback_module_ids if mid in modules_by_id
            )

            plan_json_path: Path | str = ""
            stage_failed = False

            # Etapa 1: realizar-planeación
            if "planeacion" in ordered_stages and not stage_failed:
                try:
                    plan_res = self.planner_agent.run(
                        RealizarPlaneacionRequest(
                            target=str(subject_root),
                            activity_number=spec.activity_number,
                            module_snapshot=mod_snap,
                            related_feedback_snapshots=prior_snaps,
                            notes_subdir_hint=spec.notes_subdir_hint,
                        )
                    )
                    plan_json_path = plan_res.plan_json_path
                    rec["stages_executed"]["planeacion"] = {
                        "agent_id": AGENT_ID_REALIZAR_PLANEACION,
                        "status": "completed",
                        "plan_json": plan_res.plan_json_path.relative_to(self.workspace.repo_root).as_posix(),
                        "plan_md": plan_res.plan_md_path.relative_to(self.workspace.repo_root).as_posix(),
                        "notes_dir": plan_res.notes_dir.relative_to(self.workspace.repo_root).as_posix(),
                        "semantic_ready": bool(plan_res.semantic_validation.get("ready_eligible")),
                    }
                    rec["blockers"].extend(plan_res.blockers)
                except Exception as exc:
                    stage_failed = True
                    overall_ok = False
                    rec["stages_executed"]["planeacion"] = {
                        "agent_id": AGENT_ID_REALIZAR_PLANEACION,
                        "status": "blocked",
                        "error": f"{type(exc).__name__}: {exc}",
                    }

            # Etapa 2: encontrar-recursos
            if "recopilacion_y_organizacion_de_recursos" in ordered_stages and not stage_failed:
                try:
                    res_out = self.resources_agent.run(
                        EncontrarRecursosRequest(
                            target=str(subject_root),
                            activity_number=spec.activity_number,
                            plan_json_path=plan_json_path,
                            extra_platform_urls=spec.extra_resource_urls,
                            download_from_platform=req.download_from_platform,
                        )
                    )
                    rec["stages_executed"]["recopilacion_y_organizacion_de_recursos"] = {
                        "agent_id": AGENT_ID_ENCONTRAR_RECURSOS,
                        "status": "completed",
                        "manifest": res_out.manifest_path.relative_to(self.workspace.repo_root).as_posix(),
                        "downloaded_count": res_out.downloaded_count,
                        "organized_files_count": res_out.organized_files_count,
                        "warnings": list(res_out.missing_or_blocked),
                    }
                except Exception as exc:
                    stage_failed = True
                    overall_ok = False
                    rec["stages_executed"]["recopilacion_y_organizacion_de_recursos"] = {
                        "agent_id": AGENT_ID_ENCONTRAR_RECURSOS,
                        "status": "blocked",
                        "error": f"{type(exc).__name__}: {exc}",
                    }

            # Etapa 3: extraer-conceptos
            if "extraccion_de_conceptos" in ordered_stages and not stage_failed:
                try:
                    conc_out = self.concepts_agent.run(
                        ExtraerConceptosRequest(
                            target=str(subject_root),
                            activity_number=spec.activity_number,
                            plan_json_path=plan_json_path,
                            motors=req.extractor_motors,
                            force_rerun=req.force_reextract_concepts,
                        )
                    )
                    rec["stages_executed"]["extraccion_de_conceptos"] = {
                        "agent_id": AGENT_ID_EXTRAER_CONCEPTOS,
                        "status": "completed",
                        "selected_motor": conc_out.selected_motor,
                        "concepts_count": conc_out.concepts_count,
                        "notes_concepts_dir": conc_out.notes_concepts_dir.relative_to(self.workspace.repo_root).as_posix(),
                        "synced_extractor_dir": conc_out.synced_extractor_dir.relative_to(self.workspace.repo_root).as_posix(),
                    }
                except Exception as exc:
                    stage_failed = True
                    overall_ok = False
                    rec["stages_executed"]["extraccion_de_conceptos"] = {
                        "agent_id": AGENT_ID_EXTRAER_CONCEPTOS,
                        "status": "blocked",
                        "error": f"{type(exc).__name__}: {exc}",
                    }

            # Etapa 4: realizar-actividad + estilo-escribir
            if "realizacion_de_actividades_y_ciclos_de_calidad" in ordered_stages and not stage_failed:
                try:
                    act_out = self.activity_agent.run(
                        RealizarActividadRequest(
                            target=str(subject_root),
                            activity_number=spec.activity_number,
                            plan_json_path=plan_json_path,
                            delivery_source_tex=spec.delivery_source_tex,
                            delivery_target_rel=spec.delivery_target_rel,
                            expected_delivery_pages=spec.expected_delivery_pages,
                            expected_arial_pt=spec.expected_arial_pt,
                            docx_deliverable_rel=spec.docx_deliverable_rel,
                            use_llm_style_refinement=req.use_llm_style_refinement,
                        )
                    )
                    rec["stages_executed"]["realizacion_de_actividades_y_ciclos_de_calidad"] = {
                        "agent_id": AGENT_ID_REALIZAR_ACTIVIDAD,
                        "collaborator": AGENT_ID_ESTILO_ESCRIBIR,
                        "status": act_out.stage_status,
                        "quality_ok": act_out.ok,
                        "report_pdf": (
                            act_out.report_pdf_path.relative_to(self.workspace.repo_root).as_posix()
                            if act_out.report_pdf_path
                            else None
                        ),
                        "delivery_artifact": (
                            act_out.delivery_artifact_path.relative_to(self.workspace.repo_root).as_posix()
                            if act_out.delivery_artifact_path
                            else None
                        ),
                        "manifest": act_out.manifest_path.relative_to(self.workspace.repo_root).as_posix(),
                    }
                    if not act_out.ok:
                        stage_failed = True
                        overall_ok = False
                except Exception as exc:
                    stage_failed = True
                    overall_ok = False
                    rec["stages_executed"]["realizacion_de_actividades_y_ciclos_de_calidad"] = {
                        "agent_id": AGENT_ID_REALIZAR_ACTIVIDAD,
                        "status": "blocked",
                        "error": f"{type(exc).__name__}: {exc}",
                    }

            rec["ok"] = not stage_failed
            activity_records.append(rec)

        manifest_payload: dict[str, Any] = {
            "run_id": run_id,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "orchestrator": self.orchestrator_id,
            "agents_topology": {
                "coordinator": self.orchestrator_id,
                "platform_navigation": {
                    "agent_id": self.nav_agent.agent_id,
                    "agent_type": self.nav_agent.agent_type,
                },
                "planning": AGENT_ID_REALIZAR_PLANEACION,
                "resources": AGENT_ID_ENCONTRAR_RECURSOS,
                "concepts": AGENT_ID_EXTRAER_CONCEPTOS,
                "activity_and_quality": AGENT_ID_REALIZAR_ACTIVIDAD,
                "style_collaborator": AGENT_ID_ESTILO_ESCRIBIR,
            },
            "pipeline_order": list(ordered_stages),
            "snapshot_path": (
                snapshot_path.relative_to(self.workspace.repo_root).as_posix()
                if snapshot_path is not None and snapshot_path.is_relative_to(self.workspace.repo_root)
                else (str(snapshot_path) if snapshot_path else None)
            ),
            "ok": overall_ok,
            "global_blockers": global_blockers,
            "activities": activity_records,
        }
        serialized = json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n"
        assert_no_credential_leak(serialized)
        manifest_path = run_dir / "manifest-itesca-workflow.json"
        manifest_path.write_text(serialized, encoding="utf-8")

        report_md = self._render_markdown_report(manifest_payload)
        assert_no_credential_leak(report_md)
        report_path = run_dir / "reporte-itesca-workflow.md"
        report_path.write_text(report_md, encoding="utf-8")

        return ItescaWorkflowResult(
            orchestrator_id=self.orchestrator_id,
            run_id=run_id,
            run_dir=run_dir,
            manifest_path=manifest_path,
            report_path=report_path,
            ok=overall_ok,
            snapshot_path=snapshot_path,
            activities=tuple(activity_records),
            global_blockers=tuple(global_blockers),
        )

    def _render_markdown_report(self, payload: dict[str, Any]) -> str:
        lines = [
            f"# Flujo Académico ITESCA (`{payload['orchestrator']}`)",
            "",
            f"- **Ejecución**: `{payload['run_id']}`",
            f"- **Fecha UTC**: `{payload['generated_at_utc']}`",
            f"- **Snapshot plataforma (`navegación-itesca`)**: `{payload.get('snapshot_path')}`",
            f"- **Secuencia aplicada**: `{' -> '.join(payload['pipeline_order'])}`",
            f"- **Estado global**: `{'OK' if payload['ok'] else 'CON BLOQUEOS / FALLOS'}`",
            "",
            "## Resumen por actividad",
            "",
        ]
        for act in payload.get("activities") or []:
            lines.append(
                f"### `{act['subject']}` — Actividad {act['activity_number']} (Moodle `{act['moodle_module_id']}`)"
            )
            lines.append(f"- **Estado**: `{'OK' if act['ok'] else 'BLOQUEADO/ERROR'}`")
            for stage_key, stage_data in (act.get("stages_executed") or {}).items():
                lines.append(f"- **{stage_key}** (`{stage_data.get('agent_id')}`): `{stage_data.get('status')}`")
                if stage_data.get("plan_json"):
                    lines.append(f"  - Planeación: `{stage_data['plan_json']}`")
                if stage_data.get("manifest"):
                    lines.append(f"  - Manifiesto: `{stage_data['manifest']}`")
                if stage_data.get("notes_concepts_dir"):
                    lines.append(
                        f"  - Conceptos ({stage_data.get('concepts_count')} fichas, motor `{stage_data.get('selected_motor')}`): "
                        f"`{stage_data['notes_concepts_dir']}`"
                    )
                if stage_data.get("report_pdf"):
                    lines.append(f"  - PDF raíz: `{stage_data['report_pdf']}`")
                if stage_data.get("delivery_artifact"):
                    lines.append(f"  - Entregable verificado: `{stage_data['delivery_artifact']}`")
                if stage_data.get("error"):
                    lines.append(f"  - Detalle de error/bloqueo: `{stage_data['error']}`")
            for blk in act.get("blockers") or []:
                lines.append(f"- **Restricción / bloqueo operativo** (`{blk.get('code')}`): {blk.get('detail')}")
            lines.append("")
        return "\n".join(lines).strip() + "\n"


__all__ = [
    "AulaTeXItescaOrchestrator",
    "DEFAULT_ITESCA_ACTIVE_SPECS",
    "ItescaActivitySpec",
    "ItescaWorkflowRequest",
    "ItescaWorkflowResult",
    "ORCHESTRATOR_ID_AULATEX",
    "PIPELINE_STAGE_ORDER",
]
