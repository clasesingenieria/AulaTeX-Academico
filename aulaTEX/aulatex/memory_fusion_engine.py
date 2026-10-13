from __future__ import annotations

import json
import re
from pathlib import Path


class MemoryFusionEngine:
    def distill(self, fused: dict, output_path: Path) -> dict:
        dna = {
            "editorial_dna": [],
            "quality_gates": [],
            "operational_rules": [],
            "telemetry": [],
            "disciplinary_knowledge": [],
        }
        for cluster in fused.get("clusters", []):
            text = str(cluster.get("canonical", ""))
            lower = text.lower()
            item = {
                "text": text,
                "frequency": cluster.get("frequency", 0),
                "section": cluster.get("section", ""),
            }
            if any(term in lower for term in ["ciclo", "json parseable", "motor", "codex", "gpt", "claude"]):
                dna["telemetry"].append(item)
            elif any(term in lower for term in ["compilar", "referencias rotas", "citas", "quality", "calidad"]):
                dna["quality_gates"].append(item)
            elif any(term in lower for term in ["normalización", "normalizacion", "propagar", "deduplic", "lossless"]):
                dna["operational_rules"].append(item)
            elif any(term in lower for term in ["filosof", "justicia", "derecho", "ius", "juríd"]):
                dna["disciplinary_knowledge"].append(item)
            else:
                dna["editorial_dna"].append(item)
        output_path.write_text(json.dumps(dna, ensure_ascii=False, indent=2), encoding="utf-8")
        return dna
    def fuse_markdown_files(self, markdown_files: list[Path], output_path: Path) -> dict:
        groups: dict[str, dict] = {}
        for md_file in markdown_files:
            section = "summary"
            content = md_file.read_text(encoding="utf-8", errors="replace")
            if self._fuse_json_markdown(content, groups, md_file.name):
                continue
            paragraph: list[str] = []
            in_fenced_block = False
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("```"):
                    in_fenced_block = not in_fenced_block
                    continue
                if in_fenced_block and stripped.startswith(('"', '-', '*')):
                    stripped = stripped.strip(',')
                    stripped = re.sub(r'^"?[A-Za-z0-9_ -]+"?\s*:\s*', '', stripped).strip()
                    stripped = stripped.strip('"').strip(',')
                    self._add_markdown_value(groups, stripped, section, md_file.name)
                    continue
                if in_fenced_block:
                    continue
                if line.startswith("## "):
                    self._flush_markdown_paragraph(groups, paragraph, section, md_file.name)
                    paragraph = []
                    section = line[3:].strip().lower().replace(" ", "_")
                    continue
                if not stripped:
                    self._flush_markdown_paragraph(groups, paragraph, section, md_file.name)
                    paragraph = []
                    continue
                if stripped.startswith("- "):
                    self._flush_markdown_paragraph(groups, paragraph, section, md_file.name)
                    paragraph = []
                    self._add_markdown_value(groups, stripped[2:].strip(), section, md_file.name)
                    continue
                if stripped.startswith('"'):
                    self._flush_markdown_paragraph(groups, paragraph, section, md_file.name)
                    paragraph = []
                    value = stripped.strip(',')
                    value = re.sub(r'^"?[A-Za-z0-9_ -]+"?\s*:\s*', '', value).strip()
                    value = value.strip('"').strip(',')
                    self._add_markdown_value(groups, value, section, md_file.name)
                    continue
                if stripped.startswith(("#", "{", "}", "[", "]")):
                    continue
                paragraph.append(stripped)
            self._flush_markdown_paragraph(groups, paragraph, section, md_file.name)
        fused = {
            "clusters": sorted(groups.values(), key=lambda item: (-item["frequency"], item["canonical"])),
            "cluster_count": len(groups),
            "source_files": [p.name for p in markdown_files],
        }
        output_path.write_text(json.dumps(fused, ensure_ascii=False, indent=2), encoding="utf-8")
        return fused

    def _fuse_json_markdown(self, content: str, groups: dict[str, dict], source: str) -> bool:
        candidates = [content]
        fenced = re.findall(r"```(?:json)?\s*(.*?)```", content, flags=re.IGNORECASE | re.DOTALL)
        candidates.extend(block.strip() for block in fenced if block.strip())
        payload = None
        for candidate in candidates:
            try:
                payload = json.loads(candidate)
                break
            except json.JSONDecodeError:
                continue
        if not isinstance(payload, dict):
            return False
        consumed = False
        for section, values in payload.items():
            if isinstance(values, list):
                for value in values:
                    if isinstance(value, str):
                        self._add_markdown_value(groups, value, str(section), source)
                        consumed = True
                    elif isinstance(value, dict):
                        for nested_value in value.values():
                            if isinstance(nested_value, str):
                                self._add_markdown_value(groups, nested_value, str(section), source)
                                consumed = True
            elif isinstance(values, str):
                self._add_markdown_value(groups, values, str(section), source)
                consumed = True
        return consumed

    def _flush_markdown_paragraph(self, groups: dict[str, dict], paragraph: list[str], section: str, source: str) -> None:
        if not paragraph:
            return
        value = " ".join(paragraph).strip()
        paragraph.clear()
        self._add_markdown_value(groups, value, section, source)

    def _add_markdown_value(self, groups: dict[str, dict], value: str, section: str, source: str) -> None:
        value = re.sub(r"\s+", " ", value).strip()
        if len(value) < 24:
            return
        key = self._semantic_key(value)
        if not key:
            return
        bucket = groups.setdefault(key, {
            "canonical": value,
            "frequency": 0,
            "sources": [],
            "variants": [],
            "section": section,
        })
        bucket["frequency"] += 1
        bucket["sources"].append(source)
        if value not in bucket["variants"]:
            bucket["variants"].append(value)
    def fuse_directory(self, memory_dir: Path, output_path: Path) -> dict:
        groups: dict[str, dict] = {}
        for json_file in sorted(memory_dir.glob("*.json")):
            payload = json.loads(json_file.read_text(encoding="utf-8", errors="replace"))
            for section, values in payload.items():
                if not isinstance(values, list):
                    continue
                for value in values:
                    if not isinstance(value, str) or not value.strip():
                        continue
                    key = self._semantic_key(value)
                    bucket = groups.setdefault(
                        key,
                        {
                            "canonical": value.strip(),
                            "frequency": 0,
                            "sources": [],
                            "variants": [],
                            "section": section,
                        },
                    )
                    bucket["frequency"] += 1
                    bucket["sources"].append(json_file.name)
                    if value.strip() not in bucket["variants"]:
                        bucket["variants"].append(value.strip())

        fused = {
            "clusters": sorted(groups.values(), key=lambda item: (-item["frequency"], item["canonical"])),
            "cluster_count": len(groups),
        }
        output_path.write_text(json.dumps(fused, ensure_ascii=False, indent=2), encoding="utf-8")
        return fused

    def _semantic_key(self, text: str) -> str:
        value = text.lower()
        replacements = {
            "json": "estructura",
            "estructurada": "estructura",
            "normalizacion": "normalizar",
            "normalización": "normalizar",
            "deduplicacion": "dedupe",
            "deduplicación": "dedupe",
            "lossless": "sinperdida",
            "tex reconstruible": "texreconstruible",
        }
        for old, new in replacements.items():
            value = value.replace(old, new)
        value = re.sub(r"[^a-záéíóúñ0-9 ]+", " ", value)
        tokens = [token for token in value.split() if len(token) > 3]
        return " ".join(sorted(set(tokens))[:12])