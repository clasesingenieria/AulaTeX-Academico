"""Ciclos de optimización de calidad que SÍ mejoran el .tex real.

A diferencia de ``agent --cycle-mode full`` (que solo genera propuestas LLM
efímeras y puntúa un consenso que no toca el archivo), este módulo ejecuta ciclos
que:

1. Miden la calidad editorial real del ``.tex`` (score propio + contrato).
2. Piden al LLM UNA mejora concreta y aplicable como reemplazo de un bloque
   textual existente (JSON estructurado).
3. Aplican el reemplazo de forma segura solo si el bloque original existe.
4. Recompilan y verifican que el contrato editorial siga en 100 y el PDF exista.
5. Revierten el ciclo si la compilación falla, el contrato baja o la calidad no
   mejora.

Así, tras converger el contrato a 100, los ciclos adicionales elevan la calidad
del documento de forma verificable y quedan registrados.
"""

from __future__ import annotations

import json
import re
import statistics
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .activity_observer import (
    FOOTER_METADATA_MAX_CHARS,
    FOOTER_METADATA_MIN_CHARS,
    ActivityObservationRequest,
    ActivityObserver,
    footer_metadata_text,
)
from .llm_bridge import DEFAULT_MAX_TOKENS, AulaTeXLLMClient
from .quality_panel import PanelVerdict, QualityPanel, build_default_panel
from .semantic_audit import SemanticAuditResult, SemanticAuditor
from .workspace import AulaTeXWorkspace


POLICY_IMPROVEMENT_KINDS = (
    "correccion-semantica",
    "enumeracion",
    "conector",
    "precision-cita",
    "postura-propia",
    "estructura",
)
QUALITY_COMPONENTS = (
    "citas",
    "estructura",
    "base_conceptual",
    "listas",
    "conectores",
    "extension",
    "integridad",
)


@dataclass(frozen=True)
class ActivityOptimizeRequest:
    target: str
    activity_number: int = 1
    output: str = ""
    # Modo de parada. Por DEFECTO se optimiza hasta CONVERGER a target_quality
    # (no un número fijo de ciclos): se ejecutan los ciclos que sean necesarios
    # hasta alcanzar la calidad objetivo, estancarse o llegar al tope de seguridad.
    # Si el usuario fija cycles>0 explícitamente, se respeta ese número exacto.
    cycles: int = 0
    target_quality: float = 100.0
    max_cycles: int = 40
    stall_limit: int = 6
    engines: tuple[str, ...] = ("GPT-5.6-Luna", "GPT-5.6-Terra")
    max_tokens: int = DEFAULT_MAX_TOKENS
    backup: bool = True
    require_contract_100: bool = True
    run_semantic_audit: bool = True
    semantic_fail_closed: bool = True
    semantic_audit_engine: str = ""
    semantic_feedback_path: str = ""
    # Panel de jueces: sustituye la comparacion de _quality_score por mayoria
    # entre heuristica, reward model y juez LLM. Ver quality_panel.py.
    use_quality_panel: bool = False
    panel_llm_judge: bool = True
    reward_model_dir: str = ""
    use_trained_policy: bool = True
    policy_model_dir: str = ""


@dataclass(frozen=True)
class ActivityOptimizeResult:
    run_id: str
    run_dir: Path
    ok: bool
    manifest_path: Path
    report_path: Path
    applied_cycles: int
    quality_before: float
    quality_after: float
    tex_path: Path | None
    initial_tex_snapshot_path: Path | None = None
    final_tex_snapshot_path: Path | None = None
    semantic_blocking_before: int = 0
    semantic_blocking_after: int = 0
    semantic_audit_available: bool = True


@dataclass
class CycleRecord:
    index: int
    engine: str
    accepted: bool
    reason: str
    quality_before: float
    quality_after: float
    contract_before: float
    contract_after: float
    improvement_kind: str = ""
    diff_chars: int = 0
    semantic_blocking_before: int = 0
    semantic_blocking_after: int = 0
    panel_verdict: dict[str, Any] | None = None
    planned_engine: str = ""
    planned_improvement_kind: str = ""
    planned_action_source: str = "round-robin"
    planned_expected_acceptance: float | None = None
    planned_expected_reward: float | None = None
    quality_breakdown_before: dict[str, float] = field(default_factory=dict)
    quality_breakdown_after: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class PlannedAction:
    engine: str
    improvement_kind: str = ""
    source: str = "round-robin"
    expected_acceptance: float | None = None
    expected_reward: float | None = None


@dataclass(frozen=True)
class TrainedPolicyBundle:
    accept_pipeline: Any
    reward_pipeline: Any
    numeric_features: tuple[str, ...]
    categorical_features: tuple[str, ...]
    model_dir: Path


class ActivityOptimizer:
    def __init__(self, workspace: AulaTeXWorkspace | None = None, llm: AulaTeXLLMClient | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.observer = ActivityObserver(self.workspace)
        self.llm = llm or AulaTeXLLMClient()
        self.semantic_auditor = SemanticAuditor(self.llm)
        self._panel: QualityPanel | None = None
        self._policy_cache: TrainedPolicyBundle | None = None
        self._policy_cache_key: str = ""
        self._policy_error: str = ""
        self.root = self.workspace.feedback_root / "activity-optimize" / "runs"
        self.root.mkdir(parents=True, exist_ok=True)

    def optimize(self, request: ActivityOptimizeRequest) -> ActivityOptimizeResult:
        run_id = f"{self.workspace.timestamp()}-activity-{int(request.activity_number):02d}-optimize"
        run_dir = self._resolve_run_dir(request, run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        observation = self._observe(request, run_dir / "obs-initial")
        state = json.loads(observation["state"].read_text(encoding="utf-8"))
        evaluation = json.loads(observation["evaluation"].read_text(encoding="utf-8"))
        tex_path = self.workspace.resolve_target(state.get("target_tex", ""))

        if not tex_path.exists() or not tex_path.is_file():
            return self._finalize(request, run_id, run_dir, [], 0.0, 0.0, None, ok=False,
                                  note="No se encontró el TEX de la actividad.")

        # Base conceptual: cargar conceptos del extractor (si existen) para puntuar
        # su cobertura. Si faltan y la base conceptual del .tex es escasa, se intenta
        # correr el extractor en modo local para materializar conceptos.
        self._current_concepts = self._load_or_build_concepts(request, tex_path)
        original_text = tex_path.read_text(encoding="utf-8", errors="replace")

        contract_before = float((evaluation.get("contract") or {}).get("score", 0.0))
        if request.require_contract_100 and contract_before < 100.0:
            return self._finalize(request, run_id, run_dir, [], 0.0, 0.0, tex_path, ok=False,
                                  initial_text=original_text, final_text=original_text,
                                  note=(f"El contrato editorial está en {contract_before}/100; "
                                        "primero converge con activity-monitor antes de optimizar calidad."))

        if request.backup:
            backup_path = tex_path.with_suffix(tex_path.suffix + ".activity-optimize.bak")
            backup_path.write_text(original_text, encoding="utf-8")

        rubric = self._rubric_text(state, evaluation)
        current_text = original_text
        quality_start = self._quality_score(current_text)
        contract_current = contract_before

        cycles: list[CycleRecord] = []
        engines = request.engines or ("GPT-5.6-Luna", "GPT-5.6-Terra")
        semantic_engine = request.semantic_audit_engine.strip() or engines[-1]
        semantic_current = self._semantic_audit(
            request,
            current_text,
            tex_path,
            semantic_engine,
            run_dir / "semantic-initial.json",
        )
        semantic_initial = semantic_current

        # Modo de parada:
        #  - fixed_cycles (cycles>0): número exacto de ciclos solicitado.
        #  - convergencia (cycles<=0, por DEFECTO): iterar hasta que la calidad
        #    alcance target_quality, se estanque (stall_limit ciclos consecutivos
        #    sin mejora aceptada) o se llegue al tope de seguridad max_cycles.
        fixed_cycles = int(request.cycles) if int(request.cycles) > 0 else 0
        target_quality = float(request.target_quality)
        hard_cap = fixed_cycles if fixed_cycles > 0 else max(1, int(request.max_cycles))
        stall_limit = max(1, int(request.stall_limit))
        stall = 0

        index = 0
        while index < hard_cap:
            # Parada por convergencia (solo en modo convergencia).
            if fixed_cycles == 0:
                if (
                    self._quality_score(current_text) >= target_quality
                    and self._semantic_gate_passed(request, semantic_current)
                ):
                    break
                if request.run_semantic_audit and not semantic_current.audit_available:
                    break
                if stall >= stall_limit:
                    break
            index += 1
            quality_breakdown_before = self._quality_breakdown(current_text, self._current_concepts)
            quality_before = round(sum(quality_breakdown_before.values()), 2)
            action = self._select_cycle_action(
                request,
                engines,
                index,
                quality_before,
                contract_current,
                len(semantic_current.blocking_findings),
                quality_breakdown_before,
            )
            engine = action.engine
            cycle_dir = run_dir / f"cycle-{index:02d}"
            cycle_dir.mkdir(parents=True, exist_ok=True)

            proposal = self._request_improvement(
                engine,
                current_text,
                rubric,
                request,
                cycle_dir,
                semantic_current,
                desired_improvement_kind=action.improvement_kind,
            )

            if proposal is None:
                # Solo cuenta como estancamiento si el motor SÍ respondió y aun así
                # no propuso nada útil; un 401 no dice nada sobre la calidad del texto.
                transient = getattr(self, "_last_llm_failure_transient", False)
                if not transient:
                    stall += 1
                razon = ("El motor no respondió por un fallo de infraestructura (credenciales o red)."
                         if transient else "El motor no devolvió una propuesta aplicable.")
                cycles.append(CycleRecord(index, engine, False, razon,
                                          quality_before, quality_before, contract_current, contract_current,
                                          planned_engine=action.engine,
                                          planned_improvement_kind=action.improvement_kind,
                                          planned_action_source=action.source,
                                          planned_expected_acceptance=action.expected_acceptance,
                                          planned_expected_reward=action.expected_reward,
                                          quality_breakdown_before=quality_breakdown_before,
                                          quality_breakdown_after=quality_breakdown_before))
                continue

            candidate_text, kind = self._apply_proposal(current_text, proposal)
            if candidate_text is None:
                stall += 1
                cycles.append(CycleRecord(index, engine, False,
                                          "El bloque original propuesto no se encontró textualmente en el TEX.",
                                          quality_before, quality_before, contract_current, contract_current,
                                          improvement_kind=proposal.get("improvement_kind", ""),
                                          planned_engine=action.engine,
                                          planned_improvement_kind=action.improvement_kind,
                                          planned_action_source=action.source,
                                          planned_expected_acceptance=action.expected_acceptance,
                                          planned_expected_reward=action.expected_reward,
                                          quality_breakdown_before=quality_breakdown_before,
                                          quality_breakdown_after=quality_breakdown_before))
                continue

            # Escribir candidato, recompilar y verificar contrato + calidad.
            tex_path.write_text(candidate_text, encoding="utf-8")
            new_eval = self._observe_eval(request, cycle_dir / "obs")
            contract_after = float((new_eval.get("contract") or {}).get("score", 0.0))
            compile_ok = self._compile_ok(new_eval)
            quality_breakdown_after = self._quality_breakdown(candidate_text, self._current_concepts)
            quality_after = round(sum(quality_breakdown_after.values()), 2)
            semantic_candidate = self._semantic_audit(
                request,
                candidate_text,
                tex_path,
                semantic_engine,
                cycle_dir / "semantic-candidate.json",
            )
            semantic_before_count = len(semantic_current.blocking_findings)
            semantic_after_count = len(semantic_candidate.blocking_findings)
            semantic_progress = self._semantic_candidate_acceptable(
                request, semantic_current, semantic_candidate
            )
            # Si el candidato resuelve un hallazgo semantico, basta con no degradar.
            resolves_semantic = semantic_after_count < semantic_before_count
            verdict = self._quality_verdict(
                request, current_text, candidate_text,
                quality_before, quality_after, allow_tie=resolves_semantic,
            )
            quality_progress = verdict.improved

            accept = (
                compile_ok
                and contract_after >= contract_current
                and (not request.require_contract_100 or contract_after >= 100.0)
                and quality_progress
                and semantic_progress
            )

            if accept:
                diff = abs(len(candidate_text) - len(current_text))
                current_text = candidate_text
                contract_current = contract_after
                semantic_current = semantic_candidate
                stall = 0  # hubo mejora aceptada: se reinicia el contador de estancamiento
                cycles.append(CycleRecord(index, engine, True, "Mejora aplicada y verificada.",
                                          quality_before, quality_after, contract_current, contract_after,
                                          improvement_kind=kind, diff_chars=diff,
                                          semantic_blocking_before=semantic_before_count,
                                          semantic_blocking_after=semantic_after_count,
                                          panel_verdict=verdict.to_dict() if request.use_quality_panel else None,
                                          planned_engine=action.engine,
                                          planned_improvement_kind=action.improvement_kind,
                                          planned_action_source=action.source,
                                          planned_expected_acceptance=action.expected_acceptance,
                                          planned_expected_reward=action.expected_reward,
                                          quality_breakdown_before=quality_breakdown_before,
                                          quality_breakdown_after=quality_breakdown_after))
            else:
                # Revertir el candidato.
                tex_path.write_text(current_text, encoding="utf-8")
                stall += 1  # ciclo sin mejora: acerca la parada por estancamiento
                reason = self._reject_reason(compile_ok, contract_after, contract_current, quality_after, quality_before, request)
                if request.use_quality_panel and not verdict.improved:
                    reason = f"{reason} | panel: {verdict.rule} ({verdict.detail})"
                cycles.append(CycleRecord(index, engine, False, reason,
                                          quality_before, quality_after, contract_current, contract_after,
                                          improvement_kind=kind,
                                          semantic_blocking_before=semantic_before_count,
                                          semantic_blocking_after=semantic_after_count,
                                          panel_verdict=verdict.to_dict() if request.use_quality_panel else None,
                                          planned_engine=action.engine,
                                          planned_improvement_kind=action.improvement_kind,
                                          planned_action_source=action.source,
                                          planned_expected_acceptance=action.expected_acceptance,
                                          planned_expected_reward=action.expected_reward,
                                          quality_breakdown_before=quality_breakdown_before,
                                          quality_breakdown_after=quality_breakdown_after))

        # Asegurar que el archivo final refleja el mejor estado aceptado.
        tex_path.write_text(current_text, encoding="utf-8")
        quality_end = self._quality_score(current_text)
        applied = sum(1 for c in cycles if c.accepted)
        ok = (
            quality_end >= quality_start
            and quality_end >= target_quality
            and contract_current >= contract_before
            and self._semantic_gate_passed(request, semantic_current)
        )
        note = (
            f"Calidad objetivo no alcanzada: {quality_end}/{target_quality}; "
            "se conserva el mejor estado aceptado."
            if quality_end < target_quality else ""
        )

        return self._finalize(request, run_id, run_dir, cycles, quality_start, quality_end, tex_path,
                              ok=ok, note=note, contract_before=contract_before, contract_after=contract_current,
                              applied=applied, initial_text=original_text, final_text=current_text,
                              semantic_before=semantic_initial,
                              semantic_after=semantic_current)

    # ---------------------------------------------------------------- observación

    def _observe(self, request: ActivityOptimizeRequest, out_dir: Path) -> dict[str, Path]:
        observation = self.observer.observe(
            ActivityObservationRequest(
                target=request.target,
                activity_number=request.activity_number,
                output=str(out_dir),
                compile_check=True,
            )
        )
        return {"state": observation.state_path, "evaluation": observation.evaluation_path}

    def _observe_eval(self, request: ActivityOptimizeRequest, out_dir: Path) -> dict[str, Any]:
        paths = self._observe(request, out_dir)
        return json.loads(paths["evaluation"].read_text(encoding="utf-8"))

    def _compile_ok(self, evaluation: dict[str, Any]) -> bool:
        checks = evaluation.get("checks") or {}
        # compile_ready acepta True/'unknown'/'environment-blocked'; el observer ya lo normaliza.
        return bool(checks.get("compile_ready", True))

    # ---------------------------------------------------------------- calidad

    def _quality_score(self, text: str) -> float:
        """Score de calidad editorial verificable (0-100), independiente del LLM."""
        concepts = getattr(self, "_current_concepts", None)
        return round(sum(self._quality_breakdown(text, concepts).values()), 2)

    def _quality_breakdown(self, text: str, concepts: list[str] | None = None) -> dict[str, float]:
        """Desglose por componente del score de calidad (cada uno con su tope).

        Filosofía editorial: PREMIAR prosa bien estructurada en subsecciones
        TEMÁTICAS del desarrollo y una BASE CONCEPTUAL suficiente que justifique el
        producto; PENALIZAR el exceso de listas y los títulos-etiqueta ('Marco
        conceptual', 'Desarrollo'). Topes (suman 100): citas 20, estructura 20,
        base_conceptual 15, listas 8, conectores 12, extension 10, integridad 15.
        """
        body = self._strip_comments(text)

        # Citas visibles (densidad): 20 pts con 5 citas.
        cites = len(re.findall(r"\\cite[tp]?\*?(?:\[[^\]]*\])*\{", body))
        c_cites = min(20.0, cites * 4.0)

        # Estructura: secciones (10) + subsecciones TEMÁTICAS del desarrollo (10) = 20 pts.
        # SOLO cuentan subsecciones del acto de Desarrollo (intro/conclusión en prosa).
        # Se PENALIZA usar títulos-etiqueta ('Marco conceptual', 'Desarrollo',
        # 'Metodología', 'Participación publicada'): restan porque no nombran el tema.
        sections = len(re.findall(r"\\section\{", body))
        dev_subsections = self._count_development_subsections(body)
        c_structure = min(10.0, sections * 3.4) + min(10.0, dev_subsections * 5.0)
        label_titles = re.findall(
            r"\\(?:sub)?section\*?\{\s*(marco conceptual|desarrollo|metodolog[íi]a[^}]*|"
            r"participaci[óo]n publicada[^}]*|lectura e interpretaci[óo]n)\s*\}",
            body, re.IGNORECASE)
        c_structure = max(0.0, c_structure - len(label_titles) * 3.0)

        # BASE CONCEPTUAL (15 pts): suficiencia de conceptos que justifican el producto.
        c_concept = self._concept_base_score(body, concepts)

        # Balance prosa/listas: 8 pts. PREMIA 1 lista (foro), PENALIZA exceso.
        enums = len(re.findall(r"\\begin\{(enumerate|itemize)\}", body))
        if enums == 0:
            c_enums = 6.0
        elif enums == 1:
            c_enums = 8.0
        elif enums == 2:
            c_enums = 6.0
        else:
            c_enums = max(0.0, 6.0 - (enums - 2) * 3.0)

        # Densidad argumentativa: conectores de razonamiento: 12 pts (~5 conectores).
        connectors = len(re.findall(
            r"\b(por tanto|por ello|en consecuencia|sin embargo|no obstante|es decir|"
            r"en cambio|por el contrario|de ese modo|as[íi]|adem[áa]s|dado que|puesto que|"
            r"en efecto|por consiguiente)\b",
            body, re.IGNORECASE))
        c_connectors = min(12.0, connectors * 2.4)

        # Extensión sustantiva del cuerpo: 10 pts con ~1000 palabras.
        words = len(re.findall(r"\b\w+\b", body))
        c_extension = min(10.0, words / 100.0)

        # Integridad / postura propia: 15 pts (~4 marcadores).
        integrity = len(re.findall(
            r"\b(desde mi perspectiva|considero|sostengo|mi postura|a mi juicio|"
            r"reflexi[óo]n propia|declaraci[óo]n de uso|inteligencia artificial|"
            r"no invent|supuesto)\b",
            body, re.IGNORECASE))
        c_integrity = min(15.0, integrity * 4.0)

        return {
            "citas": round(c_cites, 2),
            "estructura": round(c_structure, 2),
            "base_conceptual": round(c_concept, 2),
            "listas": round(c_enums, 2),
            "conectores": round(c_connectors, 2),
            "extension": round(c_extension, 2),
            "integridad": round(c_integrity, 2),
        }

    def _concept_base_score(self, body: str, concepts: list[str] | None) -> float:
        """Puntúa (0-15) la SUFICIENCIA de la base conceptual del desarrollo.

        Combina dos señales:
          (a) conceptos DEFINIDOS/destacados en el cuerpo (términos en \\textbf o
              \\textit dentro del desarrollo, que evidencian delimitación conceptual);
          (b) COBERTURA de los conceptos del extractor (si se proveen): proporción de
              conceptos clave del extractor mencionados en el cuerpo.
        Cada señal aporta hasta ~7.5 pts. Si no hay conceptos del extractor, la
        señal (a) puede alcanzar el tope por sí sola (documento autosuficiente).
        """
        # Región del desarrollo (donde debe vivir la base conceptual).
        dev = self._development_region(body)
        emphasised = set(
            m.group(1).strip().lower()
            for m in re.finditer(r"\\text(?:bf|it)\{([^}]{3,60})\}", dev)
        )
        # Señal (a): número de términos destacados (hasta 8 -> 7.5 pts).
        a = min(7.5, len(emphasised) * 1.25)

        # Señal (b): cobertura de conceptos del extractor.
        if concepts:
            # Normalizar acentos (LaTeX \'i y Unicode) para que la coincidencia no
            # falle por la codificacion; y cobertura por TOKENS significativos para
            # conceptos largos (basta con que el cuerpo cubra sus terminos clave).
            norm_body = self._normalize_concept_text(body)
            key = [str(x).strip() for x in concepts if len(str(x).strip()) >= 4]
            if key:
                covered = 0
                for concept in key:
                    nc = self._normalize_concept_text(concept)
                    if nc and nc in norm_body:
                        covered += 1
                        continue
                    # Cobertura por tokens: conceptos largos se dan por cubiertos si
                    # >=70% de sus tokens significativos (>=4 letras) estan en el cuerpo.
                    toks = [t for t in re.findall(r"[a-z]{4,}", nc)
                            if t not in {"para", "sobre", "entre", "segun", "entre",
                                         "relacionadas", "sistemas", "federales"}]
                    if toks and sum(1 for t in toks if t in norm_body) / len(toks) >= 0.7:
                        covered += 1
                ratio = covered / len(key)
                b = 7.5 * ratio
            else:
                b = 7.5
        else:
            # Sin conceptos del extractor: la señal (a) puede cubrir hasta el tope.
            b = min(7.5, a)
        return min(15.0, a + b)

    @staticmethod
    def _normalize_concept_text(text: str) -> str:
        """Normaliza acentos LaTeX (\\'i, \\'a, \\~n...) y Unicode a ASCII minusculas.

        Permite comparar conceptos del extractor (con acentos Unicode) contra el
        cuerpo del .tex (con acentos LaTeX o Unicode) sin falsos negativos.
        """
        import unicodedata
        s = text.lower()
        # Acentos LaTeX: \'a \'e \'i \'o \'u \~n \"u -> letra base.
        s = re.sub(r"\\['`^\"~=.]\s*\{?\\?([a-z])\}?", r"\1", s)
        s = re.sub(r"\\['`^\"~=.]([a-z])", r"\1", s)
        # Unicode -> ASCII.
        s = unicodedata.normalize("NFKD", s)
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        return s

    def _load_or_build_concepts(self, request: ActivityOptimizeRequest, tex_path: Path) -> list[str]:
        """Carga conceptos del extractor; si faltan y la base conceptual es escasa,
        intenta correr el extractor local (tfidf) para materializarlos.

        Nunca hace fallar la optimización: ante cualquier error, devuelve [].
        """
        target_root = tex_path.parent
        concepts = self._read_extractor_concepts(target_root)
        if concepts:
            return concepts
        # ¿Vale la pena correr el extractor? Solo si la base conceptual del .tex es
        # escasa (pocos términos destacados en el desarrollo).
        try:
            body = self._strip_comments(tex_path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            return []
        dev = self._development_region(body)
        emphasised = set(re.findall(r"\\text(?:bf|it)\{([^}]{3,60})\}", dev))
        if len(emphasised) >= 6:
            return []  # base conceptual suficiente; no hace falta el extractor
        # Intento de ejecución local del extractor (motor tfidf, sin API).
        try:
            from .extractor_adapter import ExtractorAdapter, ExtractorRequest

            adapter = ExtractorAdapter(self.workspace)
            adapter.run(ExtractorRequest(
                target=str(target_root),
                activity_number=int(request.activity_number),
                motor="tfidf",
            ))
            return self._read_extractor_concepts(target_root)
        except Exception:
            return []

    def _read_extractor_concepts(self, target_root: Path) -> list[str]:
        """Lee conceptos_detectados.json del extractor (varias ubicaciones posibles)."""
        candidates = [
            target_root / "extractor-aulatex" / "conceptos_detectados.json",
            target_root / "extractor-aulatex" / "conceptos.json",
        ]
        for path in candidates:
            data = self._safe_load_json(path)
            if data is None:
                continue
            return self._extract_concept_names(data)
        return []

    def _safe_load_json(self, path: Path) -> Any:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            return None
        return None

    def _extract_concept_names(self, data: Any) -> list[str]:
        """Normaliza distintas formas del JSON de conceptos a una lista de strings."""
        names: list[str] = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    names.append(item)
                elif isinstance(item, dict):
                    for k in ("concepto", "termino", "nombre", "label", "text"):
                        if item.get(k):
                            names.append(str(item[k]))
                            break
        elif isinstance(data, dict):
            for k in ("conceptos", "terminos", "items", "concepts"):
                if isinstance(data.get(k), list):
                    names.extend(self._extract_concept_names(data[k]))
        return [n.strip() for n in names if isinstance(n, str) and n.strip()]

    def _development_region(self, body: str) -> str:
        """Devuelve el texto del acto de Desarrollo (entre Introducción y Conclusión)."""
        sec_iter = list(re.finditer(r"\\section\*?\{([^}]*)\}", body))
        if not sec_iter:
            return body
        dev_start = None
        concl_start = None
        for m in sec_iter:
            title = m.group(1).lower()
            if dev_start is None and not re.search(r"introducci[óo]n", title) and not re.search(r"conclusi[óo]n", title):
                dev_start = m.end()
            if re.search(r"conclusi[óo]n", title):
                concl_start = m.start()
                break
        if dev_start is None:
            return body
        return body[dev_start: concl_start if concl_start is not None else len(body)]

    def _count_development_subsections(self, body: str) -> int:
        """Cuenta \\subsection SOLO dentro del acto de Desarrollo.

        El Desarrollo es la(s) sección(es) entre la Introducción y la Conclusión.
        Las subsecciones en Introducción o Conclusión NO cuentan: esos actos deben
        ser prosa continua. Si no puede delimitarse, cuenta todas (fallback).
        """
        # Localiza el inicio del desarrollo (fin de la Introducción) y el inicio de
        # la Conclusión.
        sec_iter = list(re.finditer(r"\\section\*?\{([^}]*)\}", body))
        if not sec_iter:
            return len(re.findall(r"\\subsection\*?\{", body))
        dev_start = None
        concl_start = None
        for m in sec_iter:
            title = m.group(1).lower()
            if dev_start is None and not re.search(r"introducci[óo]n", title):
                # primera sección que no es la introducción = inicio del desarrollo
                if not re.search(r"conclusi[óo]n", title):
                    dev_start = m.end()
            if re.search(r"conclusi[óo]n", title):
                concl_start = m.start()
                break
        if dev_start is None:
            return 0
        region = body[dev_start: concl_start if concl_start is not None else len(body)]
        return len(re.findall(r"\\subsection\*?\{", region))

    def _quality_gap_hint(self, text: str) -> str:
        """Frase que indica al LLM qué componentes están por debajo de su tope."""
        caps = {"citas": 20.0, "estructura": 20.0, "base_conceptual": 15.0, "listas": 8.0,
                "conectores": 12.0, "extension": 10.0, "integridad": 15.0}
        bd = self._quality_breakdown(text, getattr(self, "_current_concepts", None))
        body = self._strip_comments(text)
        enums = len(re.findall(r"\\begin\{(enumerate|itemize)\}", body))
        concepts = getattr(self, "_current_concepts", None)
        concept_hint = ""
        if concepts:
            low_body = body.lower()
            missing = [c for c in concepts if len(str(c)) >= 4 and str(c).lower() not in low_body][:6]
            if missing:
                concept_hint = " Conceptos clave aún no abordados: " + ", ".join(missing) + "."
        gaps = []
        labels = {
            "citas": "más citas visibles (\\citep con claves existentes)",
            "estructura": (
                "organizar el DESARROLLO en más subsecciones TEMÁTICAS cuyo TÍTULO NOMBRE EL "
                "CONCEPTO o el tema (NUNCA 'Marco conceptual', 'Desarrollo', 'Metodología' ni "
                "'Participación publicada'). La Introducción y la Conclusión van en PROSA "
                "CONTINUA, sin subsecciones"
            ),
            "base_conceptual": (
                "reforzar la BASE CONCEPTUAL que justifica el producto: definir y destacar "
                "(con \\textbf) los conceptos pertinentes y suficientes que gravitan alrededor "
                "del foro, en párrafos o subsecciones temáticas del desarrollo." + concept_hint
            ),
            "listas": (
                "reducir el número de listas/enumeraciones convirtiéndolas en PROSA argumentada "
                "(deja a lo sumo la lista estrictamente necesaria, p. ej. la del foro)"
                if enums >= 3 else
                "mantener a lo sumo 1 lista justificada (el resto en prosa)"
            ),
            "conectores": "más conectores lógicos (por tanto, sin embargo, en consecuencia...)",
            "extension": "desarrollar más el análisis (mayor extensión sustantiva)",
            "integridad": "reforzar la postura propia y la reflexión fundamentada",
        }
        for k, cap in caps.items():
            if bd.get(k, 0.0) < cap - 0.5:
                gaps.append(f"- {labels[k]} (actual {bd.get(k,0.0)}/{cap})")
        footer_hint = self._footer_metadata_hint(text)
        if footer_hint:
            gaps.append(footer_hint)
        if not gaps:
            return "El documento está cerca del máximo; refina precisión y cohesión en PROSA (evita añadir listas)."
        return (
            "Para acercar la calidad a 100, prioriza mejorar (PREFIERE prosa sobre listas, "
            "títulos que NOMBREN el concepto/tema):\n"
            + "\n".join(gaps)
        )

    def _footer_metadata_hint(self, text: str) -> str:
        """Directiva sobre el texto que la plantilla lleva al pie de página."""
        visible = footer_metadata_text(text)
        if not visible:
            return ""
        n = len(visible)
        if n > FOOTER_METADATA_MAX_CHARS:
            return (
                f"- ACORTAR \\documentsubtitle a un máximo de {FOOTER_METADATA_MAX_CHARS} caracteres "
                f"(actual {n}): la plantilla lo imprime en el pie de página junto al nombre del curso "
                f"y ambos bloques se SOLAPAN. Conservar el título completo en \\documenttitle y dejar "
                f"en el subtítulo una versión breve pero informativa, de {FOOTER_METADATA_MIN_CHARS}-"
                f"{FOOTER_METADATA_MAX_CHARS} caracteres. NO tocar \\documenttitle."
            )
        if n < FOOTER_METADATA_MIN_CHARS:
            return (
                f"- AMPLIAR \\documentsubtitle (actual {n} caracteres): queda demasiado escueto para el "
                f"pie de página. Redactarlo entre {FOOTER_METADATA_MIN_CHARS} y {FOOTER_METADATA_MAX_CHARS} "
                f"caracteres, acotando el objeto del trabajo sin repetir el título."
            )
        return ""

    # ---------------------------------------------------------------- LLM

    def _rubric_text(self, state: dict[str, Any], evaluation: dict[str, Any]) -> str:
        contract = evaluation.get("contract") or {}
        subject = state.get("subject") or state.get("scope_key") or ""
        technique = ""
        signals = state.get("signals") or {}
        technique = signals.get("didactic_technique") or contract.get("didactic_technique") or ""
        return (
            f"Materia/scope: {subject}\n"
            f"Técnica didáctica: {technique}\n"
            "Objetivo de calidad: elevar rigor argumentativo, densidad de citas pertinentes, "
            "estructura (listas/enumeraciones que ordenen el razonamiento), conectores lógicos, "
            "postura propia fundamentada e integridad académica, SIN cambiar la técnica didáctica, "
            "sin inventar fuentes ni claves de cita nuevas, y conservando el formato LaTeX."
        )

    def _request_improvement(self, engine: str, current_text: str, rubric: str,
                             request: ActivityOptimizeRequest, cycle_dir: Path,
                             semantic_audit: SemanticAuditResult,
                             desired_improvement_kind: str = "") -> dict[str, Any] | None:
        body = self._strip_comments(current_text)
        cite_keys = sorted(set(re.findall(r"\\cite[tp]?\*?(?:\[[^\]]*\])*\{([^}]+)\}", body)))
        allowed_keys = sorted({k.strip() for group in cite_keys for k in group.split(",") if k.strip()})
        semantic_guidance = self._semantic_guidance(semantic_audit)
        desired_kind_rule = ""
        if desired_improvement_kind:
            desired_kind_rule = (
                "- PRIORIDAD DE ESTE CICLO: intenta una mejora de tipo "
                f"'{desired_improvement_kind}'. El campo 'improvement_kind' DEBE reflejar ese tipo "
                "si encuentras una corrección local y segura; solo cambia de tipo si el documento no "
                "admite una mejora aplicable de esa clase en una única aparición exacta.\n"
            )

        prompt = (
            "Eres un editor académico experto en LaTeX. Se te da un documento .tex de una actividad "
            "universitaria que YA cumple el contrato editorial al 100%. Tu tarea es proponer UNA sola "
            "mejora de CALIDAD concreta y segura, expresada como el reemplazo textual de un bloque "
            "existente por una versión mejorada.\n\n"
            "REGLAS ESTRICTAS:\n"
            "- Devuelve SOLO un objeto JSON válido, sin texto adicional ni ```.\n"
            "- El campo 'original_block' DEBE ser una copia EXACTA y literal de un fragmento contiguo "
            "presente en el documento (incluye saltos de línea reales). Copia entre 2 y 24 líneas; "
            "si una observación aparece en varias zonas, corrige una zona exacta por ciclo y deja "
            "que los ciclos posteriores corrijan las demás.\n"
            "- El campo 'improved_block' es su reemplazo: mismo rol, mejor rigor/estructura/densidad, "
            "LaTeX válido y balanceado (no rompas entornos ni llaves).\n"
            "- NO inventes claves de cita nuevas. Solo puedes usar estas claves ya presentes: "
            f"{', '.join(allowed_keys) or '(ninguna)'}.\n"
            "- NO cambies la técnica didáctica. Conserva el sentido salvo cuando la AUDITORÍA "
            "SEMÁNTICA exija corregir una afirmación; esa corrección tiene prioridad.\n"
            "- Prefiere: convertir prosa difusa en enumeraciones ordenadas, añadir un conector lógico, "
            "precisar una afirmación con una cita ya existente, reforzar la postura propia o resolver "
            "UNA observación semántica bloqueante en una aparición exacta por ciclo. No incluyas "
            "secciones distantes ni uses puntos suspensivos: una corrección parcial aplicable es "
            "preferible a un bloque enorme no localizable.\n"
            f"{desired_kind_rule}\n"
            "Formato JSON EXACTO:\n"
            '{\n'
            '  "improvement_kind": "<correccion-semantica|enumeracion|conector|precision-cita|postura-propia|estructura>",\n'
            '  "justification": "<por qué eleva la calidad, 1-2 frases>",\n'
            '  "original_block": "<copia literal del bloque existente>",\n'
            '  "improved_block": "<bloque mejorado>"\n'
            '}\n\n'
            f"Guía de calidad:\n{rubric}\n\n"
            f"AUDITORÍA SEMÁNTICA (prioridad sobre mejoras formales):\n{semantic_guidance}\n\n"
            f"{self._quality_gap_hint(current_text)}\n\n"
            "DOCUMENTO .tex ACTUAL:\n"
            "-----8<-----\n"
            f"{current_text}\n"
            "-----8<-----\n"
        )

        # Un 401/429/5xx agota el ciclo sin que el motor llegue a proponer nada.
        # En corridas largas las credenciales caducan y así se perdía el 78% de
        # los ciclos, que además contaban como estancamiento.
        result = None
        for attempt in range(1, 4):
            result = self.llm.call(engine, prompt, max_tokens=request.max_tokens)
            if result.ok and result.text.strip():
                break
            if not self._is_transient_llm_failure(result):
                break
            if attempt < 3:
                time.sleep(2 ** attempt)

        raw = result.text if (result and result.ok) else ((result.error if result else "") or "")
        (cycle_dir / "llm-raw.txt").write_text(raw, encoding="utf-8")
        if result is None or not result.ok or not result.text.strip():
            self._last_llm_failure_transient = self._is_transient_llm_failure(result)
            return None
        self._last_llm_failure_transient = False
        proposal = self._parse_json_proposal(result.text)
        if proposal is not None:
            (cycle_dir / "proposal.json").write_text(
                json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")
        return proposal

    @staticmethod
    def _is_transient_llm_failure(result: Any) -> bool:
        """Distingue el fallo de infraestructura del de contenido."""
        if result is None:
            return True
        if getattr(result, "ok", False):
            return False
        error = str(getattr(result, "error", "") or "")
        return any(code in error for code in ("401", "403", "429", "500", "502", "503", "504", "timeout", "Timeout"))

    def _parse_json_proposal(self, text: str) -> dict[str, Any] | None:
        candidate = text.strip()
        # Quitar fences de código si el modelo los añadió.
        fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", candidate, re.DOTALL)
        if fence:
            candidate = fence.group(1)
        else:
            first = candidate.find("{")
            last = candidate.rfind("}")
            if first != -1 and last != -1 and last > first:
                candidate = candidate[first : last + 1]
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        if not str(data.get("original_block", "")).strip() or not str(data.get("improved_block", "")).strip():
            return None
        return data

    # ---------------------------------------------------------------- aplicación

    def _apply_proposal(self, text: str, proposal: dict[str, Any]) -> tuple[str | None, str]:
        original_block = str(proposal.get("original_block", ""))
        improved_block = str(proposal.get("improved_block", ""))
        kind = str(proposal.get("improvement_kind", ""))

        if not self._latex_balanced(improved_block):
            return None, kind

        # 1) Coincidencia exacta y única.
        if original_block in text:
            if text.count(original_block) != 1:
                return None, kind
            return text.replace(original_block, improved_block, 1), kind

        # 2) Coincidencia tolerante a espacios en blanco (colapsando runs de espacios
        #    y normalizando fin de línea) que resuelva a un ÚNICO span real del texto.
        span = self._find_flexible_span(text, original_block)
        if span is None:
            return None, kind
        start, end = span
        candidate = text[:start] + improved_block + text[end:]
        return candidate, kind

    def _find_flexible_span(self, text: str, block: str) -> tuple[int, int] | None:
        """Localiza un único span de ``text`` que coincide con ``block`` salvo por
        diferencias de espacios en blanco (espacios/tabs/saltos de línea colapsados).

        Devuelve (start, end) sobre el texto ORIGINAL, o None si no hay match único.
        """
        # Construir un patrón que trate cualquier run de whitespace como \s+.
        tokens = block.strip().split()
        if not tokens:
            return None
        pattern = r"\s+".join(re.escape(tok) for tok in tokens)
        matches = list(re.finditer(pattern, text))
        if len(matches) != 1:
            return None
        return matches[0].start(), matches[0].end()

    def _latex_balanced(self, block: str) -> bool:
        if block.count("{") != block.count("}"):
            return False
        begins = re.findall(r"\\begin\{([^}]+)\}", block)
        ends = re.findall(r"\\end\{([^}]+)\}", block)
        return sorted(begins) == sorted(ends)

    def _reject_reason(self, compile_ok: bool, contract_after: float, contract_before: float,
                       quality_after: float, quality_before: float, request: ActivityOptimizeRequest) -> str:
        if not compile_ok:
            return "La compilación falló tras aplicar la mejora; revertido."
        if request.require_contract_100 and contract_after < 100.0:
            return f"El contrato bajó a {contract_after}/100 tras la mejora; revertido."
        if contract_after < contract_before:
            return f"El contrato retrocedió ({contract_before}->{contract_after}); revertido."
        if quality_after <= quality_before:
            return f"La calidad no mejoró ({quality_before}->{quality_after}); revertido."
        return "Rechazado por criterio de aceptación."

    def _quality_verdict(
        self,
        request: ActivityOptimizeRequest,
        before_text: str,
        after_text: str,
        quality_before: float,
        quality_after: float,
        *,
        allow_tie: bool,
    ) -> PanelVerdict:
        """Decide si el candidato mejora la calidad.

        Sin panel se conserva la regla historica: comparar ``_quality_score``.
        Con panel, la decision es por mayoria entre heuristica, reward model y
        juez LLM (ver quality_panel.py).
        """
        if not request.use_quality_panel:
            improved = (quality_after >= quality_before if allow_tie
                        else quality_after > quality_before)
            from .quality_panel import JudgeVote  # local: evita coste si no se usa

            vote = JudgeVote("heuristic", improved, quality_before, quality_after)
            return PanelVerdict(improved, (vote,), "heuristica")

        if self._panel is None:
            self._panel = build_default_panel(
                self._quality_score,
                llm=self.llm,
                reward_model_dir=request.reward_model_dir or None,
                enable_llm_judge=request.panel_llm_judge,
            )
        return self._panel.evaluate(before_text, after_text, allow_tie=allow_tie)

    def _semantic_audit(
        self,
        request: ActivityOptimizeRequest,
        text: str,
        tex_path: Path,
        engine: str,
        output_path: Path,
    ) -> SemanticAuditResult:
        if not request.run_semantic_audit:
            return SemanticAuditResult(True, True, 0, 0)
        return self.semantic_auditor.audit(
            text,
            tex_path.parent,
            engine=engine,
            max_tokens=request.max_tokens,
            output_path=output_path,
            feedback_path=Path(request.semantic_feedback_path) if request.semantic_feedback_path else None,
        )

    def _semantic_gate_passed(
        self,
        request: ActivityOptimizeRequest,
        audit: SemanticAuditResult,
    ) -> bool:
        if not request.run_semantic_audit:
            return True
        if not audit.audit_available:
            return not request.semantic_fail_closed
        return not audit.blocking_findings

    def _semantic_candidate_acceptable(
        self,
        request: ActivityOptimizeRequest,
        before: SemanticAuditResult,
        after: SemanticAuditResult,
    ) -> bool:
        if not request.run_semantic_audit:
            return True
        if not after.audit_available:
            return not request.semantic_fail_closed
        before_count = len(before.blocking_findings)
        after_count = len(after.blocking_findings)
        if before_count:
            return after_count < before_count
        return after_count == 0

    def _semantic_guidance(self, audit: SemanticAuditResult) -> str:
        if not audit.audit_available:
            return f"AUDITORÍA NO DISPONIBLE: {audit.error}. No declares resuelto el contenido."
        if not audit.blocking_findings:
            return "Sin observaciones semánticas bloqueantes; no introduzcas afirmaciones nuevas sin respaldo."
        lines = []
        for index, finding in enumerate(audit.blocking_findings[:6], start=1):
            lines.append(
                f"{index}. [{finding.kind}] {finding.claim}\n"
                f"   Razón: {finding.explanation}\n"
                f"   Corrección sugerida: "
                f"{finding.suggested_fix or 'contrastar y corregir con los pasajes locales'}"
            )
        return "\n".join(lines)

    def _select_cycle_action(
        self,
        request: ActivityOptimizeRequest,
        engines: tuple[str, ...],
        cycle_index: int,
        quality_before: float,
        contract_before: float,
        semantic_blocking_before: int,
        quality_breakdown_before: dict[str, float] | None = None,
    ) -> PlannedAction:
        fallback_kind = "correccion-semantica" if semantic_blocking_before > 0 else ""
        fallback = PlannedAction(
            engine=engines[(cycle_index - 1) % len(engines)],
            improvement_kind=fallback_kind,
            source="round-robin",
        )
        policy = self._load_trained_policy(request)
        if policy is None:
            return fallback

        best: PlannedAction | None = None
        best_value = float("-inf")
        for engine in engines:
            for improvement_kind in self._policy_candidate_kinds(semantic_blocking_before):
                features = self._policy_feature_vector(
                    policy,
                    engine=engine,
                    improvement_kind=improvement_kind,
                    quality_before=quality_before,
                    contract_before=contract_before,
                    semantic_blocking_before=semantic_blocking_before,
                    cycle_index=cycle_index,
                    activity_number=int(request.activity_number),
                    quality_breakdown_before=quality_breakdown_before or {},
                )
                acceptance = self._predict_acceptance(policy, features)
                reward = self._predict_reward(policy, features)
                expected_value = acceptance * reward
                if expected_value > best_value:
                    best_value = expected_value
                    best = PlannedAction(
                        engine=engine,
                        improvement_kind=improvement_kind,
                        source="trained-policy",
                        expected_acceptance=acceptance,
                        expected_reward=reward,
                    )
        if best is None or best.expected_acceptance is None or best.expected_reward is None:
            return fallback
        if best.expected_acceptance <= 0.0 or best.expected_reward <= 0.0:
            return fallback
        return best

    def _policy_candidate_kinds(self, semantic_blocking_before: int) -> tuple[str, ...]:
        if semantic_blocking_before > 0:
            return ("correccion-semantica",)
        return POLICY_IMPROVEMENT_KINDS

    def _resolve_policy_model_dir(self, request: ActivityOptimizeRequest) -> Path:
        if request.policy_model_dir.strip():
            return self.workspace.resolve_target(request.policy_model_dir)
        return self.workspace.feedback_root / "training" / "models"

    def _load_trained_policy(self, request: ActivityOptimizeRequest) -> TrainedPolicyBundle | None:
        if not request.use_trained_policy:
            return None
        model_dir = self._resolve_policy_model_dir(request)
        cache_key = str(model_dir.resolve()) if model_dir.exists() else str(model_dir)
        if self._policy_cache is not None and self._policy_cache_key == cache_key:
            return self._policy_cache

        accept_path = model_dir / "accept_clf.joblib"
        reward_path = model_dir / "reward_reg.joblib"
        if not accept_path.exists() or not reward_path.exists():
            self._policy_cache = None
            self._policy_cache_key = cache_key
            self._policy_error = "modelos de política no encontrados"
            return None
        try:
            import joblib
        except Exception as exc:  # noqa: BLE001 - el fallback cubre entornos sin sklearn/joblib
            self._policy_cache = None
            self._policy_cache_key = cache_key
            self._policy_error = str(exc)
            return None

        try:
            accept_meta = joblib.load(accept_path)
            reward_meta = joblib.load(reward_path)
            bundle = TrainedPolicyBundle(
                accept_pipeline=accept_meta["pipeline"],
                reward_pipeline=reward_meta["pipeline"],
                numeric_features=tuple(accept_meta.get("numeric") or ()),
                categorical_features=tuple(accept_meta.get("categorical") or ()),
                model_dir=model_dir,
            )
        except Exception as exc:  # noqa: BLE001 - si la carga falla se vuelve al heurístico
            self._policy_cache = None
            self._policy_cache_key = cache_key
            self._policy_error = str(exc)
            return None

        self._policy_cache = bundle
        self._policy_cache_key = cache_key
        self._policy_error = ""
        return bundle

    def _policy_feature_vector(
        self,
        policy: TrainedPolicyBundle,
        *,
        engine: str,
        improvement_kind: str,
        quality_before: float,
        contract_before: float,
        semantic_blocking_before: int,
        cycle_index: int,
        activity_number: int,
        quality_breakdown_before: dict[str, float],
    ) -> Any:
        import numpy as np

        values: dict[str, Any] = {
            "quality_before": float(quality_before),
            "contract_before": float(contract_before),
            "semantic_blocking_before": int(semantic_blocking_before),
            "cycle": int(cycle_index),
            "activity_number": int(activity_number),
            "engine": engine,
            "improvement_kind": improvement_kind,
        }
        for component in QUALITY_COMPONENTS:
            values[f"quality_{component}_before"] = float(quality_breakdown_before.get(component, 0.0) or 0.0)
        row: list[Any] = []
        for name in policy.numeric_features:
            row.append(float(values.get(name, 0.0) or 0.0))
        for name in policy.categorical_features:
            row.append(str(values.get(name, "") or "(vacio)"))
        return np.asarray([row], dtype=object)

    def _predict_acceptance(self, policy: TrainedPolicyBundle, features: Any) -> float:
        try:
            proba = policy.accept_pipeline.predict_proba(features)
        except Exception:  # noqa: BLE001 - el fallback ya cubre errores en tiempo de ejecución
            return 0.0
        if getattr(proba, "ndim", 0) != 2 or proba.shape[1] < 2:
            return 0.0
        return float(proba[0][1])

    def _predict_reward(self, policy: TrainedPolicyBundle, features: Any) -> float:
        try:
            pred = policy.reward_pipeline.predict(features)
        except Exception:  # noqa: BLE001 - el fallback ya cubre errores en tiempo de ejecución
            return 0.0
        return float(pred[0]) if len(pred) else 0.0

    # ---------------------------------------------------------------- utilidades

    def _strip_comments(self, text: str) -> str:
        lines = [line for line in text.splitlines() if not line.lstrip().startswith("%")]
        return "\n".join(lines)

    def _normalize_ws(self, text: str) -> str:
        return re.sub(r"[ \t]+", " ", text)

    def _resolve_run_dir(self, request: ActivityOptimizeRequest, run_id: str) -> Path:
        if request.output.strip():
            return self.workspace.resolve_target(request.output) / run_id
        return self.root / run_id

    def _planned_action_summary(self, cycles: list[CycleRecord]) -> dict[str, Any]:
        total_cycles = len(cycles)
        policy_cycles = [c for c in cycles if c.planned_action_source == "trained-policy"]
        fallback_cycles = total_cycles - len(policy_cycles)
        aligned_engine = sum(1 for c in policy_cycles if (c.planned_engine or c.engine) == c.engine)
        aligned_kind = sum(
            1
            for c in policy_cycles
            if (c.planned_improvement_kind or "") == (c.improvement_kind or "")
        )
        aligned_action = sum(
            1
            for c in policy_cycles
            if (c.planned_engine or c.engine) == c.engine
            and (c.planned_improvement_kind or "") == (c.improvement_kind or "")
        )
        accepted_policy = sum(1 for c in policy_cycles if c.accepted)
        accepted_aligned = sum(
            1
            for c in policy_cycles
            if c.accepted
            and (c.planned_engine or c.engine) == c.engine
            and (c.planned_improvement_kind or "") == (c.improvement_kind or "")
        )
        accepted_misaligned = sum(
            1
            for c in policy_cycles
            if c.accepted
            and not (
                (c.planned_engine or c.engine) == c.engine
                and (c.planned_improvement_kind or "") == (c.improvement_kind or "")
            )
        )
        expected_values = [
            float(c.planned_expected_acceptance) * float(c.planned_expected_reward)
            for c in policy_cycles
            if c.planned_expected_acceptance is not None and c.planned_expected_reward is not None
        ]
        quality_deltas = [float(c.quality_after) - float(c.quality_before) for c in policy_cycles]
        return {
            "total_cycles": total_cycles,
            "policy_cycles": len(policy_cycles),
            "fallback_cycles": fallback_cycles,
            "policy_usage_rate": round(len(policy_cycles) / total_cycles, 4) if total_cycles else 0.0,
            "engine_alignment_rate": round(aligned_engine / len(policy_cycles), 4) if policy_cycles else 0.0,
            "kind_alignment_rate": round(aligned_kind / len(policy_cycles), 4) if policy_cycles else 0.0,
            "action_alignment_rate": round(aligned_action / len(policy_cycles), 4) if policy_cycles else 0.0,
            "accepted_policy_cycles": accepted_policy,
            "accepted_aligned_policy_cycles": accepted_aligned,
            "accepted_misaligned_policy_cycles": accepted_misaligned,
            "mean_expected_value": round(statistics.fmean(expected_values), 4) if expected_values else 0.0,
            "mean_policy_quality_delta": round(statistics.fmean(quality_deltas), 4) if quality_deltas else 0.0,
        }

    def _finalize(self, request: ActivityOptimizeRequest, run_id: str, run_dir: Path,
                  cycles: list[CycleRecord], quality_before: float, quality_after: float,
                  tex_path: Path | None, *, ok: bool, note: str = "",
                  contract_before: float = 0.0, contract_after: float = 0.0,
                  applied: int = 0,
                  initial_text: str = "",
                  final_text: str = "",
                  semantic_before: SemanticAuditResult | None = None,
                  semantic_after: SemanticAuditResult | None = None) -> ActivityOptimizeResult:
        semantic_before = semantic_before or SemanticAuditResult(True, True, 0, 0)
        semantic_after = semantic_after or semantic_before
        semantic_gate_passed = self._semantic_gate_passed(request, semantic_after)
        planned_action_summary = self._planned_action_summary(cycles)
        initial_snapshot_path: Path | None = None
        final_snapshot_path: Path | None = None
        if tex_path is not None:
            initial_snapshot_path = run_dir / "initial-state.tex"
            final_snapshot_path = run_dir / "final-state.tex"
            initial_snapshot_path.write_text(initial_text or final_text, encoding="utf-8")
            final_snapshot_path.write_text(final_text or initial_text, encoding="utf-8")
        manifest = {
            "run_id": run_id,
            "kind": "activity-optimize",
            "target": self.workspace.relative(self.workspace.resolve_target(request.target)),
            "activity_number": int(request.activity_number),
            "stop_mode": ("fixed-cycles" if int(request.cycles) > 0 else "converge-to-quality"),
            "requested_cycles": int(request.cycles),
            "target_quality": float(request.target_quality),
            "max_cycles": int(request.max_cycles),
            "converged": bool(quality_after >= float(request.target_quality) and semantic_gate_passed),
            "engines": list(request.engines),
            "trained_policy_requested": bool(request.use_trained_policy),
            "trained_policy_active": bool(self._load_trained_policy(request) is not None),
            "trained_policy_model_dir": self.workspace.relative(self._resolve_policy_model_dir(request)),
            "trained_policy_error": self._policy_error,
            "planned_action_summary": planned_action_summary,
            "ok": bool(ok),
            "note": note,
            "quality_before": quality_before,
            "quality_after": quality_after,
            "quality_delta": round(quality_after - quality_before, 2),
            "contract_before": contract_before,
            "contract_after": contract_after,
            "semantic_gate_passed": semantic_gate_passed,
            "semantic_audit_available": semantic_after.audit_available,
            "semantic_blocking_before": len(semantic_before.blocking_findings),
            "semantic_blocking_after": len(semantic_after.blocking_findings),
            "semantic_findings": [asdict(item) for item in semantic_after.findings],
            "applied_cycles": applied,
            "tex": self.workspace.relative(tex_path) if tex_path else "",
            "initial_tex_snapshot": self.workspace.relative(initial_snapshot_path) if initial_snapshot_path else "",
            "final_tex_snapshot": self.workspace.relative(final_snapshot_path) if final_snapshot_path else "",
            "cycles": [self._cycle_dict(c) for c in cycles],
        }
        manifest_path = run_dir / "manifest.json"
        report_path = run_dir / "reporte-optimize.md"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        report_path.write_text(self._render_report(manifest), encoding="utf-8")
        self.workspace.append_bitacora(run_id, "activity-optimize", manifest)
        return ActivityOptimizeResult(
            run_id=run_id, run_dir=run_dir, ok=bool(ok),
            manifest_path=manifest_path, report_path=report_path,
            applied_cycles=applied, quality_before=quality_before,
            quality_after=quality_after, tex_path=tex_path,
            initial_tex_snapshot_path=initial_snapshot_path,
            final_tex_snapshot_path=final_snapshot_path,
            semantic_blocking_before=len(semantic_before.blocking_findings),
            semantic_blocking_after=len(semantic_after.blocking_findings),
            semantic_audit_available=semantic_after.audit_available,
        )

    def _cycle_dict(self, c: CycleRecord) -> dict[str, Any]:
        payload = {
            "cycle": c.index,
            "engine": c.engine,
            "accepted": c.accepted,
            "reason": c.reason,
            "improvement_kind": c.improvement_kind,
            "planned_engine": c.planned_engine or c.engine,
            "planned_improvement_kind": c.planned_improvement_kind,
            "planned_action_source": c.planned_action_source,
            "quality_before": c.quality_before,
            "quality_after": c.quality_after,
            "contract_before": c.contract_before,
            "contract_after": c.contract_after,
            "semantic_blocking_before": c.semantic_blocking_before,
            "semantic_blocking_after": c.semantic_blocking_after,
            "quality_breakdown_before": c.quality_breakdown_before,
            "quality_breakdown_after": c.quality_breakdown_after,
        }
        if c.planned_expected_acceptance is not None:
            payload["planned_expected_acceptance"] = round(float(c.planned_expected_acceptance), 4)
        if c.planned_expected_reward is not None:
            payload["planned_expected_reward"] = round(float(c.planned_expected_reward), 4)
            acceptance = c.planned_expected_acceptance or 0.0
            payload["planned_expected_value"] = round(float(acceptance) * float(c.planned_expected_reward), 4)
        if c.panel_verdict is not None:
            payload["panel_verdict"] = c.panel_verdict
        return payload

    def _render_report(self, manifest: dict[str, Any]) -> str:
        lines = [
            "# Optimización de calidad de actividad",
            "",
            f"- Objetivo: {manifest['target']}",
            f"- Actividad: {manifest['activity_number']}",
            f"- Ciclos solicitados: {manifest['requested_cycles']}",
            f"- Ciclos aplicados (aceptados): {manifest['applied_cycles']}",
            f"- Calidad antes: {manifest['quality_before']}/100",
            f"- Calidad después: {manifest['quality_after']}/100 (Δ {manifest['quality_delta']})",
            f"- Contrato: {manifest['contract_before']} → {manifest['contract_after']} /100",
            f"- Auditoría semántica: {'DISPONIBLE' if manifest['semantic_audit_available'] else 'NO DISPONIBLE'}; "
            f"bloqueos {manifest['semantic_blocking_before']} → {manifest['semantic_blocking_after']}",
            f"- Puerta semántica: {'APROBADA' if manifest['semantic_gate_passed'] else 'BLOQUEADA'}",
            f"- Estado: {'OK' if manifest['ok'] else 'SIN CAMBIOS/REVISAR'}",
            "",
        ]
        if manifest.get("note"):
            lines.extend([f"> {manifest['note']}", ""])
        summary = manifest.get("planned_action_summary") or {}
        if summary:
            lines.extend([
                "## Resumen de planificación",
                "",
                f"- Ciclos totales: {summary.get('total_cycles', 0)}",
                f"- Ciclos con política entrenada: {summary.get('policy_cycles', 0)} "
                f"({summary.get('policy_usage_rate', 0.0):.1%})",
                f"- Ciclos en fallback heurístico: {summary.get('fallback_cycles', 0)}",
            ])
            if summary.get("policy_cycles", 0):
                lines.extend([
                    f"- Alineación de motor: {summary.get('engine_alignment_rate', 0.0):.1%}",
                    f"- Alineación de tipo de mejora: {summary.get('kind_alignment_rate', 0.0):.1%}",
                    f"- Alineación completa de acción: {summary.get('action_alignment_rate', 0.0):.1%}",
                    f"- Ciclos aceptados alineados: {summary.get('accepted_aligned_policy_cycles', 0)}",
                    f"- Ciclos aceptados desalineados: {summary.get('accepted_misaligned_policy_cycles', 0)}",
                    f"- Valor esperado medio de la política: {summary.get('mean_expected_value', 0.0)}",
                    f"- Δ calidad medio en ciclos de política: {summary.get('mean_policy_quality_delta', 0.0):+.2f}",
                    "",
                ])
            else:
                lines.append("")
        lines.extend(["## Ciclos", ""])
        for c in manifest.get("cycles", []):
            mark = "✅" if c["accepted"] else "⏭️"
            plan = (
                f"plan={c.get('planned_engine')}/{c.get('planned_improvement_kind') or 'n/a'}"
                f" via {c.get('planned_action_source') or 'n/a'}"
            )
            if c.get("planned_expected_value") is not None:
                plan += (
                    f" (p={c.get('planned_expected_acceptance')}, "
                    f"r={c.get('planned_expected_reward')}, v={c.get('planned_expected_value')})"
                )
            actual = f"real={c['engine']}/{c.get('improvement_kind') or 'n/a'}"
            lines.append(
                f"- {mark} Ciclo {c['cycle']} ({c['engine']}) "
                f"[{c.get('improvement_kind') or 'n/a'}]: "
                f"calidad {c['quality_before']}→{c['quality_after']}, "
                f"contrato {c['contract_before']}→{c['contract_after']}. "
                f"{plan}; {actual}. {c['reason']}"
            )
        if manifest.get("semantic_findings"):
            lines.extend(["", "## Observaciones semánticas", ""])
            for finding in manifest["semantic_findings"]:
                lines.append(
                    f"- **{finding['severity']} / {finding['kind']}**: "
                    f"{finding['claim']} — {finding['explanation']}"
                )
        lines.append("")
        return "\n".join(lines)
