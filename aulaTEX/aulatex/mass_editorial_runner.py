from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from .incremental_detail_planner import DetailPlannerRequest, IncrementalDetailPlanner
from .workspace import AulaTeXWorkspace, EditorialScope


@dataclass(frozen=True)
class MassEditorialRunnerRequest:
    cycles_per_node: int = 11
    max_scopes: int = 0
    detail_max_scopes: int = 6
    scope_offset: int = 0
    scope_level: str = ""
    target: str = "."
    output: str = ""
    persist_memory: bool = True
    append_contract_index: bool = False


@dataclass(frozen=True)
class MassEditorialRunnerResult:
    ok: bool
    run_id: str
    run_dir: Path
    progress_path: Path
    proposals_path: Path
    proposals_jsonl_path: Path
    contract_proposals_path: Path
    report_path: Path
    processed_scopes: int
    failed_scopes: int
    scope_total: int


ProgressCallback = Callable[[dict], None]


class MassEditorialRunner:
    def __init__(self, workspace: AulaTeXWorkspace | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.detail_planner = IncrementalDetailPlanner(self.workspace)

    def run(self, request: MassEditorialRunnerRequest, progress_callback: ProgressCallback | None = None) -> MassEditorialRunnerResult:
        run_id = f"{self.workspace.timestamp()}-mass-editorial-runner"
        run_dir = self._resolve_run_dir(request, run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        progress_path = run_dir / "progress.json"
        proposals_path = run_dir / "proposals.json"
        proposals_jsonl_path = run_dir / "proposals.ndjson"
        contract_proposals_path = run_dir / "contract-proposals.md"
        report_path = run_dir / "report.md"
        errors_path = run_dir / "errors.ndjson"

        scopes = self._select_scopes(request)
        proposals: list[dict] = []
        failures: list[dict] = []
        started = time.time()

        self._write_progress(
            progress_path,
            {
                "status": "running",
                "run_id": run_id,
                "scope_total": len(scopes),
                "processed_scopes": 0,
                "failed_scopes": 0,
                "cycles_per_node": max(1, int(request.cycles_per_node)),
                "detail_max_scopes": max(1, int(request.detail_max_scopes)),
                "materialization_enabled": False,
                "compile_enabled": False,
                "started_at_epoch": started,
                "run_dir": self.workspace.relative(run_dir),
            },
            progress_callback,
        )

        with proposals_jsonl_path.open("w", encoding="utf-8") as proposals_jsonl, errors_path.open("w", encoding="utf-8") as errors_jsonl:
            for index, scope in enumerate(scopes, start=1):
                checkpoint = {
                    "status": "running",
                    "run_id": run_id,
                    "scope_total": len(scopes),
                    "processed_scopes": index - 1,
                    "failed_scopes": len(failures),
                    "current_index": index,
                    "current_scope_key": scope.key,
                    "current_scope_level": scope.level,
                    "elapsed_seconds": round(time.time() - started, 3),
                    "run_dir": self.workspace.relative(run_dir),
                }
                self._write_progress(progress_path, checkpoint, progress_callback)
                try:
                    result = self.detail_planner.run(
                        DetailPlannerRequest(
                            target=scope.relative_path or ".",
                            activity_number=self._activity_number(scope),
                            output=str(run_dir / "detail-planner"),
                            max_scopes=max(1, int(request.detail_max_scopes)),
                            max_fixed_point_passes=max(1, int(request.cycles_per_node)),
                            persist_memory=bool(request.persist_memory),
                        )
                    )
                    proposal = self._proposal_from_scope(scope, index, result)
                    proposals.append(proposal)
                    proposals_jsonl.write(json.dumps(proposal, ensure_ascii=False) + "\n")
                    proposals_jsonl.flush()
                except Exception as exc:  # runner masivo: registrar y continuar
                    failure = {
                        "proposal_id": f"MER-{index:05d}",
                        "scope_key": scope.key,
                        "scope_level": scope.level,
                        "status": "FAILED",
                        "error": str(exc),
                    }
                    failures.append(failure)
                    errors_jsonl.write(json.dumps(failure, ensure_ascii=False) + "\n")
                    errors_jsonl.flush()

        finished = time.time()
        payload = {
            "kind": "mass-editorial-runner",
            "version": 1,
            "run_id": run_id,
            "status": "completed" if not failures else "completed-with-errors",
            "scope_total": len(scopes),
            "processed_scopes": len(proposals),
            "failed_scopes": len(failures),
            "cycles_per_node": max(1, int(request.cycles_per_node)),
            "detail_max_scopes": max(1, int(request.detail_max_scopes)),
            "materialization_enabled": False,
            "compile_enabled": False,
            "started_at_epoch": started,
            "finished_at_epoch": finished,
            "elapsed_seconds": round(finished - started, 3),
            "request": {
                "target": request.target,
                "scope_level": request.scope_level,
                "scope_offset": int(request.scope_offset),
                "max_scopes": int(request.max_scopes),
                "persist_memory": bool(request.persist_memory),
            },
            "artifacts": {
                "progress": self.workspace.relative(progress_path),
                "proposals_jsonl": self.workspace.relative(proposals_jsonl_path),
                "contract_proposals": self.workspace.relative(contract_proposals_path),
                "report": self.workspace.relative(report_path),
                "errors_jsonl": self.workspace.relative(errors_path),
            },
            "proposals": proposals,
            "failures": failures,
        }
        proposals_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        contract_proposals_path.write_text(self._render_contract_proposals(payload), encoding="utf-8")
        report_path.write_text(self._render_report(payload), encoding="utf-8")
        if request.append_contract_index:
            self._append_contract_index(payload, contract_proposals_path)
        self.workspace.append_bitacora(run_id, "mass-editorial-runner", payload)
        self._write_progress(
            progress_path,
            {
                "status": payload["status"],
                "run_id": run_id,
                "scope_total": len(scopes),
                "processed_scopes": len(proposals),
                "failed_scopes": len(failures),
                "elapsed_seconds": payload["elapsed_seconds"],
                "proposals": self.workspace.relative(proposals_path),
                "contract_proposals": self.workspace.relative(contract_proposals_path),
                "report": self.workspace.relative(report_path),
                "run_dir": self.workspace.relative(run_dir),
            },
            progress_callback,
        )
        return MassEditorialRunnerResult(
            ok=not failures,
            run_id=run_id,
            run_dir=run_dir,
            progress_path=progress_path,
            proposals_path=proposals_path,
            proposals_jsonl_path=proposals_jsonl_path,
            contract_proposals_path=contract_proposals_path,
            report_path=report_path,
            processed_scopes=len(proposals),
            failed_scopes=len(failures),
            scope_total=len(scopes),
        )

    def _resolve_run_dir(self, request: MassEditorialRunnerRequest, run_id: str) -> Path:
        if request.output.strip():
            return self.workspace.resolve_target(request.output) / run_id
        return self.workspace.temp_root / "mass-editorial-runner" / run_id

    def _select_scopes(self, request: MassEditorialRunnerRequest) -> list[EditorialScope]:
        by_key, _children = self.workspace.editorial_scope_index()
        seed = self.workspace.find_scope_for_target(request.target)
        scopes = list(by_key.values())
        if seed is not None and seed.key != "interinstitucional":
            prefix = seed.key + "/"
            scopes = [scope for scope in scopes if scope.key == seed.key or scope.key.startswith(prefix)]
        if request.scope_level.strip():
            scopes = [scope for scope in scopes if scope.level == request.scope_level.strip()]
        offset = max(0, int(request.scope_offset))
        if offset:
            scopes = scopes[offset:]
        if request.max_scopes > 0:
            scopes = scopes[: int(request.max_scopes)]
        return scopes

    def _activity_number(self, scope: EditorialScope) -> int:
        if not scope.activity:
            return 0
        digits = "".join(ch for ch in scope.activity if ch.isdigit())
        return int(digits) if digits else 0

    def _proposal_from_scope(self, scope: EditorialScope, index: int, result) -> dict:
        return {
            "proposal_id": f"MER-{index:05d}",
            "scope_key": scope.key,
            "scope_level": scope.level,
            "node": scope.label,
            "relative_path": scope.relative_path,
            "origin": "mass-editorial-runner/detail-planner",
            "type": "editing_details_memory_reinforcement",
            "status": "PROPOSED",
            "estimated_impact": self._estimated_impact(result.updated_scopes),
            "justification": "Se reforzó memoria editorial distribuida y se generaron detalles editoriales antes de cualquier materialización TEX.",
            "detail_run_id": result.run_id,
            "detail_manifest": self.workspace.relative(result.manifest_path),
            "detail_report": self.workspace.relative(result.report_path),
            "processed_scopes": list(result.processed_scopes),
            "updated_scopes": list(result.updated_scopes),
            "materialization_enabled": False,
            "compile_enabled": False,
        }

    def _estimated_impact(self, updated_scopes: Iterable[str]) -> str:
        count = len(list(updated_scopes))
        if count >= 4:
            return "alto"
        if count >= 2:
            return "medio"
        if count == 1:
            return "bajo"
        return "sin-cambio"

    def _write_progress(self, path: Path, payload: dict, callback: ProgressCallback | None) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if callback:
            callback(payload)

    def _render_contract_proposals(self, payload: dict) -> str:
        lines = [
            "# Propuestas automáticas — runner masivo AulaTeX",
            "",
            f"Run ID: `{payload['run_id']}`",
            f"Estado: `{payload['status']}`",
            f"Scopes procesados: {payload['processed_scopes']} / {payload['scope_total']}",
            f"Fallos: {payload['failed_scopes']}",
            "",
            "> Estas entradas son propuestas. No habilitan materialización TEX ni compilación PDF hasta validación humana.",
            "",
        ]
        for proposal in payload["proposals"]:
            lines.extend(
                [
                    "---",
                    "",
                    f"ID: {proposal['proposal_id']}",
                    f"Nodo: {proposal['scope_key']}",
                    f"Origen: {proposal['origin']}",
                    f"Tipo: {proposal['type']}",
                    f"Estado: {proposal['status']}",
                    f"Impacto estimado: {proposal['estimated_impact']}",
                    f"Justificación: {proposal['justification']}",
                    f"Evidencia: `{proposal['detail_report']}`",
                    "",
                ]
            )
        return "\n".join(lines).rstrip() + "\n"

    def _render_report(self, payload: dict) -> str:
        by_level: dict[str, int] = {}
        for proposal in payload["proposals"]:
            by_level[proposal["scope_level"]] = by_level.get(proposal["scope_level"], 0) + 1
        lines = [
            "# Reporte runner masivo AulaTeX",
            "",
            f"- Run ID: `{payload['run_id']}`",
            f"- Estado: `{payload['status']}`",
            f"- Procesados: {payload['processed_scopes']} / {payload['scope_total']}",
            f"- Fallos: {payload['failed_scopes']}",
            f"- Ciclos por nodo solicitados: {payload['cycles_per_node']}",
            f"- Detail max scopes: {payload['detail_max_scopes']}",
            f"- Duración: {payload['elapsed_seconds']}s",
            "- Materialización TEX: deshabilitada",
            "- Compilación PDF: deshabilitada",
            "",
            "## Distribución por nivel",
            "",
        ]
        for level, count in sorted(by_level.items()):
            lines.append(f"- {level}: {count}")
        lines.extend(
            [
                "",
                "## Artefactos",
                "",
                f"- Propuestas JSON: `{payload['artifacts']['proposals_jsonl']}`",
                f"- Propuestas Markdown: `{payload['artifacts']['contract_proposals']}`",
                f"- Progreso: `{payload['artifacts']['progress']}`",
            ]
        )
        return "\n".join(lines).rstrip() + "\n"

    def _append_contract_index(self, payload: dict, contract_proposals_path: Path) -> None:
        contract = self.workspace.feedback_root / "contrato-editorial.md"
        marker = "\n## Índice de corridas automáticas\n"
        entry = (
            f"\n- `{payload['run_id']}` — {payload['processed_scopes']}/{payload['scope_total']} "
            f"scopes, estado `{payload['status']}`, propuestas: "
            f"`{self.workspace.relative(contract_proposals_path)}`\n"
        )
        if not contract.exists():
            contract.write_text("# Contrato Editorial AulaTeX\n" + marker + entry, encoding="utf-8")
            return
        text = contract.read_text(encoding="utf-8", errors="replace")
        if marker.strip() not in text:
            text = text.rstrip() + marker + entry
        else:
            text = text.rstrip() + entry
        contract.write_text(text, encoding="utf-8")
