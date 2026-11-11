"""Agente ``monitor-unadm`` (tipo ``monitor-entregas``) para AulaTeX.

Supervisa el estado de entregas académicas en UnADM, consumiendo información
extraída por ``navegación-unadm`` / ``navegación-itesca`` (tipo ``navegación-plataforma``),
contrastándola con los artefactos locales del repositorio (planeaciones canónicas,
recursos clasificados, notas conceptuales y entregables en PDF), evaluando
los prerrequisitos satisfechos y bloqueos detectados, y emitiendo recomendaciones
verificables al orquestador ``aulatex``.

Garantiza aislamiento total de credenciales y ausencia de fugas de secretos.
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
from .navegacion_plataforma import (
    AGENT_TYPE_NAVEGACION_PLATAFORMA,
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
from .realizar_planeacion_unadm import UNADM_SUBJECTS_CATALOG
from .workspace import AulaTeXWorkspace

AGENT_ID_MONITOR_UNADM = "monitor-unadm"


@dataclass(frozen=True)
class MonitorUnadmRequest:
    subject_slug: str
    activity_number: int | None = None
    course_id: int | None = None
    module_id: int | None = None
    nav_snapshot: dict[str, Any] | None = None
    inspect_platform: bool = False
    output_dir: str = ""


class MonitorUnadmAgent(MonitorEntregasAgent):
    """Agente de monitoreo de entregas de UnADM bajo coordinación de aulatex."""

    agent_id: str = AGENT_ID_MONITOR_UNADM
    agent_type: str = AGENT_TYPE_MONITOR_ENTREGAS

    def __init__(
        self,
        workspace: AulaTeXWorkspace | None = None,
        nav_agent: NavegacionUnadmAgent | None = None,
    ) -> None:
        super().__init__(workspace=workspace)
        self.nav_agent = nav_agent or NavegacionUnadmAgent(self.workspace, agent_id=AGENT_ID_NAVEGACION_ITESCA)
        if self.nav_agent.agent_type != AGENT_TYPE_NAVEGACION_PLATAFORMA:
            raise ValueError(
                f"Contrato inválido: el agente de navegación debe ser de tipo {AGENT_TYPE_NAVEGACION_PLATAFORMA}."
            )
        self.runs_root = self.workspace.feedback_root / "monitor-unadm" / "runs"
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

    def _locate_deliverable_artifact(self, subject_root: Path, activity_number: int) -> tuple[Path | None, str | None]:
        """Localiza el artefacto PDF entregable en entregas-<slug>/ y calcula su SHA-256."""
        layout = subject_layout(subject_root)
        deliveries_dir = layout.get("deliveries")
        if not deliveries_dir or not deliveries_dir.is_dir():
            return None, None

        # Patrones canónicos de entregables en el proyecto UnADM:
        # Actividad-S4-*.pdf, Actividad-04-*.pdf, Actividad-4-*.pdf
        patterns = [
            f"Actividad-S{activity_number}-*.pdf",
            f"Actividad-S{activity_number}.pdf",
            f"Actividad-{activity_number:02d}-*.pdf",
            f"Actividad-{activity_number:02d}.pdf",
            f"Actividad-{activity_number}-*.pdf",
            f"Actividad-{activity_number}.pdf",
        ]
        for pat in patterns:
            matches = sorted(deliveries_dir.glob(pat))
            if matches:
                pdf_path = matches[0]
                digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
                return pdf_path, digest

        return None, None

    def _locate_forum_artifact(self, subject_root: Path, activity_number: int) -> tuple[Path | None, str | None]:
        """Localiza un borrador o comprobante de participación en foro."""
        layout = subject_layout(subject_root)
        notes_dir = layout.get("notes")
        if notes_dir and notes_dir.is_dir():
            for adir in notes_dir.glob(f"*0*{activity_number}*"):
                if not adir.is_dir():
                    continue
                for cand in adir.glob("*.txt"):
                    if any(w in cand.stem.lower() for w in ("participacion", "foro", "replica")):
                        digest = hashlib.sha256(cand.read_bytes()).hexdigest()
                        return cand, digest
                for cand in adir.glob("*.md"):
                    if any(w in cand.stem.lower() for w in ("participacion", "foro", "seguimiento")):
                        digest = hashlib.sha256(cand.read_bytes()).hexdigest()
                        return cand, digest

        return None, None

    def _check_delivered_in_manifests(self, subject_slug: str, activity_number: int) -> bool:
        """Comprueba si la actividad ya fue enviada formalmente según los manifiestos de entregas previas."""
        delivery_runs = self.workspace.feedback_root / "entregar-unadm" / "runs"
        if not delivery_runs.is_dir():
            return False
        for m_file in delivery_runs.glob("**/manifest.json"):
            try:
                data = json.loads(m_file.read_text(encoding="utf-8"))
                for d in data.get("deliveries", []):
                    if (
                        d.get("subject") == subject_slug
                        and int(d.get("activity_number", -1)) == int(activity_number)
                        and d.get("platform_submission_performed") is True
                    ):
                        return True
            except Exception:
                continue
        return False

    def evaluate_activity(
        self,
        subject_slug: str,
        activity_number: int,
        course_id: int | None = None,
        module_id: int | None = None,
        nav_snapshot: dict[str, Any] | None = None,
        module_snapshot: dict[str, Any] | None = None,
    ) -> DeliveryRecommendation:
        """Evalúa el estado de una actividad y emite recomendación técnica a aulatex."""
        base_slug = subject_slug.replace("-lde", "").strip()
        subject_root = self._resolve_subject_root(base_slug)
        layout = subject_layout(subject_root)

        satisfied: list[str] = []
        blockers: list[dict[str, Any]] = []

        # 1. Comprobar planeación canónica
        plans_dir = layout.get("plans")
        plan_found = False
        if plans_dir and plans_dir.is_dir():
            candidates = [
                plans_dir / f"planeacion-{base_slug}-Actividad-{activity_number}.json",
                plans_dir / f"planeacion-canonica-actividad-{activity_number:02d}.json",
                plans_dir / f"planeacion-canonica-actividad-{activity_number}.json",
            ]
            for c in candidates:
                if c.is_file():
                    try:
                        pdata = json.loads(c.read_text(encoding="utf-8-sig"))
                        if pdata.get("schema_version") == "1.0.0":
                            plan_found = True
                            satisfied.append("planeacion_canonica_verificada")
                            break
                    except Exception:
                        pass
        if not plan_found:
            blockers.append({
                "code": "falta_planeacion",
                "detail": f"Falta planeación canónica PCA v1.0.0 para actividad {activity_number}",
                "blocking": True,
            })

        # 2. Comprobar recursos organizados
        ref_dir = layout.get("references")
        notes_dir = layout.get("notes")
        resources_found = False

        # Buscar en carpetas de notas de la actividad
        if notes_dir and notes_dir.is_dir():
            act_patterns = [
                f"actividad-{activity_number:02d}-*",
                f"actividad-{activity_number}-*",
            ]
            for pat in act_patterns:
                for adir in notes_dir.glob(pat):
                    if not adir.is_dir():
                        continue
                    if (adir / "recursos-actividad.json").is_file() or (adir / f"recursos-actividad-{activity_number}-manifest.json").is_file():
                        resources_found = True
                        break
                    corpus_sub = adir / "corpus-extractor"
                    mat_sub = adir / "material-docente"
                    if (corpus_sub.is_dir() and any(corpus_sub.iterdir())) or (mat_sub.is_dir() and any(mat_sub.iterdir())):
                        resources_found = True
                        break
                if resources_found:
                    break

        # Buscar en raíz de referencias
        if not resources_found and ref_dir and ref_dir.is_dir():
            manifest_candidates = [
                ref_dir / f"recursos-actividad-{activity_number}-manifest.json",
                ref_dir / f"recursos-actividad-{activity_number}.json",
                ref_dir / "inventario-referencias.json",
                ref_dir / "inventario-aula.json",
            ]
            corpus_candidates = [
                ref_dir / f"corpus-actividad-{activity_number:02d}",
                ref_dir / f"corpus-actividad-{activity_number}",
                ref_dir / "corpus-extractor",
            ]
            for mc in manifest_candidates:
                if mc.is_file():
                    resources_found = True
                    break
            if not resources_found:
                for cc in corpus_candidates:
                    if cc.is_dir() and any(cc.iterdir()):
                        resources_found = True
                        break

        if resources_found:
            satisfied.append("recursos_organizados_verificados")
        else:
            blockers.append({
                "code": "falta_recursos",
                "detail": f"Faltan recursos organizados en corpus para actividad {activity_number}",
                "blocking": True,
            })

        # 3. Comprobar notas y conceptos extraídos
        notes_dir = layout.get("notes")
        concepts_found = False
        if notes_dir and notes_dir.is_dir():
            # Buscar carpeta de notas de la actividad
            act_patterns = [
                f"actividad-{activity_number:02d}-*",
                f"actividad-{activity_number}-*",
            ]
            for pat in act_patterns:
                matching_dirs = [d for d in notes_dir.glob(pat) if d.is_dir()]
                for md in matching_dirs:
                    if any(md.glob("*.json")) or any(md.glob("*.md")):
                        concepts_found = True
                        break
                if concepts_found:
                    break
        if concepts_found:
            satisfied.append("conceptos_extraidos_verificados")
        else:
            blockers.append({
                "code": "falta_conceptos",
                "detail": f"Faltan notas de conceptos procesados para actividad {activity_number}",
                "blocking": True,
            })

        # 4. Comprobar entregable local en entregas-<slug>/
        pdf_path, pdf_sha256 = self._locate_deliverable_artifact(subject_root, activity_number)
        if pdf_path is not None and pdf_sha256 is not None:
            satisfied.append("entregable_local_compilado")
        else:
            cat_info = UNADM_SUBJECTS_CATALOG.get(base_slug, {}).get("activities", {}).get(activity_number, {})
            if cat_info.get("kind") == "forum":
                forum_path, forum_sha = self._locate_forum_artifact(subject_root, activity_number)
                if forum_path is not None and forum_sha is not None:
                    satisfied.append("borrador_foro_verificado")
                    pdf_path = forum_path
                    pdf_sha256 = forum_sha

        # 5. Comprobar estado en plataforma y manifiestos de envíos previos
        platform_status = "sin_inspeccion_remota"
        active_snapshot = module_snapshot
        if active_snapshot is None and nav_snapshot is not None:
            active_snapshot = nav_snapshot.get("modules", {}).get(str(module_id))

        already_delivered_manifest = self._check_delivered_in_manifests(base_slug, activity_number)

        if active_snapshot is not None:
            full_text = active_snapshot.get("full_main_text", "") + " " + active_snapshot.get("intro_text", "")
            lower_text = full_text.lower()
            is_submitted = (
                "enviado para calificar" in lower_text
                or "calificado" in lower_text
                or "hecho: hacer un envío" in lower_text
                or "hecho: hacer publicaciones en foro" in lower_text
                or "hecho: hacer publicaciones" in lower_text
            )
            is_draft = "borrador (no enviado)" in lower_text
            is_pending = (
                "por hacer: hacer un envío" in lower_text
                or "por hacer: hacer publicaciones" in lower_text
                or "aun no se ha hecho ninguna tarea" in lower_text
                or "aún no se ha hecho ninguna tarea" in lower_text
                or "no se ha entregado nada" in lower_text
                or "añadir envío" in lower_text
            )

            if is_submitted and not is_draft:
                platform_status = "entregado_en_plataforma"
            elif is_draft:
                platform_status = "Borrador (no enviado)"
            elif is_pending:
                platform_status = "pendiente_de_envio"
            else:
                platform_status = "pendiente_o_no_registrado"

        # 6. Formular recomendación técnica para aulatex
        recommended_action = "bloqueado_falta_prerrequisitos"
        rationale = ""
        proposed_artifact = str(pdf_path) if pdf_path else None
        proposed_sha = pdf_sha256

        if platform_status in ("entregado_en_plataforma", "Enviado para calificar"):
            recommended_action = "ya_entregado"
            rationale = "La actividad ya fue enviada previamente y se encuentra en estado 'Enviado para calificar' en la plataforma UnADM."
            blockers.append({
                "code": "actividad_ya_enviada",
                "detail": "La actividad ya cuenta con envío registrado en la plataforma virtual.",
                "blocking": False,
            })
        elif "entregable_local_compilado" in satisfied or "borrador_foro_verificado" in satisfied:
            # Si el entregable local está listo y no ha sido entregado a la plataforma, queda a la espera de autorización
            recommended_action = "esperar-autorizacion-entrega"
            rationale = (
                f"El artefacto entregable está compilado en {pdf_path.name} (SHA-256: {pdf_sha256[:12]}...). "
                "Queda pendiente de validación explícita del usuario; autorizar la realización no equivale a autorizar su envío."
            )
        elif "planeacion_canonica_verificada" in satisfied and "recursos_organizados_verificados" in satisfied and "conceptos_extraidos_verificados" in satisfied:
            recommended_action = "solicitar-realizar-actividad"
            rationale = (
                "Se verificaron todos los prerrequisitos necesarios: planeación canónica PCA v1.0.0, "
                "recursos recopilados en corpus y conceptos extraídos en notas. "
                "Se recomienda al orquestador aulatex autorizar y canalizar la ejecución de realizar-actividad."
            )
        else:
            missing = [b["code"] for b in blockers if b.get("blocking", False)]
            recommended_action = "bloqueado_falta_prerrequisitos"
            rationale = f"Existen prerrequisitos insatisfechos que bloquean la realización: {', '.join(missing)}."

        recommendation = DeliveryRecommendation(
            institution="UnADM",
            subject_slug=base_slug,
            activity_number=activity_number,
            recommended_action=recommended_action,
            prerequisites_satisfied=tuple(satisfied),
            blockers=tuple(blockers),
            rationale=rationale,
            proposed_delivery_artifact=proposed_artifact,
            proposed_delivery_sha256=proposed_sha,
        )
        assert_no_credential_leak(asdict(recommendation))
        return recommendation

    def monitor_deliveries(self, request: MonitorUnadmRequest) -> PendingSubmissionsReport:
        """Inspecciona y compila el informe general de entregas de la asignatura."""
        run_id = f"{self.workspace.timestamp()}-monitor-unadm"
        run_dir = (
            self.workspace.resolve_target(request.output_dir)
            if request.output_dir.strip()
            else self.runs_root / run_id
        )
        run_dir.mkdir(parents=True, exist_ok=True)

        base_slug = request.subject_slug.replace("-lde", "").strip()
        catalog_entry = UNADM_SUBJECTS_CATALOG.get(base_slug, {})
        cid = request.course_id or catalog_entry.get("course_id") or 3482

        nav_snapshot: dict[str, Any] | None = request.nav_snapshot
        overall_blockers: list[dict[str, Any]] = []

        if request.inspect_platform and nav_snapshot is None:
            try:
                mod_targets_list: list[UnadmModuleTarget] = []
                if request.module_id and request.activity_number:
                    mod_targets_list.append(
                        UnadmModuleTarget(
                            module_id=request.module_id,
                            course_id=cid,
                            local_activity_number=request.activity_number,
                            subject_slug=base_slug,
                        )
                    )
                else:
                    for act_k, act_info in catalog_entry.get("activities", {}).items():
                        mid_val = act_info.get("module_id")
                        if mid_val:
                            mod_targets_list.append(
                                UnadmModuleTarget(
                                    module_id=int(mid_val),
                                    kind=act_info.get("kind", "assign"),
                                    course_id=cid,
                                    local_activity_number=int(act_k),
                                    subject_slug=base_slug,
                                )
                            )
                nav_req = UnadmNavigationRequest(
                    inspect_dashboard=False,
                    course_ids=(cid,),
                    modules=tuple(mod_targets_list),
                    output_dir=str(run_dir / "navegacion"),
                )
                nav_res = self.nav_agent.inspect(nav_req)
                nav_snapshot = nav_res.snapshot
                if nav_res.blockers:
                    overall_blockers.extend(nav_res.blockers)
            except Exception as exc:
                overall_blockers.append({
                    "stage": "monitor_unadm_nav",
                    "code": "platform_inspection_failed",
                    "detail": str(exc),
                    "blocking": False,
                })

        # Descubrimiento dinámico de actividades a evaluar
        activities_to_eval: list[int] = []
        if request.activity_number:
            activities_to_eval = [request.activity_number]
        else:
            discovered_acts: set[int] = set()

            # 1. Catálogo institucional
            for act_k in catalog_entry.get("activities", {}).keys():
                try:
                    discovered_acts.add(int(act_k))
                except (ValueError, TypeError):
                    pass

            # 2. Artefactos locales existentes en el repositorio
            subject_root_loc = self._resolve_subject_root(base_slug)
            layout_loc = subject_layout(subject_root_loc)
            plans_dir = layout_loc.get("plans")
            if plans_dir and plans_dir.is_dir():
                for p_file in plans_dir.glob("*.json"):
                    m = re.search(r"[Aa]ctividad[-_](\d+)", p_file.stem)
                    if m:
                        discovered_acts.add(int(m.group(1)))
                orig_dir = plans_dir / "originales-docentes"
                if orig_dir.is_dir():
                    for o_file in orig_dir.glob("*"):
                        m = re.search(r"[Ss](\d+)", o_file.name)
                        if m:
                            discovered_acts.add(int(m.group(1)))

            deliv_dir = layout_loc.get("deliveries")
            if deliv_dir and deliv_dir.is_dir():
                for d_file in deliv_dir.glob("*.pdf"):
                    m = re.search(r"[Aa]ctividad-S?(\d+)", d_file.name)
                    if m:
                        discovered_acts.add(int(m.group(1)))

            notes_dir = layout_loc.get("notes")
            if notes_dir and notes_dir.is_dir():
                for n_dir in notes_dir.glob("actividad-*"):
                    m = re.search(r"actividad-(\d+)", n_dir.name)
                    if m:
                        discovered_acts.add(int(m.group(1)))

            # 3. Snapshot de navegación o módulos de la plataforma
            if nav_snapshot and "modules" in nav_snapshot:
                for mod_data in nav_snapshot["modules"].values():
                    t = mod_data.get("title", "") + " " + mod_data.get("name", "")
                    m = re.search(r"[Aa]ctividad\s*(\d+)", t)
                    if m:
                        discovered_acts.add(int(m.group(1)))
                    m_s = re.search(r"[Ss](\d+)", t)
                    if m_s:
                        discovered_acts.add(int(m_s.group(1)))

            # 4. Secciones del curso en la plataforma (detectar semanas activas, ej. section-8 / Semana 7)
            if nav_snapshot and "courses" in nav_snapshot and str(cid) in nav_snapshot["courses"]:
                c_sections = nav_snapshot["courses"][str(cid)].get("sections", [])
                for sec in c_sections:
                    for ln in sec.get("links", []):
                        lt = ln.get("title", "")
                        m = re.search(r"[Aa]ctividad\s*(\d+)", lt)
                        if m:
                            discovered_acts.add(int(m.group(1)))
                        m_s = re.search(r"[Ss](\d+)", lt)
                        if m_s:
                            discovered_acts.add(int(m_s.group(1)))

            if not discovered_acts:
                discovered_acts = set(range(1, 10))
            else:
                # Asegurar evaluación de la semana activa actual (Semana 7)
                if base_slug == "antecedentes-de-los-derechos-humanos":
                    discovered_acts.add(9)
                elif base_slug in ("teoria-del-estado-y-constitucion", "derecho-penal-especial-mexicano"):
                    discovered_acts.add(7)

            activities_to_eval = sorted(discovered_acts)
        pending_items: list[PendingDeliveryItem] = []
        recommendations: list[DeliveryRecommendation] = []

        subject_root = self._resolve_subject_root(base_slug)

        for act in activities_to_eval:
            mod_snap = None
            act_cat = catalog_entry.get("activities", {}).get(act, {})
            act_mid = request.module_id or act_cat.get("module_id")
            if nav_snapshot and act_mid and str(act_mid) in nav_snapshot.get("modules", {}):
                mod_snap = nav_snapshot["modules"][str(act_mid)]

            rec = self.evaluate_activity(
                subject_slug=base_slug,
                activity_number=act,
                course_id=cid,
                module_id=act_mid,
                nav_snapshot=nav_snapshot,
                module_snapshot=mod_snap,
            )
            recommendations.append(rec)

            pdf_path, pdf_sha = self._locate_deliverable_artifact(subject_root, act)

            item = PendingDeliveryItem(
                institution="UnADM",
                subject_slug=base_slug,
                activity_number=act,
                activity_title=act_cat.get("title", f"Actividad {act}"),
                module_id=act_mid,
                course_id=cid,
                platform_status="Enviado para calificar" if rec.recommended_action == "ya_entregado" else "pendiente_o_borrador",
                due_date=None,
                local_planning_ready="planeacion_canonica_verificada" in rec.prerequisites_satisfied,
                local_resources_ready="recursos_organizados_verificados" in rec.prerequisites_satisfied,
                local_concepts_ready="conceptos_extraidos_verificados" in rec.prerequisites_satisfied,
                local_deliverable_ready=pdf_path is not None,
                local_deliverable_path=str(pdf_path) if pdf_path else None,
                local_deliverable_sha256=pdf_sha,
                satisfied_requirements=rec.prerequisites_satisfied,
                detected_blockers=rec.blockers,
            )
            pending_items.append(item)

        # Generar manifiesto JSON
        manifest: dict[str, Any] = {
            "schema_version": "1.0.0",
            "run_id": run_id,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "institution": "UnADM",
            "subject_slug": base_slug,
            "course_id": cid,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "pending_deliveries": [asdict(item) for item in pending_items],
            "recommendations": [asdict(r) for r in recommendations],
            "blockers": overall_blockers,
        }
        assert_no_credential_leak(manifest)
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        # Generar resumen legible Markdown
        summary_lines = [
            f"# Informe de Monitoreo de Entregas UnADM (`{self.agent_id}`)",
            "",
            f"- **Institución:** UnADM",
            f"- **Asignatura:** `{base_slug}` (Curso {cid})",
            f"- **Fecha:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "## Estado y Recomendaciones por Actividad",
            "",
            "| Actividad | Estado Plataforma | Prerrequisitos Satisfechos | Entregable Local | Acción Recomendada |",
            "|---|---|---|---|---|",
        ]
        for it, r in zip(pending_items, recommendations):
            deliv_badge = f"`{Path(it.local_deliverable_path).name}`" if it.local_deliverable_ready and it.local_deliverable_path else "No generado"
            prereqs_str = ", ".join(r.prerequisites_satisfied) if r.prerequisites_satisfied else "Ninguno"
            summary_lines.append(
                f"| Actividad {it.activity_number} | {it.platform_status} | {prereqs_str} | {deliv_badge} | **{r.recommended_action}** |"
            )

        summary_lines.extend(["", "## Rationale Técnico para aulatex", ""])
        for r in recommendations:
            summary_lines.append(f"- **Actividad {r.activity_number}:** {r.rationale}")
            if r.proposed_delivery_artifact:
                summary_lines.append(f"  - *Artefacto propuesto:* `{r.proposed_delivery_artifact}` (SHA-256: `{r.proposed_delivery_sha256}`)")

        summary_md = "\n".join(summary_lines) + "\n"
        assert_no_credential_leak(summary_md)
        summary_md_path = run_dir / "resumen-monitoreo.md"
        summary_md_path.write_text(summary_md, encoding="utf-8")

        return PendingSubmissionsReport(
            run_id=run_id,
            run_dir=run_dir,
            institution="UnADM",
            timestamp_utc=manifest["timestamp_utc"],
            pending_deliveries=tuple(pending_items),
            recommendations=tuple(recommendations),
            blockers=tuple(overall_blockers),
            manifest_path=manifest_path,
            summary_md_path=summary_md_path,
        )


# Registrar monitor institucional UnADM
register_delivery_monitor("UnADM", MonitorUnadmAgent)
register_delivery_monitor("unadmexico", MonitorUnadmAgent)

__all__ = [
    "AGENT_ID_MONITOR_UNADM",
    "MonitorUnadmAgent",
    "MonitorUnadmRequest",
]
