from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .editorial_memory import EditorialMemoryStore
from .extractor_adapter import CORE_EXTRACTOR_ARTIFACTS
from .workspace import AulaTeXWorkspace, EditorialScope


@dataclass(frozen=True)
class EditorialContextBundle:
    scope_key: str
    markdown: str
    data: dict[str, Any]


class EditorialContextProvider:
    """Construye contexto reutilizable para agente, generador y memoria editorial.

    Reúne memoria distribuida, herencia, extractor, bibliografía, conceptos,
    referencias y señales locales sin depender de una memoria centralizada.
    """

    def __init__(self, workspace: AulaTeXWorkspace | None = None, store: EditorialMemoryStore | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.store = store or EditorialMemoryStore(self.workspace)

    def build_for_scope(self, scope_key: str, *, include_ancestors: bool = True, max_chars: int = 18000) -> EditorialContextBundle:
        by_key, _children = self.workspace.editorial_scope_index()
        scope = by_key.get(scope_key)
        if scope is None:
            return EditorialContextBundle(scope_key, "", {"scope_key": scope_key, "found": False})

        target = self.workspace.repo_root / scope.relative_path if scope.relative_path else self.workspace.repo_root
        scope_memory = self.store.get_memory(scope.key)
        editing_details = dict((scope_memory.get("node_metadata") or {}).get("editing_details") or {})
        memory = self.store.summarize_for_scope(scope.key, include_ancestors=include_ancestors, max_chars=max_chars // 3)
        extractor = self._extractor_payload(target, max_items=18)
        bibliography = self._bibliography_payload(target, max_items=18)
        references = self._reference_payload(target, max_items=18)
        local_tex = self._tex_payload(target, max_items=12)
        distributed = self._distributed_memory_paths(target, max_items=12)

        data: dict[str, Any] = {
            "found": True,
            "scope_key": scope.key,
            "level": scope.level,
            "label": scope.label,
            "relative_path": scope.relative_path,
            "editing_details": editing_details,
            "memory_markdown": memory,
            "extractor": extractor,
            "bibliography": bibliography,
            "references": references,
            "tex": local_tex,
            "distributed_memory": distributed,
        }
        markdown = self._render_markdown(data)
        if len(markdown) > max_chars:
            markdown = markdown[:max_chars] + "\n\n[Contexto editorial truncado por presupuesto; consultar memoria distribuida y extractor local.]"
        return EditorialContextBundle(scope.key, markdown, data)

    def _extractor_payload(self, target: Path, *, max_items: int) -> dict[str, Any]:
        root = target / "extractor-aulatex"
        payload: dict[str, Any] = {"available": root.exists(), "artifacts": {}}
        if not root.exists():
            return payload
        for name, filename in CORE_EXTRACTOR_ARTIFACTS.items():
            matches = list(root.rglob(filename))[:3]
            values = []
            for path in matches:
                values.extend(self._json_or_lines(path, limit=max_items))
            if values:
                payload["artifacts"][name] = values[:max_items]
        return payload

    def _bibliography_payload(self, target: Path, *, max_items: int) -> list[str]:
        items: list[str] = []
        for bib in sorted(target.glob("*.bib"))[:4]:
            text = self._safe_read(bib)
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("@") or "title" in stripped.lower() or "author" in stripped.lower():
                    items.append(f"{self.workspace.relative(bib)}: {stripped[:240]}")
                if len(items) >= max_items:
                    return items
        return items

    def _reference_payload(self, target: Path, *, max_items: int) -> list[str]:
        items: list[str] = []
        for folder in sorted(target.glob("referencias-*")) + sorted(target.glob("planeaciones-*")):
            if folder.is_dir():
                for path in sorted(folder.rglob("*")):
                    if path.is_file():
                        items.append(self.workspace.relative(path))
                    if len(items) >= max_items:
                        return items
        return items

    def _tex_payload(self, target: Path, *, max_items: int) -> list[str]:
        items: list[str] = []
        for tex in sorted(target.glob("*.tex"))[:8]:
            for line in self._safe_read(tex).splitlines():
                stripped = line.strip()
                if stripped.startswith("\\section") or stripped.startswith("\\subsection") or stripped.startswith("\\frametitle"):
                    items.append(f"{self.workspace.relative(tex)}: {stripped[:220]}")
                if len(items) >= max_items:
                    return items
        return items

    def _distributed_memory_paths(self, target: Path, *, max_items: int) -> list[str]:
        paths = []
        for path in sorted(target.rglob(".memoria-aulatex/*.json"))[:max_items]:
            paths.append(self.workspace.relative(path))
        return paths

    def _json_or_lines(self, path: Path, *, limit: int) -> list[str]:
        text = self._safe_read(path)
        if not text:
            return []
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return [line.strip()[:240] for line in text.splitlines() if line.strip()][:limit]
        out: list[str] = []
        self._flatten(payload, out, limit=limit)
        return out[:limit]

    def _flatten(self, value: Any, out: list[str], *, limit: int) -> None:
        if len(out) >= limit:
            return
        if isinstance(value, dict):
            for key, nested in value.items():
                if isinstance(nested, (str, int, float)):
                    out.append(f"{key}: {nested}"[:240])
                else:
                    self._flatten(nested, out, limit=limit)
                if len(out) >= limit:
                    return
        elif isinstance(value, list):
            for item in value:
                self._flatten(item, out, limit=limit)
                if len(out) >= limit:
                    return
        elif isinstance(value, str) and value.strip():
            out.append(value.strip()[:240])

    def _safe_read(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""

    def _render_markdown(self, data: dict[str, Any]) -> str:
        lines = [
            "## Contexto editorial unificado AulaTeX",
            f"- Scope: {data.get('level')} | {data.get('scope_key')}",
            f"- Ruta: {data.get('relative_path') or '.'}",
            "- Prioridad: instrucciones locales > extractor > memoria distribuida > herencia > LLM.",
            "- Regla: no inventar referencias; si faltan, marcar supuesto y usar investigación pendiente.",
            "",
            "### Memoria editorial distribuida/heredada",
            data.get("memory_markdown") or "Sin memoria disponible.",
            "",
            "### Detail planner",
        ]
        editing = data.get("editing_details") or {}
        if editing:
            heading = editing.get("heading_contract") or {}
            didactic = editing.get("didactic_contract") or {}
            lines.append(f"- Subject canonico: {heading.get('subject_rule','')}")
            lines.append(f"- Tecnica detectada: {didactic.get('detected_id','general')}")
            for rule in list(editing.get("quality_rules") or [])[:5]:
                lines.append(f"- Regla: {rule}")
        else:
            lines.append("- Sin editing_details persistidos.")
        lines.extend([
            "",
            "### Extractor y planeación disponible",
        ])
        extractor = data.get("extractor", {})
        if extractor.get("artifacts"):
            for name, values in extractor["artifacts"].items():
                lines.append(f"- {name}:")
                lines.extend(f"  - {item}" for item in values[:12])
        else:
            lines.append("- Sin artefactos de extractor disponibles.")
        lines.append("\n### Bibliografía y referencias locales")
        for item in data.get("bibliography", [])[:12]:
            lines.append(f"- {item}")
        for item in data.get("references", [])[:12]:
            lines.append(f"- {item}")
        if not data.get("bibliography") and not data.get("references"):
            lines.append("- Sin referencias locales detectadas.")
        lines.append("\n### Señales TEX locales")
        tex_items = data.get("tex", [])
        lines.extend(f"- {item}" for item in tex_items[:12]) if tex_items else lines.append("- Sin señales TEX detectadas.")
        lines.append("\n### Archivos de memoria distribuida")
        mem_paths = data.get("distributed_memory", [])
        lines.extend(f"- {item}" for item in mem_paths[:12]) if mem_paths else lines.append("- Sin archivos .memoria-aulatex detectados bajo el nodo.")
        return "\n".join(lines)
