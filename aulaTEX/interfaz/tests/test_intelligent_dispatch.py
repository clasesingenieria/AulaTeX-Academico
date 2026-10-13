from __future__ import annotations

import json
from pathlib import Path

import pytest

from interfaz.config import Settings
from interfaz.intelligent_dispatch import (
    execute_intelligent_dispatch_plan,
    extract_intelligent_instruction,
    format_dispatch_summary,
    format_motor_capabilities_markdown,
    motor_capabilities,
    plan_intelligent_dispatch,
    run_intelligent_dispatch,
)


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        telegram_bot_token="token",
        notes_dir=tmp_path / "notes",
        audio_storage_dir=tmp_path / "audio",
        bot_mode="polling",
        azure_speech_key="speech-key",
        azure_speech_region="eastus",
        azure_speech_language="es-MX",
        llm_provider="model-router",
        llm_api_kind="openai-chat",
        azure_openai_endpoint="https://example.services.ai.azure.com/openai/v1/",
        azure_openai_api_key="router-key",
        azure_openai_chat_deployment="model-router",
    )


def test_extract_intelligent_instruction_accepts_prefix() -> None:
    assert extract_intelligent_instruction("motor: planifica UCNL actividad 1") == "planifica UCNL actividad 1"
    assert extract_intelligent_instruction("texto normal") is None


def test_motor_capabilities_describe_full_delegate_layer() -> None:
    capabilities = motor_capabilities("plan-only")
    rendered = format_motor_capabilities_markdown(capabilities)

    assert capabilities.execution_mode == "plan-only"
    assert capabilities.supported_kinds == ("intelligent-engine", "agent", "activity-monitor")
    assert capabilities.workflow_backends == ("langgraph", "classic")
    assert "delegate-to-aulatex" in capabilities.planes["execution"]
    assert "plan-only" in capabilities.planes["execution"]
    assert "bot-interfaz contiene la capa de control" in rendered
    assert "aulaTEX.aulatex" in rendered


def test_plan_only_blocks_real_execution_after_planning(tmp_path: Path, monkeypatch) -> None:
    settings = make_settings(tmp_path)
    monkeypatch.setattr(
        "interfaz.intelligent_dispatch.invoke_chat",
        lambda *args, **kwargs: json.dumps(
            {"kind": "intelligent-engine", "request": {"target": ".", "max_targets": 1}},
            ensure_ascii=False,
        ),
    )
    plan = plan_intelligent_dispatch("planifica sin ejecutar", settings)

    with pytest.raises(RuntimeError, match="plan-only"):
        execute_intelligent_dispatch_plan(plan, execution_mode="plan-only")


def test_run_intelligent_dispatch_executes_engine(tmp_path: Path, monkeypatch) -> None:
    settings = make_settings(tmp_path)

    monkeypatch.setattr(
        "interfaz.intelligent_dispatch.invoke_chat",
        lambda *args, **kwargs: json.dumps(
            {
                "kind": "intelligent-engine",
                "request": {
                    "target": ".",
                    "activity_number": 2,
                    "backend": "classic",
                    "max_targets": 3,
                    "include_reports": True,
                    "include_presentations": False,
                    "engines": ["Codex"],
                },
            },
            ensure_ascii=False,
        ),
    )

    class FakeResult:
        def __init__(self, run_dir: Path) -> None:
            self.run_dir = run_dir
            self.manifest_path = run_dir / "manifest.json"
            self.report_path = run_dir / "report.md"

    class FakeEngine:
        def run(self, request):
            run_dir = tmp_path / "run"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "scope": {"scope_label": "Interinstitucional", "target_root": "."},
                        "inventory_summary": {"planned_targets": 3, "tex_total": 7},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (run_dir / "report.md").write_text("# Reporte\n\nContenido", encoding="utf-8")
            return FakeResult(run_dir)

    monkeypatch.setattr("interfaz.intelligent_dispatch.IntelligentEngine", lambda: FakeEngine())

    dispatch = run_intelligent_dispatch("planifica el repositorio", settings)

    assert dispatch.request.backend == "classic"
    assert dispatch.request.activity_number == 2
    assert dispatch.request.max_targets == 3
    assert dispatch.request.include_presentations is False
    assert dispatch.request.engines == ("Codex",)
    summary = format_dispatch_summary(dispatch)
    assert "Motor inteligente ejecutado." in summary
    assert "Objetivos planificados: 3" in summary


def test_plan_intelligent_dispatch_normalizes_gpt_5_6_engine_aliases(tmp_path: Path, monkeypatch) -> None:
    settings = make_settings(tmp_path)
    monkeypatch.setattr(
        "interfaz.intelligent_dispatch.invoke_chat",
        lambda *args, **kwargs: json.dumps(
            {
                "kind": "intelligent-engine",
                "request": {
                    "target": ".",
                    "engines": ["sol", "GPT-5.6-Luna", "terra"],
                },
            },
            ensure_ascii=False,
        ),
    )

    plan = plan_intelligent_dispatch("planifica con sol, luna y terra", settings)

    assert plan.request.engines == ("GPT-5.6-SOL", "GPT-5.6-Luna", "GPT-5.6-Terra")


def test_plan_intelligent_dispatch_builds_agent_request(tmp_path: Path, monkeypatch) -> None:
    settings = make_settings(tmp_path)

    monkeypatch.setattr(
        "interfaz.intelligent_dispatch.invoke_chat",
        lambda *args, **kwargs: json.dumps(
            {
                "kind": "agent",
                "request": {
                    "target": ".",
                    "level": "materia",
                    "action": "realizar-actividad",
                    "activity_number": 1,
                    "iterations": 4,
                    "cycle_mode": "full",
                    "compile_tex": False,
                    "run_extractor": True,
                    "engines": ["Claude Foundry", "Codex"],
                },
            },
            ensure_ascii=False,
        ),
    )

    plan = plan_intelligent_dispatch("realiza actividad 1", settings)

    assert plan.kind == "agent"
    assert plan.request.action == "realizar-actividad"
    assert plan.request.iterations == 4
    assert plan.request.cycle_mode == "full"
    assert plan.request.compile_tex is False
    assert plan.request.engines == ["Claude Foundry", "Codex"]


def test_run_intelligent_dispatch_executes_activity_monitor(tmp_path: Path, monkeypatch) -> None:
    settings = make_settings(tmp_path)

    monkeypatch.setattr(
        "interfaz.intelligent_dispatch.invoke_chat",
        lambda *args, **kwargs: json.dumps(
            {
                "kind": "activity-monitor",
                "request": {
                    "target": ".",
                    "activity_number": 1,
                    "max_cycles": 3,
                    "compile_check": True,
                    "run_extractor": True,
                    "apply_bibliography_repair": True,
                    "stop_on_blocker": False,
                    "workflow_backend": "classic",
                },
            },
            ensure_ascii=False,
        ),
    )

    class FakeResult:
        def __init__(self, run_dir: Path) -> None:
            self.run_dir = run_dir
            self.manifest_path = run_dir / "manifest.json"
            self.report_path = run_dir / "report.md"

    class FakeMonitor:
        def run(self, request):
            run_dir = tmp_path / "monitor-run"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "kind": "activity-monitor",
                        "target": ".",
                        "activity_number": 1,
                        "workflow_backend": "classic",
                        "ok": True,
                        "cycles": [{"cycle": 1}, {"cycle": 2}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (run_dir / "report.md").write_text("# Monitor\n\nContenido", encoding="utf-8")
            return FakeResult(run_dir)

    monkeypatch.setattr("interfaz.intelligent_dispatch.ActivityMonitor", lambda: FakeMonitor())

    dispatch = run_intelligent_dispatch("monitorea actividad 1 hasta pasar", settings)

    assert dispatch.kind == "activity-monitor"
    assert dispatch.request.max_cycles == 3
    assert dispatch.request.stop_on_blocker is False
    summary = format_dispatch_summary(dispatch)
    assert "Activity monitor ejecutado." in summary
    assert "Ciclos registrados: 2" in summary