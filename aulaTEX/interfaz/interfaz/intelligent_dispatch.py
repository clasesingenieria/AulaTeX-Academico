from __future__ import annotations

import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aulaTEX.aulatex import (  # type: ignore[import-not-found]
    ActivityMonitor,
    ActivityMonitorRequest,
    AgentRequest,
    AulaTeXAgent,
    AulaTeXWorkspace,
    IntelligentEngine,
    IntelligentEngineRequest,
    LLM_ENGINES,
)

from .azure_openai_client import invoke_chat
from .config import Settings

INTELLIGENT_COMMAND_PREFIXES = ("motor:", "inteligente:", "aulatex:")
EXECUTION_MODE_DELEGATE = "delegate"
EXECUTION_MODE_PLAN_ONLY = "plan-only"
SUPPORTED_EXECUTION_MODES = (EXECUTION_MODE_DELEGATE, EXECUTION_MODE_PLAN_ONLY)
ENGINE_LABEL_BY_PROVIDER = {
    "azure-openai": "Auto (model-router)",
    "model-router": "Auto (model-router)",
    "auto": "Auto (model-router)",
    "codex": "Codex",
    "gpt-pro": "GPT-Pro",
    "claude-foundry": "Claude Foundry",
}
ENGINE_NAME_ALIASES = {
    "sol": "GPT-5.6-SOL",
    "gpt-5.6-sol": "GPT-5.6-SOL",
    "luna": "GPT-5.6-Luna",
    "gpt-5.6-luna": "GPT-5.6-Luna",
    "terra": "GPT-5.6-Terra",
    "gpt-5.6-terra": "GPT-5.6-Terra",
    "codex": "Codex",
    "gpt-pro": "GPT-Pro",
    "gpt pro": "GPT-Pro",
    "gptpro": "GPT-Pro",
    "claude": "Claude Foundry",
    "claude foundry": "Claude Foundry",
    "claude-foundry": "Claude Foundry",
    "model-router": "Auto (model-router)",
    "model router": "Auto (model-router)",
    "auto": "Auto (model-router)",
    "azure-openai": "Auto (model-router)",
    "azure openai": "Auto (model-router)",
}
INTELLIGENT_ROUTER_PROMPT = """Eres un enrutador de instrucciones para el motor inteligente de AulaTeX.
Convierte una instruccion libre del usuario en un objeto JSON valido con esta forma exacta:
{
  "kind": "intelligent-engine",
  "request": {}
}

Reglas:
- kind solo puede ser intelligent-engine, agent o activity-monitor.
- Usa intelligent-engine para planificar, priorizar, inventariar, auditar lotes o campanas amplias.
- Usa agent para ejecutar generar-plantilla, generar-actividad o realizar-actividad sobre un target concreto.
- Usa activity-monitor para ejecutar ciclos repetidos de observacion, revision, bibliografia, extractor y compilacion hasta pasar o agotar ciclos.
- Si kind=intelligent-engine, request debe tener: target, activity_number, output, backend, max_targets, audit_path, include_reports, include_presentations, engines.
- Si kind=agent, request debe tener: target, level, action, activity_number, generation_mode, iterations, cycle_mode, compile_tex, apply_feedback, run_extractor, skip_extractor, engines.
- Si kind=activity-monitor, request debe tener: target, activity_number, output, max_cycles, compile_check, run_extractor, apply_bibliography_repair, stop_on_blocker, workflow_backend.
- target debe ser una ruta relativa al repositorio cuando el usuario identifique una carpeta o archivo. Usa "." si no se especifica.
- activity_number debe ser entero >= 0. Usa 0 solo cuando no aplique.
- backend y workflow_backend solo pueden ser langgraph o classic.
- level solo puede ser interinstitucional, institucion, carrera, materia o actividad.
- action solo puede ser generar-plantilla, generar-actividad o realizar-actividad.
- generation_mode solo puede ser direct o downward.
- cycle_mode solo puede ser stages o full.
- max_targets debe ser entero entre 1 y 24.
- max_cycles debe ser entero entre 1 y 12.
- include_reports=false si el usuario pide solo presentaciones.
- include_presentations=false si el usuario pide solo reportes.
- engines debe contener solo estos nombres exactos cuando el usuario los pida: GPT-5.6-SOL, GPT-5.6-Luna, GPT-5.6-Terra, Codex, Auto (model-router), GPT-Pro, Claude Foundry.
- Si el usuario no pide motores concretos, deja engines como lista vacia.
- No inventes rutas inexistentes si la instruccion no alcanza para resolverlas.
- Responde exclusivamente con JSON valido, sin Markdown ni explicaciones.
"""

EDITORIAL_PROPOSAL_PROMPT = """Eres un estratega editorial para AulaTeX.
Debes convertir una nota limpia en una propuesta operativa para trabajar sobre el repositorio actual.

Responde exclusivamente con JSON valido, sin Markdown ni explicaciones, con esta forma exacta:
{
    "instruction": "",
    "backend": "langgraph",
    "target_hint": ".",
    "nucleo": "",
    "desarrollo": "",
    "accionables": "",
    "evidencias": "",
    "sintesis": ""
}

Reglas:
- instruction debe ser una instruccion clara y ejecutable para /motor, centrada en campanas, lotes, rutas, ciclos o acciones editoriales sobre el repo.
- backend solo puede ser langgraph o classic. Prefiere langgraph salvo restriccion explicita.
- target_hint debe ser una ruta candidata observada en el repo o ".".
- nucleo, desarrollo, accionables, evidencias y sintesis deben redactarse como instrucciones para trabajo editorial sobre proyecto, no como comentario sobre una nota personal.
- accionables debe incluir lote/campana sugerido, criterios de prioridad y siguiente paso de ejecucion.
- no inventes rutas inexistentes.
"""


@dataclass(frozen=True)
class IntelligentDispatchPlan:
    instruction: str
    kind: str
    request: IntelligentEngineRequest | AgentRequest | ActivityMonitorRequest
    payload: dict[str, Any]


@dataclass(frozen=True)
class IntelligentDispatchResult:
    instruction: str
    kind: str
    request: IntelligentEngineRequest | AgentRequest | ActivityMonitorRequest
    manifest: dict[str, Any]
    result: Any


@dataclass(frozen=True)
class EditorialProposal:
    instruction: str
    backend: str
    target_hint: str
    sections: dict[str, str]


@dataclass(frozen=True)
class BotMotorCapabilities:
    execution_mode: str
    supported_kinds: tuple[str, ...]
    workflow_backends: tuple[str, ...]
    llm_engines: tuple[str, ...]
    planes: dict[str, tuple[str, ...]]
    persistence_contracts: tuple[str, ...]
    delegated_to: str


def normalize_execution_mode(value: str | None) -> str:
    normalized = str(value or EXECUTION_MODE_DELEGATE).strip().lower().replace("_", "-")
    if normalized in {"disabled", "dry-run", "dryrun", "plan", "planonly"}:
        return EXECUTION_MODE_PLAN_ONLY
    if normalized in {"enabled", "execute", "delegated", "aulatex"}:
        return EXECUTION_MODE_DELEGATE
    return normalized if normalized in SUPPORTED_EXECUTION_MODES else EXECUTION_MODE_DELEGATE


def motor_capabilities(execution_mode: str | None = None) -> BotMotorCapabilities:
    mode = normalize_execution_mode(execution_mode)
    return BotMotorCapabilities(
        execution_mode=mode,
        supported_kinds=("intelligent-engine", "agent", "activity-monitor"),
        workflow_backends=("langgraph", "classic"),
        llm_engines=tuple(LLM_ENGINES),
        planes={
            "control": ("telegram-command", "telegram-callback", "confirm-before-run", "plan-only-switch"),
            "routing": ("llm-json-router", "scope-candidate-resolution", "request-coercion", "target-validation"),
            "workflow": ("campaign-planning", "agent-cycle", "activity-monitor", "langgraph", "classic"),
            "execution": ("delegate-to-aulatex", "plan-only"),
            "outputs": ("plan-markdown", "summary-text", "manifest-json", "report-markdown"),
        },
        persistence_contracts=("pending_motor_dispatches", "proposal.editorial_instruction", "manifest_path", "report_path", "run_dir"),
        delegated_to="aulaTEX.aulatex",
    )


def format_motor_capabilities_markdown(capabilities: BotMotorCapabilities | None = None) -> str:
    capabilities = capabilities or motor_capabilities()
    lines = [
        "# Capacidades de motor en bot-interfaz",
        "",
        "bot-interfaz contiene la capa de control, enrutamiento, validación y propuesta; la ejecución real se delega al AulaTeX operativo.",
        "",
        f"- Modo de ejecución: `{capabilities.execution_mode}`",
        f"- Delegado real: `{capabilities.delegated_to}`",
        "- Tipos soportados: " + ", ".join(f"`{item}`" for item in capabilities.supported_kinds),
        "- Backends de flujo: " + ", ".join(f"`{item}`" for item in capabilities.workflow_backends),
        "- Motores LLM: " + ", ".join(capabilities.llm_engines),
        "",
        "## Planos integrados",
    ]
    for plane, items in capabilities.planes.items():
        lines.append(f"- {plane}: " + ", ".join(f"`{item}`" for item in items))
    lines.extend(
        [
            "",
            "## Contratos de persistencia",
            "- " + "\n- ".join(capabilities.persistence_contracts),
        ]
    )
    return "\n".join(lines)


def instruction_help_text() -> str:
    return (
        "Usa /motor seguido de una instruccion editorial.\n\n"
        "Ejemplos:\n"
        "/motor planifica UCNL/licenciatura-en-administracion/administracion-i-lad actividad 1\n"
        "/motor revisa solo reportes en UnADM con backend classic y maximo 4 objetivos\n"
        "Tambien puedes escribir motor: <instruccion>."
    )


def extract_intelligent_instruction(text: str) -> str | None:
    raw = text.strip()
    lowered = raw.casefold()
    for prefix in INTELLIGENT_COMMAND_PREFIXES:
        if lowered.startswith(prefix):
            instruction = raw[len(prefix) :].strip()
            return instruction or ""
    return None


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_text.casefold()).strip()


def _score_scope_candidate(instruction: str, candidate: str) -> int:
    instruction_tokens = set(_normalize_text(instruction).split())
    candidate_tokens = set(_normalize_text(candidate).split())
    if not instruction_tokens or not candidate_tokens:
        return 0
    overlap = instruction_tokens & candidate_tokens
    if not overlap:
        return 0
    score = len(overlap) * 3
    candidate_norm = _normalize_text(candidate)
    for token in overlap:
        if len(token) >= 4 and token in candidate_norm:
            score += 1
    return score


def _candidate_scope_lines(instruction: str) -> list[str]:
    scopes_root = [path for path in sorted(REPO_ROOT.iterdir()) if path.is_dir() and not path.name.startswith(".")]
    candidates: list[tuple[int, str]] = []
    for path in scopes_root:
        candidate = path.name
        score = _score_scope_candidate(instruction, candidate)
        if score > 0:
            candidates.append((score, candidate))
        for child in sorted(path.rglob("*.tex")):
            relative = child.relative_to(REPO_ROOT).as_posix()
            score = _score_scope_candidate(instruction, relative)
            if score > 0:
                candidates.append((score, relative))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    unique_lines: list[str] = []
    seen: set[str] = set()
    for _, candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        unique_lines.append(candidate)
        if len(unique_lines) >= 12:
            break
    return unique_lines


def _default_engines(provider: str) -> tuple[str, ...]:
    import os

    router_only = (os.getenv("AULATEX_MODEL_ROUTER_ONLY", "") or "").strip().lower()
    if router_only in {"1", "true", "yes", "on", "si", "sí"}:
        return ("Auto (model-router)",)

    preferred = ENGINE_LABEL_BY_PROVIDER.get(provider, "Auto (model-router)")
    ordered = [preferred, *LLM_ENGINES]
    seen: set[str] = set()
    result: list[str] = []
    for engine in ordered:
        if engine in seen:
            continue
        seen.add(engine)
        result.append(engine)
    return tuple(result)


def _normalize_engines(raw_engines: object, provider: str) -> tuple[str, ...]:
    defaults = _default_engines(provider)
    if defaults == ("Auto (model-router)",):
        return defaults
    if not isinstance(raw_engines, list) or not raw_engines:
        return defaults

    result: list[str] = []
    for raw in raw_engines:
        key = str(raw or "").strip()
        if not key:
            continue
        engine = ENGINE_NAME_ALIASES.get(key.casefold(), key)
        if engine in LLM_ENGINES and engine not in result:
            result.append(engine)
    return tuple(result) or defaults


def _coerce_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"1", "true", "yes", "si", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _coerce_int(value: object, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def _build_router_messages(instruction: str) -> list[dict[str, str]]:
    candidates = _candidate_scope_lines(instruction)
    candidate_block = "\n".join(f"- {candidate}" for candidate in candidates) if candidates else "- ."
    return [
        {"role": "system", "content": INTELLIGENT_ROUTER_PROMPT},
        {
            "role": "user",
            "content": (
                f"Repositorio raiz: {REPO_ROOT.as_posix()}\n"
                f"Rutas candidatas observadas:\n{candidate_block}\n\n"
                f"Instruccion del usuario:\n{instruction}"
            ),
        },
    ]


def _resolve_existing_target(target: str) -> str:
    target = str(target or ".").strip() or "."
    target_path = Path(target)
    resolved_target = (REPO_ROOT / target_path).resolve() if not target_path.is_absolute() else target_path.resolve()
    if target != "." and not resolved_target.exists():
        raise RuntimeError(f"El target solicitado no existe en el repositorio: {target}")
    return target


def _coerce_backend(value: object, default: str = "langgraph") -> str:
    backend = str(value or default).strip().lower() or default
    return backend if backend in {"langgraph", "classic"} else default


def _infer_level(target: str, activity_number: int) -> str:
    workspace = AulaTeXWorkspace()
    resolved_target = workspace.resolve_target(target)
    scope = workspace.find_scope_for_target(resolved_target, activity_number=activity_number or None)
    if scope is not None and scope.level in {"interinstitucional", "institucion", "carrera", "materia", "actividad"}:
        return scope.level
    if resolved_target.suffix.lower() == ".tex":
        return "actividad"
    return "materia"


def _intelligent_engine_request_from_payload(payload: dict[str, Any], settings: Settings) -> IntelligentEngineRequest:
    target = _resolve_existing_target(str(payload.get("target") or ".").strip() or ".")
    return IntelligentEngineRequest(
        target=target,
        activity_number=_coerce_int(payload.get("activity_number"), 0, 0, 999),
        output=str(payload.get("output") or "").strip(),
        backend=_coerce_backend(payload.get("backend"), "langgraph"),
        max_targets=_coerce_int(payload.get("max_targets"), 12, 1, 24),
        audit_path=str(payload.get("audit_path") or "").strip(),
        include_reports=_coerce_bool(payload.get("include_reports"), True),
        include_presentations=_coerce_bool(payload.get("include_presentations"), True),
        engines=_normalize_engines(payload.get("engines"), settings.llm_provider),
    )


def _agent_request_from_payload(payload: dict[str, Any], settings: Settings) -> AgentRequest:
    target = _resolve_existing_target(str(payload.get("target") or ".").strip() or ".")
    activity_number = _coerce_int(payload.get("activity_number"), 1, 1, 999)
    level = str(payload.get("level") or "").strip().lower()
    if level not in {"interinstitucional", "institucion", "carrera", "materia", "actividad"}:
        level = _infer_level(target, activity_number)
    action = str(payload.get("action") or "realizar-actividad").strip().lower() or "realizar-actividad"
    if action not in {"generar-plantilla", "generar-actividad", "realizar-actividad"}:
        action = "realizar-actividad"
    generation_mode = str(payload.get("generation_mode") or "direct").strip().lower() or "direct"
    if generation_mode not in {"direct", "downward"}:
        generation_mode = "direct"
    cycle_mode = str(payload.get("cycle_mode") or "stages").strip().lower() or "stages"
    if cycle_mode not in {"stages", "full"}:
        cycle_mode = "stages"

    return AgentRequest(
        target=target,
        level=level,
        action=action,
        activity_number=activity_number,
        generation_mode=generation_mode,
        parent_scope_key=str(payload.get("parent_scope_key") or "").strip(),
        child_level=str(payload.get("child_level") or "").strip(),
        child_name=str(payload.get("child_name") or "").strip(),
        engines=list(_normalize_engines(payload.get("engines"), settings.llm_provider)),
        iterations=_coerce_int(payload.get("iterations"), 5, 1, 24),
        cycle_mode=cycle_mode,
        compile_tex=_coerce_bool(payload.get("compile_tex"), True),
        apply_feedback=_coerce_bool(payload.get("apply_feedback"), False),
        run_extractor=_coerce_bool(payload.get("run_extractor"), action in {"realizar-actividad", "generar-actividad"}),
        skip_extractor=_coerce_bool(payload.get("skip_extractor"), False),
    )


def _activity_monitor_request_from_payload(payload: dict[str, Any]) -> ActivityMonitorRequest:
    target = _resolve_existing_target(str(payload.get("target") or ".").strip() or ".")
    return ActivityMonitorRequest(
        target=target,
        activity_number=_coerce_int(payload.get("activity_number"), 1, 1, 999),
        output=str(payload.get("output") or "").strip(),
        max_cycles=_coerce_int(payload.get("max_cycles"), 2, 1, 12),
        compile_check=_coerce_bool(payload.get("compile_check"), True),
        run_extractor=_coerce_bool(payload.get("run_extractor"), True),
        apply_bibliography_repair=_coerce_bool(payload.get("apply_bibliography_repair"), True),
        stop_on_blocker=_coerce_bool(payload.get("stop_on_blocker"), True),
        workflow_backend=_coerce_backend(payload.get("workflow_backend"), "langgraph"),
    )


def _parse_dispatch_kind(value: object) -> str:
    kind = str(value or "intelligent-engine").strip().lower() or "intelligent-engine"
    return kind if kind in {"intelligent-engine", "agent", "activity-monitor"} else "intelligent-engine"


def _request_from_payload(payload: dict[str, Any], settings: Settings) -> tuple[str, IntelligentEngineRequest | AgentRequest | ActivityMonitorRequest]:
    kind = _parse_dispatch_kind(payload.get("kind"))
    request_payload = payload.get("request") if isinstance(payload.get("request"), dict) else payload
    if kind == "agent":
        return kind, _agent_request_from_payload(request_payload, settings)
    if kind == "activity-monitor":
        return kind, _activity_monitor_request_from_payload(request_payload)
    return kind, _intelligent_engine_request_from_payload(request_payload, settings)


def build_editorial_proposal(note_title: str, corrected_text: str, concepts: str, settings: Settings) -> EditorialProposal:
    candidate_block = "\n".join(f"- {candidate}" for candidate in _candidate_scope_lines(f"{note_title}\n{corrected_text}")) or "- ."
    raw = invoke_chat(
        settings,
        [
            {"role": "system", "content": EDITORIAL_PROPOSAL_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Repositorio raiz: {REPO_ROOT.as_posix()}\n"
                    f"Rutas candidatas observadas:\n{candidate_block}\n\n"
                    f"Titulo de referencia:\n{note_title}\n\n"
                    f"Nota limpia:\n{corrected_text}\n\n"
                    f"Conceptos detectados:\n{concepts}"
                ),
            },
        ],
        max_tokens=2200,
        temperature=0.2,
        response_format_json=True,
    )
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("La propuesta editorial no devolvio JSON valido.") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("La propuesta editorial no devolvio un objeto JSON.")

    instruction = str(payload.get("instruction") or "").strip()
    if not instruction:
        raise RuntimeError("La propuesta editorial no incluyo una instruccion ejecutable.")
    backend = str(payload.get("backend") or "langgraph").strip().lower() or "langgraph"
    if backend not in {"langgraph", "classic"}:
        backend = "langgraph"
    target_hint = str(payload.get("target_hint") or ".").strip() or "."
    target_path = Path(target_hint)
    resolved_target = (REPO_ROOT / target_path).resolve() if not target_path.is_absolute() else target_path.resolve()
    if target_hint != "." and not resolved_target.exists():
        target_hint = "."

    return EditorialProposal(
        instruction=instruction,
        backend=backend,
        target_hint=target_hint,
        sections={
            "Nucleo": str(payload.get("nucleo") or "").strip(),
            "Desarrollo": str(payload.get("desarrollo") or "").strip(),
            "Accionables": str(payload.get("accionables") or "").strip(),
            "Evidencias y supuestos": str(payload.get("evidencias") or "").strip(),
            "Sintesis breve": str(payload.get("sintesis") or "").strip(),
        },
    )


def plan_intelligent_dispatch(instruction: str, settings: Settings) -> IntelligentDispatchPlan:
    messages = _build_router_messages(instruction)
    raw = invoke_chat(
        settings,
        messages,
        max_tokens=1600,
        temperature=0.1,
        response_format_json=True,
    )
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("El LLM no devolvio una instruccion JSON valida para el motor inteligente.") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("La instruccion estructurada del motor inteligente no es un objeto JSON.")

    kind, request = _request_from_payload(payload, settings)
    return IntelligentDispatchPlan(instruction=instruction, kind=kind, request=request, payload=payload)


def execute_intelligent_dispatch_plan(plan: IntelligentDispatchPlan, *, execution_mode: str | None = None) -> IntelligentDispatchResult:
    mode = normalize_execution_mode(execution_mode)
    if mode == EXECUTION_MODE_PLAN_ONLY:
        raise RuntimeError("El modo plan-only está activo: bot-interfaz preparó el plan, pero la ejecución queda deshabilitada y delegada al AulaTeX real.")

    if plan.kind == "agent":
        result = AulaTeXAgent().run(plan.request)
    elif plan.kind == "activity-monitor":
        result = ActivityMonitor().run(plan.request)
    else:
        result = IntelligentEngine().run(plan.request)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    return IntelligentDispatchResult(
        instruction=plan.instruction,
        kind=plan.kind,
        request=plan.request,
        manifest=manifest,
        result=result,
    )


def run_intelligent_dispatch(instruction: str, settings: Settings, *, execution_mode: str | None = None) -> IntelligentDispatchResult:
    return execute_intelligent_dispatch_plan(plan_intelligent_dispatch(instruction, settings), execution_mode=execution_mode)


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def format_dispatch_plan_markdown(plan: IntelligentDispatchPlan) -> str:
    request = plan.request
    lines = [
        "# Validar ejecución del motor inteligente",
        "",
        "El motor inteligente todavía no se ha ejecutado. Revisa el plan y confirma si deseas continuar.",
        "",
        f"- Tipo de ejecución: `{plan.kind}`",
        f"- Instrucción original: {plan.instruction}",
        "",
    ]
    if isinstance(request, IntelligentEngineRequest):
        lines.extend(
            [
                f"- Target: `{request.target}`",
                f"- Actividad: {request.activity_number}",
                f"- Backend: `{request.backend}`",
                f"- Máximo de objetivos: {request.max_targets}",
                f"- Incluir reportes: {'sí' if request.include_reports else 'no'}",
                f"- Incluir presentaciones: {'sí' if request.include_presentations else 'no'}",
                f"- Motores: {', '.join(request.engines)}",
                "",
            ]
        )
    elif isinstance(request, AgentRequest):
        lines.extend(
            [
                f"- Target: `{request.target}`",
                f"- Nivel: `{request.level}`",
                f"- Acción: `{request.action}`",
                f"- Actividad: {request.activity_number}",
                f"- Iteraciones: {request.iterations}",
                f"- Cycle mode: `{request.cycle_mode}`",
                f"- Compilar: {'sí' if request.compile_tex else 'no'}",
                f"- Run extractor: {'sí' if request.run_extractor else 'no'}",
                f"- Motores: {', '.join(request.engines)}",
                "",
            ]
        )
    elif isinstance(request, ActivityMonitorRequest):
        lines.extend(
            [
                f"- Target: `{request.target}`",
                f"- Actividad: {request.activity_number}",
                f"- Backend: `{request.workflow_backend}`",
                f"- Ciclos máximos: {request.max_cycles}",
                f"- Compile check: {'sí' if request.compile_check else 'no'}",
                f"- Run extractor: {'sí' if request.run_extractor else 'no'}",
                f"- Reparar bibliografía: {'sí' if request.apply_bibliography_repair else 'no'}",
                f"- Detener en blocker: {'sí' if request.stop_on_blocker else 'no'}",
                "",
            ]
        )
    lines.extend(
        [
            "## JSON interpretado",
            "",
            "```json",
            json.dumps(plan.payload, ensure_ascii=False, indent=2),
            "```",
            "",
            "Pulsa **Ejecutar motor** para continuar o **Cancelar** para descartar.",
        ]
    )
    return "\n".join(lines)


def format_dispatch_summary(dispatch: IntelligentDispatchResult) -> str:
    scope = dispatch.manifest.get("scope", {}) if isinstance(dispatch.manifest.get("scope"), dict) else {}
    inventory = dispatch.manifest.get("inventory_summary", {}) if isinstance(dispatch.manifest.get("inventory_summary", {}), dict) else {}
    request = dispatch.request
    run_dir = _display_path(dispatch.result.run_dir)
    manifest_path = _display_path(dispatch.result.manifest_path)
    report_path = _display_path(dispatch.result.report_path)
    lines: list[str] = []
    if isinstance(request, IntelligentEngineRequest):
        lines.extend(
            [
                "Motor inteligente ejecutado.",
                f"Target: {request.target}",
                f"Scope: {scope.get('scope_label') or scope.get('target_root') or request.target}",
                f"Backend: {request.backend}",
                f"Motores: {', '.join(request.engines)}",
                f"Objetivos planificados: {inventory.get('planned_targets', 0)}",
                f"Inventario TEX: {inventory.get('tex_total', 0)}",
            ]
        )
    elif isinstance(request, AgentRequest):
        consensus = dispatch.manifest.get("consensus", {}) if isinstance(dispatch.manifest.get("consensus"), dict) else {}
        compile_results = dispatch.manifest.get("compile_results", []) if isinstance(dispatch.manifest.get("compile_results"), list) else []
        lines.extend(
            [
                "Agente AulaTeX ejecutado.",
                f"Target: {dispatch.manifest.get('target') or request.target}",
                f"Nivel: {dispatch.manifest.get('level') or request.level}",
                f"Acción: {dispatch.manifest.get('action') or request.action}",
                f"Actividad: {dispatch.manifest.get('activity_number') or request.activity_number}",
                f"Motores: {', '.join(dispatch.manifest.get('engines') or request.engines)}",
                f"Consensus score: {consensus.get('consensus_score', 0)}",
                f"Compilaciones registradas: {len(compile_results)}",
            ]
        )
    elif isinstance(request, ActivityMonitorRequest):
        cycles = dispatch.manifest.get("cycles", []) if isinstance(dispatch.manifest.get("cycles"), list) else []
        lines.extend(
            [
                "Activity monitor ejecutado.",
                f"Target: {dispatch.manifest.get('target') or request.target}",
                f"Actividad: {dispatch.manifest.get('activity_number') or request.activity_number}",
                f"Backend: {dispatch.manifest.get('workflow_backend') or request.workflow_backend}",
                f"Ciclos registrados: {len(cycles)}",
                f"Estado final: {'PASS' if dispatch.manifest.get('ok') else 'PENDIENTE'}",
            ]
        )
    lines.extend([f"Run: {run_dir}", f"Manifest: {manifest_path}", f"Reporte: {report_path}"])
    return "\n".join(lines)