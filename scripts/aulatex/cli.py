from __future__ import annotations

import argparse
import json
from dataclasses import asdict
import os
from pathlib import Path

from .activity_monitor import ActivityMonitor, ActivityMonitorRequest
from .calibration import ActivityCalibration, CalibrationRequest, MotorCalibrationRequest
from .activity_observer import ActivityObservationRequest, ActivityObserver
from .activity_optimizer import ActivityOptimizeRequest, ActivityOptimizer
from .activity_revision import ActivityRevisionRequest, ActivityReviser
from .agent import AgentRequest, AulaTeXAgent
from .agentic_patterns import pattern_catalog_markdown
from .bibliography_repair import BibliographyRepairer, BibliographyRepairRequest
from .compilation_repair import CompilationRepairRequest, CompilationRepairer
from .config import MODEL_ROUTER_ENGINE, credential_status, load_aulatex_env
from .construction import ConstructionBuilder, ConstructionRequest
from .editorial_memory import EDITORIAL_LEVELS, EditorialMemoryBuilder, EditorialMemoryRequest
from .extractor_adapter import EXTRACTOR_MOTORS, ExtractorAdapter, ExtractorRequest
from .incremental_detail_planner import DetailPlannerRequest, IncrementalDetailPlanner
from .intelligent_engine import IntelligentEngine, IntelligentEngineRequest
from .investigation import InvestigationBuilder, InvestigationRequest
from .progress import resolve_reporter
from .llm_bridge import DEFAULT_MAX_TOKENS, DEFAULT_TIMEOUT_SECONDS, LLM_ENGINES, AulaTeXLLMClient, validate_llm_response
from .mass_editorial_runner import MassEditorialRunner, MassEditorialRunnerRequest
from .token_counter import count_text_tokens
from .workspace import AulaTeXWorkspace


def _editorial_checkpoint_root(workspace: AulaTeXWorkspace) -> Path:
    root = workspace.temp_root / "editorial-memory" / "checkpoints"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _default_editorial_checkpoint_name(scope_key: str, build_level: str, propagation_mode: str) -> str:
    safe_scope = scope_key.replace("/", "__").replace("\\", "__")
    return f"{safe_scope}--{build_level}--{propagation_mode}.json"


def _resolve_editorial_checkpoint_path(
    workspace: AulaTeXWorkspace,
    checkpoint_ref: str,
    *,
    scope_key: str,
    build_level: str,
    propagation_mode: str,
) -> Path:
    root = _editorial_checkpoint_root(workspace)
    if checkpoint_ref:
        candidate = Path(checkpoint_ref)
        if candidate.is_absolute() or candidate.parent != Path("."):
            return candidate
        name = candidate.name if candidate.suffix == ".json" else f"{candidate.name}.json"
        return root / name
    return root / _default_editorial_checkpoint_name(scope_key, build_level, propagation_mode)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_prompt_text(prompt_value: str | None, prompt_file: str) -> str:
    prompt_text = prompt_value or ""
    if prompt_file:
        prompt_text = Path(prompt_file).read_text(encoding="utf-8")
    if not prompt_text.strip():
        raise SystemExit("Se requiere un prompt literal o --prompt-file.")
    return prompt_text


def _collect_execution_optimize_plan_summaries(execution_summary: object) -> list[dict[str, object]]:
    if not isinstance(execution_summary, dict):
        return []
    targets = execution_summary.get("targets")
    if not isinstance(targets, list):
        return []
    summaries: list[dict[str, object]] = []
    for target_record in targets:
        if not isinstance(target_record, dict):
            continue
        actions = target_record.get("actions")
        if not isinstance(actions, list):
            continue
        for action in actions:
            if not isinstance(action, dict):
                continue
            if str(action.get("action") or "") != "realizar-actividad":
                continue
            summary = action.get("optimize_plan_summary")
            if not isinstance(summary, dict):
                continue
            summaries.append(
                {
                    "target": target_record.get("target", ""),
                    "activity_number": target_record.get("activity_number", 0),
                    "policy_cycles": summary.get("policy_cycles", 0),
                    "policy_usage_rate": summary.get("policy_usage_rate", 0.0),
                    "action_alignment_rate": summary.get("action_alignment_rate", 0.0),
                    "accepted_aligned_policy_cycles": summary.get("accepted_aligned_policy_cycles", 0),
                    "accepted_misaligned_policy_cycles": summary.get("accepted_misaligned_policy_cycles", 0),
                    "mean_policy_quality_delta": summary.get("mean_policy_quality_delta", 0.0),
                }
            )
    return summaries


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aulatex", description="AulaTeX GUI and agentic editorial workflow.")
    sub = parser.add_subparsers(dest="command")

    gui = sub.add_parser("gui", help="Open the AulaTeX GUI.")
    gui.add_argument("--diagnostics", action="store_true", help="Enable diagnostic metrics and performance views.")
    sub.add_parser("agent-patterns", help="List the agentic patterns integrated in AulaTeX.")

    env_cmd = sub.add_parser("llm-env", help="Show AulaTeX LLM credential status without secrets.")

    check = sub.add_parser("llm-check", help="Check configured AulaTeX LLM engines.")
    check.add_argument("--engine", action="append", choices=LLM_ENGINES)

    validate = sub.add_parser("llm-validate", help="Verify that one LLM returns usable content without printing it.")
    validate.add_argument("--engine", default=MODEL_ROUTER_ENGINE, choices=LLM_ENGINES)
    validate.add_argument("--timeout-seconds", type=int, default=45)
    validate.add_argument("--max-tokens", type=int, default=32)
    validate.add_argument("--configure-on-failure", action="store_true", help="Offer secure interactive correction for model-router if validation fails.")

    configure = sub.add_parser("llm-config", help="Validate model-router and repair endpoint, API key and deployment interactively on failure.")
    configure.add_argument("--timeout-seconds", type=int, default=45)
    configure.add_argument("--max-tokens", type=int, default=32)
    configure.add_argument("--non-interactive", action="store_true", help="Only validate; never prompt or modify credentials.")

    tokenize = sub.add_parser("llm-tokenize", help="Count prompt tokens with a local Python tokenizer.")
    tokenize.add_argument("prompt", nargs="?")
    tokenize.add_argument("--prompt-file", default="")
    tokenize.add_argument("--engine", default="Codex", choices=LLM_ENGINES)

    prompt = sub.add_parser("llm-prompt", help="Run one prompt through one LLM engine.")
    prompt.add_argument("prompt", nargs="?")
    prompt.add_argument("--prompt-file", default="")
    prompt.add_argument("--engine", default="Codex", choices=LLM_ENGINES)
    prompt.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    prompt.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)

    agent = sub.add_parser("agent", help="Run an incremental AulaTeX agent cycle.")
    agent.add_argument("--target", default=".")
    agent.add_argument("--level", default="materia", choices=("interinstitucional", "institucion", "carrera", "materia", "actividad"))
    agent.add_argument("--action", default="generar-plantilla")
    agent.add_argument("--activity", type=int, default=1)
    agent.add_argument("--generation-mode", default="direct", choices=("direct", "downward"))
    agent.add_argument("--parent-scope-key", default="")
    agent.add_argument("--child-level", default="")
    agent.add_argument("--child-name", default="")
    agent.add_argument("--engine", action="append", choices=LLM_ENGINES)
    agent.add_argument("--iterations", type=int, default=5)
    agent.add_argument("--cycle-mode", default="stages", choices=("stages", "full"), help="stages=1..5 etapas; full=N ciclos completos de todos los roles.")
    agent.add_argument("--no-compile", action="store_true")
    agent.add_argument("--apply-feedback", action="store_true")
    agent.add_argument("--run-extractor", action="store_true", help="Force run-extractor inside the agent cycle.")
    agent.add_argument("--no-extractor", action="store_true", help="Disable automatic extractor for generar/realizar actividad.")
    agent.add_argument("--extractor-probe", action="store_true", help="Run extractor adapter in probe/configuration mode.")
    agent.add_argument("--extractor-fuentes", default="")
    agent.add_argument("--extractor-planeacion", default="")
    agent.add_argument("--extractor-conceptos", default="")
    agent.add_argument("--extractor-salida", default="")
    agent.add_argument("--extractor-motor", default="anthropicfoundry", choices=EXTRACTOR_MOTORS)
    agent.add_argument("--no-detail-planner", action="store_true", help="Disable the prerequisite detail planner before realizar-actividad.")
    agent.add_argument("--detail-max-scopes", type=int, default=6)
    agent.add_argument("--no-monitor", action="store_true", help="Disable the automatic post-processing monitor loop after realizar-actividad.")
    agent.add_argument("--no-optimize", action="store_true", help="Disable the automatic post-processing quality optimization after realizar-actividad.")
    agent.add_argument("--no-foro-producto", action="store_true", help="Disable the automatic FORO product pattern (tcolorbox + copy button + 3-act structure) after realizar-actividad.")
    agent.add_argument("--no-mapa-layout", action="store_true", help="Disable the automatic TikZ concept-map layout optimizer (anti-overlap + link-label placement + vertical fill) after realizar-actividad when the product is a concept map.")
    agent.add_argument("--no-final-compile", action="store_true", help="Disable the automatic final latexmk compilation after monitor/optimize in realizar-actividad.")
    agent.add_argument("--monitor-max-cycles", type=int, default=1, help="Max cycles for the automatic post-processing monitor loop (default 1).")
    agent.add_argument("--optimize-cycles", type=int, default=0, help="Fixed number of quality optimization cycles after realizar-actividad. Default 0 = converge-to-quality (run until target quality 100 is reached).")
    agent.add_argument("--no-semantic-audit", action="store_true", help="Disable semantic claim auditing (only for offline/debug runs).")
    agent.add_argument("--semantic-feedback", default="", help="Archivo JSON/TXT con retroalimentación externa para la auditoría semántica.")

    editorial = sub.add_parser("editorial-memory", help="Build persistent editorial memory from a selected scope.")
    editorial.add_argument("--target", default=".")
    editorial.add_argument("--activity", type=int, default=0)
    editorial.add_argument("--build-level", default="materia", choices=EDITORIAL_LEVELS)
    editorial.add_argument("--propagation-mode", default="ascendente", choices=("local", "ascendente", "ascendente-exhaustivo", "recursivo"))
    editorial.add_argument("--engine", action="append", choices=LLM_ENGINES)
    editorial.add_argument("--iterations", type=int, default=2)
    editorial.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    editorial.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    editorial.add_argument("--scope-offset", type=int, default=0)
    editorial.add_argument("--scope-limit", type=int, default=0)
    editorial.add_argument("--batch-size", type=int, default=0)
    editorial.add_argument("--max-batches", type=int, default=0)
    editorial.add_argument("--checkpoint", default="")
    editorial.add_argument("--resume-checkpoint", default="")

    detail_planner = sub.add_parser("detail-planner", help="Build incremental editorial details and recursive backtrack hints for a scope.")
    detail_planner.add_argument("--target", default=".")
    detail_planner.add_argument("--activity", type=int, default=0)
    detail_planner.add_argument("--output", default="")
    detail_planner.add_argument("--max-scopes", type=int, default=6)
    detail_planner.add_argument("--max-fixed-point-passes", type=int, default=4)
    detail_planner.add_argument("--no-persist-memory", action="store_true")

    mass_runner = sub.add_parser("mass-editorial-runner", help="Run proposal-only recursive detail planning over many editorial scopes.")
    mass_runner.add_argument("--target", default=".")
    mass_runner.add_argument("--output", default="")
    mass_runner.add_argument("--cycles-per-node", type=int, default=11)
    mass_runner.add_argument("--detail-max-scopes", type=int, default=6)
    mass_runner.add_argument("--max-scopes", type=int, default=0)
    mass_runner.add_argument("--scope-offset", type=int, default=0)
    mass_runner.add_argument("--scope-level", default="", choices=("", "interinstitucional", "institucion", "carrera", "materia", "actividad"))
    mass_runner.add_argument("--no-persist-memory", action="store_true")
    mass_runner.add_argument("--append-contract-index", action="store_true")
    mass_runner.add_argument("--monitor", action="store_true", help="Print one progress JSON line per processed scope.")

    investigation = sub.add_parser("investigation", help="Consolidate the knowledge base before extractor: local context, web sources and bibliography.")
    investigation.add_argument("--target", default=".")
    investigation.add_argument("--activity", type=int, default=0)
    investigation.add_argument("--engine", action="append", choices=LLM_ENGINES)
    investigation.add_argument("--iterations", type=int, default=2)
    investigation.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    investigation.add_argument("--query", action="append", default=[])
    investigation.add_argument("--url", action="append", default=[])

    extractor = sub.add_parser("extractor", help="Run the concept extractor through the structured AulaTeX adapter.")
    extractor.add_argument("--target", default=".")
    extractor.add_argument("--activity", type=int, default=0)
    extractor.add_argument("--fuentes", default="")
    extractor.add_argument("--planeacion", default="")
    extractor.add_argument("--conceptos", default="")
    extractor.add_argument("--salida", default="")
    extractor.add_argument("--motor", default="anthropicfoundry", choices=EXTRACTOR_MOTORS)
    extractor.add_argument("--top-k", type=int, default=12)
    extractor.add_argument("--max-citas", type=int, default=8)
    extractor.add_argument("--recursivo", action=argparse.BooleanOptionalAction, default=True)
    extractor.add_argument("--probe", action="store_true")
    extractor.add_argument("--preview", action="store_true")
    extractor.add_argument("--timeout-seconds", type=int, default=3600)

    activity_observe = sub.add_parser("activity-observe", help="Observe and evaluate an activity without modifying source files.")
    activity_observe.add_argument("--target", required=True)
    activity_observe.add_argument("--activity", type=int, default=1)
    activity_observe.add_argument("--output", default="")
    activity_observe.add_argument("--compile-check", action="store_true")

    activity_monitor = sub.add_parser("activity-monitor", help="Run a monitored recursive activity loop with bounded retries.")
    activity_monitor.add_argument("--target", required=True)
    activity_monitor.add_argument("--activity", type=int, default=1)
    activity_monitor.add_argument("--output", default="")
    activity_monitor.add_argument("--max-cycles", type=int, default=2)
    activity_monitor.add_argument("--compile-check", action="store_true")
    activity_monitor.add_argument("--run-extractor", action="store_true")
    activity_monitor.add_argument("--extractor-motor", action="append", choices=EXTRACTOR_MOTORS)
    activity_monitor.add_argument("--apply-bibliography-repair", action="store_true")
    activity_monitor.add_argument("--no-apply-revision-patches", action="store_true")
    activity_monitor.add_argument("--no-bibliography-backup", action="store_true")
    activity_monitor.add_argument("--no-revision-backup", action="store_true")
    activity_monitor.add_argument("--keep-going", action="store_true")
    activity_monitor.add_argument("--workflow-backend", default="langgraph", choices=("langgraph", "classic"))
    activity_monitor.add_argument("--no-detail-planner", action="store_true")
    activity_monitor.add_argument("--detail-max-scopes", type=int, default=6)

    activity_optimize = sub.add_parser("activity-optimize", help="Run LLM quality-optimization cycles that actually improve the activity TEX. By default it CONVERGES to target quality (100) running as many cycles as needed.")
    activity_optimize.add_argument("--target", required=True)
    activity_optimize.add_argument("--activity", type=int, default=1)
    activity_optimize.add_argument("--output", default="")
    activity_optimize.add_argument("--cycles", type=int, default=0, help="Fixed number of cycles. Default 0 = converge-to-quality mode (run until target quality, stall or max-cycles).")
    activity_optimize.add_argument("--target-quality", type=float, default=100.0, help="Quality score to converge to (default 100).")
    activity_optimize.add_argument("--max-cycles", type=int, default=40, help="Safety cap on cycles in converge mode (default 40).")
    activity_optimize.add_argument("--stall-limit", type=int, default=6, help="Stop after this many consecutive cycles without accepted improvement (default 6).")
    activity_optimize.add_argument("--engine", action="append", choices=LLM_ENGINES)
    activity_optimize.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    activity_optimize.add_argument("--no-backup", action="store_true")
    activity_optimize.add_argument("--allow-incomplete-contract", action="store_true", help="Optimize even if the editorial contract is below 100.")
    activity_optimize.add_argument("--no-semantic-audit", action="store_true", help="Disable semantic claim auditing (only for offline/debug runs).")
    activity_optimize.add_argument("--semantic-feedback", default="", help="Archivo JSON/TXT con retroalimentación externa para la auditoría semántica.")
    activity_optimize.add_argument("--quality-panel", action="store_true", help="Decide con panel de jueces (heuristica + reward model + LLM) en vez de solo _quality_score.")
    activity_optimize.add_argument("--no-panel-llm-judge", action="store_true", help="Excluye el juez LLM del panel (mas barato, menos criterio de fondo).")
    activity_optimize.add_argument("--reward-model-dir", default="", help="Ruta del reward model entrenado. Por defecto AULATEX_REWARD_MODEL_DIR.")

    activity_revise = sub.add_parser("activity-revise", help="Build a structured revision plan for an activity.")
    activity_revise.add_argument("--target", required=True)
    activity_revise.add_argument("--activity", type=int, default=1)
    activity_revise.add_argument("--output", default="")
    activity_revise.add_argument("--apply", action="store_true")
    activity_revise.add_argument("--no-backup", action="store_true")
    activity_revise.add_argument("--workflow-backend", default="langgraph", choices=("langgraph", "classic"))

    foro_producto = sub.add_parser("foro-producto", help="Apply the mature FORO product pattern (tcolorbox + copy button + 3-act structure, no metadiscourse, AI footnote) to a foro activity TEX.")
    foro_producto.add_argument("--target", required=True)
    foro_producto.add_argument("--activity", type=int, default=1)
    foro_producto.add_argument("--output", default="")
    foro_producto.add_argument("--apply", action="store_true", help="Write changes (default is a dry-run simulation).")

    compilation_repair = sub.add_parser("compilation-repair", help="Attempt bounded compilation repair for an activity TEX.")
    compilation_repair.add_argument("--target", required=True)
    compilation_repair.add_argument("--activity", type=int, default=1)
    compilation_repair.add_argument("--output", default="")

    bib_repair = sub.add_parser("bibliography-repair", help="Plan or apply bibliography key repairs for an activity.")
    bib_repair.add_argument("--target", required=True)
    bib_repair.add_argument("--activity", type=int, default=1)
    bib_repair.add_argument("--output", default="")
    bib_repair.add_argument("--apply", action="store_true")
    bib_repair.add_argument("--no-backup", action="store_true")
    bib_repair.add_argument("--min-confidence", type=float, default=0.72)
    bib_repair.add_argument("--workflow-backend", default="langgraph", choices=("langgraph", "classic"))

    generation = sub.add_parser("generation", help="Create or reinforce an editorial node with foundational memory, plan and maqueta.")
    generation.add_argument("--parent-scope-key", default="interinstitucional")
    generation.add_argument("--node-level", required=True, choices=("institucion", "carrera", "materia", "actividad"))
    generation.add_argument("--node-name", required=True)
    generation.add_argument("--activity", type=int, default=1)
    generation.add_argument("--mode", default="crear", choices=("crear", "reforzar"))
    generation.add_argument("--destination", default="")
    generation.add_argument("--ingest-text", default="")
    generation.add_argument("--ingest-document", default="")
    generation.add_argument("--engine", action="append", choices=LLM_ENGINES)
    generation.add_argument("--iterations", type=int, default=2)
    generation.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)

    intelligent_engine = sub.add_parser("intelligent-engine", help="Plan a resumable bulk editorial campaign over the current workspace.")
    intelligent_engine.add_argument("--target", default=".")
    intelligent_engine.add_argument("--activity", type=int, default=0)
    intelligent_engine.add_argument("--output", default="")
    intelligent_engine.add_argument("--backend", default="langgraph", choices=("langgraph", "classic"))
    intelligent_engine.add_argument("--max-targets", type=int, default=12)
    intelligent_engine.add_argument("--audit", default="")
    intelligent_engine.add_argument("--no-reports", action="store_true")
    intelligent_engine.add_argument("--no-presentations", action="store_true")
    intelligent_engine.add_argument("--engine", action="append", choices=LLM_ENGINES)
    intelligent_engine.add_argument(
        "--execute",
        action="store_true",
        help="Ejecutar las acciones recomendadas (no solo planificar), emitiendo progreso observable.",
    )
    intelligent_engine.add_argument(
        "--action",
        action="append",
        choices=("realizar-actividad", "construir-memoria-editorial"),
        help="Acciones a ejecutar por objetivo cuando se usa --execute (repetible). Por defecto: memoria + actividad.",
    )
    intelligent_engine.add_argument("--monitor-max-cycles", type=int, default=1)
    intelligent_engine.add_argument("--optimize-cycles", type=int, default=0, help="0 = converger automáticamente a calidad 100.")
    intelligent_engine.add_argument(
        "--progress",
        action="store_true",
        help="Emitir marcadores ::progress::/::notice::/::result:: a stderr para el monitor visual.",
    )

    calibration = sub.add_parser(
        "calibrar-actividad",
        help="Ejecutar el lazo cerrado opcional de calibración con retroalimentación externa.",
    )
    calibration.add_argument("--target", required=True)
    calibration.add_argument("--activity", type=int, default=1)
    calibration.add_argument("--feedback", required=True, help="Archivo JSON/TXT de retroalimentación docente.")
    calibration.add_argument("--output", default="")
    calibration.add_argument("--max-rounds", type=int, default=3)
    calibration.add_argument("--engine", action="append", choices=LLM_ENGINES)
    calibration.add_argument("--monitor-max-cycles", type=int, default=100)
    calibration.add_argument("--optimize-cycles", type=int, default=0)
    calibration.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)

    motor_calibration = sub.add_parser(
        "calibrar-motor",
        help="Promover retroalimentación validada a reglas persistentes del motor inteligente.",
    )
    motor_calibration.add_argument("--feedback", required=True, help="Archivo JSON/TXT de retroalimentación.")
    motor_calibration.add_argument("--target-context", default="", help="Materia o actividad que originó la calibración.")
    motor_calibration.add_argument("--target", default="", help="TEX de prueba para validar que el motor reproduce la retroalimentación sin recibirla.")
    motor_calibration.add_argument("--activity", type=int, default=0)
    motor_calibration.add_argument("--max-rounds", type=int, default=2)
    motor_calibration.add_argument("--engine", action="append", choices=LLM_ENGINES)
    motor_calibration.add_argument("--monitor-max-cycles", type=int, default=100)
    motor_calibration.add_argument("--optimize-cycles", type=int, default=0)
    motor_calibration.add_argument("--output", default="")

    compile_cmd = sub.add_parser("compile", help="Compile a TeX file with the shared latexmk wrapper.")
    compile_cmd.add_argument("tex")

    mapa_layout = sub.add_parser(
        "mapa-layout",
        help="Optimize a concept-map (mc*) TikZ layout: force-directed anti-overlap, converts relative to absolute coordinates, renders a real preview and (optionally) writes the .tex. Fixes choques/empalmes/palabras de enlace comidas.",
    )
    mapa_layout.add_argument("tex")
    mapa_layout.add_argument("--iters", type=int, default=2500)
    mapa_layout.add_argument("--repulsion", type=float, default=0.5)
    mapa_layout.add_argument("--step", type=float, default=0.32)
    mapa_layout.add_argument("--spring", type=float, default=0.005)
    mapa_layout.add_argument("--xlim", type=float, default=13.5)
    mapa_layout.add_argument("--ylim", type=float, default=11.0)
    mapa_layout.add_argument("--target-aspect", type=float, default=1.4, help="Estira Y/comprime X para llenar el alto (0 = desactivar).")
    mapa_layout.add_argument("--vspread", type=float, default=1.4, help="Separación vertical extra tras optimizar (aire para etiquetas).")
    mapa_layout.add_argument("--hspread", type=float, default=1.08, help="Separación horizontal extra (sin salir de página).")
    mapa_layout.add_argument("--label-clearance", type=float, default=1.35, help="Holgura de la caja de etiqueta (evita empalmes etiqueta-nodo).")
    mapa_layout.add_argument("--out-dir", default=".aulatex-temp/opt-mapa2")
    mapa_layout.add_argument("--write", action="store_true", help="Write the optimized absolute coordinates back into the .tex.")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if bool(getattr(args, "diagnostics", False)):
        os.environ["AULATEX_ENABLE_DIAGNOSTIC_METRICS"] = "1"

    if args.command in (None, "gui"):
        if args.command is None and os.name != "nt":
            parser.print_help()
            return
        from .gui import main as gui_main

        gui_main(diagnostics_enabled=bool(getattr(args, "diagnostics", False)))
        return

    if args.command == "agent-patterns":
        print(pattern_catalog_markdown())
        return

    if args.command == "llm-env":
        env_result = load_aulatex_env()
        print(f"env: {'OK' if env_result.exists else 'MISSING'} {env_result.path}")
        for status in credential_status():
            marker = "OK" if status.ok else "FALTAN"
            missing = ", ".join(status.missing) if status.missing else "-"
            print(f"{status.engine}: {marker} missing={missing}")
        return

    if args.command == "llm-check":
        bridge = AulaTeXLLMClient()
        engines = args.engine or list(bridge.engines())
        for engine in engines:
            result = bridge.check(engine)
            print(f"{result.engine}: {'OK' if result.ok else 'ERROR'} {result.text or result.error}")
        return

    if args.command in ("llm-validate", "llm-config"):
        repair = args.command == "llm-config" or args.configure_on_failure
        if repair:
            if args.command == "llm-validate" and args.engine != MODEL_ROUTER_ENGINE:
                parser.error("--configure-on-failure solo está disponible para model-router.")
            from .llm_setup import configure_model_router

            payload = configure_model_router(
                timeout_seconds=args.timeout_seconds, max_tokens=args.max_tokens,
                non_interactive=bool(getattr(args, "non_interactive", False)),
            )
        else:
            payload = validate_llm_response(
                args.engine, timeout_seconds=args.timeout_seconds, max_tokens=args.max_tokens,
            )
        print(json.dumps(payload, ensure_ascii=False))
        if not payload["ok"]:
            raise SystemExit(1)
        return

    if args.command == "llm-tokenize":
        prompt_text = _resolve_prompt_text(args.prompt, args.prompt_file)
        result = count_text_tokens(args.engine, prompt_text)
        print(
            json.dumps(
                {
                    "engine": result.engine,
                    "deployment": result.deployment,
                    "token_count": result.token_count,
                    "tokenizer_source": result.tokenizer_source,
                    "tokenizer_name": result.tokenizer_name,
                    "approximate": result.approximate,
                    "note": result.note,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "llm-prompt":
        prompt_text = _resolve_prompt_text(args.prompt, args.prompt_file)
        result = AulaTeXLLMClient().call(
            args.engine,
            prompt_text,
            max_tokens=args.max_tokens,
            timeout_seconds=args.timeout_seconds,
        )
        if not result.ok:
            raise SystemExit(f"{result.engine}: {result.error}")
        print(result.text)
        return

    if args.command == "agent":
        request = AgentRequest(
            target=args.target,
            level=args.level,
            action=args.action,
            activity_number=args.activity,
            generation_mode=args.generation_mode,
            parent_scope_key=args.parent_scope_key,
            child_level=args.child_level,
            child_name=args.child_name,
            engines=args.engine or ["Codex", "Claude Foundry", "GPT-Pro", "Auto (model-router)"],
            iterations=args.iterations,
            cycle_mode=args.cycle_mode,
            compile_tex=not args.no_compile,
            apply_feedback=args.apply_feedback,
            run_extractor=bool(args.run_extractor),
            skip_extractor=bool(args.no_extractor),
            extractor_probe_only=bool(args.extractor_probe),
            extractor_fuentes=args.extractor_fuentes,
            extractor_planeacion=args.extractor_planeacion,
            extractor_conceptos=args.extractor_conceptos,
            extractor_salida=args.extractor_salida,
            extractor_motor=args.extractor_motor,
            run_detail_planner=not bool(args.no_detail_planner),
            detail_planner_max_scopes=args.detail_max_scopes,
            run_monitor=not bool(args.no_monitor),
            run_optimize=not bool(args.no_optimize),
            run_foro_producto=not bool(args.no_foro_producto),
            run_mapa_layout=not bool(args.no_mapa_layout),
            run_final_compile=not bool(args.no_final_compile),
            monitor_max_cycles=args.monitor_max_cycles,
            optimize_cycles=args.optimize_cycles,
            run_semantic_audit=not bool(args.no_semantic_audit),
            semantic_feedback_path=args.semantic_feedback,
        )
        result = AulaTeXAgent().run(request)
        print(json.dumps({
            "ok": result.ok,
            "run_dir": str(result.run_dir),
            "report": str(result.report_path),
            "monitor_ok": result.monitor_ok,
            "optimize_ok": result.optimize_ok,
            "quality_before": result.quality_before,
            "quality_after": result.quality_after,
            "optimize_plan_summary": result.optimize_plan_summary,
            "final_compile_ok": result.final_compile_ok,
            "semantic_blocking_before": result.semantic_blocking_before,
            "semantic_blocking_after": result.semantic_blocking_after,
            "semantic_audit_available": result.semantic_audit_available,
        }, ensure_ascii=False, indent=2))
        if not result.ok:
            raise SystemExit(1)
        return

    if args.command == "detail-planner":
        result = IncrementalDetailPlanner(AulaTeXWorkspace()).run(
            DetailPlannerRequest(
                target=args.target,
                activity_number=args.activity,
                output=args.output,
                max_scopes=args.max_scopes,
                max_fixed_point_passes=args.max_fixed_point_passes,
                persist_memory=not bool(args.no_persist_memory),
            )
        )
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "run_id": result.run_id,
                    "run_dir": str(result.run_dir),
                    "manifest": str(result.manifest_path),
                    "report": str(result.report_path),
                    "processed_scopes": list(result.processed_scopes),
                    "updated_scopes": list(result.updated_scopes),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "mass-editorial-runner":
        def emit_progress(event: dict) -> None:
            if bool(args.monitor):
                print(json.dumps(event, ensure_ascii=False), flush=True)

        result = MassEditorialRunner(AulaTeXWorkspace()).run(
            MassEditorialRunnerRequest(
                target=args.target,
                output=args.output,
                cycles_per_node=args.cycles_per_node,
                detail_max_scopes=args.detail_max_scopes,
                max_scopes=args.max_scopes,
                scope_offset=args.scope_offset,
                scope_level=args.scope_level,
                persist_memory=not bool(args.no_persist_memory),
                append_contract_index=bool(args.append_contract_index),
            ),
            progress_callback=emit_progress,
        )
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "run_id": result.run_id,
                    "run_dir": str(result.run_dir),
                    "progress": str(result.progress_path),
                    "proposals": str(result.proposals_path),
                    "proposals_jsonl": str(result.proposals_jsonl_path),
                    "contract_proposals": str(result.contract_proposals_path),
                    "report": str(result.report_path),
                    "processed_scopes": result.processed_scopes,
                    "failed_scopes": result.failed_scopes,
                    "scope_total": result.scope_total,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "editorial-memory":
        workspace = AulaTeXWorkspace()
        scope = workspace.find_scope_for_target(args.target, activity_number=args.activity or None)
        if scope is None:
            raise SystemExit(f"No se pudo resolver un scope editorial para: {args.target}")
        builder = EditorialMemoryBuilder(workspace=workspace, llm_bridge=AulaTeXLLMClient())
        request = EditorialMemoryRequest(
            source_scope_key=scope.key,
            build_level=args.build_level,
            propagation_mode=args.propagation_mode,
            iterations=args.iterations,
            engines=args.engine or ["Codex", "Claude Foundry", "GPT-Pro"],
            max_tokens=args.max_tokens,
            timeout_seconds=args.timeout_seconds,
            scope_offset=args.scope_offset,
            scope_limit=args.scope_limit,
        )

        if args.batch_size > 0 or args.resume_checkpoint:
            full_plan = builder.plan_scopes(scope.key, args.build_level, args.propagation_mode)
            if not full_plan:
                raise SystemExit("No se pudo calcular el plan editorial para la corrida por lotes.")

            checkpoint_path = _resolve_editorial_checkpoint_path(
                workspace,
                args.resume_checkpoint or args.checkpoint,
                scope_key=scope.key,
                build_level=args.build_level,
                propagation_mode=args.propagation_mode,
            )
            start_offset = max(0, int(args.scope_offset))
            end_offset = len(full_plan)
            if args.scope_limit > 0:
                end_offset = min(len(full_plan), start_offset + int(args.scope_limit))
            batch_size = max(1, int(args.batch_size or 1))

            checkpoint_payload: dict
            if args.resume_checkpoint:
                if not checkpoint_path.exists():
                    raise SystemExit(f"Checkpoint no encontrado: {checkpoint_path}")
                checkpoint_payload = _read_json(checkpoint_path)
                if checkpoint_payload.get("source_scope_key") != scope.key:
                    raise SystemExit("El checkpoint no corresponde al scope editorial solicitado.")
                start_offset = max(start_offset, int(checkpoint_payload.get("next_scope_offset", start_offset)))
                end_offset = min(end_offset, int(checkpoint_payload.get("end_scope_offset", end_offset)))
                batch_size = max(1, int(checkpoint_payload.get("batch_size", batch_size)))
            else:
                checkpoint_payload = {
                    "mode": "editorial-memory-batch",
                    "status": "running",
                    "source_scope_key": scope.key,
                    "build_level": args.build_level,
                    "propagation_mode": args.propagation_mode,
                    "iterations": int(args.iterations),
                    "engines": request.engines,
                    "max_tokens": int(args.max_tokens),
                    "timeout_seconds": int(args.timeout_seconds),
                    "plan_scope_count": len(full_plan),
                    "start_scope_offset": start_offset,
                    "end_scope_offset": end_offset,
                    "next_scope_offset": start_offset,
                    "batch_size": batch_size,
                    "checkpoint_path": str(checkpoint_path),
                    "batches": [],
                }
                _write_json(checkpoint_path, checkpoint_payload)

            if start_offset >= end_offset:
                checkpoint_payload["status"] = "completed"
                checkpoint_payload["next_scope_offset"] = end_offset
                _write_json(checkpoint_path, checkpoint_payload)
                print(
                    json.dumps(
                        {
                            "ok": True,
                            "completed": True,
                            "checkpoint": str(checkpoint_path),
                            "processed_scopes": 0,
                            "next_scope_offset": end_offset,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                return

            offset = start_offset
            last_result = None
            executed_batches = 0
            while offset < end_offset:
                if args.max_batches > 0 and executed_batches >= int(args.max_batches):
                    checkpoint_payload["status"] = "paused"
                    break
                current_limit = min(batch_size, end_offset - offset)
                batch_request = EditorialMemoryRequest(
                    source_scope_key=scope.key,
                    build_level=args.build_level,
                    propagation_mode=args.propagation_mode,
                    iterations=args.iterations,
                    engines=request.engines,
                    max_tokens=args.max_tokens,
                    timeout_seconds=args.timeout_seconds,
                    scope_offset=offset,
                    scope_limit=current_limit,
                )
                result = builder.build(batch_request)
                processed_scopes = len(result.built_scopes)
                next_offset = offset + processed_scopes
                checkpoint_payload["batches"].append(
                    {
                        "scope_offset": offset,
                        "scope_limit": current_limit,
                        "processed_scopes": processed_scopes,
                        "ok": result.ok,
                        "cancelled": result.cancelled,
                        "run_dir": str(result.run_dir),
                        "manifest": str(result.manifest_path),
                    }
                )
                checkpoint_payload["next_scope_offset"] = next_offset
                checkpoint_payload["last_run_dir"] = str(result.run_dir)
                checkpoint_payload["last_manifest"] = str(result.manifest_path)
                checkpoint_payload["status"] = "running" if result.ok and not result.cancelled else "stopped"
                _write_json(checkpoint_path, checkpoint_payload)
                last_result = result
                executed_batches += 1
                if not result.ok or result.cancelled or processed_scopes <= 0:
                    break
                offset = next_offset

            finished = int(checkpoint_payload.get("next_scope_offset", start_offset)) >= end_offset
            checkpoint_payload["status"] = "completed" if finished else checkpoint_payload.get("status", "stopped")
            _write_json(checkpoint_path, checkpoint_payload)
            print(
                json.dumps(
                    {
                        "ok": bool(finished and last_result is not None and last_result.ok),
                        "completed": finished,
                        "checkpoint": str(checkpoint_path),
                        "next_scope_offset": checkpoint_payload["next_scope_offset"],
                        "end_scope_offset": end_offset,
                        "batch_size": batch_size,
                        "batches_executed": len(checkpoint_payload["batches"]),
                        "last_run_dir": checkpoint_payload.get("last_run_dir", ""),
                        "last_manifest": checkpoint_payload.get("last_manifest", ""),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return

        result = builder.build(request)
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "run_dir": str(result.run_dir),
                    "manifest": str(result.manifest_path),
                    "built_scopes": list(result.built_scopes),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "extractor":
        adapter = ExtractorAdapter(AulaTeXWorkspace())
        request = ExtractorRequest(
            target=args.target,
            activity_number=args.activity,
            fuentes=args.fuentes,
            planeacion=args.planeacion,
            conceptos=args.conceptos,
            salida=args.salida,
            motor=args.motor,
            recursive=bool(args.recursivo),
            top_k=args.top_k,
            max_citas=args.max_citas,
            probe_only=bool(args.probe),
            timeout_seconds=args.timeout_seconds,
        )
        if args.preview:
            print(adapter.preview_markdown(request))
            return
        result = adapter.run(request)
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "run_dir": str(result.run_dir),
                    "manifest": str(result.manifest_path),
                    "output_dir": str(result.output_dir),
                    "stdout": str(result.stdout_path),
                    "stderr": str(result.stderr_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "activity-observe":
        result = ActivityObserver(AulaTeXWorkspace()).observe(
            ActivityObservationRequest(
                target=args.target,
                activity_number=args.activity,
                output=args.output,
                compile_check=bool(args.compile_check),
            )
        )
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "run_dir": str(result.run_dir),
                    "state": str(result.state_path),
                    "evaluation": str(result.evaluation_path),
                    "actions": str(result.actions_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "activity-monitor":
        result = ActivityMonitor(AulaTeXWorkspace()).run(
            ActivityMonitorRequest(
                target=args.target,
                activity_number=args.activity,
                output=args.output,
                max_cycles=args.max_cycles,
                compile_check=bool(args.compile_check),
                run_extractor=bool(args.run_extractor),
                extractor_motors=tuple(args.extractor_motor or ["anthropicfoundry", "tfidf"]),
                apply_bibliography_repair=bool(args.apply_bibliography_repair),
                apply_revision_patches=not bool(args.no_apply_revision_patches),
                backup_bibliography=not bool(args.no_bibliography_backup),
                backup_revision=not bool(args.no_revision_backup),
                stop_on_blocker=not bool(args.keep_going),
                workflow_backend=args.workflow_backend,
                run_detail_planner=not bool(args.no_detail_planner),
                detail_planner_max_scopes=args.detail_max_scopes,
            )
        )
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "run_dir": str(result.run_dir),
                    "manifest": str(result.manifest_path),
                    "report": str(result.report_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "activity-optimize":
        result = ActivityOptimizer(AulaTeXWorkspace()).optimize(
            ActivityOptimizeRequest(
                target=args.target,
                activity_number=args.activity,
                output=args.output,
                cycles=args.cycles,
                target_quality=args.target_quality,
                max_cycles=args.max_cycles,
                stall_limit=args.stall_limit,
                engines=tuple(args.engine or ["GPT-5.6-Luna", "GPT-5.6-Terra"]),
                max_tokens=args.max_tokens,
                backup=not bool(args.no_backup),
                require_contract_100=not bool(args.allow_incomplete_contract),
                run_semantic_audit=not bool(args.no_semantic_audit),
                semantic_feedback_path=args.semantic_feedback,
                use_quality_panel=bool(args.quality_panel),
                panel_llm_judge=not bool(args.no_panel_llm_judge),
                reward_model_dir=args.reward_model_dir,
            )
        )
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "run_dir": str(result.run_dir),
                    "manifest": str(result.manifest_path),
                    "report": str(result.report_path),
                    "stop_mode": ("fixed-cycles" if int(args.cycles) > 0 else "converge-to-quality"),
                    "target_quality": args.target_quality,
                    "applied_cycles": result.applied_cycles,
                    "quality_before": result.quality_before,
                    "quality_after": result.quality_after,
                    "converged": bool(
                        result.ok
                        and result.quality_after >= args.target_quality
                        and result.semantic_blocking_after == 0
                    ),
                    "semantic_blocking_before": result.semantic_blocking_before,
                    "semantic_blocking_after": result.semantic_blocking_after,
                    "semantic_audit_available": result.semantic_audit_available,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "foro-producto":
        from .foro_producto import ForoProductoRequest, ForoProductoTransformer

        result = ForoProductoTransformer(AulaTeXWorkspace()).run(
            ForoProductoRequest(
                target=args.target,
                activity_number=args.activity,
                apply=bool(args.apply),
                output=args.output,
            )
        )
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "applied": result.applied,
                    "is_foro": result.is_foro,
                    "tex": str(result.tex_path) if result.tex_path else "",
                    "txt": str(result.txt_path) if result.txt_path else "",
                    "reason": result.reason,
                    "changes": result.changes,
                    "warnings": result.warnings,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "activity-revise":
        result = ActivityReviser(AulaTeXWorkspace()).revise(
            ActivityRevisionRequest(
                target=args.target,
                activity_number=args.activity,
                output=args.output,
                apply=bool(args.apply),
                backup=not bool(args.no_backup),
                workflow_backend=args.workflow_backend,
            )
        )
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "run_dir": str(result.run_dir),
                    "plan": str(result.plan_path),
                    "report": str(result.report_path),
                    "patched_tex": str(result.patched_tex_path) if result.patched_tex_path else "",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "compilation-repair":
        result = CompilationRepairer(AulaTeXWorkspace()).repair(
            CompilationRepairRequest(
                target=args.target,
                activity_number=args.activity,
                output=args.output,
            )
        )
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "run_dir": str(result.run_dir),
                    "plan": str(result.plan_path),
                    "report": str(result.report_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "bibliography-repair":
        result = BibliographyRepairer(AulaTeXWorkspace()).repair(
            BibliographyRepairRequest(
                target=args.target,
                activity_number=args.activity,
                output=args.output,
                apply=bool(args.apply),
                backup=not bool(args.no_backup),
                min_confidence=args.min_confidence,
                workflow_backend=args.workflow_backend,
            )
        )
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "run_dir": str(result.run_dir),
                    "plan": str(result.plan_path),
                    "report": str(result.report_path),
                    "patched_tex": str(result.patched_tex_path) if result.patched_tex_path else "",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "investigation":
        workspace = AulaTeXWorkspace()
        scope = workspace.find_scope_for_target(args.target, activity_number=args.activity or None)
        if scope is None:
            raise SystemExit(f"No se pudo resolver un scope editorial para: {args.target}")
        builder = InvestigationBuilder(workspace=workspace, llm_bridge=AulaTeXLLMClient())
        request = InvestigationRequest(
            scope_key=scope.key,
            iterations=args.iterations,
            engines=args.engine or ["Codex", "Auto (model-router)", "Claude Foundry", "GPT-Pro"],
            max_tokens=args.max_tokens,
            search_terms=tuple(args.query or []),
            seed_urls=tuple(args.url or []),
        )
        result = builder.build(request)
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "cancelled": result.cancelled,
                    "run_dir": str(result.run_dir),
                    "manifest": str(result.manifest_path),
                    "knowledge": str(result.knowledge_path),
                    "bibliography": str(result.bibliography_path),
                    "web_sources": str(result.web_sources_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "generation":
        workspace = AulaTeXWorkspace()
        builder = ConstructionBuilder(workspace=workspace, llm_bridge=AulaTeXLLMClient())
        request = ConstructionRequest(
            parent_scope_key=args.parent_scope_key,
            node_level=args.node_level,
            node_name=args.node_name,
            activity_number=args.activity,
            operation_mode=args.mode,
            destination_path=args.destination,
            ingest_text=args.ingest_text,
            ingest_document_path=args.ingest_document,
            engines=args.engine or ["Codex", "Auto (model-router)", "Claude Foundry", "GPT-Pro"],
            iterations=args.iterations,
            max_tokens=args.max_tokens,
        )
        result = builder.build(request)
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "cancelled": result.cancelled,
                    "run_dir": str(result.run_dir),
                    "manifest": str(result.manifest_path),
                    "node_dir": str(result.node_dir),
                    "memory": str(result.memory_path),
                    "plan": str(result.plan_path),
                    "maqueta": str(result.maqueta_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "intelligent-engine":
        reporter = resolve_reporter(bool(getattr(args, "progress", False)))
        default_actions = IntelligentEngineRequest().actions
        result = IntelligentEngine(AulaTeXWorkspace()).run(
            IntelligentEngineRequest(
                target=args.target,
                activity_number=args.activity,
                output=args.output,
                backend=args.backend,
                max_targets=args.max_targets,
                audit_path=args.audit,
                include_reports=not bool(args.no_reports),
                include_presentations=not bool(args.no_presentations),
                engines=tuple(args.engine or IntelligentEngineRequest().engines),
                execute=bool(getattr(args, "execute", False)),
                actions=tuple(args.action) if getattr(args, "action", None) else default_actions,
                monitor_max_cycles=int(getattr(args, "monitor_max_cycles", 1)),
                optimize_cycles=int(getattr(args, "optimize_cycles", 0)),
            ),
            reporter=reporter,
        )
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "run_id": result.run_id,
                    "run_dir": str(result.run_dir),
                    "manifest": str(result.manifest_path),
                    "report": str(result.report_path),
                    "executed": result.executed,
                    "execution_ok": result.execution_ok,
                    "optimize_plan_summaries": _collect_execution_optimize_plan_summaries(result.execution_summary),
                    "execution_summary": result.execution_summary,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        if not result.ok or (result.executed and not result.execution_ok):
            raise SystemExit(1)
        return

    if args.command == "calibrar-actividad":
        request = CalibrationRequest(
            target=args.target,
            activity_number=args.activity,
            feedback_path=args.feedback,
            output=args.output,
            max_rounds=args.max_rounds,
            engines=tuple(args.engine or ("GPT-5.6-Terra",)),
            monitor_max_cycles=args.monitor_max_cycles,
            optimize_cycles=args.optimize_cycles,
            max_tokens=args.max_tokens,
        )
        result = ActivityCalibration(AulaTeXWorkspace()).run(request)
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "run_id": result.run_id,
                    "run_dir": str(result.run_dir),
                    "manifest": str(result.manifest_path),
                    "target": result.target,
                    "activity_number": result.activity_number,
                    "rounds": [asdict(item) for item in result.rounds],
                    "semantic_blocking": (
                        len(result.final_audit.blocking_findings)
                        if result.final_audit
                        else None
                    ),
                    "promotion_ok": result.promotion_ok,
                    "promoted_scope_keys": list(result.promoted_scope_keys),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "calibrar-motor":
        result = ActivityCalibration(AulaTeXWorkspace()).calibrate_motor(
            MotorCalibrationRequest(
                feedback_path=args.feedback,
                target_context=args.target_context,
                target=args.target,
                activity_number=args.activity,
                output=args.output,
                max_rounds=args.max_rounds,
                engines=tuple(args.engine or ("GPT-5.6-Terra",)),
                monitor_max_cycles=args.monitor_max_cycles,
                optimize_cycles=args.optimize_cycles,
            )
        )
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "run_id": result.run_id,
                    "rules_path": str(result.rules_path),
                    "manifest": str(result.manifest_path),
                    "rules_added": list(result.rules),
                    "self_test_ok": result.self_test_ok,
                    "self_test_rounds": list(result.self_test_rounds),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "compile":
        result = AulaTeXWorkspace().compile_tex(args.tex)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        raise SystemExit(result.returncode)

    if args.command == "mapa-layout":
        import subprocess as _sp
        import sys as _sys
        _script = Path(__file__).resolve().parents[1] / "optimize_mapa_layout.py"
        _cmd = [
            _sys.executable, str(_script), args.tex,
            "--iters", str(args.iters),
            "--repulsion", str(args.repulsion),
            "--step", str(args.step),
            "--spring", str(args.spring),
            "--xlim", str(args.xlim),
            "--ylim", str(args.ylim),
            "--target-aspect", str(args.target_aspect),
            "--vspread", str(args.vspread),
            "--hspread", str(args.hspread),
            "--label-clearance", str(args.label_clearance),
            "--out-dir", args.out_dir,
        ]
        if args.write:
            _cmd.append("--write")
        raise SystemExit(_sp.run(_cmd).returncode)

    parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
