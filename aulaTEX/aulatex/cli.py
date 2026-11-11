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
    supervised = sub.add_parser("supervised-activity", help="Run a bounded GPT-5-mini activity stage with authenticated ITESCA sources and evidence.")
    supervised.add_argument("--out", required=True)
    supervised.add_argument("--root", default=str(Path.cwd()))
    supervised.add_argument("--stage", required=True, choices=["portal", "prepare", "research", "plan", "draft", "evaluate", "revise", "build", "visual", "finalize", "all"])

    planning = sub.add_parser("generar-planeaciones", help="Normalizar planeaciones JSON en carpetas versionables de la materia; sin generación pedagógica automática.")
    planning.add_argument("target", help="Carpeta existente de la materia.")
    planning.add_argument("--source", required=True, help="Modelo JSON revisado con activity o activities y sus fuentes.")
    planning.add_argument("--index-name", default="README.md", help="Nombre del índice generado; permite conservar un README por unidades.")

    node_planning = sub.add_parser("planeacion-nodos", help="Preparar, validar o publicar planeaciones por nodo; no ejecuta actividades.")
    node_planning.add_argument("--root", default=str(Path.cwd()))
    node_planning.add_argument("--mode", choices=("prepare", "validate", "publish"), default="prepare")
    node_planning.add_argument("--output", default="", help="Carpeta nueva para el manifiesto JSON y Markdown de preparacion.")
    node_planning.add_argument("--source", default="", help="JSON por nodo, dentro del proyecto.")
    node_planning.add_argument("--scope-key", default="", help="Identidad exacta del nodo para validar/publicar.")

    convert_planning = sub.add_parser("convertir-planeaciones", help="Convertir fuentes locales a PCA needs_review y generar cotejo; no aprueba ni ejecuta actividades.")
    convert_planning.add_argument("--root", default=str(Path.cwd()))
    convert_planning.add_argument("--target", default=".", help="Institucion, carrera o materia que se va a convertir.")
    convert_planning.add_argument("--output", required=True, help="Carpeta nueva para el manifiesto del lote.")
    convert_planning.add_argument("--publish-node-bindings", action="store_true", help="Publicar cadenas de nodo needs_review solo para correspondencias documentadas y unicas.")

    review_planning = sub.add_parser("cotejar-planeaciones", help="Cotejar cada actividad del lote y publicar indice JSON y Markdown sin ejecutar.")
    review_planning.add_argument("--root", default=str(Path.cwd()))
    review_planning.add_argument("--batch", required=True)
    review_planning.add_argument("--output", required=True)
    review_planning.add_argument("--revision", action="append", default=[], help="PCA publicada que sustituye explicitamente una revision del lote en el cotejo.")

    diagnostic_planning = sub.add_parser("monitor-planeaciones", help="Observar hashes y bloqueos de un cotejo en una instantanea JSON y Markdown; no ejecuta actividades.")
    diagnostic_planning.add_argument("--root", default=str(Path.cwd()))
    diagnostic_planning.add_argument("--review", required=True)
    diagnostic_planning.add_argument("--output", required=True)

    publish_review = sub.add_parser("publicar-revision-planeacion", help="Publicar una PCA revisada e inmutable; ready requiere evidencia y validacion.")
    publish_review.add_argument("--root", default=str(Path.cwd()))
    publish_review.add_argument("--scope-key", required=True)
    publish_review.add_argument("--source", required=True)

    pilot_planning = sub.add_parser("campana-planeaciones", help="Preparar admision piloto de revisiones validadas; no ejecuta ni envia.")
    pilot_planning.add_argument("--root", default=str(Path.cwd()))
    pilot_planning.add_argument("--review", required=True)
    pilot_planning.add_argument("--output", required=True)
    pilot_planning.add_argument("--max-activities", type=int, default=1)
    pilot_planning.add_argument("--max-cycles", type=int, default=1)

    run_pilot = sub.add_parser("ejecutar-campana-planeaciones", help="Revalidar y ejecutar un piloto admitido, sin aplicar parches ni enviar a plataforma.")
    run_pilot.add_argument("--root", default=str(Path.cwd()))
    run_pilot.add_argument("--campaign", required=True)
    run_pilot.add_argument("--output", required=True)

    catalog = sub.add_parser("catalogo-plantillas", help="Auditar plantillas, estructura y temporales sin regenerar ni borrar documentos.")
    catalog.add_argument("--root", default=str(Path.cwd()), help="Raiz del repositorio que se va a revisar.")
    catalog.add_argument("--export", action="store_true", help="Actualizar catalogo-plantillas-aulatex.json y la auditoria en README.md.")

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
    agent.add_argument("--node-plan", default="", help="Planeacion por nodo relativa al proyecto; realizar-actividad exige perfiles validados.")
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
    activity_monitor.add_argument("--node-plan", default="", help="Revision JSON de nodo ready; revalida consigna y hashes antes del monitor.")
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

    flujo_uas = sub.add_parser("flujo-uas", help="Ejecutar el flujo de trabajo académico secuencial para UAS orquestado por aulatex.")
    flujo_uas.add_argument("--subject", default="derecho-mercantil", help="Slug o nombre de la materia UAS.")
    flujo_uas.add_argument("--course-id", type=int, default=632, help="ID del curso en la plataforma virtual UAS.")
    flujo_uas.add_argument("--module-id", type=int, default=49882, help="ID del módulo / actividad en UAS.")
    flujo_uas.add_argument("--activity", type=int, default=2, help="Número de actividad.")
    flujo_uas.add_argument("--week", type=int, default=2, help="Semana curricular.")
    flujo_uas.add_argument("--topic", default="Sujetos del Derecho, personas físicas y morales, sanción, hechos y actos jurídicos")
    flujo_uas.add_argument("--student-name", default="Martín Jonathan De La Cruz Muñoz")
    flujo_uas.add_argument("--student-id", default="26031061")
    flujo_uas.add_argument("--advisor", default="Por confirmar")
    flujo_uas.add_argument("--group", default="LCP-2026-I")
    flujo_uas.add_argument("--city", default="Culiacán, Sinaloa, México")
    flujo_uas.add_argument("--engine", default="xelatex", choices=("xelatex", "pdflatex", "latexmk"))
    flujo_uas.add_argument("--no-download", action="store_true", help="No intentar descarga remota; usar fuentes locales.")
    flujo_uas.add_argument("--output", default="", help="Directorio personalizado de salida.")
    flujo_uas.add_argument("--check-only", action="store_true", help="Solo verificar precondiciones y credenciales.")
    flujo_uas.add_argument("--json", action="store_true", help="Emitir resultado completo en JSON.")
    flujo_uas.add_argument("--pending", action="store_true", help="Ejecutar monitor-uas y secuencialmente realizar entregas pendientes.")
    flujo_uas.add_argument("--inspect", action="store_true", help="Inspeccionar plataforma UAS en vivo.")
    flujo_uas.add_argument("--no-compile", action="store_true", help="No compilar manuscritos TeX.")

    sitio_lex = sub.add_parser("diseno-sitio-lex", aliases=["sitio-lex"], help="Auditar, verificar y sincronizar el portal nativo de Lex Contable en Google Sites.")
    sitio_lex.add_argument("--url", default="", help="URL pública a auditar.")
    sitio_lex.add_argument("--no-compile", action="store_true", help="No recompilar reporte TeX.")
    sitio_lex.add_argument("--json", action="store_true", help="Emitir salida en formato JSON.")

    itesca_wf = sub.add_parser("itesca-workflow", help="Ejecutar el flujo de trabajo académico para ITESCA orquestado por aulatex.")
    itesca_wf.add_argument("--snapshot", default="", help="Ruta al snapshot JSON sanitizado de navegación ITESCA.")
    itesca_wf.add_argument("--activity", type=int, default=0, help="Filtrar por número de actividad específico (7, 8, 9, 15).")
    itesca_wf.add_argument("--no-download", action="store_true", help="No intentar descarga remota; usar material docente ya descargado.")
    itesca_wf.add_argument("--force-reextract", action="store_true", help="Forzar re-ejecución del extractor de conceptos.")
    itesca_wf.add_argument("--use-llm-style", action="store_true", help="Permitir refinamiento de voz con LLM en estilo-escribir.")
    itesca_wf.add_argument("--stage", action="append", default=[], help="Etapas a ejecutar (planeacion, recopilacion_y_organizacion_de_recursos, extraccion_de_conceptos, realizacion_de_actividades_y_ciclos_de_calidad).")

    nav_it = sub.add_parser("navegacion-itesca", help="Inspeccionar plataforma ITESCA Virtual de forma autenticada y solo lectura.")
    nav_it.add_argument("--course-id", action="append", type=int, default=[], help="ID de curso Moodle (ej. 209, 215).")
    nav_it.add_argument("--module-id", action="append", type=int, default=[], help="ID de módulo Moodle (ej. 1761, 1762, 1763, 2915).")
    nav_it.add_argument("--output", default="", help="Ruta de salida para el snapshot JSON sanitizado.")

    plan_it = sub.add_parser("realizar-planeacion-itesca", help="Generar planeación canónica ITESCA desde evidencia verificada.")
    plan_it.add_argument("--target", required=True, help="Carpeta de la materia objetivo.")
    plan_it.add_argument("--activity", type=int, required=True, help="Número de actividad.")
    plan_it.add_argument("--snapshot", required=True, help="Ruta al snapshot JSON de navegación.")

    rec_it = sub.add_parser("encontrar-recursos-itesca", help="Localizar, descargar y organizar recursos de actividad ITESCA.")
    rec_it.add_argument("--target", required=True, help="Carpeta de la materia objetivo.")
    rec_it.add_argument("--activity", type=int, required=True, help="Número de actividad.")
    rec_it.add_argument("--plan", default="", help="Ruta al archivo JSON de planeación.")
    rec_it.add_argument("--no-download", action="store_true")

    conc_it = sub.add_parser("extraer-conceptos-itesca", help="Extraer conceptos académicos para actividad ITESCA.")
    conc_it.add_argument("--target", required=True)
    conc_it.add_argument("--activity", type=int, required=True)
    conc_it.add_argument("--plan", default="")
    conc_it.add_argument("--motor", default="novapro")
    conc_it.add_argument("--force", action="store_true")

    act_it = sub.add_parser("realizar-actividad-itesca", help="Desarrollar actividad ITESCA con plantillas y ciclos de calidad.")
    act_it.add_argument("--target", required=True)
    act_it.add_argument("--activity", type=int, required=True)
    act_it.add_argument("--plan", default="")
    act_it.add_argument("--delivery-source", default="")
    act_it.add_argument("--delivery-target", default="")
    act_it.add_argument("--expected-pages", type=int, default=0)
    act_it.add_argument("--expected-arial", type=float, default=0.0)
    act_it.add_argument("--docx-deliverable", default="")

    estilo_it = sub.add_parser("estilo-escribir-eval", help="Auditar estilo académico en archivos .tex o .docx.")
    estilo_it.add_argument("--tex", default="")
    estilo_it.add_argument("--docx", default="")
    estilo_it.add_argument("--bib", default="")
    estilo_it.add_argument("--apply", action="store_true")

    itesca_pending = sub.add_parser("itesca-pending", aliases=["monitor-itesca"], help="Auditar y validar entregas pendientes en ITESCA orquestadas por aulatex.")
    itesca_pending.add_argument("--subject", default="all", help="Slug de la materia ITESCA ('all', 'estadistica-aplicada-para-la-administracion', 'seminario-i').")
    itesca_pending.add_argument("--course-id", type=int, default=None, help="ID del curso en ITESCA.")
    itesca_pending.add_argument("--snapshot", default="", help="Ruta al snapshot de navegación local.")
    itesca_pending.add_argument("--inspect", action="store_true", help="Inspeccionar plataforma ITESCA en vivo.")
    itesca_pending.add_argument("--output", default="", help="Directorio de salida.")
    itesca_pending.add_argument("--json", action="store_true", help="Emitir salida en JSON.")
    itesca_pending.add_argument("--run-workflow", action="store_true", help="Ejecutar el flujo completo de agentes (consulta, planeaciones, recursos, conceptos, realizar-actividad) antes de compilar el informe.")

    itesca_entrega = sub.add_parser("itesca-entrega", aliases=["entregar-itesca"], help="Envío autenticado de entregables a ITESCA tras autorización explícita.")
    itesca_entrega.add_argument("--subject", required=True, help="Slug de la materia ITESCA.")
    itesca_entrega.add_argument("--activity", type=int, required=True, help="Número de actividad.")
    itesca_entrega.add_argument("--artifact", default="", help="Ruta del entregable local (.pdf/.docx). Si se omite, se infiere del catálogo.")
    itesca_entrega.add_argument("--user-validated", action="store_true", help="Autorización explícita obligatoria del usuario (user_validated=True).")
    itesca_entrega.add_argument("--sha256", default=None, help="SHA-256 esperado.")
    itesca_entrega.add_argument("--course-id", type=int, default=None, help="ID del curso en ITESCA.")
    itesca_entrega.add_argument("--module-id", type=int, default=None, help="ID del módulo en ITESCA.")
    itesca_entrega.add_argument("--finalize", action="store_true", help="Marcar como envío definitivo ('Enviar para calificar').")
    itesca_entrega.add_argument("--live", dest="dry_run", action="store_false", help="Envío en vivo a plataforma (por omisión --dry-run está activo).")
    itesca_entrega.set_defaults(dry_run=True)
    itesca_entrega.add_argument("--output", default="", help="Directorio de comprobantes.")
    itesca_entrega.add_argument("--json", action="store_true", help="Emitir salida en JSON.")

    uas_pending = sub.add_parser("uas-pending", aliases=["monitor-uas"], help="Auditar y realizar entregas pendientes en UAS orquestadas por aulatex.")
    uas_pending.add_argument("--subject", default="derecho-mercantil", help="Slug de la materia UAS (o 'all'/'todas').")
    uas_pending.add_argument("--course-id", type=int, default=None, help="ID del curso en UAS.")
    uas_pending.add_argument("--inspect", action="store_true", help="Inspeccionar plataforma en vivo.")
    uas_pending.add_argument("--download", action="store_true", help="Descargar recursos remotos.")
    uas_pending.add_argument("--no-compile", action="store_true", help="No compilar manuscritos TeX.")
    uas_pending.add_argument("--output", default="", help="Directorio de salida.")
    uas_pending.add_argument("--json", action="store_true", help="Emitir salida en JSON.")

    uas_entrega = sub.add_parser("uas-entrega", aliases=["entregar-uas"], help="Envio autenticado de entregables a UAS tras autorizacion explicita.")
    uas_entrega.add_argument("--subject", required=True, help="Slug de la materia UAS.")
    uas_entrega.add_argument("--activity", type=int, required=True, help="Numero de actividad.")
    uas_entrega.add_argument("--artifact", required=True, help="Ruta del entregable local (.pdf/.xlsx).")
    uas_entrega.add_argument("--user-validated", action="store_true", help="Autorizacion explicita obligatoria del usuario.")
    uas_entrega.add_argument("--sha256", default=None, help="SHA-256 esperado.")
    uas_entrega.add_argument("--course-id", type=int, default=None, help="ID del curso en UAS.")
    uas_entrega.add_argument("--module-id", type=int, default=None, help="ID del modulo en UAS.")
    uas_entrega.add_argument("--finalize", action="store_true", help="Marcar como envio definitivo.")
    uas_entrega.add_argument("--live", dest="dry_run", action="store_false", help="Envio en vivo (por defecto dry_run=True).")
    uas_entrega.set_defaults(dry_run=True)
    uas_entrega.add_argument("--output", default="", help="Directorio de comprobantes.")
    uas_entrega.add_argument("--json", action="store_true", help="Emitir salida en JSON.")

    unadm_wf = sub.add_parser("unadm-workflow", help="Ejecutar el flujo de trabajo académico secuencial para UnADM orquestado por aulatex.")
    unadm_wf.add_argument("--subject", default="derecho-penal-especial-mexicano", help="Slug o nombre de la materia UnADM.")
    unadm_wf.add_argument("--activity", type=int, default=1, help="Número de actividad (ej. 1, 2, 3).")
    unadm_wf.add_argument("--course-id", type=int, default=None, help="ID del curso en la plataforma virtual UnADM (ej. 3482, 3432, 3441).")
    unadm_wf.add_argument("--module-id", type=int, default=None, help="ID del módulo / asignación en UnADM.")
    unadm_wf.add_argument("--no-inspect", action="store_true", help="No inspeccionar la plataforma en línea; usar planeaciones/recursos locales.")
    unadm_wf.add_argument("--no-download", action="store_true", help="No intentar descarga remota; usar material docente ya descargado.")
    unadm_wf.add_argument("--no-compile", action="store_true", help="No compilar el PDF final con LaTeX.")
    unadm_wf.add_argument("--use-llm-style", action="store_true", help="Permitir refinamiento de voz con LLM en estilo-escribir.")
    unadm_wf.add_argument("--pending", action="store_true", help="Ejecutar monitor-unadm y posteriormente realizar-actividad para todas las entregas pendientes identificadas.")
    unadm_wf.add_argument("--submit-to-platform", action="store_true", help="Solicitar el envío a la plataforma UnADM al finalizar.")
    unadm_wf.add_argument("--user-validated", action="store_true", help="Validación explícita del usuario requerida para enviar a plataforma.")
    unadm_wf.add_argument("--output", default="", help="Directorio personalizado de salida para la corrida.")

    nav_unadm = sub.add_parser("navegacion-unadm", help="Inspeccionar plataforma UnADM Virtual (aulavirtual.unadmexico.mx) de forma autenticada y solo lectura.")
    nav_unadm.add_argument("--course-id", action="append", type=int, default=[], help="ID de curso Moodle UnADM (ej. 3482, 3432, 3441).")
    nav_unadm.add_argument("--output", default="", help="Ruta de salida para el snapshot JSON sanitizado.")

    mon_unadm = sub.add_parser("monitor-unadm", help="Monitorear entregas pendientes y recomendaciones en UnADM.")
    mon_unadm.add_argument("--subject", default="derecho-penal-especial-mexicano", help="Slug de la materia UnADM.")
    mon_unadm.add_argument("--activity", type=int, default=None, help="Número de actividad a monitorear.")
    mon_unadm.add_argument("--course-id", type=int, default=None, help="ID de curso en UnADM.")
    mon_unadm.add_argument("--module-id", type=int, default=None, help="ID del módulo en UnADM.")
    mon_unadm.add_argument("--inspect", action="store_true", help="Inspeccionar plataforma en línea si faltan datos.")
    mon_unadm.add_argument("--output", default="", help="Directorio de salida.")

    ent_unadm = sub.add_parser("entregar-unadm", help="Enviar actividad formalmente a UnADM (requiere validación explícita).")
    ent_unadm.add_argument("--subject", default="derecho-penal-especial-mexicano", help="Slug de la materia UnADM.")
    ent_unadm.add_argument("--activity", type=int, default=1, help="Número de actividad.")
    ent_unadm.add_argument("--artifact", default="", help="Ruta al artefacto PDF.")
    ent_unadm.add_argument("--sha256", default="", help="Hash SHA-256 esperado.")
    ent_unadm.add_argument("--course-id", type=int, default=None, help="ID de curso en UnADM.")
    ent_unadm.add_argument("--module-id", type=int, default=None, help="ID de tarea en UnADM.")
    ent_unadm.add_argument("--user-validated", action="store_true", help="Validación explícita del usuario (OBLIGATORIA para permitir envío).")
    ent_unadm.add_argument("--finalize", action="store_true", help="Enviar definitivamente para calificar en vez de borrador.")
    ent_unadm.add_argument("--live", action="store_true", help="Ejecutar en vivo con navegador en vez de simulación dry-run.")
    ent_unadm.add_argument("--output", default="", help="Directorio de salida.")

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
        from .gui import enable_high_dpi_awareness, main as gui_main

        enable_high_dpi_awareness()
        gui_main(diagnostics_enabled=bool(getattr(args, "diagnostics", False)))
        return

    if args.command == "catalogo-plantillas":
        from .template_catalog import build_template_catalog, export_catalog, render_catalog_markdown

        try:
            workspace = AulaTeXWorkspace(Path(args.root).resolve())
            catalog = build_template_catalog(workspace)
            if args.export:
                paths = export_catalog(workspace, catalog)
                print(json.dumps({"subjects": len(catalog["subjects"]), "candidates": len(catalog["artifacts"]),
                                  "issues": len(catalog["issues"]), "exports": [str(path) for path in paths]},
                                 ensure_ascii=False, indent=2))
            else:
                print(render_catalog_markdown(catalog))
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        return

    if args.command in {"cotejar-planeaciones", "publicar-revision-planeacion", "campana-planeaciones", "ejecutar-campana-planeaciones", "monitor-planeaciones"}:
        from .planning_conversion import publish_conversion
        from .planning_review import observe_planning, prepare_campaign, review_batch, run_campaign
        from jsonschema import ValidationError

        workspace = AulaTeXWorkspace(args.root)
        try:
            if args.command == "cotejar-planeaciones":
                result = review_batch(workspace, args.batch, workspace.resolve_target(args.output), revisions=tuple(args.revision))
                result = {"counts": result["counts"], "automatic_execution": False}
            elif args.command == "campana-planeaciones":
                result = prepare_campaign(workspace, args.review, workspace.resolve_target(args.output), max_activities=args.max_activities, max_cycles=args.max_cycles)
            elif args.command == "ejecutar-campana-planeaciones":
                result = run_campaign(workspace, args.campaign, workspace.resolve_target(args.output))
            elif args.command == "monitor-planeaciones":
                result = observe_planning(workspace, args.review, workspace.resolve_target(args.output))
                result = {"mode": result["mode"], "counts": result["counts"], "editorial_execution": False}
            else:
                scopes, _children = workspace.editorial_scope_index()
                scope = scopes[args.scope_key]
                if scope.level != "materia":
                    raise ValueError("publication_requires_subject")
                document = json.loads(workspace.resolve_target(args.source).read_text(encoding="utf-8-sig"))
                result = publish_conversion(workspace, scope, document)
        except (OSError, ValueError, KeyError, ValidationError) as error:
            parser.error(type(error).__name__ + ": operacion bloqueada; revisar evidencia, identidad y revision.")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "convertir-planeaciones":
        from .planning_conversion import convert_local_batch

        workspace = AulaTeXWorkspace(args.root)
        try:
            result = convert_local_batch(workspace, workspace.resolve_target(args.output), args.target, publish_bindings=args.publish_node_bindings)
        except (OSError, ValueError) as error:
            parser.error(str(error))
        print(json.dumps({key: value for key, value in result.items() if key != "records"}, ensure_ascii=False, indent=2))
        return

    if args.command == "planeacion-nodos":
        from .node_planning import NodePlanLoader, prepare_propagation, publish_plan, write_propagation
        from jsonschema import ValidationError

        workspace = AulaTeXWorkspace(args.root)
        try:
            if args.mode == "prepare":
                if args.output:
                    artifacts = write_propagation(workspace, workspace.resolve_target(args.output))
                    print(json.dumps({"mode": "prepare_only", "artifacts": [workspace.relative(path) for path in artifacts]}, ensure_ascii=False, indent=2))
                else:
                    print(json.dumps(prepare_propagation(workspace), ensure_ascii=False, indent=2))
            else:
                by_key, _children = workspace.editorial_scope_index()
                if not args.source or args.scope_key not in by_key:
                    raise ValueError("Se requieren --source y --scope-key del catalogo.")
                scope = by_key[args.scope_key]
                source = workspace.relative(workspace.resolve_target(args.source))
                resolved = NodePlanLoader(workspace).load(source, scope)
                artifacts = publish_plan(workspace, scope, resolved.plan) if args.mode == "publish" else ()
                print(json.dumps({"mode": args.mode, "node": scope.key, "review_state": resolved.plan["review"]["state"], "artifacts": [workspace.relative(path) for path in artifacts]}, ensure_ascii=False, indent=2))
        except (OSError, ValueError, ValidationError) as error:
            parser.error(str(error))
        return

    if args.command == "generar-planeaciones":
        from .planning_layout import generate_plans

        try:
            artifacts = generate_plans(Path(args.target), Path(args.source), index_name=args.index_name)
        except (ValueError, OSError) as error:
            parser.error(str(error))
        print(json.dumps({"artifacts": [str(path) for path in artifacts], "mode": "normalizar_modelo_aportado"}, ensure_ascii=False, indent=2))
        return

    if args.command == "supervised-activity":
        from .supervised_activity import main as supervised_main
        supervised_main(["--root", args.root, "--out", args.out, "--stage", args.stage])
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
            node_plan=args.node_plan,
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
                node_plan=args.node_plan,
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

    if args.command in ("diseno-sitio-lex", "sitio-lex"):
        from .agente_sitio_lex import AgenteSitioLex
        agent = AgenteSitioLex(AulaTeXWorkspace())
        audit = agent.audit_published_site(site_url=getattr(args, "url", None) or None)
        exec_res = agent.synchronize_evidence_and_report(audit, compile_latex=not getattr(args, "no_compile", False))
        payload = {
            "ok": exec_res.ok,
            "compliance_score": exec_res.audit.compliance_score,
            "has_forbidden_iframes": exec_res.audit.has_forbidden_iframes,
            "forbidden_iframe_sources": list(exec_res.audit.forbidden_iframe_sources),
            "matched_sections": list(exec_res.audit.matched_sections),
            "missing_sections": list(exec_res.audit.missing_sections),
            "compile_ok": exec_res.compile_ok,
            "pdf_sha256": exec_res.pdf_sha256,
            "pdf_pages": exec_res.pdf_pages,
            "deliverable_pdf": str(exec_res.deliverable_pdf) if exec_res.deliverable_pdf else None,
            "errors": list(exec_res.errors),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if args.command in ("flujo-uas", "uas-pending", "monitor-uas"):
        from .flujo_uas import FlujoUasOrchestrator, FlujoUasRequest

        orchestrator = FlujoUasOrchestrator(AulaTeXWorkspace())
        if getattr(args, "check_only", False):
            prereqs = orchestrator.verify_prerequisites()
            print(json.dumps(prereqs, ensure_ascii=False, indent=2))
            return

        if getattr(args, "pending", False) or args.command in ("uas-pending", "monitor-uas"):
            batch_res = orchestrator.run_pending_deliveries(
                subject_slug=getattr(args, "subject", "derecho-mercantil"),
                course_id=getattr(args, "course_id", None),
                inspect_platform=getattr(args, "inspect", False),
                download_resources=getattr(args, "download", False) if hasattr(args, "download") else (not getattr(args, "no_download", False)),
                compile_pdf=not getattr(args, "no_compile", False),
                output_dir=getattr(args, "output", ""),
            )
            print(json.dumps(batch_res, ensure_ascii=False, indent=2))
            return


        from .flujo_uas import FlujoUasOrchestrator, FlujoUasRequest

        orchestrator = FlujoUasOrchestrator(AulaTeXWorkspace())
        if args.check_only:
            prereqs = orchestrator.verify_prerequisites()
            print(json.dumps(prereqs, ensure_ascii=False, indent=2))
            return

        req = FlujoUasRequest(
            subject_slug=args.subject,
            course_id=args.course_id,
            module_id=args.module_id,
            activity_number=args.activity,
            week=args.week,
            topic=args.topic,
            student_name=args.student_name,
            student_id=args.student_id,
            advisor_name=args.advisor,
            group_name=args.group,
            city=args.city,
            engine=args.engine,
            download_online=not args.no_download,
            output_dir=args.output,
        )
        res = orchestrator.execute_workflow(req)
        if getattr(args, "json", False):
            print(json.dumps(res.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(res.summary)
        return

    if args.command == "itesca-workflow":
        from .itesca_workflow import (
            AulaTeXItescaOrchestrator,
            DEFAULT_ITESCA_ACTIVE_SPECS,
            ItescaWorkflowRequest,
            PIPELINE_STAGE_ORDER,
        )

        ws = AulaTeXWorkspace()
        orch = AulaTeXItescaOrchestrator(ws)
        specs = DEFAULT_ITESCA_ACTIVE_SPECS
        if args.activity > 0:
            specs = tuple(s for s in specs if s.activity_number == args.activity)
        stages = tuple(args.stage) if args.stage else PIPELINE_STAGE_ORDER
        res = orch.run(
            ItescaWorkflowRequest(
                specs=specs,
                snapshot_path=args.snapshot,
                stages=stages,
                download_from_platform=not args.no_download,
                force_reextract_concepts=bool(args.force_reextract),
                use_llm_style_refinement=bool(args.use_llm_style),
            )
        )
        print(json.dumps({
            "ok": res.ok,
            "run_id": res.run_id,
            "manifest": ws.relative(res.manifest_path),
            "report": ws.relative(res.report_path),
            "activities": [
                {
                    "subject": a["subject"],
                    "activity_number": a["activity_number"],
                    "ok": a["ok"],
                    "stages": list(a["stages_executed"].keys()),
                }
                for a in res.activities
            ],
            "global_blockers": list(res.global_blockers),
        }, ensure_ascii=False, indent=2))
        return

    if args.command == "navegacion-itesca":
        from .navegacion_itesca import NavegacionItescaAgent, ItescaNavigationRequest

        ws = AulaTeXWorkspace()
        nav = NavegacionItescaAgent(ws)
        c_ids = tuple(args.course_id) if args.course_id else (209, 215)
        m_ids = tuple(args.module_id) if args.module_id else (1761, 1762, 1763, 2915)
        out = nav.inspect(ItescaNavigationRequest(course_ids=c_ids, module_ids=m_ids))
        print(json.dumps({
            "agent_id": out.agent_id,
            "run_id": out.run_id,
            "snapshot_path": ws.relative(out.snapshot_path),
            "courses_discovered": out.courses_discovered,
            "modules_discovered": out.modules_discovered,
            "timeline_events": out.timeline_events,
            "blockers": list(out.blockers),
        }, ensure_ascii=False, indent=2))
        return

    if args.command == "realizar-planeacion-itesca":
        from .realizar_planeacion import RealizarPlaneacionAgent, RealizarPlaneacionRequest

        ws = AulaTeXWorkspace()
        snap_doc = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
        mod_snap = next((m for m in snap_doc.get("modules", []) if int(m.get("module_id", 0)) == int(args.activity)), None)
        if mod_snap is None and snap_doc.get("modules"):
            mod_snap = snap_doc["modules"][0]
        res = RealizarPlaneacionAgent(ws).run(
            RealizarPlaneacionRequest(
                target=args.target,
                activity_number=args.activity,
                module_snapshot=mod_snap or {},
            )
        )
        print(json.dumps({
            "agent_id": res.agent_id,
            "plan_json": ws.relative(res.plan_json_path),
            "plan_md": ws.relative(res.plan_md_path),
            "notes_dir": ws.relative(res.notes_dir),
            "ready_eligible": res.semantic_validation.get("ready_eligible"),
        }, ensure_ascii=False, indent=2))
        return

    if args.command == "encontrar-recursos-itesca":
        from .encontrar_recursos import EncontrarRecursosAgent, EncontrarRecursosRequest

        ws = AulaTeXWorkspace()
        res = EncontrarRecursosAgent(ws).run(
            EncontrarRecursosRequest(
                target=args.target,
                activity_number=args.activity,
                plan_json_path=args.plan,
                download_from_platform=not args.no_download,
            )
        )
        print(json.dumps({
            "agent_id": res.agent_id,
            "manifest": ws.relative(res.manifest_path),
            "downloaded": res.downloaded_count,
            "organized": res.organized_files_count,
        }, ensure_ascii=False, indent=2))
        return

    if args.command == "extraer-conceptos-itesca":
        from .extraer_conceptos import ExtraerConceptosAgent, ExtraerConceptosRequest

        ws = AulaTeXWorkspace()
        res = ExtraerConceptosAgent(ws).run(
            ExtraerConceptosRequest(
                target=args.target,
                activity_number=args.activity,
                plan_json_path=args.plan,
                motors=(args.motor, "tfidf"),
                force_rerun=bool(args.force),
            )
        )
        print(json.dumps({
            "agent_id": res.agent_id,
            "motor": res.selected_motor,
            "concepts_count": res.concepts_count,
            "notes_concepts_dir": ws.relative(res.notes_concepts_dir),
        }, ensure_ascii=False, indent=2))
        return

    if args.command == "realizar-actividad-itesca":
        from .realizar_actividad import RealizarActividadAgent, RealizarActividadRequest

        ws = AulaTeXWorkspace()
        res = RealizarActividadAgent(ws).run(
            RealizarActividadRequest(
                target=args.target,
                activity_number=args.activity,
                plan_json_path=args.plan,
                delivery_source_tex=args.delivery_source,
                delivery_target_rel=args.delivery_target,
                expected_delivery_pages=args.expected_pages if args.expected_pages > 0 else None,
                expected_arial_pt=args.expected_arial if args.expected_arial > 0 else None,
                docx_deliverable_rel=args.docx_deliverable,
            )
        )
        print(json.dumps({
            "agent_id": res.agent_id,
            "ok": res.ok,
            "status": res.stage_status,
            "report_pdf": ws.relative(res.report_pdf_path) if res.report_pdf_path else None,
            "delivery_artifact": ws.relative(res.delivery_artifact_path) if res.delivery_artifact_path else None,
            "manifest": ws.relative(res.manifest_path),
        }, ensure_ascii=False, indent=2))
        return

    if args.command == "estilo-escribir-eval":
        from .estilo_escribir import EstiloEscribirAgent

        ws = AulaTeXWorkspace()
        agent = EstiloEscribirAgent(ws)
        if args.tex:
            collab = agent.collaborate_on_tex(args.tex, bib_path=args.bib, apply=bool(args.apply))
            print(json.dumps({
                "agent_id": collab.agent_id,
                "passed": collab.after.passed,
                "score_before": collab.before.score,
                "score_after": collab.after.score,
                "applied_changes": list(collab.applied_changes),
            }, ensure_ascii=False, indent=2))
        elif args.docx:
            from docx import Document
            doc = Document(args.docx)
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            ev = agent.evaluate_plain_prose(text)
            print(json.dumps({
                "agent_id": agent.agent_id,
                "passed": ev.passed,
                "score": ev.score,
                "critical": list(ev.critical_issues),
                "warnings": list(ev.style_warnings),
            }, ensure_ascii=False, indent=2))
        return

    if args.command in ("uas-entrega", "entregar-uas"):
        from .flujo_uas import FlujoUasOrchestrator

        orchestrator = FlujoUasOrchestrator(AulaTeXWorkspace())
        res = orchestrator.submit_authorized_delivery(
            subject_slug=args.subject,
            activity_number=args.activity,
            artifact_path=args.artifact,
            user_validated=getattr(args, "user_validated", False),
            expected_sha256=getattr(args, "sha256", None),
            course_id=getattr(args, "course_id", None),
            module_id=getattr(args, "module_id", None),
            finalize=getattr(args, "finalize", False),
            dry_run=getattr(args, "dry_run", True),
            output_dir=getattr(args, "output", ""),
        )
        print(json.dumps({
            "ok": res.ok,
            "status": res.status,
            "receipt_path": str(res.receipt_path) if res.receipt_path else None,
            "blockers": list(res.blockers),
            "manifest_path": str(res.manifest_path) if res.manifest_path else None,
            "summary": res.summary,
        }, ensure_ascii=False, indent=2))
        return

    if args.command == "unadm-workflow":
        from .unadm_workflow import UnadmWorkflowOrchestrator, UnadmWorkflowRequest

        ws = AulaTeXWorkspace()
        orch = UnadmWorkflowOrchestrator(ws)

        if getattr(args, "pending", False):
            pending_res = orch.run_pending_deliveries(
                subject_slug=args.subject,
                course_id=args.course_id,
                inspect_platform=not args.no_inspect,
                download_online_resources=not args.no_download,
                compile_pdf=not args.no_compile,
                use_llm_style=bool(args.use_llm_style),
                output_dir=args.output,
            )
            print(json.dumps(pending_res, ensure_ascii=False, indent=2))
            return

        req = UnadmWorkflowRequest(
            subject_slug=args.subject,
            activity_number=args.activity,
            course_id=args.course_id,
            module_id=args.module_id,
            inspect_platform=not args.no_inspect,
            download_online_resources=not args.no_download,
            compile_pdf=not args.no_compile,
            use_llm_style=bool(args.use_llm_style),
            submit_to_platform=bool(getattr(args, "submit_to_platform", False)),
            user_validated=bool(getattr(args, "user_validated", False)),
            output_dir=args.output,
        )
        res = orch.run(req)
        print(json.dumps({
            "ok": res.ok,
            "run_id": res.run_id,
            "subject": res.subject_slug,
            "activity": res.activity_number,
            "manifest": ws.relative(res.manifest_path),
            "summary_md": ws.relative(res.summary_md_path),
            "proposed_delivery": res.proposed_delivery,
            "stages": [
                {
                    "stage": s.stage_name,
                    "agent": s.agent_id,
                    "ok": s.ok,
                    "summary": s.summary,
                    "blockers": list(s.blockers),
                }
                for s in res.stages
            ],
            "global_blockers": list(res.blockers),
        }, ensure_ascii=False, indent=2))
        return

    if args.command == "navegacion-unadm":
        from .navegacion_unadm import NavegacionUnadmAgent, UnadmNavigationRequest

        ws = AulaTeXWorkspace()
        nav = NavegacionUnadmAgent(ws)
        c_ids = tuple(args.course_id) if args.course_id else (3432, 3482, 3441)
        out = nav.inspect(UnadmNavigationRequest(course_ids=c_ids, output_dir=args.output))
        print(json.dumps({
            "agent_id": out.agent_id,
            "run_id": out.run_id,
            "snapshot_path": ws.relative(out.snapshot_path) if out.snapshot_path else "",
            "courses_discovered": out.courses_discovered,
            "assignments_discovered": out.assignments_discovered,
            "forums_discovered": out.forums_discovered,
            "resources_discovered": out.resources_discovered,
            "blockers": list(out.blockers),
        }, ensure_ascii=False, indent=2))
        return

    if args.command == "monitor-unadm":
        from .monitor_unadm import MonitorUnadmAgent, MonitorUnadmRequest

        ws = AulaTeXWorkspace()
        mon = MonitorUnadmAgent(ws)
        req = MonitorUnadmRequest(
            subject_slug=args.subject,
            activity_number=args.activity,
            course_id=args.course_id,
            module_id=args.module_id,
            inspect_platform=bool(args.inspect),
            output_dir=args.output,
        )
        report = mon.monitor_deliveries(req)
        print(json.dumps({
            "ok": report.ok,
            "run_id": report.run_id,
            "institution": report.institution,
            "manifest": ws.relative(report.manifest_path) if report.manifest_path else "",
            "summary_md": ws.relative(report.summary_md_path) if report.summary_md_path else "",
            "pending_count": len(report.pending_deliveries),
            "recommendations": [
                {
                    "activity": r.activity_number,
                    "action": r.recommended_action,
                    "prerequisites_satisfied": list(r.prerequisites_satisfied),
                    "rationale": r.rationale,
                    "proposed_artifact": r.proposed_delivery_artifact,
                }
                for r in report.recommendations
            ],
            "blockers": list(report.blockers),
        }, ensure_ascii=False, indent=2))
        return

    if args.command == "entregar-unadm":
        from .entregar_unadm import EntregarUnadmAgent, EntregarUnadmRequest

        ws = AulaTeXWorkspace()
        agent = EntregarUnadmAgent(ws)
        req = EntregarUnadmRequest(
            subject_slug=args.subject,
            activity_number=args.activity,
            artifact_path=args.artifact,
            expected_sha256=args.sha256 if args.sha256 else None,
            course_id=args.course_id,
            module_id=args.module_id,
            user_validated=bool(args.user_validated),
            finalize=bool(args.finalize),
            dry_run=not bool(args.live),
            output_dir=args.output,
        )
        res = agent.submit(req)
        print(json.dumps({
            "ok": res.ok,
            "status": res.status,
            "run_id": res.run_id,
            "artifact": res.artifact_path,
            "sha256": res.sha256,
            "platform_url": res.platform_url,
            "receipt": ws.relative(res.receipt_path) if res.receipt_path else "",
            "manifest": ws.relative(res.manifest_path) if res.manifest_path else "",
            "blockers": list(res.blockers),
        }, ensure_ascii=False, indent=2))
        return

    if args.command in ("itesca-pending", "monitor-itesca"):
        from .monitor_itesca import MonitorItescaAgent, MonitorItescaRequest

        ws = AulaTeXWorkspace()
        mon = MonitorItescaAgent(ws)
        req = MonitorItescaRequest(
            subject_slug=getattr(args, "subject", "all"),
            course_id=getattr(args, "course_id", None),
            snapshot_path=getattr(args, "snapshot", ""),
            inspect_platform=bool(getattr(args, "inspect", False)),
            output_dir=getattr(args, "output", ""),
            run_workflow=bool(getattr(args, "run_workflow", False)),
        )
        report = mon.monitor_deliveries(req)
        print(json.dumps({
            "ok": report.ok,
            "run_id": report.run_id,
            "institution": report.institution,
            "manifest": ws.relative(report.manifest_path) if report.manifest_path else "",
            "summary_md": ws.relative(report.summary_md_path) if report.summary_md_path else "",
            "pending_count": len(report.pending_deliveries),
            "pending_deliveries": [
                {
                    "subject": it.subject_slug,
                    "activity": it.activity_number,
                    "title": it.activity_title,
                    "module_id": it.module_id,
                    "platform_status": it.platform_status,
                    "deliverable_ready": it.local_deliverable_ready,
                    "deliverable_path": ws.relative(Path(it.local_deliverable_path)) if it.local_deliverable_path else None,
                    "sha256": it.local_deliverable_sha256,
                }
                for it in report.pending_deliveries
            ],
            "recommendations": [
                {
                    "subject": r.subject_slug,
                    "activity": r.activity_number,
                    "action": r.recommended_action,
                    "prerequisites_satisfied": list(r.prerequisites_satisfied),
                    "rationale": r.rationale,
                    "proposed_artifact": ws.relative(Path(r.proposed_delivery_artifact)) if r.proposed_delivery_artifact else None,
                }
                for r in report.recommendations
            ],
            "blockers": list(report.blockers),
        }, ensure_ascii=False, indent=2))
        return

    if args.command in ("itesca-entrega", "entregar-itesca"):
        from .entregar_itesca import EntregarItescaAgent, EntregarItescaRequest
        from .monitor_itesca import ITESCA_SUBJECTS_CATALOG, _clean_slug

        ws = AulaTeXWorkspace()
        agent = EntregarItescaAgent(ws)

        clean_slug = _clean_slug(args.subject)
        artifact_path = args.artifact.strip()
        if not artifact_path:
            cat_entry = ITESCA_SUBJECTS_CATALOG.get(clean_slug, {})
            act_info = cat_entry.get("activities", {}).get(args.activity, {})
            artifact_path = act_info.get("deliverable_rel", "")

        req = EntregarItescaRequest(
            subject_slug=clean_slug,
            activity_number=args.activity,
            artifact_path=artifact_path,
            expected_sha256=getattr(args, "sha256", None),
            course_id=getattr(args, "course_id", None),
            module_id=getattr(args, "module_id", None),
            user_validated=bool(getattr(args, "user_validated", False)),
            finalize=bool(getattr(args, "finalize", False)),
            dry_run=bool(getattr(args, "dry_run", True)),
            output_dir=getattr(args, "output", ""),
        )
        res = agent.submit(req)
        print(json.dumps({
            "ok": res.ok,
            "status": res.status,
            "run_id": res.run_id,
            "artifact": res.artifact_path,
            "sha256": res.sha256,
            "platform_url": res.platform_url,
            "receipt": ws.relative(res.receipt_path) if res.receipt_path else "",
            "manifest": ws.relative(res.manifest_path) if res.manifest_path else "",
            "blockers": list(res.blockers),
        }, ensure_ascii=False, indent=2))
        return

    parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
