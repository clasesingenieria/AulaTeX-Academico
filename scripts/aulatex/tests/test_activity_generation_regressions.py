from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.aulatex.agent import AgentRequest, AgentTargetContext, AulaTeXAgent
from scripts.aulatex.agentic_patterns import AgentTask, AgenticStateMachine, EditorialConsensusEngine
from scripts.aulatex.activity_optimizer import ActivityOptimizeRequest, ActivityOptimizer, PlannedAction
from scripts.aulatex.intelligent_engine import IntelligentEngine, IntelligentEngineRequest
from scripts.aulatex.llm_bridge import LLMCallResult
from scripts.aulatex.semantic_audit import SemanticAuditResult


class _Workspace:
    def relative(self, path: Path) -> str:
        return path.as_posix()


class _CaptureAgent:
    request: AgentRequest | None = None

    def __init__(self, _workspace: object) -> None:
        pass

    def run(self, request: AgentRequest) -> SimpleNamespace:
        type(self).request = request
        return SimpleNamespace(
            ok=False,
            run_dir=Path("run"),
            monitor_ok=False,
            optimize_ok=False,
            quality_before=7.0,
            quality_after=7.0,
            optimize_plan_summary=None,
            final_compile_ok=False,
            semantic_blocking_before=1,
            semantic_blocking_after=1,
            semantic_audit_available=True,
        )


def test_intelligent_engine_preserves_requested_tex(monkeypatch, tmp_path: Path) -> None:
    from scripts.aulatex import agent as agent_module

    tex = tmp_path / "presentacion-materia-Actividad-7.tex"
    tex.write_text("\\documentclass{beamer}", encoding="utf-8")
    monkeypatch.setattr(agent_module, "AulaTeXAgent", _CaptureAgent)

    engine = object.__new__(IntelligentEngine)
    engine.workspace = _Workspace()
    request = IntelligentEngineRequest(engines=("Auto (model-router)",))
    reporter = SimpleNamespace(notice=lambda *_: None, progress=lambda *_: None)

    ok, _ = engine._exec_realizar_actividad(
        request, str(tex), str(tmp_path), 7, tmp_path, reporter, 0.0, 1.0
    )

    assert not ok
    assert _CaptureAgent.request is not None
    assert Path(_CaptureAgent.request.target) == tex
    assert _CaptureAgent.request.monitor_max_cycles == 1
    assert _CaptureAgent.request.optimize_cycles == 0
    assert _CaptureAgent.request.run_monitor is True
    assert _CaptureAgent.request.run_optimize is True
    assert _CaptureAgent.request.run_final_compile is True


def test_realizar_actividad_defaults_to_one_monitored_cycle_with_convergence() -> None:
    request = AgentRequest(action="realizar-actividad")

    assert request.monitor_max_cycles == 1
    assert request.optimize_cycles == 0
    assert request.run_monitor is True
    assert request.run_optimize is True
    assert request.run_final_compile is True


def test_generated_beamer_applies_to_explicit_presentation(tmp_path: Path) -> None:
    tex = tmp_path / "presentacion-materia-Actividad-7.tex"
    tex.write_text(
        "\\documentclass{beamer}\n\\begin{document}\n"
        "\\begin{frame}{En construcción}Pendiente\\end{frame}\n\\end{document}\n",
        encoding="utf-8",
    )
    document = (
        "\\documentclass{beamer}\n\\begin{document}\n"
        "\\begin{frame}{Brief}Contenido completo\\end{frame}\n"
        "\\begin{frame}{Roles}Equipo\\end{frame}\n"
        "\\begin{frame}{Cierre}Validación\\end{frame}\n\\end{document}"
    )
    agent = object.__new__(AulaTeXAgent)
    agent.workspace = _Workspace()
    agent._select_compile_targets = lambda *_: [tex]
    target = AgentTargetContext(tex, tex, "scope", str(tex), "direct")
    task = AgentTask("generar", "arquitecto", "generar", "prompt")
    workflow = AgenticStateMachine()

    result = agent._apply_generated_tex(
        AgentRequest(action="realizar-actividad", activity_number=7),
        target,
        [task],
        [LLMCallResult("fake", True, f"```tex\n{document}\n```")],
        workflow,
    )

    assert result["applied"] is True
    assert tex.read_text(encoding="utf-8") == document


@pytest.mark.parametrize("presentation, repeats", [(False, 150), (False, 1), (True, 1)])
def test_generated_tex_preserves_completed_documents(tmp_path: Path, presentation: bool, repeats: int) -> None:
    name = "presentacion" if presentation else "reporte"
    tex = tmp_path / f"{name}-materia-Actividad-7.tex"
    document_class = "beamer" if presentation else "article"
    original = (
        f"\\documentclass{{{document_class}}}\n\\begin{{document}}\n"
        + "% \\pendiente{Comentario interno}\n"
        + "Contenido revisado. " * repeats
        + "\n\\end{document}"
    )
    tex.write_text(original, encoding="utf-8")
    replacement = original.replace("Contenido revisado.", "Contenido nuevo.")
    agent = object.__new__(AulaTeXAgent)
    agent.workspace = _Workspace()
    agent._select_compile_targets = lambda *_: [tex]
    target = AgentTargetContext(tex, tex, "scope", str(tex), "direct")

    result = agent._apply_generated_tex(
        AgentRequest(action="realizar-actividad", activity_number=7), target,
        [AgentTask("generar", "arquitecto", "generar", "prompt")],
        [LLMCallResult("fake", True, replacement)], AgenticStateMachine(),
    )

    assert result["applied"] is False
    assert result["reason"] == "destino-ya-redactado"
    assert tex.read_text(encoding="utf-8") == original


@pytest.mark.parametrize(
    "build_ok, returncode, pdf_state, raises, has_target, expected",
    [
        (False, 1, "fresh", False, True, False),
        (True, 1, "fresh", False, True, False),
        (True, 0, "missing", False, True, False),
        (True, 0, "stale", False, True, False),
        (True, 0, "fresh", True, True, False),
        (True, 0, "fresh", False, False, False),
        (True, 0, "fresh", False, True, True),
    ],
)
def test_final_compile_requires_success_and_current_pdf(
    tmp_path: Path, build_ok: bool, returncode: int, pdf_state: str,
    raises: bool, has_target: bool, expected: bool,
) -> None:
    tex = tmp_path / "reporte-materia-Actividad-1.tex"
    tex.write_text("Contenido", encoding="utf-8")
    os.utime(tex, (1000, 1000))
    if pdf_state != "missing":
        pdf = tex.with_suffix(".pdf")
        pdf.write_bytes(b"%PDF-1.4 test")
        modified = 1001 if pdf_state == "fresh" else 999
        os.utime(pdf, (modified, modified))

    def compile_tex(*args, **kwargs):
        if raises:
            raise RuntimeError("Fallo de compilacion simulado")
        return SimpleNamespace(ok=build_ok, returncode=returncode, stdout="", stderr="")

    agent = object.__new__(AulaTeXAgent)
    agent.workspace = SimpleNamespace(relative=str, compile_tex=compile_tex)
    agent._select_compile_targets = lambda *_: [tex] if has_target else []
    report = tmp_path / "report.md"
    report.write_text("Prueba", encoding="utf-8")
    request = AgentRequest(
        action="realizar-actividad", run_foro_producto=False, run_monitor=False,
        run_optimize=False, run_mapa_layout=False,
    )
    target = AgentTargetContext(tex, tex, "scope", str(tex), "direct")

    result = agent._postprocess_activity(request, target, tmp_path, report)

    assert result[4] is expected


@pytest.mark.parametrize("cycle_mode, iterations, call_count", [("stages", 5, 5), ("full", 2, 10), ("stages", 3, 3)])
@pytest.mark.parametrize("completed", [False, True])
def test_agent_passes_generated_tex_and_compile_evidence_to_reviewers(
    tmp_path: Path, cycle_mode: str, iterations: int, call_count: int, completed: bool,
) -> None:
    tex = tmp_path / "reporte-materia-Actividad-1.tex"
    original = "\\documentclass{article}\n\\begin{document}\nEXISTING_CONTENT\n\\end{document}"
    tex.write_text(original if completed else "\\pendiente{Redactar}", encoding="utf-8")
    document = "\\documentclass{article}\n\\begin{document}\nGENERATED_CONTENT\n\\end{document}"
    expected_document = original if completed else document
    events = []
    prompts = []

    class FakeLLM:
        def engines(self):
            return ("Auto (model-router)",)

        def call(self, engine, prompt, **kwargs):
            prompts.append(prompt)
            index = len(prompts)
            events.append(f"llm-{index}")
            text = document if index % 5 == 3 else f"RESULT_STAGE_{index}"
            return LLMCallResult(engine, True, text)

    def compile_tex(*args, **kwargs):
        events.append("compile")
        assert tex.read_text(encoding="utf-8") == expected_document
        return SimpleNamespace(ok=False, returncode=1, stdout="", stderr="COMPILE_FAILURE_EVIDENCE")

    agent = object.__new__(AulaTeXAgent)
    agent.llm = FakeLLM()
    agent.workspace = SimpleNamespace(
        feedback_root=tmp_path, timestamp=lambda: "test-run", relative=str,
        context_summary=lambda *_: "Initial context", compile_tex=compile_tex,
        append_bitacora=lambda *_: None,
    )
    target = AgentTargetContext(tex, tex, "", str(tex), "direct")
    agent._resolve_target_context = lambda *_: target
    agent._select_compile_targets = lambda *_: [tex]
    agent._postprocess_activity = lambda *_: (None,) * 9

    result = agent.run(AgentRequest(
        target=str(tex), action="realizar-actividad", engines=["Auto (model-router)"],
        run_detail_planner=False, skip_extractor=True, cycle_mode=cycle_mode, iterations=iterations,
    ))

    assert result.ok is False
    expected_events = []
    for index in range(1, call_count + 1):
        expected_events.append(f"llm-{index}")
        if index % 5 == 3:
            expected_events.append("compile")
    assert events == expected_events
    assert "RESULT_STAGE_1" in prompts[1]
    assert "RESULT_STAGE_2" in prompts[2]
    for index, prompt in enumerate(prompts, start=1):
        if index % 5 in {4, 0}:
            assert "GENERATED_CONTENT" in prompt
            assert "COMPILE_FAILURE_EVIDENCE" in prompt
            assert expected_document in prompt
            assert "TEX actual:" in prompt
        if index % 5 == 0:
            assert f"RESULT_STAGE_{index - 1}" in prompt
    assert tex.read_text(encoding="utf-8") == expected_document


@pytest.mark.parametrize("cycles", [0, 1])
@pytest.mark.parametrize("quality, expected", [(70.0, False), (100.0, True)])
def test_optimizer_requires_target_quality(tmp_path: Path, cycles: int, quality: float, expected: bool) -> None:
    tex = tmp_path / "reporte-materia-Actividad-1.tex"
    tex.write_text("Contenido que debe preservarse", encoding="utf-8")
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"target_tex": str(tex)}), encoding="utf-8")
    evaluation = tmp_path / "evaluation.json"
    evaluation.write_text(json.dumps({"contract": {"score": 100}}), encoding="utf-8")
    optimizer = object.__new__(ActivityOptimizer)
    optimizer.workspace = SimpleNamespace(timestamp=lambda: "test", resolve_target=Path)
    optimizer._resolve_run_dir = lambda *_: tmp_path / "run"
    optimizer._observe = lambda *_: {"state": state, "evaluation": evaluation}
    optimizer._load_or_build_concepts = lambda *_: []
    optimizer._rubric_text = lambda *_: "Rubrica"
    optimizer._quality_score = lambda *_: quality
    optimizer._quality_breakdown = lambda *_: {"test": quality}
    optimizer._semantic_audit = lambda *_: SemanticAuditResult(True, True, 1, 1)
    optimizer._select_cycle_action = lambda *_: PlannedAction("fake")
    optimizer._request_improvement = lambda *args, **kwargs: None
    optimizer._finalize = lambda *args, **kwargs: SimpleNamespace(**kwargs)

    result = optimizer.optimize(ActivityOptimizeRequest(
        target=str(tex), cycles=cycles, max_cycles=2, stall_limit=1, backup=False,
    ))

    assert result.ok is expected
    assert ("no alcanzada" in result.note) is not expected
    assert tex.read_text(encoding="utf-8") == "Contenido que debe preservarse"


def test_empty_llm_response_blocks_consensus() -> None:
    task = AgentTask("generar", "arquitecto", "generar", "prompt")
    report = EditorialConsensusEngine().evaluate(
        [task], [LLMCallResult("fake", True, "")]
    )

    assert not report.passed
    assert any("sin respuesta util" in risk for risk in report.risks)
