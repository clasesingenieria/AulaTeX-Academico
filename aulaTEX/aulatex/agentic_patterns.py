from __future__ import annotations

import functools
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from .llm_bridge import LLMCallResult


PATTERN_CATALOG = (
    {
        "id": "ch05-planning-memory",
        "source": "chapter05",
        "name": "Planning + memory augmented agent",
        "applied_as": "plan editorial, memoria compartida de hallazgos y continuidad entre ciclos",
    },
    {
        "id": "ch07-tool-workflow",
        "source": "chapter07",
        "name": "Tool-using agent + stateful workflow",
        "applied_as": "registro de herramientas, invocacion segura, maquina de estados y auditoria",
    },
    {
        "id": "ch08-verification",
        "source": "chapter08",
        "name": "Verification and validation agent",
        "applied_as": "rubrica verificable para identidad, bibliografia, trazabilidad y compilacion",
    },
    {
        "id": "ch15-consensus",
        "source": "chapter15",
        "name": "Collective intelligence consensus",
        "applied_as": "roles especializados, critico adversarial y puntuacion de consenso editorial",
    },
)


@dataclass(frozen=True)
class AgentTask:
    stage: str
    role: str
    mission: str
    prompt: str
    weight: float = 1.0


@dataclass(frozen=True)
class AgentEvent:
    timestamp: str
    state: str
    action: str
    status: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {
            "timestamp": self.timestamp,
            "state": self.state,
            "action": self.action,
            "status": self.status,
            "detail": self.detail,
        }


@dataclass
class SharedMemory:
    notes: list[str] = field(default_factory=list)
    proposals: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)

    def remember(self, category: str, text: str) -> None:
        value = text.strip()
        if not value:
            return
        if category == "proposal":
            self.proposals.append(value)
        elif category == "risk":
            self.risks.append(value)
        else:
            self.notes.append(value)

    def summary(self, max_chars: int = 2400) -> str:
        chunks: list[str] = []
        if self.notes:
            chunks.append("Notas:\n" + "\n".join(f"- {item}" for item in self.notes[-6:]))
        if self.proposals:
            chunks.append("Propuestas:\n" + "\n".join(f"- {item}" for item in self.proposals[-4:]))
        if self.risks:
            chunks.append("Riesgos:\n" + "\n".join(f"- {item}" for item in self.risks[-6:]))
        text = "\n\n".join(chunks)
        return text[:max_chars]


class AgenticStateMachine:
    TRANSITIONS = {
        "initialized": {"planned", "failed"},
        "planned": {"researched", "evaluated", "finalized", "failed"},
        "researched": {"generated", "evaluated", "finalized", "failed"},
        "generated": {"compiled", "evaluated", "failed"},
        "compiled": {"evaluated", "failed"},
        "evaluated": {"finalized", "failed"},
        "failed": {"finalized"},
        "finalized": set(),
    }

    def __init__(self) -> None:
        self.state = "initialized"
        self.events: list[AgentEvent] = []
        self.record("init", "ok", "AulaTeX workflow initialized")

    def transition(self, next_state: str, detail: str, *, guard: bool = True) -> bool:
        allowed = self.TRANSITIONS.get(self.state, set())
        if not guard:
            self.record(f"{self.state}->{next_state}", "blocked", detail)
            return False
        if next_state not in allowed:
            self.record(f"{self.state}->{next_state}", "blocked", "invalid transition: " + detail)
            return False
        previous = self.state
        self.state = next_state
        self.record(f"{previous}->{next_state}", "ok", detail)
        return True

    def record(self, action: str, status: str, detail: str) -> None:
        self.events.append(
            AgentEvent(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                state=self.state,
                action=action,
                status=status,
                detail=detail,
            )
        )

    def as_dicts(self) -> list[dict[str, str]]:
        return [event.as_dict() for event in self.events]

    def to_markdown(self) -> str:
        lines = ["# Auditoria agentica AulaTeX", ""]
        for event in self.events:
            lines.append(f"- {event.timestamp} [{event.status}] `{event.state}` {event.action}: {event.detail}")
        lines.append("")
        return "\n".join(lines)


@dataclass(frozen=True)
class InvocationResult:
    ok: bool
    result: Any = None
    error: str = ""


def graceful_fallback(
    fallback_value: Any = None,
    *,
    max_retries: int = 1,
    on_failure: Callable[[str, Exception], None] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for attempt in range(1, max(1, max_retries) + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if attempt < max_retries:
                        time.sleep(min(2 ** (attempt - 1), 8))
            if on_failure and last_exc is not None:
                try:
                    on_failure(getattr(func, "__name__", "callable"), last_exc)
                except Exception:
                    pass
            return fallback_value

        return wrapper

    return decorator


def safe_invoke(func: Callable[..., Any], *args: Any, **kwargs: Any) -> InvocationResult:
    try:
        return InvocationResult(True, func(*args, **kwargs), "")
    except Exception as exc:
        return InvocationResult(False, None, f"{type(exc).__name__}: {exc}")


@dataclass(frozen=True)
class ConsensusReport:
    consensus_score: float
    passed: bool
    criteria: dict[str, bool]
    role_scores: dict[str, float]
    risks: list[str]
    recommendations: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "consensus_score": round(self.consensus_score, 2),
            "passed": self.passed,
            "criteria": self.criteria,
            "role_scores": {key: round(value, 2) for key, value in self.role_scores.items()},
            "risks": self.risks,
            "recommendations": self.recommendations,
        }

    def to_markdown(self) -> str:
        lines = [
            "## Consenso y validacion",
            "",
            f"- Puntuacion de consenso: {self.consensus_score:.2f}/10",
            f"- Estado: {'PASS' if self.passed else 'REVISAR'}",
            "",
            "### Criterios",
        ]
        for criterion, ok in self.criteria.items():
            lines.append(f"- {criterion}: {'OK' if ok else 'FALTA'}")
        lines.append("")
        lines.append("### Puntuacion por rol")
        for role, score in self.role_scores.items():
            lines.append(f"- {role}: {score:.2f}/10")
        if self.risks:
            lines.append("")
            lines.append("### Riesgos")
            lines.extend(f"- {risk}" for risk in self.risks)
        if self.recommendations:
            lines.append("")
            lines.append("### Recomendaciones")
            lines.extend(f"- {item}" for item in self.recommendations)
        lines.append("")
        return "\n".join(lines)


class EditorialConsensusEngine:
    REQUIRED_TERMS = {
        "identidad_institucional": ("institucional", "identidad", "programa"),
        "bibliografia": ("bibliografia", "fuente", "referencia"),
        "trazabilidad": ("trazabilidad", "criterio", "rubrica", "evidencia"),
        "compilacion": ("compilacion", "latex", "tex", "pdf"),
        "riesgos": ("riesgo", "faltante", "placeholder", "error"),
    }

    def evaluate(self, tasks: list[AgentTask], results: list[LLMCallResult]) -> ConsensusReport:
        merged = "\n\n".join(result.text for result in results if result.ok).lower()
        criteria = {
            name: any(term in merged for term in terms)
            for name, terms in self.REQUIRED_TERMS.items()
        }
        role_scores: dict[str, float] = {}
        for task, result in zip(tasks, results):
            role_scores[task.role] = self._score(task, result)
        criterion_score = 10.0 * (sum(1 for ok in criteria.values() if ok) / max(1, len(criteria)))
        role_score = sum(role_scores.values()) / max(1, len(role_scores))
        consensus_score = (criterion_score * 0.45) + (role_score * 0.55)
        risks = self._risks(criteria, results)
        recommendations = self._recommendations(criteria, consensus_score)
        return ConsensusReport(
            consensus_score=consensus_score,
            passed=consensus_score >= 7.0 and not risks,
            criteria=criteria,
            role_scores=role_scores,
            risks=risks,
            recommendations=recommendations,
        )

    def _score(self, task: AgentTask, result: LLMCallResult) -> float:
        if not result.ok or not result.text.strip():
            return 0.0
        text = result.text.lower()
        score = 3.0
        if len(result.text) >= 900:
            score += 1.5
        if "##" in result.text or "- " in result.text:
            score += 1.0
        for keyword in self._role_keywords(task.role):
            if keyword in text:
                score += 0.8
        if "supuesto" in text or "no invent" in text or "si falta" in text:
            score += 0.7
        return min(10.0, score * task.weight)

    def _role_keywords(self, role: str) -> tuple[str, ...]:
        role_l = role.lower()
        if "investigador" in role_l:
            return ("fuente", "contexto", "hallazgo", "riesgo")
        if "arquitecto" in role_l:
            return ("estructura", "plantilla", "reporte", "presentacion")
        if "verificador" in role_l:
            return ("checklist", "compilacion", "criterio", "evidencia")
        if "critico" in role_l:
            return ("riesgo", "faltante", "bloqueante", "aceptacion")
        return ("editorial", "institucional", "trazabilidad")

    def _risks(self, criteria: dict[str, bool], results: list[LLMCallResult]) -> list[str]:
        risks = [f"Criterio sin cobertura: {name}" for name, ok in criteria.items() if not ok]
        failed = [result.engine for result in results if not result.ok or not result.text.strip()]
        if failed:
            risks.append("LLM sin respuesta util: " + ", ".join(failed))
        return risks

    def _recommendations(self, criteria: dict[str, bool], consensus_score: float) -> list[str]:
        recommendations: list[str] = []
        if not criteria.get("bibliografia", False):
            recommendations.append("Ejecutar un ciclo de recuperacion documental antes de generar actividad final.")
        if not criteria.get("compilacion", False):
            recommendations.append("Activar compilacion y anexar logs latexmk al siguiente ciclo.")
        if consensus_score < 7.0:
            recommendations.append("Repetir con al menos tres roles: investigador, arquitecto y critico.")
        if not recommendations:
            recommendations.append("Usar el reporte como retroalimentacion editorial aplicable al objetivo.")
        return recommendations


def build_editorial_tasks(request: Any, context: str, memory: SharedMemory | None = None) -> list[AgentTask]:
    memory_text = memory.summary() if memory else ""
    base = (
        "Eres AulaTeX, sistema multiagente editorial para plantillas LaTeX institucionales. "
        "Opera con los patrones: planificacion con memoria, uso de herramientas, flujo con estados, "
        "verificacion-validacion y consenso multiagente. Trabaja en espanol academico, no inventes fuentes "
        "y marca supuestos cuando falte informacion.\n\n"
        f"Nivel: {request.level}\n"
        f"Accion: {request.action}\n"
        f"Actividad: {request.activity_number}\n\n"
        f"Modo de generacion: {getattr(request, 'generation_mode', 'direct')}\n"
        f"Padre editorial: {getattr(request, 'parent_scope_key', '') or 'N/A'}\n"
        f"Nivel hijo: {getattr(request, 'child_level', '') or 'N/A'}\n"
        f"Hijo solicitado: {getattr(request, 'child_name', '') or 'N/A'}\n\n"
        f"Memoria compartida:\n{memory_text or 'Sin memoria previa en este ciclo.'}\n\n"
        f"Contexto local:\n{context}\n"
    )
    return [
        AgentTask(
            stage="planificar",
            role="Planificador editorial",
            mission="descomponer el objetivo en plan ejecutable y criterios de aceptacion",
            prompt=base
            + "\nROL PLANIFICADOR: produce un plan breve por fases para investigar, generar, compilar y evaluar. "
            "Incluye criterios de aceptacion por institucion, carrera, materia y actividad, "
            "mas una seccion explicita de riesgos, faltantes, placeholders y errores bloqueantes.",
            weight=1.0,
        ),
        AgentTask(
            stage="investigar",
            role="Investigador documental",
            mission="detectar fuentes, contexto curricular y faltantes editoriales",
            prompt=base
            + "\nROL INVESTIGADOR: diagnostica identidad institucional, programa analitico, bibliografia, "
            "estructura local, activos visuales y riesgos de trazabilidad. Prioriza hallazgos.",
            weight=1.05,
        ),
        AgentTask(
            stage="generar",
            role="Arquitecto de plantillas",
            mission="proponer estructura de reporte/presentacion y actividad",
            prompt=base
            + "\nROL ARQUITECTO: genera propuesta lista para convertir a archivos. Incluye reporte, presentacion, "
            "pautas de realizacion, bibliografia, imagen institucional y control editorial.",
            weight=1.0,
        ),
        AgentTask(
            stage="validar",
            role="Verificador y validador",
            mission="verificar consistencia, compilacion y evidencias",
            prompt=base
            + "\nROL VERIFICADOR: evalua si la propuesta es defendible y compilable. Devuelve checklist con "
            "evidencia, riesgos latexmk, cobertura bibliografica, placeholders y pruebas recomendadas.",
            weight=1.1,
        ),
        AgentTask(
            stage="criticar",
            role="Critico adversarial",
            mission="encontrar fallas antes de aplicar cambios",
            prompt=base
            + "\nROL CRITICO ADVERSARIAL: busca errores bloqueantes, omisiones institucionales, alucinaciones, "
            "fuentes no verificadas, problemas de compilacion y criterios para el siguiente ciclo.",
            weight=1.1,
        ),
    ]


def pattern_catalog_markdown() -> str:
    lines = ["# Patrones agenticos integrados en AulaTeX", ""]
    for item in PATTERN_CATALOG:
        lines.append(f"## {item['name']}")
        lines.append(f"- Origen local: `{item['source']}`")
        lines.append(f"- Uso en AulaTeX: {item['applied_as']}")
        lines.append("")
    return "\n".join(lines)
