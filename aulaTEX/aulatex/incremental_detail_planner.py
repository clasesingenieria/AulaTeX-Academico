from __future__ import annotations

import json
import re
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .activity_contract import (
    DIDACTIC_TECHNIQUE_CONTRACTS,
    REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT,
)
from .didactic_catalog import (
    canonical_technique_id,
    get_technique_contract,
)
from .editorial_memory import EditorialMemoryStore
from .workspace import AulaTeXWorkspace, EditorialScope


@dataclass(frozen=True)
class DetailPlannerRequest:
    target: str = "."
    activity_number: int = 0
    output: str = ""
    max_scopes: int = 6
    max_fixed_point_passes: int = 4
    persist_memory: bool = True


@dataclass(frozen=True)
class DetailPlannerResult:
    ok: bool
    run_id: str
    run_dir: Path
    manifest_path: Path
    report_path: Path
    processed_scopes: tuple[str, ...]
    updated_scopes: tuple[str, ...]


class IncrementalDetailPlanner:
    def __init__(self, workspace: AulaTeXWorkspace | None = None, store: EditorialMemoryStore | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.store = store or EditorialMemoryStore(self.workspace)
        self.root = self.workspace.temp_root / "detail-planner" / "runs"
        self.root.mkdir(parents=True, exist_ok=True)

    def run(self, request: DetailPlannerRequest) -> DetailPlannerResult:
        by_key, children = self.workspace.editorial_scope_index()
        seed_scope = self.workspace.find_scope_for_target(request.target, activity_number=request.activity_number or None)
        if seed_scope is None:
            raise ValueError(f"No se pudo resolver un scope editorial para: {request.target}")

        run_id = f"{self.workspace.timestamp()}-detail-planner"
        run_dir = self._resolve_run_dir(request, run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        pending_queue = deque(self._initial_scope_queue(seed_scope, children, request.max_scopes))
        backtrack_queue: deque[str] = deque()
        processed_stack: list[str] = []
        scope_entries: dict[str, dict[str, Any]] = {}
        updated_scopes: list[str] = []
        novelty_events: list[dict[str, Any]] = []
        review_counts: dict[str, int] = {}
        fixed_point_pass = 1

        while fixed_point_pass <= max(1, int(request.max_fixed_point_passes)):
            progressed = False
            active_queue = backtrack_queue if backtrack_queue else pending_queue
            while active_queue:
                scope_key = active_queue.popleft()
                scope = by_key.get(scope_key)
                if scope is None:
                    active_queue = backtrack_queue if backtrack_queue else pending_queue
                    continue
                if review_counts.get(scope_key, 0) >= 2:
                    active_queue = backtrack_queue if backtrack_queue else pending_queue
                    continue

                processed = self._process_scope(seed_scope, scope, request)
                processed_stack.append(scope_key)
                review_counts[scope_key] = review_counts.get(scope_key, 0) + 1
                scope_entries[scope_key] = processed
                progressed = True

                if processed["changed"] and scope_key not in updated_scopes:
                    updated_scopes.append(scope_key)

                for event in processed["novelty_events"]:
                    novelty_events.append(event)

                if processed["novelty_events"]:
                    for candidate in self._backtrack_targets(scope, processed_stack, by_key):
                        if candidate == scope_key:
                            continue
                        if review_counts.get(candidate, 0) >= 2:
                            continue
                        if candidate in backtrack_queue or candidate in pending_queue:
                            continue
                        backtrack_queue.append(candidate)

                active_queue = backtrack_queue if backtrack_queue else pending_queue

            if not progressed or not backtrack_queue:
                break
            fixed_point_pass += 1

        state = {
            "pending_queue": list(pending_queue),
            "processed_stack": processed_stack,
            "backtrack_queue": list(backtrack_queue),
            "novelty_events": novelty_events,
            "dirty_scopes": [key for key, item in scope_entries.items() if item["changed"]],
            "inheritance_refresh": sorted({event["scope_key"] for event in novelty_events}),
            "fixed_point_pass": fixed_point_pass,
            "max_fixed_point_passes": max(1, int(request.max_fixed_point_passes)),
        }
        manifest = {
            "kind": "detail-planner",
            "version": 1,
            "run_id": run_id,
            "request": {
                "target": request.target,
                "activity_number": int(request.activity_number),
                "output": request.output,
                "max_scopes": int(request.max_scopes),
                "max_fixed_point_passes": int(request.max_fixed_point_passes),
                "persist_memory": bool(request.persist_memory),
            },
            "seed_scope": self._scope_payload(seed_scope),
            "state": state,
            "processed_scopes": [scope_entries[key] for key in processed_stack if key in scope_entries],
            "updated_scopes": updated_scopes,
        }

        manifest_path = run_dir / "manifest.json"
        report_path = run_dir / "report.md"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        report_path.write_text(self._render_report(manifest), encoding="utf-8")
        self.workspace.append_bitacora(run_id, "detail-planner", manifest)
        return DetailPlannerResult(
            ok=True,
            run_id=run_id,
            run_dir=run_dir,
            manifest_path=manifest_path,
            report_path=report_path,
            processed_scopes=tuple(processed_stack),
            updated_scopes=tuple(updated_scopes),
        )

    def _resolve_run_dir(self, request: DetailPlannerRequest, run_id: str) -> Path:
        if request.output.strip():
            output_root = self.workspace.resolve_target(request.output)
            return output_root / run_id
        return self.root / run_id

    def _initial_scope_queue(
        self,
        seed_scope: EditorialScope,
        children: dict[str, list[EditorialScope]],
        max_scopes: int,
    ) -> list[str]:
        queue: list[str] = []

        def add(scope_key: str) -> None:
            if not scope_key or scope_key in queue or len(queue) >= max(1, int(max_scopes)):
                return
            queue.append(scope_key)

        add(seed_scope.key)
        for child in children.get(seed_scope.key, []):
            add(child.key)
        if seed_scope.parent_key:
            for sibling in children.get(seed_scope.parent_key, []):
                add(sibling.key)
        for ancestor in self.workspace.scope_chain(seed_scope.key)[1:]:
            add(ancestor.key)
        return queue

    def _process_scope(self, seed_scope: EditorialScope, scope: EditorialScope, request: DetailPlannerRequest) -> dict[str, Any]:
        payload = self.store.get_memory(scope.key)
        node_metadata = dict(payload.get("node_metadata") or {})
        previous_details = dict(node_metadata.get("editing_details") or {})
        related_keys = self._related_scope_keys(scope)
        related_memories = self.store.get_memories(related_keys)
        editing_details = self._build_editing_details(seed_scope, scope, request, related_keys, related_memories, previous_details)
        novelty_events = self._compute_novelty_events(scope, previous_details, editing_details)
        editing_details["novelty_signals"] = [event["section"] for event in novelty_events]

        changed = previous_details != editing_details
        if changed and request.persist_memory:
            updated_payload = dict(payload)
            updated_node_metadata = dict(node_metadata)
            updated_node_metadata["editing_details"] = editing_details
            updated_node_metadata["detail_planner"] = {
                "run_id": self.workspace.timestamp(),
                "scope_key": scope.key,
                "related_scope_keys": related_keys,
                "novelty_count": len(novelty_events),
            }
            updated_payload["node_metadata"] = updated_node_metadata
            self.store.save_memory(scope, updated_payload, seed_scope.key)

        return {
            "scope_key": scope.key,
            "scope_level": scope.level,
            "label": scope.label,
            "changed": changed,
            "novelty_events": novelty_events,
            "editing_details": editing_details,
            "related_scope_keys": related_keys,
        }

    def _build_editing_details(
        self,
        seed_scope: EditorialScope,
        scope: EditorialScope,
        request: DetailPlannerRequest,
        related_keys: list[str],
        related_memories: dict[str, dict],
        previous_details: dict[str, Any],
    ) -> dict[str, Any]:
        source_artifacts = self._source_artifacts(scope)
        context_excerpt = self._activity_context_excerpt(seed_scope, scope, request)
        technique_id = self._infer_didactic_technique(context_excerpt)
        technique_contract = get_technique_contract(technique_id)
        inherited_fixes = self._collect_inherited_compilation_fixes(related_memories, previous_details)
        learned_from = [
            {
                "scope_key": key,
                "has_memory": bool(related_memories.get(key)),
            }
            for key in related_keys
        ]
        return {
            "heading_contract": {
                "title_rule": "El titulo visible no debe incluir 'Actividad #' cuando el producto es una actividad.",
                "subtitle_rule": "El subtitulo debe compactar tema, producto o problema sin metadiscurso.",
                "subject_rule": f"Actividad {int(request.activity_number)} - {scope.subject or scope.label}" if int(request.activity_number) > 0 else (scope.subject or scope.label),
                "scope_label": scope.label,
            },
            "didactic_contract": {
                "detected_id": technique_id,
                "catalogo_no": technique_contract.get("catalogo_no"),
                "nombre_oficial": technique_contract.get("nombre_oficial", ""),
                "nivel": technique_contract.get("nivel", ""),
                "familia": technique_contract.get("familia", ""),
                "aliases": list(technique_contract.get("aliases", ())),
                "required_visible_elements": list(technique_contract.get("required_visible_elements", ())),
                "preservation_rule": technique_contract.get("preservation_rule", "Conservar la forma visible solicitada por la consigna."),
                "preservation_rule_official": technique_contract.get("preservation_rule_official", ""),
                "structure_rule": technique_contract.get("structure_rule", ""),
                "three_act_gravity_rule": technique_contract.get("three_act_gravity_rule", ""),
                "layout_rule": technique_contract.get("layout_rule", ""),
                "no_gap_rule": technique_contract.get("no_gap_rule", ""),
                "closure_rule": technique_contract.get("closure_rule", ""),
                # Evidencia oficial UnADM (fascículos + web): pasos de construcción
                # y secciones completas para que el motor materialice con fidelidad.
                "build_steps": technique_contract.get("build_steps", ""),
                "official_contract": technique_contract.get("official_contract", {}),
                # Consolidación de construcción TikZ/LaTeX + rúbrica de puntuación
                # (didactic_builder_consolidator): cómo materializar el producto y
                # cómo se puntúa, para integrarlo con realizar-actividad.
                "tikz_pattern": technique_contract.get("tikz_pattern", {}),
                "scoring_rubric": technique_contract.get("scoring_rubric", {}),
                "construction_integration": technique_contract.get("construction_contract", {}).get("realizar_actividad_integration", {}),
                # Patrón curado desde una actividad REAL ya entregada (máxima
                # prioridad: probado en producción). Incluye trazabilidad de origen.
                "real_pattern": technique_contract.get("real_pattern", {}),
            },
            "structure_contract": {
                "three_part_structure": REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT["quality_gates"]["three_part_structure"],
                "development_section": REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT["quality_gates"]["development_section"],
                "product_centric_gravity": REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT["quality_gates"]["product_centric_gravity"],
                "introduction": REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT["quality_gates"]["introduction"],
                "conclusion": REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT["quality_gates"]["conclusion"],
            },
            "layout_contract": {
                "no_gap_before_visual_deliverable": REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT["compilation_rules"]["no_gap_before_visual_deliverable"],
                "landscape_single_page": REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT["compilation_rules"]["landscape_single_page"],
                "conclusion_single_page": REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT["compilation_rules"]["conclusion_single_page"],
                "page_control": REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT["compilation_rules"]["page_control"],
                "always_use_latexmk": REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT["compilation_rules"].get(
                    "always_use_latexmk",
                    "Compilar siempre con latexmk y aislar los auxiliares en .build/latex.",
                ),
                "no_build_residues": REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT["compilation_rules"].get(
                    "no_build_residues",
                    "La carpeta de la actividad no debe conservar auxiliares de compilación junto al TEX.",
                ),
            },
            "bibliography_contract": {
                "visible_citations_rule": REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT["quality_gates"]["visible_citations"],
                "reference_growth_rule": REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT["quality_gates"]["reference_growth"],
                "local_first_rule": REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT["source_validation_rules"]["local_first_online_when_needed"],
            },
            "institutional_identity": {
                "institution": scope.institution,
                "career": scope.career,
                "subject": scope.subject,
                "activity": scope.activity or (f"Actividad {int(request.activity_number)}" if int(request.activity_number) > 0 else ""),
                "seed_scope_key": seed_scope.key,
            },
            "compilation_fixes": inherited_fixes,
            "quality_rules": self._quality_rules(),
            "exceptions": list(previous_details.get("exceptions", [])),
            "learned_from": learned_from,
            "novelty_signals": [],
            "derived_from": {
                "local_memory": bool(self.store.get_memory(scope.key).get("node_metadata", {})),
                "ancestor_memory": any(key != scope.key and related_memories.get(key) for key in related_keys),
                "related_nodes": related_keys,
                "source_artifacts": source_artifacts,
            },
            "confidence": self._confidence_payload(source_artifacts, related_memories, context_excerpt),
        }

    def _related_scope_keys(self, scope: EditorialScope) -> list[str]:
        keys: list[str] = []
        for item in self.workspace.scope_chain(scope.key):
            if item.key not in keys:
                keys.append(item.key)
        by_key, children = self.workspace.editorial_scope_index()
        if scope.parent_key:
            for sibling in children.get(scope.parent_key, []):
                if sibling.key != scope.key and sibling.key not in keys:
                    keys.append(sibling.key)
        for child in children.get(scope.key, []):
            if child.key not in keys:
                keys.append(child.key)
        return keys[:8]

    def _source_artifacts(self, scope: EditorialScope) -> list[str]:
        root = self.workspace.resolve_target(scope.relative_path)
        if not root.exists() or not root.is_dir():
            return []
        names = ("README.md", "COMPILACION.md")
        artifacts = [self.workspace.relative(root / name) for name in names if (root / name).exists()]
        artifacts.extend(self.workspace.relative(path) for path in sorted(root.glob("*.bib"))[:2])
        artifacts.extend(self.workspace.relative(path) for path in sorted(root.glob("reporte-*.tex"))[:2])
        artifacts.extend(self.workspace.relative(path) for path in sorted(root.glob("presentacion-*.tex"))[:1])
        return artifacts

    def _infer_didactic_technique(self, context_excerpt: str) -> str:
        """Detecta la técnica por alias, priorizando el match MÁS ESPECÍFICO.

        Se ordenan todos los (alias, técnica) por longitud de alias descendente,
        de modo que un alias más largo y específico (p. ej. "cronología ilustrada"
        -> cronologia_ilustrada) gane sobre uno más corto y genérico (p. ej.
        "cronología" -> linea_de_tiempo). Evita colisiones por orden del diccionario.
        """
        normalized = context_excerpt.casefold()
        candidates: list[tuple[int, int, str]] = []
        for order, (technique_id, contract) in enumerate(DIDACTIC_TECHNIQUE_CONTRACTS.items()):
            for alias in contract.get("aliases", ()):
                alias_cf = str(alias).casefold()
                if alias_cf and alias_cf in normalized:
                    candidates.append((len(alias_cf), -order, technique_id))
        if not candidates:
            return "general"
        # Empate de longitud: gana el declarado primero (las legacy van al frente).
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return candidates[0][2]

    def _collect_inherited_compilation_fixes(
        self,
        related_memories: dict[str, dict],
        previous_details: dict[str, Any],
    ) -> list[str]:
        fixes: list[str] = []
        for item in previous_details.get("compilation_fixes", []):
            if item not in fixes:
                fixes.append(str(item))
        for memory in related_memories.values():
            metadata = memory.get("node_metadata", {}) if isinstance(memory, dict) else {}
            details = metadata.get("editing_details", {}) if isinstance(metadata, dict) else {}
            for item in details.get("compilation_fixes", []):
                text = str(item)
                if text and text not in fixes:
                    fixes.append(text)
        return fixes[:8]

    def _quality_rules(self) -> list[str]:
        quality_gates = REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT.get("quality_gates", {})
        visible_rules = REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT.get("visible_text_rules", {})
        compilation_rules = REALIZAR_ACTIVIDAD_PIPELINE_CONTRACT.get("compilation_rules", {})
        ordered_keys = (
            "headings",
            "didactic_format",
            "bibliography",
            "visible_citations",
            "reference_growth",
            "content",
            "visible_style",
            "three_part_structure",
            "introduction",
            "development_section",
            "product_centric_gravity",
            "conclusion",
            "compile",
        )
        lines = [str(quality_gates[key]) for key in ordered_keys if key in quality_gates]
        for key in (
            "avoid_metadiscourse",
            "fold_context_into_introduction",
            "three_part_body",
            "development_title_cosmetic",
            "product_centric_development",
            "fold_analysis_into_conclusion",
        ):
            if key in visible_rules:
                lines.append(str(visible_rules[key]))
        for key in ("no_gap_before_visual_deliverable", "landscape_single_page", "conclusion_single_page"):
            if key in compilation_rules:
                lines.append(str(compilation_rules[key]))
        return lines

    def _confidence_payload(
        self,
        source_artifacts: list[str],
        related_memories: dict[str, dict],
        context_excerpt: str,
    ) -> dict[str, Any]:
        artifact_score = 0.2 if source_artifacts else 0.0
        memory_score = min(0.5, len([key for key, value in related_memories.items() if value]) * 0.1)
        context_score = 0.3 if context_excerpt.strip() else 0.0
        global_score = round(min(1.0, artifact_score + memory_score + context_score), 2)
        return {
            "global": global_score,
            "by_section": {
                "heading_contract": round(min(1.0, 0.4 + artifact_score), 2),
                "didactic_contract": round(min(1.0, 0.2 + context_score), 2),
                "bibliography_contract": round(min(1.0, 0.2 + memory_score + artifact_score), 2),
            },
        }

    def _activity_context_excerpt(
        self,
        seed_scope: EditorialScope,
        scope: EditorialScope,
        request: DetailPlannerRequest,
    ) -> str:
        if scope.key != seed_scope.key or scope.level != "actividad":
            return self.workspace.context_summary(scope.relative_path, max_chars=5000)

        parts: list[str] = []
        target = self.workspace.resolve_target(request.target)
        if target.is_file():
            parts.append(self.workspace.context_summary(str(target), max_chars=5000))

        base = self.workspace.resolve_target(scope.relative_path) / "extractor-aulatex"
        activity_number = int(request.activity_number or 0)
        if activity_number > 0 and base.is_dir():
            pattern = re.compile(
                rf"conceptos-.*-(?:actividad-0?{activity_number}|s0?{activity_number})\b",
                re.IGNORECASE,
            )
            for candidate in sorted(base.glob("conceptos-*")):
                summary = candidate / "resumen_planeacion.json"
                if candidate.is_dir() and pattern.search(candidate.name) and summary.is_file():
                    parts.insert(0, summary.read_text(encoding="utf-8", errors="replace")[:10000])
                    break

        return "\n\n".join(parts) or self.workspace.context_summary(scope.relative_path, max_chars=5000)

    def _compute_novelty_events(
        self,
        scope: EditorialScope,
        previous_details: dict[str, Any],
        current_details: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if not previous_details:
            return [
                {
                    "scope_key": scope.key,
                    "scope_level": scope.level,
                    "section": "bootstrap",
                    "reason": "Se genero detail planning inicial para el nodo.",
                }
            ]

        events: list[dict[str, Any]] = []
        for section in (
            "heading_contract",
            "didactic_contract",
            "bibliography_contract",
            "institutional_identity",
            "compilation_fixes",
            "quality_rules",
            "exceptions",
        ):
            if previous_details.get(section) != current_details.get(section):
                events.append(
                    {
                        "scope_key": scope.key,
                        "scope_level": scope.level,
                        "section": section,
                        "reason": f"Cambio detectado en {section}; requiere refresco incremental.",
                    }
                )
        return events

    def _backtrack_targets(
        self,
        scope: EditorialScope,
        processed_stack: list[str],
        by_key: dict[str, EditorialScope],
    ) -> list[str]:
        candidates: list[str] = []
        if processed_stack:
            previous_key = processed_stack[-1]
            if previous_key != scope.key:
                candidates.append(previous_key)
        if scope.parent_key and scope.parent_key in by_key:
            candidates.append(scope.parent_key)
        return candidates

    def _scope_payload(self, scope: EditorialScope) -> dict[str, Any]:
        return {
            "scope_key": scope.key,
            "scope_level": scope.level,
            "label": scope.label,
            "relative_path": scope.relative_path,
            "institution": scope.institution,
            "career": scope.career,
            "subject": scope.subject,
            "activity": scope.activity,
            "parent_key": scope.parent_key,
        }

    def _render_report(self, manifest: dict[str, Any]) -> str:
        lines = [
            "# Detail planner AulaTeX",
            "",
            f"- Run: {manifest['run_id']}",
            f"- Scope semilla: {manifest['seed_scope']['scope_key']}",
            f"- Scopes procesados: {len(manifest.get('processed_scopes', []))}",
            f"- Scopes actualizados: {len(manifest.get('updated_scopes', []))}",
            f"- Novedades: {len(manifest.get('state', {}).get('novelty_events', []))}",
            f"- fixed_point_pass: {manifest.get('state', {}).get('fixed_point_pass', 0)} / {manifest.get('state', {}).get('max_fixed_point_passes', 0)}",
            "",
            "## Cola serializable",
            "",
            f"- pending_queue: {json.dumps(manifest.get('state', {}).get('pending_queue', []), ensure_ascii=False)}",
            f"- backtrack_queue: {json.dumps(manifest.get('state', {}).get('backtrack_queue', []), ensure_ascii=False)}",
            f"- dirty_scopes: {json.dumps(manifest.get('state', {}).get('dirty_scopes', []), ensure_ascii=False)}",
            "",
            "## Scopes",
            "",
        ]
        for item in manifest.get("processed_scopes", []):
            lines.append(f"### {item['scope_key']}")
            lines.append("")
            lines.append(f"- Nivel: {item['scope_level']}")
            lines.append(f"- Label: {item['label']}")
            lines.append(f"- Cambio: {item['changed']}")
            lines.append(f"- Relacionados: {', '.join(item.get('related_scope_keys', [])) or 'ninguno'}")
            novelty = item.get("novelty_events", [])
            lines.append(f"- Novedades: {len(novelty)}")
            details = item.get("editing_details", {})
            heading = details.get("heading_contract", {})
            didactic = details.get("didactic_contract", {})
            lines.append(f"- Subject: {heading.get('subject_rule', '')}")
            lines.append(f"- Tecnica detectada: {didactic.get('detected_id', 'general')}")
            lines.append("")
        return "\n".join(lines) + "\n"


__all__ = [
    "DetailPlannerRequest",
    "DetailPlannerResult",
    "IncrementalDetailPlanner",
]