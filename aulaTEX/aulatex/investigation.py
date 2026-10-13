from __future__ import annotations

import html
import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Callable
from urllib.parse import parse_qs, unquote, urlparse

try:
    import requests
except ModuleNotFoundError:
    requests = None

from .config import diagnostic_metrics_enabled
from .editorial_memory import ENGINE_PRIORITY, EditorialMemoryStore
from .langchain_adapter import AulaTeXLLMInterface, AulaTeXLangChainAdapter
from .llm_bridge import DEFAULT_MAX_TOKENS
from .llm_bridge import LLM_ENGINES, AulaTeXLLMClient
from .workspace import AulaTeXWorkspace, EditorialScope


KNOWLEDGE_SECTIONS = (
    "scope_profile",
    "local_inventory",
    "web_findings",
    "bibliography_notes",
    "asset_targets",
    "reference_targets",
    "analytical_program",
    "recommended_queries",
    "open_questions",
    "next_actions",
)


@dataclass(frozen=True)
class InvestigationRequest:
    scope_key: str
    iterations: int = 2
    engines: list[str] | tuple[str, ...] = ("Codex", "Auto (model-router)", "Claude Foundry", "GPT-Pro")
    max_tokens: int = DEFAULT_MAX_TOKENS
    search_terms: tuple[str, ...] = ()
    seed_urls: tuple[str, ...] = ()


@dataclass(frozen=True)
class InvestigationEvent:
    kind: str
    message: str
    current: int = 0
    total: int = 0
    scope_key: str = ""
    engine: str = ""
    cycle: int = 0


@dataclass(frozen=True)
class InvestigationBuildResult:
    run_id: str
    run_dir: Path
    manifest_path: Path
    knowledge_path: Path
    bibliography_path: Path
    web_sources_path: Path
    ok: bool
    cancelled: bool = False


@dataclass(frozen=True)
class WebSource:
    title: str
    url: str
    snippet: str
    origin: str


class InvestigationStore:
    def __init__(self, workspace: AulaTeXWorkspace | None = None, *, diagnostics_enabled: bool | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.diagnostics_enabled = diagnostic_metrics_enabled() if diagnostics_enabled is None else diagnostics_enabled
        self.root = self.workspace.feedback_root / "investigacion"
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "investigacion.db"
        self.scopes_dir = self.root / "scopes"
        self.scopes_dir.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

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

                CREATE TABLE IF NOT EXISTS knowledge (
                    scope_key TEXT PRIMARY KEY,
                    level TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    source_urls_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    scope_key TEXT NOT NULL,
                    iterations INTEGER NOT NULL,
                    engines_json TEXT NOT NULL,
                    queries_json TEXT NOT NULL,
                    urls_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    ok INTEGER NOT NULL DEFAULT 0,
                    cancelled INTEGER NOT NULL DEFAULT 0
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

    def start_run(self, run_id: str, request: InvestigationRequest, engines: list[str]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO runs (run_id, scope_key, iterations, engines_json, queries_json, urls_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    request.scope_key,
                    int(request.iterations),
                    json.dumps(engines, ensure_ascii=False),
                    json.dumps(list(request.search_terms), ensure_ascii=False),
                    json.dumps(list(request.seed_urls), ensure_ascii=False),
                ),
            )

    def finish_run(self, run_id: str, *, ok: bool, cancelled: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE runs SET completed_at=CURRENT_TIMESTAMP, ok=?, cancelled=? WHERE run_id=?",
                (1 if ok else 0, 1 if cancelled else 0, run_id),
            )

    def record_cycle(self, *, run_id: str, scope_key: str, cycle_index: int, engine: str, ok: bool, response_text: str) -> None:
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

    def get_knowledge(self, scope_key: str) -> dict:
        with self._connect() as conn:
            row = conn.execute("SELECT payload_json FROM knowledge WHERE scope_key=?", (scope_key,)).fetchone()
        if row is None:
            return self._empty_payload()
        try:
            payload = json.loads(row["payload_json"])
        except json.JSONDecodeError:
            return self._empty_payload()
        return self._normalize_payload(payload)

    def save_knowledge(self, scope: EditorialScope, payload: dict, web_sources: list[WebSource]) -> None:
        normalized = self._normalize_payload(payload)
        self.upsert_scope(scope)
        sources_payload = [source.__dict__ for source in web_sources]
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO knowledge (scope_key, level, payload_json, source_urls_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(scope_key) DO UPDATE SET
                    level=excluded.level,
                    payload_json=excluded.payload_json,
                    source_urls_json=excluded.source_urls_json,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    scope.key,
                    scope.level,
                    json.dumps(normalized, ensure_ascii=False, indent=2),
                    json.dumps(sources_payload, ensure_ascii=False, indent=2),
                ),
            )
        slug = scope.key.replace("/", "__")
        (self.scopes_dir / f"{slug}.json").write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
        (self.scopes_dir / f"{slug}.md").write_text(self.render_knowledge_markdown(scope, normalized), encoding="utf-8")

    def render_knowledge_markdown(self, scope: EditorialScope, payload: dict | None = None) -> str:
        data = self._normalize_payload(payload or self.get_knowledge(scope.key))
        lines = [
            "# Base de conocimiento AulaTeX",
            "",
            f"- Alcance: {scope.level}",
            f"- Etiqueta: {scope.label}",
            f"- Ruta: {scope.relative_path or '.'}",
            f"- Bibliografia consolidada: {len(data.get('bib_entries', []))} entradas",
            "",
        ]
        for section in KNOWLEDGE_SECTIONS:
            items = data.get(section, [])
            if not items:
                continue
            lines.append(f"## {section}")
            lines.append("")
            lines.extend(f"- {item}" for item in items)
            lines.append("")
        if data.get("bib_entries"):
            lines.extend(["## bib_entries", ""])
            for entry in data["bib_entries"]:
                lines.append("```bibtex")
                lines.append(entry)
                lines.append("```")
                lines.append("")
        return "\n".join(lines)

    def render_metrics_markdown(self, scope_key: str) -> str:
        if not self.diagnostics_enabled:
            return "# Diagnóstico desactivado\n\n- Ejecuta AulaTeX con --diagnostics o define AULATEX_ENABLE_DIAGNOSTIC_METRICS=1 para medir desempeño.\n"
        with self._connect() as conn:
            by_engine = conn.execute(
                """
                SELECT engine, COUNT(*) AS calls, SUM(CASE WHEN ok = 1 THEN 1 ELSE 0 END) AS ok_calls,
                       AVG(response_chars) AS avg_chars, MAX(response_chars) AS max_chars
                FROM cycles WHERE scope_key=? GROUP BY engine ORDER BY engine
                """,
                (scope_key,),
            ).fetchall()
            by_cycle = conn.execute(
                """
                SELECT cycle_index, COUNT(*) AS calls, SUM(CASE WHEN ok = 1 THEN 1 ELSE 0 END) AS ok_calls,
                       AVG(response_chars) AS avg_chars
                FROM cycles WHERE scope_key=? GROUP BY cycle_index ORDER BY cycle_index
                """,
                (scope_key,),
            ).fetchall()
        lines = ["# Metricas de investigación", ""]
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
            lines.append("- Aun no hay ejecuciones registradas para este scope.")
        return "\n".join(lines)

    def _empty_payload(self) -> dict:
        payload = {section: [] for section in KNOWLEDGE_SECTIONS}
        payload["bib_entries"] = []
        payload["sources"] = []
        payload["schema_version"] = 1
        return payload

    def _normalize_payload(self, payload: dict) -> dict:
        normalized = self._empty_payload()
        if not isinstance(payload, dict):
            return normalized
        for section in KNOWLEDGE_SECTIONS:
            normalized[section] = _normalize_list(payload.get(section, []))
        normalized["bib_entries"] = _normalize_bib_entries(payload.get("bib_entries", []))
        normalized["sources"] = _normalize_list(payload.get("sources", []))
        return normalized


class InvestigationBuilder:
    def __init__(
        self,
        workspace: AulaTeXWorkspace | None = None,
        llm_bridge: AulaTeXLLMInterface | None = None,
        store: InvestigationStore | None = None,
        editorial_store: EditorialMemoryStore | None = None,
    ) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.llm = llm_bridge or AulaTeXLangChainAdapter(AulaTeXLLMClient())
        self.store = store or InvestigationStore(self.workspace)
        self.editorial_store = editorial_store or EditorialMemoryStore(self.workspace)

    def build(
        self,
        request: InvestigationRequest,
        progress: Callable[[InvestigationEvent], None] | None = None,
        cancel_event: Event | None = None,
    ) -> InvestigationBuildResult:
        run_id = self.workspace.timestamp()
        run_dir = self.store.root / "runs" / f"{run_id}-investigacion"
        run_dir.mkdir(parents=True, exist_ok=True)

        by_key, _children = self.workspace.editorial_scope_index()
        scope = by_key.get(request.scope_key)
        if scope is None:
            raise ValueError(f"Scope no encontrado: {request.scope_key}")

        engines = self._normalize_engines(request.engines)
        self.store.upsert_scope(scope)
        self.store.start_run(run_id, request, engines)

        queries = list(request.search_terms) or self.default_search_terms(scope)
        web_sources = self.collect_web_sources(queries, list(request.seed_urls))
        total = max(1, int(request.iterations)) * len(engines)
        current = 0
        overall_ok = True
        cancelled = False
        target_root = self.workspace.resolve_target(scope.relative_path or ".")

        self._emit(progress, InvestigationEvent("start", f"Investigación iniciada para {scope.label}", 0, total, scope.key))

        for cycle_index in range(1, max(1, int(request.iterations)) + 1):
            if self._is_cancelled(cancel_event):
                cancelled = True
                break
            for engine in engines:
                if self._is_cancelled(cancel_event):
                    cancelled = True
                    break
                current += 1
                self._emit(
                    progress,
                    InvestigationEvent(
                        "progress",
                        f"{scope.label} | ciclo {cycle_index} | {engine}",
                        current,
                        total,
                        scope.key,
                        engine,
                        cycle_index,
                    ),
                )
                prompt = self._build_prompt(scope, queries, web_sources, cycle_index)
                result = self.llm.call(engine, prompt, max_tokens=request.max_tokens)
                response_text = result.text if result.ok else result.error
                self.store.record_cycle(
                    run_id=run_id,
                    scope_key=scope.key,
                    cycle_index=cycle_index,
                    engine=result.engine,
                    ok=result.ok,
                    response_text=response_text,
                )
                candidate = self._parse_response(response_text, scope, result.engine, cycle_index)
                current_payload = self.store.get_knowledge(scope.key)
                merged = self._merge_payload(current_payload, candidate, scope, queries, web_sources)
                self.store.save_knowledge(scope, merged, web_sources)
                (run_dir / f"{current:04d}-{result.engine.replace(' ', '_')}-ciclo-{cycle_index}.md").write_text(response_text, encoding="utf-8")
                if not result.ok:
                    overall_ok = False
                self._emit(
                    progress,
                    InvestigationEvent(
                        "result",
                        f"{result.engine}: {'OK' if result.ok else 'ERROR'} ({len(response_text)} chars)",
                        current,
                        total,
                        scope.key,
                        result.engine,
                        cycle_index,
                    ),
                )

        final_payload = self.store.get_knowledge(scope.key)
        knowledge_dir = target_root / "investigacion-aulatex"
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        knowledge_path = knowledge_dir / "base-conocimiento.json"
        knowledge_path.write_text(json.dumps(final_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        (knowledge_dir / "base-conocimiento.md").write_text(self.store.render_knowledge_markdown(scope, final_payload), encoding="utf-8")
        web_sources_path = knowledge_dir / "fuentes-web.md"
        web_sources_path.write_text(self._render_web_sources_markdown(web_sources, queries), encoding="utf-8")
        bibliography_path = self._materialize_scope_artifacts(scope, target_root, final_payload, web_sources)

        manifest = {
            "run_id": run_id,
            "scope_key": scope.key,
            "iterations": int(request.iterations),
            "engines": engines,
            "queries": queries,
            "seed_urls": list(request.seed_urls),
            "web_sources": [source.__dict__ for source in web_sources],
            "knowledge_dir": self.workspace.relative(knowledge_dir),
            "knowledge_path": self.workspace.relative(knowledge_path),
            "web_sources_path": self.workspace.relative(web_sources_path),
            "bibliography_path": self.workspace.relative(bibliography_path),
            "ok": overall_ok and not cancelled,
            "cancelled": cancelled,
        }
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        self.store.finish_run(run_id, ok=overall_ok and not cancelled, cancelled=cancelled)
        self.workspace.append_bitacora(run_id, "investigacion", manifest)

        if cancelled:
            self._emit(progress, InvestigationEvent("cancelled", f"Investigación cancelada en {run_dir}", current, total, scope.key))
        else:
            self._emit(progress, InvestigationEvent("done", f"Investigación cerrada en {run_dir}", total, total, scope.key))
        return InvestigationBuildResult(
            run_id=run_id,
            run_dir=run_dir,
            manifest_path=manifest_path,
            knowledge_path=knowledge_path,
            bibliography_path=bibliography_path,
            web_sources_path=web_sources_path,
            ok=overall_ok and not cancelled,
            cancelled=cancelled,
        )

    def preview_markdown(self, scope: EditorialScope, search_terms: list[str] | None = None, seed_urls: list[str] | None = None) -> str:
        queries = search_terms or self.default_search_terms(scope)
        target_root = self.workspace.resolve_target(scope.relative_path or ".")
        lines = [
            f"Scope: {scope.level} | {scope.key}",
            f"Ruta: {scope.relative_path or '.'}",
            "",
            "Artefactos previstos:",
            f"- {self.workspace.relative(target_root / 'investigacion-aulatex' / 'base-conocimiento.json')}",
            f"- {self.workspace.relative(target_root / 'investigacion-aulatex' / 'base-conocimiento.md')}",
            f"- {self.workspace.relative(target_root / 'investigacion-aulatex' / 'fuentes-web.md')}",
            f"- {self.workspace.relative(self._preferred_bib_path(scope, target_root))}",
        ]
        references_dir = self._references_dir(scope, target_root)
        if references_dir is not None:
            lines.append(f"- {self.workspace.relative(references_dir)}")
        asset_dir = self._asset_dir(scope, target_root)
        if asset_dir is not None:
            lines.append(f"- {self.workspace.relative(asset_dir)}")
        analytical_program = self._analytical_program_path(scope, target_root)
        if analytical_program is not None:
            lines.append(f"- {self.workspace.relative(analytical_program)}")
        lines.extend(["", "Consultas sugeridas:"])
        lines.extend(f"- {item}" for item in queries)
        if seed_urls:
            lines.extend(["", "URLs semilla:"])
            lines.extend(f"- {item}" for item in seed_urls)
        return "\n".join(lines)

    def default_search_terms(self, scope: EditorialScope) -> list[str]:
        base_terms: list[str] = []
        if scope.level == "institucion":
            base_terms = [
                f"{scope.label} sitio oficial",
                f"{scope.label} oferta educativa pdf",
                f"{scope.label} identidad institucional logo oficial",
            ]
        elif scope.level == "carrera":
            base_terms = [
                f"{scope.career} {scope.institution} plan de estudios",
                f"{scope.career} {scope.institution} mapa curricular pdf",
                f"{scope.career} {scope.institution} bibliografia recomendada",
            ]
        elif scope.level == "materia":
            base_terms = [
                f"{scope.subject} {scope.institution} programa analitico",
                f"{scope.subject} bibliografia recomendada",
                f"{scope.subject} objetivos temario pdf",
            ]
        elif scope.level == "actividad":
            base_terms = [
                f"{scope.subject} {scope.institution} actividad {scope.activity}",
                f"{scope.subject} conceptos clave bibliografia",
                f"{scope.subject} autores fundamentales",
            ]
        return _normalize_list(base_terms)[:4]

    def collect_web_sources(self, search_terms: list[str], seed_urls: list[str]) -> list[WebSource]:
        sources: list[WebSource] = []
        for url in seed_urls[:6]:
            fetched = self._fetch_url(url, origin="seed")
            if fetched is not None:
                sources.append(fetched)
        for query in search_terms[:4]:
            sources.extend(self._search_query(query))
        deduped: list[WebSource] = []
        seen: set[str] = set()
        for source in sources:
            marker = source.url.strip().lower()
            if not marker or marker in seen:
                continue
            seen.add(marker)
            deduped.append(source)
        return deduped[:12]

    def _build_prompt(self, scope: EditorialScope, queries: list[str], web_sources: list[WebSource], cycle_index: int) -> str:
        current_payload = self.store.get_knowledge(scope.key)
        local_context = self.workspace.context_summary(scope.relative_path or ".", max_chars=4500)
        editorial_context = self.editorial_store.summarize_for_scope(scope.key, include_ancestors=True, max_chars=2800)
        web_context = self._render_web_context_for_prompt(web_sources)
        payload_json = json.dumps(current_payload, ensure_ascii=False, indent=2)
        return (
            "Eres AulaTeX en fase de Investigación. Debes consolidar base de conocimiento previa a extracción y redacción. "
            "Mapea fuentes locales, consultas web, bibliografía y artefactos faltantes sin inventar datos no sustentados. "
            "Responde solo JSON válido.\n\n"
            f"Scope: {scope.level} | {scope.key}\n"
            f"Iteración: {cycle_index}\n"
            f"Consultas previstas: {', '.join(queries) or 'sin consultas manuales'}\n\n"
            "Esquema requerido:\n"
            "{\n"
            '  "scope_profile": ["..."],\n'
            '  "local_inventory": ["..."],\n'
            '  "web_findings": ["..."],\n'
            '  "bibliography_notes": ["..."],\n'
            '  "asset_targets": ["..."],\n'
            '  "reference_targets": ["..."],\n'
            '  "analytical_program": ["..."],\n'
            '  "recommended_queries": ["..."],\n'
            '  "open_questions": ["..."],\n'
            '  "next_actions": ["..."],\n'
            '  "bib_entries": ["@misc{...}"]\n'
            "}\n\n"
            "Reglas:\n"
            "- Usa frases breves, accionables y deduplicadas.\n"
            "- No inventes ISBN, DOI, autores ni fechas. Si faltan, usa notas descriptivas conservadoras.\n"
            "- Si la fuente es local, indícalo como Archivo local en BibTeX.\n"
            "- Si el scope es institución o carrera, prioriza assets y bibliografía base.\n"
            "- Si el scope es materia, prioriza programa analítico, referencias y bibliografía recomendada.\n"
            "- Si el scope es actividad, prioriza carpeta de referencias específica y vacíos de investigación.\n\n"
            f"Memoria editorial heredada:\n{editorial_context or 'Sin memoria editorial previa.'}\n\n"
            f"Base de conocimiento actual:\n{payload_json}\n\n"
            f"Contexto local:\n{local_context}\n\n"
            f"Contexto web:\n{web_context or 'Sin fuentes web recuperadas.'}\n"
        )

    def _parse_response(self, text: str, scope: EditorialScope, engine: str, cycle_index: int) -> dict:
        payload = _extract_first_json(text)
        if payload is None:
            fallback = _extract_bullets(text)
            return {
                "scope_profile": [f"Salida no estructurada desde {engine} para {scope.label}"],
                "local_inventory": fallback[:6],
                "web_findings": [],
                "bibliography_notes": [],
                "asset_targets": [],
                "reference_targets": [],
                "analytical_program": [],
                "recommended_queries": [f"Normalizar salida del ciclo {cycle_index} en formato JSON."],
                "open_questions": ["Revisar manualmente la respuesta del motor antes de reutilizarla aguas abajo."],
                "next_actions": ["Repetir investigación con más contexto o URLs semilla."],
                "bib_entries": [],
            }
        return payload

    def _merge_payload(
        self,
        current: dict,
        candidate: dict,
        scope: EditorialScope,
        queries: list[str],
        web_sources: list[WebSource],
    ) -> dict:
        merged = self.store._normalize_payload(current)
        candidate_normalized = self.store._normalize_payload(candidate)
        for section in KNOWLEDGE_SECTIONS:
            merged[section] = _normalize_list(merged.get(section, []) + candidate_normalized.get(section, []))
        merged["recommended_queries"] = _normalize_list(merged.get("recommended_queries", []) + queries + candidate_normalized.get("recommended_queries", []))
        merged["sources"] = _normalize_list(
            merged.get("sources", [])
            + candidate_normalized.get("sources", [])
            + [scope.key]
            + [source.url for source in web_sources]
        )
        merged["bib_entries"] = _normalize_bib_entries(merged.get("bib_entries", []) + candidate_normalized.get("bib_entries", []))
        return merged

    def _materialize_scope_artifacts(self, scope: EditorialScope, target_root: Path, payload: dict, web_sources: list[WebSource]) -> Path:
        asset_dir = self._asset_dir(scope, target_root)
        if asset_dir is not None:
            (asset_dir / "web").mkdir(parents=True, exist_ok=True)
            (asset_dir / "web" / "README.md").write_text(self._render_asset_readme(scope, web_sources), encoding="utf-8")

        references_dir = self._references_dir(scope, target_root)
        if references_dir is not None:
            references_dir.mkdir(parents=True, exist_ok=True)
            (references_dir / "README.md").write_text(self._render_references_readme(scope, payload, web_sources), encoding="utf-8")

        analytical_program_path = self._analytical_program_path(scope, target_root)
        if analytical_program_path is not None and not analytical_program_path.exists() and payload.get("analytical_program"):
            analytical_program_path.write_text(self._render_analytical_program(scope, payload), encoding="utf-8")

        bibliography_path = self._preferred_bib_path(scope, target_root)
        bibliography_path.parent.mkdir(parents=True, exist_ok=True)
        existing = bibliography_path.read_text(encoding="utf-8", errors="replace") if bibliography_path.exists() else ""
        merged_bib = self._merge_bibliography(existing, payload.get("bib_entries", []), scope)
        bibliography_path.write_text(merged_bib, encoding="utf-8")
        return bibliography_path

    def _preferred_bib_path(self, scope: EditorialScope, target_root: Path) -> Path:
        existing_bibs = sorted(target_root.glob("*.bib"))
        if existing_bibs:
            for bib in existing_bibs:
                if "clean" not in bib.name.lower():
                    return bib
            return existing_bibs[0]
        if scope.level in {"institucion", "carrera"}:
            return target_root / f"bibliografia-{self._scope_slug(scope)}.bib"
        if scope.level == "actividad":
            activity_slug = _slugify(scope.activity or scope.label)
            return target_root / f"{activity_slug}.bib"
        return target_root / f"{self._subject_slug(scope)}.bib"

    def _references_dir(self, scope: EditorialScope, target_root: Path) -> Path | None:
        if scope.level == "actividad":
            return target_root / f"referencias-{_slugify(scope.activity or scope.label)}"
        return target_root / f"referencias-{self._scope_slug(scope)}"

    def _asset_dir(self, scope: EditorialScope, target_root: Path) -> Path | None:
        if scope.level not in {"institucion", "carrera"}:
            return None
        return target_root / f"assets-{self._scope_slug(scope)}"

    def _analytical_program_path(self, scope: EditorialScope, target_root: Path) -> Path | None:
        if scope.level not in {"materia", "actividad"}:
            return None
        return target_root / f"programa-analitico-{self._subject_slug(scope)}.md"

    def _render_web_context_for_prompt(self, web_sources: list[WebSource]) -> str:
        lines: list[str] = []
        for source in web_sources[:10]:
            lines.append(f"- {source.title} | {source.url} | {source.snippet}")
        return "\n".join(lines)

    def _render_web_sources_markdown(self, web_sources: list[WebSource], queries: list[str]) -> str:
        lines = ["# Fuentes web AulaTeX", "", "## Consultas", ""]
        lines.extend(f"- {query}" for query in queries)
        lines.extend(["", "## Resultados", ""])
        if not web_sources:
            lines.append("- Sin resultados web o dependencias de red no disponibles.")
        for source in web_sources:
            lines.append(f"- {source.title} | {source.url}")
            if source.snippet:
                lines.append(f"  {source.snippet}")
        lines.append("")
        return "\n".join(lines)

    def _render_asset_readme(self, scope: EditorialScope, web_sources: list[WebSource]) -> str:
        lines = [
            f"# Assets sugeridos para {scope.label}",
            "",
            "Esta carpeta fue creada por la fase Investigación de AulaTeX para resguardar recursos institucionales o programáticos.",
            "",
            "## Fuentes detectadas",
            "",
        ]
        if not web_sources:
            lines.append("- Sin fuentes web confirmadas en esta corrida.")
        else:
            lines.extend(f"- {source.title}: {source.url}" for source in web_sources[:10])
        lines.append("")
        return "\n".join(lines)

    def _render_references_readme(self, scope: EditorialScope, payload: dict, web_sources: list[WebSource]) -> str:
        lines = [
            f"# Referencias de {scope.label}",
            "",
            "Carpeta consolidada por la fase Investigación de AulaTeX.",
            "",
            "## Hallazgos prioritarios",
            "",
        ]
        findings = payload.get("bibliography_notes", []) + payload.get("web_findings", [])
        if findings:
            lines.extend(f"- {item}" for item in findings[:20])
        else:
            lines.append("- Aún no hay hallazgos consolidados.")
        lines.extend(["", "## Fuentes web", ""])
        if web_sources:
            lines.extend(f"- {source.title}: {source.url}" for source in web_sources[:12])
        else:
            lines.append("- Sin fuentes web registradas en esta corrida.")
        lines.append("")
        return "\n".join(lines)

    def _render_analytical_program(self, scope: EditorialScope, payload: dict) -> str:
        lines = [f"# Programa analitico de {scope.label}", "", "## Sintesis de investigación", ""]
        lines.extend(f"- {item}" for item in payload.get("analytical_program", []))
        if not payload.get("analytical_program"):
            lines.append("- Sin datos suficientes para sintetizar un programa analítico en esta corrida.")
        lines.extend(["", "## Bibliografía y vacíos", ""])
        notes = payload.get("bibliography_notes", []) + payload.get("open_questions", [])
        lines.extend(f"- {item}" for item in notes[:20])
        if not notes:
            lines.append("- Sin observaciones registradas.")
        lines.append("")
        return "\n".join(lines)

    def _merge_bibliography(self, existing: str, entries: list[str], scope: EditorialScope) -> str:
        normalized_entries = _normalize_bib_entries(entries)
        blocks: list[str] = []
        if existing.strip():
            blocks.append(existing.strip())
        elif scope.level in {"materia", "actividad"}:
            blocks.append(f"% Bibliografia local de {scope.label}\n% Consolidada por la fase Investigación de AulaTeX.")
        else:
            blocks.append(f"% Bibliografia base de {scope.label}\n% Consolidada por la fase Investigación de AulaTeX.")
        existing_keys = {match.group(1).lower() for match in re.finditer(r"@\w+\{\s*([^,]+)", existing, re.IGNORECASE)}
        for entry in normalized_entries:
            match = re.search(r"@\w+\{\s*([^,]+)", entry, re.IGNORECASE)
            key = match.group(1).lower() if match else ""
            if key and key in existing_keys:
                continue
            if key:
                existing_keys.add(key)
            blocks.append(entry.strip())
        return "\n\n".join(block for block in blocks if block.strip()) + "\n"

    def _search_query(self, query: str) -> list[WebSource]:
        if requests is None:
            return []
        try:
            response = requests.get(
                "https://duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0 AulaTeX"},
                timeout=12,
            )
            response.raise_for_status()
        except Exception:
            return []
        html_text = response.text
        results: list[WebSource] = []
        pattern = re.compile(
            r'<a[^>]*class="result__a"[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>.*?(?:<a[^>]*class="result__snippet"[^>]*>|<div[^>]*class="result__snippet"[^>]*>)(?P<snippet>.*?)(?:</a>|</div>)',
            re.IGNORECASE | re.DOTALL,
        )
        for match in pattern.finditer(html_text):
            href = self._decode_duckduckgo_url(html.unescape(match.group("href")))
            title = _clean_html(match.group("title"))
            snippet = _clean_html(match.group("snippet"))
            if not href or not title:
                continue
            results.append(WebSource(title=title, url=href, snippet=snippet[:360], origin=f"query:{query}"))
            if len(results) >= 3:
                break
        return results

    def _fetch_url(self, url: str, *, origin: str) -> WebSource | None:
        if requests is None:
            return None
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0 AulaTeX"}, timeout=12)
            response.raise_for_status()
        except Exception:
            return None
        page = response.text[:120000]
        title_match = re.search(r"<title[^>]*>(.*?)</title>", page, re.IGNORECASE | re.DOTALL)
        title = _clean_html(title_match.group(1)) if title_match else url
        snippet = _clean_html(page)[:360]
        return WebSource(title=title or url, url=url, snippet=snippet, origin=origin)

    def _decode_duckduckgo_url(self, href: str) -> str:
        if href.startswith("//"):
            return "https:" + href
        if href.startswith("http://") or href.startswith("https://"):
            return href
        parsed = urlparse(href)
        if parsed.path == "/l/":
            target = parse_qs(parsed.query).get("uddg", [""])[0]
            return unquote(target)
        return href

    def _scope_slug(self, scope: EditorialScope) -> str:
        if scope.level == "institucion":
            return _slugify(scope.label)
        if scope.level == "carrera":
            return _slugify(scope.career or scope.label)
        if scope.level == "materia":
            return self._subject_slug(scope)
        return _slugify(scope.activity or scope.label)

    def _subject_slug(self, scope: EditorialScope) -> str:
        base = _slugify(scope.subject or scope.label)
        parts = base.split("-")
        if len(parts) >= 2 and len(parts[-1]) <= 4 and parts[-1].isalnum():
            return "-".join(parts[:-1]) or base
        return base

    def _normalize_engines(self, engines: list[str] | tuple[str, ...]) -> list[str]:
        from .config import MODEL_ROUTER_ENGINE, restrict_engines_to_available

        selected = [engine for engine in restrict_engines_to_available(engines) if engine in self.llm.engines()]
        if not selected:
            selected = [MODEL_ROUTER_ENGINE]
        return sorted(selected, key=lambda item: (ENGINE_PRIORITY.get(item, 999), item))

    def _emit(self, callback: Callable[[InvestigationEvent], None] | None, event: InvestigationEvent) -> None:
        if callback is not None:
            callback(event)

    def _is_cancelled(self, cancel_event: Event | None) -> bool:
        return bool(cancel_event is not None and cancel_event.is_set())


def _normalize_list(items: object) -> list[str]:
    if isinstance(items, str):
        items = [items]
    if not isinstance(items, list):
        return []
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


def _normalize_bib_entries(items: object) -> list[str]:
    if isinstance(items, str):
        items = [items]
    if not isinstance(items, list):
        return []
    entries: list[str] = []
    seen_keys: set[str] = set()
    for item in items:
        if not isinstance(item, str):
            continue
        entry = item.strip()
        if not entry.startswith("@"):
            continue
        match = re.search(r"@\w+\{\s*([^,]+)", entry, re.IGNORECASE)
        key = match.group(1).lower() if match else entry.lower()
        if key in seen_keys:
            continue
        seen_keys.add(key)
        entries.append(entry)
    return entries


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
    return _normalize_list(bullets)


def _slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "recurso"


def _clean_html(value: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    return re.sub(r"\s+", " ", text).strip()