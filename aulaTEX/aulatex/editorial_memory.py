from __future__ import annotations

import json
import os
import re
import sqlite3
import hashlib
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Callable, Iterable

from .config import ENGINE_ENV_PREFIX, diagnostic_metrics_enabled
from .llm_bridge import DEFAULT_MAX_TOKENS, DEFAULT_TIMEOUT_SECONDS, LLM_ENGINES, AulaTeXLLMClient
from .memory_fusion_engine import MemoryFusionEngine
from .memory_unifier import unify_markdown_memories
from .workspace import AulaTeXWorkspace, EditorialScope


EDITORIAL_LEVELS = (
    "actividad",
    "materia",
    "carrera",
    "institucion",
    "interinstitucional",
)

PROPAGATION_MODES = (
    "local",
    "lateral",
    "ascendente",
    "ascendente-exhaustivo",
    "descendente",
    "recursivo",
    "bidireccional",
)

ENGINE_PRIORITY = {
    "Codex": 10,
    "Auto (model-router)": 20,
    "Claude Foundry": 30,
    "GPT-Pro": 40,
}

SCHEMA_VERSION = 3

MEMORY_SECTIONS = (
    "summary",
    "identity_rules",
    "structure_rules",
    "activity_rules",
    "quality_gates",
    "latex_rules",
    "bibliography_rules",
    "propagation_hints",
    "open_questions",
)

MEMORY_STRING_FIELDS = (
    "artifact_name",
)

MEMORY_LIST_FIELDS = (
    "sources",
    "artifact_types",
    "supported_artifact_types",
    "source_documents",
    "source_fragments",
    "concepts",
    "section_titles",
    "citations",
    "bibliography_index",
)

MEMORY_DICT_FIELDS = (
    "node_metadata",
    "curricular_context",
    "artifact_templates",
    "editorial_dna",
    "tex_blueprint",
    "tex_content_memory",
)


@dataclass(frozen=True)
class EditorialMemoryRequest:
    source_scope_key: str
    build_level: str = "materia"
    propagation_mode: str = "ascendente"
    iterations: int = 2
    engines: list[str] | tuple[str, ...] = ("Codex", "Claude Foundry", "GPT-Pro")
    max_tokens: int = DEFAULT_MAX_TOKENS
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    scope_offset: int = 0
    scope_limit: int = 0


@dataclass(frozen=True)
class EditorialMemoryEvent:
    kind: str
    message: str
    current: int = 0
    total: int = 0
    scope_key: str = ""
    engine: str = ""
    cycle: int = 0


@dataclass(frozen=True)
class EditorialMemoryBuildResult:
    run_id: str
    run_dir: Path
    manifest_path: Path
    built_scopes: tuple[str, ...]
    ok: bool
    cancelled: bool = False


class EditorialMemoryStore:
    def __init__(self, workspace: AulaTeXWorkspace | None = None, *, diagnostics_enabled: bool | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.diagnostics_enabled = diagnostic_metrics_enabled() if diagnostics_enabled is None else diagnostics_enabled
        self.root = self.workspace.feedback_root / "editorial-memory"
        self.root.mkdir(parents=True, exist_ok=True)
        self.temp_root = self.workspace.temp_root / "editorial-memory"
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.temp_root / "editorial-memory.db"
        self.scopes_dir = self.temp_root / "scope-cache"
        self.scopes_dir.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _safe_scope_slug(self, scope_key: str, *, max_prefix: int = 72) -> str:
        normalized = scope_key.replace('/', '__')
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", normalized).strip("._")
        digest = hashlib.sha1(scope_key.encode("utf-8", errors="replace")).hexdigest()[:12]
        if len(safe) > max_prefix:
            safe = safe[:max_prefix].rstrip("._-")
        return f"{safe}--{digest}"

    def _local_scope_memory_path(self, scope: EditorialScope) -> Path | None:
        rel = Path(scope.relative_path)
        if scope.level == "actividad":
            base_dir = self.workspace.repo_root / rel
        elif scope.level == "materia":
            base_dir = (self.workspace.repo_root / rel).parent
        elif scope.level == "carrera":
            base_dir = (self.workspace.repo_root / rel).parent
        elif scope.level == "institucion":
            base_dir = self.workspace.repo_root
        else:
            return None
        filename = f"memoria-{scope.level}-{self._safe_scope_slug(scope.key, max_prefix=40)}.json"
        return base_dir / ".memoria-aulatex" / filename

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS scopes (
                    scope_key TEXT PRIMARY KEY,
                    level TEXT NOT NULL,
                    label TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    institution TEXT NOT NULL,
                    career TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    activity TEXT NOT NULL,
                    parent_key TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS memories (
                    scope_key TEXT PRIMARY KEY,
                    level TEXT NOT NULL,
                    memory_json TEXT NOT NULL,
                    source_scope_key TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    source_scope_key TEXT NOT NULL,
                    build_level TEXT NOT NULL,
                    propagation_mode TEXT NOT NULL,
                    iterations INTEGER NOT NULL,
                    engines_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    ok INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS cycles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    scope_key TEXT NOT NULL,
                    cycle_index INTEGER NOT NULL,
                    engine TEXT NOT NULL,
                    ok INTEGER NOT NULL,
                    response_chars INTEGER NOT NULL,
                    response_text TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def upsert_scope(self, scope: EditorialScope) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO scopes (
                    scope_key, level, label, relative_path, institution, career, subject, activity, parent_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(scope_key) DO UPDATE SET
                    level=excluded.level,
                    label=excluded.label,
                    relative_path=excluded.relative_path,
                    institution=excluded.institution,
                    career=excluded.career,
                    subject=excluded.subject,
                    activity=excluded.activity,
                    parent_key=excluded.parent_key,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    scope.key,
                    scope.level,
                    scope.label,
                    scope.relative_path,
                    scope.institution,
                    scope.career,
                    scope.subject,
                    scope.activity,
                    scope.parent_key,
                ),
            )

    def start_run(self, request: EditorialMemoryRequest, engines: list[str], run_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO runs (run_id, source_scope_key, build_level, propagation_mode, iterations, engines_json, ok)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    run_id,
                    request.source_scope_key,
                    request.build_level,
                    request.propagation_mode,
                    int(request.iterations),
                    json.dumps(engines, ensure_ascii=False),
                ),
            )

    def finish_run(self, run_id: str, ok: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE runs SET completed_at=CURRENT_TIMESTAMP, ok=? WHERE run_id=?",
                (1 if ok else 0, run_id),
            )

    def record_cycle(
        self,
        *,
        run_id: str,
        scope_key: str,
        cycle_index: int,
        engine: str,
        ok: bool,
        response_text: str,
    ) -> None:
        if not self.diagnostics_enabled:
            return
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO cycles (run_id, scope_key, cycle_index, engine, ok, response_chars, response_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, scope_key, cycle_index, engine, 1 if ok else 0, len(response_text), response_text),
            )

    def get_memory(self, scope_key: str) -> dict:
        with self._connect() as conn:
            row = conn.execute("SELECT memory_json FROM memories WHERE scope_key=?", (scope_key,)).fetchone()
        if row is not None:
            payload = self._normalize_memory(json.loads(row["memory_json"]))
            if any(payload.get(section) for section in MEMORY_SECTIONS):
                return payload

        by_key, _children = self.workspace.editorial_scope_index()
        scope = by_key.get(scope_key)
        if scope is not None:
            local_path = self._local_scope_memory_path(scope)
            if local_path and local_path.exists():
                return self._normalize_memory(json.loads(local_path.read_text(encoding="utf-8")))
        return self._empty_memory()

    def get_memories(self, scope_keys: Iterable[str]) -> dict[str, dict]:
        keys = [key for key in dict.fromkeys(scope_keys) if key]
        if not keys:
            return {}
        placeholders = ",".join("?" for _ in keys)
        query = f"SELECT scope_key, memory_json FROM memories WHERE scope_key IN ({placeholders})"
        with self._connect() as conn:
            rows = conn.execute(query, keys).fetchall()
        memories: dict[str, dict] = {}
        for row in rows:
            payload = self._normalize_memory(json.loads(row["memory_json"]))
            if any(payload.get(section) for section in MEMORY_SECTIONS):
                memories[str(row["scope_key"])] = payload
        for key in keys:
            if key not in memories:
                memory = self.get_memory(key)
                if any(memory.get(section) for section in MEMORY_SECTIONS):
                    memories[key] = memory
        return memories

    def save_memory(self, scope: EditorialScope, payload: dict, source_scope_key: str) -> None:
        normalized = self._normalize_memory(payload)
        normalized = self._enrich_memory(scope, normalized)
        self.upsert_scope(scope)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO memories (scope_key, level, memory_json, source_scope_key)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(scope_key) DO UPDATE SET
                    level=excluded.level,
                    memory_json=excluded.memory_json,
                    source_scope_key=excluded.source_scope_key,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (scope.key, scope.level, json.dumps(normalized, ensure_ascii=False, indent=2), source_scope_key),
            )
        json_path = self.scopes_dir / f"{scope.key.replace('/', '__')}.json"
        json_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
        markdown_path = self.scopes_dir / f"{scope.key.replace('/', '__')}.md"
        markdown_content = self.render_memory_markdown(scope, normalized)
        markdown_path.write_text(markdown_content, encoding="utf-8")

        snapshots_dir = self.temp_root / "scope-snapshots" / self._safe_scope_slug(scope.key)
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = snapshots_dir / f"snapshot-{self.workspace.timestamp()}.md"
        snapshot_path.write_text(markdown_content, encoding="utf-8")
        unify_markdown_memories(snapshots_dir, snapshots_dir / "unified-memory.json")

        self._write_local_scope_memory(scope, normalized)

    def _write_local_scope_memory(self, scope: EditorialScope, payload: dict) -> None:
        local_path = self._local_scope_memory_path(scope)
        if local_path is None:
            return
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _enrich_memory(self, scope: EditorialScope, payload: dict) -> dict:
        enriched = self._normalize_memory(payload)
        metadata = {
            "scope_key": scope.key,
            "level": scope.level,
            "label": scope.label,
            "relative_path": scope.relative_path,
            "institution": scope.institution,
            "career": scope.career,
            "subject": scope.subject,
            "activity": scope.activity,
            "parent_key": scope.parent_key,
        }
        enriched["node_metadata"] = {**enriched.get("node_metadata", {}), **metadata}

        if scope.level not in {"actividad", "materia"}:
            enriched["schema_version"] = SCHEMA_VERSION
            return enriched

        subject_dir = self.workspace.repo_root / scope.relative_path
        activity_number = "".join(ch for ch in scope.activity if ch.isdigit()) if scope.level == "actividad" else ""

        artifact_paths: dict[str, Path] = {}
        for candidate in sorted(subject_dir.glob("reporte-*.tex")):
            if re.search(r"-Actividad-\d+\.tex$", candidate.name, re.IGNORECASE):
                continue
            artifact_paths.setdefault("reporte_base", candidate)
            break
        for candidate in sorted(subject_dir.glob("presentacion-*.tex")):
            if re.search(r"-Actividad-\d+\.tex$", candidate.name, re.IGNORECASE):
                continue
            artifact_paths.setdefault("presentacion_base", candidate)
            break
        if scope.level == "actividad" and activity_number:
            for candidate in sorted(subject_dir.glob(f"reporte-*-Actividad-{activity_number}.tex")):
                artifact_paths.setdefault("reporte", candidate)
                break
            for candidate in sorted(subject_dir.glob(f"presentacion-*-Actividad-{activity_number}.tex")):
                artifact_paths.setdefault("presentacion", candidate)
                break

        artifact_types = [kind for kind in ("reporte", "presentacion") if kind in artifact_paths]
        supported_types = [kind for kind in ("reporte", "presentacion") if f"{kind}_base" in artifact_paths or kind in artifact_paths]
        if scope.level == "actividad":
            primary_type = artifact_types[0] if artifact_types else (supported_types[0] if supported_types else "reporte")
            if primary_type in artifact_paths:
                enriched["artifact_name"] = artifact_paths[primary_type].stem
            elif activity_number:
                enriched["artifact_name"] = f"{primary_type}-{scope.subject}-Actividad-{activity_number}"
            enriched["artifact_types"] = _dedupe_lines(enriched.get("artifact_types", []) + artifact_types)
        else:
            templates: dict[str, str] = dict(enriched.get("artifact_templates", {}))
            if "reporte_base" in artifact_paths:
                templates["reporte"] = artifact_paths["reporte_base"].stem
            if "presentacion_base" in artifact_paths:
                templates["presentacion"] = artifact_paths["presentacion_base"].stem
            enriched["artifact_templates"] = templates
            enriched["supported_artifact_types"] = _dedupe_lines(enriched.get("supported_artifact_types", []) + supported_types)

        source_documents = list(enriched.get("source_documents", []))
        source_fragments = list(enriched.get("source_fragments", []))
        concepts = list(enriched.get("concepts", []))
        section_titles = list(enriched.get("section_titles", []))
        citations = list(enriched.get("citations", []))
        bibliography_index = list(enriched.get("bibliography_index", []))
        tex_blueprint = dict(enriched.get("tex_blueprint", {}))
        tex_content_memory = dict(enriched.get("tex_content_memory", {}))
        bibliography_sources = dict(tex_content_memory.get("bibliography_sources", {}))

        readme_path = subject_dir / "README.md"
        if readme_path.exists():
            source_documents.append(self.workspace.relative(readme_path))
            source_fragments.extend(_extract_nonempty_lines(self._safe_read_text(readme_path), limit=6, max_len=220))

        program_path = next(iter(sorted(subject_dir.glob("programa-analitico*.md"))), None)
        curricular_context = dict(enriched.get("curricular_context", {}))
        if program_path is not None and program_path.exists():
            source_documents.append(self.workspace.relative(program_path))
            program_context = _extract_program_context(self._safe_read_text(program_path))
            curricular_context = {**program_context, **curricular_context}
            source_fragments.extend(program_context.get("source_fragments", []))
            concepts.extend(program_context.get("work_axes", []))

        bib_paths = [path for path in sorted(subject_dir.glob("*.bib")) if path.is_file()]
        for bib_path in bib_paths:
            source_documents.append(self.workspace.relative(bib_path))
            bib_text = self._safe_read_text(bib_path)
            bib_entries = _extract_bibtex_entries(bib_text, self.workspace.relative(bib_path))
            bibliography_sources.update(bib_entries)
            bib_index = _bibliography_index_from_entries(bib_entries)
            bibliography_index.extend(bib_index)
            concepts.extend(_extract_bibliography_titles(bib_index))

        artifact_blueprints: dict[str, dict] = {}
        artifact_content_memory: dict[str, dict] = {}
        for kind, tex_path in artifact_paths.items():
            relative_tex_path = self.workspace.relative(tex_path)
            source_documents.append(relative_tex_path)
            tex_text = self._safe_read_text(tex_path)
            inline_bibliography = _extract_thebibliography_entries(tex_text, relative_tex_path)
            bibliography_sources.update(inline_bibliography)
            bibliography_index.extend(_bibliography_index_from_entries(inline_bibliography))
            blueprint = _extract_tex_blueprint(tex_text, relative_tex_path, bibliography_sources)
            artifact_blueprints[kind] = blueprint
            content_memory = blueprint.get("content_memory", {})
            if content_memory:
                artifact_content_memory[kind] = content_memory
            section_titles.extend(blueprint.get("section_titles", []))
            citations.extend(blueprint.get("cited_keys", []))
            concepts.extend(blueprint.get("concepts", []))
            source_fragments.extend(blueprint.get("source_fragments", []))
            for key in ("coursename", "coursecode", "documentsubject", "documenttitle", "documentsubtitle"):
                value = blueprint.get(key)
                if value and key not in curricular_context:
                    curricular_context[key] = value

        if artifact_blueprints:
            tex_blueprint["artifacts"] = artifact_blueprints
            preferred_key = "reporte" if "reporte" in artifact_blueprints else next(iter(artifact_blueprints.keys()))
            tex_blueprint["primary"] = artifact_blueprints.get(preferred_key, {})
            tex_content_memory["artifacts"] = artifact_content_memory
            tex_content_memory["primary"] = artifact_content_memory.get(preferred_key, {})
            tex_content_memory["bibliography_sources"] = bibliography_sources

        enriched["curricular_context"] = curricular_context
        enriched["tex_blueprint"] = tex_blueprint
        enriched["tex_content_memory"] = tex_content_memory
        enriched["source_documents"] = _dedupe_lines(source_documents)
        enriched["source_fragments"] = _dedupe_lines(source_fragments)
        enriched["concepts"] = _dedupe_lines(concepts)
        enriched["section_titles"] = _dedupe_lines(section_titles)
        enriched["citations"] = _dedupe_lines(citations)
        enriched["bibliography_index"] = _dedupe_lines(bibliography_index)
        enriched["sources"] = _dedupe_lines(enriched.get("sources", []) + enriched["source_documents"])
        enriched["editorial_dna"] = _synthesize_editorial_dna(enriched, enriched.get("editorial_dna", {}))
        enriched["schema_version"] = SCHEMA_VERSION
        return enriched

    def _safe_read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def render_memory_markdown(self, scope: EditorialScope, payload: dict | None = None) -> str:
        data = self._normalize_memory(payload or self.get_memory(scope.key))
        lines = [
            "# Memoria editorial AulaTeX",
            "",
            f"- Alcance: {scope.level}",
            f"- Etiqueta: {scope.label}",
            f"- Ruta: {scope.relative_path}",
            f"- Compresion: {data['compression'].get('method', 'union-dedupe')}",
            f"- Sin regresion: {'si' if data['compression'].get('lossless', True) else 'no'}",
            f"- Secciones fijadas: {', '.join(data.get('locked_sections', [])) or 'ninguna'}",
            "",
        ]
        for section in MEMORY_SECTIONS:
            items = data.get(section, [])
            if not items:
                continue
            lines.append(f"## {section}")
            lines.append("")
            lines.extend(f"- {item}" for item in items)
            lines.append("")
        editorial_dna = _normalize_editorial_dna(data.get("editorial_dna", {}))
        if editorial_dna:
            lines.append("## editorial_dna")
            lines.append("")
            essence = editorial_dna.get("essence", [])
            if essence:
                lines.append("### esencia")
                lines.extend(f"- {item}" for item in essence[:12])
                lines.append("")
            reason = editorial_dna.get("reason_for_being", [])
            if reason:
                lines.append("### razon_de_ser")
                lines.extend(f"- {item}" for item in reason[:12])
                lines.append("")
            styles = editorial_dna.get("style_markers", [])
            if styles:
                lines.append("### identidad_estilistica")
                lines.extend(f"- {item}" for item in styles[:12])
                lines.append("")
            patterns = editorial_dna.get("argumentative_patterns", [])
            if patterns:
                lines.append("### patrones_argumentativos")
                lines.extend(f"- {item}" for item in patterns[:12])
                lines.append("")
            graph = editorial_dna.get("knowledge_graph", {})
            if graph:
                lines.append("### grafo_de_conocimiento")
                lines.append(f"- Conceptos: {len(graph.get('concepts', []))}")
                lines.append(f"- Citas: {len(graph.get('citations', []))}")
                lines.append(f"- Relaciones reforzadas: {len(graph.get('relations', []))}")
                lines.append(f"- Evidencias: {len(graph.get('evidence', []))}")
                lines.append("")
        tex_primary = data.get("tex_content_memory", {}).get("primary", {})
        if tex_primary:
            lines.append("## adn_tex")
            lines.append("")
            lines.append(f"- Artefacto primario: `{tex_primary.get('relative_path', '')}`")
            lines.append(f"- Caracteres LaTeX preservados: {tex_primary.get('raw_latex_chars', 0)}")
            lines.append(f"- Bloques/parrafos indexados: {len(tex_primary.get('paragraph_map', []))}")
            lines.append(f"- Claves citadas: {', '.join(tex_primary.get('all_cited_keys', [])) or 'ninguna'}")
            missing = tex_primary.get("missing_bibliography_keys", [])
            lines.append(f"- Claves sin referencia: {', '.join(missing) if missing else 'ninguna'}")
            lines.append("")
        return "\n".join(lines)

    def summarize_for_scope(self, scope_key: str, include_ancestors: bool = True, max_chars: int = 6000) -> str:
        by_key, _children = self.workspace.editorial_scope_index()
        scope = by_key.get(scope_key)
        if scope is None:
            return ""
        scope_keys = [scope_key]
        if include_ancestors:
            scope_keys.extend(item.key for item in self.workspace.scope_chain(scope_key)[1:])

        chunks: list[str] = []
        for key in scope_keys:
            current = by_key.get(key)
            if current is None:
                continue
            memory = self.get_memory(key)
            if all(not value for value in memory.values() if isinstance(value, list)):
                continue
            chunk = self.render_memory_markdown(current, memory)
            current_size = sum(len(item) for item in chunks)
            if current_size + len(chunk) > max_chars:
                if not chunks:
                    chunks.append(chunk[:max_chars])
                break
            chunks.append(chunk)
        return "\n\n".join(chunks)

    def lock_scope_sections(self, scope_key: str, sections: list[str] | None = None) -> dict:
        by_key, _children = self.workspace.editorial_scope_index()
        scope = by_key.get(scope_key)
        if scope is None:
            return self._empty_memory()
        payload = self.get_memory(scope_key)
        if sections is None:
            sections = [section for section in MEMORY_SECTIONS if payload.get(section)]
        locked = set(payload.get("locked_sections", []))
        locked.update(section for section in sections if section in MEMORY_SECTIONS)
        payload["locked_sections"] = sorted(locked)
        self.save_memory(scope, payload, scope_key)
        return payload

    def unlock_scope_sections(self, scope_key: str, sections: list[str] | None = None) -> dict:
        by_key, _children = self.workspace.editorial_scope_index()
        scope = by_key.get(scope_key)
        if scope is None:
            return self._empty_memory()
        payload = self.get_memory(scope_key)
        locked = set(payload.get("locked_sections", []))
        if sections is None:
            locked.clear()
        else:
            locked.difference_update(section for section in sections if section in MEMORY_SECTIONS)
        payload["locked_sections"] = sorted(locked)
        self.save_memory(scope, payload, scope_key)
        return payload

    def render_metrics_markdown(self, scope_keys: list[str] | tuple[str, ...]) -> str:
        if not self.diagnostics_enabled:
            return "# Diagnóstico desactivado\n\n- Ejecuta AulaTeX con --diagnostics o define AULATEX_ENABLE_DIAGNOSTIC_METRICS=1 para medir desempeño.\n"
        keys = [key for key in scope_keys if key]
        if not keys:
            return "# Metricas\n\n- Sin scopes seleccionados.\n"
        placeholders = ", ".join("?" for _ in keys)
        with self._connect() as conn:
            by_engine = conn.execute(
                f"""
                SELECT engine, COUNT(*) AS calls, SUM(CASE WHEN ok = 1 THEN 1 ELSE 0 END) AS ok_calls,
                       AVG(response_chars) AS avg_chars, MAX(response_chars) AS max_chars
                FROM cycles
                WHERE scope_key IN ({placeholders})
                GROUP BY engine
                ORDER BY engine
                """,
                tuple(keys),
            ).fetchall()
            by_cycle = conn.execute(
                f"""
                SELECT cycle_index, COUNT(*) AS calls, SUM(CASE WHEN ok = 1 THEN 1 ELSE 0 END) AS ok_calls,
                       AVG(response_chars) AS avg_chars
                FROM cycles
                WHERE scope_key IN ({placeholders})
                GROUP BY cycle_index
                ORDER BY cycle_index
                """,
                tuple(keys),
            ).fetchall()
        lines = ["# Metricas del orquestador", ""]
        if by_engine:
            lines.extend(["## Por motor", ""])
            for row in by_engine:
                lines.append(
                    f"- {row['engine']}: llamadas={row['calls']}, ok={row['ok_calls']}, promedio_chars={int(row['avg_chars'] or 0)}, max_chars={int(row['max_chars'] or 0)}"
                )
            lines.append("")
        if by_cycle:
            lines.extend(["## Por ciclo", ""])
            for row in by_cycle:
                lines.append(
                    f"- Ciclo {row['cycle_index']}: llamadas={row['calls']}, ok={row['ok_calls']}, promedio_chars={int(row['avg_chars'] or 0)}"
                )
            lines.append("")
        if len(lines) == 2:
            lines.append("- Aun no hay ejecuciones registradas para este plan.")
        return "\n".join(lines)

    def _empty_memory(self) -> dict:
        payload = {section: [] for section in MEMORY_SECTIONS}
        for field in MEMORY_STRING_FIELDS:
            payload[field] = ""
        for field in MEMORY_LIST_FIELDS:
            payload[field] = []
        for field in MEMORY_DICT_FIELDS:
            payload[field] = {}
        payload["locked_sections"] = []
        payload["compression"] = {"method": "union-dedupe", "lossless": True}
        payload["schema_version"] = SCHEMA_VERSION
        return payload

    def _normalize_memory(self, payload: dict) -> dict:
        normalized = self._empty_memory()
        if not isinstance(payload, dict):
            return normalized
        for field in MEMORY_STRING_FIELDS:
            value = payload.get(field, "")
            normalized[field] = value.strip() if isinstance(value, str) else ""
        for section in MEMORY_SECTIONS:
            items = payload.get(section, [])
            if isinstance(items, str):
                items = [items]
            if isinstance(items, list):
                normalized[section] = _dedupe_lines(items)
        for field in MEMORY_LIST_FIELDS:
            items = payload.get(field, [])
            if isinstance(items, str):
                items = [items]
            if isinstance(items, list):
                normalized[field] = _dedupe_lines(items)
        for field in MEMORY_DICT_FIELDS:
            value = payload.get(field, {})
            if isinstance(value, dict):
                normalized[field] = _normalize_editorial_dna(value) if field == "editorial_dna" else value
        locked_sections = payload.get("locked_sections", [])
        if isinstance(locked_sections, str):
            locked_sections = [locked_sections]
        if isinstance(locked_sections, list):
            normalized["locked_sections"] = sorted(
                section for section in _dedupe_lines(locked_sections) if section in MEMORY_SECTIONS
            )
        compression = payload.get("compression", {})
        if isinstance(compression, dict):
            normalized["compression"] = {
                "method": compression.get("method", "union-dedupe"),
                "lossless": bool(compression.get("lossless", True)),
            }
        try:
            normalized["schema_version"] = max(SCHEMA_VERSION, int(payload.get("schema_version", SCHEMA_VERSION)))
        except (TypeError, ValueError):
            normalized["schema_version"] = SCHEMA_VERSION
        return normalized


class EditorialMemoryBuilder:
    def __init__(
        self,
        workspace: AulaTeXWorkspace | None = None,
        llm_bridge: AulaTeXLLMClient | None = None,
        store: EditorialMemoryStore | None = None,
    ) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.llm = llm_bridge or AulaTeXLLMClient()
        self.store = store or EditorialMemoryStore(self.workspace)
        self.memory_fusion = MemoryFusionEngine()

    def build(
        self,
        request: EditorialMemoryRequest,
        progress: Callable[[EditorialMemoryEvent], None] | None = None,
        cancel_event: Event | None = None,
    ) -> EditorialMemoryBuildResult:
        run_id = self.workspace.timestamp()
        run_dir = self.store.temp_root / "runs" / f"{run_id}-editorial-memory"
        run_dir.mkdir(parents=True, exist_ok=True)

        by_key, children = self.workspace.editorial_scope_index()
        source_scope = by_key.get(request.source_scope_key)
        if source_scope is None:
            raise ValueError(f"Scope no encontrado: {request.source_scope_key}")
        if request.build_level not in EDITORIAL_LEVELS:
            raise ValueError(f"Nivel editorial invalido: {request.build_level}")

        engines = self._normalize_engines(request.engines)
        self.store.start_run(request, engines, run_id)
        for scope in by_key.values():
            self.store.upsert_scope(scope)

        full_plan = self._plan_scopes(source_scope, request.build_level, request.propagation_mode, by_key, children)
        scope_offset = max(0, int(request.scope_offset))
        scope_limit = max(0, int(request.scope_limit))
        if scope_offset >= len(full_plan):
            raise ValueError(
                f"El desplazamiento del lote ({scope_offset}) rebasa el plan calculado ({len(full_plan)} scopes)"
            )
        plan = full_plan[scope_offset:]
        if scope_limit:
            plan = plan[:scope_limit]
        if not plan:
            raise ValueError("El lote seleccionado no contiene scopes para construir memoria editorial")
        total = max(1, len(plan) * max(1, int(request.iterations)) * len(engines))
        current = 0
        cycle_logs: list[dict] = []
        overall_ok = True
        cancelled = False

        self._emit(progress, EditorialMemoryEvent("start", f"Plan editorial: {', '.join(scope.label for scope in plan)}", 0, total, source_scope.key))

        for scope in plan:
            if self._is_cancelled(cancel_event):
                cancelled = True
                break
            for cycle_index in range(1, max(1, int(request.iterations)) + 1):
                cycle_markdowns: list[Path] = []
                if self._is_cancelled(cancel_event):
                    cancelled = True
                    break
                for engine in engines:
                    if self._is_cancelled(cancel_event):
                        cancelled = True
                        break
                    current += 1
                    prompt = self._build_prompt(source_scope, scope, cycle_index, request, by_key, engine)
                    self._emit(
                        progress,
                        EditorialMemoryEvent(
                            "progress",
                            f"{scope.label} | ciclo {cycle_index} | {engine}",
                            current,
                            total,
                            scope.key,
                            engine,
                            cycle_index,
                        ),
                    )
                    engine_prefix = ENGINE_ENV_PREFIX.get(engine, "")
                    engine_token_cap_name = f"AULATEX_MAX_OUTPUT_TOKENS_{engine_prefix}" if engine_prefix else ""
                    engine_max_tokens = int(os.environ.get(engine_token_cap_name, request.max_tokens))
                    result = self.llm.call(
                        engine,
                        prompt,
                        max_tokens=min(int(request.max_tokens), engine_max_tokens),
                        timeout_seconds=max(5, int(request.timeout_seconds)),
                    )
                    response_text = result.text if result.ok else result.error
                    self.store.record_cycle(
                        run_id=run_id,
                        scope_key=scope.key,
                        cycle_index=cycle_index,
                        engine=result.engine,
                        ok=result.ok,
                        response_text=response_text,
                    )
                    current_memory = self.store.get_memory(scope.key)
                    candidate = self._parse_response(response_text, source_scope, scope, engine, cycle_index)
                    merged = self._merge_non_regressive(current_memory, candidate, source_scope, scope)
                    self.store.save_memory(scope, merged, request.source_scope_key)
                    cycle_logs.append(
                        {
                            "scope_key": scope.key,
                            "scope_level": scope.level,
                            "cycle": cycle_index,
                            "engine": result.engine,
                            "ok": result.ok,
                            "chars": len(response_text),
                        }
                    )
                    safe_scope_slug = self.store._safe_scope_slug(scope.key)
                    safe_engine = re.sub(r"[^A-Za-z0-9_.-]+", "_", result.engine).strip("._")
                    scope_file = run_dir / f"{current:04d}-{safe_scope_slug}-{safe_engine}.md"
                    scope_file.write_text(response_text, encoding="utf-8")
                    cycle_markdowns.append(scope_file)
                    if not result.ok:
                        overall_ok = False
                    self._emit(
                        progress,
                        EditorialMemoryEvent(
                            "result",
                            f"{result.engine}: {'OK' if result.ok else 'ERROR'} ({len(response_text)} chars)",
                            current,
                            total,
                            scope.key,
                            result.engine,
                            cycle_index,
                        ),
                    )

                if cycle_markdowns:
                    fused_dir = run_dir / "fused-memory"
                    fused_dir.mkdir(parents=True, exist_ok=True)
                    safe_scope_slug = self.store._safe_scope_slug(scope.key)
                    fused_output = fused_dir / f"{safe_scope_slug}--cycle-{cycle_index:03d}.json"
                    self.memory_fusion.fuse_markdown_files(cycle_markdowns, fused_output)
                if cancelled:
                    break
            if cancelled:
                break

        manifest = {
            "run_id": run_id,
            "source_scope_key": request.source_scope_key,
            "build_level": request.build_level,
            "propagation_mode": request.propagation_mode,
            "iterations": int(request.iterations),
            "engines": engines,
            "timeout_seconds": max(5, int(request.timeout_seconds)),
            "scope_offset": scope_offset,
            "scope_limit": scope_limit,
            "full_plan_scope_count": len(full_plan),
            "batch_scope_count": len(plan),
            "built_scopes": [scope.key for scope in plan],
            "cycles": cycle_logs,
            "ok": overall_ok and not cancelled,
            "cancelled": cancelled,
        }
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        self.store.finish_run(run_id, overall_ok and not cancelled)
        self.workspace.append_bitacora(run_id, "memoria-editorial", manifest)
        if cancelled:
            self._emit(progress, EditorialMemoryEvent("cancelled", f"Memoria editorial cancelada en {run_dir}", current, total, source_scope.key))
        else:
            self._emit(progress, EditorialMemoryEvent("done", f"Memoria editorial cerrada en {run_dir}", total, total, source_scope.key))
        return EditorialMemoryBuildResult(run_id, run_dir, manifest_path, tuple(scope.key for scope in plan), overall_ok and not cancelled, cancelled)

    def plan_scopes(
        self,
        source_scope_key: str,
        build_level: str,
        propagation_mode: str,
    ) -> list[EditorialScope]:
        by_key, children = self.workspace.editorial_scope_index()
        source_scope = by_key.get(source_scope_key)
        if source_scope is None:
            return []
        return self._plan_scopes(source_scope, build_level, propagation_mode, by_key, children)

    def _normalize_engines(self, engines: list[str] | tuple[str, ...]) -> list[str]:
        from .config import MODEL_ROUTER_ENGINE, restrict_engines_to_available

        selected = [engine for engine in restrict_engines_to_available(engines) if engine in self.llm.engines()]
        if not selected:
            selected = [MODEL_ROUTER_ENGINE]
        return sorted(selected, key=lambda engine: (ENGINE_PRIORITY.get(engine, 999), engine))

    def _plan_scopes(
        self,
        source_scope: EditorialScope,
        build_level: str,
        propagation_mode: str,
        by_key: dict[str, EditorialScope],
        children: dict[str, list[EditorialScope]],
    ) -> list[EditorialScope]:
        allowed = set(PROPAGATION_MODES)
        mode = propagation_mode if propagation_mode in allowed else "ascendente"
        order = {level: index for index, level in enumerate(EDITORIAL_LEVELS)}

        if mode in {"local", "lateral"}:
            build_level = source_scope.level
        elif mode in {"ascendente", "ascendente-exhaustivo", "recursivo"} and order[build_level] < order[source_scope.level]:
            raise ValueError("El nivel de construccion no puede ser mas profundo que el origen seleccionado en propagacion ascendente")
        elif mode == "descendente" and order[build_level] > order[source_scope.level]:
            raise ValueError("El nivel de construccion no puede ser mas alto que el origen seleccionado en propagacion descendente")

        plan: list[EditorialScope] = []
        seen: set[str] = set()

        if mode == "local":
            self._append_scope(plan, seen, source_scope)
            return plan

        if mode == "lateral":
            self._append_scope(plan, seen, source_scope)
            parent = by_key.get(source_scope.parent_key)
            if parent is not None:
                for sibling in children.get(parent.key, []):
                    if sibling.level == source_scope.level:
                        self._append_scope(plan, seen, sibling)
            return plan

        if mode == "descendente":
            self._append_descendants_preorder(plan, seen, source_scope, children, order, order[build_level])
            return plan

        if mode == "bidireccional" and order[build_level] < order[source_scope.level]:
            self._append_descendants_preorder(plan, seen, source_scope, children, order, order[build_level])
            return plan

        current = source_scope
        while current is not None:
            if mode == "recursivo":
                self._append_subtree_postorder(plan, seen, current, children)
            elif mode == "bidireccional":
                self._append_subtree_postorder(plan, seen, current, children)
            else:
                self._append_scope(plan, seen, current)

            if mode == "ascendente-exhaustivo":
                parent = by_key.get(current.parent_key)
                if parent is not None:
                    for sibling in children.get(parent.key, []):
                        self._append_scope(plan, seen, sibling)

            if current.level == build_level:
                break
            if mode == "local":
                break
            next_scope = by_key.get(current.parent_key)
            current = next_scope
        return plan

    def _append_scope(self, plan: list[EditorialScope], seen: set[str], scope: EditorialScope) -> None:
        if scope.key in seen:
            return
        plan.append(scope)
        seen.add(scope.key)

    def _append_subtree_postorder(
        self,
        plan: list[EditorialScope],
        seen: set[str],
        scope: EditorialScope,
        children: dict[str, list[EditorialScope]],
    ) -> None:
        for child in children.get(scope.key, []):
            self._append_subtree_postorder(plan, seen, child, children)
        self._append_scope(plan, seen, scope)

    def _append_descendants_preorder(
        self,
        plan: list[EditorialScope],
        seen: set[str],
        scope: EditorialScope,
        children: dict[str, list[EditorialScope]],
        order: dict[str, int],
        build_order: int,
    ) -> None:
        self._append_scope(plan, seen, scope)
        if order[scope.level] == build_order:
            return
        for child in children.get(scope.key, []):
            if order[child.level] < build_order:
                continue
            self._append_descendants_preorder(plan, seen, child, children, order, build_order)

    def describe_scope_transfer(
        self,
        source_scope_key: str,
        target_scope_key: str,
        propagation_mode: str,
    ) -> dict:
        by_key, _children = self.workspace.editorial_scope_index()
        source_scope = by_key.get(source_scope_key)
        target_scope = by_key.get(target_scope_key)
        if source_scope is None or target_scope is None:
            return {"relation": "desconocida", "objective": "indeterminado", "strategy": "indeterminada"}
        current_memory = self.store.get_memory(target_scope.key)
        return _transfer_profile(source_scope, target_scope, propagation_mode, current_memory, by_key)

    def _build_prompt(
        self,
        source_scope: EditorialScope,
        target_scope: EditorialScope,
        cycle_index: int,
        request: EditorialMemoryRequest,
        by_key: dict[str, EditorialScope],
        engine: str,
    ) -> str:
        current_memory = self.store.get_memory(target_scope.key)
        source_memory = self.store.get_memory(source_scope.key)
        parent_memory = ""
        if target_scope.parent_key and target_scope.parent_key in by_key:
            parent_memory = self.store.summarize_for_scope(target_scope.parent_key, include_ancestors=True, max_chars=2500)
        historical_dna = self._load_historical_dna(target_scope, engine=engine)
        local_context = self.workspace.context_summary(target_scope.relative_path, max_chars=4000)
        memory_json = json.dumps(_memory_prompt_view(current_memory), ensure_ascii=False, indent=2)
        source_memory_json = json.dumps(_memory_prompt_view(source_memory), ensure_ascii=False, indent=2)
        transfer = _transfer_profile(source_scope, target_scope, request.propagation_mode, current_memory, by_key)
        transfer_rules = "\n".join(f"- {item}" for item in transfer.get("rules", [])) or "- Preserva solo mejoras verificables."
        return (
            "Eres AulaTeX y estas consolidando memoria editorial persistente para una suite academica en LaTeX. "
            "Debes preservar todo lo valido, agregar solo mejoras verificables y nunca eliminar reglas utiles previas. "
            "Tu tarea no es solo resumir reglas: debes reforzar el ADN editorial del nodo como cerebro persistente. "
            "La compresion debe ser lossless por deduplicacion, no por recorte. Responde solo JSON valido.\n\n"
            f"Origen: {source_scope.level} | {source_scope.key}\n"
            f"Destino: {target_scope.level} | {target_scope.key}\n"
            f"Propagacion: {request.propagation_mode}\n"
            f"Relacion entre nodos: {transfer.get('relation', 'desconocida')}\n"
            f"Objetivo editorial: {transfer.get('objective', 'refuerzo')}\n"
            f"Estrategia: {transfer.get('strategy', 'progresiva')}\n"
            f"Ciclo: {cycle_index}\n\n"
            "Esquema requerido:\n"
            "{\n"
            '  "summary": ["..."],\n'
            '  "identity_rules": ["..."],\n'
            '  "structure_rules": ["..."],\n'
            '  "activity_rules": ["..."],\n'
            '  "quality_gates": ["..."],\n'
            '  "latex_rules": ["..."],\n'
            '  "bibliography_rules": ["..."],\n'
            '  "propagation_hints": ["..."],\n'
            '  "open_questions": ["..."],\n'
            '  "editorial_dna": {\n'
            '    "identity": {"tone": ["..."], "institutional": ["..."], "curricular": ["..."]},\n'
            '    "essence": ["..."],\n'
            '    "reason_for_being": ["..."],\n'
            '    "style_markers": ["..."],\n'
            '    "argumentative_patterns": ["..."],\n'
            '    "knowledge_graph": {\n'
            '      "concepts": ["..."],\n'
            '      "citations": ["..."],\n'
            '      "relations": [{"source": "...", "target": "...", "kind": "supports|contrasts|depends_on|develops", "justification": "..."}],\n'
            '      "evidence": ["..."]\n'
            '    },\n'
            '    "reinforcement_log": ["..."]\n'
            '  }\n'
            "}\n\n"
            "Reglas: usa frases cortas, accionables y sin duplicados; marca supuestos; no inventes fuentes; no copies LaTeX completo; refuerza conexiones, ideas, conceptos, patrones argumentativos e identidad estilistica.\n\n"
            f"Reglas de transferencia para este salto:\n{transfer_rules}\n\n"
            f"Memoria del origen:\n{source_memory_json}\n\n"
            f"Memoria actual del destino:\n{memory_json}\n\n"
            f"DNA historico fusionado del nodo:\n{historical_dna}\n\n"
            f"Memoria heredada:\n{parent_memory or 'Sin memoria heredada aun.'}\n\n"
            f"Contexto local:\n{local_context}\n"
        )

    def _load_historical_dna(self, scope: EditorialScope, *, engine: str = "") -> str:
        runs_roots = [self.store.root / "runs", self.store.temp_root / "runs"]
        legacy_pattern = f"*{scope.key.replace('/', '__')}*.md"
        safe_scope_slug = self.store._safe_scope_slug(scope.key)
        safe_pattern = f"*{safe_scope_slug}*.md"
        files = sorted({
            path
            for runs_root in runs_roots
            if runs_root.exists()
            for path in (*runs_root.rglob(legacy_pattern), *runs_root.rglob(safe_pattern))
        })
        if not files:
            return "Sin DNA historico fusionado aun."

        dna_dir = self.workspace.repo_root / ".build" / "editorial-dna"
        dna_dir.mkdir(parents=True, exist_ok=True)
        dna_path = dna_dir / f"{safe_scope_slug}--historical-dna.json"
        try:
            fused = self.memory_fusion.fuse_markdown_files(files, dna_path)
        except Exception:
            return "DNA historico no disponible por error de fusion."

        prefix = ENGINE_ENV_PREFIX.get(engine, "")
        engine_env_name = f"AULATEX_HISTORICAL_DNA_PROMPT_CHARS_{prefix}" if prefix else ""
        max_chars = int(os.environ.get(engine_env_name, os.environ.get("AULATEX_HISTORICAL_DNA_PROMPT_CHARS", "120000")))
        compact = []
        used_chars = 0
        for cluster in fused.get("clusters", []):
            item = {
                "canonical": cluster.get("canonical", ""),
                "frequency": cluster.get("frequency", 0),
                "section": cluster.get("section", ""),
            }
            item_size = len(json.dumps(item, ensure_ascii=False)) + 4
            if compact and used_chars + item_size > max_chars:
                break
            compact.append(item)
            used_chars += item_size
        return json.dumps(
            {
                "cluster_count": fused.get("cluster_count", 0),
                "included_cluster_count": len(compact),
                "prompt_char_budget": max_chars,
                "truncated_for_prompt": len(compact) < int(fused.get("cluster_count", 0) or 0),
                "top_clusters": compact,
            },
            ensure_ascii=False,
            indent=2,
        )

    def _parse_response(
        self,
        response_text: str,
        source_scope: EditorialScope,
        target_scope: EditorialScope,
        engine: str,
        cycle_index: int,
    ) -> dict:
        payload = _extract_first_json(response_text)
        if payload is None:
            fallback_lines = _extract_bullets(response_text)
            return {
                "summary": fallback_lines[:8] or [f"Salida sin JSON parseable desde {engine} para {target_scope.label}"],
                "identity_rules": [f"Fuente provisional: {engine} desde {source_scope.label}"],
                "structure_rules": [],
                "activity_rules": [],
                "quality_gates": ["Revisar respuesta no estructurada antes de aplicar aguas abajo."],
                "latex_rules": [],
                "bibliography_rules": [],
                "propagation_hints": [f"Ciclo {cycle_index} necesita normalizacion manual si se reutiliza."],
                "open_questions": [],
                "editorial_dna": {
                    "essence": fallback_lines[:4],
                    "reinforcement_log": [f"Retroalimentacion no estructurada recibida desde {engine} en ciclo {cycle_index}."] if fallback_lines else [],
                },
            }
        return payload

    def _merge_non_regressive(
        self,
        current: dict,
        candidate: dict,
        source_scope: EditorialScope,
        target_scope: EditorialScope,
    ) -> dict:
        merged = self.store._normalize_memory(current)
        candidate_normalized = self.store._normalize_memory(candidate)
        locked_sections = set(merged.get("locked_sections", []))
        for section in MEMORY_SECTIONS:
            if section in locked_sections:
                merged[section] = _dedupe_lines(merged.get(section, []))
                continue
            merged[section] = _dedupe_lines(merged.get(section, []) + candidate_normalized.get(section, []))
        merged["editorial_dna"] = _merge_editorial_dna(
            merged.get("editorial_dna", {}),
            candidate_normalized.get("editorial_dna", {}),
        )
        merged["editorial_dna"] = _apply_feedback_reinforcement(merged["editorial_dna"], candidate_normalized)
        merged["sources"] = _dedupe_lines(
            merged.get("sources", [])
            + candidate_normalized.get("sources", [])
            + [source_scope.key, target_scope.key]
        )
        merged["locked_sections"] = sorted(locked_sections)
        merged["compression"] = {"method": "union-dedupe", "lossless": True}
        merged["schema_version"] = max(SCHEMA_VERSION, int(candidate_normalized.get("schema_version", SCHEMA_VERSION) or SCHEMA_VERSION))
        return merged

    def _emit(self, callback: Callable[[EditorialMemoryEvent], None] | None, event: EditorialMemoryEvent) -> None:
        if callback is not None:
            callback(event)

    def _is_cancelled(self, cancel_event: Event | None) -> bool:
        return bool(cancel_event is not None and cancel_event.is_set())


def _ancestor_keys(scope: EditorialScope, by_key: dict[str, EditorialScope]) -> list[str]:
    keys: list[str] = []
    current = by_key.get(scope.parent_key)
    while current is not None:
        keys.append(current.key)
        current = by_key.get(current.parent_key)
    return keys


def _scope_relation(source_scope: EditorialScope, target_scope: EditorialScope, by_key: dict[str, EditorialScope]) -> str:
    if source_scope.key == target_scope.key:
        return "mismo-nodo"
    source_ancestors = set(_ancestor_keys(source_scope, by_key))
    target_ancestors = set(_ancestor_keys(target_scope, by_key))
    if target_scope.key in source_ancestors:
        return "ancestro"
    if source_scope.key in target_ancestors:
        return "descendiente"
    if source_scope.parent_key and source_scope.parent_key == target_scope.parent_key and source_scope.level == target_scope.level:
        return "hermano"
    if source_scope.level == target_scope.level:
        return "lateral-transversal"
    return "transversal"


def _has_substantive_memory(memory: dict) -> bool:
    if any(memory.get(section) for section in MEMORY_SECTIONS):
        return True
    editorial_dna = memory.get("editorial_dna", {}) if isinstance(memory.get("editorial_dna", {}), dict) else {}
    if editorial_dna.get("essence") or editorial_dna.get("knowledge_graph") or editorial_dna.get("writing_memory"):
        return True
    return False


def _transfer_profile(
    source_scope: EditorialScope,
    target_scope: EditorialScope,
    propagation_mode: str,
    target_memory: dict,
    by_key: dict[str, EditorialScope],
) -> dict:
    relation = _scope_relation(source_scope, target_scope, by_key)
    target_has_memory = _has_substantive_memory(target_memory)

    if relation == "mismo-nodo":
        return {
            "relation": relation,
            "objective": "canonizacion-local",
            "strategy": "constructiva y de preservacion total",
            "rules": [
                "Preserva la redacción, el TEX reconstruible y el ADN editorial completo del nodo.",
                "Refuerza conceptos, relaciones, estilo y patrones argumentativos usando solo fuentes locales verificables.",
                "No elimines memoria útil previa; compacta por unión y deduplicación.",
            ],
        }

    if relation == "ancestro":
        return {
            "relation": relation,
            "objective": "abstraccion-ascendente",
            "strategy": "progresiva y sintetica",
            "rules": [
                "Eleva patrones, identidad, conceptos y relaciones reutilizables desde el hijo hacia el ancestro.",
                "No copies redacción literal completa de un hijo dentro del ancestro; sintetiza patrones editoriales y señales de conocimiento.",
                "Conserva trazabilidad conceptual, citas recurrentes y reglas de calidad transferibles.",
            ],
        }

    if relation == "descendiente":
        return {
            "relation": relation,
            "objective": "refuerzo-descendente" if target_has_memory else "construccion-descendente",
            "strategy": "constructiva" if not target_has_memory else "progresiva con refuerzo local",
            "rules": [
                "Transfiere identidad, estilo, gates de calidad, estructura reusable y conceptos marco del padre al hijo.",
                "Si el hijo no tiene memoria suficiente, construye un andamiaje editorial inicial sin inventar fuentes ni citas específicas.",
                "Si el hijo ya tiene memoria, refuérzalo sin sobrescribir su redacción local ni su evidencia propia.",
            ],
        }

    if relation in {"hermano", "lateral-transversal"}:
        return {
            "relation": relation,
            "objective": "refuerzo-lateral" if target_has_memory else "transferencia-lateral-constructiva",
            "strategy": "progresiva por analogia controlada",
            "rules": [
                "Transfiere solo patrones reutilizables: identidad institucional, estructura, calidad, conceptos y relaciones recurrentes.",
                "No copies redacción literal, conclusiones específicas ni bibliografía exclusiva de un hermano hacia otro.",
                "Cuando falten datos locales, deja preguntas abiertas o estructura base en vez de inventar contenido concreto.",
            ],
        }

    return {
        "relation": relation,
        "objective": "sincronizacion-transversal",
        "strategy": "progresiva y conservadora",
        "rules": [
            "Comparte solo abstracciones editoriales estables entre nodos no equivalentes.",
            "Prioriza identidad, estructura reusable, gates de calidad y grafo conceptual; evita transferir redacción literal.",
            "Si el destino está vacío, crea un cerebro editorial mínimo y deja abiertos los vacíos de contexto local.",
        ],
    }


def _dedupe_lines(items: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for item in items:
        if not isinstance(item, str):
            continue
        value = re.sub(r"\s+", " ", item).strip(" -\t\r\n")
        if not value:
            continue
        marker = value.lower()
        if marker in seen:
            continue
        seen.add(marker)
        normalized.append(value)
    return normalized


def _dedupe_dict_items(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    normalized: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        marker = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if marker in seen:
            continue
        seen.add(marker)
        normalized.append(item)
    return normalized


def _normalize_weight_map(value: object) -> dict[str, int]:
    normalized: dict[str, int] = {}
    if not isinstance(value, dict):
        return normalized
    for key, raw in value.items():
        if not isinstance(key, str):
            continue
        label = re.sub(r"\s+", " ", key).strip()
        if not label:
            continue
        try:
            weight = max(1, int(raw))
        except (TypeError, ValueError):
            continue
        normalized[label] = max(normalized.get(label, 0), weight)
    return normalized


def _normalize_relation_items(items: object) -> list[dict]:
    normalized: list[dict] = []
    if not isinstance(items, list):
        return normalized
    for item in items:
        if not isinstance(item, dict):
            continue
        source = re.sub(r"\s+", " ", str(item.get("source", ""))).strip()
        target = re.sub(r"\s+", " ", str(item.get("target", ""))).strip()
        if not source or not target:
            continue
        relation = {
            "source": source,
            "target": target,
            "kind": re.sub(r"\s+", " ", str(item.get("kind", "association"))).strip() or "association",
            "weight": max(1, int(item.get("weight", 1) or 1)),
        }
        justification = re.sub(r"\s+", " ", str(item.get("justification", ""))).strip()
        if justification:
            relation["justification"] = justification
        evidence = item.get("evidence", [])
        if isinstance(evidence, str):
            evidence = [evidence]
        if isinstance(evidence, list):
            relation["evidence"] = _dedupe_lines([str(part) for part in evidence])
        normalized.append(relation)
    return _dedupe_dict_items(normalized)


def _deep_merge_dicts(base: dict, incoming: dict) -> dict:
    merged = dict(base or {})
    for key, value in (incoming or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dicts(merged[key], value)
        elif isinstance(value, list) and isinstance(merged.get(key), list):
            merged[key] = _dedupe_lines([str(item) for item in merged[key] + value])
        elif value not in (None, "", [], {}):
            merged[key] = value
    return merged


def _normalize_editorial_dna(payload: dict | None) -> dict:
    if not isinstance(payload, dict):
        return {}
    knowledge_graph = payload.get("knowledge_graph", {}) if isinstance(payload.get("knowledge_graph", {}), dict) else {}
    normalized = {
        "identity": payload.get("identity", {}) if isinstance(payload.get("identity", {}), dict) else {},
        "essence": _dedupe_lines(payload.get("essence", []) if isinstance(payload.get("essence", []), list) else [payload.get("essence", "")]),
        "structure": payload.get("structure", {}) if isinstance(payload.get("structure", {}), dict) else {},
        "reason_for_being": _dedupe_lines(payload.get("reason_for_being", []) if isinstance(payload.get("reason_for_being", []), list) else [payload.get("reason_for_being", "")]),
        "style_markers": _dedupe_lines(payload.get("style_markers", []) if isinstance(payload.get("style_markers", []), list) else [payload.get("style_markers", "")]),
        "argumentative_patterns": _dedupe_lines(payload.get("argumentative_patterns", []) if isinstance(payload.get("argumentative_patterns", []), list) else [payload.get("argumentative_patterns", "")]),
        "reinforcement_log": _dedupe_lines(payload.get("reinforcement_log", []) if isinstance(payload.get("reinforcement_log", []), list) else [payload.get("reinforcement_log", "")]),
        "knowledge_graph": {
            "concepts": _dedupe_lines(knowledge_graph.get("concepts", []) if isinstance(knowledge_graph.get("concepts", []), list) else [knowledge_graph.get("concepts", "")]),
            "citations": _dedupe_lines(knowledge_graph.get("citations", []) if isinstance(knowledge_graph.get("citations", []), list) else [knowledge_graph.get("citations", "")]),
            "evidence": _dedupe_lines(knowledge_graph.get("evidence", []) if isinstance(knowledge_graph.get("evidence", []), list) else [knowledge_graph.get("evidence", "")]),
            "relations": _normalize_relation_items(knowledge_graph.get("relations", [])),
            "concept_weights": _normalize_weight_map(knowledge_graph.get("concept_weights", {})),
            "citation_weights": _normalize_weight_map(knowledge_graph.get("citation_weights", {})),
        },
        "writing_memory": [item for item in payload.get("writing_memory", []) if isinstance(item, dict)],
        "reconstructable_source": payload.get("reconstructable_source", "") if isinstance(payload.get("reconstructable_source", ""), str) else "",
    }
    return {key: value for key, value in normalized.items() if value not in ({}, [], "")}


def _merge_weight_maps(base: dict[str, int], incoming: dict[str, int]) -> dict[str, int]:
    merged = dict(base)
    for key, value in incoming.items():
        merged[key] = max(1, int(merged.get(key, 0))) + max(1, int(value)) if key in merged else max(1, int(value))
    return merged


def _merge_relation_lists(base: list[dict], incoming: list[dict]) -> list[dict]:
    merged: dict[tuple[str, str, str], dict] = {}
    for item in _normalize_relation_items(base) + _normalize_relation_items(incoming):
        key = (item.get("source", ""), item.get("target", ""), item.get("kind", "association"))
        existing = merged.get(key)
        if existing is None:
            merged[key] = dict(item)
            continue
        existing["weight"] = max(1, int(existing.get("weight", 1))) + max(1, int(item.get("weight", 1)))
        existing["evidence"] = _dedupe_lines(existing.get("evidence", []) + item.get("evidence", []))
        if item.get("justification") and not existing.get("justification"):
            existing["justification"] = item["justification"]
    return list(merged.values())


def _overlay_relation_lists(base: list[dict], incoming: list[dict]) -> list[dict]:
    merged: dict[tuple[str, str, str], dict] = {}
    for item in _normalize_relation_items(base) + _normalize_relation_items(incoming):
        key = (item.get("source", ""), item.get("target", ""), item.get("kind", "association"))
        existing = merged.get(key)
        if existing is None:
            merged[key] = dict(item)
            continue
        existing["weight"] = max(max(1, int(existing.get("weight", 1))), max(1, int(item.get("weight", 1))))
        existing["evidence"] = _dedupe_lines(existing.get("evidence", []) + item.get("evidence", []))
        if item.get("justification") and not existing.get("justification"):
            existing["justification"] = item["justification"]
    return list(merged.values())


def _merge_editorial_dna(current: dict | None, candidate: dict | None) -> dict:
    base = _normalize_editorial_dna(current)
    incoming = _normalize_editorial_dna(candidate)
    graph_base = base.get("knowledge_graph", {})
    graph_incoming = incoming.get("knowledge_graph", {})
    merged = {
        "identity": _deep_merge_dicts(base.get("identity", {}), incoming.get("identity", {})),
        "essence": _dedupe_lines(base.get("essence", []) + incoming.get("essence", [])),
        "structure": _deep_merge_dicts(base.get("structure", {}), incoming.get("structure", {})),
        "reason_for_being": _dedupe_lines(base.get("reason_for_being", []) + incoming.get("reason_for_being", [])),
        "style_markers": _dedupe_lines(base.get("style_markers", []) + incoming.get("style_markers", [])),
        "argumentative_patterns": _dedupe_lines(base.get("argumentative_patterns", []) + incoming.get("argumentative_patterns", [])),
        "reinforcement_log": _dedupe_lines(base.get("reinforcement_log", []) + incoming.get("reinforcement_log", [])),
        "knowledge_graph": {
            "concepts": _dedupe_lines(graph_base.get("concepts", []) + graph_incoming.get("concepts", [])),
            "citations": _dedupe_lines(graph_base.get("citations", []) + graph_incoming.get("citations", [])),
            "evidence": _dedupe_lines(graph_base.get("evidence", []) + graph_incoming.get("evidence", [])),
            "relations": _merge_relation_lists(graph_base.get("relations", []), graph_incoming.get("relations", [])),
            "concept_weights": _merge_weight_maps(graph_base.get("concept_weights", {}), graph_incoming.get("concept_weights", {})),
            "citation_weights": _merge_weight_maps(graph_base.get("citation_weights", {}), graph_incoming.get("citation_weights", {})),
        },
        "writing_memory": incoming.get("writing_memory", []) or base.get("writing_memory", []),
        "reconstructable_source": incoming.get("reconstructable_source", "") or base.get("reconstructable_source", ""),
    }
    return _normalize_editorial_dna(merged)


def _feedback_signal_lines(memory: dict) -> list[str]:
    lines: list[str] = []
    for key in ("summary", "identity_rules", "structure_rules", "activity_rules", "quality_gates", "open_questions"):
        value = memory.get(key, [])
        if isinstance(value, list):
            lines.extend(str(item) for item in value)
    editorial_dna = _normalize_editorial_dna(memory.get("editorial_dna", {}))
    lines.extend(editorial_dna.get("essence", []))
    lines.extend(editorial_dna.get("reason_for_being", []))
    lines.extend(editorial_dna.get("style_markers", []))
    lines.extend(editorial_dna.get("argumentative_patterns", []))
    graph = editorial_dna.get("knowledge_graph", {})
    lines.extend(graph.get("concepts", []))
    lines.extend(graph.get("citations", []))
    lines.extend(graph.get("evidence", []))
    return _dedupe_lines(lines)


def _is_brain_concept(value: str) -> bool:
    if not value or len(value) > 140:
        return False
    lowered = value.lower()
    if _is_operational_noise(value):
        return False
    if ":: fuente=" in lowered:
        return False
    if lowered.startswith("supuesto:"):
        return False
    return bool(re.search(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]", value))


def _is_operational_noise(value: str) -> bool:
    lowered = value.lower()
    markers = (
        "json parseable",
        "salida sin",
        "compresión",
        "compresion",
        "normalización",
        "normalizacion",
        "ciclo ",
        "control de calidad",
        "fuente provisional",
        "propagación",
        "propagacion",
        "deduplicación",
        "deduplicacion",
        "schema_version",
    )
    return any(marker in lowered for marker in markers)


def _concept_seed_from_line(value: str) -> str:
    text = re.sub(r"\s+", " ", value).strip(" -\t\r\n.;:")
    return text


def _candidate_concepts_from_feedback(memory: dict) -> list[str]:
    concepts: list[str] = []
    for line in _feedback_signal_lines(memory):
        concept = _concept_seed_from_line(line)
        if _is_brain_concept(concept):
            concepts.append(concept)
    return _dedupe_lines(concepts)


def _relation_items_from_concepts(concepts: list[str]) -> list[dict]:
    relations: list[dict] = []
    seeds = concepts[:6]
    for index, source in enumerate(seeds):
        for target in seeds[index + 1:index + 3]:
            relations.append(
                {
                    "source": source,
                    "target": target,
                    "kind": "cohesion",
                    "weight": 1,
                    "justification": "Coaparecen en la misma retroalimentación editorial.",
                }
            )
    return relations


def _apply_feedback_reinforcement(editorial_dna: dict, candidate_memory: dict) -> dict:
    dna = _normalize_editorial_dna(editorial_dna)
    graph = dna.setdefault("knowledge_graph", {})
    graph.setdefault("concepts", [])
    graph.setdefault("citations", [])
    graph.setdefault("evidence", [])
    graph.setdefault("relations", [])
    graph.setdefault("concept_weights", {})
    graph.setdefault("citation_weights", {})

    concept_signals = _candidate_concepts_from_feedback(candidate_memory)
    citation_signals = _dedupe_lines(candidate_memory.get("citations", [])) if isinstance(candidate_memory.get("citations", []), list) else []
    evidence_signals = _dedupe_lines(candidate_memory.get("summary", []) + candidate_memory.get("quality_gates", []))

    graph["concepts"] = _dedupe_lines(graph.get("concepts", []) + concept_signals)
    graph["citations"] = _dedupe_lines(graph.get("citations", []) + citation_signals)
    graph["evidence"] = _dedupe_lines(graph.get("evidence", []) + evidence_signals)
    graph["concept_weights"] = _merge_weight_maps(graph.get("concept_weights", {}), {item: 1 for item in concept_signals})
    graph["citation_weights"] = _merge_weight_maps(graph.get("citation_weights", {}), {item: 1 for item in citation_signals})
    graph["relations"] = _merge_relation_lists(graph.get("relations", []), _relation_items_from_concepts(concept_signals))

    dna["essence"] = _brain_lines(dna.get("essence", []) + concept_signals[:8], 24)
    dna["reason_for_being"] = _brain_lines(dna.get("reason_for_being", []) + candidate_memory.get("summary", [])[:4], 24)
    dna["style_markers"] = _brain_lines(dna.get("style_markers", []) + candidate_memory.get("identity_rules", [])[:6], 20)
    dna["argumentative_patterns"] = _brain_lines(
        dna.get("argumentative_patterns", []) + candidate_memory.get("structure_rules", [])[:6] + candidate_memory.get("activity_rules", [])[:6],
        20,
    )
    dna["reinforcement_log"] = _brain_lines(
        dna.get("reinforcement_log", [])
        + [f"Refuerzo editorial aplicado sobre {len(concept_signals)} conceptos y {len(citation_signals)} citas."]
        + candidate_memory.get("summary", [])[:2],
        30,
        allow_operational=True,
    )
    return _normalize_editorial_dna(dna)


def _memory_prompt_view(memory: dict) -> dict:
    normalized = dict(memory or {})
    editorial_dna = _normalize_editorial_dna(normalized.get("editorial_dna", {}))
    tex_primary = normalized.get("tex_content_memory", {}).get("primary", {}) if isinstance(normalized.get("tex_content_memory", {}), dict) else {}
    prompt_view = {
        section: normalized.get(section, [])[:12] for section in MEMORY_SECTIONS if normalized.get(section)
    }
    for field in ("artifact_name", "artifact_types", "supported_artifact_types", "source_documents", "concepts", "section_titles", "citations"):
        value = normalized.get(field)
        if isinstance(value, list):
            prompt_view[field] = value[:20]
        elif value:
            prompt_view[field] = value
    if editorial_dna:
        graph = editorial_dna.get("knowledge_graph", {})
        prompt_view["editorial_dna"] = {
            "identity": editorial_dna.get("identity", {}),
            "essence": editorial_dna.get("essence", [])[:12],
            "reason_for_being": editorial_dna.get("reason_for_being", [])[:12],
            "style_markers": editorial_dna.get("style_markers", [])[:12],
            "argumentative_patterns": editorial_dna.get("argumentative_patterns", [])[:12],
            "knowledge_graph": {
                "concepts": graph.get("concepts", [])[:20],
                "citations": graph.get("citations", [])[:20],
                "relations": graph.get("relations", [])[:12],
                "evidence": graph.get("evidence", [])[:12],
            },
            "writing_memory_blocks": len(editorial_dna.get("writing_memory", [])),
            "has_reconstructable_source": bool(editorial_dna.get("reconstructable_source", "")),
        }
    if tex_primary:
        prompt_view["tex_primary"] = {
            "relative_path": tex_primary.get("relative_path", ""),
            "raw_latex_chars": tex_primary.get("raw_latex_chars", 0),
            "content_blocks": len(tex_primary.get("content_blocks", [])),
            "all_cited_keys": tex_primary.get("all_cited_keys", [])[:20],
        }
    return prompt_view


def _brain_lines(items: list[str], max_items: int, *, allow_operational: bool = False) -> list[str]:
    normalized = [item for item in items if isinstance(item, str) and item.strip()]
    if not allow_operational:
        normalized = [item for item in normalized if not _is_operational_noise(item)]
    return _dedupe_lines(normalized)[:max_items]


def _brain_concepts(items: list[str], max_items: int) -> list[str]:
    selected = [item for item in items if _is_brain_concept(item)]
    return _dedupe_lines(selected)[:max_items]


def _relations_from_content_blocks(blocks: list[dict], concepts: list[str]) -> list[dict]:
    relations: list[dict] = []
    candidates = _brain_concepts(concepts, 20)
    if not candidates:
        candidates = []
    for block in blocks[:120]:
        if not isinstance(block, dict):
            continue
        text = str(block.get("text", ""))
        lowered = text.lower()
        kind = str(block.get("kind", "")).strip()
        section = str(block.get("section", "")).strip()
        subsection = str(block.get("subsection", "")).strip()
        paragraph_heading = str(block.get("paragraph_heading", "")).strip()
        evidence = [str(block.get("id", ""))] if block.get("id") else []

        if section and subsection:
            relations.append(
                {
                    "source": section,
                    "target": subsection,
                    "kind": "organizes",
                    "weight": 1,
                    "evidence": evidence,
                }
            )
        if (subsection or section) and paragraph_heading:
            relations.append(
                {
                    "source": subsection or section,
                    "target": paragraph_heading,
                    "kind": "develops",
                    "weight": 1,
                    "evidence": evidence,
                }
            )
        if kind == "concept_node":
            concept_text = _concept_seed_from_line(text)
            if _is_brain_concept(concept_text):
                relations.append(
                    {
                        "source": subsection or section or "documento",
                        "target": concept_text,
                        "kind": "develops",
                        "weight": 1,
                        "evidence": evidence,
                    }
                )

        matched = [concept for concept in candidates if concept.lower() in lowered][:5]
        for concept in matched:
            if section:
                relations.append(
                    {
                        "source": section,
                        "target": concept,
                        "kind": "develops",
                        "weight": 1,
                        "evidence": evidence,
                    }
                )
        for index, source in enumerate(matched):
            for target in matched[index + 1:index + 3]:
                relations.append(
                    {
                        "source": source,
                        "target": target,
                        "kind": "cooccurrence",
                        "weight": 1,
                        "evidence": evidence,
                    }
                )
    return _merge_relation_lists([], relations)


def _synthesize_editorial_dna(memory: dict, existing_dna: dict | None = None) -> dict:
    dna = _normalize_editorial_dna(existing_dna or memory.get("editorial_dna", {}))
    tex_primary = memory.get("tex_content_memory", {}).get("primary", {}) if isinstance(memory.get("tex_content_memory", {}), dict) else {}
    curricular_context = memory.get("curricular_context", {}) if isinstance(memory.get("curricular_context", {}), dict) else {}
    work_axes = curricular_context.get("work_axes", []) if isinstance(curricular_context.get("work_axes", []), list) else []
    purpose = curricular_context.get("purpose", "") if isinstance(curricular_context.get("purpose", ""), str) else ""
    graph = dna.get("knowledge_graph", {})
    graph["concepts"] = _dedupe_lines(graph.get("concepts", []) + memory.get("concepts", []))
    graph["citations"] = _dedupe_lines(graph.get("citations", []) + memory.get("citations", []))
    graph["evidence"] = _dedupe_lines(graph.get("evidence", []) + memory.get("bibliography_index", []) + memory.get("source_documents", []))
    graph["relations"] = _overlay_relation_lists(graph.get("relations", []), _relations_from_content_blocks(tex_primary.get("content_blocks", []), graph.get("concepts", [])))
    dna["knowledge_graph"] = graph
    dna["identity"] = _deep_merge_dicts(
        dna.get("identity", {}),
        {
            "node_metadata": memory.get("node_metadata", {}),
            "curricular_context": memory.get("curricular_context", {}),
            "identity_rules": memory.get("identity_rules", [])[:12],
        },
    )
    dna["structure"] = _deep_merge_dicts(
        dna.get("structure", {}),
        {
            "section_titles": memory.get("section_titles", []),
            "artifact_name": memory.get("artifact_name", ""),
            "artifact_types": memory.get("artifact_types", []) or memory.get("supported_artifact_types", []),
            "tex_functional_structure": tex_primary.get("functional_structure", {}),
        },
    )
    dna["essence"] = _brain_lines(
        work_axes
        + _brain_concepts(memory.get("concepts", []), 20)
        + _brain_concepts(graph.get("concepts", []), 20)
        + memory.get("activity_rules", []),
        24,
    )
    dna["reason_for_being"] = _brain_lines(
        ([purpose] if purpose else [])
        + work_axes
        + memory.get("structure_rules", [])
        + memory.get("activity_rules", [])
        + memory.get("section_titles", []),
        24,
    )
    dna["style_markers"] = _brain_lines(
        dna.get("style_markers", []) + memory.get("identity_rules", []) + memory.get("latex_rules", []),
        20,
    )
    dna["argumentative_patterns"] = _brain_lines(
        dna.get("argumentative_patterns", []) + memory.get("structure_rules", []) + memory.get("activity_rules", []) + memory.get("quality_gates", []),
        20,
    )
    dna["writing_memory"] = tex_primary.get("content_blocks", []) or dna.get("writing_memory", [])
    dna["reconstructable_source"] = tex_primary.get("raw_latex", "") or dna.get("reconstructable_source", "")
    dna["reinforcement_log"] = _brain_lines(
        dna.get("reinforcement_log", [])
        + [
            f"ADN sintetizado con {len(graph.get('concepts', []))} conceptos, {len(graph.get('citations', []))} citas y {len(graph.get('relations', []))} relaciones.",
            f"Memoria de redacción preservada en {len(dna.get('writing_memory', []))} bloques.",
        ],
        40,
        allow_operational=True,
    )
    return _normalize_editorial_dna(dna)


def _extract_first_json(text: str) -> dict | None:
    if not text.strip():
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        try:
            payload = json.loads(fenced.group(1))
            return payload if isinstance(payload, dict) else None
        except json.JSONDecodeError:
            pass

    start = text.find("{")
    while start >= 0:
        depth = 0
        for index in range(start, len(text)):
            char = text[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : index + 1]
                    try:
                        payload = json.loads(candidate)
                        return payload if isinstance(payload, dict) else None
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)
    return None


def _extract_bullets(text: str) -> list[str]:
    bullets: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(("-", "*")):
            bullets.append(line[1:].strip())
            continue
        if re.match(r"^\d+[.)]\s+", line):
            bullets.append(re.sub(r"^\d+[.)]\s+", "", line))
    return _dedupe_lines(bullets)


def _latex_to_plain(text: str) -> str:
    value = text or ""
    value = re.sub(r"\\cite\w*(?:\[[^\]]*\]){0,2}\{([^{}]*)\}", "", value)
    value = re.sub(r"\\textbf\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\textit\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\emph\{([^{}]*)\}", r"\1", value)
    value = value.replace(r"\&", "&")
    value = value.replace("\\\\", " ")
    value = value.replace("~", " ")
    value = re.sub(r"\\[a-zA-Z]+", " ", value)
    value = value.replace("{", " ").replace("}", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _extract_nonempty_lines(text: str, *, limit: int = 8, max_len: int = 240) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = _latex_to_plain(raw)
        if not line:
            continue
        lines.append(line[:max_len])
        if len(lines) >= limit:
            break
    return _dedupe_lines(lines)


def _extract_program_context(text: str) -> dict:
    normalized = text or ""
    headings = list(re.finditer(r"^##\s+(.+)$", normalized, re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(headings):
        start = match.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(normalized)
        sections[match.group(1).strip().lower()] = normalized[start:end].strip()

    work_axes: list[str] = []
    ejes = sections.get("ejes de trabajo", "")
    for line in ejes.splitlines():
        stripped = line.strip()
        if re.match(r"^\d+[.)]?\s+", stripped):
            work_axes.append(re.sub(r"^\d+[.)]?\s+", "", stripped))

    source_fragments = []
    for key in ("encuadre institucional", "proposito de realizacion"):
        if sections.get(key):
            source_fragments.extend(_extract_nonempty_lines(sections[key], limit=2, max_len=240))
    source_fragments.extend(work_axes[:5])
    return {
        "institutional_frame": _latex_to_plain(sections.get("encuadre institucional", "")),
        "purpose": _latex_to_plain(sections.get("proposito de realizacion", "")),
        "work_axes": _dedupe_lines(work_axes),
        "source_fragments": _dedupe_lines(source_fragments),
    }


def _extract_bibliography_index(text: str) -> list[str]:
    return _bibliography_index_from_entries(_extract_bibtex_entries(text, "inline"))


def _bibliography_index_from_entries(entries: dict[str, dict]) -> list[str]:
    lines: list[str] = []
    for key, entry in entries.items():
        title = entry.get("title") or entry.get("entry_text") or ""
        source = entry.get("source_path", "")
        label = f"{key} :: {title}" if title else key
        if source:
            label = f"{label} :: fuente={source}"
        lines.append(label)
    return _dedupe_lines(lines)


def _extract_bibtex_entries(text: str, relative_path: str) -> dict[str, dict]:
    entries: dict[str, dict] = {}
    entry_pattern = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,(.*?)(?=^\s*@\w+\s*\{|\Z)", re.DOTALL | re.MULTILINE)
    for match in entry_pattern.finditer(text or ""):
        entry_type = match.group(1).strip()
        key = match.group(2).strip()
        body = match.group(3).strip()
        fields = _extract_bibtex_fields(body)
        entry = {
            "key": key,
            "source_type": "bibtex",
            "source_path": relative_path,
            "entry_type": entry_type,
            "title": _latex_to_plain(fields.get("title", "")),
            "author": _latex_to_plain(fields.get("author", "")),
            "year": _latex_to_plain(fields.get("year", "")),
            "publisher": _latex_to_plain(fields.get("publisher", "")),
            "journal": _latex_to_plain(fields.get("journal", "")),
            "url": _latex_to_plain(fields.get("url", "") or fields.get("howpublished", "")),
            "note": _latex_to_plain(fields.get("note", "")),
            "raw_entry": match.group(0).strip(),
        }
        entries[key] = {k: v for k, v in entry.items() if v not in ("", None)}
    return entries


def _extract_bibtex_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    field_pattern = re.compile(
        r"(\w+)\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|\"[^\"]*\"|[^,\n]+)\s*,?",
        re.DOTALL,
    )
    for match in field_pattern.finditer(body or ""):
        name = match.group(1).strip().lower()
        value = match.group(2).strip()
        if (value.startswith("{") and value.endswith("}")) or (value.startswith('"') and value.endswith('"')):
            value = value[1:-1]
        fields[name] = value.strip()
    return fields


def _extract_thebibliography_entries(text: str, relative_path: str) -> dict[str, dict]:
    entries: dict[str, dict] = {}
    env_match = re.search(r"\\begin\{thebibliography\}(.*?)\\end\{thebibliography\}", text or "", re.DOTALL)
    if not env_match:
        return entries
    body = env_match.group(1)
    matches = list(re.finditer(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}", body))
    for index, match in enumerate(matches):
        key = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        raw_entry = body[start:end].strip()
        entry_text = _latex_to_plain(raw_entry)
        entries[key] = {
            "key": key,
            "source_type": "thebibliography",
            "source_path": f"{relative_path}#thebibliography",
            "entry_text": entry_text,
            "title": _guess_inline_bibliography_title(raw_entry),
            "raw_entry": raw_entry,
        }
    return entries


def _guess_inline_bibliography_title(entry_text: str) -> str:
    if not entry_text:
        return ""
    italic_match = re.search(r"\\textit\{([^{}]+)\}", entry_text)
    if italic_match:
        return _latex_to_plain(italic_match.group(1))
    plain_text = _latex_to_plain(entry_text)
    pieces = [piece.strip() for piece in re.split(r"\.\s+", plain_text) if piece.strip()]
    if len(pieces) >= 2:
        return pieces[1][:180]
    return entry_text[:180]


def _extract_bibliography_titles(entries: list[str]) -> list[str]:
    titles: list[str] = []
    for item in entries:
        if " :: " in item:
            _key, title = item.split(" :: ", 1)
            if title:
                titles.append(title)
    return _dedupe_lines(titles)


def _extract_tex_blueprint(text: str, relative_path: str, bibliography_lookup: dict[str, dict] | None = None) -> dict:
    macros: dict[str, str] = {}
    for name in ("documenttitle", "documentsubtitle", "documentsubject", "coursename", "coursecode", "documentauthor"):
        match = re.search(rf"\\def\\{name}\s*\{{(.*?)\}}", text, re.DOTALL)
        if match:
            macros[name] = _latex_to_plain(match.group(1))

    abstract_match = re.search(r"\\begin\{abstractd\}(.*?)\\end\{abstractd\}", text, re.DOTALL)
    abstract_text = _latex_to_plain(abstract_match.group(1)) if abstract_match else ""
    section_titles = _dedupe_lines([_latex_to_plain(item) for item in re.findall(r"\\section\{([^}]*)\}", text)])
    subsection_titles = _dedupe_lines([_latex_to_plain(item) for item in re.findall(r"\\subsection\{([^}]*)\}", text)])
    cited_keys = _extract_citation_keys(text)
    concept_nodes = _dedupe_lines(
        [_latex_to_plain(item) for item in re.findall(r"\\node\[[^\]]+\]\s*\([^)]+\)\s*at\s*\([^)]+\)\s*\{([^}]*)\};", text)]
    )
    intro_match = re.search(r"\\section\{Introducci[oó]n\}(.*?)(?=\\section\{|\\end\{document\})", text, re.DOTALL | re.IGNORECASE)
    intro_text = _latex_to_plain(intro_match.group(1)) if intro_match else ""
    source_fragments = []
    if abstract_text:
        source_fragments.extend(_extract_nonempty_lines(abstract_text, limit=3, max_len=260))
    if intro_text:
        source_fragments.extend(_extract_nonempty_lines(intro_text, limit=4, max_len=260))
    source_fragments.extend(concept_nodes[:8])
    content_memory = _extract_tex_content_memory(text, relative_path, bibliography_lookup or {})

    return {
        "relative_path": relative_path,
        **macros,
        "abstract": abstract_text,
        "section_titles": section_titles,
        "subsection_titles": subsection_titles,
        "cited_keys": _dedupe_lines(cited_keys),
        "concepts": concept_nodes,
        "source_fragments": _dedupe_lines(source_fragments),
        "content_memory": content_memory,
    }


def _extract_tex_content_memory(text: str, relative_path: str, bibliography_lookup: dict[str, dict]) -> dict:
    all_citations = _extract_citation_keys(text)
    blocks = _extract_tex_content_blocks(text, relative_path, bibliography_lookup)
    citation_map: dict[str, dict] = {}
    for block in blocks:
        for key in block.get("cited_keys", []):
            item = citation_map.setdefault(
                key,
                {
                    "key": key,
                    "blocks": [],
                    "bibliography": _bibliography_for_key(key, bibliography_lookup),
                },
            )
            item["blocks"].append(block["id"])
    missing = [key for key in _dedupe_lines(all_citations) if key not in bibliography_lookup]
    return {
        "relative_path": relative_path,
        "raw_latex_sha256": hashlib.sha256((text or "").encode("utf-8", errors="replace")).hexdigest(),
        "raw_latex_chars": len(text or ""),
        "raw_latex": text or "",
        "functional_structure": _extract_tex_functional_structure(text),
        "paragraph_map": blocks,
        "content_blocks": blocks,
        "citation_map": citation_map,
        "all_cited_keys": _dedupe_lines(all_citations),
        "missing_bibliography_keys": missing,
    }


def _extract_tex_functional_structure(text: str) -> dict:
    documentclass_match = re.search(r"\\documentclass(?:\[([^\]]*)\])?\{([^}]+)\}", text or "", re.DOTALL)
    packages = []
    for match in re.finditer(r"\\usepackage(?:\[[^\]]*\])?\{([^}]+)\}", text or ""):
        packages.extend(part.strip() for part in match.group(1).split(",") if part.strip())
    inputs = [item.strip() for item in re.findall(r"\\input\{([^}]+)\}", text or "")]
    environments = _dedupe_lines(re.findall(r"\\begin\{([^}]+)\}", text or ""))
    commands = _dedupe_lines(re.findall(r"\\(template\w+|insertcoverwatermark|bibliography|bibliographystyle|setcitestyle)", text or ""))
    return {
        "documentclass": {
            "class": documentclass_match.group(2).strip() if documentclass_match else "",
            "options": _latex_to_plain(documentclass_match.group(1) or "") if documentclass_match else "",
        },
        "packages": _dedupe_lines(packages),
        "inputs": _dedupe_lines(inputs),
        "environments": environments,
        "template_commands": commands,
    }


def _extract_tex_content_blocks(text: str, relative_path: str, bibliography_lookup: dict[str, dict]) -> list[dict]:
    blocks: list[dict] = []
    current_section = ""
    current_subsection = ""
    current_paragraph = ""
    order = 1
    in_tikz_options = False

    def add_block(kind: str, latex: str, *, section: str | None = None, subsection: str | None = None, paragraph: str | None = None) -> None:
        nonlocal order
        plain = _latex_to_plain(latex)
        if not plain:
            return
        cited_keys = _extract_citation_keys(latex)
        block = {
            "id": f"b{order:04d}",
            "order": order,
            "kind": kind,
            "section": section if section is not None else current_section,
            "subsection": subsection if subsection is not None else current_subsection,
            "paragraph_heading": paragraph if paragraph is not None else current_paragraph,
            "text": plain,
            "latex": latex.strip(),
            "cited_keys": cited_keys,
            "bibliography": [_bibliography_for_key(key, bibliography_lookup) for key in cited_keys],
            "source_path": relative_path,
        }
        blocks.append(block)
        order += 1

    abstract_match = re.search(r"\\begin\{abstractd\}(.*?)\\end\{abstractd\}", text or "", re.DOTALL)
    if abstract_match:
        add_block("abstract", abstract_match.group(1), section="Resumen editorial", subsection="", paragraph="")

    body = _document_body_without_bibliography(text or "")
    buffer: list[str] = []

    def flush_buffer() -> None:
        if not buffer:
            return
        latex = "\n".join(buffer).strip()
        buffer.clear()
        if latex:
            add_block("paragraph", latex)

    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            flush_buffer()
            continue
        if line.startswith("%"):
            continue
        if line.startswith(r"\begin{tikzpicture}["):
            flush_buffer()
            in_tikz_options = True
            continue
        if in_tikz_options:
            if line == "]" or line.endswith("]"):
                in_tikz_options = False
            continue

        heading = _match_heading(line, "section")
        if heading is not None:
            flush_buffer()
            current_section = heading
            current_subsection = ""
            current_paragraph = ""
            add_block("section", line, section=current_section, subsection="", paragraph="")
            continue

        heading = _match_heading(line, "subsection")
        if heading is not None:
            flush_buffer()
            current_subsection = heading
            current_paragraph = ""
            add_block("subsection", line, subsection=current_subsection, paragraph="")
            continue

        heading = _match_heading(line, "paragraph")
        if heading is not None:
            flush_buffer()
            current_paragraph = heading
            add_block("paragraph_heading", line, paragraph=current_paragraph)
            continue

        node_text = _extract_node_text(line)
        if node_text:
            flush_buffer()
            add_block("concept_node", node_text)
            continue

        caption = _match_command_argument(line, "caption")
        if caption is not None:
            flush_buffer()
            add_block("caption", line)
            continue

        item_match = re.match(r"\\item(?:\[[^\]]*\])?\s*(.+)$", line)
        if item_match:
            flush_buffer()
            add_block("list_item", line)
            continue

        if _is_structural_latex_line(line):
            flush_buffer()
            continue

        if _looks_like_content(line):
            buffer.append(line)
        else:
            flush_buffer()

    flush_buffer()
    return blocks


def _document_body_without_bibliography(text: str) -> str:
    body_match = re.search(r"\\begin\{document\}(.*?)(?:\\end\{document\}|\Z)", text or "", re.DOTALL)
    body = body_match.group(1) if body_match else text
    body = re.sub(r"\\begin\{abstractd\}.*?\\end\{abstractd\}", "", body, flags=re.DOTALL)
    body = re.split(r"\\begin\{thebibliography\}|\\bibliography\{", body, maxsplit=1)[0]
    return body


def _match_heading(line: str, command: str) -> str | None:
    match = re.match(rf"\\{command}\*?\{{(.+?)\}}", line)
    return _latex_to_plain(match.group(1)) if match else None


def _match_command_argument(line: str, command: str) -> str | None:
    match = re.match(rf"\\{command}\*?\{{(.+?)\}}", line)
    return match.group(1) if match else None


def _extract_node_text(line: str) -> str:
    match = re.search(r"\\node(?:\[[^\]]+\])?(?:\s*\([^)]+\))?\s*(?:at\s*\([^)]+\))?\s*\{(.+?)\};", line)
    return match.group(1) if match else ""


def _is_structural_latex_line(line: str) -> bool:
    if ".style" in line or re.match(r"^(draw|fill|align|text width|minimum height|inner sep|font)\s*=", line):
        return True
    if re.match(r"^[A-Za-z0-9_!\\.\s/-]+,\s*$", line) and "=" in line:
        return True
    structural_prefixes = (
        r"\begin",
        r"\end",
        r"\newpage",
        r"\clearpage",
        r"\thispagestyle",
        r"\template",
        r"\insertcoverwatermark",
        r"\centering",
        r"\vspace",
        r"\resizebox",
        r"\draw",
        r"\label",
        r"\input",
        r"\setcitestyle",
        r"\usepackage",
        r"\renewcommand",
        r"\def",
        r"\AddToShipoutPictureBG",
        r"\ifthenelse",
        r"\includegraphics",
    )
    return line.startswith(structural_prefixes) or line in {"{", "}", "};", "]"}


def _looks_like_content(line: str) -> bool:
    if not re.search(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]", line):
        return False
    if re.match(r"^[\\{}\[\](),.;:%\s-]+$", line):
        return False
    return True


def _extract_citation_keys(text: str) -> list[str]:
    keys: list[str] = []
    pattern = re.compile(r"\\cite\w*(?:\[[^\]]*\]){0,2}\{([^{}]+)\}")
    for chunk in pattern.findall(text or ""):
        keys.extend(part.strip() for part in chunk.split(",") if part.strip())
    return _dedupe_lines(keys)


def _bibliography_for_key(key: str, bibliography_lookup: dict[str, dict]) -> dict:
    entry = bibliography_lookup.get(key)
    if entry:
        return entry
    return {
        "key": key,
        "source_type": "missing",
        "source_path": "",
        "warning": "La clave aparece citada en el TEX pero no se encontro en .bib ni en thebibliography.",
    }
