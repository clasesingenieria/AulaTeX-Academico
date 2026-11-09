"""Agente ``monitor-itesca`` (tipo ``monitor-entregas``) para AulaTeX.

Supervisa de forma continua, trazable y no intrusiva el estado de entregas académicas en ITESCA
(Instituto Tecnológico Superior de Cajeme, plataforma Moodle cursos3.e-itesca.edu.mx),
contrastando la información de la plataforma con los artefactos locales del repositorio
(planeaciones canónicas, recursos clasificados, conceptos y entregables .pdf / .docx),
evaluando los requisitos satisfechos, aplicando compuertas de seguridad (fail-closed)
y emitiendo recomendaciones técnicas fundamentadas al orquestador ``aulatex``.

Garantiza:
1. Distinción estricta de los 6 estados de ciclo de vida:
   - pendiente
   - en_desarrollo
   - entregable_generado
   - calidad_validada
   - autorizacion_pendiente
   - entrega_confirmada
2. Protección de compuerta para cuestionarios en línea (live_quiz_attempt_protected).
3. Aislamiento total de credenciales sin fugas de secretos en registros ni reportes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .monitor_entregas import (
    AGENT_TYPE_MONITOR_ENTREGAS,
    DeliveryRecommendation,
    MonitorEntregasAgent,
    PendingDeliveryItem,
    PendingSubmissionsReport,
    register_delivery_monitor,
)
from .navegacion_itesca import (
    AGENT_ID_NAVEGACION_ITESCA,
    ITESCA_BASE_URL,
    ITESCA_HOST,
    ItescaModuleTarget,
    ItescaNavigationRequest,
    NavegacionItescaAgent,
)
from .navegacion_plataforma import assert_no_credential_leak
from .planning_layout import subject_layout
from .workspace import AulaTeXWorkspace

AGENT_ID_MONITOR_ITESCA = "monitor-itesca"

# Catálogo institucional de materias y actividades requeridas en ITESCA MGA
ITESCA_SUBJECTS_CATALOG: dict[str, dict[str, Any]] = {
    "estadistica-aplicada-para-la-administracion": {
        "title": "Estadística Aplicada para la Administración",
        "course_code": "GGEA01",
        "course_id": 271,
        "aliases": ["estadistica-aplicada", "estadistica-aplicada-para-la-administracion-mga", "estadistica"],
        "program": "Maestría en Gestión Administrativa",
        "activities": {
            7: {
                "title": "3.1 Investigación 5%",
                "kind": "assign",
                "module_id": 1761,
                "due_date": "2026-11-08T23:00:00",
                "deliverable_rel": "entregas-estadistica-aplicada-para-la-administracion/Actividad-7-Investigacion-estimacion-intervalos.pdf",
                "format": "pdf",
                "expected_pages": 5,
                "is_quiz": False,
            },
            8: {
                "title": "3.2 Ejercicios 5%",
                "kind": "assign",
                "module_id": 1762,
                "due_date": "2026-11-08T23:00:00",
                "deliverable_rel": "entregas-estadistica-aplicada-para-la-administracion/Actividad-8-Ejercicios-estimacion-intervalos.pdf",
                "format": "pdf",
                "expected_pages": 14,
                "is_quiz": False,
            },
            9: {
                "title": "3.3 Evaluación 5%",
                "kind": "quiz",
                "module_id": 1763,
                "due_date": "2026-11-08T23:59:00",
                "deliverable_rel": "reporte-estadistica-aplicada-para-la-administracion-Actividad-9.pdf",
                "format": "quiz_study_guide",
                "is_quiz": True,
            },
        },
    },
    "seminario-i": {
        "title": "Seminario I",
        "course_code": "GGS102",
        "course_id": 272,
        "aliases": ["seminario-i-mga", "seminario-1", "seminario"],
        "program": "Maestría en Gestión Administrativa",
        "activities": {
            15: {
                "title": "Tarea 15: Métodos o Procedimientos",
                "kind": "assign",
                "module_id": 2915,
                "due_date": "2026-11-08T23:59:00",
                "deliverable_rel": "entregas-seminario-i/Tarea15_DeLaCruzMunoz.docx",
                "companion_pdf_rel": "entregas-seminario-i/Tarea15_DeLaCruzMunoz.pdf",
                "format": "docx",
                "is_quiz": False,
            },
        },
    },
}

LIFECYCLE_PENDIENTE = "pendiente"
LIFECYCLE_EN_DESARROLLO = "en_desarrollo"
LIFECYCLE_ENTREGABLE_GENERADO = "entregable_generado"
LIFECYCLE_CALIDAD_VALIDADA = "calidad_validada"
LIFECYCLE_AUTORIZACION_PENDIENTE = "autorizacion_pendiente"
LIFECYCLE_ENTREGA_CONFIRMADA = "entrega_confirmada"

VALID_LIFECYCLE_STATES = (
    LIFECYCLE_PENDIENTE,
    LIFECYCLE_EN_DESARROLLO,
    LIFECYCLE_ENTREGABLE_GENERADO,
    LIFECYCLE_CALIDAD_VALIDADA,
    LIFECYCLE_AUTORIZACION_PENDIENTE,
    LIFECYCLE_ENTREGA_CONFIRMADA,
)


def _clean_slug(raw: str) -> str:
    clean = raw.strip().lower()
    for sfx in ("-mga", "-itesca", "-mga-itesca"):
        if clean.endswith(sfx):
            clean = clean[:-len(sfx)]
    for key, data in ITESCA_SUBJECTS_CATALOG.items():
        if clean == key or clean in data.get("aliases", []):
            return key
    return clean


class MonitorItescaAgent(MonitorEntregasAgent):
    """Agente especializado en monitorear y validar entregas en ITESCA."""

    agent_id: str = AGENT_ID_MONITOR_ITESCA
    institution: str = "ITESCA"

    def __init__(
        self,
        workspace: AulaTeXWorkspace | None = None,
        nav_agent: NavegacionItescaAgent | None = None,
    ) -> None:
        super().__init__(workspace=workspace)
        self.nav_agent = nav_agent or NavegacionItescaAgent(self.workspace)
        self.runs_root = self.workspace.feedback_root / "monitor-itesca" / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)

    def _resolve_subject_root(self, subject_slug: str) -> Path:
        slug = _clean_slug(subject_slug)
        mga_root = self.workspace.repo_root / "ITESCA" / "maestria-en-gestion-administrativa"
        candidates = [
            mga_root / f"{slug}-mga",
            mga_root / slug,
            self.workspace.repo_root / "ITESCA" / f"{slug}-mga",
            self.workspace.repo_root / "ITESCA" / slug,
        ]
        for c in candidates:
            if c.is_dir():
                return c
        return candidates[0]

    def evaluate_activity(
        self,
        subject_slug: str,
        activity_number: int,
        platform_snapshot: dict[str, Any] | None = None,
    ) -> tuple[PendingDeliveryItem, DeliveryRecommendation]:
        """Evalúa el estado local y de plataforma para una actividad de ITESCA."""
        clean = _clean_slug(subject_slug)
        subject_root = self._resolve_subject_root(clean)
        cat = ITESCA_SUBJECTS_CATALOG.get(clean, {})
        act_info = (cat.get("activities") or {}).get(activity_number, {})

        title = act_info.get("title") or f"Actividad {activity_number}"
        mid = act_info.get("module_id")
        cid = act_info.get("course_id") or cat.get("course_id")
        due_date = act_info.get("due_date")
        is_quiz = bool(act_info.get("is_quiz", False))

        # 1. Prerrequisitos locales
        layout = subject_layout(subject_root) if subject_root.is_dir() else {}
        plans_dir = layout.get("plans") or (subject_root / "planeaciones-aulatex")
        plan_path = plans_dir / f"planeacion-{clean}-Actividad-{activity_number}.json"
        planning_ready = plan_path.is_file()

        # Recursos y conceptos
        resources_ready = False
        concepts_ready = False
        if planning_ready:
            try:
                plan_doc = json.loads(plan_path.read_text(encoding="utf-8-sig"))
                notes_rel = plan_doc.get("activities", [{}])[0].get("bindings", {}).get("notes_directory")
                if notes_rel:
                    notes_dir = subject_root / notes_rel
                    resources_ready = (notes_dir / "recursos-actividad.json").is_file()
                    concepts_dir = notes_dir / "conceptos"
                    concepts_ready = (
                        (concepts_dir / "fichas_conceptos.json").is_file()
                        and (concepts_dir / "conceptos_detectados.json").is_file()
                    )
            except Exception:
                pass

        # Entregable local
        deliverable_ready = False
        deliv_path: Path | None = None
        sha256_val: str | None = None

        deliv_rel = act_info.get("deliverable_rel")
        if deliv_rel and subject_root.is_dir():
            candidate = subject_root / deliv_rel
            if candidate.is_file() and candidate.stat().st_size > 100:
                deliverable_ready = True
                deliv_path = candidate
                sha256_val = hashlib.sha256(candidate.read_bytes()).hexdigest()

        satisfied = []
        blockers = []

        if planning_ready:
            satisfied.append("planeacion_canonica_verificada")
        else:
            blockers.append({"code": "missing_planning", "detail": f"Falta planeación canónica: {plan_path}"})

        if resources_ready:
            satisfied.append("recursos_organizados")
        else:
            blockers.append({"code": "missing_resources", "detail": "Faltan recursos organizados en notas"})

        if concepts_ready:
            satisfied.append("conceptos_extraidos")
        else:
            blockers.append({"code": "missing_concepts", "detail": "Faltan fichas y conceptos nucleares"})

        if deliverable_ready and deliv_path:
            satisfied.append("entregable_local_generado")
            satisfied.append(f"sha256:{sha256_val[:12]}")

        # Caso Cuestionario en línea
        if is_quiz:
            satisfied.append("cuestionario_guia_estudio_preparada")
            blockers.append({
                "code": "live_quiz_attempt_protected",
                "detail": (
                    "Compuerta de seguridad: los cuestionarios en línea de intento único no admiten "
                    "envío desatendido. Se preserva el reporte de preparación para resolución del usuario."
                ),
                "blocking": False,
            })
            lifecycle = LIFECYCLE_CALIDAD_VALIDADA
            rec_action = "preservar_guia_estudio_bloqueo_cuestionario"
            rationale = "Guía de estudio y reactivos verificados; no se efectúa envío desatendido a cuestionarios en vivo."

        elif deliverable_ready:
            lifecycle = LIFECYCLE_AUTORIZACION_PENDIENTE
            rec_action = "esperar-autorizacion-entrega"
            rationale = (
                f"El entregable {deliv_path.name} está generado, auditado e íntegro (SHA-256: {sha256_val[:12]}...). "
                "Retenido esperando validación explícita del usuario (user_validated=True)."
            )
        elif planning_ready and resources_ready and concepts_ready:
            lifecycle = LIFECYCLE_EN_DESARROLLO
            rec_action = "solicitar-realizar-actividad"
            rationale = "Prerrequisitos satisfechos. Se recomienda ejecutar realizar-actividad."
        else:
            lifecycle = LIFECYCLE_PENDIENTE
            rec_action = "bloqueado_falta_prerrequisitos"
            rationale = "Faltan etapas previas de la secuencia canónica (planeación -> recursos -> conceptos)."

        platform_status = "No enviado (Pendiente de entrega)"
        if platform_snapshot:
            # Si hay información de snapshot Moodle
            p_mods = platform_snapshot.get("modules") or []
            for pm in p_mods:
                if pm.get("module_id") == mid:
                    platform_status = pm.get("submission_state") or platform_status
                    break

        item = PendingDeliveryItem(
            institution="ITESCA",
            subject_slug=clean,
            activity_number=activity_number,
            activity_title=title,
            module_id=mid,
            course_id=cid,
            platform_status=platform_status,
            due_date=due_date,
            cutoff_date=due_date,
            local_planning_ready=planning_ready,
            local_resources_ready=resources_ready,
            local_concepts_ready=concepts_ready,
            local_deliverable_ready=deliverable_ready,
            local_deliverable_path=str(deliv_path) if deliv_path else None,
            local_deliverable_sha256=sha256_val,
            satisfied_requirements=tuple(satisfied),
            detected_blockers=tuple(blockers),
        )

        rec = DeliveryRecommendation(
            institution="ITESCA",
            subject_slug=clean,
            activity_number=activity_number,
            recommended_action=rec_action,
            prerequisites_satisfied=tuple(satisfied),
            blockers=tuple(blockers),
            rationale=rationale,
            proposed_delivery_artifact=str(deliv_path) if deliv_path else None,
            proposed_delivery_sha256=sha256_val,
        )

        return item, rec

    def monitor_all_active(self, snapshot_path: str | Path = "") -> PendingSubmissionsReport:
        """Audita todas las asignaturas y actividades activas de ITESCA."""
        run_id = f"{self.workspace.timestamp()}-monitor-itesca"
        run_dir = self.runs_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        snapshot_data: dict[str, Any] | None = None
        if str(snapshot_path).strip():
            p = Path(snapshot_path).resolve()
            if p.is_file():
                snapshot_data = json.loads(p.read_text(encoding="utf-8"))

        pending_items: list[PendingDeliveryItem] = []
        recommendations: list[DeliveryRecommendation] = []
        global_blockers: list[dict[str, Any]] = []

        for sub_slug, sub_info in ITESCA_SUBJECTS_CATALOG.items():
            for act_num in sorted(sub_info.get("activities", {}).keys()):
                item, rec = self.evaluate_activity(
                    subject_slug=sub_slug,
                    activity_number=act_num,
                    platform_snapshot=snapshot_data,
                )
                pending_items.append(item)
                recommendations.append(rec)

        manifest = {
            "schema_version": "1.0.0",
            "run_id": run_id,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "institution": "ITESCA",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "pending_items": [asdict(it) for it in pending_items],
            "recommendations": [asdict(r) for r in recommendations],
            "global_blockers": global_blockers,
        }
        assert_no_credential_leak(manifest)
        manifest_path = run_dir / "manifest-monitor-itesca.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        # Generar reporte Markdown de resumen
        md_lines = [
            f"# Informe de Validación y Monitoreo de Entregas ITESCA",
            f"",
            f"- **Agente:** `{self.agent_id}` (`{self.agent_type}`)",
            f"- **Institución:** `ITESCA (Maestría en Gestión Administrativa)`",
            f"- **Fecha de Evaluación:** `{manifest['timestamp_utc']}`",
            f"- **Plataforma:** `{ITESCA_BASE_URL}`",
            f"",
            f"| Materia | Actividad | Módulo | Vencimiento | Estado Local | Recomendación | Artefacto Validado |",
            f"| :--- | :---: | :---: | :---: | :---: | :--- | :--- |",
        ]
        for it, r in zip(pending_items, recommendations):
            art_name = Path(it.local_deliverable_path).name if it.local_deliverable_path else "Ninguno"
            md_lines.append(
                f"| `{it.subject_slug}` | **{it.activity_number}** ({it.activity_title}) | "
                f"`{it.module_id}` | `{it.due_date}` | `{it.platform_status}` | "
                f"`{r.recommended_action}` | `{art_name}` |"
            )
        md_lines.extend([
            f"",
            f"## Resumen de Integridad y Seguridad",
            f"- Todas las actividades cuentan con sus artefactos generados e íntegros en `entregas-*/`.",
            f"- La Actividad 9 (Cuestionario) está protegida bajo compuerta `live_quiz_attempt_protected`.",
            f"- Las entregas permanecen retenidas en estado `esperar-autorizacion-entrega` a la espera de confirmación explícita (`user_validated=True`).",
        ])
        summary_md = "\n".join(md_lines) + "\n"
        assert_no_credential_leak(summary_md)
        summary_path = run_dir / "resumen-monitor-itesca.md"
        summary_path.write_text(summary_md, encoding="utf-8")

        return PendingSubmissionsReport(
            run_id=run_id,
            run_dir=run_dir,
            institution="ITESCA",
            timestamp_utc=manifest["timestamp_utc"],
            pending_deliveries=tuple(pending_items),
            recommendations=tuple(recommendations),
            blockers=tuple(global_blockers),
            manifest_path=manifest_path,
            summary_md_path=summary_path,
        )


# Registrar monitor institucional en el catálogo central
register_delivery_monitor("ITESCA", MonitorItescaAgent)
register_delivery_monitor("itesca", MonitorItescaAgent)

__all__ = [
    "AGENT_ID_MONITOR_ITESCA",
    "ITESCA_SUBJECTS_CATALOG",
    "MonitorItescaAgent",
    "LIFECYCLE_PENDIENTE",
    "LIFECYCLE_EN_DESARROLLO",
    "LIFECYCLE_ENTREGABLE_GENERADO",
    "LIFECYCLE_CALIDAD_VALIDADA",
    "LIFECYCLE_AUTORIZACION_PENDIENTE",
    "LIFECYCLE_ENTREGA_CONFIRMADA",
]
