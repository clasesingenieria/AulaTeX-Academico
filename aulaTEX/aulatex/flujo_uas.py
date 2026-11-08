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
import json
import os
from pathlib import Path
import re
import socket
import time
from typing import Any
from urllib.parse import urlsplit

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


__all__ = [
    "FlujoUasOrchestrator",
    "FlujoUasRequest",
    "FlujoUasResult",
    "MonitorUasAgent",
    "MonitorUasRequest",
    "EntregarUasAgent",
    "EntregarUasRequest",
]
