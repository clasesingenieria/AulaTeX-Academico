from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .activity_observer import ActivityObservationRequest, ActivityObserver
from .compilation_diagnostics import classify_compile_failure, is_environment_issue
from .workspace import AulaTeXWorkspace


@dataclass(frozen=True)
class CompilationRepairRequest:
    target: str
    activity_number: int = 1
    output: str = ""


@dataclass(frozen=True)
class CompilationRepairResult:
    run_id: str
    run_dir: Path
    ok: bool
    plan_path: Path
    report_path: Path


class CompilationRepairer:
    def __init__(self, workspace: AulaTeXWorkspace | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.observer = ActivityObserver(self.workspace)
        self.root = self.workspace.feedback_root / "compilation-repair" / "runs"
        self.root.mkdir(parents=True, exist_ok=True)

    def repair(self, request: CompilationRepairRequest) -> CompilationRepairResult:
        run_id = f"{self.workspace.timestamp()}-activity-{int(request.activity_number):02d}-compile-repair"
        run_dir = self._resolve_run_dir(request, run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        observation = self.observer.observe(
            ActivityObservationRequest(
                target=request.target,
                activity_number=request.activity_number,
                output=str(run_dir / "obs"),
                compile_check=False,
            )
        )
        state = json.loads(observation.state_path.read_text(encoding="utf-8"))
        tex_path = self.workspace.resolve_target(state.get("target_tex", ""))

        attempts = []
        ok = False
        for clean_mode in ("safe", "full"):
            result = self.workspace.compile_tex(tex_path, clean_mode=clean_mode)
            combined = f"{result.stdout}\n{result.stderr}"
            category = classify_compile_failure(combined) if not result.ok else "ok"
            attempts.append(
                {
                    "clean_mode": clean_mode,
                    "ok": result.ok,
                    "returncode": result.returncode,
                    "category": category,
                    "environment_issue": bool(not result.ok and is_environment_issue(category)),
                    "stdout_tail": result.stdout[-2500:],
                    "stderr_tail": result.stderr[-2500:],
                }
            )
            if result.ok:
                ok = True
                break

        environment_blocker = bool(attempts and all(attempt.get("environment_issue") for attempt in attempts))

        plan = {
            "run_id": run_id,
            "target_tex": state.get("target_tex", ""),
            "activity_number": int(request.activity_number),
            "attempts": attempts,
            "observation": self.workspace.relative(observation.state_path),
            "ok": ok,
            "environment_blocker": environment_blocker,
            "classification": "environment" if environment_blocker else "tex-or-build" if not ok else "ok",
        }
        plan_path = run_dir / "plan-reparacion-compilacion.json"
        report_path = run_dir / "reporte-reparacion-compilacion.md"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        report_path.write_text(self._render_report(plan), encoding="utf-8")
        self.workspace.append_bitacora(run_id, "compilation-repair", plan)
        return CompilationRepairResult(run_id, run_dir, ok, plan_path, report_path)

    def _resolve_run_dir(self, request: CompilationRepairRequest, run_id: str) -> Path:
        if request.output.strip():
            return self.workspace.resolve_target(request.output)
        return self.root / run_id

    def _render_report(self, plan: dict) -> str:
        lines = [
            "# Reparación de compilación",
            "",
            f"- TEX: {plan['target_tex']}",
            f"- Actividad: {plan['activity_number']}",
            f"- Estado final: {'OK' if plan['ok'] else 'ERROR'}",
            f"- Clasificación: {plan['classification']}",
            "",
            "## Intentos",
            "",
        ]
        for attempt in plan.get("attempts", []):
            lines.extend(
                [
                    f"- clean_mode={attempt['clean_mode']} ok={attempt['ok']} rc={attempt['returncode']} category={attempt['category']}",
                ]
            )
        if plan.get("environment_blocker"):
            lines.extend(["", "## Diagnóstico", "", "- El bloqueo es de entorno TeX; no implica por sí mismo un defecto editorial del TEX."])
        lines.append("")
        return "\n".join(lines)