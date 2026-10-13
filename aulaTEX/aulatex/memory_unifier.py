from __future__ import annotations

import json
import re
from pathlib import Path


def unify_markdown_memories(memory_dir: Path, output_path: Path) -> None:
    sections: dict[str, list[str]] = {}
    for md_file in sorted(memory_dir.glob("*.md")):
        current = "summary"
        sections.setdefault(current, [])
        content = md_file.read_text(encoding="utf-8", errors="replace")
        for line in content.splitlines():
            header = re.match(r"^##\s+(.+)$", line.strip())
            if header:
                current = header.group(1).strip().lower().replace(" ", "_")
                sections.setdefault(current, [])
                continue
            if line.strip().startswith("- "):
                sections[current].append(line.strip()[2:].strip())

    unified = {key: _dedupe(values) for key, values in sections.items() if values}
    output_path.write_text(json.dumps(unified, ensure_ascii=False, indent=2), encoding="utf-8")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = re.sub(r"\s+", " ", value.strip().lower())
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(value.strip())
    return result