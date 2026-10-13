from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypedDict

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:  # pragma: no cover - defensive fallback for environments without langgraph
    END = "__end__"
    START = "__start__"
    StateGraph = None

from .activity_revision import ActivityRevisionRequest, ActivityReviser
from .activity_observer import ActivityObservationRequest, ActivityObserver
from .bibliography_repair import BibliographyRepairRequest, BibliographyRepairer
from .compilation_repair import CompilationRepairRequest, CompilationRepairer
from .extractor_adapter import ExtractorAdapter, ExtractorRequest, ExtractorRunResult
from .incremental_detail_planner import DetailPlannerRequest, DetailPlannerResult, IncrementalDetailPlanner
from .workspace import AulaTeXWorkspace


@dataclass(frozen=True)
class ActivityMonitorRequest:
    target: str
    activity_number: int = 1
    output: str = ""
    max_cycles: int = 2
    compile_check: bool = False
    run_extractor: bool = False
    extractor_motors: tuple[str, ...] = ("anthropicfoundry", "tfidf")
    apply_bibliography_repair: bool = False
    apply_revision_patches: bool = True
    backup_bibliography: bool = True
    backup_revision: bool = True
    stop_on_blocker: bool = True
    workflow_backend: Literal["langgraph", "classic"] = "langgraph"
    run_detail_planner: bool = True
    detail_planner_max_scopes: int = 6


@dataclass(frozen=True)
class ActivityMonitorResult:
    run_id: str
    run_dir: Path
    ok: bool
    manifest_path: Path
    report_path: Path


class MonitorGraphState(TypedDict):
    cycle_index: int
    cycles: list[dict[str, Any]]
    final_ok: bool
    stop: bool
    last_next_action: str
    continue_after_action: bool


class ActivityMonitor:
    def __init__(self, workspace: AulaTeXWorkspace | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.observer = ActivityObserver(self.workspace)
        self.repairer = BibliographyRepairer(self.workspace)
        self.reviser = ActivityReviser(self.workspace)
        self.compilation_repairer = CompilationRepairer(self.workspace)
        self.extractor = ExtractorAdapter(self.workspace)
        self.detail_planner = IncrementalDetailPlanner(self.workspace)
        self.root = self.workspace.feedback_root / "activity-monitor" / "runs"
        self.root.mkdir(parents=True, exist_ok=True)

    def run(self, request: ActivityMonitorRequest) -> ActivityMonitorResult:
        run_id = f"{self.workspace.timestamp()}-activity-{int(request.activity_number):02d}-monitor"
        run_dir = self._resolve_run_dir(request, run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        detail_plan_result: DetailPlannerResult | None = None
        if bool(request.run_detail_planner):
            detail_plan_result = self.detail_planner.run(
                DetailPlannerRequest(
                    target=request.target,
                    activity_number=request.activity_number,
                    output=str(run_dir / "detail-planner"),
                    max_scopes=request.detail_planner_max_scopes,
                    persist_memory=True,
                )
            )

        if request.workflow_backend == "langgraph" and StateGraph is not None:
            cycles, final_ok = self._run_langgraph(request, run_dir)
        else:
            cycles, final_ok = self._run_classic(request, run_dir)

        return self._finalize_result(request, run_id, run_dir, cycles, final_ok, detail_plan_result)

    def _run_classic(self, request: ActivityMonitorRequest, run_dir: Path) -> tuple[list[dict[str, Any]], bool]:
        cycles: list[dict[str, Any]] = []
        final_ok = False

        for cycle_index in range(1, max(1, int(request.max_cycles)) + 1):
            cycle_dir = run_dir / f"cycle-{cycle_index:02d}"
            cycle_dir.mkdir(parents=True, exist_ok=True)
            cycle_record, evaluation = self._observe_cycle(request, cycle_dir, cycle_index)
            cycles.append(cycle_record)

            if evaluation.get("passed"):
                final_ok = True
                break

            if next_action == "repair-bibliography":
                repair_result = self.repairer.repair(
                    BibliographyRepairRequest(
                        target=request.target,
                        activity_number=request.activity_number,
                        output=str(cycle_dir / "bibliography-repair"),
                        apply=bool(request.apply_bibliography_repair),
                        backup=bool(request.backup_bibliography),
                        workflow_backend=request.workflow_backend,
                    )
                )
                cycle_record["executed_action"] = "bibliography-repair"
                cycle_record["action_result"] = {
                    "ok": repair_result.ok,
                    "plan": self.workspace.relative(repair_result.plan_path),
                    "report": self.workspace.relative(repair_result.report_path),
                    "patched_tex": self.workspace.relative(repair_result.patched_tex_path) if repair_result.patched_tex_path else "",
                }
                continue

            if next_action == "revise-activity":
                revision_result = self.reviser.revise(
                    ActivityRevisionRequest(
                        target=request.target,
                        activity_number=request.activity_number,
                        output=str(cycle_dir / "activity-revision"),
                        apply=bool(request.apply_revision_patches),
                        backup=bool(request.backup_revision),
                        workflow_backend=request.workflow_backend,
                    )
                )
                cycle_record["executed_action"] = "revise-activity"
                cycle_record["action_result"] = {
                    "ok": revision_result.ok,
                    "plan": self.workspace.relative(revision_result.plan_path),
                    "report": self.workspace.relative(revision_result.report_path),
                    "patched_tex": self.workspace.relative(revision_result.patched_tex_path) if revision_result.patched_tex_path else "",
                }
                if revision_result.patched_tex_path is not None:
                    continue
                if request.stop_on_blocker:
                    break
                continue

            if next_action == "run-extractor" and request.run_extractor:
                extractor_result = None
                extractor_attempts: list[dict[str, Any]] = []
                for motor in self._extractor_motors(request):
                    attempt = self.extractor.run(
                        ExtractorRequest(
                            target=request.target,
                            activity_number=request.activity_number,
                            motor=motor,
                        )
                    )
                    extractor_attempts.append(self._extractor_result_payload(attempt, motor))
                    if attempt.ok:
                        extractor_result = attempt
                        break
                cycle_record["executed_action"] = "run-extractor"
                cycle_record["action_result"] = {
                    "ok": bool(extractor_result.ok) if extractor_result is not None else False,
                    "selected_motor": extractor_result_payload.get("motor", "") if (extractor_result_payload := (extractor_attempts[-1] if extractor_attempts else {})) else "",
                    "attempts": extractor_attempts,
                }
                if extractor_result is not None and extractor_result.ok:
                    continue
                if request.stop_on_blocker:
                    break

            if next_action == "repair-compilation":
                compilation_result = self.compilation_repairer.repair(
                    CompilationRepairRequest(
                        target=request.target,
                        activity_number=request.activity_number,
                        output=str(cycle_dir / "compilation-repair"),
                    )
                )
                cycle_record["executed_action"] = "repair-compilation"
                cycle_record["action_result"] = {
                    "ok": compilation_result.ok,
                    "classification": json.loads(compilation_result.plan_path.read_text(encoding="utf-8")).get("classification", ""),
                    "plan": self.workspace.relative(compilation_result.plan_path),
                    "report": self.workspace.relative(compilation_result.report_path),
                }
                if compilation_result.ok:
                    continue
                if cycle_record["action_result"].get("classification") == "environment":
                    continue
                if request.stop_on_blocker:
                    break

            if request.stop_on_blocker:
                break

        return cycles, final_ok

    def _run_langgraph(self, request: ActivityMonitorRequest, run_dir: Path) -> tuple[list[dict[str, Any]], bool]:
        if StateGraph is None:
            return self._run_classic(request, run_dir)

        def observe(state: MonitorGraphState) -> dict[str, Any]:
            cycle_index = int(state["cycle_index"])
            cycle_dir = run_dir / f"cycle-{cycle_index:02d}"
            cycle_dir.mkdir(parents=True, exist_ok=True)
            cycle_record, evaluation = self._observe_cycle(request, cycle_dir, cycle_index)
            cycles = [*state["cycles"], cycle_record]
            return {
                "cycles": cycles,
                "final_ok": bool(evaluation.get("passed")),
                "last_next_action": str(evaluation.get("next_action") or ""),
                "continue_after_action": False,
                "stop": False,
            }

        def route_after_observe(state: MonitorGraphState) -> str:
            if state["final_ok"]:
                return "end"
            action = state["last_next_action"]
            if action == "repair-bibliography":
                return "repair_bibliography"
            if action == "revise-activity":
                return "revise_activity"
            if action == "run-extractor":
                return "run_extractor" if request.run_extractor else ("advance" if not request.stop_on_blocker else "stop")
            if action == "repair-compilation":
                return "repair_compilation"
            return "advance" if not request.stop_on_blocker else "stop"

        def repair_bibliography(state: MonitorGraphState) -> dict[str, Any]:
            cycle_dir = run_dir / f"cycle-{int(state['cycle_index']):02d}"
            cycle_record = dict(state["cycles"][-1])
            repair_result = self.repairer.repair(
                BibliographyRepairRequest(
                    target=request.target,
                    activity_number=request.activity_number,
                    output=str(cycle_dir / "bibliography-repair"),
                    apply=bool(request.apply_bibliography_repair),
                    backup=bool(request.backup_bibliography),
                    workflow_backend=request.workflow_backend,
                )
            )
            cycle_record["executed_action"] = "bibliography-repair"
            cycle_record["action_result"] = {
                "ok": repair_result.ok,
                "plan": self.workspace.relative(repair_result.plan_path),
                "report": self.workspace.relative(repair_result.report_path),
                "patched_tex": self.workspace.relative(repair_result.patched_tex_path) if repair_result.patched_tex_path else "",
            }
            return {
                "cycles": self._replace_last_cycle(state["cycles"], cycle_record),
                "continue_after_action": True,
            }

        def revise_activity(state: MonitorGraphState) -> dict[str, Any]:
            cycle_dir = run_dir / f"cycle-{int(state['cycle_index']):02d}"
            cycle_record = dict(state["cycles"][-1])
            revision_result = self.reviser.revise(
                ActivityRevisionRequest(
                    target=request.target,
                    activity_number=request.activity_number,
                    output=str(cycle_dir / "activity-revision"),
                    apply=bool(request.apply_revision_patches),
                    backup=bool(request.backup_revision),
                    workflow_backend=request.workflow_backend,
                )
            )
            cycle_record["executed_action"] = "revise-activity"
            cycle_record["action_result"] = {
                "ok": revision_result.ok,
                "plan": self.workspace.relative(revision_result.plan_path),
                "report": self.workspace.relative(revision_result.report_path),
                "patched_tex": self.workspace.relative(revision_result.patched_tex_path) if revision_result.patched_tex_path else "",
            }
            can_continue = (revision_result.patched_tex_path is not None) or (not request.stop_on_blocker)
            return {
                "cycles": self._replace_last_cycle(state["cycles"], cycle_record),
                "continue_after_action": can_continue,
            }

        def run_extractor(state: MonitorGraphState) -> dict[str, Any]:
            cycle_record = dict(state["cycles"][-1])
            extractor_result = None
            extractor_attempts: list[dict[str, Any]] = []
            for motor in self._extractor_motors(request):
                attempt = self.extractor.run(
                    ExtractorRequest(
                        target=request.target,
                        activity_number=request.activity_number,
                        motor=motor,
                    )
                )
                extractor_attempts.append(self._extractor_result_payload(attempt, motor))
                if attempt.ok:
                    extractor_result = attempt
                    break
            cycle_record["executed_action"] = "run-extractor"
            cycle_record["action_result"] = {
                "ok": bool(extractor_result.ok) if extractor_result is not None else False,
                "selected_motor": extractor_result_payload.get("motor", "") if (extractor_result_payload := (extractor_attempts[-1] if extractor_attempts else {})) else "",
                "attempts": extractor_attempts,
            }
            can_continue = (extractor_result is not None and extractor_result.ok) or (not request.stop_on_blocker)
            return {
                "cycles": self._replace_last_cycle(state["cycles"], cycle_record),
                "continue_after_action": can_continue,
            }

        def repair_compilation(state: MonitorGraphState) -> dict[str, Any]:
            cycle_dir = run_dir / f"cycle-{int(state['cycle_index']):02d}"
            cycle_record = dict(state["cycles"][-1])
            compilation_result = self.compilation_repairer.repair(
                CompilationRepairRequest(
                    target=request.target,
                    activity_number=request.activity_number,
                    output=str(cycle_dir / "compilation-repair"),
                )
            )
            classification = json.loads(compilation_result.plan_path.read_text(encoding="utf-8")).get("classification", "")
            cycle_record["executed_action"] = "repair-compilation"
            cycle_record["action_result"] = {
                "ok": compilation_result.ok,
                "classification": classification,
                "plan": self.workspace.relative(compilation_result.plan_path),
                "report": self.workspace.relative(compilation_result.report_path),
            }
            can_continue = bool(compilation_result.ok or classification == "environment" or not request.stop_on_blocker)
            return {
                "cycles": self._replace_last_cycle(state["cycles"], cycle_record),
                "continue_after_action": can_continue,
            }

        def stop(state: MonitorGraphState) -> dict[str, Any]:
            return {"stop": True, "continue_after_action": False}

        def advance(state: MonitorGraphState) -> dict[str, Any]:
            if not state["continue_after_action"]:
                return {"stop": True}
            if int(state["cycle_index"]) >= max(1, int(request.max_cycles)):
                return {"stop": True}
            return {"cycle_index": int(state["cycle_index"]) + 1, "stop": False}

        def route_after_advance(state: MonitorGraphState) -> str:
            return "end" if state["stop"] else "observe"

        graph = StateGraph(MonitorGraphState)
        graph.add_node("observe", observe)
        graph.add_node("repair_bibliography", repair_bibliography)
        graph.add_node("revise_activity", revise_activity)
        graph.add_node("run_extractor", run_extractor)
        graph.add_node("repair_compilation", repair_compilation)
        graph.add_node("stop", stop)
        graph.add_node("advance", advance)
        graph.add_edge(START, "observe")
        graph.add_conditional_edges(
            "observe",
            route_after_observe,
            {
                "repair_bibliography": "repair_bibliography",
                "revise_activity": "revise_activity",
                "run_extractor": "run_extractor",
                "repair_compilation": "repair_compilation",
                "advance": "advance",
                "stop": "stop",
                "end": END,
            },
        )
        graph.add_edge("repair_bibliography", "advance")
        graph.add_edge("revise_activity", "advance")
        graph.add_edge("run_extractor", "advance")
        graph.add_edge("repair_compilation", "advance")
        graph.add_edge("stop", END)
        graph.add_conditional_edges("advance", route_after_advance, {"observe": "observe", "end": END})

        app = graph.compile()
        result = app.invoke(
            {
                "cycle_index": 1,
                "cycles": [],
                "final_ok": False,
                "stop": False,
                "last_next_action": "",
                "continue_after_action": False,
            }
        )
        return list(result["cycles"]), bool(result["final_ok"])

    def _observe_cycle(
        self,
        request: ActivityMonitorRequest,
        cycle_dir: Path,
        cycle_index: int,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        observation = self.observer.observe(
            ActivityObservationRequest(
                target=request.target,
                activity_number=request.activity_number,
                output=str(cycle_dir / "observe"),
                compile_check=bool(request.compile_check),
            )
        )
        evaluation = json.loads(observation.evaluation_path.read_text(encoding="utf-8"))
        cycle_record: dict[str, Any] = {
            "cycle": cycle_index,
            "observation": {
                "ok": observation.ok,
                "state": self.workspace.relative(observation.state_path),
                "evaluation": self.workspace.relative(observation.evaluation_path),
                "actions": self.workspace.relative(observation.actions_path),
            },
            "score": evaluation.get("score"),
            "basic_score": evaluation.get("basic_score"),
            "passed": bool(evaluation.get("passed")),
            "next_action": str(evaluation.get("next_action") or ""),
            "critical_findings": list(evaluation.get("critical_findings") or []),
            "contract": evaluation.get("contract", {}),
            "executed_action": "",
            "action_result": {},
        }
        return cycle_record, evaluation

    def _replace_last_cycle(self, cycles: list[dict[str, Any]], cycle_record: dict[str, Any]) -> list[dict[str, Any]]:
        if not cycles:
            return [cycle_record]
        return [*cycles[:-1], cycle_record]

    def _finalize_result(
        self,
        request: ActivityMonitorRequest,
        run_id: str,
        run_dir: Path,
        cycles: list[dict[str, Any]],
        final_ok: bool,
        detail_plan_result: DetailPlannerResult | None,
    ) -> ActivityMonitorResult:
        manifest = {
            "run_id": run_id,
            "kind": "activity-monitor",
            "workflow_backend": request.workflow_backend if StateGraph is not None else "classic",
            "target": self.workspace.relative(self.workspace.resolve_target(request.target)),
            "activity_number": int(request.activity_number),
            "max_cycles": int(request.max_cycles),
            "compile_check": bool(request.compile_check),
            "run_extractor": bool(request.run_extractor),
            "run_detail_planner": bool(request.run_detail_planner),
            "extractor_motors": list(self._extractor_motors(request)),
            "apply_bibliography_repair": bool(request.apply_bibliography_repair),
            "apply_revision_patches": bool(request.apply_revision_patches),
            "ok": final_ok,
            "detail_planner": self._detail_planner_manifest(detail_plan_result),
            "cycles": cycles,
        }
        manifest_path = run_dir / "manifest.json"
        report_path = run_dir / "reporte-monitor.md"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        report_path.write_text(self._render_report(manifest), encoding="utf-8")
        self.workspace.append_bitacora(run_id, "activity-monitor", manifest)
        return ActivityMonitorResult(run_id, run_dir, final_ok, manifest_path, report_path)

    def _resolve_run_dir(self, request: ActivityMonitorRequest, run_id: str) -> Path:
        if request.output.strip():
            return self.workspace.resolve_target(request.output) / run_id
        return self.root / run_id

    def _extractor_motors(self, request: ActivityMonitorRequest) -> tuple[str, ...]:
        motors = tuple(motor.strip() for motor in request.extractor_motors if motor and motor.strip())
        return motors or ("anthropicfoundry", "tfidf")

    def _extractor_result_payload(self, result: ExtractorRunResult, motor: str) -> dict[str, Any]:
        return {
            "motor": motor,
            "ok": result.ok,
            "run_dir": self.workspace.relative(result.run_dir),
            "manifest": self.workspace.relative(result.manifest_path),
            "output_dir": self.workspace.relative(result.output_dir),
            "stdout": self.workspace.relative(result.stdout_path),
            "stderr": self.workspace.relative(result.stderr_path),
        }

    def _detail_planner_manifest(self, result: DetailPlannerResult | None) -> dict[str, Any]:
        if result is None:
            return {"enabled": False}
        return {
            "enabled": True,
            "ok": result.ok,
            "run_dir": self.workspace.relative(result.run_dir),
            "manifest": self.workspace.relative(result.manifest_path),
            "report": self.workspace.relative(result.report_path),
            "processed_scopes": list(result.processed_scopes),
            "updated_scopes": list(result.updated_scopes),
        }

    def _render_report(self, manifest: dict[str, Any]) -> str:
        lines = [
            "# Monitor de actividad AulaTeX",
            "",
            f"- Objetivo: {manifest['target']}",
            f"- Actividad: {manifest['activity_number']}",
            f"- Ciclos máximos: {manifest['max_cycles']}",
            f"- Backend: {manifest.get('workflow_backend', 'classic')}",
            f"- Estado final: {'PASS' if manifest['ok'] else 'PENDIENTE'}",
            "",
            "## Detail planner",
            "",
        ]
        detail_planner = manifest.get("detail_planner") or {}
        if detail_planner.get("enabled"):
            lines.extend(
                [
                    f"- Estado: {'OK' if detail_planner.get('ok') else 'ERROR'}",
                    f"- Reporte: {detail_planner.get('report', '')}",
                    f"- Scopes procesados: {len(detail_planner.get('processed_scopes', []))}",
                    f"- Scopes actualizados: {len(detail_planner.get('updated_scopes', []))}",
                    "",
                ]
            )
        else:
            lines.extend(["- No se ejecuto detail planner en este ciclo.", ""])
        lines.extend([
            "## Ciclos",
            "",
        ])
        for cycle in manifest.get("cycles", []):
            lines.extend(
                [
                    f"### Ciclo {cycle['cycle']}",
                    "",
                    f"- Score: {cycle.get('score')}",
                    f"- Score base: {cycle.get('basic_score')}",
                    f"- Passed: {cycle.get('passed')}",
                    f"- Siguiente acción: {cycle.get('next_action')}",
                    f"- Acción ejecutada: {cycle.get('executed_action') or 'ninguna'}",
                ]
            )
            contract = cycle.get("contract") or {}
            if contract:
                lines.append(f"- Score contractual: {contract.get('score')}")
            findings = cycle.get("critical_findings") or []
            if findings:
                lines.append("- Hallazgos críticos:")
                lines.extend(f"  - {item}" for item in findings)
            action_result = cycle.get("action_result") or {}
            if action_result:
                lines.append(f"- Resultado acción: {json.dumps(action_result, ensure_ascii=False)}")
            lines.append("")
        return "\n".join(lines)