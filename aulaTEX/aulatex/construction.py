from __future__ import annotations

import html
import json
import re
import sqlite3
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Callable, Iterable

from .config import diagnostic_metrics_enabled
from .editorial_context import EditorialContextProvider
from .editorial_memory import ENGINE_PRIORITY, EditorialMemoryStore
from .llm_bridge import DEFAULT_MAX_TOKENS, LLM_ENGINES, AulaTeXLLMClient
from .workspace import AulaTeXWorkspace, EditorialScope, GENERATION_MARKER_FILENAME


CONSTRUCTION_NODE_LEVELS = (
    "institucion",
    "carrera",
    "materia",
    "actividad",
)

FUNDATIONAL_MEMORY_SECTIONS = (
    "summary",
    "identity_rules",
    "structure_rules",
    "style_rules",
    "quality_gates",
    "latex_rules",
    "bibliography_rules",
    "research_markers",
)

PLAN_SECTIONS = (
    "objetivo_editorial",
    "alcance",
    "estructura_base",
    "criterios_evaluacion",
    "bibliografia_requerida",
    "riesgos",
    "siguiente_fase_agente",
)

MAQUETA_LIST_FIELDS = (
    "objetivo",
    "competencias",
    "resultados_esperados",
    "estructura_sugerida",
    "criterios_evaluacion",
    "bibliografia_requerida",
    "marcadores_investigacion",
)

EDITORIAL_TEX_SECTIONS = (
    "plantilla",
    "actividad",
    "reporte",
    "presentacion",
)


@dataclass(frozen=True)
class ConstructionRequest:
    parent_scope_key: str = "interinstitucional"
    node_level: str = "actividad"
    node_name: str = ""
    activity_number: int = 1
    operation_mode: str = "crear"
    destination_path: str = ""
    ingest_text: str = ""
    ingest_document_path: str = ""
    engines: list[str] | tuple[str, ...] = ("Codex", "Auto (model-router)", "Claude Foundry", "GPT-Pro")
    iterations: int = 2
    max_tokens: int = DEFAULT_MAX_TOKENS


@dataclass(frozen=True)
class ConstructionEvent:
    kind: str
    message: str
    current: int = 0
    total: int = 0
    node_key: str = ""
    engine: str = ""
    cycle: int = 0
    elapsed_ms: int = 0


@dataclass(frozen=True)
class ConstructionResult:
    run_id: str
    run_dir: Path
    node_key: str
    node_dir: Path
    memory_path: Path
    plan_path: Path
    maqueta_path: Path
    manifest_path: Path
    ok: bool
    cancelled: bool = False


@dataclass(frozen=True)
class ConstructionNodeSpec:
    key: str
    parent_scope_key: str
    level: str
    name: str
    label: str
    activity_number: int
    operation_mode: str
    relative_path: str
    output_dir: Path
    future_agent_entrypoint: str


class ConstructionStore:
    def __init__(self, workspace: AulaTeXWorkspace | None = None, *, diagnostics_enabled: bool | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.diagnostics_enabled = diagnostic_metrics_enabled() if diagnostics_enabled is None else diagnostics_enabled
        self.root = self.workspace.feedback_root / "construccion"
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "construccion.db"
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS nodes (
                    node_key TEXT PRIMARY KEY,
                    parent_scope_key TEXT NOT NULL,
                    level TEXT NOT NULL,
                    node_name TEXT NOT NULL,
                    activity_number INTEGER NOT NULL DEFAULT 0,
                    relative_path TEXT NOT NULL,
                    output_dir TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS construction_runs (
                    run_id TEXT PRIMARY KEY,
                    node_key TEXT NOT NULL,
                    parent_scope_key TEXT NOT NULL,
                    node_level TEXT NOT NULL,
                    node_name TEXT NOT NULL,
                    activity_number INTEGER NOT NULL DEFAULT 0,
                    iterations INTEGER NOT NULL,
                    engines_json TEXT NOT NULL,
                    manifest_path TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    ok INTEGER NOT NULL DEFAULT 0,
                    cancelled INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS construction_cycles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    node_key TEXT NOT NULL,
                    cycle_index INTEGER NOT NULL,
                    engine TEXT NOT NULL,
                    ok INTEGER NOT NULL,
                    elapsed_ms INTEGER NOT NULL,
                    response_chars INTEGER NOT NULL,
                    response_text TEXT NOT NULL,
                    consolidated_memory_json TEXT NOT NULL,
                    consolidated_plan_json TEXT NOT NULL,
                    consolidated_maqueta_json TEXT NOT NULL,
                    memory_items INTEGER NOT NULL DEFAULT 0,
                    sections_created INTEGER NOT NULL DEFAULT 0,
                    progress_percent REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS construction_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_key TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    memory_kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    summary_text TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def node_exists(self, node_key: str) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM nodes WHERE node_key=?", (node_key,)).fetchone()
        return row is not None

    def node_exists_many(self, node_keys: Iterable[str]) -> set[str]:
        keys = [key for key in dict.fromkeys(node_keys) if key]
        if not keys:
            return set()
        placeholders = ",".join("?" for _ in keys)
        query = f"SELECT node_key FROM nodes WHERE node_key IN ({placeholders})"
        with self._connect() as conn:
            rows = conn.execute(query, keys).fetchall()
        return {str(row["node_key"]) for row in rows}

    def upsert_node(self, node: ConstructionNodeSpec, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO nodes (
                    node_key, parent_scope_key, level, node_name, activity_number, relative_path, output_dir, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(node_key) DO UPDATE SET
                    parent_scope_key=excluded.parent_scope_key,
                    level=excluded.level,
                    node_name=excluded.node_name,
                    activity_number=excluded.activity_number,
                    relative_path=excluded.relative_path,
                    output_dir=excluded.output_dir,
                    status=excluded.status,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    node.key,
                    node.parent_scope_key,
                    node.level,
                    node.name,
                    int(node.activity_number),
                    node.relative_path,
                    str(node.output_dir),
                    status,
                ),
            )

    def start_run(self, run_id: str, request: ConstructionRequest, node: ConstructionNodeSpec, engines: list[str]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO construction_runs (
                    run_id, node_key, parent_scope_key, node_level, node_name, activity_number, iterations, engines_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    node.key,
                    node.parent_scope_key,
                    node.level,
                    node.name,
                    int(node.activity_number),
                    int(request.iterations),
                    json.dumps(engines, ensure_ascii=False),
                ),
            )

    def finish_run(self, run_id: str, *, ok: bool, cancelled: bool, manifest_path: Path) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE construction_runs
                SET completed_at=CURRENT_TIMESTAMP,
                    ok=?,
                    cancelled=?,
                    manifest_path=?
                WHERE run_id=?
                """,
                (1 if ok else 0, 1 if cancelled else 0, str(manifest_path), run_id),
            )

    def record_cycle(
        self,
        *,
        run_id: str,
        node_key: str,
        cycle_index: int,
        engine: str,
        ok: bool,
        elapsed_ms: int,
        response_text: str,
        consolidated_memory: dict,
        consolidated_plan: dict,
        consolidated_maqueta: dict,
        memory_items: int,
        sections_created: int,
        progress_percent: float,
    ) -> None:
        if not self.diagnostics_enabled:
            return
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO construction_cycles (
                    run_id, node_key, cycle_index, engine, ok, elapsed_ms, response_chars, response_text,
                    consolidated_memory_json, consolidated_plan_json, consolidated_maqueta_json,
                    memory_items, sections_created, progress_percent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    node_key,
                    cycle_index,
                    engine,
                    1 if ok else 0,
                    int(elapsed_ms),
                    len(response_text),
                    response_text,
                    json.dumps(consolidated_memory, ensure_ascii=False, indent=2),
                    json.dumps(consolidated_plan, ensure_ascii=False, indent=2),
                    json.dumps(consolidated_maqueta, ensure_ascii=False, indent=2),
                    int(memory_items),
                    int(sections_created),
                    float(progress_percent),
                ),
            )

    def save_memory_snapshot(self, node_key: str, run_id: str, kind: str, payload: dict | str, summary_text: str) -> None:
        if isinstance(payload, str):
            payload_json = json.dumps({"text": payload}, ensure_ascii=False, indent=2)
        else:
            payload_json = json.dumps(payload, ensure_ascii=False, indent=2)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO construction_memories (node_key, run_id, memory_kind, payload_json, summary_text)
                VALUES (?, ?, ?, ?, ?)
                """,
                (node_key, run_id, kind, payload_json, summary_text),
            )

    def list_constructed_children(self, parent_scope_key: str, level: str) -> list[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT node_key, node_name, activity_number, relative_path, status
                FROM nodes
                WHERE parent_scope_key=? AND level=?
                ORDER BY activity_number, node_name
                """,
                (parent_scope_key, level),
            ).fetchall()
        return list(rows)

    def get_latest_run(self, node_key: str) -> sqlite3.Row | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT run_id, node_key, parent_scope_key, node_level, node_name, activity_number,
                       iterations, engines_json, manifest_path, created_at, completed_at, ok, cancelled
                FROM construction_runs
                WHERE node_key=?
                ORDER BY created_at DESC, run_id DESC
                LIMIT 1
                """,
                (node_key,),
            ).fetchone()
        return row

    def list_memory_snapshots(self, node_key: str, limit: int = 12) -> list[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT run_id, memory_kind, summary_text, created_at
                FROM construction_memories
                WHERE node_key=?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (node_key, max(1, int(limit))),
            ).fetchall()
        return list(rows)

    def list_recent_cycles(self, node_key: str, limit: int = 12) -> list[sqlite3.Row]:
        if not self.diagnostics_enabled:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT cycle_index, engine, ok, elapsed_ms, response_chars, memory_items,
                       sections_created, progress_percent, created_at
                FROM construction_cycles
                WHERE node_key=?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (node_key, max(1, int(limit))),
            ).fetchall()
        return list(rows)

    def render_metrics_markdown(self, node_key: str) -> str:
        if not self.diagnostics_enabled:
            return "# Diagnóstico desactivado\n\n- Ejecuta AulaTeX con --diagnostics o define AULATEX_ENABLE_DIAGNOSTIC_METRICS=1 para medir desempeño.\n"
        if not node_key:
            return "# Metricas de construccion\n\n- Sin nodo seleccionado.\n"
        with self._connect() as conn:
            by_engine = conn.execute(
                """
                SELECT engine,
                       COUNT(*) AS calls,
                       SUM(response_chars) AS chars,
                       AVG(elapsed_ms) AS avg_ms,
                       SUM(CASE WHEN ok = 0 THEN 1 ELSE 0 END) AS errors
                FROM construction_cycles
                WHERE node_key=?
                GROUP BY engine
                ORDER BY engine
                """,
                (node_key,),
            ).fetchall()
            by_cycle = conn.execute(
                """
                SELECT cycle_index,
                       MAX(progress_percent) AS avance,
                       MAX(memory_items) AS memory_items,
                       MAX(sections_created) AS sections_created
                FROM construction_cycles
                WHERE node_key=?
                GROUP BY cycle_index
                ORDER BY cycle_index
                """,
                (node_key,),
            ).fetchall()

        lines = ["# Metricas de construccion", ""]
        if by_engine:
            lines.extend(["## Por motor", ""])
            for row in by_engine:
                lines.append(
                    f"- {row['engine']}: llamadas={row['calls']}, chars={int(row['chars'] or 0)}, tiempo_ms_promedio={int(row['avg_ms'] or 0)}, errores={row['errors']}"
                )
            lines.append("")
        if by_cycle:
            lines.extend(["## Por ciclo", ""])
            for row in by_cycle:
                lines.append(
                    f"- Ciclo {row['cycle_index']}: avance={int(row['avance'] or 0)}%, memoria_generada={int(row['memory_items'] or 0)}, secciones_creadas={int(row['sections_created'] or 0)}"
                )
            lines.append("")
        if len(lines) == 2:
            lines.append("- Aun no hay corridas registradas para este nodo.")
        return "\n".join(lines)


class ConstructionBuilder:
    def __init__(
        self,
        workspace: AulaTeXWorkspace | None = None,
        llm_bridge: AulaTeXLLMClient | None = None,
        store: ConstructionStore | None = None,
        editorial_store: EditorialMemoryStore | None = None,
    ) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.llm = llm_bridge or AulaTeXLLMClient()
        self.store = store or ConstructionStore(self.workspace)
        self.editorial_store = editorial_store or EditorialMemoryStore(self.workspace)
        self.editorial_context = EditorialContextProvider(self.workspace, self.editorial_store)

    def preview_node(self, request: ConstructionRequest) -> ConstructionNodeSpec:
        by_key, children = self.workspace.editorial_scope_index()
        parent_scope = self._resolve_parent_scope(request, by_key)
        return self._build_node_spec(parent_scope, request, by_key, children)

    def build(
        self,
        request: ConstructionRequest,
        progress: Callable[[ConstructionEvent], None] | None = None,
        cancel_event: Event | None = None,
    ) -> ConstructionResult:
        by_key, children = self.workspace.editorial_scope_index()
        parent_scope = self._resolve_parent_scope(request, by_key)
        node = self._build_node_spec(parent_scope, request, by_key, children)
        inputs = self._build_inputs(request, parent_scope, node, by_key, children)

        run_id = self.workspace.timestamp()
        run_dir = self.store.root / "runs" / f"{run_id}-{_slugify(node.name or node.label)}"
        run_dir.mkdir(parents=True, exist_ok=True)

        engines = self._normalize_engines(request.engines)
        total = max(1, int(request.iterations)) * len(engines)
        current = 0
        cancelled = False
        overall_ok = True

        self.store.upsert_node(node, "running")
        self.store.start_run(run_id, request, node, engines)
        self.store.save_memory_snapshot(node.key, run_id, "ancestros", inputs["ancestors_payload"], inputs["ancestors_text"])
        self.store.save_memory_snapshot(node.key, run_id, "padre", inputs["parent_payload"], inputs["parent_text"])
        self.store.save_memory_snapshot(node.key, run_id, "hermanos", inputs["siblings_payload"], inputs["siblings_synthesis"])
        self.store.save_memory_snapshot(
            node.key,
            run_id,
            "reglas-interinstitucionales",
            inputs["interinstitutional_payload"],
            inputs["interinstitutional_text"],
        )
        self.store.save_memory_snapshot(
            node.key,
            run_id,
            "ingesta",
            inputs["ingestion_payload"],
            inputs["ingestion_summary"],
        )

        consolidated = self._load_existing_payload(node)
        cycle_logs: list[dict] = []

        self._emit(progress, ConstructionEvent("start", f"Generacion editorial para {node.label} en modo {node.operation_mode}", 0, total, node.key))

        for cycle_index in range(1, max(1, int(request.iterations)) + 1):
            if self._is_cancelled(cancel_event):
                cancelled = True
                break
            for engine in engines:
                if self._is_cancelled(cancel_event):
                    cancelled = True
                    break
                current += 1
                prompt = self._build_prompt(request, parent_scope, node, inputs, consolidated, cycle_index)
                self._emit(
                    progress,
                    ConstructionEvent(
                        "progress",
                        f"{node.label} | ciclo {cycle_index} | {engine}",
                        current,
                        total,
                        node.key,
                        engine,
                        cycle_index,
                    ),
                )
                started = time.perf_counter()
                result = self.llm.call(engine, prompt, max_tokens=request.max_tokens)
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                response_text = result.text if result.ok else result.error
                candidate = self._parse_response(response_text, node, engine)
                consolidated = self._merge_payload(consolidated, candidate, node, inputs)
                memory_items = _count_memory_items(consolidated["memoria_fundacional"])
                sections_created = _count_sections(consolidated)
                progress_percent = round((current / total) * 100, 2)
                self.store.record_cycle(
                    run_id=run_id,
                    node_key=node.key,
                    cycle_index=cycle_index,
                    engine=result.engine,
                    ok=result.ok,
                    elapsed_ms=elapsed_ms,
                    response_text=response_text,
                    consolidated_memory=consolidated["memoria_fundacional"],
                    consolidated_plan=consolidated["plan_editorial"],
                    consolidated_maqueta=consolidated["maqueta_inicial"],
                    memory_items=memory_items,
                    sections_created=sections_created,
                    progress_percent=progress_percent,
                )
                cycle_logs.append(
                    {
                        "cycle": cycle_index,
                        "engine": result.engine,
                        "ok": result.ok,
                        "elapsed_ms": elapsed_ms,
                        "chars": len(response_text),
                        "memory_items": memory_items,
                        "sections_created": sections_created,
                    }
                )
                raw_path = run_dir / f"{current:04d}-ciclo-{cycle_index:02d}-{result.engine.replace(' ', '_')}.md"
                raw_path.write_text(response_text, encoding="utf-8")
                if not result.ok:
                    overall_ok = False
                self._emit(
                    progress,
                    ConstructionEvent(
                        "result",
                        f"{result.engine}: {'OK' if result.ok else 'ERROR'} | {len(response_text)} chars | {elapsed_ms} ms",
                        current,
                        total,
                        node.key,
                        result.engine,
                        cycle_index,
                        elapsed_ms,
                    ),
                )

        final_payload = self._finalize_payload(consolidated, node, inputs)
        node.output_dir.mkdir(parents=True, exist_ok=True)
        artifact_names = _construction_artifact_names(
            node_level=node.level,
            node_name=node.name,
            output_dir=node.output_dir,
            activity_number=int(node.activity_number),
        )
        memory_path = node.output_dir / artifact_names["memory"]
        plan_path = node.output_dir / "plan.md"
        maqueta_path = node.output_dir / artifact_names["maqueta"]

        memory_path.write_text(json.dumps(final_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        plan_path.write_text(self._render_plan_markdown(node, final_payload), encoding="utf-8")
        self._write_node_marker(node, final_payload)

        self.store.save_memory_snapshot(
            node.key,
            run_id,
            "memoria-fundacional",
            final_payload,
            self._memory_summary(final_payload["memoria_fundacional"]),
        )

        manifest = {
            "run_id": run_id,
            "node_key": node.key,
            "node_level": node.level,
            "node_name": node.name,
            "node_label": node.label,
            "parent_scope_key": node.parent_scope_key,
            "activity_number": int(node.activity_number),
            "operation_mode": node.operation_mode,
            "destination_path": node.relative_path,
            "ingestion": inputs["ingestion_manifest"],
            "engines": engines,
            "iterations": int(request.iterations),
            "cancelled": cancelled,
            "ok": overall_ok and not cancelled,
            "node_dir": self.workspace.relative(node.output_dir),
            "artifacts": {
                "memory": self.workspace.relative(memory_path),
                "plan": self.workspace.relative(plan_path),
                "maqueta": "",
            },
            "future_agent_contract": final_payload["future_agent_contract"],
            "cycle_logs": cycle_logs,
        }
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        (run_dir / artifact_names["memory"]).write_text(memory_path.read_text(encoding="utf-8"), encoding="utf-8")
        (run_dir / "plan.md").write_text(plan_path.read_text(encoding="utf-8"), encoding="utf-8")
        final_ok = overall_ok and not cancelled
        self.store.finish_run(run_id, ok=final_ok, cancelled=cancelled, manifest_path=manifest_path)
        self.store.upsert_node(node, "ready" if final_ok else ("cancelled" if cancelled else "observed"))
        self.workspace.append_bitacora(run_id, "construccion-descendente", manifest)

        self._emit(
            progress,
            ConstructionEvent(
                "cancelled" if cancelled else "done",
                f"Nodo {node.label} {'cancelado' if cancelled else 'construido'} en {node.output_dir}",
                total if not cancelled else current,
                total,
                node.key,
            ),
        )
        return ConstructionResult(run_id, run_dir, node.key, node.output_dir, memory_path, plan_path, maqueta_path, manifest_path, final_ok, cancelled)

    def _normalize_engines(self, engines: list[str] | tuple[str, ...]) -> list[str]:
        from .config import MODEL_ROUTER_ENGINE, restrict_engines_to_available

        selected = [engine for engine in restrict_engines_to_available(engines) if engine in self.llm.engines()]
        if not selected:
            selected = [MODEL_ROUTER_ENGINE]
        return sorted(selected, key=lambda engine: (ENGINE_PRIORITY.get(engine, 999), engine))

    def _resolve_parent_scope(self, request: ConstructionRequest, by_key: dict[str, EditorialScope]) -> EditorialScope:
        parent_key = (request.parent_scope_key or "interinstitucional").strip() or "interinstitucional"
        if request.node_level == "institucion":
            parent_key = "interinstitucional"
        parent_scope = by_key.get(parent_key)
        if parent_scope is None:
            raise ValueError(f"Padre editorial no encontrado: {parent_key}")
        if request.node_level == "carrera" and parent_scope.level != "institucion":
            raise ValueError("Una carrera nueva requiere una institución como padre.")
        if request.node_level == "materia" and parent_scope.level not in {"carrera", "institucion"}:
            raise ValueError("Una materia nueva requiere una carrera o institución como padre.")
        if request.node_level == "actividad" and parent_scope.level != "materia":
            raise ValueError("Una actividad nueva requiere una materia como padre.")
        if request.node_level not in CONSTRUCTION_NODE_LEVELS:
            raise ValueError(f"Nivel de construcción inválido: {request.node_level}")
        return parent_scope

    def _build_node_spec(
        self,
        parent_scope: EditorialScope,
        request: ConstructionRequest,
        by_key: dict[str, EditorialScope],
        children: dict[str, list[EditorialScope]],
    ) -> ConstructionNodeSpec:
        name = re.sub(r"\s+", " ", request.node_name).strip()
        if not name:
            raise ValueError("El nombre del nuevo nodo no puede estar vacío.")
        mode = (request.operation_mode or "crear").strip().lower()
        if mode not in {"crear", "reforzar"}:
            raise ValueError(f"Modo de operación inválido: {request.operation_mode}")

        destination_hint = (request.destination_path or "").strip()
        effective_parent = parent_scope
        if destination_hint:
            hinted_output_dir = self.workspace.resolve_target(destination_hint)
            effective_parent = self._infer_parent_scope_from_destination(request.node_level, hinted_output_dir, parent_scope)

        if request.node_level == "institucion":
            node_key = name
            relative_path = name
            output_dir = self.workspace.repo_root / name
            label = name
        elif request.node_level in {"carrera", "materia"}:
            slug = _slugify(name)
            node_key = f"{effective_parent.key}/{slug}"
            relative_path = f"{effective_parent.relative_path.rstrip('/')}/{slug}" if effective_parent.relative_path != "." else slug
            output_dir = self.workspace.resolve_target(relative_path)
            label = name
        else:
            if int(request.activity_number) < 1:
                raise ValueError("El número de actividad debe ser mayor o igual a 1.")
            slug = _slugify(name)
            activity_key = f"actividad-{int(request.activity_number):02d}-{slug}"
            node_key = f"{effective_parent.key}/{activity_key}"
            relative_path = f"{effective_parent.relative_path.rstrip('/')}/_aulatex-construccion-{activity_key}"
            output_dir = self.workspace.resolve_target(relative_path)
            label = f"Actividad {int(request.activity_number)} - {name}"

        if destination_hint:
            output_dir = self.workspace.resolve_target(destination_hint)
            relative_path = self.workspace.relative(output_dir)
            if request.node_level == "institucion" and relative_path == ".":
                raise ValueError("La institución nueva no puede apuntar a la raíz del repositorio.")
            if request.node_level in {"carrera", "materia"}:
                node_key = f"{effective_parent.key}/{output_dir.name}"

        exists_in_catalog = node_key in by_key
        exists_in_store = self.store.node_exists(node_key)
        destination_has_content = output_dir.exists() and any(output_dir.iterdir())

        if mode == "crear":
            if exists_in_catalog:
                raise ValueError(f"El nodo ya existe en el catálogo editorial: {node_key}")
            if exists_in_store:
                raise ValueError(f"El nodo ya existe en la base de generación: {node_key}")
            if destination_has_content:
                raise ValueError(f"La ruta de salida ya contiene información: {self.workspace.relative(output_dir)}")
        if request.node_level == "actividad" and mode == "crear":
            self._validate_new_activity(parent_scope, request.activity_number, children)

        return ConstructionNodeSpec(
            key=node_key,
            parent_scope_key=effective_parent.key,
            level=request.node_level,
            name=name,
            label=label,
            activity_number=int(request.activity_number) if request.node_level == "actividad" else 0,
            operation_mode=mode,
            relative_path=relative_path,
            output_dir=output_dir,
            future_agent_entrypoint=self.workspace.relative(output_dir / "plan.md"),
        )

    def _infer_parent_scope_from_destination(
        self,
        node_level: str,
        output_dir: Path,
        fallback_parent: EditorialScope,
    ) -> EditorialScope:
        if node_level == "institucion":
            return fallback_parent
        anchor = output_dir.parent if node_level in {"carrera", "materia", "actividad"} else output_dir
        inferred = self.workspace.find_scope_for_target(anchor)
        if inferred is None:
            return fallback_parent
        if node_level == "carrera" and inferred.level == "institucion":
            return inferred
        if node_level == "materia" and inferred.level in {"carrera", "institucion"}:
            return inferred
        if node_level == "actividad" and inferred.level == "materia":
            return inferred
        return fallback_parent

    def _validate_new_activity(
        self,
        parent_scope: EditorialScope,
        activity_number: int,
        children: dict[str, list[EditorialScope]],
    ) -> None:
        sibling_activities = children.get(parent_scope.key, [])
        for sibling in sibling_activities:
            match = re.search(r"Actividad\s+(\d+)", sibling.label, re.IGNORECASE)
            if match and int(match.group(1)) == int(activity_number):
                raise ValueError(f"Ya existe una actividad {activity_number} bajo {parent_scope.label}.")

    def _build_inputs(
        self,
        request: ConstructionRequest,
        parent_scope: EditorialScope,
        node: ConstructionNodeSpec,
        by_key: dict[str, EditorialScope],
        children: dict[str, list[EditorialScope]],
    ) -> dict:
        chain = self.workspace.scope_chain(parent_scope.key)
        ancestors_payload = []
        ancestor_parts: list[str] = []
        for scope in chain:
            memory_md = self.editorial_store.summarize_for_scope(scope.key, include_ancestors=False, max_chars=1800)
            context = self.workspace.context_summary(scope.relative_path, max_chars=1800)
            payload = {
                "key": scope.key,
                "level": scope.level,
                "label": scope.label,
                "memory": memory_md,
                "context": context,
            }
            ancestors_payload.append(payload)
            ancestor_parts.append(
                f"## {scope.level} | {scope.label}\n\nMemoria:\n{memory_md or 'Sin memoria persistente.'}\n\nContexto:\n{context}"
            )

        parent_memory = self.editorial_store.summarize_for_scope(parent_scope.key, include_ancestors=False, max_chars=2500)
        parent_context = self.workspace.context_summary(parent_scope.relative_path, max_chars=2500)
        parent_payload = {
            "key": parent_scope.key,
            "level": parent_scope.level,
            "label": parent_scope.label,
            "memory": parent_memory,
            "context": parent_context,
        }
        parent_text = (
            f"Padre: {parent_scope.level} | {parent_scope.label}\n\n"
            f"Memoria:\n{parent_memory or 'Sin memoria persistente.'}\n\n"
            f"Contexto:\n{parent_context}"
        )

        sibling_scopes = [scope for scope in children.get(parent_scope.key, []) if scope.level == node.level]
        sibling_payload = []
        for scope in sibling_scopes:
            sibling_payload.append(
                {
                    "key": scope.key,
                    "label": scope.label,
                    "level": scope.level,
                    "relative_path": scope.relative_path,
                    "memory": self.editorial_store.summarize_for_scope(scope.key, include_ancestors=False, max_chars=900),
                }
            )
        for built in self.store.list_constructed_children(parent_scope.key, node.level):
            sibling_payload.append(
                {
                    "key": built["node_key"],
                    "label": built["node_name"],
                    "level": node.level,
                    "relative_path": built["relative_path"],
                    "memory": f"Nodo en construcción con estado {built['status']}",
                }
            )
        siblings_synthesis = self._synthesize_siblings(node.level, sibling_payload)

        inter_key = "interinstitucional"
        inter_text = self.editorial_store.summarize_for_scope(inter_key, include_ancestors=False, max_chars=2500)
        inter_scope = by_key.get(inter_key)
        inter_context = self.workspace.context_summary(inter_scope.relative_path, max_chars=2200) if inter_scope is not None else ""
        inter_payload = {
            "key": inter_key,
            "memory": inter_text,
            "context": inter_context,
        }
        ingestion_payload, ingestion_summary = self._build_ingestion_payload(request)
        destination_exists = node.output_dir.exists()
        if destination_exists:
            destination_context = self.workspace.context_summary(node.output_dir, max_chars=2200)
        else:
            destination_context = "Destino aún no creado en disco. Debes proponer estructura, assets y referencias editoriales iniciales sin inventar entregables finales."
        destination_payload = {
            "path": node.relative_path,
            "exists": destination_exists,
            "mode": node.operation_mode,
            "context": destination_context,
            "layout_contract": self._destination_contract(node),
        }
        unified_parent_context = self.editorial_context.build_for_scope(parent_scope.key, include_ancestors=True, max_chars=18000)
        return {
            "ancestors_payload": ancestors_payload,
            "ancestors_text": "\n\n".join(ancestor_parts) or "Sin ancestros disponibles.",
            "parent_payload": parent_payload,
            "parent_text": parent_text,
            "siblings_payload": sibling_payload,
            "siblings_synthesis": siblings_synthesis,
            "interinstitutional_payload": inter_payload,
            "interinstitutional_text": (
                f"Memoria:\n{inter_text or 'Sin memoria consolidada.'}\n\nContexto:\n{inter_context or 'Sin contexto adicional.'}"
            ),
            "ingestion_payload": ingestion_payload,
            "ingestion_summary": ingestion_summary,
            "ingestion_manifest": {
                "has_text": bool(ingestion_payload.get("text")),
                "has_document": bool(ingestion_payload.get("document", {}).get("path")),
                "document_path": ingestion_payload.get("document", {}).get("path", ""),
            },
            "ingestion_text": self._render_ingestion_text(ingestion_payload, ingestion_summary),
            "destination_payload": destination_payload,
            "destination_text": (
                f"Destino: {node.relative_path}\n"
                f"Modo: {node.operation_mode}\n"
                f"Existe en disco: {'sí' if destination_exists else 'no'}\n\n"
                f"Contrato de layout:\n{destination_payload['layout_contract']}\n\n"
                f"Contexto del destino:\n{destination_context}"
            ),
            "unified_editorial_context": unified_parent_context.markdown,
        }

    def _synthesize_siblings(self, node_level: str, siblings_payload: list[dict]) -> str:
        if not siblings_payload:
            return "No existen hermanos previos para sintetizar. Debes proponer una base editorial fundacional desde ancestros y padre."

        labels = ", ".join(item["label"] for item in siblings_payload[:12])
        with_memory = sum(1 for item in siblings_payload if item.get("memory"))
        docs = []
        activity_numbers = []
        for item in siblings_payload:
            rel = item.get("relative_path", "")
            root = self.workspace.resolve_target(rel) if rel else None
            if root is None or not root.exists():
                continue
            if root.is_dir():
                docs.extend(path.name for path in sorted(root.glob("*.bib"))[:3])
                docs.extend(path.name for path in sorted(root.glob("reporte-*.tex"))[:3])
                docs.extend(path.name for path in sorted(root.glob("presentacion-*.tex"))[:3])
            match = re.search(r"Actividad\s+(\d+)", item.get("label", ""), re.IGNORECASE)
            if match:
                activity_numbers.append(int(match.group(1)))

        repeated_docs = _top_repeated(_dedupe_lines(docs), docs)
        synthesis = [
            f"- Hermanos existentes: {len(siblings_payload)} de nivel {node_level}.",
            f"- Nombres de referencia: {labels}.",
            f"- Hermanos con memoria o antecedentes registrados: {with_memory}.",
        ]
        if repeated_docs:
            synthesis.append(f"- Artefactos recurrentes detectados: {', '.join(repeated_docs)}.")
        if activity_numbers:
            synthesis.append(
                f"- Numeración de actividades ya usada: {', '.join(str(number) for number in sorted(set(activity_numbers)))}."
            )
        synthesis.extend(
            [
                "- Sintetiza patrones de estructura, longitud típica, bibliografía recurrente, criterios de evaluación y estilo sin copiar contenido literal.",
                "- Usa a los hermanos solo como contraste editorial para homogeneizar la nueva propuesta.",
            ]
        )
        return "\n".join(synthesis)

    def _build_prompt(
        self,
        request: ConstructionRequest,
        parent_scope: EditorialScope,
        node: ConstructionNodeSpec,
        inputs: dict,
        consolidated: dict,
        cycle_index: int,
    ) -> str:
        reinforcement_hint = ""
        if node.operation_mode == "reforzar" or cycle_index > 1:
            reinforcement_hint = self._build_reinforcement_focus(consolidated, node)
        return (
            "Eres AulaTeX en modo GENERACION EDITORIAL DESCENDENTE. Este flujo crea o refuerza nodos editoriales. "
            "No investigues a fondo, no redactes la actividad completa y no ejecutes el flujo del Agente. "
            "Tu trabajo es producir memoria fundacional, plan editorial y una maqueta inicial reutilizable. "
            "Responde solo JSON valido.\n\n"
            f"Padre editorial: {parent_scope.level} | {parent_scope.key}\n"
            f"Nodo a crear: {node.level} | {node.label}\n"
            f"Modo de operacion: {node.operation_mode}\n"
            f"Ruta objetivo: {node.relative_path}\n"
            f"Ciclo: {cycle_index}\n"
            "Orden de fusion: union + deduplicacion sin regresion.\n\n"
            "Esquema obligatorio:\n"
            "{\n"
            '  "memoria_fundacional": {\n'
            '    "summary": ["..."],\n'
            '    "identity_rules": ["..."],\n'
            '    "structure_rules": ["..."],\n'
            '    "style_rules": ["..."],\n'
            '    "quality_gates": ["..."],\n'
            '    "latex_rules": ["..."],\n'
            '    "bibliography_rules": ["..."],\n'
            '    "research_markers": ["..."]\n'
            "  },\n"
            '  "plan_editorial": {\n'
            '    "objetivo_editorial": ["..."],\n'
            '    "alcance": ["..."],\n'
            '    "estructura_base": ["..."],\n'
            '    "criterios_evaluacion": ["..."],\n'
            '    "bibliografia_requerida": ["..."],\n'
            '    "riesgos": ["..."],\n'
            '    "siguiente_fase_agente": ["..."]\n'
            "  },\n"
            '  "maqueta_inicial": {\n'
            '    "titulo": "...",\n'
            '    "objetivo": ["..."],\n'
            '    "competencias": ["..."],\n'
            '    "resultados_esperados": ["..."],\n'
            '    "estructura_sugerida": ["..."],\n'
            '    "criterios_evaluacion": ["..."],\n'
            '    "bibliografia_requerida": ["..."],\n'
            '    "marcadores_investigacion": ["..."]\n'
            "  },\n"
            '  "tex_editorial": {\n'
            '    "plantilla": ["..."],\n'
            '    "actividad": ["..."],\n'
            '    "reporte": ["..."],\n'
            '    "presentacion": ["..."]\n'
            "  }\n"
            "}\n\n"
            "Restricciones:\n"
            "- No copies memoria de hermanos literalmente; solo sintetiza patrones recurrentes.\n"
            "- La maqueta.tex debe quedar lista para que el Agente luego investigue, redacte, evalúe y compile.\n"
            "- No generes la actividad completa ni bibliografía inventada.\n"
            "- Si el modo es reforzar, mejora la memoria existente sin perder reglas previas útiles.\n"
            "- Si hay ingesta textual o documental, úsala como restricción editorial y como material base para orientar el TEX final.\n"
            "- Usa bullets breves, accionables y deduplicados.\n"
            f"{reinforcement_hint}\n"
            f"Memoria consolidada actual:\n{json.dumps(consolidated, ensure_ascii=False, indent=2)}\n\n"
            f"Memoria de ancestros:\n{inputs['ancestors_text']}\n\n"
            f"Memoria del padre:\n{inputs['parent_text']}\n\n"
            f"Sintesis de hermanos:\n{inputs['siblings_synthesis']}\n\n"
            f"Ingesta adicional:\n{inputs['ingestion_text']}\n\n"
            f"Contexto del destino:\n{inputs['destination_text']}\n\n"
            f"Contexto editorial unificado del padre/nodo:\n{inputs.get('unified_editorial_context') or 'Sin contexto editorial unificado.'}\n\n"
            f"Reglas interinstitucionales:\n{inputs['interinstitutional_text']}\n"
        )

    def _build_reinforcement_focus(self, consolidated: dict, node: ConstructionNodeSpec) -> str:
        payload = _normalize_construction_payload(consolidated, node)
        gaps: list[str] = []

        missing_memory = [section for section in FUNDATIONAL_MEMORY_SECTIONS if not payload["memoria_fundacional"].get(section)]
        if missing_memory:
            gaps.append(f"Completa memoria fundacional faltante: {', '.join(missing_memory)}.")

        weak_plan = [
            section
            for section in PLAN_SECTIONS
            if len(payload["plan_editorial"].get(section, [])) < 1
        ]
        if weak_plan:
            gaps.append(f"Cierra huecos del plan editorial: {', '.join(weak_plan)}.")

        weak_tex = [
            section
            for section in EDITORIAL_TEX_SECTIONS
            if len(payload["tex_editorial"].get(section, [])) < 2
        ]
        if weak_tex:
            gaps.append(f"Vuelve específicas las indicaciones por entregable en: {', '.join(weak_tex)}.")

        if len(payload["maqueta_inicial"].get("criterios_evaluacion", [])) < 2:
            gaps.append("Refuerza criterios de evaluación de la maqueta con señales verificables y no genéricas.")

        if len(payload["maqueta_inicial"].get("estructura_sugerida", [])) < 2:
            gaps.append("Define una estructura sugerida más operativa para reporte, presentación y futuras actividades.")

        if not gaps:
            gaps.append("No dupliques contenido: mejora especificidad, trazabilidad y consistencia entre memoria, maqueta y entregables.")

        lines = [
            "- En esta pasada debes reforzar primero los huecos concretos detectados, antes de agregar nuevas variantes.",
            *[f"- {gap}" for gap in gaps],
            "- Si una sección ya es suficiente, no la reescribas; solo añade reglas que mejoren precisión editorial o trazabilidad.",
            "- Prioriza herencia ascendente utilizable en reporte y presentación, no solo bullets genéricos de memoria.",
        ]
        return "\\n".join(lines)

    def _parse_response(self, response_text: str, node: ConstructionNodeSpec, engine: str) -> dict:
        payload = _extract_first_json(response_text)
        if isinstance(payload, dict):
            return payload
        bullets = _extract_bullets(response_text)
        return {
            "memoria_fundacional": {
                "summary": bullets[:6] or [f"Salida no estructurada desde {engine} para {node.label}"],
                "identity_rules": [f"Validar respuesta manualmente antes de promover el nodo {node.key}."],
                "structure_rules": [],
                "style_rules": [],
                "quality_gates": ["Respuesta sin JSON válido; revisar antes de usar aguas abajo."],
                "latex_rules": [],
                "bibliography_rules": [],
                "research_markers": [],
            },
            "plan_editorial": {
                "objetivo_editorial": [f"Normalizar propuesta de {node.label}."],
                "alcance": [],
                "estructura_base": [],
                "criterios_evaluacion": ["Revisar estructura y consistencia antes de pasar al Agente."],
                "bibliografia_requerida": [],
                "riesgos": ["La propuesta requiere estructuración adicional."],
                "siguiente_fase_agente": ["Investigar y completar lagunas detectadas."],
            },
            "maqueta_inicial": {
                "titulo": node.label,
                "objetivo": [f"Completar la maqueta inicial de {node.label}."],
                "competencias": [],
                "resultados_esperados": [],
                "estructura_sugerida": [],
                "criterios_evaluacion": [],
                "bibliografia_requerida": [],
                "marcadores_investigacion": ["Definir fuentes, citas y vacíos de contenido antes de redactar."],
            },
            "tex_editorial": {
                "plantilla": ["Definir plantilla base con reglas editoriales, assets y referencias de estilo antes de redactar."],
                "actividad": ["Desarrollar la actividad respetando objetivo, criterios de evaluación y marcadores de investigación."],
                "reporte": ["Estructurar el reporte con bibliografía requerida y cierre verificable."],
                "presentacion": ["Preparar la presentación con síntesis visual, continuidad editorial y evidencias clave."],
            },
        }

    def _merge_payload(self, current: dict, candidate: dict, node: ConstructionNodeSpec, inputs: dict) -> dict:
        merged = _normalize_construction_payload(current, node)
        candidate_payload = _normalize_construction_payload(candidate, node)
        for section in FUNDATIONAL_MEMORY_SECTIONS:
            merged["memoria_fundacional"][section] = _dedupe_lines(
                merged["memoria_fundacional"].get(section, []) + candidate_payload["memoria_fundacional"].get(section, [])
            )
        for section in PLAN_SECTIONS:
            merged["plan_editorial"][section] = _dedupe_lines(
                merged["plan_editorial"].get(section, []) + candidate_payload["plan_editorial"].get(section, [])
            )
        current_title = merged["maqueta_inicial"].get("titulo", "").strip()
        candidate_title = candidate_payload["maqueta_inicial"].get("titulo", "").strip()
        merged["maqueta_inicial"]["titulo"] = candidate_title or current_title or node.label
        for field in MAQUETA_LIST_FIELDS:
            merged["maqueta_inicial"][field] = _dedupe_lines(
                merged["maqueta_inicial"].get(field, []) + candidate_payload["maqueta_inicial"].get(field, [])
            )
        for section in EDITORIAL_TEX_SECTIONS:
            merged["tex_editorial"][section] = _dedupe_lines(
                merged["tex_editorial"].get(section, []) + candidate_payload["tex_editorial"].get(section, [])
            )
        merged["node"] = {
            "key": node.key,
            "level": node.level,
            "label": node.label,
            "relative_path": node.relative_path,
        }
        merged["input_summary"] = {
            "parent_scope_key": node.parent_scope_key,
            "ancestor_count": len(inputs.get("ancestors_payload", [])),
            "sibling_count": len(inputs.get("siblings_payload", [])),
        }
        return merged

    def _finalize_payload(self, payload: dict, node: ConstructionNodeSpec, inputs: dict) -> dict:
        normalized = _normalize_construction_payload(payload, node)
        normalized["input_memory"] = {
            "ancestors": inputs["ancestors_payload"],
            "parent": inputs["parent_payload"],
            "siblings_synthesis": inputs["siblings_synthesis"],
            "ingesta": inputs["ingestion_payload"],
            "destino": inputs["destination_payload"],
            "reglas_interinstitucionales": inputs["interinstitutional_payload"],
        }
        defaults = self._default_tex_editorial_guidance(node, normalized, inputs)
        for section in EDITORIAL_TEX_SECTIONS:
            normalized["tex_editorial"][section] = _dedupe_lines(
                normalized["tex_editorial"].get(section, []) + defaults.get(section, [])
            )
        artifact_names = _construction_artifact_names(
            node_level=node.level,
            node_name=node.name,
            output_dir=node.output_dir,
            activity_number=int(node.activity_number),
        )
        normalized["generation_contract"] = {
            "mode": node.operation_mode,
            "destination_path": node.relative_path,
            "files": [artifact_names["memory"], "plan.md"],
        }
        normalized["future_agent_contract"] = {
            "status": "ready-for-agent",
            "allowed_actions": ["investigar", "redactar", "evaluar", "compilar"],
            "entrypoint": node.future_agent_entrypoint,
            "notes": "El Agente debe consumir esta maqueta sin recrear el nodo ni reconstruir memoria fundacional.",
        }
        return normalized

    def _render_plan_markdown(self, node: ConstructionNodeSpec, payload: dict) -> str:
        plan = payload["plan_editorial"]
        lines = [
            "# Plan editorial fundacional",
            "",
            f"- Nodo: {node.label}",
            f"- Nivel: {node.level}",
            f"- Padre: {node.parent_scope_key}",
            f"- Modo: {node.operation_mode}",
            f"- Destino: {node.relative_path}",
            f"- Entrada futura del agente: {payload['future_agent_contract']['entrypoint']}",
            f"- Ingesta textual: {'sí' if payload.get('input_memory', {}).get('ingesta', {}).get('text') else 'no'}",
            f"- Ingesta documental: {'sí' if payload.get('input_memory', {}).get('ingesta', {}).get('document', {}).get('path') else 'no'}",
            "",
        ]
        titles = {
            "objetivo_editorial": "Objetivo editorial",
            "alcance": "Alcance",
            "estructura_base": "Estructura base",
            "criterios_evaluacion": "Criterios de evaluación",
            "bibliografia_requerida": "Bibliografía requerida",
            "riesgos": "Riesgos",
            "siguiente_fase_agente": "Fase siguiente del agente",
        }
        for section in PLAN_SECTIONS:
            lines.append(f"## {titles[section]}")
            lines.append("")
            items = plan.get(section, [])
            if items:
                lines.extend(f"- {item}" for item in items)
            else:
                lines.append("- Pendiente de consolidar.")
            lines.append("")
        return "\n".join(lines)

    def _render_maqueta_tex(self, node: ConstructionNodeSpec, payload: dict) -> str:
        maqueta = payload["maqueta_inicial"]
        tex_editorial = payload.get("tex_editorial", {})
        ingesta = payload.get("input_memory", {}).get("ingesta", {})
        title = _latex_escape(maqueta.get("titulo") or node.label)
        sections = [
            ("Objetivo", maqueta.get("objetivo", [])),
            ("Competencias", maqueta.get("competencias", [])),
            ("Resultados esperados", maqueta.get("resultados_esperados", [])),
            ("Estructura sugerida", maqueta.get("estructura_sugerida", [])),
            ("Criterios de evaluación", maqueta.get("criterios_evaluacion", [])),
            ("Bibliografía requerida", maqueta.get("bibliografia_requerida", [])),
            ("Marcadores de investigación", maqueta.get("marcadores_investigacion", [])),
        ]
        lines = [
            "% AulaTeX - maqueta inicial de construcción descendente",
            "% Contrato futuro: el Agente puede investigar, redactar, evaluar y compilar a partir de este archivo.",
            "\\documentclass[12pt]{article}",
            "\\usepackage[utf8]{inputenc}",
            "\\usepackage[T1]{fontenc}",
            "\\usepackage[spanish]{babel}",
            "\\usepackage{enumitem}",
            "\\usepackage{hyperref}",
            "\\usepackage{longtable}",
            "",
            f"\\title{{{title}}}",
            "\\author{AulaTeX}",
            "\\date{\\today}",
            "",
            "\\begin{document}",
            "\\maketitle",
            "",
            f"\\noindent\\textbf{{Nodo editorial:}} {_latex_escape(node.key)}\\\\",
            f"\\textbf{{Padre editorial:}} {_latex_escape(node.parent_scope_key)}\\\\",
            f"\\textbf{{Modo de generación:}} {_latex_escape(node.operation_mode)}\\\\",
            f"\\textbf{{Destino:}} {_latex_escape(node.relative_path)}\\\\",
            f"\\textbf{{Contrato futuro:}} {_latex_escape(payload['future_agent_contract']['status'])}",
            "",
        ]
        lines.extend(
            [
                "\\section*{Ingesta base}",
                "\\begin{itemize}[leftmargin=*]",
                f"  \\item Texto libre proporcionado: {_latex_escape('sí' if ingesta.get('text') else 'no')}",
                f"  \\item Documento de apoyo proporcionado: {_latex_escape(ingesta.get('document', {}).get('path') or 'no')}",
                "\\end{itemize}",
                "",
            ]
        )
        if ingesta.get("text"):
            lines.extend(
                [
                    "\\subsection*{Resumen de la ingesta textual}",
                    "\\begin{quote}",
                    _latex_escape(_truncate_text(ingesta.get("text", ""), 1200)),
                    "\\end{quote}",
                    "",
                ]
            )
        document_excerpt = ingesta.get("document", {}).get("excerpt", "")
        if document_excerpt:
            lines.extend(
                [
                    "\\subsection*{Resumen del documento de apoyo}",
                    "\\begin{quote}",
                    _latex_escape(_truncate_text(document_excerpt, 1200)),
                    "\\end{quote}",
                    "",
                ]
            )
        for heading, items in sections:
            lines.extend(
                [
                    f"\\section*{{{_latex_escape(heading)}}}",
                    "\\begin{itemize}[leftmargin=*]",
                ]
            )
            safe_items = items or ["Pendiente de desarrollo en la siguiente fase del Agente."]
            lines.extend(f"  \\item {_latex_escape(item)}" for item in safe_items)
            lines.extend(["\\end{itemize}", ""])
        lines.extend(
            [
                "\\section*{Indicaciones editoriales por entregable}",
                "",
            ]
        )
        tex_titles = {
            "plantilla": "Plantilla",
            "actividad": "Actividad",
            "reporte": "Reporte",
            "presentacion": "Presentación",
        }
        for section in EDITORIAL_TEX_SECTIONS:
            lines.extend(
                [
                    f"\\subsection*{{{_latex_escape(tex_titles[section])}}}",
                    "\\begin{itemize}[leftmargin=*]",
                ]
            )
            section_items = tex_editorial.get(section, []) or ["Pendiente de consolidar en siguientes ciclos."]
            lines.extend(f"  \\item {_latex_escape(item)}" for item in section_items)
            lines.extend(["\\end{itemize}", ""])
        lines.extend(["\\end{document}", ""])
        return "\n".join(lines)

    def _memory_summary(self, memory: dict) -> str:
        chunks = []
        for section in FUNDATIONAL_MEMORY_SECTIONS:
            items = memory.get(section, [])
            if items:
                chunks.append(f"{section}: {len(items)}")
        return ", ".join(chunks) or "Sin memoria fundacional consolidada."

    def _build_ingestion_payload(self, request: ConstructionRequest) -> tuple[dict, str]:
        text = re.sub(r"\s+", " ", (request.ingest_text or "")).strip()
        payload: dict = {
            "text": text,
            "document": {},
        }
        summary_parts: list[str] = []
        if text:
            summary_parts.append(f"Texto libre: {min(len(text), 4000)} chars")
        document_path = (request.ingest_document_path or "").strip()
        if document_path:
            resolved = self.workspace.resolve_target(document_path)
            if not resolved.exists() or not resolved.is_file():
                raise ValueError(f"Documento de ingesta no encontrado: {document_path}")
            payload["document"] = self._extract_document_payload(resolved)
            summary_parts.append(f"Documento: {payload['document'].get('path', document_path)}")
        if not summary_parts:
            summary_parts.append("Sin ingesta adicional.")
        return payload, " | ".join(summary_parts)

    def _render_ingestion_text(self, payload: dict, summary: str) -> str:
        lines = [summary]
        text = payload.get("text", "")
        if text:
            lines.extend(["", "Texto libre:", _truncate_text(text, 1800)])
        document = payload.get("document", {})
        if isinstance(document, dict) and document.get("path"):
            lines.extend(
                [
                    "",
                    f"Documento: {document.get('path')}",
                    f"Tipo: {document.get('kind', 'desconocido')}",
                    document.get("note", ""),
                    _truncate_text(document.get("excerpt", ""), 2200),
                ]
            )
        return "\n".join(line for line in lines if line)

    def _extract_document_payload(self, path: Path) -> dict:
        suffix = path.suffix.lower()
        excerpt = ""
        note = ""
        kind = suffix.lstrip(".") or "archivo"
        if suffix in {".md", ".txt", ".tex", ".bib", ".json", ".yml", ".yaml"}:
            excerpt = path.read_text(encoding="utf-8", errors="replace")
            kind = "texto"
        elif suffix == ".docx":
            kind = "docx"
            try:
                with zipfile.ZipFile(path) as archive:
                    document_xml = archive.read("word/document.xml").decode("utf-8", errors="replace")
                excerpt = re.sub(r"<[^>]+>", " ", document_xml)
                excerpt = html.unescape(re.sub(r"\s+", " ", excerpt)).strip()
            except (KeyError, OSError, zipfile.BadZipFile) as exc:
                note = f"No se pudo extraer texto de DOCX: {exc}"
        else:
            kind = "binario"
            note = "Tipo de documento no extraíble automáticamente; se usará solo como referencia contextual."
        return {
            "path": self.workspace.relative(path),
            "kind": kind,
            "note": note,
            "excerpt": _truncate_text(excerpt, 6000),
            "size_bytes": path.stat().st_size,
        }

    def _default_tex_editorial_guidance(self, node: ConstructionNodeSpec, payload: dict, inputs: dict) -> dict:
        memory = payload.get("memoria_fundacional", {})
        plan = payload.get("plan_editorial", {})
        maqueta = payload.get("maqueta_inicial", {})
        ingestion = inputs.get("ingestion_payload", {})
        destination = inputs.get("destination_payload", {})
        text_hint = "Usa la ingesta proporcionada como restricción editorial inicial." if ingestion.get("text") or ingestion.get("document", {}).get("path") else "Trabaja con la memoria fundacional consolidada como fuente base."
        return {
            "plantilla": _dedupe_lines(
                [
                    destination.get("layout_contract", ""),
                    *memory.get("latex_rules", [])[:3],
                    *memory.get("structure_rules", [])[:3],
                    text_hint,
                ]
            ),
            "actividad": _dedupe_lines(
                [
                    *maqueta.get("objetivo", [])[:2],
                    *maqueta.get("criterios_evaluacion", [])[:3],
                    *memory.get("research_markers", [])[:3],
                    text_hint,
                ]
            ),
            "reporte": _dedupe_lines(
                [
                    *plan.get("estructura_base", [])[:3],
                    *memory.get("style_rules", [])[:3],
                    *memory.get("bibliography_rules", [])[:3],
                    *memory.get("quality_gates", [])[:3],
                ]
            ),
            "presentacion": _dedupe_lines(
                [
                    *maqueta.get("resultados_esperados", [])[:3],
                    *memory.get("style_rules", [])[:2],
                    *plan.get("alcance", [])[:2],
                    "Sintetiza visualmente la memoria editorial sin perder continuidad con plantilla, actividad y reporte.",
                ]
            ),
        }

    def _load_existing_payload(self, node: ConstructionNodeSpec) -> dict:
        payload = _empty_construction_payload(node)
        if node.operation_mode != "reforzar":
            return payload
        for candidate in _construction_memory_candidates(node):
            if not candidate.exists() or not candidate.is_file():
                continue
            try:
                existing = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            return _normalize_construction_payload(existing, node)
        return payload

    def _destination_contract(self, node: ConstructionNodeSpec) -> str:
        contracts = {
            "institucion": "Prepara una raíz institucional reutilizable con carpetas por carrera, carpeta assets y referencias claras a plantillas LaTeX compartidas.",
            "carrera": "Prepara una carrera como contenedor de materias, reutilizando assets y lineamientos de la institución padre.",
            "materia": "Prepara una materia con estructura apta para actividades, bibliografía y entregables académicos reutilizables.",
            "actividad": "Prepara una actividad con maqueta base, criterios de evaluación, bibliografía requerida y marcadores de investigación sin redactar el entregable completo.",
        }
        return contracts.get(node.level, "Prepara una estructura editorial reusable y coherente con AulaTeX.")

    def _write_node_marker(self, node: ConstructionNodeSpec, payload: dict) -> None:
        marker_path = node.output_dir / GENERATION_MARKER_FILENAME
        marker = {
            "key": node.key,
            "level": node.level,
            "label": node.label,
            "name": node.name,
            "parent_scope_key": node.parent_scope_key,
            "activity_number": int(node.activity_number),
            "relative_path": node.relative_path,
            "operation_mode": node.operation_mode,
            "entrypoint": payload.get("future_agent_contract", {}).get("entrypoint", ""),
        }
        marker_path.write_text(json.dumps(marker, ensure_ascii=False, indent=2), encoding="utf-8")

    def _emit(self, callback: Callable[[ConstructionEvent], None] | None, event: ConstructionEvent) -> None:
        if callback is not None:
            callback(event)

    def _is_cancelled(self, cancel_event: Event | None) -> bool:
        return bool(cancel_event is not None and cancel_event.is_set())


def _empty_construction_payload(node: ConstructionNodeSpec) -> dict:
    return _normalize_construction_payload({}, node)


def _construction_artifact_names(
    *,
    node_level: str,
    node_name: str,
    output_dir: Path,
    activity_number: int,
) -> dict[str, str]:
    folder_slug = output_dir.name
    if node_level == "materia":
        base_slug = re.sub(r"-(lde|lad|mga|isc|imtc)$", "", folder_slug, flags=re.IGNORECASE)
    elif node_level == "actividad":
        base_slug = f"actividad-{int(activity_number):02d}-{_slugify(node_name)}"
    else:
        base_slug = _slugify(node_name) or _slugify(folder_slug) or node_level
    base_slug = base_slug.strip("-") or node_level
    return {
        "memory": f"memoria-fundacional-{base_slug}.json",
        "maqueta": f"maqueta-{base_slug}.tex",
    }


def _construction_memory_candidates(node: ConstructionNodeSpec) -> tuple[Path, ...]:
    artifact_names = _construction_artifact_names(
        node_level=node.level,
        node_name=node.name,
        output_dir=node.output_dir,
        activity_number=int(node.activity_number),
    )
    return (
        node.output_dir / artifact_names["memory"],
        node.output_dir / "memoria-fundacional.json",
        node.output_dir / "memory-fundacional.json",
    )


def _normalize_construction_payload(payload: dict, node: ConstructionNodeSpec) -> dict:
    normalized = {
        "node": {
            "key": node.key,
            "level": node.level,
            "label": node.label,
            "relative_path": node.relative_path,
        },
        "memoria_fundacional": {section: [] for section in FUNDATIONAL_MEMORY_SECTIONS},
        "plan_editorial": {section: [] for section in PLAN_SECTIONS},
        "maqueta_inicial": {"titulo": node.label, **{field: [] for field in MAQUETA_LIST_FIELDS}},
        "tex_editorial": {section: [] for section in EDITORIAL_TEX_SECTIONS},
        "input_summary": {},
    }
    if not isinstance(payload, dict):
        return normalized
    memory = payload.get("memoria_fundacional", {})
    if isinstance(memory, dict):
        for section in FUNDATIONAL_MEMORY_SECTIONS:
            normalized["memoria_fundacional"][section] = _normalize_list(memory.get(section, []))
    plan = payload.get("plan_editorial", {})
    if isinstance(plan, dict):
        for section in PLAN_SECTIONS:
            normalized["plan_editorial"][section] = _normalize_list(plan.get(section, []))
    maqueta = payload.get("maqueta_inicial", {})
    if isinstance(maqueta, dict):
        title = maqueta.get("titulo")
        if isinstance(title, str) and title.strip():
            normalized["maqueta_inicial"]["titulo"] = re.sub(r"\s+", " ", title).strip()
        for field in MAQUETA_LIST_FIELDS:
            normalized["maqueta_inicial"][field] = _normalize_list(maqueta.get(field, []))
    tex_editorial = payload.get("tex_editorial", {})
    if isinstance(tex_editorial, dict):
        for section in EDITORIAL_TEX_SECTIONS:
            normalized["tex_editorial"][section] = _normalize_list(tex_editorial.get(section, []))
    input_summary = payload.get("input_summary", {})
    if isinstance(input_summary, dict):
        normalized["input_summary"] = input_summary
    return normalized


def _normalize_list(value: list[str] | str) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return _dedupe_lines(value)


def _dedupe_lines(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if not isinstance(item, str):
            continue
        normalized = re.sub(r"\s+", " ", item).strip(" -\t\r\n")
        if not normalized:
            continue
        marker = normalized.lower()
        if marker in seen:
            continue
        seen.add(marker)
        out.append(normalized)
    return out


def _top_repeated(unique_values: list[str], all_values: list[str], limit: int = 6) -> list[str]:
    counts = {value: 0 for value in unique_values}
    for value in all_values:
        if value in counts:
            counts[value] += 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [value for value, count in ordered if count > 1][:limit]


def _slugify(text: str) -> str:
    collapsed = re.sub(r"\s+", "-", text.strip().lower())
    cleaned = re.sub(r"[^a-z0-9\-_]+", "-", collapsed)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned or "nuevo-nodo"


def _count_memory_items(memory: dict) -> int:
    return sum(len(memory.get(section, [])) for section in FUNDATIONAL_MEMORY_SECTIONS)


def _count_sections(payload: dict) -> int:
    sections = 0
    for section in FUNDATIONAL_MEMORY_SECTIONS:
        if payload["memoria_fundacional"].get(section):
            sections += 1
    for section in PLAN_SECTIONS:
        if payload["plan_editorial"].get(section):
            sections += 1
    if payload["maqueta_inicial"].get("titulo"):
        sections += 1
    for field in MAQUETA_LIST_FIELDS:
        if payload["maqueta_inicial"].get(field):
            sections += 1
    for field in EDITORIAL_TEX_SECTIONS:
        if payload.get("tex_editorial", {}).get(field):
            sections += 1
    return sections


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


def _latex_escape(value: str) -> str:
    replacements = {
        "\\": r"\\textbackslash{}",
        "&": r"\\&",
        "%": r"\\%",
        "$": r"\\$",
        "#": r"\\#",
        "_": r"\\_",
        "{": r"\\{",
        "}": r"\\}",
        "~": r"\\textasciitilde{}",
        "^": r"\\textasciicircum{}",
    }
    text = value or ""
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _truncate_text(text: str, max_chars: int) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."