from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

from .intelligent_engine import IntelligentEngine, IntelligentEngineRequest
from .llm_bridge import DEFAULT_MAX_TOKENS, AulaTeXLLMClient
from .semantic_audit import SemanticAuditResult, SemanticAuditor
from .workspace import AulaTeXWorkspace


@dataclass(frozen=True)
class CalibrationRequest:
    target: str
    activity_number: int = 1
    feedback_path: str = ""
    output: str = ""
    max_rounds: int = 3
    engines: tuple[str, ...] = ("GPT-5.6-Terra",)
    monitor_max_cycles: int = 100
    optimize_cycles: int = 0
    max_tokens: int = DEFAULT_MAX_TOKENS


@dataclass(frozen=True)
class CalibrationRound:
    round_number: int
    engine_run_id: str
    engine_ok: bool
    monitor_ok: bool | None
    optimize_ok: bool | None
    final_compile_ok: bool | None
    semantic_ok: bool
    semantic_available: bool
    semantic_blocking: int
    changed: bool
    hash_before: str
    hash_after: str
    engine_run_dir: str
    audit_path: str


@dataclass(frozen=True)
class CalibrationResult:
    ok: bool
    run_id: str
    run_dir: Path
    manifest_path: Path
    target: str
    activity_number: int
    rounds: tuple[CalibrationRound, ...] = ()
    final_audit: SemanticAuditResult | None = None
    promotion_ok: bool = False
    promoted_scope_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class MotorCalibrationRequest:
    feedback_path: str
    target_context: str = ""
    target: str = ""
    activity_number: int = 0
    output: str = ""
    max_rounds: int = 2
    engines: tuple[str, ...] = ("GPT-5.6-Terra",)
    monitor_max_cycles: int = 100
    optimize_cycles: int = 0


@dataclass(frozen=True)
class MotorCalibrationResult:
    ok: bool
    run_id: str
    rules_path: Path
    manifest_path: Path
    rules: tuple[str, ...] = ()
    self_test_ok: bool | None = None
    self_test_rounds: tuple[dict[str, Any], ...] = ()


class ActivityCalibration:
    """Ejecuta el lazo cerrado opcional de calibración post-entrega."""

    def __init__(
        self,
        workspace: AulaTeXWorkspace | None = None,
        llm: AulaTeXLLMClient | None = None,
    ) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        client = llm or AulaTeXLLMClient()
        self.engine = IntelligentEngine(self.workspace)
        self.auditor = SemanticAuditor(client)

    def calibrate_motor(self, request: MotorCalibrationRequest) -> MotorCalibrationResult:
        feedback = self._resolve_feedback(request.feedback_path)
        if feedback is None:
            raise FileNotFoundError("La calibración del motor requiere un archivo de retroalimentación válido.")
        run_id = f"{self.workspace.timestamp()}-calibracion-motor"
        run_dir = self.workspace.resolve_target(request.output) if request.output.strip() else (
            self.workspace.temp_root / "calibration" / "motor" / run_id
        )
        run_dir.mkdir(parents=True, exist_ok=True)
        rules = self._rules_from_feedback(feedback)
        rules_path = self.workspace.repo_root / "retroalimentacion-editorial" / "aulatex" / "motor-calibration-rules.json"
        rules_path.parent.mkdir(parents=True, exist_ok=True)
        existing: dict[str, Any] = {"version": 1, "rules": [], "calibrations": []}
        if rules_path.exists():
            try:
                existing = json.loads(rules_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = {"version": 1, "rules": [], "calibrations": []}
        merged_rules = self._merge_lines(existing.get("rules", []), rules)
        existing["version"] = 1
        existing["rules"] = merged_rules
        existing.setdefault("calibrations", []).append(
            {
                "run_id": run_id,
                "feedback_path": self.workspace.relative(feedback),
                "target_context": request.target_context,
                "rules_added": rules,
            }
        )
        rules_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        self_test_rounds: list[dict[str, Any]] = []
        self_test_ok: bool | None = None
        if request.target.strip():
            target = self.workspace.resolve_target(request.target)
            for round_number in range(1, max(1, int(request.max_rounds)) + 1):
                engine_result = self.engine.run(
                    IntelligentEngineRequest(
                        target=str(target),
                        activity_number=request.activity_number,
                        output=str(run_dir / f"self-test-{round_number:02d}" / "engine"),
                        max_targets=1,
                        # La prueba debe demostrar autosuficiencia: no recibe el
                        # feedback original, solo carga las reglas persistentes.
                        audit_path="",
                        include_reports=False,
                        include_presentations=False,
                        engines=request.engines,
                        execute=True,
                        actions=("realizar-actividad",),
                        monitor_max_cycles=request.monitor_max_cycles,
                        optimize_cycles=request.optimize_cycles,
                    )
                )
                audit = self.auditor.audit(
                    target.read_text(encoding="utf-8", errors="replace"),
                    target.parent,
                    engine=request.engines[-1],
                    feedback_path=feedback,
                    output_path=run_dir / f"self-test-{round_number:02d}" / "validation.json",
                )
                self_test_ok = bool(engine_result.execution_ok and audit.ok and not audit.blocking_findings)
                self_test_rounds.append(
                    {
                        "round": round_number,
                        "engine_run_id": engine_result.run_id,
                        "execution_ok": engine_result.execution_ok,
                        "semantic_ok": audit.ok,
                        "semantic_blocking": len(audit.blocking_findings),
                        "self_test_ok": self_test_ok,
                    }
                )
                if self_test_ok:
                    break
                self._refine_motor_rules(rules_path, audit)
        else:
            self_test_ok = None
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "kind": "motor-calibration",
                    "version": 1,
                    "run_id": run_id,
                    "feedback_path": self.workspace.relative(feedback),
                    "target_context": request.target_context,
                    "rules_path": self.workspace.relative(rules_path),
                    "rules_added": rules,
                    "rules_total": len(merged_rules),
                    "self_test_ok": self_test_ok,
                    "self_test_rounds": self_test_rounds,
                    "ok": bool(merged_rules),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return MotorCalibrationResult(
            bool(merged_rules) and self_test_ok is not False,
            run_id,
            rules_path,
            manifest_path,
            tuple(rules),
            self_test_ok=self_test_ok,
            self_test_rounds=tuple(self_test_rounds),
        )

    def _refine_motor_rules(self, rules_path: Path, audit: SemanticAuditResult) -> None:
        try:
            payload = json.loads(rules_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {"version": 1, "rules": [], "calibrations": []}
        refinements = [
            f"Resolver observación calibrada: {finding.suggested_fix or finding.explanation}"
            for finding in audit.blocking_findings
        ]
        payload["rules"] = self._merge_lines(payload.get("rules", []), refinements)
        payload.setdefault("refinements", []).append(
            {"blocking_count": len(audit.blocking_findings), "rules_added": refinements}
        )
        rules_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def run(self, request: CalibrationRequest) -> CalibrationResult:
        target = self.workspace.resolve_target(request.target)
        if target.is_dir():
            candidates = sorted(target.glob("*Actividad-*.tex"))
            if len(candidates) != 1:
                raise ValueError("La calibración requiere un TEX único o un target TEX explícito.")
            target = candidates[0]
        if not target.exists() or target.suffix.lower() != ".tex":
            raise FileNotFoundError(f"No existe el TEX calibrable: {target}")

        feedback = self._resolve_feedback(request.feedback_path)
        if feedback is None:
            raise FileNotFoundError("La calibración requiere --feedback con un JSON/TXT existente.")

        run_id = f"{self.workspace.timestamp()}-calibracion-actividad-{request.activity_number:02d}"
        run_dir = self._resolve_run_dir(request, run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        rounds: list[CalibrationRound] = []
        final_audit: SemanticAuditResult | None = None

        for round_number in range(1, max(1, int(request.max_rounds)) + 1):
            before = self._hash_file(target)
            engine_result = self.engine.run(
                IntelligentEngineRequest(
                    target=str(target),
                    activity_number=request.activity_number,
                    output=str(run_dir / f"round-{round_number:02d}" / "engine"),
                    max_targets=1,
                    audit_path=str(feedback),
                    include_reports=False,
                    include_presentations=False,
                    engines=request.engines,
                    execute=True,
                    actions=("realizar-actividad",),
                    monitor_max_cycles=request.monitor_max_cycles,
                    optimize_cycles=request.optimize_cycles,
                )
            )
            after = self._hash_file(target)
            audit_path = run_dir / f"round-{round_number:02d}" / "semantic-audit.json"
            final_audit = self.auditor.audit(
                target.read_text(encoding="utf-8", errors="replace"),
                target.parent,
                engine=request.engines[-1],
                max_tokens=request.max_tokens,
                output_path=audit_path,
                feedback_path=feedback,
            )
            target_record = (engine_result.execution_summary.get("targets") or [{}])[0]
            action_record = (target_record.get("actions") or [{}])[0]
            round_result = CalibrationRound(
                round_number=round_number,
                engine_run_id=engine_result.run_id,
                engine_ok=bool(engine_result.execution_ok),
                monitor_ok=action_record.get("monitor_ok"),
                optimize_ok=action_record.get("optimize_ok"),
                final_compile_ok=action_record.get("final_compile_ok"),
                semantic_ok=final_audit.ok,
                semantic_available=final_audit.audit_available,
                semantic_blocking=len(final_audit.blocking_findings),
                changed=before != after,
                hash_before=before,
                hash_after=after,
                engine_run_dir=str(action_record.get("run_dir") or ""),
                audit_path=self.workspace.relative(audit_path),
            )
            rounds.append(round_result)
            if self._round_passed(round_result):
                break

        result = CalibrationResult(
            ok=bool(rounds and self._round_passed(rounds[-1])),
            run_id=run_id,
            run_dir=run_dir,
            manifest_path=run_dir / "manifest.json",
            target=self.workspace.relative(target),
            activity_number=request.activity_number,
            rounds=tuple(rounds),
            final_audit=final_audit,
        )
        if result.ok:
            promoted_keys, promotion_ok = self._promote_calibration(result, feedback)
            result = replace(
                result,
                promotion_ok=promotion_ok,
                promoted_scope_keys=tuple(promoted_keys),
            )
        self._write_manifest(result, request, feedback)
        return result

    def _promote_calibration(self, result: CalibrationResult, feedback: Path) -> tuple[list[str], bool]:
        from .editorial_memory import EditorialMemoryStore

        scope = self.workspace.find_scope_for_target(result.target, activity_number=result.activity_number)
        if scope is None:
            return [], False
        rules = self._rules_from_feedback(feedback)
        store = EditorialMemoryStore(self.workspace)
        promoted: list[str] = []
        scopes = [scope]
        by_key, _children = self.workspace.editorial_scope_index()
        parent = by_key.get(scope.parent_key)
        if parent is not None and parent.level == "materia":
            scopes.append(parent)
        for target_scope in scopes:
            memory = store.get_memory(target_scope.key)
            memory["activity_rules"] = self._merge_lines(
                memory.get("activity_rules", []), rules
            )
            memory["quality_gates"] = self._merge_lines(
                memory.get("quality_gates", []), [
                    f"Calibración validada de {result.target}: semantic_blocking=0, compilación final correcta.",
                ]
            )
            memory["propagation_hints"] = self._merge_lines(
                memory.get("propagation_hints", []), [
                    f"Reglas promovidas desde la retroalimentación de Actividad {result.activity_number}; conservar su trazabilidad.",
                ]
            )
            store.save_memory(target_scope, memory, result.target)
            promoted.append(target_scope.key)
        return promoted, bool(promoted)

    @staticmethod
    def _rules_from_feedback(feedback: Path) -> list[str]:
        raw = feedback.read_text(encoding="utf-8", errors="replace")
        normalized = raw.lower()
        rules = []
        if "volunt" in normalized and "german" in normalized:
            rules.append(
                "Cuando el régimen voluntario depende del pago de cuotas o primas, aproximarlo al modelo germano; no clasificarlo automáticamente como latino."
            )
            rules.append(
                "En la clasificación del régimen voluntario, revisar también sujetos y vigencia normativa; no incluir automáticamente a las personas trabajadoras del hogar sin verificar si pertenecen al régimen obligatorio."
            )
            rules.append(
                "Cuando aparezca el seguro facultativo, distinguir su referencia histórica o doctrinal del seguro de salud para la familia vigente y evitar presentarlos como modalidades equivalentes sin evidencia."
            )
        if "hogar" in normalized and "obligatorio" in normalized:
            rules.append(
                "Verificar la regulación vigente de las personas trabajadoras del hogar antes de incluirlas en el régimen voluntario; pueden pertenecer al régimen obligatorio."
            )
        if "facultativo" in normalized and not any("seguro facultativo" in rule for rule in rules):
            rules.append(
                "Tratar el seguro facultativo con cautela histórica y doctrinal, distinguiéndolo del seguro de salud para la familia vigente."
            )
        return rules or [
            "Usar la retroalimentación docente validada como criterio de revisión en futuras actividades de la materia."
        ]

    @staticmethod
    def _merge_lines(current: Any, additions: list[str]) -> list[str]:
        values = [str(item).strip() for item in current if str(item).strip()] if isinstance(current, list) else []
        for item in additions:
            if item not in values:
                values.append(item)
        return values

    def _round_passed(self, round_result: CalibrationRound) -> bool:
        return bool(
            round_result.engine_ok
            and round_result.monitor_ok is not False
            and round_result.optimize_ok is not False
            and round_result.final_compile_ok is not False
            and round_result.semantic_available
            and round_result.semantic_ok
            and round_result.semantic_blocking == 0
        )

    def _resolve_feedback(self, feedback_path: str) -> Path | None:
        if not feedback_path.strip():
            return None
        candidate = Path(feedback_path)
        if not candidate.is_absolute():
            candidate = self.workspace.repo_root / candidate
        return candidate.resolve() if candidate.exists() and candidate.is_file() else None

    def _resolve_run_dir(self, request: CalibrationRequest, run_id: str) -> Path:
        if request.output.strip():
            candidate = Path(request.output)
            if not candidate.is_absolute():
                candidate = self.workspace.repo_root / candidate
            return candidate.resolve() / run_id
        return self.workspace.temp_root / "calibration" / "runs" / run_id

    def _hash_file(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _write_manifest(self, result: CalibrationResult, request: CalibrationRequest, feedback: Path) -> None:
        payload: dict[str, Any] = {
            "kind": "activity-calibration",
            "version": 1,
            "run_id": result.run_id,
            "request": {**asdict(request), "engines": list(request.engines)},
            "target": result.target,
            "activity_number": result.activity_number,
            "feedback_path": self.workspace.relative(feedback),
            "ok": result.ok,
            "promotion_ok": result.promotion_ok,
            "promoted_scope_keys": list(result.promoted_scope_keys),
            "rounds": [asdict(item) for item in result.rounds],
            "final_audit": result.final_audit.as_dict() if result.final_audit else None,
        }
        result.manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")