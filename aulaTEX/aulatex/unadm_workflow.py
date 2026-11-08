"""Flujo de trabajo académico para UnADM orquestado por el agente ``aulatex``.

Coordina la ejecución en estricta secuencia:
1. ``planeación``: inspección de plataforma mediante ``navegación-itesca`` (UnADM)
   y estructuración con ``realizar-planeación``.
2. ``recopilación y organización de recursos``: localización, descarga y clasificación
   con ``encontrar-recursos``.
3. ``extracción de conceptos``: procesamiento de corpus y generación de fichas trazables
   en notas con ``extraer-conceptos``.
4. ``monitoreo y recomendación de entrega``: consulta técnica a ``monitor-unadm``
   (tipo ``monitor-entregas``) para evaluar requisitos satisfechos y bloqueos.
   El monitor emite recomendación a ``aulatex``; ``aulatex`` evalúa, autoriza y canaliza
   la solicitud hacia ``realizar-actividad``.
5. ``realización de actividades y ciclos de calidad``: autoría con plantilla UnADM,
   refinamiento de voz con ``estilo-escribir``, compilación y auditoría con ``realizar-actividad``.
6. ``localización y propuesta de entrega``: localización del artefacto PDF en la carpeta
   ``entregas-<slug>/`` y presentación estructurada al usuario, quedando en estado
   `pendiente_validacion_usuario`.

Principio rector de soberanía del usuario:
"Autorizar la realización de una actividad no equivale a autorizar su envío."
La entrega formal a la plataforma con ``entregar-unadm`` (tipo ``realizar-entrega``)
solo se ejecuta tras validación explícita del usuario (`user_validated=True`).

Garantiza aislamiento estricto de credenciales (bóveda PlatformCredentialVault sin
exposición en archivos ni registros) y compuertas de parada ante bloqueos reales.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import time
from typing import Any

from .encontrar_recursos import (
    AGENT_ID_ENCONTRAR_RECURSOS,
    EncontrarRecursosAgent,
    EncontrarRecursosRequest,
    EncontrarRecursosResult,
)
from .entregar_unadm import (
    AGENT_ID_ENTREGAR_UNADM,
    EntregarUnadmAgent,
    EntregarUnadmRequest,
)
from .estilo_escribir import AGENT_ID_ESTILO_ESCRIBIR, EstiloEscribirAgent
from .extraer_conceptos import (
    AGENT_ID_EXTRAER_CONCEPTOS,
    ExtraerConceptosAgent,
    ExtraerConceptosRequest,
    ExtraerConceptosResult,
)
from .monitor_entregas import (
    AGENT_TYPE_MONITOR_ENTREGAS,
    DeliveryRecommendation,
    PendingDeliveryItem,
    PendingSubmissionsReport,
)
from .monitor_unadm import (
    AGENT_ID_MONITOR_UNADM,
    MonitorUnadmAgent,
    MonitorUnadmRequest,
)
from .navegacion_plataforma import (
    AGENT_TYPE_NAVEGACION_PLATAFORMA,
    PlatformCredentialBlockedError,
    PlatformNavigationError,
    assert_no_credential_leak,
)
from .navegacion_unadm import (
    AGENT_ID_NAVEGACION_ITESCA,
    COURSES_UNADM,
    NavegacionUnadmAgent,
    UNADM_HOST,
    UnadmModuleTarget,
    UnadmNavigationRequest,
    UnadmNavigationResult,
)
from .planning_layout import subject_layout
from .realizar_actividad import (
    AGENT_ID_REALIZAR_ACTIVIDAD,
    RealizarActividadAgent,
    RealizarActividadRequest,
    RealizarActividadResult,
)
from .realizar_entrega import (
    AGENT_TYPE_REALIZAR_ENTREGA,
    DeliverySubmissionRequest,
    DeliverySubmissionResult,
    DeliveryValidationError,
)
from .realizar_planeacion_unadm import (
    AGENT_ID_REALIZAR_PLANEACION,
    RealizarPlaneacionUnadmAgent,
    RealizarPlaneacionUnadmRequest,
    RealizarPlaneacionUnadmResult,
    UNADM_SUBJECTS_CATALOG,
)
from .workspace import AulaTeXWorkspace

AGENT_ID_ORQUESTADOR_AULATEX = "aulatex"


@dataclass(frozen=True)
class UnadmWorkflowRequest:
    subject_slug: str
    activity_number: int
    course_id: int | None = None
    module_id: int | None = None
    inspect_platform: bool = True
    download_online_resources: bool = True
    compile_pdf: bool = True
    use_llm_style: bool = False
    style_engine: str = "Amazon Nova Pro"
    output_dir: str = ""
    submit_to_platform: bool = False  # Si se solicita explícitamente enviar a plataforma
    user_validated: bool = False      # Validación explícita del usuario (requerida para submit_to_platform)


@dataclass(frozen=True)
class WorkflowStageStatus:
    stage_name: str
    agent_id: str
    ok: bool
    duration_sec: float
    summary: str
    artifacts: tuple[str, ...] = field(default_factory=tuple)
    blockers: tuple[dict[str, Any], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class UnadmWorkflowResult:
    run_id: str
    run_dir: Path
    subject_slug: str
    activity_number: int
    ok: bool
    stages: tuple[WorkflowStageStatus, ...]
    manifest_path: Path
    summary_md_path: Path
    planning_result: RealizarPlaneacionUnadmResult | None = None
    resources_result: EncontrarRecursosResult | None = None
    concepts_result: ExtraerConceptosResult | None = None
    delivery_recommendation: DeliveryRecommendation | None = None
    activity_result: RealizarActividadResult | None = None
    proposed_delivery: dict[str, Any] | None = None
    submission_result: DeliverySubmissionResult | None = None
    blockers: tuple[dict[str, Any], ...] = field(default_factory=tuple)


class UnadmWorkflowOrchestrator:
    """Orquestador ``aulatex`` del flujo académico UnADM."""

    agent_id: str = AGENT_ID_ORQUESTADOR_AULATEX

    def __init__(
        self,
        workspace: AulaTeXWorkspace | None = None,
        nav_agent: NavegacionUnadmAgent | None = None,
        planeacion_agent: RealizarPlaneacionUnadmAgent | None = None,
        recursos_agent: EncontrarRecursosAgent | None = None,
        conceptos_agent: ExtraerConceptosAgent | None = None,
        monitor_agent: MonitorUnadmAgent | None = None,
        actividad_agent: RealizarActividadAgent | None = None,
        entrega_agent: EntregarUnadmAgent | None = None,
    ) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.nav_agent = nav_agent or NavegacionUnadmAgent(self.workspace, agent_id=AGENT_ID_NAVEGACION_ITESCA)
        if self.nav_agent.agent_type != AGENT_TYPE_NAVEGACION_PLATAFORMA:
            raise ValueError(f"Contrato inválido: el agente de navegación debe ser de tipo {AGENT_TYPE_NAVEGACION_PLATAFORMA}.")
        self.planeacion_agent = planeacion_agent or RealizarPlaneacionUnadmAgent(self.workspace)
        self.recursos_agent = recursos_agent or EncontrarRecursosAgent(self.workspace, nav_agent=self.nav_agent)
        self.conceptos_agent = conceptos_agent or ExtraerConceptosAgent(self.workspace)
        self.monitor_agent = monitor_agent or MonitorUnadmAgent(self.workspace, nav_agent=self.nav_agent)
        if self.monitor_agent.agent_type != AGENT_TYPE_MONITOR_ENTREGAS:
            raise ValueError(f"Contrato inválido: el monitor de entregas debe ser de tipo {AGENT_TYPE_MONITOR_ENTREGAS}.")
        self.actividad_agent = actividad_agent or RealizarActividadAgent(self.workspace)
        self.entrega_agent = entrega_agent or EntregarUnadmAgent(self.workspace)
        if self.entrega_agent.agent_type != AGENT_TYPE_REALIZAR_ENTREGA:
            raise ValueError(f"Contrato inválido: el agente de entrega debe ser de tipo {AGENT_TYPE_REALIZAR_ENTREGA}.")
        self.runs_root = self.workspace.feedback_root / "unadm-workflow" / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)

    def _resolve_subject_root(self, subject_slug: str) -> Path:
        base_slug = subject_slug.replace("-lde", "").strip()
        candidates = [
            self.workspace.repo_root / "UnADM" / "licenciatura-en-derecho-unadm" / f"{base_slug}-lde",
            self.workspace.repo_root / "UnADM" / "licenciatura-en-derecho-unadm" / base_slug,
            self.workspace.repo_root / "UnADM" / f"{base_slug}-lde",
            self.workspace.repo_root / "UnADM" / base_slug,
        ]
        for c in candidates:
            if c.is_dir():
                return c
        return candidates[0]

    def run(self, request: UnadmWorkflowRequest) -> UnadmWorkflowResult:
        run_id = f"{self.workspace.timestamp()}-unadm-workflow"
        run_dir = (
            self.workspace.resolve_target(request.output_dir)
            if request.output_dir.strip()
            else self.runs_root / run_id
        )
        run_dir.mkdir(parents=True, exist_ok=True)

        base_slug = request.subject_slug.replace("-lde", "").strip()
        catalog_entry = UNADM_SUBJECTS_CATALOG.get(base_slug, {})
        cid = request.course_id or catalog_entry.get("course_id") or 3482

        stages: list[WorkflowStageStatus] = []
        overall_blockers: list[dict[str, Any]] = []

        # ------------------------------------------------------------------
        # ETAPA 1: Planeación (Navegación UnADM -> realizar-planeación)
        # ------------------------------------------------------------------
        t0 = time.time()
        nav_snapshot: dict[str, Any] | None = None
        module_snapshot: dict[str, Any] | None = None

        if request.inspect_platform:
            try:
                mod_target = None
                if request.module_id:
                    mod_target = UnadmModuleTarget(
                        module_id=request.module_id,
                        course_id=cid,
                        local_activity_number=request.activity_number,
                        subject_slug=base_slug,
                    )
                nav_req = UnadmNavigationRequest(
                    inspect_dashboard=False,
                    course_ids=(cid,),
                    modules=(mod_target,) if mod_target else (),
                    output_dir=str(run_dir / "navegacion"),
                )
                nav_res = self.nav_agent.inspect(nav_req)
                nav_snapshot = nav_res.snapshot
                if request.module_id and str(request.module_id) in nav_snapshot.get("modules", {}):
                    module_snapshot = nav_snapshot["modules"][str(request.module_id)]
                if nav_res.blockers:
                    overall_blockers.extend(nav_res.blockers)
            except PlatformCredentialBlockedError as pbe:
                overall_blockers.append({"stage": "navegacion_unadm", "code": str(pbe), "blocking": True})
            except Exception as exc:
                overall_blockers.append({"stage": "navegacion_unadm", "code": "platform_access_error", "detail": str(exc), "blocking": False})

        # Estructurar la planeación canónica
        try:
            plan_req = RealizarPlaneacionUnadmRequest(
                subject_slug=base_slug,
                activity_number=request.activity_number,
                module_snapshot=module_snapshot,
            )
            plan_res = self.planeacion_agent.plan(plan_req)
            t_plan = time.time() - t0
            stages.append(
                WorkflowStageStatus(
                    stage_name="planeacion",
                    agent_id=AGENT_ID_REALIZAR_PLANEACION,
                    ok=plan_res.semantic_validation.get("passed", True),
                    duration_sec=round(t_plan, 2),
                    summary=f"Planeación canónica PCA v1.0.0 generada en {plan_res.plan_json_path.name}",
                    artifacts=(
                        self.workspace.relative(plan_res.plan_json_path),
                        self.workspace.relative(plan_res.plan_md_path),
                        self.workspace.relative(plan_res.consigna_path),
                    ),
                    blockers=plan_res.blockers,
                )
            )
            if plan_res.blockers:
                overall_blockers.extend(plan_res.blockers)
        except Exception as exc:
            t_plan = time.time() - t0
            stages.append(
                WorkflowStageStatus(
                    stage_name="planeacion",
                    agent_id=AGENT_ID_REALIZAR_PLANEACION,
                    ok=False,
                    duration_sec=round(t_plan, 2),
                    summary=f"Fallo en generación de planeación: {exc}",
                    blockers=({"code": "planeacion_failed", "detail": str(exc)},),
                )
            )
            return self._finalize_run(run_id, run_dir, base_slug, request.activity_number, False, stages, overall_blockers)

        # ------------------------------------------------------------------
        # ETAPA 2: Recopilación y organización de recursos (encontrar-recursos)
        # ------------------------------------------------------------------
        t0 = time.time()
        try:
            rec_req = EncontrarRecursosRequest(
                target=f"UnADM/licenciatura-en-derecho-unadm/{base_slug}-lde",
                activity_number=request.activity_number,
                plan_json_path=plan_res.plan_json_path,
                download_from_platform=request.download_online_resources and bool(nav_snapshot),
            )
            rec_res = self.recursos_agent.run(rec_req)
            t_rec = time.time() - t0
            rec_ok = rec_res.organized_files_count > 0 or rec_res.total_resources > 0
            stages.append(
                WorkflowStageStatus(
                    stage_name="recopilacion_recursos",
                    agent_id=AGENT_ID_ENCONTRAR_RECURSOS,
                    ok=rec_ok,
                    duration_sec=round(t_rec, 2),
                    summary=f"{rec_res.total_resources} recursos organizados ({rec_res.organized_files_count} en corpus)",
                    artifacts=(
                        self.workspace.relative(rec_res.manifest_path),
                        self.workspace.relative(rec_res.corpus_dir),
                        self.workspace.relative(rec_res.material_docente_dir),
                    ),
                    blockers=tuple({"code": m} for m in rec_res.missing_or_blocked),
                )
            )
        except Exception as exc:
            t_rec = time.time() - t0
            stages.append(
                WorkflowStageStatus(
                    stage_name="recopilacion_recursos",
                    agent_id=AGENT_ID_ENCONTRAR_RECURSOS,
                    ok=False,
                    duration_sec=round(t_rec, 2),
                    summary=f"Fallo en recopilación de recursos: {exc}",
                    blockers=({"code": "recursos_failed", "detail": str(exc)},),
                )
            )
            return self._finalize_run(run_id, run_dir, base_slug, request.activity_number, False, stages, overall_blockers, plan_res)

        # ------------------------------------------------------------------
        # ETAPA 3: Extracción de conceptos (extraer-conceptos)
        # ------------------------------------------------------------------
        t0 = time.time()
        try:
            ext_req = ExtraerConceptosRequest(
                target=f"UnADM/licenciatura-en-derecho-unadm/{base_slug}-lde",
                activity_number=request.activity_number,
                plan_json_path=plan_res.plan_json_path,
            )
            ext_res = self.conceptos_agent.run(ext_req)
            t_ext = time.time() - t0
            stages.append(
                WorkflowStageStatus(
                    stage_name="extraccion_conceptos",
                    agent_id=AGENT_ID_EXTRAER_CONCEPTOS,
                    ok=ext_res.ok,
                    duration_sec=round(t_ext, 2),
                    summary=f"{ext_res.concepts_count} conceptos materializados en notas y sincronizados con extractor-aulatex",
                    artifacts=tuple(ext_res.artifacts),
                )
            )
        except Exception as exc:
            t_ext = time.time() - t0
            stages.append(
                WorkflowStageStatus(
                    stage_name="extraccion_conceptos",
                    agent_id=AGENT_ID_EXTRAER_CONCEPTOS,
                    ok=False,
                    duration_sec=round(t_ext, 2),
                    summary=f"Fallo en extracción de conceptos: {exc}",
                    blockers=({"code": "conceptos_failed", "detail": str(exc)},),
                )
            )
            return self._finalize_run(run_id, run_dir, base_slug, request.activity_number, False, stages, overall_blockers, plan_res, rec_res)

        # ------------------------------------------------------------------
        # ETAPA 4: Monitoreo de entregas y recomendación técnica (monitor-unadm)
        # aulatex solicita recomendación; si los prerrequisitos se cumplen, autoriza realizar-actividad
        # ------------------------------------------------------------------
        t0 = time.time()
        delivery_rec: DeliveryRecommendation | None = None
        authorized_by_aulatex = False
        try:
            delivery_rec = self.monitor_agent.evaluate_activity(
                subject_slug=base_slug,
                activity_number=request.activity_number,
                course_id=cid,
                module_id=request.module_id,
                nav_snapshot=nav_snapshot,
                module_snapshot=module_snapshot,
            )
            t_mon = time.time() - t0

            # Evaluar decisión de aulatex en base a la recomendación del monitor
            if delivery_rec.recommended_action == "solicitar-realizar-actividad":
                authorized_by_aulatex = True
                mon_summary = (
                    f"Monitor verificó prerrequisitos ({len(delivery_rec.prerequisites_satisfied)} satisfechos). "
                    f"aulatex autoriza y canaliza la ejecución hacia realizar-actividad."
                )
                mon_ok = True
            elif delivery_rec.recommended_action == "esperar-autorizacion-entrega":
                authorized_by_aulatex = True
                mon_summary = (
                    f"Entregable ya compilado ({Path(delivery_rec.proposed_delivery_artifact or '').name}). "
                    f"aulatex autoriza re-auditoría editorial y preserva propuesta para validación."
                )
                mon_ok = True
            elif delivery_rec.recommended_action == "ya_entregado":
                authorized_by_aulatex = False
                mon_summary = "Actividad ya entregada en UnADM ('Enviado para calificar'). No se requiere nueva confección."
                mon_ok = True
            else:
                authorized_by_aulatex = False
                mon_summary = f"Monitor bloqueado por falta de prerrequisitos: {delivery_rec.rationale}"
                mon_ok = False

            stages.append(
                WorkflowStageStatus(
                    stage_name="monitoreo_entregas",
                    agent_id=AGENT_ID_MONITOR_UNADM,
                    ok=mon_ok,
                    duration_sec=round(t_mon, 2),
                    summary=mon_summary,
                    artifacts=(),
                    blockers=delivery_rec.blockers,
                )
            )
            if delivery_rec.blockers:
                overall_blockers.extend(delivery_rec.blockers)
        except Exception as exc:
            t_mon = time.time() - t0
            stages.append(
                WorkflowStageStatus(
                    stage_name="monitoreo_entregas",
                    agent_id=AGENT_ID_MONITOR_UNADM,
                    ok=False,
                    duration_sec=round(t_mon, 2),
                    summary=f"Fallo en monitoreo de entregas: {exc}",
                    blockers=({"code": "monitor_failed", "detail": str(exc)},),
                )
            )
            return self._finalize_run(run_id, run_dir, base_slug, request.activity_number, False, stages, overall_blockers, plan_res, rec_res, ext_res)

        # ------------------------------------------------------------------
        # ETAPA 5: Realización de actividad y ciclos de calidad (realizar-actividad + estilo-escribir)
        # Solo se ejecuta si aulatex autorizó tras recomendación del monitor
        # ------------------------------------------------------------------
        t0 = time.time()
        act_res: RealizarActividadResult | None = None
        if authorized_by_aulatex:
            try:
                act_req = RealizarActividadRequest(
                    target=f"UnADM/licenciatura-en-derecho-unadm/{base_slug}-lde",
                    activity_number=request.activity_number,
                    plan_json_path=plan_res.plan_json_path,
                    use_llm_style_refinement=request.use_llm_style,
                    style_engine=request.style_engine,
                )
                act_res = self.actividad_agent.run(act_req)
                t_act = time.time() - t0
                stages.append(
                    WorkflowStageStatus(
                        stage_name="realizacion_actividad",
                        agent_id=AGENT_ID_REALIZAR_ACTIVIDAD,
                        ok=act_res.ok,
                        duration_sec=round(t_act, 2),
                        summary=f"Reporte elaborado y auditado (estilo aprobado: {len(act_res.style_results)} verificaciones)",
                        artifacts=(
                            self.workspace.relative(act_res.report_tex_path),
                            self.workspace.relative(act_res.report_pdf_path) if act_res.report_pdf_path else "",
                            self.workspace.relative(act_res.manifest_path),
                        ),
                        blockers=act_res.blockers,
                    )
                )
                if act_res.blockers:
                    overall_blockers.extend(act_res.blockers)
            except Exception as exc:
                t_act = time.time() - t0
                stages.append(
                    WorkflowStageStatus(
                        stage_name="realizacion_actividad",
                        agent_id=AGENT_ID_REALIZAR_ACTIVIDAD,
                        ok=False,
                        duration_sec=round(t_act, 2),
                        summary=f"Fallo en realización de actividad: {exc}",
                        blockers=({"code": "actividad_failed", "detail": str(exc)},),
                    )
                )
                return self._finalize_run(
                    run_id, run_dir, base_slug, request.activity_number, False, stages, overall_blockers,
                    plan_res, rec_res, ext_res, None, delivery_rec
                )
        else:
            stages.append(
                WorkflowStageStatus(
                    stage_name="realizacion_actividad",
                    agent_id=AGENT_ID_REALIZAR_ACTIVIDAD,
                    ok=True,
                    duration_sec=0.0,
                    summary="Omitida por aulatex: la actividad no requería regeneración según el monitor.",
                )
            )

        # ------------------------------------------------------------------
        # ETAPA 6: Localización y retención de entrega propuesta (Soberanía del Usuario)
        # "Autorizar la realización de una actividad no equivale a autorizar su envío."
        # ------------------------------------------------------------------
        t0 = time.time()
        subject_root = self._resolve_subject_root(base_slug)
        layout = subject_layout(subject_root)
        deliveries_dir = layout.get("deliveries")
        deliv_artifact_path: Path | None = None
        deliv_sha256: str = ""

        # Localizar en entregas-<slug>/
        if deliveries_dir and deliveries_dir.is_dir():
            patterns = [
                f"Actividad-S{request.activity_number}-*.pdf",
                f"Actividad-S{request.activity_number}.pdf",
                f"Actividad-{request.activity_number:02d}-*.pdf",
                f"Actividad-{request.activity_number:02d}.pdf",
                f"Actividad-{request.activity_number}-*.pdf",
                f"Actividad-{request.activity_number}.pdf",
            ]
            for pat in patterns:
                matches = sorted(deliveries_dir.glob(pat))
                if matches:
                    deliv_artifact_path = matches[0]
                    break

        # Si aún no estaba en entregas pero el reporte raíz fue generado, promoverlo a entregas
        if deliv_artifact_path is None and act_res is not None and act_res.report_pdf_path and act_res.report_pdf_path.is_file():
            deliveries_dir.mkdir(parents=True, exist_ok=True)
            promoted_name = f"Actividad-S{request.activity_number}-{base_slug}.pdf"
            deliv_artifact_path = deliveries_dir / promoted_name
            shutil.copy2(act_res.report_pdf_path, deliv_artifact_path)

        proposed_delivery_data: dict[str, Any] | None = None
        if deliv_artifact_path and deliv_artifact_path.is_file():
            deliv_sha256 = hashlib.sha256(deliv_artifact_path.read_bytes()).hexdigest()
            proposed_delivery_data = {
                "artifact_path": str(deliv_artifact_path),
                "artifact_rel": self.workspace.relative(deliv_artifact_path),
                "filename": deliv_artifact_path.name,
                "sha256": deliv_sha256,
                "bytes": deliv_artifact_path.stat().st_size,
                "validation_state": "pendiente_validacion_usuario",
                "staged_at_utc": datetime.now(timezone.utc).isoformat(),
                "notice": "Autorizar la realización de una actividad no equivale a autorizar su envío. La entrega está retenida a la espera de validación explícita del usuario.",
            }
            # Guardar en run_dir
            prop_path = run_dir / f"entrega-propuesta-actividad-{request.activity_number}.json"
            prop_path.write_text(json.dumps(proposed_delivery_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        t_stage = time.time() - t0
        stages.append(
            WorkflowStageStatus(
                stage_name="propuesta_entrega",
                agent_id=AGENT_ID_ORQUESTADOR_AULATEX,
                ok=True,
                duration_sec=round(t_stage, 2),
                summary=(
                    f"Artefacto localizado ({deliv_artifact_path.name if deliv_artifact_path else 'ninguno'}). "
                    f"Retenido como PENDIENTE DE VALIDACIÓN EXPLÍCITA DEL USUARIO."
                ),
                artifacts=(str(deliv_artifact_path),) if deliv_artifact_path else (),
            )
        )

        # ------------------------------------------------------------------
        # ETAPA OPCIONAL: Enviar a plataforma si se solicitó explícitamente
        # "Solo podrá enviar la entrega después de recibir validación explícita del usuario"
        # ------------------------------------------------------------------
        submission_res: DeliverySubmissionResult | None = None
        if request.submit_to_platform:
            t0 = time.time()
            sub_req = EntregarUnadmRequest(
                subject_slug=base_slug,
                activity_number=request.activity_number,
                artifact_path=deliv_artifact_path or "",
                expected_sha256=deliv_sha256,
                course_id=cid,
                module_id=request.module_id,
                user_validated=request.user_validated,
                dry_run=True,  # Default seguro en flujo
                output_dir=str(run_dir / "entrega"),
            )
            submission_res = self.entrega_agent.submit(sub_req)
            t_sub = time.time() - t0
            stages.append(
                WorkflowStageStatus(
                    stage_name="envio_plataforma",
                    agent_id=AGENT_ID_ENTREGAR_UNADM,
                    ok=submission_res.ok,
                    duration_sec=round(t_sub, 2),
                    summary=f"Estado de envío: {submission_res.status}",
                    artifacts=(str(submission_res.receipt_path),) if submission_res.receipt_path else (),
                    blockers=submission_res.blockers,
                )
            )
            if submission_res.blockers:
                overall_blockers.extend(submission_res.blockers)

        all_ok = all(s.ok for s in stages) and not any(b.get("blocking", False) for b in overall_blockers)
        return self._finalize_run(
            run_id, run_dir, base_slug, request.activity_number, all_ok, stages, overall_blockers,
            plan_res, rec_res, ext_res, act_res, delivery_rec, proposed_delivery_data, submission_res
        )

    def _finalize_run(
        self,
        run_id: str,
        run_dir: Path,
        subject_slug: str,
        activity_number: int,
        ok: bool,
        stages: list[WorkflowStageStatus],
        blockers: list[dict[str, Any]],
        plan_res: RealizarPlaneacionUnadmResult | None = None,
        rec_res: EncontrarRecursosResult | None = None,
        ext_res: ExtraerConceptosResult | None = None,
        act_res: RealizarActividadResult | None = None,
        delivery_rec: DeliveryRecommendation | None = None,
        proposed_delivery: dict[str, Any] | None = None,
        submission_res: DeliverySubmissionResult | None = None,
    ) -> UnadmWorkflowResult:
        manifest: dict[str, Any] = {
            "schema_version": "1.0.0",
            "run_id": run_id,
            "orchestrator_agent": self.agent_id,
            "orchestrator_agent_id": self.agent_id,
            "institution": "UnADM",
            "subject_slug": subject_slug,
            "activity_number": activity_number,
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "ok": ok,
            "stages": [
                {
                    "stage": s.stage_name,
                    "agent_id": s.agent_id,
                    "ok": s.ok,
                    "duration_sec": s.duration_sec,
                    "summary": s.summary,
                    "artifacts": list(s.artifacts),
                    "blockers": list(s.blockers),
                }
                for s in stages
            ],
            "delivery_recommendation": asdict(delivery_rec) if delivery_rec else None,
            "proposed_delivery": proposed_delivery,
            "submission_status": submission_res.status if submission_res else "not_requested",
            "blockers": blockers,
        }
        assert_no_credential_leak(manifest)
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        # Generar resumen legible Markdown
        summary_lines = [
            f"# Resumen de Ejecución: Flujo Académico UnADM (Actividad {activity_number})",
            "",
            f"- **Orquestador:** `{self.agent_id}`",
            f"- **Asignatura:** `{subject_slug}`",
            f"- **Actividad:** {activity_number}",
            f"- **Estado global:** `{'EXITOSO' if ok else 'BLOQUEADO / REQUIERE ATENCIÓN'}`",
            f"- **Fecha:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "## Secuencia de Agentes Ejecutada",
            "",
            "| Etapa | Agente | Estado | Duración | Resumen |",
            "|---|---|---|---|---|",
        ]
        for s in stages:
            status_badge = "OK" if s.ok else "FALLÓ"
            summary_lines.append(f"| {s.stage_name} | `{s.agent_id}` | {status_badge} | {s.duration_sec}s | {s.summary} |")

        if proposed_delivery:
            summary_lines.extend([
                "",
                "## Entrega Propuesta y Soberanía del Usuario",
                "",
                "> [!IMPORTANT]",
                "> **Autorizar la realización de una actividad no equivale a autorizar su envío.**",
                f"> - **Artefacto propuesto:** `{proposed_delivery.get('filename')}`",
                f"> - **Ubicación:** `{proposed_delivery.get('artifact_path')}`",
                f"> - **SHA-256:** `{proposed_delivery.get('sha256')}`",
                f"> - **Tamaño:** {proposed_delivery.get('bytes', 0):,} bytes",
                f"> - **Estado de validación:** `{proposed_delivery.get('validation_state')}`",
                "> ",
                "> El documento fue compilado y auditado con éxito, pero **NO HA SIDO ENVIADO** a la plataforma UnADM.",
                "> El agente `entregar-unadm` requiere validación explícita del usuario (`user_validated=True`) antes de cualquier mutación.",
            ])

        if blockers:
            summary_lines.extend(["", "## Bloqueos y Observaciones", ""])
            for b in blockers:
                summary_lines.append(f"- **[{b.get('stage', 'sistema')}]:** `{b.get('code')}` - {b.get('detail', '')}")

        summary_lines.extend(["", "## Artefactos Clave Generados", ""])
        for s in stages:
            for art in s.artifacts:
                if art:
                    summary_lines.append(f"- `{art}`")

        summary_md = "\n".join(summary_lines) + "\n"
        assert_no_credential_leak(summary_md)
        summary_md_path = run_dir / "resumen-ejecucion.md"
        summary_md_path.write_text(summary_md, encoding="utf-8")

        self.workspace.append_bitacora(run_id, "unadm-workflow", manifest)

        return UnadmWorkflowResult(
            run_id=run_id,
            run_dir=run_dir,
            subject_slug=subject_slug,
            activity_number=activity_number,
            ok=ok,
            stages=tuple(stages),
            manifest_path=manifest_path,
            summary_md_path=summary_md_path,
            planning_result=plan_res,
            resources_result=rec_res,
            concepts_result=ext_res,
            activity_result=act_res,
            delivery_recommendation=delivery_rec,
            proposed_delivery=proposed_delivery,
            submission_result=submission_res,
            blockers=tuple(blockers),
        )

    def run_pending_deliveries(
        self,
        subject_slug: str,
        course_id: int | None = None,
        inspect_platform: bool = False,
        download_online_resources: bool = False,
        compile_pdf: bool = True,
        use_llm_style: bool = False,
        output_dir: str = "",
    ) -> dict[str, Any]:
        """
        Ejecuta monitor-unadm para auditar el estado de entregas de la materia,
        e invoca secuencialmente realizar-actividad (con estilo-escribir y auditorías)
        para aquellas actividades donde el monitor recomiende 'solicitar-realizar-actividad'.

        Las entregas generadas quedan retenidas en estado 'pendiente_validacion_usuario'.
        """
        base_slug = subject_slug.replace("-lde", "").strip()

        # Soporte multi-materia cuando se solicita 'all', 'todas' o lista separada por comas
        if base_slug.lower() in ("all", "todas", "*", "multi") or "," in base_slug:
            subjects = (
                [s.strip() for s in base_slug.split(",") if s.strip()]
                if "," in base_slug
                else list(UNADM_SUBJECTS_CATALOG.keys())
            )
            multi_results: dict[str, Any] = {}
            multi_ok = True
            for subj in subjects:
                res = self.run_pending_deliveries(
                    subject_slug=subj,
                    inspect_platform=inspect_platform,
                    download_online_resources=download_online_resources,
                    compile_pdf=compile_pdf,
                    use_llm_style=use_llm_style,
                )
                multi_results[subj] = res
                if not res.get("ok", True):
                    multi_ok = False
            return {
                "ok": multi_ok,
                "multi_subject": True,
                "subjects": subjects,
                "results": multi_results,
            }

        catalog_entry = UNADM_SUBJECTS_CATALOG.get(base_slug, {})
        cid = course_id or catalog_entry.get("course_id") or 3482

        run_id = f"{self.workspace.timestamp()}-unadm-pending-batch"
        batch_dir = (
            self.workspace.resolve_target(output_dir)
            if output_dir.strip()
            else self.runs_root / run_id
        )
        batch_dir.mkdir(parents=True, exist_ok=True)

        # 1. Ejecutar monitor-unadm
        mon_req = MonitorUnadmRequest(
            subject_slug=base_slug,
            course_id=cid,
            inspect_platform=inspect_platform,
            output_dir=str(batch_dir / "monitor"),
        )
        mon_report = self.monitor_agent.monitor_deliveries(mon_req)

        # 2. Identificar entregas pendientes que requieren realización
        # Incluye tanto las que tienen prerrequisitos listos como las que requieren
        # completar la secuencia canónica (planeación -> recursos -> conceptos -> actividad)
        pending_activities: list[int] = [
            r.activity_number
            for r in mon_report.recommendations
            if r.recommended_action == "solicitar-realizar-actividad"
            or (
                r.recommended_action == "bloqueado_falta_prerrequisitos"
                and any(
                    b.get("code") in ("falta_planeacion", "falta_recursos", "falta_conceptos")
                    for b in r.blockers
                )
            )
        ]

        already_ready: list[dict[str, Any]] = [
            {
                "activity": r.activity_number,
                "action": r.recommended_action,
                "artifact": r.proposed_delivery_artifact,
                "sha256": r.proposed_delivery_sha256,
            }
            for r in mon_report.recommendations
            if r.recommended_action in ("esperar-autorizacion-entrega", "ya_entregado")
        ]

        executed_activities: list[dict[str, Any]] = []
        overall_ok = True

        # 3. Para cada actividad pendiente, autorizar y ejecutar realizar-actividad dentro del flujo
        for act_num in pending_activities:
            act_req = UnadmWorkflowRequest(
                subject_slug=base_slug,
                activity_number=act_num,
                course_id=cid,
                inspect_platform=inspect_platform,
                download_online_resources=download_online_resources,
                compile_pdf=compile_pdf,
                use_llm_style=use_llm_style,
                output_dir=str(batch_dir / f"actividad-{act_num:02d}"),
                submit_to_platform=False,  # NO enviar sin validación explícita
                user_validated=False,
            )
            act_res = self.run(act_req)
            if not act_res.ok:
                overall_ok = False

            executed_activities.append({
                "activity": act_num,
                "ok": act_res.ok,
                "proposed_delivery": act_res.proposed_delivery,
                "manifest": self.workspace.relative(act_res.manifest_path),
                "summary_md": self.workspace.relative(act_res.summary_md_path),
                "blockers": list(act_res.blockers),
            })

        # 4. Generar reporte consolidado
        manifest_batch: dict[str, Any] = {
            "schema_version": "1.0.0",
            "run_id": run_id,
            "orchestrator_agent": self.agent_id,
            "institution": "UnADM",
            "subject_slug": base_slug,
            "course_id": cid,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "ok": overall_ok,
            "total_monitored": len(mon_report.recommendations),
            "pending_activities_detected": pending_activities,
            "already_ready_or_submitted": already_ready,
            "executed_activities": executed_activities,
            "notice": "Autorizar la realización de una actividad no equivale a autorizar su envío. Todas las entregas preparadas quedan retenidas en estado 'pendiente_validacion_usuario'.",
        }
        assert_no_credential_leak(manifest_batch)
        manifest_path = batch_dir / "manifest-batch-pendientes.json"
        manifest_path.write_text(json.dumps(manifest_batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        summary_lines = [
            f"# Resumen de Ejecución: Monitor UnADM y Realización de Entregas Pendientes",
            "",
            f"- **Orquestador:** `{self.agent_id}`",
            f"- **Institución:** UnADM",
            f"- **Asignatura:** `{base_slug}` (Curso {cid})",
            f"- **Fecha:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"- **Estado global:** `{'EXITOSO' if overall_ok else 'REQUIERE ATENCIÓN'}`",
            "",
            "## 1. Diagnóstico de Monitoreo (`monitor-unadm`)",
            "",
            f"- **Actividades evaluadas:** {len(mon_report.recommendations)}",
            f"- **Actividades pendientes de realizar:** {pending_activities if pending_activities else 'Ninguna'}",
            f"- **Actividades ya compiladas o entregadas:** {len(already_ready)}",
            "",
            "| Actividad | Recomendación Monitor | Prerrequisitos Satisfechos | Artefacto Local |",
            "|---|---|---|---|",
        ]
        for r in mon_report.recommendations:
            art_name = Path(r.proposed_delivery_artifact).name if r.proposed_delivery_artifact else "Pendiente"
            prereqs = ", ".join(r.prerequisites_satisfied) if r.prerequisites_satisfied else "Ninguno"
            summary_lines.append(f"| Actividad {r.activity_number} | **{r.recommended_action}** | {prereqs} | `{art_name}` |")

        summary_lines.extend(["", "## 2. Actividades Realizadas y Retenidas (`realizar-actividad`)", ""])
        if executed_activities:
            for ex in executed_activities:
                status_badge = "EXITOSO" if ex["ok"] else "FALLÓ"
                summary_lines.append(f"### Actividad {ex['activity']}: `{status_badge}`")
                prop = ex.get("proposed_delivery") or {}
                if prop:
                    summary_lines.append(f"- **Artefacto:** `{prop.get('filename')}`")
                    summary_lines.append(f"- **Ruta:** `{prop.get('artifact_path')}`")
                    summary_lines.append(f"- **SHA-256:** `{prop.get('sha256')}`")
                    summary_lines.append(f"- **Estado de entrega:** `{prop.get('validation_state')}`")
                summary_lines.append(f"- **Manifiesto:** `{ex['manifest']}`")
                summary_lines.append("")
        else:
            summary_lines.append("No se requirió realizar ninguna actividad: todas las actividades estaban ya compiladas o entregadas.")

        summary_lines.extend([
            "",
            "## 3. Principio de Seguridad y Soberanía",
            "",
            "> [!IMPORTANT]",
            "> **Autorizar la realización de una actividad no equivale a autorizar su envío.**",
            "> Las actividades han sido desarrolladas, auditadas con estilo-escribir y compiladas, pero **NO HAN SIDO ENVIADAS** a UnADM.",
            "> El agente `entregar-unadm` permanece a la espera de la validación explícita del usuario (`user_validated=True`).",
        ])

        summary_md = "\n".join(summary_lines) + "\n"
        assert_no_credential_leak(summary_md)
        summary_md_path = batch_dir / "resumen-batch-pendientes.md"
        summary_md_path.write_text(summary_md, encoding="utf-8")

        return {
            "ok": overall_ok,
            "run_id": run_id,
            "subject": base_slug,
            "course_id": cid,
            "total_monitored": len(mon_report.recommendations),
            "pending_activities_detected": pending_activities,
            "executed_count": len(executed_activities),
            "executed_activities": executed_activities,
            "already_ready_count": len(already_ready),
            "manifest": self.workspace.relative(manifest_path),
            "summary_md": self.workspace.relative(summary_md_path),
        }


__all__ = [
    "AGENT_ID_ORQUESTADOR_AULATEX",
    "UnadmWorkflowOrchestrator",
    "UnadmWorkflowRequest",
    "UnadmWorkflowResult",
    "WorkflowStageStatus",
]
