from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from .activity_contract import DIDACTIC_TECHNIQUE_CONTRACTS, REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT
from .progress import NullProgressReporter, ProgressReporter
from .workspace import AulaTeXWorkspace

# Acciones que el ejecutor del motor inteligente sabe correr en proceso.
_SUPPORTED_EXEC_ACTIONS = ("construir-memoria-editorial", "realizar-actividad")


@dataclass(frozen=True)
class IntelligentEngineRequest:
    target: str = "."
    activity_number: int = 0
    output: str = ""
    backend: Literal["langgraph", "classic"] = "langgraph"
    max_targets: int = 12
    audit_path: str = ""
    include_reports: bool = True
    include_presentations: bool = True
    engines: tuple[str, ...] = ("Auto (model-router)",)
    # Ejecución observable: si es True el motor no solo planifica, sino que
    # ejecuta las acciones recomendadas (realizar-actividad, memoria editorial)
    # emitiendo progreso. Ver IntelligentEngine.execute().
    execute: bool = False
    actions: tuple[str, ...] = ("realizar-actividad", "construir-memoria-editorial")
    # Un ciclo monitorizado y luego convergencia de calidad a 100 (0).
    monitor_max_cycles: int = 1
    optimize_cycles: int = 0


@dataclass(frozen=True)
class IntelligentEngineResult:
    ok: bool
    run_id: str
    run_dir: Path
    manifest_path: Path
    report_path: Path
    executed: bool = False
    execution_ok: bool | None = None
    execution_summary: dict[str, Any] = field(default_factory=dict)


class IntelligentEngine:
    """Planificador v1 del motor inteligente editorial.

    Las corridas operativas se guardan en .aulatex-temp para evitar versionar
    manifests, reportes y colas intermedias. La documentación estable debe vivir
    fuera de esta carpeta si se quiere conservar.
    """

    def __init__(self, workspace: AulaTeXWorkspace | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.root = self.workspace.temp_root / "intelligent-engine" / "runs"
        self.root.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        request: IntelligentEngineRequest,
        reporter: ProgressReporter | None = None,
    ) -> IntelligentEngineResult:
        reporter = reporter or NullProgressReporter()
        reporter.progress(2, "Resolviendo alcance del motor inteligente...")
        run_id = f"{self.workspace.timestamp()}-intelligent-engine"
        run_dir = self._resolve_run_dir(request, run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        scope = self.workspace.find_scope_for_target(
            request.target,
            activity_number=request.activity_number or None,
        )
        target_root = self.workspace.resolve_target(request.target)
        target_root_relative = self.workspace.relative(target_root)
        reporter.progress(6, "Inventariando documentos LaTeX...")
        inventory = self._collect_tex_inventory(request, target_root)
        audit_payload = self._load_audit_payload(request.audit_path)
        issues_by_target = self._group_audit_issues(audit_payload, target_root_relative)
        audit_status = self._audit_status(request.audit_path, audit_payload, issues_by_target)
        reporter.progress(10, f"Priorizando objetivos ({len(inventory)} .tex detectados)...")
        plans = self._build_target_plans(request, inventory, issues_by_target)

        manifest = {
            "kind": "intelligent-engine",
            "version": 1,
            "run_id": run_id,
            "request": {
                **asdict(request),
                "engines": list(request.engines),
            },
            "scope": {
                "resolved": scope is not None,
                "scope_key": scope.key if scope else "",
                "scope_level": scope.level if scope else "",
                "scope_label": scope.label if scope else "",
                "target_root": target_root_relative,
            },
            "architecture": self._build_architecture_contract(request),
            "graph_contract": self._build_graph_contract(request),
            "realizar_actividad_contract": self._build_realizar_actividad_contract(),
            "audit_status": audit_status,
            "inventory_summary": {
                "tex_total": len(inventory),
                "report_total": sum(1 for item in inventory if item["tex_kind"] == "report"),
                "presentation_total": sum(1 for item in inventory if item["tex_kind"] == "presentation"),
                "audit_targets": len(issues_by_target),
                "planned_targets": len(plans),
            },
            "targets": plans,
        }
        manifest_path = run_dir / "manifest.json"
        report_path = run_dir / "report.md"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        report_path.write_text(self._build_markdown_report(manifest), encoding="utf-8")
        reporter.progress(15, f"Plan listo: {len(plans)} objetivo(s) priorizado(s).")

        executed = False
        execution_ok: bool | None = None
        execution_summary: dict[str, Any] = {}
        if request.execute:
            executed = True
            execution_ok, execution_summary = self._execute_plan(
                request, plans, run_dir, reporter
            )
            manifest["execution"] = execution_summary
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            reporter.result(
                "success" if execution_ok else "error",
                "Ejecución del motor inteligente completada."
                if execution_ok
                else "Ejecución del motor inteligente con incidencias.",
            )
        else:
            reporter.result("success", "Plan del motor inteligente generado (sin ejecutar).")

        return IntelligentEngineResult(
            ok=True if not executed else bool(execution_ok),
            run_id=run_id,
            run_dir=run_dir,
            manifest_path=manifest_path,
            report_path=report_path,
            executed=executed,
            execution_ok=execution_ok,
            execution_summary=execution_summary,
        )

    # ------------------------------------------------------------------
    # Ejecución observable del plan (no solo planificación)
    # ------------------------------------------------------------------
    def _execute_plan(
        self,
        request: IntelligentEngineRequest,
        plans: list[dict[str, Any]],
        run_dir: Path,
        reporter: ProgressReporter,
    ) -> tuple[bool, dict[str, Any]]:
        """Ejecuta las acciones seleccionadas sobre cada objetivo priorizado.

        Acciones soportadas (``request.actions``):
        * ``realizar-actividad`` → AulaTeXAgent con post-proceso monitor+optimize.
        * ``construir-memoria-editorial`` → EditorialMemoryBuilder sobre el scope.

        Cada objetivo consume una fracción homogénea del rango 15→100 % para que
        el lanzador pinte una barra global coherente. Se emiten ``::stage::`` por
        objetivo y ``::notice::``/``::result::`` por acción.
        """

        actionable = [
            plan
            for plan in plans
            if int(plan.get("activity_number") or 0) > 0
            and str(plan.get("tex_kind")) in {"report", "presentation"}
        ]
        summary: dict[str, Any] = {
            "requested_actions": list(request.actions),
            "planned_targets": len(plans),
            "actionable_targets": len(actionable),
            "targets": [],
            "ok": True,
        }

        if not actionable:
            reporter.notice("No hay objetivos con actividad ejecutable en el plan.")
            summary["ok"] = True
            return True, summary

        base, span = 15.0, 85.0
        total = len(actionable)
        overall_ok = True

        for index, plan in enumerate(actionable):
            target = str(plan["target"])
            directory = str(plan["directory"])
            activity = int(plan.get("activity_number") or 0)
            stage_id = f"target-{index + 1:02d}"
            reporter.stage(stage_id, f"{Path(directory).name} · Actividad {activity}")
            reporter.progress(
                base + span * (index / total),
                f"[{index + 1}/{total}] {Path(directory).name} · Actividad {activity}",
            )

            target_record: dict[str, Any] = {
                "target": target,
                "directory": directory,
                "activity_number": activity,
                "actions": [],
                "ok": True,
            }

            action_slots = [a for a in request.actions if a in _SUPPORTED_EXEC_ACTIONS]
            action_span = span / total / max(1, len(action_slots))

            for action_pos, action_id in enumerate(action_slots):
                sub_base = base + span * (index / total) + action_span * action_pos
                action_ok, action_detail = self._run_single_action(
                    action_id,
                    request,
                    target=target,
                    directory=directory,
                    activity=activity,
                    run_dir=run_dir / stage_id,
                    reporter=reporter,
                    progress_base=sub_base,
                    progress_span=action_span,
                )
                target_record["actions"].append(action_detail)
                if not action_ok:
                    target_record["ok"] = False
                    overall_ok = False

            summary["targets"].append(target_record)
            reporter.result(
                "success" if target_record["ok"] else "warning",
                f"{Path(directory).name} · Actividad {activity} "
                f"({'OK' if target_record['ok'] else 'con incidencias'})",
            )

        reporter.progress(100, "Motor inteligente: ejecución de objetivos finalizada.")
        summary["ok"] = overall_ok
        return overall_ok, summary

    def _run_single_action(
        self,
        action_id: str,
        request: IntelligentEngineRequest,
        *,
        target: str,
        directory: str,
        activity: int,
        run_dir: Path,
        reporter: ProgressReporter,
        progress_base: float,
        progress_span: float,
    ) -> tuple[bool, dict[str, Any]]:
        run_dir.mkdir(parents=True, exist_ok=True)
        started = time.time()
        reporter.progress(progress_base, f"→ {action_id}: {Path(directory).name} A{activity}")

        try:
            if action_id == "construir-memoria-editorial":
                ok, extra = self._exec_editorial_memory(
                    request, directory, activity, run_dir, reporter, progress_base, progress_span
                )
            elif action_id == "realizar-actividad":
                ok, extra = self._exec_realizar_actividad(
                    request, target, directory, activity, run_dir, reporter, progress_base, progress_span
                )
            else:
                reporter.notice(f"Acción no soportada por el ejecutor: {action_id}")
                return True, {"action": action_id, "ok": True, "skipped": True}
        except Exception as error:  # noqa: BLE001 - reportar sin abortar la campaña
            reporter.result("error", f"{action_id} falló: {error}")
            return False, {
                "action": action_id,
                "ok": False,
                "error": str(error),
                "elapsed_s": round(time.time() - started, 1),
            }

        elapsed = round(time.time() - started, 1)
        reporter.result(
            "success" if ok else "warning",
            f"{action_id} {'OK' if ok else 'con incidencias'} ({elapsed}s)",
        )
        return ok, {"action": action_id, "ok": ok, "elapsed_s": elapsed, **extra}

    def _exec_editorial_memory(
        self,
        request: IntelligentEngineRequest,
        directory: str,
        activity: int,
        run_dir: Path,
        reporter: ProgressReporter,
        progress_base: float,
        progress_span: float,
    ) -> tuple[bool, dict[str, Any]]:
        from .editorial_memory import (
            EditorialMemoryBuilder,
            EditorialMemoryEvent,
            EditorialMemoryRequest,
        )

        scope = self.workspace.find_scope_for_target(directory, activity_number=activity or None)
        if scope is None:
            reporter.notice(f"Sin scope editorial resoluble para {Path(directory).name}; se omite memoria.")
            return True, {"skipped": True, "reason": "scope-no-resuelto"}

        reporter.notice(f"Construyendo memoria editorial (materia) para {scope.label}...")
        builder = EditorialMemoryBuilder(self.workspace)

        def _on_event(event: EditorialMemoryEvent) -> None:
            if event.total:
                frac = min(1.0, event.current / max(1, event.total))
                reporter.progress(
                    progress_base + progress_span * frac,
                    f"Memoria editorial: {event.message}",
                )
            if event.kind in {"scope", "error", "start"}:
                reporter.notice(event.message)

        result = builder.build(
            EditorialMemoryRequest(
                source_scope_key=scope.key,
                build_level="materia",
                propagation_mode="local",
                engines=tuple(request.engines),
            ),
            progress=_on_event,
        )
        reporter.progress(progress_base + progress_span * 0.95, "Memoria editorial persistida.")
        return bool(getattr(result, "ok", False)), {
            "scope_key": scope.key,
            "built_scopes": list(getattr(result, "built_scopes", ())),
            "run_dir": self.workspace.relative(getattr(result, "run_dir", run_dir)),
        }

    def _exec_realizar_actividad(
        self,
        request: IntelligentEngineRequest,
        target: str,
        directory: str,
        activity: int,
        run_dir: Path,
        reporter: ProgressReporter,
        progress_base: float,
        progress_span: float,
    ) -> tuple[bool, dict[str, Any]]:
        from .agent import AgentRequest, AulaTeXAgent

        reporter.notice(
            f"realizar-actividad A{activity} (incluye detail-planner + monitor + optimize)..."
        )
        reporter.progress(progress_base + progress_span * 0.15, "Redactando y evaluando actividad...")
        agent = AulaTeXAgent(self.workspace)
        result = agent.run(
            AgentRequest(
                # Conservar el objetivo exacto: una presentación no debe degradarse
                # a la carpeta de la materia ni terminar en un reporte distinto.
                target=target,
                level="actividad",
                action="realizar-actividad",
                activity_number=activity,
                engines=list(request.engines),
                run_monitor=True,
                run_optimize=True,
                monitor_max_cycles=int(request.monitor_max_cycles),
                optimize_cycles=int(request.optimize_cycles),
                    semantic_feedback_path=request.audit_path,
            )
        )
        reporter.progress(
            progress_base + progress_span * 0.9,
            f"Actividad terminada (monitor={result.monitor_ok}, optimize={result.optimize_ok}, "
            f"compile={getattr(result, 'final_compile_ok', None)}).",
        )
        return bool(getattr(result, "ok", False)), {
            "run_dir": self.workspace.relative(getattr(result, "run_dir", run_dir)),
            "monitor_ok": getattr(result, "monitor_ok", None),
            "optimize_ok": getattr(result, "optimize_ok", None),
            "quality_before": getattr(result, "quality_before", None),
            "quality_after": getattr(result, "quality_after", None),
            "optimize_plan_summary": getattr(result, "optimize_plan_summary", None),
            "final_compile_ok": getattr(result, "final_compile_ok", None),
            "semantic_blocking_before": getattr(result, "semantic_blocking_before", None),
            "semantic_blocking_after": getattr(result, "semantic_blocking_after", None),
            "semantic_audit_available": getattr(result, "semantic_audit_available", None),
        }

    def _resolve_run_dir(self, request: IntelligentEngineRequest, run_id: str) -> Path:
        if request.output:
            candidate = Path(request.output)
            if not candidate.is_absolute():
                candidate = self.workspace.repo_root / candidate
            return candidate.resolve()
        return self.root / run_id

    def _collect_tex_inventory(self, request: IntelligentEngineRequest, target_root: Path) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        if target_root.is_file() and target_root.suffix.lower() == ".tex":
            tex_candidates = [target_root]
        elif target_root.exists() and target_root.is_dir():
            tex_candidates = sorted(target_root.rglob("*.tex"))
        else:
            tex_candidates = []

        requested_activity = int(request.activity_number or 0)
        for tex in tex_candidates:
            tex_kind = self._detect_tex_kind(tex)
            if tex_kind == "report" and not request.include_reports:
                continue
            if tex_kind == "presentation" and not request.include_presentations:
                continue
            if tex_kind == "other":
                continue
            # --activity N acota el inventario a esa actividad; sin ella se
            # inventaria todo. Sin este filtro el motor prioriza por score y
            # elige otra actividad aunque se haya pedido una concreta.
            if requested_activity > 0 and self._extract_activity_number(tex.stem) != requested_activity:
                continue
            pdf_path = tex.with_suffix(".pdf")
            items.append(
                {
                    "target": self.workspace.relative(tex),
                    "directory": self.workspace.relative(tex.parent),
                    "tex_kind": tex_kind,
                    "activity_number": self._extract_activity_number(tex.stem),
                    "pdf_exists": pdf_path.exists(),
                }
            )
        return items

    def _load_audit_payload(self, audit_path: str) -> dict[str, Any]:
        if not audit_path:
            return {}
        candidate = Path(audit_path)
        if not candidate.is_absolute():
            candidate = self.workspace.repo_root / candidate
        if not candidate.exists() or not candidate.is_file():
            return {}
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _audit_status(self, audit_path: str, audit_payload: dict[str, Any], issues_by_target: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
        candidate = Path(audit_path) if audit_path else Path()
        if audit_path and not candidate.is_absolute():
            candidate = self.workspace.repo_root / candidate
        return {
            "path": audit_path,
            "exists": bool(audit_path) and candidate.exists() and candidate.is_file(),
            "loaded": bool(audit_payload),
            "issue_total": len(audit_payload.get("issues", [])) if isinstance(audit_payload.get("issues", []), list) else 0,
            "target_total": len(issues_by_target),
        }

    def _group_audit_issues(self, audit_payload: dict[str, Any], target_root_relative: str) -> dict[str, list[dict[str, str]]]:
        grouped: dict[str, list[dict[str, str]]] = {}
        target_prefix = "" if target_root_relative == "." else target_root_relative.rstrip("/") + "/"
        for issue in audit_payload.get("issues", []):
            if not isinstance(issue, dict):
                continue
            target = str(issue.get("Target") or issue.get("target") or "").strip()
            if not target:
                continue
            if target_root_relative not in ("", "."):
                if target != target_root_relative and not target.startswith(target_prefix):
                    continue
            grouped.setdefault(target, []).append(
                {
                    "severity": str(issue.get("Severity") or issue.get("severity") or "warning"),
                    "kind": str(issue.get("Kind") or issue.get("kind") or "issue"),
                    "detail": str(issue.get("Detail") or issue.get("detail") or ""),
                }
            )
        return grouped

    def _build_target_plans(
        self,
        request: IntelligentEngineRequest,
        inventory: list[dict[str, Any]],
        issues_by_target: dict[str, list[dict[str, str]]],
    ) -> list[dict[str, Any]]:
        plans: list[dict[str, Any]] = []
        for item in inventory:
            target = str(item["target"])
            issues = issues_by_target.get(target, [])
            score = self._score_target(item, issues)
            actions = self._propose_actions(request, item, issues)
            if score <= 0 and not actions:
                continue
            plans.append(
                {
                    "target": target,
                    "directory": item["directory"],
                    "tex_kind": item["tex_kind"],
                    "activity_number": item["activity_number"],
                    "priority_score": score,
                    "issues": issues,
                    "recommended_actions": actions,
                }
            )
        plans.sort(key=lambda item: (-int(item["priority_score"]), item["target"]))
        limit = max(1, int(request.max_targets)) if plans else 0
        return plans[:limit]

    def _score_target(self, item: dict[str, Any], issues: list[dict[str, str]]) -> int:
        score = 0
        if not bool(item.get("pdf_exists")):
            score += 25
        weights = {
            "error": 20,
            "warning": 8,
            "quality": 5,
        }
        kind_weights = {
            "pdf-faltante": 40,
            "pdf-desactualizado": 20,
            "tex-sin-memoria-directa": 12,
            "reporte-preguntas-duplicadas": 18,
            "reporte-con-pendientes-o-placeholders": 16,
            "reporte-analisis-propio-insuficiente": 14,
            "reporte-introduccion-debil": 10,
            "reporte-conclusion-debil": 10,
            "presentacion-muy-breve": 16,
            "presentacion-sin-tema-visual": 14,
            "presentacion-sin-recursos-didacticos": 12,
            "memoria-json-invalido": 18,
            "memoria-ruta-inexistente": 16,
        }
        for issue in issues:
            score += weights.get(issue.get("severity", "warning"), 5)
            score += kind_weights.get(issue.get("kind", "issue"), 4)
        return score

    def _propose_actions(
        self,
        request: IntelligentEngineRequest,
        item: dict[str, Any],
        issues: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        target = str(item["target"])
        directory = str(item["directory"])
        tex_kind = str(item["tex_kind"])
        activity_number = int(item.get("activity_number") or 0)
        issue_kinds = {issue.get("kind", "") for issue in issues}
        actions: list[dict[str, Any]] = []

        if activity_number > 0 and tex_kind in {"report", "presentation"}:
            actions.append(
                self._action(
                    "investigate-and-expand-references",
                    "Buscar/validar fuentes locales y en línea antes de redactar: memoria editorial, bibliografía recomendada, fuentes institucionales/académicas y materialización en .bib con citas visibles.",
                    [
                        ".\\aulaTEX\\aulatex.ps1",
                        "investigation",
                        "--target",
                        directory,
                        "--activity",
                        str(activity_number),
                        "--query",
                        f"{Path(directory).name} actividad {activity_number} bibliografia planeacion contenidos fuentes primarias",
                        "--query",
                        f"{Path(directory).name} actividad {activity_number} fuentes institucionales legislacion doctrina",
                        "--iterations",
                        "2",
                        *self._engine_cli_args(request),
                    ],
                    blocking=False,
                )
            )
            actions.append(
                self._action(
                    "realizar-actividad-pipeline",
                    "Ejecutar contrato integral: memoria editorial, validación de referencias locales/en línea, expansión de citas visibles, redacción o reparación, evaluación, compilación y repetición hasta aprobar gates.",
                    [
                        ".\\aulaTEX\\aulatex.ps1",
                        "activity-monitor",
                        "--target",
                        target,
                        "--activity",
                        str(activity_number),
                        "--workflow-backend",
                        request.backend,
                        "--run-extractor",
                        "--apply-bibliography-repair",
                        "--compile-check",
                        "--keep-going",
                    ],
                    blocking=True,
                )
            )

        if "tex-sin-memoria-directa" in issue_kinds or any(kind.startswith("memoria-") for kind in issue_kinds):
            actions.append(
                self._action(
                    "refresh-editorial-memory",
                    "Restablecer memoria editorial cercana al TEX antes de volver a revisar o compilar.",
                    [
                        ".\\aulaTEX\\aulatex.ps1",
                        "editorial-memory",
                        "--target",
                        directory,
                        "--build-level",
                        "materia",
                        "--propagation-mode",
                        "local",
                        *self._engine_cli_args(request),
                    ],
                    blocking=False,
                )
            )

        if tex_kind == "report" and any(kind.startswith("reporte-") for kind in issue_kinds):
            command = [
                ".\\aulaTEX\\aulatex.ps1",
                "activity-monitor",
                "--target",
                target,
                "--workflow-backend",
                request.backend,
                "--max-cycles",
                "2",
                "--compile-check",
            ]
            if activity_number > 0:
                command.extend(["--activity", str(activity_number)])
            actions.append(
                self._action(
                    "repair-report-editorially",
                    "Aplicar bucle monitorizado con heurísticas y revisiones acotadas sobre el reporte.",
                    command,
                )
            )

        if tex_kind == "presentation" and any(kind.startswith("presentacion-") for kind in issue_kinds):
            actions.append(
                self._action(
                    "plan-presentation-upgrade",
                    "Planear mejora Beamer institucional sin acoplar el motor a una escuela o script específico.",
                    [
                        ".\\aulaTEX\\aulatex.ps1",
                        "intelligent-engine",
                        "--target",
                        directory,
                        "--backend",
                        request.backend,
                        "--no-reports",
                        "--max-targets",
                        "1",
                        *self._engine_cli_args(request),
                    ],
                    blocking=False,
                )
            )

        if "pdf-faltante" in issue_kinds or "pdf-desactualizado" in issue_kinds or not bool(item.get("pdf_exists")):
            actions.append(
                self._action(
                    "compile-target",
                    "Compilar y verificar frescura del PDF como validación final del target.",
                    [".\\aulaTEX\\latexmk-build.ps1", target],
                    blocking=True,
                )
            )

        if not actions:
            actions.append(
                self._action(
                    "observe-only",
                    "Mantener target en cola de observación; no requiere acción inmediata en v1.",
                    [".\\aulaTEX\\aulatex.ps1", "activity-observe", "--target", target],
                    blocking=False,
                )
            )
        return actions

    def _action(self, action_id: str, rationale: str, command: list[str], *, blocking: bool = True) -> dict[str, Any]:
        return {
            "action_id": action_id,
            "blocking": blocking,
            "rationale": rationale,
            "command": command,
        }

    def _engine_cli_args(self, request: IntelligentEngineRequest) -> list[str]:
        return [argument for engine in request.engines for argument in ("--engine", engine)]

    def _build_architecture_contract(self, request: IntelligentEngineRequest) -> dict[str, Any]:
        return {
            "goal": "Operar campañas masivas por lotes y ciclos con priorización, memoria, LLM y validación reproducible.",
            "control_plane": {
                "runtime": "PowerShell",
                "responsibilities": [
                    "lanzar campañas",
                    "particionar lotes",
                    "coordinar compilación",
                    "publicar artefactos",
                ],
            },
            "engine_plane": {
                "runtime": "Python",
                "responsibilities": [
                    "descubrir targets",
                    "consolidar auditoría",
                    "priorizar",
                    "enrutar acciones",
                    "persistir manifiestos y reportes",
                ],
            },
            "workflow_plane": {
                "backend": request.backend,
                "responsibilities": [
                    "grafo de estados",
                    "reintentos acotados",
                    "transiciones deterministas",
                    "observabilidad por nodo",
                ],
            },
            "modules": [
                {"name": "campaign_scheduler", "status": "planned", "purpose": "segmentación de campañas y lotes"},
                {"name": "scope_inventory", "status": "available", "purpose": "inventario de scopes y TEX"},
                {"name": "audit_ingestor", "status": "available", "purpose": "consumo de audit.json y manifest previos"},
                {"name": "priority_router", "status": "scaffolded", "purpose": "ranking de targets y mapeo de acciones"},
                {"name": "source_note_ingestor", "status": "policy", "purpose": "usar notas como trazabilidad y memoria, no como autoridad bibliográfica final"},
                {"name": "editorial_memory_retriever", "status": "contracted", "purpose": "consultar memoria editorial local, ascendente y nodos relacionados antes de redactar o corregir"},
                {"name": "didactic_technique_router", "status": "policy", "purpose": "detectar la técnica didáctica del insumo y preservar su forma visible: cuestionario, caso, foro, mapa u otra técnica"},
                {"name": "questionnaire_answer_validator", "status": "contracted", "purpose": "validar reactivos, respuestas y justificaciones contra fuentes locales sólidas o fuentes en línea verificables"},
                {"name": "realizar_actividad_pipeline", "status": "contracted", "purpose": "contrato integral probado: memoria editorial, fuentes locales/en línea, validación de cuestionarios, redacción, evaluación, reparación, compilación y repetición"},
                {"name": "web_source_validator", "status": "contracted", "purpose": "contrastar afirmaciones y respuestas no sustentadas por corpus local con fuentes en línea o primarias verificables"},
                {"name": "bibliography_gate", "status": "policy", "purpose": "materializar en .bib fuentes verificadas, no notas internas como fuente final"},
                {"name": "execution_runner", "status": "planned", "purpose": "ejecución de acciones con checkpointing"},
                {"name": "validation_gate", "status": "planned", "purpose": "validación de diffs, compilación y score editorial"},
                {"name": "memory_retrieval", "status": "planned", "purpose": "ADN editorial relevante por target"},
                {"name": "telemetry_store", "status": "planned", "purpose": "costos, throughput, éxitos y fallos"},
            ],
            "source_handling_policy": self._build_source_handling_policy(),
            "didactic_technique_policy": self._build_didactic_technique_policy(),
            "realizar_actividad_pipeline": self._build_realizar_actividad_contract(),
            "contracts": {
                "manifest": "run manifest persistido por campaña",
                "target_plan": "lista priorizada de acciones por TEX",
                "graph_state": "estado serializable para reanudación",
                "source_note": "nota local usada como provenance, memoria o consigna, no como fuente académica final",
                "didactic_technique": "forma didáctica del insumo preservada en desarrollo visible; cuestionario conserva pregunta-respuesta-justificación",
                "questionnaire_validation": "cada respuesta de cuestionario debe tener soporte en memoria/fuente local sólida o fuente en línea verificable; respuestas dudosas se corrigen o se marcan",
                "editorial_memory": "memoria local, ascendente y relacionada usada antes de redactar para heredar reglas, tono, fuentes y decisiones previas",
                "bibliography_entry": "fuente primaria, institucional, normativa, doctrinal o web verificada antes de citarse en el .bib",
            },
        }

    def _build_realizar_actividad_contract(self) -> dict[str, Any]:
        return REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT

    def _build_source_handling_policy(self) -> dict[str, Any]:
        return {
            "principle": "Las notas internas pueden iniciar investigación y memoria, pero no sustituyen fuentes bibliográficas verificables.",
            "allowed_note_uses": [
                "consigna",
                "trazabilidad/provenance",
                "memoria local",
                "síntesis operativa",
                "lista de hipótesis o conceptos a verificar",
            ],
            "forbidden_note_uses": [
                "citar la nota como autoridad académica final cuando hay afirmaciones normativas, doctrinales, estadísticas o históricas",
                "usar la nota como única entrada BibTeX de respaldo",
                "convertir inferencias de la nota en hechos sin validación externa",
            ],
            "bibliography_rule": "El .bib final debe contener fuentes primarias o verificadas: normas oficiales, sitios institucionales, doctrina, artículos, jurisprudencia, estadísticas o fuentes web consultables.",
            "validation_required_for": [
                "datos estadísticos",
                "requisitos legales",
                "afirmaciones normativas",
                "jurisprudencia o criterios recientes",
                "hechos históricos",
                "definiciones doctrinales",
                "atribuciones institucionales",
            ],
            "recommended_workflow": [
                "extraer de la nota afirmaciones y términos clave",
                "buscar o aportar fuentes primarias/en línea para cada afirmación sustantiva",
                "registrar la nota en memoria/provenance",
                "registrar en .bib solo las fuentes validadas",
                "usar comentarios o memoria para enlazar nota -> fuente verificada",
            ],
        }

    def _build_didactic_technique_policy(self) -> dict[str, Any]:
        return {
            "principle": "La técnica didáctica del insumo se conserva como contrato de forma: el motor mejora rigor, citas y claridad sin cambiar cuestionario por ensayo, caso por resumen ni mapa por texto plano.",
            "contracts": DIDACTIC_TECHNIQUE_CONTRACTS,
            "questionnaire_rule": "Si la nota o consigna contiene cuestionario, reactivos o respuestas, el desarrollo visible debe incluir el título dado por la nota cuando exista y conservar cada pregunta con respuesta y justificación, en tabla compacta o lista estructurada.",
            "table_rule": "Si la técnica didáctica usa tabla/cuadro, aplicar manejo robusto como en Filosofía del Derecho, Redacción en contextos virtuales y Ética y Moral jurídica: encabezados claros, caption/label cuando sea producto visible, longtable para varias filas, landscape o scriptsize cuando el ancho lo requiera, tabcolsep/arraystretch ajustados y lectura breve posterior.",
            "style_rule": "En el desarrollo no explicar la técnica didáctica desde fuera ni romper la cuarta pared; entrar al tema con tono formal y presentar el contenido solicitado.",
            "reuse_scope": "Contrato aplicable a materias de la misma carrera, otras carreras, la misma institución u otras instituciones; solo cambian identidad institucional, bibliografía verificable y datos de portada.",
            "allowed_transformations": [
                "compactar redacción sin omitir reactivos",
                "agrupar preguntas solo si se conserva pregunta-respuesta-justificación",
                "agregar contexto académico con fuentes verificadas",
                "usar longtable/tabular/landscape cuando la técnica requiera tabla amplia",
                "comentar matrices auxiliares si no son producto solicitado",
            ],
            "forbidden_transformations": [
                "convertir un cuestionario en ensayo general",
                "eliminar preguntas del insumo",
                "sustituir respuestas por paráfrasis sin conservar el sentido original",
                "citar notas internas como bibliografía final",
            ],
        }

    def _build_graph_contract(self, request: IntelligentEngineRequest) -> dict[str, Any]:
        return {
            "backend": request.backend,
            "state": {
                "run_id": "string",
                "scope_key": "string",
                "batch_id": "string",
                "queue": "list[target_plan]",
                "current_target": "string",
                "current_action": "string",
                "completed": "list[action_result]",
                "failed": "list[action_result]",
                "metrics": {
                    "issue_total_before": "int",
                    "issue_total_after": "int",
                    "pdf_fresh": "int",
                    "llm_calls": "int",
                },
                "resume_cursor": "int",
            },
            "nodes": [
                "discover",
                "ingest_audit",
                "ingest_source_notes",
                "build_editorial_memory",
                "extract_concepts_and_sources",
                "detect_didactic_technique",
                "preserve_didactic_format",
                "validate_online_sources",
                "bibliography_gate",
                "draft_or_repair_content",
                "evaluate_quality",
                "compile_and_repair",
                "repeat_until_pass",
                "prioritize",
                "route_action",
                "execute_memory",
                "execute_report",
                "execute_presentation",
                "compile",
                "validate",
                "promote",
                "stop",
            ],
            "transitions": [
                "discover -> ingest_audit",
                "ingest_audit -> ingest_source_notes",
                "ingest_source_notes -> build_editorial_memory",
                "build_editorial_memory -> extract_concepts_and_sources",
                "extract_concepts_and_sources -> detect_didactic_technique",
                "detect_didactic_technique -> preserve_didactic_format",
                "preserve_didactic_format -> validate_online_sources",
                "validate_online_sources -> bibliography_gate",
                "bibliography_gate -> draft_or_repair_content",
                "draft_or_repair_content -> evaluate_quality",
                "evaluate_quality -> compile_and_repair|repeat_until_pass",
                "compile_and_repair -> repeat_until_pass|promote",
                "repeat_until_pass -> build_editorial_memory|stop",
                "promote -> prioritize",
                "prioritize -> route_action",
                "route_action -> execute_memory|execute_report|execute_presentation|compile",
                "execute_* -> validate",
                "validate -> promote|route_action|stop",
            ],
            "batches": {
                "strategy": "small-first",
                "recommended_batch_size": 1,
                "recommended_max_batches": 1,
            },
        }

    def _build_markdown_report(self, manifest: dict[str, Any]) -> str:
        lines = [
            "# Motor inteligente AulaTeX v1",
            "",
            "Artefacto temporal generado en `.aulatex-temp/intelligent-engine/runs/`; puede eliminarse sin afectar fuentes, memorias ni PDFs finales.",
            "",
            f"- Run: {manifest['run_id']}",
            f"- Backend de flujo: {manifest['graph_contract']['backend']}",
            f"- Scope: {manifest['scope']['scope_key'] or manifest['scope']['target_root']}",
            f"- TEX inventariados: {manifest['inventory_summary']['tex_total']}",
            f"- Targets planificados: {manifest['inventory_summary']['planned_targets']}",
            "",
            "## Módulos v1",
        ]
        for module in manifest["architecture"]["modules"]:
            lines.append(f"- {module['name']}: {module['status']} | {module['purpose']}")
        policy = manifest["architecture"].get("source_handling_policy", {})
        lines.extend([
            "",
            "## Política de notas como fuentes",
            f"- Principio: {policy.get('principle', '')}",
            f"- Regla bibliográfica: {policy.get('bibliography_rule', '')}",
            "- Uso permitido de notas: " + ", ".join(policy.get("allowed_note_uses", [])),
            "- Requiere validación externa: " + ", ".join(policy.get("validation_required_for", [])),
        ])
        didactic_policy = manifest["architecture"].get("didactic_technique_policy", {})
        lines.extend([
            "",
            "## Contrato de técnicas didácticas",
            f"- Principio: {didactic_policy.get('principle', '')}",
            f"- Regla de cuestionario: {didactic_policy.get('questionnaire_rule', '')}",
            f"- Regla de tablas: {didactic_policy.get('table_rule', '')}",
            f"- Regla de estilo: {didactic_policy.get('style_rule', '')}",
            f"- Alcance de reutilización: {didactic_policy.get('reuse_scope', '')}",
        ])
        realizar = manifest.get("realizar_actividad_contract", {})
        lines.extend([
            "",
            "## Contrato operativo: realizar actividad",
            f"- Propósito: {realizar.get('purpose', '')}",
            f"- Ciclo recomendado: {realizar.get('recommended_cycle', '')}",
            "- Fases: " + " -> ".join(phase.get("id", "") for phase in realizar.get("phases", [])),
            "- Gates: " + "; ".join(f"{k}={v}" for k, v in realizar.get("quality_gates", {}).items()),
        ])
        lines.extend(["", "## Targets priorizados"])
        for target in manifest["targets"]:
            issue_kinds = ", ".join(issue["kind"] for issue in target["issues"][:6]) or "sin issues de auditoría"
            lines.append(f"- {target['target']} | score={target['priority_score']} | {issue_kinds}")
            for action in target["recommended_actions"]:
                command = " ".join(action["command"])
                lines.append(f"  - {action['action_id']}: {action['rationale']} | {command}")
        if not manifest["targets"]:
            lines.append("- No se generaron acciones; revisar filtros o aportar audit.json.")
        lines.extend(
            [
                "",
                "## Estado serializable",
                "- queue, current_target, current_action, completed, failed y metrics quedan definidos para implementar reanudación en la siguiente iteración.",
            ]
        )
        return "\n".join(lines) + "\n"

    def _detect_tex_kind(self, tex: Path) -> str:
        name = tex.name.lower()
        if name.startswith("reporte-"):
            return "report"
        if name.startswith("presentacion-"):
            return "presentation"
        return "other"

    def _extract_activity_number(self, stem: str) -> int:
        lower = stem.lower()
        marker = "actividad"
        if marker not in lower:
            return 0
        suffix = lower.split(marker, 1)[1]
        digits = "".join(char for char in suffix if char.isdigit())
        return int(digits) if digits else 0


__all__ = [
    "IntelligentEngine",
    "IntelligentEngineRequest",
    "IntelligentEngineResult",
]