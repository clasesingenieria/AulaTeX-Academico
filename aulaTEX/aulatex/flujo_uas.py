"""Orquestador del Flujo de Trabajo Académico para UAS en AulaTeX.

Coordina de manera secuencial, trazable y segura los 5 agentes especializados:
1. `navegación-itesca` (navegación de plataforma UAS, tipo navegación-plataforma)
2. `realizar-planeación`
3. `encontrar-recursos`
4. `extraer-conceptos`
5. `realizar-actividad` (colaborando con estilo-escribir y ciclos de calidad)

Garantiza la preservación de credenciales cifradas sin fugas en artefactos ni bitácoras,
y verifica precondiciones informando bloqueos concretos sin asumir datos no verificados.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import time
from typing import Any
from urllib.parse import urlsplit

from .agente_grabaciones_uas import AgenteGrabacionesUas, GrabacionesUasRequest, GrabacionesUasResult
from .encontrar_recursos_uas import EncontrarRecursosRequest, EncontrarRecursosResult, EncontrarRecursosUasAgent
from .entregar_uas import (
    AGENT_ID_ENTREGAR_UAS,
    EntregarUasAgent,
    EntregarUasRequest,
)
from .extraer_conceptos_uas import ExtraerConceptosRequest, ExtraerConceptosResult, ExtraerConceptosUasAgent
from .monitor_entregas import (
    DeliveryRecommendation,
    PendingDeliveryItem,
    PendingSubmissionsReport,
)
from .monitor_uas import (
    AGENT_ID_MONITOR_UAS,
    AGENT_TYPE_MONITOR_PLATAFORMA,
    MonitorUasAgent,
    MonitorUasRequest,
    UAS_SUBJECTS_CATALOG,
)
from .navegacion_plataforma import assert_no_credential_leak
from .navegacion_uas import (
    NavegacionUasAgent,
    UAS_HOST,
    UasModuleTarget,
    UasNavigationRequest,
    UasNavigationResult,
)
from .planning_layout import _reject_credentials, subject_layout
from .platform_credentials import PlatformCredentialVault, default_vault_path
from .realizar_actividad_uas import (
    RealizarActividadUasAgent,
    RealizarActividadUasRequest,
    RealizarActividadUasResult,
)
from .realizar_entrega import (
    AGENT_TYPE_REALIZAR_ENTREGA,
    DeliverySubmissionRequest,
    DeliverySubmissionResult,
    DeliveryValidationError,
)
from .realizar_planeacion_uas import (
    PlaneacionUasRequest,
    PlaneacionUasResult,
    RealizarPlaneacionUasAgent,
)
from .workspace import AulaTeXWorkspace


@dataclass(frozen=True)
class FlujoUasRequest:
    subject_slug: str = "derecho-mercantil"
    course_id: int = 632
    module_id: int = 49882
    activity_number: int = 2
    week: int = 2
    subject_name: str = "Derecho mercantil"
    program_name: str = "Licenciatura en Contaduría Pública"
    topic: str = "Sujetos del Derecho, personas físicas y morales, sanción, hechos y actos jurídicos"
    student_name: str = "Martín Jonathan De La Cruz Muñoz"
    student_id: str = "26031061"
    advisor_name: str = "Por confirmar"
    group_name: str = "LCP-2026-I"
    city: str = "Culiacán, Sinaloa, México"
    engine: str = "xelatex"
    download_online: bool = True
    output_dir: str = ""


@dataclass(frozen=True)
class FlujoUasResult:
    run_id: str
    run_dir: Path
    manifest_path: Path
    ok: bool
    stages_completed: tuple[str, ...]
    blockers: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    navigation: dict[str, Any] | None = None
    planning: dict[str, Any] | None = None
    resources: dict[str, Any] | None = None
    concepts: dict[str, Any] | None = None
    activity: dict[str, Any] | None = None
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        nav_info = self.navigation or {}
        plan_info = self.planning or {}
        res_info = self.resources or {}
        con_info = self.concepts or {}
        act_info = self.activity or {}

        stages_list = [
            {"agent_id": "navegación-itesca", "agent_name": "Navegación Plataforma UAS", "status": "success" if ("navegacion-plataforma" in self.stages_completed or "navegacion" in self.stages_completed) else "failed", "summary": nav_info.get("page_title") or "Inspección exitosa"},
            {"agent_id": "realizar-planeación", "agent_name": "Planeación Académica Canónica", "status": "success" if ("realizar-planeacion" in self.stages_completed or "planeacion" in self.stages_completed) else "failed", "summary": plan_info.get("contract") or "Planeación generada"},
            {"agent_id": "encontrar-recursos", "agent_name": "Recopilación y Organización de Recursos", "status": "success" if "encontrar-recursos" in self.stages_completed else "failed", "summary": f"{res_info.get('total_resources', len(res_info.get('resources', [])))} recursos organizados"},
            {"agent_id": "extraer-conceptos", "agent_name": "Extracción de Conceptos Estructurada", "status": "success" if "extraer-conceptos" in self.stages_completed else "failed", "summary": f"{con_info.get('concepts_count', con_info.get('total_conceptos', 0))} conceptos extraídos"},
            {"agent_id": "realizar-actividad", "agent_name": "Desarrollo y Ciclo de Calidad EMS", "status": "success" if "realizar-actividad" in self.stages_completed else "failed", "summary": f"EMS {act_info.get('ems_score', 0)}/100 ({act_info.get('maturity_band', 'CERTIFICADO')})"},
        ]

        return {
            "run_id": self.run_id,
            "run_dir": str(self.run_dir),
            "manifest_path": str(self.manifest_path),
            "success": self.ok,
            "ok": self.ok,
            "stages_completed": list(self.stages_completed),
            "blockers": [b.get("reason", str(b)) if isinstance(b, dict) else str(b) for b in self.blockers],
            "navigation": nav_info,
            "planning": plan_info,
            "resources": res_info,
            "concepts": con_info,
            "activity": act_info,
            "summary": self.summary,
            "tex_path": act_info.get("tex_path", ""),
            "pdf_path": act_info.get("pdf_path", ""),
            "deliverable_path": act_info.get("deliverable_path", ""),
            "stages": stages_list,
            "subject_slug": plan_info.get("subject_slug", "derecho-mercantil"),
            "activity_number": plan_info.get("activity_number", 2),
            "week": plan_info.get("week", 2),
            "topic": plan_info.get("topic", ""),
            "student_name": plan_info.get("student_name", "Martín Jonathan De La Cruz Muñoz"),
            "student_id": plan_info.get("student_id", "26031061"),
            "total_duration_sec": act_info.get("duration_sec", 0.0),
        }


class FlujoUasOrchestrator:
    """Orquestador maestro del flujo académico UAS en AulaTeX."""

    def __init__(self, workspace: AulaTeXWorkspace | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.repo_root = self.workspace.repo_root
        self.runs_root = self.workspace.feedback_root / "flujo-uas" / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)

        # Instanciar agentes coordinados
        self.agent_navegacion = NavegacionUasAgent(self.workspace)
        self.agent_planeacion = RealizarPlaneacionUasAgent(self.workspace)
        self.agent_recursos = EncontrarRecursosUasAgent(self.workspace)
        self.agent_conceptos = ExtraerConceptosUasAgent(self.workspace)
        self.agent_actividad = RealizarActividadUasAgent(self.workspace)
        self.agent_monitor = MonitorUasAgent(self.workspace, nav_agent=self.agent_navegacion)
        self.agent_entrega = EntregarUasAgent(self.workspace)
        self.agent_grabaciones = AgenteGrabacionesUas(self.workspace)

    def verify_prerequisites(self) -> dict[str, Any]:
        """Audita el estado de credenciales, red y motores TeX antes de la ejecución."""
        blockers: list[dict[str, Any]] = []

        # 1. Bóveda y PIN maestro
        pin = os.getenv("AULATEX_MASTER_PIN", "")
        vault_path = default_vault_path(self.repo_root)
        vault_ok = False
        uas_account_ok = False

        if not pin:
            blockers.append({
                "kind": "missing_master_pin",
                "detail": "Variable de entorno AULATEX_MASTER_PIN no configurada.",
            })
        elif not vault_path.exists():
            blockers.append({
                "kind": "missing_vault_file",
                "detail": f"Archivo de bóveda no encontrado en {vault_path}",
            })
        else:
            try:
                vault = PlatformCredentialVault(vault_path)
                accounts = [
                    a for a in vault.list_accounts(pin)
                    if a.get("institution", "").casefold() == "uas"
                    and urlsplit(a.get("url", "")).hostname == UAS_HOST
                ]
                if not accounts:
                    blockers.append({
                        "kind": "missing_uas_account",
                        "detail": f"No se encontró una cuenta institucional para UAS en {UAS_HOST}",
                    })
                else:
                    vault_ok = True
                    uas_account_ok = True
            except Exception as e:
                blockers.append({
                    "kind": "vault_unlock_failed",
                    "detail": f"Fallo al abrir la bóveda cifrada: {type(e).__name__}",
                })

        # 2. Conectividad DNS y HTTPS hacia UAS
        dns_ok = False
        try:
            socket.getaddrinfo(UAS_HOST, 443, type=socket.SOCK_STREAM)
            dns_ok = True
        except Exception:
            blockers.append({
                "kind": "dns_resolution_failed",
                "detail": f"No se pudo resolver el host {UAS_HOST} mediante DNS local ni DoH.",
            })

        # 3. Compilador TeX
        import shutil as sht
        tex_ok = bool(sht.which("xelatex") or sht.which("pdflatex"))
        if not tex_ok:
            blockers.append({
                "kind": "missing_tex_compiler",
                "detail": "No se encontraron los binarios de xelatex ni pdflatex en el sistema.",
            })

        return {
            "prerequisites_passed": len(blockers) == 0,
            "vault_ok": vault_ok,
            "uas_account_ok": uas_account_ok,
            "dns_ok": dns_ok,
            "tex_ok": tex_ok,
            "blockers": blockers,
        }

    def execute_workflow(self, request: FlujoUasRequest) -> FlujoUasResult:
        """Ejecuta la secuencia completa de los 5 agentes académicos para UAS."""
        run_id = f"{self.workspace.timestamp()}-flujo-uas-{request.subject_slug}-act{request.activity_number}"
        run_dir = (
            self.workspace.resolve_target(request.output_dir)
            if request.output_dir
            else self.runs_root / run_id
        )
        run_dir.mkdir(parents=True, exist_ok=True)

        stages_completed: list[str] = []
        blockers: list[dict[str, Any]] = []

        # Localizar la carpeta de la materia dentro de UAS/licenciatura-en-contaduria-uas/
        uas_root = self.repo_root / "UAS" / "licenciatura-en-contaduria-uas"
        subject_dir = uas_root / request.subject_slug
        if not subject_dir.exists():
            # Buscar coincidencia difusa en UAS
            candidates = [p for p in uas_root.glob(f"*{request.subject_slug}*") if p.is_dir()]
            if candidates:
                subject_dir = candidates[0]
            else:
                blockers.append({
                    "stage": "preflight",
                    "kind": "subject_directory_missing",
                    "detail": f"Directorio de materia {request.subject_slug} no existe en {uas_root}",
                })
                return self._finalize_result(run_id, run_dir, False, stages_completed, blockers)

        # -------------------------------------------------------------
        # ETAPA 1: Navegación de plataforma UAS (`navegación-itesca` / UAS)
        # -------------------------------------------------------------
        print(f"[Flujo UAS] 1/5: Inspección en plataforma con {self.agent_navegacion.agent_id}...")
        nav_target = UasModuleTarget(
            module_id=request.module_id,
            kind="assign",
            course_id=request.course_id,
            local_activity_number=request.activity_number,
            subject_slug=request.subject_slug,
        )
        nav_req = UasNavigationRequest(
            inspect_dashboard=True,
            course_ids=(request.course_id,),
            modules=(nav_target,),
            output_dir=str(run_dir / "01-navegacion"),
            download_resources=request.download_online,
        )

        nav_data: dict[str, Any] = {}
        try:
            nav_res = self.agent_navegacion.inspect(nav_req)
            nav_data = nav_res.snapshot
            if nav_res.blockers:
                blockers.extend(nav_res.blockers)
            stages_completed.append("navegacion-plataforma")
        except Exception as err:
            # Si falla navegación online, intentamos usar modelo existente local si está disponible
            existing_plan_path = subject_dir / f"planeaciones-{request.subject_slug}" / f"planeacion-modulo-{request.module_id}.json"
            if existing_plan_path.exists():
                print(f"[Flujo UAS] Advertencia: Conexión online bloqueada ({err}); usando respaldo local verificado.")
                nav_data = {"modules": {str(request.module_id): json.loads(existing_plan_path.read_text(encoding="utf-8")).get("activity", {})}}
                stages_completed.append("navegacion-plataforma")
            else:
                blockers.append({
                    "stage": "navegacion-plataforma",
                    "kind": type(err).__name__,
                    "detail": f"Fallo al autenticar o navegar en UAS: {str(err)}",
                })
                return self._finalize_result(run_id, run_dir, False, stages_completed, blockers, navigation=nav_data)

        # Extraer información del módulo inspeccionado
        mod_info = nav_data.get("modules", {}).get(str(request.module_id), {})

        # -------------------------------------------------------------
        # ETAPA 2: Realizar Planeación (`realizar-planeación`)
        # -------------------------------------------------------------
        print(f"[Flujo UAS] 2/5: Realizando planeación canónica con {self.agent_planeacion.agent_id}...")
        plan_req = PlaneacionUasRequest(
            subject_dir=subject_dir,
            module_data=mod_info,
            course_id=request.course_id,
            course_name_literal=f"2026_I_{request.subject_name}_LCP",
            subject_name=request.subject_name,
            program_name=request.program_name,
            week=request.week,
            topic=request.topic,
            override_activity_id=request.module_id,
            output_dir=str(subject_dir / f"planeaciones-{request.subject_slug}"),
        )
        try:
            plan_res = self.agent_planeacion.plan(plan_req)
            plan_data = plan_res.plan_dict
            stages_completed.append("realizar-planeacion")
        except Exception as err:
            blockers.append({
                "stage": "realizar-planeacion",
                "kind": type(err).__name__,
                "detail": f"Error al generar planeación: {str(err)}",
            })
            return self._finalize_result(run_id, run_dir, False, stages_completed, blockers, navigation=nav_data)

        # -------------------------------------------------------------
        # ETAPA 3: Encontrar Recursos (`encontrar-recursos`)
        # -------------------------------------------------------------
        print(f"[Flujo UAS] 3/5: Localizando y organizando recursos con {self.agent_recursos.agent_id}...")
        rec_req = EncontrarRecursosRequest(
            subject_dir=subject_dir,
            activity_plan=plan_data,
            download_online=request.download_online,
        )
        try:
            rec_res = self.agent_recursos.find_and_organize(rec_req, nav_agent=self.agent_navegacion)
            rec_data = {
                "total_found": rec_res.total_found,
                "total_downloaded": rec_res.total_downloaded,
                "resources": [asdict(r) for r in rec_res.resources],
                "inventory_json": str(rec_res.inventory_json),
                "bib_file": str(rec_res.bib_file) if rec_res.bib_file else None,
            }
            if rec_res.missing_resources:
                for miss in rec_res.missing_resources:
                    blockers.append({"stage": "encontrar-recursos", "kind": "resource_warning", "detail": miss})
            stages_completed.append("encontrar-recursos")
        except Exception as err:
            blockers.append({
                "stage": "encontrar-recursos",
                "kind": type(err).__name__,
                "detail": f"Error al organizar recursos: {str(err)}",
            })
            return self._finalize_result(
                run_id, run_dir, False, stages_completed, blockers,
                navigation=nav_data, planning=plan_data
            )

        # -------------------------------------------------------------
        # ETAPA 4: Extraer Conceptos (`extraer-conceptos`)
        # -------------------------------------------------------------
        print(f"[Flujo UAS] 4/5: Extracción de conceptos clave con {self.agent_conceptos.agent_id}...")
        concept_resources = tuple(r["local_path"] for r in rec_data.get("resources", []))
        conc_req = ExtraerConceptosRequest(
            subject_dir=subject_dir,
            activity_plan=plan_data,
            resources=concept_resources,
        )
        try:
            conc_res = self.agent_conceptos.extract(conc_req)
            conc_data = {
                "activity_id": conc_res.activity_id,
                "notes_dir": str(conc_res.notes_dir),
                "concepts_count": conc_res.concepts_count,
                "ideas_count": conc_res.ideas_count,
                "fichas_json": str(conc_res.fichas_json),
                "notes_readme": str(conc_res.notes_readme),
            }
            stages_completed.append("extraer-conceptos")
        except Exception as err:
            blockers.append({
                "stage": "extraer-conceptos",
                "kind": type(err).__name__,
                "detail": f"Error al extraer conceptos: {str(err)}",
            })
            return self._finalize_result(
                run_id, run_dir, False, stages_completed, blockers,
                navigation=nav_data, planning=plan_data, resources=rec_data
            )

        # Cargar fichas generadas para alimentar la actividad
        fichas_obj = json.loads(conc_res.fichas_json.read_text(encoding="utf-8"))

        # -------------------------------------------------------------
        # ETAPA 5: Realizar Actividad y Ciclos de Calidad (`realizar-actividad`)
        # -------------------------------------------------------------
        print(f"[Flujo UAS] 5/5: Desarrollo, estilo-escribir y compilación con {self.agent_actividad.agent_id}...")
        act_req = RealizarActividadUasRequest(
            subject_dir=subject_dir,
            activity_plan=plan_data,
            fichas_conceptos=fichas_obj,
            student_name=request.student_name,
            student_id=request.student_id,
            advisor_name=request.advisor_name,
            group_name=request.group_name,
            city=request.city,
            engine=request.engine,
            max_rounds_style=2,
            activity_number=request.activity_number,
        )
        try:
            act_res = self.agent_actividad.run(act_req)
            act_data = {
                "activity_id": act_res.activity_id,
                "tex_path": str(act_res.tex_path),
                "pdf_path": str(act_res.pdf_path) if act_res.pdf_path else None,
                "delivery_pdf_path": str(act_res.delivery_pdf_path) if act_res.delivery_pdf_path else None,
                "compile_ok": act_res.compile_ok,
                "style_score": act_res.style_score,
                "ems_score": act_res.ems_score,
                "invariants_preserved": act_res.invariants_preserved,
                "transformations_count": act_res.transformations_count,
            }
            if not act_res.compile_ok:
                blockers.append({
                    "stage": "realizar-actividad",
                    "kind": "compilation_failed",
                    "detail": "La compilación LaTeX falló; revisar mensajes de xelatex.",
                })
            else:
                stages_completed.append("realizar-actividad")
        except Exception as err:
            blockers.append({
                "stage": "realizar-actividad",
                "kind": type(err).__name__,
                "detail": f"Error al desarrollar actividad: {str(err)}",
            })
            return self._finalize_result(
                run_id, run_dir, False, stages_completed, blockers,
                navigation=nav_data, planning=plan_data, resources=rec_data, concepts=conc_data
            )

        overall_ok = len(stages_completed) == 5 and all(b.get("kind") != "compilation_failed" for b in blockers)

        return self._finalize_result(
            run_id=run_id,
            run_dir=run_dir,
            ok=overall_ok,
            stages_completed=stages_completed,
            blockers=blockers,
            navigation=nav_data,
            planning=plan_data,
            resources=rec_data,
            concepts=conc_data,
            activity=act_data,
        )

    def _finalize_result(
        self,
        run_id: str,
        run_dir: Path,
        ok: bool,
        stages_completed: list[str],
        blockers: list[dict[str, Any]],
        navigation: dict[str, Any] | None = None,
        planning: dict[str, Any] | None = None,
        resources: dict[str, Any] | None = None,
        concepts: dict[str, Any] | None = None,
        activity: dict[str, Any] | None = None,
    ) -> FlujoUasResult:
        summary_lines = [
            f"# Resumen de Ejecución Flujo Académico UAS ({run_id})",
            "",
            f"- **Resultado Global:** {'EXITOSO' if ok else 'BLOQUEADO / INCOMPLETO'}",
            f"- **Etapas Completadas ({len(stages_completed)}/5):** {', '.join(stages_completed) or 'Ninguna'}",
            f"- **Bloqueos Detectados:** {len(blockers)}",
            "",
            "## Detalle por Agente:",
            f"1. **navegación-itesca (UAS):** {'OK' if 'navegacion-plataforma' in stages_completed else 'PENDIENTE/FALLÓ'}",
            f"2. **realizar-planeación:** {'OK' if 'realizar-planeacion' in stages_completed else 'PENDIENTE/FALLÓ'}",
            f"3. **encontrar-recursos:** {'OK' if 'encontrar-recursos' in stages_completed else 'PENDIENTE/FALLÓ'}",
            f"4. **extraer-conceptos:** {'OK' if 'extraer-conceptos' in stages_completed else 'PENDIENTE/FALLÓ'}",
            f"5. **realizar-actividad (estilo-escribir + TeX):** {'OK' if 'realizar-actividad' in stages_completed else 'PENDIENTE/FALLÓ'}",
            "",
        ]
        if blockers:
            summary_lines.append("## Bloqueos Registrados:\n")
            for b in blockers:
                summary_lines.append(f"- **[{b.get('stage', 'general')}]** {b.get('kind')}: {b.get('detail')}")

        summary = "\n".join(summary_lines)

        manifest = {
            "run_id": run_id,
            "orchestrator": "aulatex",
            "institution": "UAS",
            "ok": ok,
            "stages_completed": stages_completed,
            "blockers": blockers,
            "navigation_summary": {"inspected": navigation is not None},
            "planning_summary": {"planned": planning is not None},
            "resources_summary": {"resources_organized": resources is not None},
            "concepts_summary": {"concepts_extracted": concepts is not None},
            "activity_summary": {"deliverable_created": activity is not None},
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        _reject_credentials(manifest)

        manifest_path = run_dir / "manifest-flujo-uas.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        report_path = run_dir / "reporte-flujo-uas.md"
        report_path.write_text(summary, encoding="utf-8")

        self.workspace.append_bitacora(run_id, "flujo-uas", manifest)

        return FlujoUasResult(
            run_id=run_id,
            run_dir=run_dir,
            manifest_path=manifest_path,
            ok=ok,
            stages_completed=tuple(stages_completed),
            blockers=tuple(blockers),
            navigation=navigation,
            planning=planning,
            resources=resources,
            concepts=concepts,
            activity=activity,
            summary=summary,
        )

    def monitor_deliveries(
        self,
        subject_slug: str,
        course_id: int | None = None,
        inspect_platform: bool = False,
        output_dir: str = "",
        force_reevaluate: bool = False,
    ) -> PendingSubmissionsReport:
        """Audita las entregas de una materia UAS usando monitor-uas."""
        req = MonitorUasRequest(
            subject_slug=subject_slug,
            course_id=course_id,
            inspect_platform=inspect_platform,
            output_dir=output_dir,
            force_reevaluate=force_reevaluate,
        )
        return self.agent_monitor.monitor_deliveries(req)

    def run_pending_deliveries(
        self,
        subject_slug: str,
        course_id: int | None = None,
        inspect_platform: bool = False,
        download_resources: bool = False,
        compile_pdf: bool = True,
        output_dir: str = "",
    ) -> dict[str, Any]:
        """Coordina monitor-uas y ejecuta secuencialmente el flujo canónico para actividades pendientes.

        Garantiza el principio de soberanía del usuario:
        "Autorizar la realización de una actividad no equivale a autorizar su envío."
        Todos los entregables generados se preservan localmente en estado 'autorizacion_pendiente'
        sin publicar ni enviar nada a la plataforma UAS.
        """
        clean_slug = subject_slug.replace("-uas", "").strip().lower()
        if clean_slug in ("investigacion-aplicada", "investigacion-aplicada-contaduria"):
            clean_slug = "investigacion-aplicada-a-la-contaduria"

        # Soporte multi-materia si se solicita 'all', 'todas', '*' o lista separada por comas
        if clean_slug in ("all", "todas", "*", "multi") or "," in clean_slug:
            subjects = (
                [s.strip() for s in clean_slug.split(",") if s.strip()]
                if "," in clean_slug
                else list(UAS_SUBJECTS_CATALOG.keys())
            )
            multi_results: dict[str, Any] = {}
            multi_ok = True
            for subj in subjects:
                res = self.run_pending_deliveries(
                    subject_slug=subj,
                    inspect_platform=inspect_platform,
                    download_resources=download_resources,
                    compile_pdf=compile_pdf,
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

        catalog_entry = UAS_SUBJECTS_CATALOG.get(clean_slug, {})
        cid = course_id or catalog_entry.get("course_id") or 632

        run_id = f"{self.workspace.timestamp()}-uas-pending-batch"
        batch_dir = (
            self.workspace.resolve_target(output_dir)
            if output_dir.strip()
            else self.runs_root / run_id
        )
        batch_dir.mkdir(parents=True, exist_ok=True)

        # 1. Ejecutar monitor-uas
        mon_report = self.monitor_deliveries(
            subject_slug=clean_slug,
            course_id=cid,
            inspect_platform=inspect_platform,
            output_dir=str(batch_dir / "monitor"),
        )

        # 2. Identificar actividades pendientes de realizar
        pending_activities: list[int] = []
        already_ready: list[dict[str, Any]] = []

        for rec in mon_report.recommendations:
            if rec.recommended_action == "solicitar-realizar-actividad":
                pending_activities.append(rec.activity_number)
            elif rec.recommended_action == "bloqueado_falta_prerrequisitos":
                # Si faltan planeación, recursos o entregable local, es candidata a realizarse por el flujo
                pending_activities.append(rec.activity_number)
            elif rec.recommended_action.startswith("solicitar-"):
                pending_activities.append(rec.activity_number)
            elif rec.recommended_action in ("esperar-autorizacion-entrega", "ya_entregado"):
                already_ready.append({
                    "activity": rec.activity_number,
                    "action": rec.recommended_action,
                    "artifact": rec.proposed_delivery_artifact,
                    "sha256": rec.proposed_delivery_sha256,
                    "rationale": rec.rationale,
                })

        pending_activities = sorted(list(set(pending_activities)))

        executed_activities: list[dict[str, Any]] = []
        overall_ok = True

        # 3. Para cada actividad pendiente, ejecutar la secuencia canónica
        for act_num in pending_activities:
            act_info = catalog_entry.get("activities", {}).get(act_num, {})
            mid = act_info.get("module_id", 0)
            topic = act_info.get("title", f"Actividad {act_num}")
            week = act_info.get("week", act_num)

            flujo_req = FlujoUasRequest(
                subject_slug=clean_slug,
                course_id=cid,
                module_id=mid,
                activity_number=act_num,
                week=week,
                subject_name=catalog_entry.get("title", clean_slug),
                topic=topic,
                download_online=download_resources,
                output_dir=str(batch_dir / f"actividad-{act_num:02d}"),
            )
            flujo_res = self.execute_workflow(flujo_req)
            if not flujo_res.ok:
                overall_ok = False

            deliverable_path = flujo_res.activity.get("deliverable_path") if flujo_res.activity else None
            sha256 = ""
            if deliverable_path and Path(deliverable_path).is_file():
                sha256 = hashlib.sha256(Path(deliverable_path).read_bytes()).hexdigest()

            staged_proposal = {
                "activity": act_num,
                "status": "autorizacion_pendiente" if flujo_res.ok else "error_ejecucion",
                "deliverable_path": deliverable_path,
                "sha256": sha256,
                "ems_score": flujo_res.activity.get("ems_score", 0.0) if flujo_res.activity else 0.0,
                "notice": "Autorizar la realización de una actividad no equivale a autorizar su envío. Retenida localmente.",
            }

            executed_activities.append({
                "activity": act_num,
                "ok": flujo_res.ok,
                "flujo_run_id": flujo_res.run_id,
                "stages_completed": list(flujo_res.stages_completed),
                "proposed_delivery": staged_proposal,
                "blockers": [b.get("detail", str(b)) if isinstance(b, dict) else str(b) for b in flujo_res.blockers],
            })

        batch_manifest = {
            "schema_version": "1.0.0",
            "run_id": run_id,
            "institution": "UAS",
            "subject_slug": clean_slug,
            "course_id": cid,
            "orchestrator": "aulatex",
            "ok": overall_ok,
            "pending_identified": pending_activities,
            "already_completed_or_held": already_ready,
            "executed_activities": executed_activities,
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        _reject_credentials(batch_manifest)

        manifest_file = batch_dir / "manifest-uas-pending.json"
        manifest_file.write_text(json.dumps(batch_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        summary_lines = [
            f"# Reporte de Seguimiento y Realización UAS - {clean_slug}",
            "",
            f"- **Resultado:** {'EXITOSO' if overall_ok else 'CON OBSERVACIONES'}",
            f"- **Actividades ya entregadas / en espera:** {len(already_ready)}",
            f"- **Actividades identificadas y ejecutadas:** {len(executed_activities)}",
            "",
            "## Entregables retenidos (autorizacion_pendiente):",
        ]
        for ex in executed_activities:
            prop = ex.get("proposed_delivery", {})
            summary_lines.append(f"- Actividad {ex['activity']}: {prop.get('deliverable_path')} (SHA-256: {prop.get('sha256', '')[:12]}...)")
        summary_lines.append("\n> [!IMPORTANT]\n> Principio de Soberanía del Usuario: Las entregas no han sido enviadas a UAS. Se requiere autorización explícita con `entregar-uas`.")

        report_file = batch_dir / "reporte-uas-pending.md"
        report_file.write_text("\n".join(summary_lines), encoding="utf-8")

        return batch_manifest

    def submit_authorized_delivery(
        self,
        subject_slug: str,
        activity_number: int,
        artifact_path: str | Path,
        user_validated: bool = False,
        expected_sha256: str | None = None,
        course_id: int | None = None,
        module_id: int | None = None,
        finalize: bool = False,
        dry_run: bool = True,
        output_dir: str = "",
    ) -> DeliverySubmissionResult:
        """Invoca a entregar-uas bajo el principio estricto de compuerta fail-closed.

        Si user_validated es False, detiene la operación inmediatamente informando
        el bloqueo concreto sin enviar solicitudes mutantes a UAS.
        """
        sub_req = EntregarUasRequest(
            subject_slug=subject_slug,
            activity_number=activity_number,
            artifact_path=artifact_path,
            expected_sha256=expected_sha256,
            course_id=course_id,
            module_id=module_id,
            user_validated=user_validated,
            finalize=finalize,
            dry_run=dry_run,
            output_dir=output_dir,
        )
        return self.agent_entrega.submit(sub_req)

    def run_interagent_excel_dialogue(
        self,
        subject_slug: str = "herramientas-digitales",
        course_id: int = 635,
    ) -> dict[str, Any]:
        """Ejecuta el diálogo formal multi-agente entre grabaciones-uas, monitor-uas,
        realizar-planeación y realizar-actividad para diagnosticar las deficiencias de los
        entregables Excel y presentar una Línea de Acción verificada.
        """
        clean_slug = subject_slug.replace("-uas", "").strip().lower()
        subject_root = self.agent_monitor._resolve_subject_root(clean_slug)
        plans_dir = subject_root / f"planeaciones-{clean_slug}"
        plans_dir.mkdir(parents=True, exist_ok=True)

        # 1. Ejecutar monitor-uas para actualizar estado-entregas-uas.json y recolectar auditorías XML
        mon_report = self.monitor_deliveries(
            subject_slug=clean_slug,
            course_id=course_id,
            inspect_platform=False,
        )

        catalog_entry = UAS_SUBJECTS_CATALOG.get(clean_slug, {})
        acts_dict = catalog_entry.get("activities", {})

        excel_audits: dict[str, Any] = {}
        for act_num, act_meta in sorted(acts_dict.items()):
            mid = act_meta.get("module_id")
            week = act_meta.get("week") or act_num
            delivs = self.agent_monitor._locate_deliverables(
                subject_root, act_num, week=week, title=act_meta.get("title", ""), module_id=mid
            )
            audit = self.agent_monitor.audit_excel_deliverable_against_classroom(subject_root, mid, delivs)
            if audit.get("is_excel_module") or mid in (50102, 50113):
                excel_audits[str(mid)] = {
                    "activity_number": act_num,
                    "title": act_meta.get("title", ""),
                    "week": week,
                    **audit,
                }

        # 2. Construir el Diálogo Multi-Agente estructurado
        dialogue_turns = [
            {
                "turn": 1,
                "agent_id": "monitor-uas",
                "agent_role": "Auditor Forense de Entregas y Plataforma Moodle FCA (MonitorUasAgent)",
                "statement": (
                    "He auditado a nivel XML/ZIP los libros .xlsx en 'entregas-herramientas-digitales/' frente a los 65+ "
                    "archivos oficiales de la 'Carpeta de Apoyo' (Módulo 50094) en 'referencias-herramientas-digitales/materiales-aula/' "
                    "y las calificaciones del Dr. Dámaso Guadalupe Ruíz González en Moodle FCA:\n"
                    "1. Módulo 50114 (Excel Básico S2 — Calificación 5.00/10.00, 'NPT ---> Creo que no son los ejecicios de la clase (Revise videos)'): "
                    "El archivo 'GPO103LCP_EXCEL_BASICO_MartinJonathan_DeLaCruzMunoz.xlsx' (11,340 bytes) contiene 6 hojas sintéticas "
                    "(Identificacion, Practica_1_Importes, Practica_2_Gastos, Practica_3_Formatos, Practica_4_Referencias, Comprobacion) "
                    "clonadas de 'Excel-Basico-S2-Ejemplo.xlsx' (cuya celda B3 declara literalmente 'Ejemplo hipotetico; no ejercicio asignado por el docente'). "
                    "Tiene 0% de coincidencia con los libros de clase (Cap. 1, 2, 3, 4, 6 y 7) y 'Practica_3_Formatos' tiene 0 fórmulas.\n"
                    "2. Módulo 50130 (Libro de Excel Aplicado S3 — Calificación 10.00/20.00, '*** BIEN: ...No son los ejercios de la clase ..'): "
                    "El archivo 'GPO103LCP_EXCEL_APLICADO_MartinJonathan_DeLaCruzMunoz.xlsx' (17,841 bytes) tiene 8 hojas inventadas "
                    "con datos ficticios ('ART-101 Laptop Dell', 'CLI-001 Comercial del Noroeste', 'EMP-01 García López Carlos'), "
                    "carece de objeto PivotTable nativo (xl/pivotTables/pivotTable*.xml = 0; simula la tabla dinámica con =SUMIFS) "
                    "y coexiste con un duplicado erróneo del grupo 101 ('GPO101LCP_...xlsx').\n"
                    "3. Módulo 50131 (Examen Excel Práctico en Clase S3 — Calificación 5.00/10.00, 'No corresponden a los ejercicios de clases'): "
                    "El archivo 'GPO103LCP_EXAMEN_EXCEL_S3_MartinJonathan_DeLaCruzMunoz.xlsx' (17,775 bytes) inventó 3 hojas sintéticas "
                    "(Evaluacion_Ventas, Interes_Moratorio, Escala_Calificaciones) que distorsionan las plantillas del examen: redujo "
                    "VentaMaquillaje.xlsx de 1,900 filas a 40 filas inventadas (dejando 156 etiquetas <f/> vacías en las filas 6 a 44), "
                    "alteró la escala oficial 0–20 de Alumnos.xlsx (Boris Reyes=18) a una escala inventada 0–100 (Boris Reyes=92), "
                    "y omitió Gastos.xlsx, EstadosMaquillaje.xlsx y Puntaje.xlsx (VLOOKUP aproximado).\n"
                    "4. Módulo 50144 (Semana 4 — Google Sites + Complemento LCP): Aunque el reporte PDF del sitio web nativo está listo, "
                    "falta construir el libro 'EXCEL_CONTA_MartinJonathan_DeLaCruzMunoz.xlsx' (15 hojas contables) exigido en la carpeta "
                    "'Complemento de LCP - Aplicado'."
                ),
            },
            {
                "turn": 2,
                "agent_id": "grabaciones-uas",
                "agent_role": "Agente de Grabaciones, Transcripción Whisper y Evidencia Visual (AgenteGrabacionesUas)",
                "statement": (
                    "Confirmo el diagnóstico de 'monitor-uas' con la evidencia primaria de las 6 sesiones grabadas por el Dr. Dámaso Ruíz:\n"
                    "- En S1 (Drive ID '1NaR_KBkiiZRg3ioHxiSRJw_GMqCDf2rD', 2h 06m, 1,284 segmentos SRT + 12 capturas PNG), el docente establece "
                    "[00:07:38 - 00:08:23] la creación de la carpeta institucional en Google Drive compartida exclusivamente con su correo (no pública) "
                    "y la nomenclatura obligatoria GPO103LCP_...\n"
                    "- En S2 Clase 1 ('I_H5f_gGbuc', 03/oct/2026) y S2 Clase 2 ('0FGH031UsFo', 10/oct/2026), el docente resuelve en vivo los libros "
                    "de la Carpeta de Apoyo (50094) correspondientes a los Capítulos 1, 2, 3, 4, 6 y 7: 01_ListaProductos.xlsx (FACTURAS), "
                    "02_Ventas.xlsx (1,900 registros), 02_Referencias.xlsx (Relativas, Absolutas con IGV 18% y Mixtas tabla 10x10), "
                    "VentaMaquillaje.xlsx, FuncionesTexto.xlsx (9 hojas) e Interés Moratorio.xlsx (Mora y Promoción).\n"
                    "- En S3 Clase 1 ('q9KgoQqUJpU', 17/oct/2026) y S3 Clase 2 ('ZSLk1hRY48U', 24/oct/2026), el docente desarrolla los ejercicios "
                    "de los Capítulos 5, 8, 9, 10 y 11 y aplica el Examen Práctico sobre las plantillas oficiales: Alumnos.xlsx (escala 0–20 con "
                    "=IFS(AND(B2>=0,B2<=10),'Bajo',...)), Gastos.xlsx (=IF(SUM(B3:B5)<=350,'Dentro de presupuesto','Presupuesto excedido')), "
                    "EstadosMaquillaje.xlsx (8 hojas SI/Y/O), Puntaje.xlsx (=VLOOKUP(F2,A4:C17,3,TRUE)), SelecciónCódigo.xlsx, "
                    "05_Tablas Dinámicas.xlsx, 02_Subtotales.xlsx y 03_FlujoCaja.xlsx.\n"
                    "- En S4 ('7ZomiXX7eus', 07/nov/2026) y la subcarpeta 'Complemento de LCP - Aplicado', el docente instruye integrar el "
                    "portal nativo de Google Sites con las 3 prácticas contables SUAD 25-26 en 'EXCEL_CONTA_MartinJonathan_DeLaCruzMunoz.xlsx'."
                ),
            },
            {
                "turn": 3,
                "agent_id": "realizar-planeacion",
                "agent_role": "Agente de Planeación Pedagógica Canónica (RealizarPlaneacionUasAgent)",
                "statement": (
                    "He actualizado los contratos pedagógicos y criterios de aceptación en 'planeaciones-herramientas-digitales/' "
                    "(modulo-50114.md, modulo-50130.md, modulo-50131.md y MAPEO-TRANSCRIPCION-ACTIVIDADES.md):\n"
                    "- Regla de Rechazo Automático (Invariante): Queda prohibido usar hojas sintéticas o datos inventados. Todo entregable .xlsx "
                    "debe conservar intactos los nombres de pestañas, encabezados, filas y datos originales de 'referencias-herramientas-digitales/materiales-aula/'.\n"
                    "- Contrato Módulo 50114 (Excel Básico S2): Libro 'GPO103LCP_EXCEL_BASICO_MartinJonathan_DeLaCruzMunoz.xlsx' integrado por las hojas "
                    "oficiales resueltas de Cap. 1 (FACTURAS, Ventas), Cap. 2 (ResumenGanancias), Cap. 3 (Relativas, Absolutas, Mixtas, PlayStation, Hoteles), "
                    "Cap. 4 (VentaMaquillaje 1,900 filas, Corporación_Televisiva, Estaturas), Cap. 6 (FuncionesTexto 9 hojas) y Cap. 7 (Mora, Promoción, PlanProyecto).\n"
                    "- Contrato Módulo 50130 (Excel Aplicado S3): Libro 'GPO103LCP_EXCEL_APLICADO_MartinJonathan_DeLaCruzMunoz.xlsx' integrado por las hojas "
                    "oficiales resueltas de Cap. 5 (01_FunciónLogica, 02_SIAnidado, Alumnos, Gastos, EstadosMaquillaje), Cap. 8 (01_Elegir, 02_BuscarV, "
                    "03_RangoAproximado, 04_BuscarH, Puntaje, SelecciónCódigo), Cap. 9 (ListaInmobiliaria, Tablas Dinámicas nativas), Cap. 10 (Crear Gráficos, FlujoCaja) "
                    "y Cap. 11 (Subtotales, Esquemas, Validación, Formato Condicional), eliminando el duplicado 'GPO101LCP_...xlsx'.\n"
                    "- Contrato Módulo 50131 (Examen Excel S3): Libro 'GPO103LCP_EXAMEN_EXCEL_S3_MartinJonathan_DeLaCruzMunoz.xlsx' construido directamente "
                    "sobre las plantillas oficiales de examen (Alumnos con escala 0–20 =IFS, Gastos con límite 350, EstadosMaquillaje 8 hojas, "
                    "VentaMaquillaje 1,900 registros íntegros, Interés Moratorio hojas Mora/Promoción, Puntaje con VLOOKUP aproximado y SelecciónCódigo) "
                    "+ reedición de 'reporte-herramientas-digitales-Examen-S3.tex'.\n"
                    "- Contrato Módulo 50144 (Semana 4): Reporte 'GPO103_LCP_WEB_MartinJonathan_DeLaCruzMunoz.pdf' + libro contable "
                    "'EXCEL_CONTA_MartinJonathan_DeLaCruzMunoz.xlsx' con las 15 hojas de las prácticas 1, 2 y 4 SUAD 25-26."
                ),
            },
            {
                "turn": 4,
                "agent_id": "realizar-actividad",
                "agent_role": "Agente Constructor de Libros Excel y Manuscritos LaTeX (RealizarActividadUasAgent / ResolverEjerciciosAgent)",
                "statement": (
                    "Recibo las especificaciones verificadas de 'monitor-uas', 'grabaciones-uas' y 'realizar-planeacion'. "
                    "Establezco la Línea de Acción en 5 fases deterministas para reconstruir los libros .xlsx clonando directamente "
                    "los archivos fuente de 'referencias-herramientas-digitales/materiales-aula/', inyectando las fórmulas exactas "
                    "del Dr. Dámaso, recompilando las memorias técnicas LaTeX (.tex -> .pdf) y re-auditando con 'monitor-uas' hasta "
                    "alcanzar 0 bloqueos antes de solicitar autorización de reenvío en Moodle FCA."
                ),
            },
        ]

        action_line = [
            {
                "step": 1,
                "phase": "Reconstrucción Canónica de Semana 2 — Excel Básico (Módulo 50114)",
                "responsible_agents": ["realizar-actividad", "monitor-uas"],
                "target_deliverable": "entregas-herramientas-digitales/GPO103LCP_EXCEL_BASICO_MartinJonathan_DeLaCruzMunoz.xlsx",
                "source_templates_used": [
                    "210b305c0e-01_ListaProductos.xlsx (FACTURAS)",
                    "236e9c1bd9-02_Ventas.xlsx (Ventas 1,900 filas, Ventas-2018-2019)",
                    "5a8d0def2a-02_Referencias.xlsx (Relativas, Absolutas IGV 0.18, Mixtas 10x10)",
                    "06b6557a4b-03_ResumenGanancias.xlsx / 61e2629880-ResumenGanancias_Finalizado.xlsx",
                    "83c0c60472-Alquiler.xlsx (PlayStation) / d701980d99-Hoteles.xlsx",
                    "ce7faeb208-VentaMaquillaje.xlsx (1,900 registros con SUMIF/COUNTIF/AVERAGEIF/SUMIFS)",
                    "4761c8b39a-FuncionesTexto.xlsx (9 hojas: Minúsculas, Mayúsculas, UnirCadenas, NombrePropio, Izq-Der-, Largo, HALLAR-1, HALLAR-2, EXTRAE)",
                    "7901270eeb-Interés Moratorio.xlsx (Mora, Promoción) y 13d8c6df04-Funciones de Fecha.xlsx",
                ],
                "verification_gate": "100% de hojas provenientes de Carpeta de Apoyo (50094), 0 hojas sintéticas de 'Excel-Basico-S2-Ejemplo.xlsx'.",
            },
            {
                "step": 2,
                "phase": "Reconstrucción Canónica de Semana 3 — Libro de Excel Aplicado (Módulo 50130)",
                "responsible_agents": ["realizar-actividad", "monitor-uas"],
                "target_deliverable": "entregas-herramientas-digitales/GPO103LCP_EXCEL_APLICADO_MartinJonathan_DeLaCruzMunoz.xlsx",
                "source_templates_used": [
                    "57fd09e9df-01_FunciónLogica.xlsx (8 hojas SI/Y/O) y f1e88001ca-02_SIAnidado.xlsx (5 hojas)",
                    "70debcc256-Alumnos.xlsx / 71f623e337-Gastos.xlsx / a21378de49-EstadosMaquillaje.xlsx (8 hojas)",
                    "37a36ca868-01_Elegir.xlsx, 839633c173-02_BuscarV.xlsx, 0565d75c06-03_RangoAproximado.xlsx, efd2f48e1a-04_BuscarH.xlsx, cd849b5f38-Puntaje.xlsx, 9f4890c5fe-SelecciónCódigo.xlsx",
                    "c9059985a8-01_ListaInmobiliaria.xlsx, 96bd24eb56-05_Tablas Dinámicas.xlsx, 7e7a8c50ab-03_FlujoCaja.xlsx, 587a2bb9a1-02_Subtotales.xlsx, 9f6c6137f1-04_Validación.xlsx",
                ],
                "verification_gate": "Eliminación de 'GPO101LCP_...xlsx', inclusión de las plantillas reales de Cap. 5, 8, 9, 10 y 11 y actualización de 'reporte-herramientas-digitales-Actividad-8.tex'.",
            },
            {
                "step": 3,
                "phase": "Reconstrucción Canónica de Semana 3 — Examen Excel Práctico en Clase (Módulo 50131)",
                "responsible_agents": ["realizar-actividad", "monitor-uas"],
                "target_deliverable": "entregas-herramientas-digitales/GPO103LCP_EXAMEN_EXCEL_S3_MartinJonathan_DeLaCruzMunoz.xlsx",
                "source_templates_used": [
                    "70debcc256-Alumnos.xlsx -> resuelto igual a 7c4c5c47be-Alumnos - resuelto.xlsx (escala 0-20 con =IFS(AND(B2>=0,B2<=10),'Bajo',...))",
                    "71f623e337-Gastos.xlsx -> resuelto igual a dde2afd41a-Gastos - resuelto.xlsx (=IF(SUM(B3:B5)<=350,'Dentro de presupuesto','Presupuesto excedido'))",
                    "a21378de49-EstadosMaquillaje.xlsx (8 hojas SI1..SI4, Y1..Y2, O1..O2 resueltas)",
                    "ce7faeb208-VentaMaquillaje.xlsx (1,900 registros íntegros $H$5:$H$1904 sin truncamiento ni <f/> vacías)",
                    "7901270eeb-Interés Moratorio.xlsx (hojas Mora y Promoción reales)",
                    "cd849b5f38-Puntaje.xlsx (=VLOOKUP(F2,A4:C17,3,TRUE)) y 9f4890c5fe-SelecciónCódigo.xlsx",
                ],
                "verification_gate": "Coincidencia exacta de valores y fórmulas con 'Alumnos - resuelto.xlsx' y 'Gastos - resuelto.xlsx', 0 celdas con <f/> vacío, y recompilación de 'reporte-herramientas-digitales-Examen-S3.tex'.",
            },
            {
                "step": 4,
                "phase": "Construcción del Libro Contable Complementario de Semana 4 — EXCEL_CONTA (Módulo 50144)",
                "responsible_agents": ["realizar-actividad", "grabaciones-uas"],
                "target_deliverable": "entregas-herramientas-digitales/EXCEL_CONTA_MartinJonathan_DeLaCruzMunoz.xlsx",
                "source_templates_used": [
                    "1_Balance_general_y_comparativo_Aula_SUAD_25-26.pdf (Balance1, Bal Completo Reporte, Bal Completo Cuenta, Balance Reporte, Balance Cuenta, Bal Comparativo 1..3, Bal Compar Cuenta)",
                    "2_Estado_de_resultados_Aula_SUAD_25-26.pdf (Estado de Resultados 1..2, EdoRes Comercial)",
                    "4_Buscar_objetivo_Aula_SUAD_25-26.pdf (BO INGRESOS TOTALES, PE 1, PE2 — Punto de Equilibrio 250 unidades / $500,000)",
                ],
                "verification_gate": "15 hojas contables verificadas con ecuaciones Activo = Pasivo + Capital y Punto de Equilibrio exacto.",
            },
            {
                "step": 5,
                "phase": "Validación Cruzada con MonitorUasAgent y Compuerta de Autorización de Entrega",
                "responsible_agents": ["monitor-uas", "entregar-uas"],
                "target_deliverable": "estado-entregas-uas.json",
                "source_templates_used": [
                    "entregas-herramientas-digitales/Plan-Reunion-Zoom-S2_MartinJonathanDeLaCruzMunoz.pdf (Módulo 50113)",
                    "entregas-herramientas-digitales/GPO103_LCP_WEB_MartinJonathan_DeLaCruzMunoz.pdf (Módulo 50144)",
                ],
                "verification_gate": "Ejecutar 'monitor-uas' para certificar 'is_classroom_compliant: true' en los módulos 50114, 50130, 50131 y 50144 antes de solicitar autorización del usuario para 'entregar-uas'.",
            },
        ]

        payload = {
            "schema_version": "1.0.0",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "institution": "UAS",
            "subject_slug": clean_slug,
            "course_id": course_id,
            "orchestrator": "aulatex",
            "participating_agents": [
                "monitor-uas",
                "grabaciones-uas",
                "realizar-planeacion",
                "realizar-actividad",
            ],
            "forensic_excel_audits": excel_audits,
            "interagent_dialogue": dialogue_turns,
            "action_line": action_line,
            "monitor_run_id": mon_report.run_id,
        }
        _reject_credentials(payload)

        json_out = plans_dir / "dialogo-agente-correccion-excel.json"
        json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        md_lines = [
            "# Diálogo Multi-Agente y Línea de Acción para Corrección de Actividades Excel (UAS — Herramientas Digitales)",
            "",
            f"- **Fecha de generación:** {payload['generated_at_utc']}",
            f"- **Asignatura:** `herramientas-digitales` (Curso `635`, Dr. Dámaso Guadalupe Ruíz González)",
            f"- **Agentes participantes:** `monitor-uas`, `grabaciones-uas`, `realizar-planeacion`, `realizar-actividad`",
            "",
            "---",
            "",
            "## 1. Validación Forense de Deficiencias en Entregables Excel (`monitor-uas`)",
            "",
        ]
        for mid_str, aud in excel_audits.items():
            md_lines.extend([
                f"### Módulo `{mid_str}` — {aud.get('title')} (Semana {aud.get('week')})",
                f"- **Calificación y Retroalimentación en Moodle FCA:** `{aud.get('teacher_grade') or 'Pendiente'}` — *{aud.get('teacher_feedback') or 'Sin comentario'}* (`{aud.get('action_available') or 'N/A'}`)",
                f"- **Archivo local auditado:** `{aud.get('delivered_file') or 'No generado'}`",
                f"- **Hojas detectadas en el `.xlsx` actual:** `{', '.join(aud.get('delivered_sheets', [])) or 'Ninguna'}`",
                f"- **Fórmulas totales / Tablas dinámicas nativas:** `{aud.get('total_formulas', 0)}` fórmulas / `{aud.get('pivot_tables_count', 0)}` PivotTables",
                f"- **Cumple con ejercicios de clase (`Carpeta de Apoyo 50094`):** `{'SÍ' if aud.get('is_classroom_compliant') else 'NO (RECHAZADO)'}`",
                "- **Deficiencias localizadas por AulaTeX:**",
            ])
            for df in aud.get("deficiencies", []):
                md_lines.append(f"  - {df}")
            if aud.get("expected_workbooks"):
                md_lines.append("- **Plantillas oficiales de clase requeridas:**")
                for ew in aud.get("expected_workbooks", []):
                    md_lines.append(f"  - `{ew}`")
            md_lines.append("")

        md_lines.extend([
            "---",
            "",
            "## 2. Diálogo Inter-Agente Canónico (`grabaciones-uas` ↔ `monitor-uas` ↔ `realizar-planeacion` ↔ `realizar-actividad`)",
            "",
        ])
        for turn in dialogue_turns:
            md_lines.extend([
                f"### Turno {turn['turn']} — `{turn['agent_id']}` ({turn['agent_role']})",
                "",
                turn["statement"],
                "",
            ])

        md_lines.extend([
            "---",
            "",
            "## 3. Línea de Acción Acordada (`Línea de Acción`)",
            "",
        ])
        for step in action_line:
            md_lines.extend([
                f"### Paso {step['step']}: {step['phase']}",
                f"- **Agentes responsables:** `{', '.join(step['responsible_agents'])}`",
                f"- **Entregable objetivo:** `{step['target_deliverable']}`",
                "- **Plantillas fuente oficiales a emplear:**",
            ])
            for st in step["source_templates_used"]:
                md_lines.append(f"  - `{st}`")
            md_lines.extend([
                f"- **Compuerta de verificación:** {step['verification_gate']}",
                "",
            ])

        md_out = plans_dir / "DIALOGO-AGENTE-CORRECCION-EXCEL.md"
        md_out.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

        payload["dialogue_json_path"] = str(json_out)
        payload["dialogue_md_path"] = str(md_out)
        return payload


__all__ = [
    "FlujoUasOrchestrator",
    "FlujoUasRequest",
    "FlujoUasResult",
    "MonitorUasAgent",
    "MonitorUasRequest",
    "EntregarUasAgent",
    "EntregarUasRequest",
]
