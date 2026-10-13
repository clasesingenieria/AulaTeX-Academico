from __future__ import annotations

import json
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import LLM_ENGINES
from .llm_bridge import AulaTeXLLMClient, LLMCallResult
from .workspace import AulaTeXWorkspace


SUMMARY_ENGINE_PREFERENCE = (
    "Auto (model-router)",
    "Claude Foundry",
    "Codex",
    "GPT-Pro",
)
MULTIMOTOR_SEVERITY_LABELS = {
    "rapido": "Rápido",
    "normal": "Normal",
    "profundo": "Profundo",
}
MULTIMOTOR_SEVERITY_PROFILES = {
    "rapido": {
        "engine_max_tokens": 900,
        "synthesis_max_tokens": 1100,
        "timeout_seconds": 45,
        "analysis_instruction": "Responde con criterio ejecutivo, priorizando señales fuertes y acciones inmediatas.",
        "synthesis_instruction": "Sintetiza en forma breve, prioriza consenso y evita desarrollo innecesario.",
    },
    "normal": {
        "engine_max_tokens": 1400,
        "synthesis_max_tokens": 1700,
        "timeout_seconds": 60,
        "analysis_instruction": "Responde con equilibrio entre brevedad, evidencia y accionabilidad.",
        "synthesis_instruction": "Sintetiza consenso, desacuerdos relevantes y siguiente paso accionable.",
    },
    "profundo": {
        "engine_max_tokens": 2200,
        "synthesis_max_tokens": 2600,
        "timeout_seconds": 90,
        "analysis_instruction": "Responde con mayor profundidad, riesgos, supuestos, alternativas y validaciones recomendadas.",
        "synthesis_instruction": "Sintetiza con detalle, separa consenso, matices, riesgos y plan de accion recomendado.",
    },
}
COMPACT_AFTER_MESSAGES = 10
COMPACT_AFTER_CHARS = 12000
KEEP_RECENT_MESSAGES = 6
SUMMARY_MAX_CHARS = 5000
RECENT_MESSAGE_LIMIT = 12
SIDEBAR_PREVIEW_CHARS = 120


@dataclass(frozen=True)
class ChatSpaceDefinition:
    key: str
    label: str
    description: str
    mode: str
    assigned_engine: str
    help_text: str
    system_prompt: str
    engines: tuple[str, ...] = ()

    @property
    def engine_list(self) -> tuple[str, ...]:
        if self.mode == "multi":
            return self.engines or LLM_ENGINES
        return self.engines or (self.assigned_engine,)


@dataclass(frozen=True)
class ChatMessage:
    id: int
    session_key: str
    role: str
    engine: str
    content: str
    compacted: bool
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChatSessionState:
    definition: ChatSpaceDefinition
    summary_text: str
    message_count: int
    active_messages: int
    updated_at: str
    estimated_tokens: int = 0
    estimated_chars: int = 0
    compaction_count: int = 0

    @property
    def preview(self) -> str:
        if self.summary_text.strip():
            return _shorten(self.summary_text.strip().replace("\n", " "), SIDEBAR_PREVIEW_CHARS)
        return "Sin memoria compactada aun."

    @property
    def context_label(self) -> str:
        return _format_token_count(self.estimated_tokens)


@dataclass(frozen=True)
class ChatCompactionRecord:
    id: int
    session_key: str
    summary_text: str
    compacted_messages: int
    compacted_chars: int
    first_message_id: int
    last_message_id: int
    created_at: str


@dataclass(frozen=True)
class ChatTimelineItem:
    kind: str
    sort_key: float
    message: ChatMessage | None = None
    compaction: ChatCompactionRecord | None = None


@dataclass(frozen=True)
class ChatTurnResult:
    session_key: str
    ok: bool
    engine: str
    response_text: str
    status_message: str
    compacted: bool = False
    engine_results: tuple[LLMCallResult, ...] = ()
    severity: str = "normal"


CHAT_SPACES = (
    ChatSpaceDefinition(
        key="editorial",
        label="Editorial",
        description="Estilo, tono, identidad institucional y criterios de revision.",
        mode="single",
        assigned_engine="Claude Foundry",
        help_text=(
            "Usa esta sesion para mejorar redaccion, tono institucional, coherencia, rubricas, "
            "lineamientos y criterios editoriales."
        ),
        system_prompt=(
            "Eres AulaTeX en modo Editorial. Prioriza tono academico, claridad, coherencia, "
            "identidad institucional, criterios de evaluacion y lineamientos de estilo. "
            "No inventes fuentes ni afirmaciones no sustentadas."
        ),
    ),
    ChatSpaceDefinition(
        key="proyecto",
        label="Proyecto",
        description="Planeacion del documento, estructura, entregables y continuidad.",
        mode="single",
        assigned_engine="GPT-Pro",
        help_text=(
            "Usa esta sesion para estructurar proyectos, capitulos, actividades, cronogramas, "
            "objetivos y entregables."
        ),
        system_prompt=(
            "Eres AulaTeX en modo Proyecto. Ayuda a estructurar documentos, entregables, capitulos, "
            "objetivos y dependencias entre secciones. Mantén continuidad entre iteraciones."
        ),
    ),
    ChatSpaceDefinition(
        key="investigacion",
        label="Investigacion",
        description="Sintesis de conceptos, referencias, comparaciones y mapas conceptuales.",
        mode="single",
        assigned_engine="Auto (model-router)",
        help_text=(
            "Usa esta sesion para investigar conceptos, contrastar autores, resumir bibliografia "
            "y preparar mapas conceptuales o marcos teoricos."
        ),
        system_prompt=(
            "Eres AulaTeX en modo Investigacion. Sintetiza conceptos, relaciones teoricas, referencias, "
            "antecedentes y definiciones. Marca lagunas y supuestos cuando falte evidencia."
        ),
    ),
    ChatSpaceDefinition(
        key="operativo",
        label="Operativo",
        description="Compilacion, LaTeX, scripts, errores tecnicos y automatizacion.",
        mode="single",
        assigned_engine="Codex",
        help_text=(
            "Usa esta sesion para diagnosticar errores de compilacion, comandos, scripts, rutas, "
            "paquetes LaTeX y automatizaciones de AulaTeX."
        ),
        system_prompt=(
            "Eres AulaTeX en modo Operativo. Resuelve problemas tecnicos de LaTeX, compilacion, scripts, "
            "rutas, automatizacion y diagnostico reproducible. Prioriza pasos concretos y verificables."
        ),
    ),
    ChatSpaceDefinition(
        key="multimotor",
        label="MultiMotor",
        description="Consulta paralela a todos los motores y consolida consenso accionable.",
        mode="multi",
        assigned_engine="Auto (model-router)",
        help_text=(
            "Usa esta sesion para tareas importantes: se consultan todos los motores en paralelo y luego "
            "se consolida consenso, desacuerdos y siguiente paso."
        ),
        system_prompt=(
            "Eres el coordinador multi motor de AulaTeX. Debes combinar respuestas de varios motores, "
            "identificar coincidencias, anotar desacuerdos relevantes y cerrar con una recomendacion accionable."
        ),
        engines=LLM_ENGINES,
    ),
)
CHAT_SPACE_MAP = {space.key: space for space in CHAT_SPACES}


class AulaTeXChatStore:
    def __init__(
        self,
        workspace: AulaTeXWorkspace | None = None,
        llm_bridge: AulaTeXLLMClient | None = None,
    ) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.llm = llm_bridge or AulaTeXLLMClient()
        self.root = self.workspace.feedback_root / "llm-chat"
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "llm-chat.db"
        self.exports_dir = self.root / "exports"
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        self._bootstrap_sessions()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_key TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    description TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    assigned_engine TEXT NOT NULL,
                    help_text TEXT NOT NULL,
                    system_prompt TEXT NOT NULL,
                    summary_text TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_key TEXT NOT NULL,
                    role TEXT NOT NULL,
                    engine TEXT NOT NULL DEFAULT '',
                    content TEXT NOT NULL,
                    compacted INTEGER NOT NULL DEFAULT 0,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id
                ON messages(session_key, id);

                CREATE TABLE IF NOT EXISTS compactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_key TEXT NOT NULL,
                    summary_text TEXT NOT NULL,
                    compacted_messages INTEGER NOT NULL DEFAULT 0,
                    compacted_chars INTEGER NOT NULL DEFAULT 0,
                    first_message_id INTEGER NOT NULL DEFAULT 0,
                    last_message_id INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_chat_compactions_session_id
                ON compactions(session_key, id);
                """
            )

    def _bootstrap_sessions(self) -> None:
        with self._connect() as conn:
            for space in CHAT_SPACES:
                conn.execute(
                    """
                    INSERT INTO sessions (
                        session_key, label, description, mode, assigned_engine, help_text, system_prompt
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_key) DO UPDATE SET
                        label=excluded.label,
                        description=excluded.description,
                        mode=excluded.mode,
                        assigned_engine=excluded.assigned_engine,
                        help_text=excluded.help_text,
                        system_prompt=excluded.system_prompt
                    """,
                    (
                        space.key,
                        space.label,
                        space.description,
                        space.mode,
                        space.assigned_engine,
                        space.help_text,
                        space.system_prompt,
                    ),
                )

    def definitions(self) -> tuple[ChatSpaceDefinition, ...]:
        return CHAT_SPACES

    def get_definition(self, session_key: str) -> ChatSpaceDefinition:
        return CHAT_SPACE_MAP.get(session_key, CHAT_SPACE_MAP["editorial"])

    def list_sessions(self) -> list[ChatSessionState]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    s.session_key,
                    s.summary_text,
                    s.updated_at,
                    COALESCE(msg.message_count, 0) AS message_count,
                    COALESCE(msg.active_messages, 0) AS active_messages,
                    COALESCE(msg.active_chars, 0) AS active_chars,
                    COALESCE(comp.compaction_count, 0) AS compaction_count
                FROM sessions s
                LEFT JOIN (
                    SELECT
                        session_key,
                        COUNT(*) AS message_count,
                        SUM(CASE WHEN compacted = 0 THEN 1 ELSE 0 END) AS active_messages,
                        SUM(CASE WHEN compacted = 0 THEN LENGTH(content) ELSE 0 END) AS active_chars
                    FROM messages
                    GROUP BY session_key
                ) msg ON msg.session_key = s.session_key
                LEFT JOIN (
                    SELECT session_key, COUNT(*) AS compaction_count
                    FROM compactions
                    GROUP BY session_key
                ) comp ON comp.session_key = s.session_key
                """
            ).fetchall()
        by_key = {row["session_key"]: row for row in rows}
        sessions: list[ChatSessionState] = []
        for space in CHAT_SPACES:
            row = by_key.get(space.key)
            summary_text = (row["summary_text"] if row is not None else "") or ""
            active_chars = int(row["active_chars"] if row is not None and row["active_chars"] is not None else 0)
            estimated_chars = len(summary_text) + active_chars + len(space.system_prompt)
            sessions.append(
                ChatSessionState(
                    definition=space,
                    summary_text=summary_text,
                    message_count=int(row["message_count"] if row is not None else 0),
                    active_messages=int(row["active_messages"] if row is not None and row["active_messages"] is not None else 0),
                    updated_at=(row["updated_at"] if row is not None else "") or "",
                    estimated_tokens=_estimate_tokens(estimated_chars),
                    estimated_chars=estimated_chars,
                    compaction_count=int(row["compaction_count"] if row is not None and row["compaction_count"] is not None else 0),
                )
            )
        return sessions

    def get_session_state(self, session_key: str) -> ChatSessionState:
        for item in self.list_sessions():
            if item.definition.key == session_key:
                return item
        return self.list_sessions()[0]

    def get_messages(
        self,
        session_key: str,
        *,
        include_compacted: bool = False,
        limit: int = 80,
    ) -> list[ChatMessage]:
        query = (
            "SELECT id, session_key, role, engine, content, compacted, created_at, metadata_json "
            "FROM messages WHERE session_key=?"
        )
        params: list[Any] = [session_key]
        if not include_compacted:
            query += " AND compacted=0"
        query += " ORDER BY id DESC LIMIT ?"
        params.append(max(1, limit))
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        messages = [self._row_to_message(row) for row in reversed(rows)]
        return messages

    def get_summary_text(self, session_key: str) -> str:
        with self._connect() as conn:
            row = conn.execute("SELECT summary_text FROM sessions WHERE session_key=?", (session_key,)).fetchone()
        return ((row["summary_text"] if row is not None else "") or "").strip()

    def get_compactions(self, session_key: str, *, limit: int = 20) -> list[ChatCompactionRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, session_key, summary_text, compacted_messages, compacted_chars, first_message_id, last_message_id, created_at
                FROM compactions
                WHERE session_key=?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_key, max(1, limit)),
            ).fetchall()
        return [self._row_to_compaction(row) for row in reversed(rows)]

    def get_visible_history(
        self,
        session_key: str,
        *,
        message_limit: int = 80,
        compaction_limit: int = 20,
    ) -> list[ChatTimelineItem]:
        messages = self.get_messages(session_key, include_compacted=False, limit=message_limit)
        compactions = self.get_compactions(session_key, limit=compaction_limit)
        timeline: list[ChatTimelineItem] = []
        for record in compactions:
            timeline.append(
                ChatTimelineItem(
                    kind="compaction",
                    sort_key=float(record.last_message_id) + 0.1,
                    compaction=record,
                )
            )
        for message in messages:
            timeline.append(
                ChatTimelineItem(
                    kind="message",
                    sort_key=float(message.id),
                    message=message,
                )
            )
        timeline.sort(key=lambda item: item.sort_key)
        return timeline

    def session_help(self, session_key: str) -> str:
        definition = self.get_definition(session_key)
        lines = [
            f"Sesion: {definition.label}",
            f"Objetivo: {definition.description}",
            f"Motores: {', '.join(definition.engine_list)}",
            "",
            definition.help_text,
            "",
            "Consejos:",
            "- Usa una sesion por tipo de trabajo.",
            "- El historial se guarda automaticamente.",
            "- Cuando crece demasiado, el sistema compacta contexto sin perder decisiones utiles.",
            "- En MultiMotor se consultan todos los motores y se entrega consenso consolidado.",
        ]
        return "\n".join(lines)

    def record_local_exchange(self, session_key: str, prompt: str, response_text: str) -> ChatTurnResult:
        self._store_message(session_key, "user", prompt)
        self._store_message(
            session_key,
            "assistant",
            response_text,
            engine="Herramienta local",
            metadata={"mode": "tool"},
        )
        compacted = self.compact_session(session_key)
        return ChatTurnResult(
            session_key=session_key,
            ok=True,
            engine="Herramienta local",
            response_text=response_text,
            status_message="Herramienta local completada.",
            compacted=compacted,
            severity="normal",
        )

    def send_prompt(
        self,
        session_key: str,
        prompt: str,
        *,
        severity: str = "normal",
        max_tokens: int = 1400,
        timeout_seconds: int = 60,
    ) -> ChatTurnResult:
        definition = self.get_definition(session_key)
        clean_prompt = prompt.strip()
        if not clean_prompt:
            raise ValueError("El prompt no puede estar vacio")
        severity_key = normalize_multimotor_severity(severity)

        self._store_message(session_key, "user", clean_prompt)
        prepared_prompt = self._build_prompt(session_key, clean_prompt, severity=severity_key)
        if definition.mode == "multi":
            result = self._send_multi(
                definition,
                prepared_prompt,
                clean_prompt,
                severity=severity_key,
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
            )
        else:
            llm_result = self.llm.call(
                definition.assigned_engine,
                prepared_prompt,
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
            )
            response_text = llm_result.text if llm_result.ok else llm_result.error
            self._store_message(
                session_key,
                "assistant",
                response_text,
                engine=llm_result.engine,
                metadata={"mode": "single", "ok": llm_result.ok},
            )
            compacted = self.compact_session(session_key)
            status = f"{definition.label}: {llm_result.engine} {'OK' if llm_result.ok else 'ERROR'}"
            result = ChatTurnResult(
                session_key=session_key,
                ok=llm_result.ok,
                engine=llm_result.engine,
                response_text=response_text,
                status_message=status,
                compacted=compacted,
                engine_results=(llm_result,),
                severity=severity_key,
            )
        return result

    def compact_session(self, session_key: str, *, force: bool = False) -> bool:
        active_messages = self.get_messages(session_key, include_compacted=False, limit=200)
        if not active_messages:
            return False
        total_chars = sum(len(message.content) for message in active_messages)
        if not force and len(active_messages) <= COMPACT_AFTER_MESSAGES and total_chars <= COMPACT_AFTER_CHARS:
            return False
        if len(active_messages) <= KEEP_RECENT_MESSAGES:
            return False

        definition = self.get_definition(session_key)
        to_compact = active_messages[:-KEEP_RECENT_MESSAGES]
        existing_summary = self.get_summary_text(session_key)
        compact_prompt = self._build_compaction_prompt(definition, existing_summary, to_compact)
        compact_result = self.llm.call(
            definition.assigned_engine,
            compact_prompt,
            max_tokens=min(1200, max(400, len(existing_summary) // 3 + 500)),
            timeout_seconds=60,
        )
        if compact_result.ok and compact_result.text.strip():
            summary_text = compact_result.text.strip()
        else:
            summary_text = self._heuristic_summary(existing_summary, to_compact)
        self._update_summary_text(session_key, summary_text)
        self._record_compaction(session_key, self._build_compaction_snapshot(to_compact, summary_text), to_compact)
        self._mark_compacted([message.id for message in to_compact])
        return True

    def clear_session(self, session_key: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM messages WHERE session_key=?", (session_key,))
            conn.execute("DELETE FROM compactions WHERE session_key=?", (session_key,))
            conn.execute(
                "UPDATE sessions SET summary_text='', updated_at=CURRENT_TIMESTAMP WHERE session_key=?",
                (session_key,),
            )

    def export_session_markdown(self, session_key: str) -> Path:
        state = self.get_session_state(session_key)
        timeline = self.get_visible_history(session_key, message_limit=300, compaction_limit=50)
        lines = [
            f"# Chat AulaTeX - {state.definition.label}",
            "",
            f"- Descripcion: {state.definition.description}",
            f"- Motores: {', '.join(state.definition.engine_list)}",
            f"- Contexto estimado: ~{state.context_label}",
            "",
            "## Memoria compactada",
            "",
            self.get_summary_text(session_key) or "Sin resumen aun.",
            "",
            "## Conversacion",
            "",
        ]
        for item in timeline:
            if item.kind == "compaction" and item.compaction is not None:
                record = item.compaction
                lines.extend(
                    [
                        f"### Resumen compactado #{record.id}",
                        "",
                        f"- Mensajes resumidos: {record.compacted_messages}",
                        f"- Caracteres resumidos: {record.compacted_chars}",
                        "",
                        record.summary_text,
                        "",
                    ]
                )
                continue
            if item.message is None:
                continue
            role = self._role_label(item.message)
            engine = f" [{item.message.engine}]" if item.message.engine else ""
            compacted = " (compactado)" if item.message.compacted else ""
            lines.extend([f"### {role}{engine}{compacted}", "", item.message.content, ""])
        export_path = self.exports_dir / f"{session_key}-{self.workspace.timestamp()}.md"
        export_path.write_text("\n".join(lines), encoding="utf-8")
        return export_path

    def _send_multi(
        self,
        definition: ChatSpaceDefinition,
        prepared_prompt: str,
        raw_prompt: str,
        *,
        severity: str,
        max_tokens: int,
        timeout_seconds: int,
    ) -> ChatTurnResult:
        severity_key = normalize_multimotor_severity(severity)
        profile = MULTIMOTOR_SEVERITY_PROFILES[severity_key]
        engines = [engine for engine in definition.engine_list if engine in self.llm.engines()]
        if not engines:
            engines = list(self.llm.engines()) or [definition.assigned_engine]
        engine_max_tokens = _severity_tokens(max_tokens, int(profile["engine_max_tokens"]), severity_key)
        per_call_timeout = _severity_timeout(timeout_seconds, int(profile["timeout_seconds"]), severity_key)

        ordered_results: list[LLMCallResult] = []
        with ThreadPoolExecutor(max_workers=max(1, len(engines))) as executor:
            futures = {
                executor.submit(
                    self.llm.call,
                    engine,
                    prepared_prompt,
                    max_tokens=engine_max_tokens,
                    timeout_seconds=per_call_timeout,
                ): engine
                for engine in engines
            }
            by_engine: dict[str, LLMCallResult] = {}
            for future in as_completed(futures):
                engine = futures[future]
                try:
                    by_engine[engine] = future.result()
                except Exception as exc:
                    by_engine[engine] = LLMCallResult(engine, False, "", f"{type(exc).__name__}: {exc}")
        for engine in engines:
            ordered_results.append(by_engine[engine])

        synthesized = self._synthesize_multi_response(
            definition,
            raw_prompt,
            ordered_results,
            severity=severity_key,
            max_tokens=max_tokens,
        )
        ok = any(result.ok for result in ordered_results)
        metadata = {
            "mode": "multi",
            "ok": ok,
            "severity": severity_key,
            "engine_results": [
                {
                    "engine": result.engine,
                    "ok": result.ok,
                    "text": result.text,
                    "error": result.error,
                }
                for result in ordered_results
            ],
        }
        self._store_message(
            definition.key,
            "assistant",
            synthesized,
            engine=definition.assigned_engine,
            metadata=metadata,
        )
        compacted = self.compact_session(definition.key)
        successful = [result.engine for result in ordered_results if result.ok]
        severity_label = multimotor_severity_label(severity_key)
        status = (
            f"{definition.label} {severity_label}: consenso multi motor con {', '.join(successful)}"
            if successful
            else f"{definition.label} {severity_label}: todos los motores devolvieron error"
        )
        return ChatTurnResult(
            session_key=definition.key,
            ok=ok,
            engine=definition.assigned_engine,
            response_text=synthesized,
            status_message=status,
            compacted=compacted,
            engine_results=tuple(ordered_results),
            severity=severity_key,
        )

    def _synthesize_multi_response(
        self,
        definition: ChatSpaceDefinition,
        raw_prompt: str,
        results: list[LLMCallResult],
        *,
        severity: str,
        max_tokens: int,
    ) -> str:
        severity_key = normalize_multimotor_severity(severity)
        profile = MULTIMOTOR_SEVERITY_PROFILES[severity_key]
        successful = [result for result in results if result.ok and result.text.strip()]
        if not successful:
            errors = [f"- {result.engine}: {result.error or 'Sin respuesta'}" for result in results]
            return "## Fallo multimotor\n\n" + "\n".join(errors)

        synthesis_engine = self._pick_summary_engine(results)
        synthesis_prompt = [
            definition.system_prompt,
            "",
            f"Severidad multimotor: {multimotor_severity_label(severity_key)}.",
            str(profile["synthesis_instruction"]),
            "",
            "Fusiona las respuestas siguientes.",
            "Responde en Markdown con estas secciones:",
            "## Consenso",
            "## Matices por motor",
            "## Recomendacion accionable",
            "## Riesgos o validaciones",
            "",
            f"Prompt original:\n{raw_prompt}",
            "",
        ]
        for result in results:
            synthesis_prompt.append(f"### {result.engine} | {'OK' if result.ok else 'ERROR'}")
            synthesis_prompt.append(result.text if result.ok else result.error)
            synthesis_prompt.append("")
        synthesis = self.llm.call(
            synthesis_engine,
            "\n".join(synthesis_prompt),
            max_tokens=_severity_tokens(max_tokens + 300, int(profile["synthesis_max_tokens"]), severity_key),
            timeout_seconds=_severity_timeout(90, int(profile["timeout_seconds"]), severity_key),
        )
        if synthesis.ok and synthesis.text.strip():
            return synthesis.text.strip()

        lines = [
            "## Consenso",
            "",
            f"- Motores consultados: {', '.join(result.engine for result in results)}",
            f"- Motores con respuesta: {', '.join(result.engine for result in successful)}",
            "- No se pudo sintetizar con un motor coordinador; se entrega consolidado manual.",
            "",
            "## Matices por motor",
            "",
        ]
        for result in results:
            marker = "OK" if result.ok else "ERROR"
            body = result.text if result.ok else result.error
            lines.append(f"### {result.engine} ({marker})")
            lines.append("")
            lines.append(_shorten(body.strip(), 2200) or "Sin contenido.")
            lines.append("")
        lines.extend(
            [
                "## Recomendacion accionable",
                "",
                "- Revisar coincidencias entre motores y aplicar la propuesta con mayor soporte.",
                "",
                "## Riesgos o validaciones",
                "",
                f"- Sintesis manual de contingencia para severidad {multimotor_severity_label(severity_key)}.",
            ]
        )
        return "\n".join(lines)

    def _pick_summary_engine(self, results: list[LLMCallResult]) -> str:
        available = {result.engine for result in results if result.ok}
        for engine in SUMMARY_ENGINE_PREFERENCE:
            if engine in available or engine in self.llm.engines():
                return engine
        return results[0].engine if results else "Codex"

    def _build_prompt(self, session_key: str, prompt: str, *, severity: str = "normal") -> str:
        definition = self.get_definition(session_key)
        summary_text = self.get_summary_text(session_key)
        messages = self.get_messages(session_key, include_compacted=False, limit=RECENT_MESSAGE_LIMIT)
        lines = [definition.system_prompt, "", f"Sesion: {definition.label}", f"Objetivo: {definition.description}", ""]
        if definition.mode == "multi":
            severity_key = normalize_multimotor_severity(severity)
            profile = MULTIMOTOR_SEVERITY_PROFILES[severity_key]
            lines.extend(
                [
                    f"Severidad seleccionada: {multimotor_severity_label(severity_key)}",
                    str(profile["analysis_instruction"]),
                    "",
                ]
            )
        if summary_text:
            lines.extend(["Memoria compactada vigente:", summary_text, ""])
        else:
            lines.extend(["Memoria compactada vigente:", "Sin memoria compactada aun.", ""])
        if messages:
            lines.append("Historial reciente:")
            for message in messages[:-1]:
                label = self._role_label(message)
                engine = f" [{message.engine}]" if message.engine else ""
                lines.append(f"{label}{engine}: {_shorten(message.content, 2200)}")
            lines.append("")
        lines.append(f"Usuario: {prompt}")
        return "\n".join(lines)

    def _build_compaction_prompt(
        self,
        definition: ChatSpaceDefinition,
        existing_summary: str,
        messages: list[ChatMessage],
    ) -> str:
        transcript = []
        for message in messages:
            label = self._role_label(message)
            engine = f" [{message.engine}]" if message.engine else ""
            transcript.append(f"{label}{engine}: {message.content}")
        return (
            "Eres el compactador de contexto de AulaTeX. Debes producir una memoria breve pero lossless. "
            "No elimines decisiones, restricciones, archivos mencionados, pendientes ni conclusiones utiles. "
            "Devuelve Markdown breve con secciones: Estado, Decisiones, Pendientes, Referencias. "
            f"Limita el resultado a {SUMMARY_MAX_CHARS} caracteres maximo.\n\n"
            f"Sesion: {definition.label}\n"
            f"Objetivo: {definition.description}\n\n"
            f"Resumen previo:\n{existing_summary or 'Sin resumen previo.'}\n\n"
            "Mensajes a compactar:\n"
            + "\n".join(transcript)
        )

    def _heuristic_summary(self, existing_summary: str, messages: list[ChatMessage]) -> str:
        bullets = _extract_summary_lines(existing_summary)
        for message in messages:
            label = self._role_label(message)
            prefix = f"{label}:"
            bullets.append(f"{prefix} {_first_sentence(message.content)}")
        deduped = _dedupe_lines(bullets)
        lines = ["## Estado", ""]
        lines.extend(f"- {line}" for line in deduped[:20])
        summary = "\n".join(lines)
        return summary[:SUMMARY_MAX_CHARS].strip()

    def _build_compaction_snapshot(self, messages: list[ChatMessage], summary_text: str) -> str:
        lines = [
            "## Resumen visible del bloque compactado",
            "",
            f"- Mensajes resumidos: {len(messages)}",
            f"- Tokens aproximados liberados: ~{_format_token_count(_estimate_tokens(sum(len(message.content) for message in messages)))}",
            "",
        ]
        extracted = _extract_summary_lines(summary_text)
        if extracted:
            lines.extend(f"- {item}" for item in extracted[:8])
        else:
            fallback = []
            for message in messages:
                fallback.append(f"{self._role_label(message)}: {_first_sentence(message.content)}")
            lines.extend(f"- {item}" for item in _dedupe_lines(fallback)[:8])
        return "\n".join(lines).strip()[:SUMMARY_MAX_CHARS]

    def _store_message(
        self,
        session_key: str,
        role: str,
        content: str,
        *,
        engine: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        payload = json.dumps(metadata or {}, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO messages (session_key, role, engine, content, metadata_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_key, role, engine, content.strip(), payload),
            )
            conn.execute(
                "UPDATE sessions SET updated_at=CURRENT_TIMESTAMP WHERE session_key=?",
                (session_key,),
            )

    def _record_compaction(self, session_key: str, summary_text: str, messages: list[ChatMessage]) -> None:
        if not messages:
            return
        compacted_chars = sum(len(message.content) for message in messages)
        first_id = min(message.id for message in messages)
        last_id = max(message.id for message in messages)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO compactions (
                    session_key, summary_text, compacted_messages, compacted_chars, first_message_id, last_message_id
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_key, summary_text.strip(), len(messages), compacted_chars, first_id, last_id),
            )
            conn.execute(
                "UPDATE sessions SET updated_at=CURRENT_TIMESTAMP WHERE session_key=?",
                (session_key,),
            )

    def _update_summary_text(self, session_key: str, summary_text: str) -> None:
        clean_summary = summary_text.strip()[:SUMMARY_MAX_CHARS]
        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET summary_text=?, updated_at=CURRENT_TIMESTAMP WHERE session_key=?",
                (clean_summary, session_key),
            )

    def _mark_compacted(self, message_ids: list[int]) -> None:
        if not message_ids:
            return
        placeholders = ", ".join("?" for _ in message_ids)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE messages SET compacted=1 WHERE id IN ({placeholders})",
                tuple(message_ids),
            )

    def _row_to_message(self, row: sqlite3.Row) -> ChatMessage:
        metadata: dict[str, Any] = {}
        raw_metadata = row["metadata_json"] or "{}"
        try:
            parsed = json.loads(raw_metadata)
            if isinstance(parsed, dict):
                metadata = parsed
        except json.JSONDecodeError:
            metadata = {}
        return ChatMessage(
            id=int(row["id"]),
            session_key=row["session_key"],
            role=row["role"],
            engine=row["engine"],
            content=row["content"],
            compacted=bool(row["compacted"]),
            created_at=row["created_at"],
            metadata=metadata,
        )

    def _row_to_compaction(self, row: sqlite3.Row) -> ChatCompactionRecord:
        return ChatCompactionRecord(
            id=int(row["id"]),
            session_key=row["session_key"],
            summary_text=row["summary_text"],
            compacted_messages=int(row["compacted_messages"]),
            compacted_chars=int(row["compacted_chars"]),
            first_message_id=int(row["first_message_id"]),
            last_message_id=int(row["last_message_id"]),
            created_at=row["created_at"],
        )

    def _role_label(self, message: ChatMessage) -> str:
        if message.role == "user":
            return "Usuario"
        if message.role == "assistant":
            return "Asistente"
        return message.role.capitalize()


def _shorten(text: str, max_chars: int) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    if len(clean) <= max_chars:
        return clean
    return clean[: max(0, max_chars - 1)].rstrip() + "…"


def _first_sentence(text: str) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    if not clean:
        return ""
    match = re.search(r"(.{1,220}?[\.!?])(?:\s|$)", clean)
    if match:
        return match.group(1).strip()
    return _shorten(clean, 220)


def _extract_summary_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in (text or "").splitlines():
        value = raw_line.strip().lstrip("- ").strip()
        if not value or value.startswith("## "):
            continue
        lines.append(value)
    return lines


def _dedupe_lines(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        clean = re.sub(r"\s+", " ", item or "").strip(" -\t\r\n")
        if not clean:
            continue
        marker = clean.lower()
        if marker in seen:
            continue
        seen.add(marker)
        out.append(clean)
    return out


def normalize_multimotor_severity(value: str | None) -> str:
    candidate = (value or "normal").strip().lower()
    if candidate not in MULTIMOTOR_SEVERITY_PROFILES:
        return "normal"
    return candidate


def multimotor_severity_label(value: str | None) -> str:
    return MULTIMOTOR_SEVERITY_LABELS[normalize_multimotor_severity(value)]


def _estimate_tokens(char_count: int) -> int:
    if char_count <= 0:
        return 0
    return max(1, int(round(char_count / 4.0)))


def _format_token_count(tokens: int) -> str:
    if tokens >= 1000:
        return f"{tokens / 1000.0:.1f}k tok"
    return f"{tokens} tok"


def _severity_tokens(base_tokens: int, profile_tokens: int, severity: str) -> int:
    severity_key = normalize_multimotor_severity(severity)
    if severity_key == "rapido":
        return max(300, min(base_tokens, profile_tokens))
    if severity_key == "profundo":
        return max(base_tokens, profile_tokens)
    return max(base_tokens, profile_tokens)


def _severity_timeout(base_timeout: int, profile_timeout: int, severity: str) -> int:
    severity_key = normalize_multimotor_severity(severity)
    if severity_key == "rapido":
        return max(20, min(base_timeout, profile_timeout))
    if severity_key == "profundo":
        return max(base_timeout, profile_timeout)
    return max(base_timeout, profile_timeout)
