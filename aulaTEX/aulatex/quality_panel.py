"""Panel de jueces de calidad editorial: heuristica + reward model + LLM.

Problema que resuelve
---------------------
``ActivityOptimizer`` decide si aplica una mejora comparando ``_quality_score``
antes y despues. Ese score es un proxy de SUPERFICIE: cuenta citas, secciones y
conectores con expresiones regulares. Optimizar contra el invita al efecto
Goodhart: el texto aprende a inflar la metrica (mas ``\\cite``, mas "por tanto")
sin mejorar el argumento.

La respuesta no es sustituir el proxy por otro juez unico -- eso solo mueve el
sesgo de sitio -- sino someter cada candidato a tres jueces con criterios
INDEPENDIENTES y exigir mayoria:

    heuristic  : forma verificable        (regex, deterministico, gratis)
    reward     : juicio aprendido          (encoder entrenado con el corpus real)
    llm        : razonamiento sobre fondo  (modelo potente, caro)

Enganar a los tres a la vez es mucho mas dificil que inflar un contador.

Honestidad sobre los limites
----------------------------
* El reward model aprendio DEL proxy heuristico: correlaciona con el (Spearman
  ~0.95), asi que sus votos no son del todo independientes. Aporta sobre todo
  tolerancia a la forma exacta y vision del documento completo (4096 tokens
  frente a los ~1000 que mira el regex por seccion).
* El juez LLM es el unico que razona sobre el contenido, y tambien el unico
  que puede fallar por indisponibilidad. Si no responde, se abstiene: no
  bloquea la decision.
* Con menos de dos jueces disponibles el panel degrada a la heuristica sola,
  que es el comportamiento actual. Nunca queda peor que antes.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

# Peso de cada juez cuando se pide un veredicto ponderado en vez de por mayoria.
DEFAULT_WEIGHTS = {"heuristic": 0.35, "reward": 0.35, "llm": 0.30}

# Diferencia por debajo de la cual dos scores se consideran empatados. Evita que
# el ruido numerico cuente como mejora.
SCORE_EPSILON = 0.25

_JUDGE_PROMPT = """Eres un evaluador editorial academico. Compara dos versiones de un
fragmento LaTeX y decide cual tiene MAYOR calidad academica.

Criterios, en orden de peso:
1. Solidez argumentativa: hay tesis, desarrollo y cierre, no enumeracion suelta.
2. Sustento: las afirmaciones se apoyan en fuentes citadas pertinentes.
3. Precision conceptual: los terminos se usan con rigor disciplinar.
4. Redaccion academica: prosa conectada, sin metadiscurso de ejecucion.

NO premies el mero aumento de citas, secciones o conectores si no elevan el
argumento. Un texto mas largo no es mejor por serlo.

=== VERSION A (actual) ===
{before}

=== VERSION B (propuesta) ===
{after}

Responde SOLO con JSON:
{{"mejor": "A"|"B"|"empate", "confianza": 0.0-1.0, "razon": "<una frase>"}}"""


@dataclass(frozen=True)
class JudgeVote:
    """Voto de un juez. ``improved`` es None cuando el juez se abstiene."""

    judge: str
    improved: bool | None
    score_before: float = 0.0
    score_after: float = 0.0
    confidence: float = 1.0
    reason: str = ""
    available: bool = True

    @property
    def delta(self) -> float:
        return self.score_after - self.score_before


@dataclass(frozen=True)
class PanelVerdict:
    improved: bool
    votes: tuple[JudgeVote, ...]
    rule: str
    detail: str = ""

    @property
    def available_votes(self) -> tuple[JudgeVote, ...]:
        return tuple(v for v in self.votes if v.improved is not None)

    @property
    def agreement(self) -> float:
        """Fraccion de jueces disponibles que coinciden con el veredicto."""
        votes = self.available_votes
        if not votes:
            return 0.0
        return sum(1 for v in votes if v.improved == self.improved) / len(votes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "improved": self.improved,
            "rule": self.rule,
            "agreement": round(self.agreement, 3),
            "detail": self.detail,
            "votes": [
                {
                    "judge": v.judge,
                    "improved": v.improved,
                    "score_before": round(v.score_before, 2),
                    "score_after": round(v.score_after, 2),
                    "confidence": round(v.confidence, 2),
                    "available": v.available,
                    "reason": v.reason,
                }
                for v in self.votes
            ],
        }


class RewardModelJudge:
    """Juez basado en el encoder entrenado con el corpus editorial del repo.

    Carga perezosa: si el modelo no existe o falta torch, el juez se declara
    no disponible y el panel sigue funcionando sin el.
    """

    def __init__(self, model_dir: str | Path | None = None) -> None:
        self.model_dir = Path(model_dir) if model_dir else None
        self._model = None
        self._tokenizer = None
        self._failed = False

    def _ensure_loaded(self) -> bool:
        if self._model is not None:
            return True
        if self._failed or self.model_dir is None or not self.model_dir.exists():
            return False
        try:
            import torch  # noqa: F401
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(str(self.model_dir))
            self._model = AutoModelForSequenceClassification.from_pretrained(str(self.model_dir))
            self._model.eval()
            return True
        except Exception:  # noqa: BLE001 - un juez caido no debe tumbar el ciclo
            self._failed = True
            return False

    def score(self, text: str) -> float | None:
        if not self._ensure_loaded():
            return None
        try:
            import torch

            batch = self._tokenizer(text, truncation=True, max_length=4096, return_tensors="pt")
            with torch.no_grad():
                logits = self._model(**batch).logits
            return float(logits.squeeze().item()) * 100.0
        except Exception:  # noqa: BLE001
            return None

    def vote(self, before: str, after: str) -> JudgeVote:
        score_before = self.score(before)
        score_after = self.score(after)
        if score_before is None or score_after is None:
            return JudgeVote("reward", None, available=False,
                             reason="reward model no disponible")
        if abs(score_after - score_before) < SCORE_EPSILON:
            return JudgeVote("reward", None, score_before, score_after,
                             reason="empate dentro del margen de ruido")
        return JudgeVote("reward", score_after > score_before, score_before, score_after)


class LLMJudge:
    """Juez que razona sobre el contenido con un modelo potente."""

    def __init__(self, llm: Any, engine: str = "", max_tokens: int = 800) -> None:
        self.llm = llm
        self.engine = engine
        self.max_tokens = max_tokens

    def vote(self, before: str, after: str) -> JudgeVote:
        prompt = _JUDGE_PROMPT.format(before=before[:12000], after=after[:12000])
        try:
            # 'revision' encadena GPT-Pro -> Claude Foundry -> Sonnet, con opus de red.
            result = self.llm.call_with_safety_net(
                prompt, task="revision", engine=self.engine or None,
                max_tokens=self.max_tokens)
        except Exception as exc:  # noqa: BLE001 - la indisponibilidad es abstencion
            return JudgeVote("llm", None, available=False,
                             reason=f"{exc.__class__.__name__}")
        if not getattr(result, "ok", False):
            return JudgeVote("llm", None, available=False,
                             reason=(getattr(result, "error", "") or "sin respuesta")[:120])
        payload = _extract_json(result.text)
        if not payload:
            return JudgeVote("llm", None, available=False,
                             reason="respuesta no parseable")

        choice = str(payload.get("mejor", "")).strip().upper()
        confidence = float(payload.get("confianza", 0.5) or 0.5)
        reason = str(payload.get("razon", ""))[:200]
        if choice == "B":
            return JudgeVote("llm", True, confidence=confidence, reason=reason)
        if choice == "A":
            return JudgeVote("llm", False, confidence=confidence, reason=reason)
        return JudgeVote("llm", None, confidence=confidence, reason=reason or "empate")


def _extract_json(text: str) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


class QualityPanel:
    """Consolida los votos de los jueces en un veredicto unico."""

    def __init__(
        self,
        heuristic_score: Callable[[str], float],
        reward_judge: RewardModelJudge | None = None,
        llm_judge: LLMJudge | None = None,
        weights: dict[str, float] | None = None,
    ) -> None:
        self.heuristic_score = heuristic_score
        self.reward_judge = reward_judge
        self.llm_judge = llm_judge
        self.weights = weights or DEFAULT_WEIGHTS

    def _heuristic_vote(self, before: str, after: str) -> JudgeVote:
        score_before = float(self.heuristic_score(before))
        score_after = float(self.heuristic_score(after))
        if abs(score_after - score_before) < SCORE_EPSILON:
            return JudgeVote("heuristic", None, score_before, score_after,
                             reason="sin cambio medible")
        return JudgeVote("heuristic", score_after > score_before, score_before, score_after)

    def evaluate(self, before: str, after: str, *, allow_tie: bool = False) -> PanelVerdict:
        """Veredicto por mayoria de los jueces disponibles.

        ``allow_tie`` acepta el candidato cuando hay empate. Se usa cuando la
        mejora persigue otro objetivo verificable (por ejemplo, resolver un
        hallazgo semantico) y basta con no degradar la calidad.
        """
        votes: list[JudgeVote] = [self._heuristic_vote(before, after)]
        if self.reward_judge is not None:
            votes.append(self.reward_judge.vote(before, after))
        if self.llm_judge is not None:
            votes.append(self.llm_judge.vote(before, after))

        decisive = [v for v in votes if v.improved is not None]

        # Sin jueces decisivos: solo se acepta si el llamador tolera el empate.
        if not decisive:
            return PanelVerdict(allow_tie, tuple(votes), "sin-votos",
                                "ningun juez emitio un voto decisivo")

        # Un solo juez: degradacion controlada al comportamiento anterior.
        if len(decisive) == 1:
            vote = decisive[0]
            return PanelVerdict(vote.improved or (allow_tie and vote.improved is None),
                                tuple(votes), f"juez-unico:{vote.judge}",
                                "solo un juez disponible; sin panel")

        favor = sum(1 for v in decisive if v.improved)
        against = len(decisive) - favor
        if favor > against:
            return PanelVerdict(True, tuple(votes), "mayoria",
                                f"{favor} a favor / {against} en contra")
        if against > favor:
            return PanelVerdict(False, tuple(votes), "mayoria",
                                f"{favor} a favor / {against} en contra")

        # Empate real: desempata la suma ponderada de confianzas.
        weighted = sum(
            self.weights.get(v.judge, 0.0) * v.confidence * (1 if v.improved else -1)
            for v in decisive
        )
        if abs(weighted) < 1e-9:
            return PanelVerdict(allow_tie, tuple(votes), "empate",
                                "jueces divididos sin desempate")
        return PanelVerdict(weighted > 0, tuple(votes), "ponderado",
                            f"peso neto {weighted:+.2f}")


def build_default_panel(
    heuristic_score: Callable[[str], float],
    llm: Any | None = None,
    *,
    reward_model_dir: str | Path | None = None,
    llm_engine: str = "",
    enable_llm_judge: bool | None = None,
) -> QualityPanel:
    """Panel con los jueces que esten disponibles en el entorno.

    ``AULATEX_REWARD_MODEL_DIR``  ruta del encoder entrenado.
    ``AULATEX_PANEL_LLM_JUDGE``   '0' desactiva el juez LLM (por costo).
    """
    model_dir = reward_model_dir or os.getenv("AULATEX_REWARD_MODEL_DIR", "")
    reward_judge = RewardModelJudge(model_dir) if model_dir else None

    if enable_llm_judge is None:
        enable_llm_judge = os.getenv("AULATEX_PANEL_LLM_JUDGE", "1").strip() != "0"
    llm_judge = LLMJudge(llm, engine=llm_engine) if (llm is not None and enable_llm_judge) else None

    return QualityPanel(heuristic_score, reward_judge, llm_judge)
