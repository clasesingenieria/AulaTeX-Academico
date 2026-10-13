from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .activity_contract import evaluate_activity_contract
from .compilation_diagnostics import classify_compile_failure, is_environment_issue
from .editorial_memory import EditorialMemoryStore
from .extractor_adapter import CORE_EXTRACTOR_ARTIFACTS, ExtractorAdapter, ExtractorRequest
from .workspace import AulaTeXWorkspace, EditorialScope


# Medido sobre los PDF del repo: el pie izquierdo arranca en x=72pt y el bloque
# derecho en x=395.2pt, así que hay 323pt. En \small itálica cada carácter ocupa
# ~4.53pt (Garantías A4: 70 chars -> x1=388.8). El tope real son 71 caracteres;
# se usa 68 como margen para acentos y mayúsculas, más anchas que el promedio.
FOOTER_METADATA_MAX_CHARS = 68
# Por debajo de esto el pie queda pobre y desaprovecha el ancho disponible.
FOOTER_METADATA_MIN_CHARS = 28

_RE_DOC_TITLE = re.compile(r"(?m)^\s*\\def\\documenttitle\s*\{(.*)\}\s*$")
_RE_DOC_SUBTITLE = re.compile(r"(?m)^\s*\\def\\documentsubtitle\s*\{(.*)\}\s*$")


def footer_metadata_text(tex: str) -> str:
    """Devuelve el texto visible que la plantilla lleva al pie de página.

    La plantilla usa \\documentsubtitle y, solo si está vacío, \\documenttitle.
    """
    subtitle = _RE_DOC_SUBTITLE.search(tex)
    title = _RE_DOC_TITLE.search(tex)
    candidato = (subtitle.group(1).strip() if subtitle else "") or (
        title.group(1).strip() if title else ""
    )
    # El marcado LaTeX no ocupa ancho en la página.
    return re.sub(r"\\[a-zA-Z]+\s*|[{}]", "", candidato).strip()


def _footer_metadata_overflow(tex: str) -> bool:
    """True si el texto del pie excede el ancho disponible y se solapa."""
    return len(footer_metadata_text(tex)) > FOOTER_METADATA_MAX_CHARS


def _footer_metadata_too_short(tex: str) -> bool:
    """True si el pie es tan breve que desaprovecha el ancho disponible."""
    visible = footer_metadata_text(tex)
    return bool(visible) and len(visible) < FOOTER_METADATA_MIN_CHARS


@dataclass(frozen=True)
class ActivityObservationRequest:
    target: str
    activity_number: int = 1
    output: str = ""
    compile_check: bool = False


@dataclass(frozen=True)
class ActivityObservationResult:
    run_id: str
    run_dir: Path
    ok: bool
    state_path: Path
    evaluation_path: Path
    actions_path: Path


class ActivityObserver:
    def __init__(self, workspace: AulaTeXWorkspace | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.memory_store = EditorialMemoryStore(self.workspace)
        self.extractor = ExtractorAdapter(self.workspace)
        self.root = self.workspace.feedback_root / "activity-observer" / "runs"
        self.root.mkdir(parents=True, exist_ok=True)

    def observe(self, request: ActivityObservationRequest) -> ActivityObservationResult:
        run_id = f"{self.workspace.timestamp()}-activity-{int(request.activity_number):02d}-observer"
        run_dir = self._resolve_run_dir(request, run_id)
        # timestamp() tiene resolución de segundos; en flujos anidados (monitor ->
        # compilation-repair -> observe) varios observes caen en el mismo segundo y
        # colisionan de directorio, provocando FileNotFoundError al leer artefactos
        # de un run pisado por otro. Garantizar unicidad con sufijo incremental,
        # tanto con output implícito como explícito.
        if run_dir.exists() and any(run_dir.iterdir()):
            suffix = 1
            base_run_id = run_id
            while run_dir.exists() and any(run_dir.iterdir()):
                run_id = f"{base_run_id}-{suffix:02d}"
                run_dir = self._resolve_run_dir(request, run_id)
                suffix += 1
        run_dir.mkdir(parents=True, exist_ok=True)

        scope = self.workspace.find_scope_for_target(request.target, activity_number=request.activity_number)
        target_root = self.workspace.resolve_target(scope.relative_path if scope is not None else request.target)
        tex_path = self._find_activity_tex(target_root, request.activity_number)
        pdf_path = tex_path.with_suffix(".pdf") if tex_path is not None else None
        bib_path = self._find_canonical_bib(target_root)
        clean_bib_path = target_root / f"{target_root.name.removesuffix('-lde')}-clean.bib"
        if not clean_bib_path.exists():
            clean_bib_path = target_root / "filosofia-del-derecho-clean.bib"

        tex_text = self._read_text(tex_path)
        active_tex = self._strip_tex_comments(tex_text)
        bib_text = self._read_text(bib_path)
        bib_keys = self._extract_bib_keys(bib_text)
        cited_keys = self._extract_cite_keys(active_tex)
        missing_keys = sorted(key for key in cited_keys if key not in bib_keys)
        placeholder_hits = self._find_placeholders(active_tex)
        sections = self._extract_sections(active_tex)
        extractor_state = self._observe_extractor(target_root, request.activity_number)
        compile_result = self._compile_if_requested(tex_path, request.compile_check)
        # Cargar summary/concepts desde la MISMA carpeta que resolvió el observer
        # (subcarpeta por actividad 'conceptos-<materia>-actividad-N' del contrato).
        extractor_dir = next(
            (c for c in self._extractor_activity_candidates(target_root, request.activity_number) if c.exists()),
            target_root / "extractor-aulatex",
        )
        extractor_summary = self._load_json(extractor_dir / CORE_EXTRACTOR_ARTIFACTS["planeacion"])
        extractor_concepts = self._load_json(extractor_dir / CORE_EXTRACTOR_ARTIFACTS["conceptos"])
        editing_details = self._load_editing_details(scope)

        state = self._build_state(
            run_id=run_id,
            scope=scope,
            request=request,
            target_root=target_root,
            tex_path=tex_path,
            pdf_path=pdf_path,
            bib_path=bib_path,
            clean_bib_path=clean_bib_path if clean_bib_path.exists() else None,
            cited_keys=cited_keys,
            missing_keys=missing_keys,
            placeholder_hits=placeholder_hits,
            sections=sections,
            extractor_state=extractor_state,
            extractor_summary=extractor_summary,
            extractor_concepts=extractor_concepts,
            editing_details=editing_details,
            active_tex=active_tex,
            compile_result=compile_result,
        )
        evaluation = self._build_evaluation(state)
        state["next_action"] = evaluation["next_action"]
        actions = self._build_actions_markdown(state, evaluation)

        state_path = run_dir / "estado-agente.json"
        evaluation_path = run_dir / "evaluacion.json"
        actions_path = run_dir / "acciones-recomendadas.md"
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        evaluation_path.write_text(json.dumps(evaluation, ensure_ascii=False, indent=2), encoding="utf-8")
        actions_path.write_text(actions, encoding="utf-8")

        manifest = {
            "run_id": run_id,
            "kind": "activity-observer",
            "target": self.workspace.relative(target_root),
            "activity_number": int(request.activity_number),
            "ok": bool(evaluation["passed"]),
            "state": self.workspace.relative(state_path),
            "evaluation": self.workspace.relative(evaluation_path),
            "actions": self.workspace.relative(actions_path),
        }
        (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        self.workspace.append_bitacora(run_id, "activity-observer", manifest)
        return ActivityObservationResult(run_id, run_dir, bool(evaluation["passed"]), state_path, evaluation_path, actions_path)

    def _resolve_run_dir(self, request: ActivityObservationRequest, run_id: str) -> Path:
        if request.output.strip():
            return self.workspace.resolve_target(request.output) / run_id
        return self.root / run_id

    def _find_activity_tex(self, target_root: Path, activity_number: int) -> Path | None:
        if target_root.is_file() and target_root.suffix.lower() == ".tex":
            return target_root
        if not target_root.exists() or not target_root.is_dir():
            return None
        patterns = [
            f"*Actividad-{int(activity_number)}.tex",
            f"*Actividad_{int(activity_number)}.tex",
            f"*actividad-{int(activity_number)}.tex",
            f"*actividad_{int(activity_number)}.tex",
        ]
        for pattern in patterns:
            matches = sorted(
                (path for path in target_root.glob(pattern) if path.is_file()),
                key=lambda path: (not path.name.lower().startswith("reporte-"), path.name.lower()),
            )
            if matches:
                return matches[0]
        activity_re = re.compile(rf"actividad[-_\s]*0?{int(activity_number)}", re.IGNORECASE)
        for path in sorted(target_root.glob("*.tex")):
            if activity_re.search(path.stem):
                return path
        return None

    def _find_canonical_bib(self, target_root: Path) -> Path | None:
        if not target_root.exists():
            return None
        if target_root.is_file():
            target_root = target_root.parent
        direct = sorted(path for path in target_root.glob("*.bib") if path.is_file() and "clean" not in path.stem.lower())
        if direct:
            # MGA, como LDE, conserva el sufijo del programa en la carpeta,
            # pero no en la bibliografía disciplinar. No elegir una auxiliar
            # por orden alfabético cuando existe el nombre canónico.
            preferred_stems = (
                target_root.name,
                target_root.name.removesuffix("-lde"),
                target_root.name.removesuffix("-mga"),
            )
            for stem in preferred_stems:
                preferred = next((path for path in direct if path.stem == stem), None)
                if preferred is not None:
                    return preferred
            return direct[0]
        return None

    def _extractor_activity_candidates(self, target_root: Path, activity_number: int) -> list[Path]:
        """Carpetas candidatas de la base conceptual del extractor, en orden de prioridad.

        Prioriza la subcarpeta por actividad 'conceptos-<materia>-actividad-N'
        (contrato vigente), luego variantes legacy y la raíz de extractor-aulatex.
        """
        base = target_root / "extractor-aulatex"
        candidates: list[Path] = []
        act = int(activity_number)
        if act > 0 and base.is_dir():
            # 'conceptos-*-actividad-N' o 'conceptos-*-sN' (patrón del contrato).
            act_pat = re.compile(rf"conceptos-.*-(?:actividad-0?{act}|s0?{act})\b", re.IGNORECASE)
            for cand in sorted(base.glob("conceptos-*")):
                if cand.is_dir() and act_pat.search(cand.name):
                    candidates.append(cand)
        if act > 0:
            candidates.append(base / f"actividad-{act:02d}")
        candidates.append(base)
        return candidates

    def _observe_extractor(self, target_root: Path, activity_number: int) -> dict[str, Any]:
        candidates = self._extractor_activity_candidates(target_root, activity_number)
        for candidate in candidates:
            if candidate.exists():
                artifacts = {
                    name: {
                        "present": (candidate / filename).exists(),
                        "path": self.workspace.relative(candidate / filename),
                    }
                    for name, filename in CORE_EXTRACTOR_ARTIFACTS.items()
                }
                return {
                    "ready": all(item["present"] for item in artifacts.values()),
                    "output_dir": self.workspace.relative(candidate),
                    "artifacts": artifacts,
                    "missing_artifacts": [name for name, item in artifacts.items() if not item["present"]],
                }
        preview = self.extractor.preview_markdown(ExtractorRequest(target=str(target_root), activity_number=activity_number))
        return {
            "ready": False,
            "output_dir": "",
            "artifacts": {},
            "missing_artifacts": list(CORE_EXTRACTOR_ARTIFACTS.keys()),
            "preview": preview,
        }

    def _compile_if_requested(self, tex_path: Path | None, enabled: bool) -> dict[str, Any]:
        if not enabled:
            return {"enabled": False, "ok": None, "returncode": None}
        if tex_path is None:
            return {"enabled": True, "ok": False, "returncode": None, "error": "No se encontró TEX de actividad.", "category": "missing-tex"}
        result = self.workspace.compile_tex(tex_path, clean_mode="safe")
        combined = f"{result.stdout}\n{result.stderr}"
        category = classify_compile_failure(combined) if not result.ok else "ok"
        return {
            "enabled": True,
            "ok": result.ok,
            "returncode": result.returncode,
            "category": category,
            "environment_issue": bool(not result.ok and is_environment_issue(category)),
            "stdout_tail": result.stdout[-3000:],
            "stderr_tail": result.stderr[-3000:],
        }

    def _build_state(
        self,
        *,
        run_id: str,
        scope: EditorialScope | None,
        request: ActivityObservationRequest,
        target_root: Path,
        tex_path: Path | None,
        pdf_path: Path | None,
        bib_path: Path | None,
        clean_bib_path: Path | None,
        cited_keys: list[str],
        missing_keys: list[str],
        placeholder_hits: list[str],
        sections: list[str],
        extractor_state: dict[str, Any],
        extractor_summary: dict[str, Any] | list[Any] | None,
        extractor_concepts: dict[str, Any] | list[Any] | None,
        editing_details: dict[str, Any],
        active_tex: str,
        compile_result: dict[str, Any],
    ) -> dict[str, Any]:
        bibliography_ready = bool(bib_path and bib_path.exists() and not missing_keys)
        draft_ready = bool(tex_path and tex_path.exists() and not placeholder_hits)
        if not compile_result.get("enabled"):
            compile_ready = "unknown"
        elif compile_result.get("ok"):
            compile_ready = True
        elif compile_result.get("environment_issue"):
            compile_ready = "environment-blocked"
        else:
            compile_ready = False
        next_action = self._next_action(bibliography_ready, draft_ready, extractor_state, compile_ready, missing_keys, placeholder_hits)
        return {
            "schema_version": 1,
            "run_id": run_id,
            "agent_mode": "activity-observer",
            "scope_key": scope.key if scope is not None else "",
            "activity_number": int(request.activity_number),
            "target_root": self.workspace.relative(target_root),
            "target_tex": self.workspace.relative(tex_path) if tex_path else "",
            "target_pdf": self.workspace.relative(pdf_path) if pdf_path and pdf_path.exists() else "",
            "bib_ref": self.workspace.relative(bib_path) if bib_path else "",
            "clean_bib_ref": self.workspace.relative(clean_bib_path) if clean_bib_path else "",
            "observed_state": {
                "memory_ready": bool(scope),
                "detail_planner_ready": bool(editing_details),
                "planeacion_ready": "unknown",
                "extractor_ready": bool(extractor_state.get("ready")),
                "bibliography_ready": bibliography_ready,
                "draft_ready": draft_ready,
                "compile_ready": compile_ready,
                "evaluation_ready": True,
            },
            "editing_details": editing_details,
            "signals": {
                "sections": sections,
                "sections_count": len(sections),
                "cited_keys": cited_keys,
                "cited_keys_count": len(cited_keys),
                "missing_bib_keys": missing_keys,
                "placeholder_hits": placeholder_hits,
                "objective_present": bool(re.search(r"\\textbf\{Objetivo:\}|\\section\{Objetivo", active_tex, re.IGNORECASE)),
                "purpose_present": bool(re.search(r"\\textbf\{Prop[óo]sito:\}|prop[óo]sito", active_tex, re.IGNORECASE)),
                "conclusion_present": bool(sections and any("conclus" in section.lower() for section in sections)) or bool(re.search(r"en conclusi[óo]n", active_tex, re.IGNORECASE)),
                # Encabezados: el \documenttitle NO debe incluir 'Actividad #'; debe ser temático.
                "title_generic_activity": bool(
                    re.search(
                        r"\\def\\documenttitle\s*\{[^}]*[Aa]ctividad\s*\d+",
                        active_tex,
                    )
                    or re.search(
                        r"\\(?:re)?newcommand\{\\documenttitle\}\s*\{[^}]*[Aa]ctividad\s*\d+",
                        active_tex,
                    )
                ),
                # La sección de desarrollo NO debe titularse literalmente 'Desarrollo'.
                "development_section_literal": bool(
                    re.search(r"\\section\*?\{\s*Desarrollo\s*\}", active_tex, re.IGNORECASE)
                ),
                # El pie compone subtítulo (izq) y curso (der) en la misma línea:
                # muy largo se solapan, muy corto desaprovecha el ancho.
                "footer_metadata_overflow": _footer_metadata_overflow(active_tex),
                "footer_metadata_too_short": _footer_metadata_too_short(active_tex),
                "footer_metadata_length": len(footer_metadata_text(active_tex)),
                # Postura/análisis propio: primera persona académica en la conclusión.
                "personal_stance_present": bool(
                    re.search(
                        r"\b(considero|mi (an[áa]lisis|lectura|postura|juicio)|desde mi|sostengo|a mi juicio|en mi opini[óo]n|defiendo|concluyo que)\b",
                        active_tex,
                        re.IGNORECASE,
                    )
                ),
                # El análisis propio y la postura personal deben integrarse ORGÁNICAMENTE
                # en la conclusión (prosa), NO figurar como \section/\subsection propia.
                "stance_as_separate_section": bool(
                    re.search(
                        r"\\(?:sub)?section\*?\{[^}]*(an[áa]lisis\s+propio|postura\s+personal|valoraci[óo]n\s+(?:cr[íi]tica|personal)|reflexi[óo]n\s+(?:propia|personal)|apreciaci[óo]n\s+personal|opini[óo]n\s+personal)",
                        active_tex,
                        re.IGNORECASE,
                    )
                ),
                # Opciones de cuestionario visibles (a) b) c) d) en el cuerpo): deben ir
                # comentadas o en tabla; su presencia como lista suelta es señal de ruido.
                "questionnaire_options_visible": bool(
                    re.search(r"Opciones:\s*[a-d][.)]", active_tex, re.IGNORECASE)
                ),
                "ai_declaration_present": bool(re.search(r"inteligencia artificial|uso de\s+ia\b|herramienta[s]?\s+de\s+ia\b", active_tex, re.IGNORECASE)),
                "ai_declaration_as_footnote": bool(
                    re.search(
                        r"\\footnote\{[^}]*(inteligencia artificial|uso de\s+ia\b|herramienta[s]?\s+de\s+ia\b)",
                        active_tex,
                        re.IGNORECASE | re.DOTALL,
                    )
                ),
                "ai_declaration_as_section": bool(
                    re.search(
                        r"\\section\*?\{[^}]*(declaraci[óo]n[^}]*inteligencia artificial|uso[^}]*inteligencia artificial|declaraci[óo]n[^}]*\bia\b)",
                        active_tex,
                        re.IGNORECASE,
                    )
                ),
                "product_visual_detected": bool(re.search(r"tikzpicture|\\begin\{figure\}|mapa conceptual|cuadro|tabla|diagrama", active_tex, re.IGNORECASE)),
                "metadiscourse_hits": self._find_metadiscourse(active_tex),
                "evaluation_criteria_present": bool(re.search(r"criterios|r[úu]brica|evaluaci[óo]n", active_tex, re.IGNORECASE)),
                "questionnaire_detected": bool(re.search(r"cuestionario|reactivo|pregunta\s*\d+", active_tex, re.IGNORECASE)),
                "questionnaire_contract_satisfied": bool(
                    re.search(r"cuestionario", active_tex, re.IGNORECASE)
                    and re.search(r"pregunta", active_tex, re.IGNORECASE)
                    and re.search(r"respuesta", active_tex, re.IGNORECASE)
                    and re.search(r"justificaci[óo]n", active_tex, re.IGNORECASE)
                ),
                "table_contract_satisfied": bool(
                    re.search(r"\\begin\{longtable\}|\\begin\{tabular\}", active_tex, re.IGNORECASE)
                    and re.search(r"\\toprule|\\midrule|\\hline", active_tex, re.IGNORECASE)
                    and re.search(r"\\caption\{|\\textbf\{.*?\}", active_tex, re.IGNORECASE)
                ),
                "case_study_detected": bool(re.search(r"estudio de caso|an[áa]lisis del caso|hechos", active_tex, re.IGNORECASE)),
                "didactic_technique_present": bool(re.search(r"mapa conceptual|estudio de caso|cuadro comparativo|diagrama|tabla|cuestionario|foro diagn[óo]stico|longtable|tabular", active_tex, re.IGNORECASE)),
                "extractor_planeacion_present": bool(isinstance(extractor_summary, dict) and extractor_summary),
                "extractor_objective_present": bool(isinstance(extractor_summary, dict) and str(extractor_summary.get("objetivo", "")).strip()),
                "extractor_criteria_count": len(extractor_summary.get("criterios_entrega", [])) if isinstance(extractor_summary, dict) and isinstance(extractor_summary.get("criterios_entrega", []), list) else 0,
                "extractor_verbs_count": len(extractor_summary.get("verbos_operativos", [])) if isinstance(extractor_summary, dict) and isinstance(extractor_summary.get("verbos_operativos", []), list) else 0,
                "extractor_concepts_count": len(extractor_concepts) if isinstance(extractor_concepts, list) else 0,
                # Señales de FALLBACK derivadas del propio TEX, usadas cuando no existe
                # planeación oficial (materias sin extractor-aulatex). Permiten que el
                # contrato sea efectivo sin depender exclusivamente de la planeación.
                "document_concepts_count": self._count_document_concepts(active_tex),
                "document_purpose_present": bool(
                    re.search(
                        r"\\section\{[^}]*(marco conceptual|marco te[óo]rico|conceptos (fundamentales|introductorios|clave)|fundamentos)",
                        active_tex,
                        re.IGNORECASE,
                    )
                    or re.search(r"\\textbf\{Prop[óo]sito:\}|este (documento|cuestionario|trabajo) (aborda|analiza|examina|presenta)", active_tex, re.IGNORECASE)
                ),
                "extractor": extractor_state,
                "compile": compile_result,
            },
            "next_action": next_action,
        }

    def _build_evaluation(self, state: dict[str, Any]) -> dict[str, Any]:
        observed = state["observed_state"]
        signals = state["signals"]
        checks = {
            "tex_exists": bool(state.get("target_tex")),
            "pdf_exists": bool(state.get("target_pdf")),
            "detail_planner_ready": bool(observed.get("detail_planner_ready")),
            "bibliography_ready": bool(observed.get("bibliography_ready")),
            "extractor_ready": bool(observed.get("extractor_ready")),
            "draft_without_placeholders": bool(observed.get("draft_ready")),
            "sections_minimum": int(signals.get("sections_count", 0)) >= 3,
            "compile_ready": observed.get("compile_ready") in {True, "unknown", "environment-blocked"},
        }
        critical = []
        warnings = []
        if not checks["tex_exists"]:
            critical.append("No se encontró TEX de actividad.")
        if not checks["detail_planner_ready"]:
            warnings.append("No existen editing_details persistidos para el nodo.")
        if not checks["bibliography_ready"]:
            critical.append("Hay claves bibliográficas faltantes o no hay .bib canónico.")
        if not checks["extractor_ready"]:
            critical.append("No existe salida verificable del extractor para esta actividad.")
        if not checks["draft_without_placeholders"]:
            critical.append("Hay placeholders o pendientes activos.")
        if observed.get("compile_ready") is False:
            critical.append("La compilación falló.")
        elif observed.get("compile_ready") == "environment-blocked":
            warnings.append("La compilación no pudo verificarse por una dependencia faltante del entorno TeX; no se penaliza el score editorial.")
        contract = evaluate_activity_contract(state)
        next_action = state["next_action"]
        if next_action == "finalize" and not contract["passed"]:
            next_action = "revise-activity"
            critical.extend(item for item in contract["findings"] if item not in critical)
        if next_action != "finalize":
            critical.append(f"El ciclo aún no puede cerrarse: siguiente acción requerida `{next_action}`.")
        basic_score = round(100 * sum(1 for ok in checks.values() if ok) / max(1, len(checks)), 2)
        score = round((basic_score * 0.55) + (contract["score"] * 0.45), 2)
        return {
            "passed": next_action == "finalize" and not critical and basic_score >= 85 and contract["passed"],
            "score": score,
            "basic_score": basic_score,
            "checks": checks,
            "critical_findings": critical,
            "warnings": warnings,
            "next_action": next_action,
            "contract": contract,
        }

    def _load_editing_details(self, scope: EditorialScope | None) -> dict[str, Any]:
        if scope is None:
            return {}
        memory = self.memory_store.get_memory(scope.key)
        return dict((memory.get("node_metadata") or {}).get("editing_details") or {})

    def _build_actions_markdown(self, state: dict[str, Any], evaluation: dict[str, Any]) -> str:
        lines = [
            "# Acciones recomendadas",
            "",
            f"- Actividad: {state['activity_number']}",
            f"- Scope: `{state.get('scope_key', '')}`",
            f"- TEX: `{state.get('target_tex', '')}`",
            f"- Score: {evaluation['score']}",
            f"- Siguiente acción: `{evaluation['next_action']}`",
            "",
            "## Hallazgos críticos",
            "",
        ]
        if evaluation["critical_findings"]:
            lines.extend(f"- {item}" for item in evaluation["critical_findings"])
        else:
            lines.append("- No hay hallazgos críticos.")
        warnings = evaluation.get("warnings") or []
        if warnings:
            lines.extend(["", "## Advertencias", ""])
            lines.extend(f"- {item}" for item in warnings)
        missing = state["signals"].get("missing_bib_keys", [])
        if missing:
            lines.extend(["", "## Claves bibliográficas faltantes", ""])
            lines.extend(f"- `{key}`" for key in missing)
            lines.extend([
                "",
                "Acción sugerida: buscar equivalentes en el `.bib` canónico antes de reescribir contenido.",
            ])
        placeholders = state["signals"].get("placeholder_hits", [])
        if placeholders:
            lines.extend(["", "## Pendientes detectados", ""])
            lines.extend(f"- `{item}`" for item in placeholders[:20])
        extractor = state["signals"].get("extractor", {})
        if not extractor.get("ready"):
            lines.extend(["", "## Extractor", ""])
            lines.append("- No hay salida completa del extractor para esta actividad.")
            if extractor.get("missing_artifacts"):
                lines.append("- Faltantes: " + ", ".join(extractor["missing_artifacts"]))
        lines.append("")
        return "\n".join(lines)

    def _next_action(
        self,
        bibliography_ready: bool,
        draft_ready: bool,
        extractor_state: dict[str, Any],
        compile_ready: bool | str,
        missing_keys: list[str],
        placeholder_hits: list[str],
    ) -> str:
        if missing_keys or not bibliography_ready:
            return "repair-bibliography"
        if compile_ready is False:
            return "repair-compilation"
        if not extractor_state.get("ready"):
            return "run-extractor"
        if placeholder_hits or not draft_ready:
            return "revise-activity"
        return "finalize"

    def _read_text(self, path: Path | None) -> str:
        if path is None or not path.exists() or not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    def _load_json(self, path: Path | None) -> dict[str, Any] | list[Any] | None:
        if path is None or not path.exists() or not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError:
            return None

    def _strip_tex_comments(self, text: str) -> str:
        lines = []
        for line in text.splitlines():
            if line.lstrip().startswith("%"):
                continue
            lines.append(line)
        return "\n".join(lines)

    def _extract_cite_keys(self, text: str) -> list[str]:
        keys: list[str] = []
        pattern = re.compile(r"\\cite[t|p]?\*?(?:\[[^\]]*\])*\{([^}]+)\}")
        for match in pattern.finditer(text):
            keys.extend(key.strip() for key in match.group(1).split(",") if key.strip())
        return sorted(set(keys))

    def _extract_bib_keys(self, text: str) -> set[str]:
        return {match.group(1).strip() for match in re.finditer(r"@\w+\s*\{\s*([^,\s]+)", text)}

    def _find_placeholders(self, text: str) -> list[str]:
        hits = []
        case_insensitive_patterns = (r"\\pendiente\{[^}]*\}", r"\bPENDIENTE\b", r"Actividad X", r"Semana X")
        for pattern in case_insensitive_patterns:
            hits.extend(match.group(0) for match in re.finditer(pattern, text, re.IGNORECASE))
        for pattern in (r"\bTODO\b", r"\bFIXME\b"):
            hits.extend(match.group(0) for match in re.finditer(pattern, text))
        return sorted(set(hits))

    def _find_metadiscourse(self, text: str) -> list[str]:
        """Detecta metadiscurso de ejecución visible que el contrato prohíbe.

        Incluye residuos del flujo antiguo (Refuerzo editorial Ciclo A), menciones
        de 'la actividad N' / 'esta actividad' / 'el producto solicitado' como narrador
        externo, Y metadiscurso sobre la REALIZACIÓN de la actividad que debe ir
        comentado (secciones 'Nivel cognitivo aplicado', 'Técnica didáctica aplicada',
        'Producto solicitado', frases que narran cómo se presenta/aplica el producto en
        lugar de hablar del TEMA). No penaliza texto dentro de comentarios TEX (ya
        removidos por _strip_tex_comments antes de invocar este método).
        """
        hits: list[str] = []
        patterns = (
            # Residuos del flujo antiguo.
            r"Refuerzo editorial",
            r"Ciclo A\b",
            r"\\section\*?\{[^}]*[Rr]efuerzo",
            r"\\subsection\*?\{[^}]*[Rr]efuerzo",
            # Narrador externo sobre la actividad.
            r"\bLa Actividad\s+\d+",
            r"\bEsta actividad\b",
            r"\besta actividad\b",
            r"el producto solicitado",
            r"la t[ée]cnica usada",
            # Secciones de METADISCURSO sobre la realización (deben ir comentadas o
            # integradas en prosa en la conclusión, no como sección/lista visible).
            r"\\subsection\*?\{[^}]*[Nn]ivel cognitivo",
            r"\\subsection\*?\{[^}]*[Tt][ée]cnica did[áa]ctica",
            r"\\subsection\*?\{[^}]*[Pp]roducto solicitado",
            r"\\subsection\*?\{[^}]*[Cc]riterios de evaluaci[óo]n",
            # Frases que narran la realización en lugar del tema.
            r"El nivel cognitivo (dominante|aplicado|esperado)",
            r"[Ll]a t[ée]cnica de cuestionario",
            r"[Ll]a t[ée]cnica did[áa]ctica (aplicada|utilizada|empleada)",
            r"se aplic[oó] (una|la) t[ée]cnica",
            r"El (cuestionario|producto|mapa|cuadro) se presenta en formato",
            r"Considero que esta (estructura|t[ée]cnica|actividad)",
        )
        for pattern in patterns:
            hits.extend(match.group(0).strip() for match in re.finditer(pattern, text, re.IGNORECASE))
        return sorted(set(hits))

    def _extract_sections(self, text: str) -> list[str]:
        return [match.group(1).strip() for match in re.finditer(r"\\section\{([^}]+)\}", text)]

    def _count_document_concepts(self, text: str) -> int:
        """Cuenta conceptos identificables en el marco conceptual del propio TEX.

        Fallback usado cuando NO existe planeación oficial (materias UCNL sin
        extractor-aulatex). Deriva la cobertura conceptual del documento contando
        términos técnicos resaltados de forma explícita: definiciones en
        \\textbf{...}, entradas de description/itemize con \\item[\\textbf{...}] y
        \\emph{...}. Sólo se consideran términos con longitud razonable (una a
        varias palabras) para evitar contar énfasis accidental. Devuelve el número
        de conceptos distintos detectados.
        """
        # Recortar bloques de tabla (longtable/tabular): ahí \textbf marca cabeceras y
        # respuestas correctas, no conceptos del marco. Se evalúa sólo el texto en prosa.
        prose = re.sub(
            r"\\begin\{(longtable|tabular)\}.*?\\end\{\1\}",
            " ",
            text,
            flags=re.DOTALL,
        )
        concepts: set[str] = set()
        patterns = (
            # Definiciones explícitas en listas descriptivas.
            r"\\item\[\\textbf\{([^}]{3,60})\}\]",
            r"\\item\[\\emph\{([^}]{3,60})\}\]",
            # Términos técnicos resaltados en la prosa del marco conceptual.
            r"\\textbf\{([^}]{3,60})\}",
            r"\\emph\{([^}]{3,60})\}",
        )
        stop = {
            "objetivo", "propósito", "proposito", "conclusión", "conclusion",
            "respuesta", "respuestas", "justificación", "justificacion",
            "pregunta", "preguntas", "producto elaborado", "referencias",
            "bibliografía", "bibliografia", "introducción", "introduccion",
            "correcta", "no.", "no", "opciones", "alumno", "objetivo:",
            "enfoque de analisis", "nivel cognitivo", "producto elaborado:",
        }
        for pattern in patterns:
            for match in re.finditer(pattern, prose):
                term = re.sub(r"\s+", " ", match.group(1)).strip(" .:;,").lower()
                if not term or term in stop or len(term) < 3:
                    continue
                if term.isdigit():
                    continue
                # Descartar énfasis largo (frases) o que parezca opción de respuesta ("a. ...").
                if len(term.split()) > 4:
                    continue
                if re.match(r"^[a-d]\.\s", term):
                    continue
                if term.endswith(":"):
                    continue
                concepts.add(term)
        return len(concepts)
