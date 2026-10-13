"""Preparación segura y reproducible del corpus del motor inteligente AulaTeX.

Este módulo contiene la lógica reutilizable por notebooks y pruebas. No carga
credenciales ni publica datos. Los datasets reales se escriben bajo
``data/private`` y deben permanecer fuera de Git.
"""

from __future__ import annotations

import hashlib
import json
import platform
import random
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

SCHEMA_VERSION = "1.0"
MIN_DOCUMENT_CHARS = 400
EXCLUDED_PARTS = {
    ".git", ".venv", ".aulatex-temp", ".build", "base", "node_modules",
    "outputs", "models", "data", "retroalimentacion-editorial", "__pycache__",
}
NATIVE_IMAGE_COMMANDS = (r"\insertimage", r"\begin{images}", r"\addimage")

SYSTEM_PROMPT = """Eres el motor inteligente editorial de AulaTeX. Genera una actividad académica rigurosa en LaTeX basada únicamente en el contexto y las claves bibliográficas permitidas. Conserva la técnica didáctica y organiza el cuerpo visible en Introducción, una única sección temática de desarrollo y Conclusiones. El producto solicitado debe ser el núcleo del desarrollo. No inventes fuentes ni claves de cita. Cuando uses imágenes en documentos que cargan el template AulaTeX, utiliza \\insertimage o el entorno images con \\addimage; no uses figure/includegraphics manual."""

_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----")),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}", re.I)),
    ("generic_secret", re.compile(r"(?i)\b(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[^\s'\"]{12,}")),
)
_PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
    ("phone", re.compile(r"(?<!\d)(?:\+?52[\s.-]?)?(?:\d[\s.-]?){10}(?!\d)")),
    ("student_id", re.compile(r"(?i)\b(?:matr[ií]cula|student[_ -]?id)\s*[:#-]?\s*[A-Z0-9-]{5,}")),
    ("windows_path", re.compile(r"\b[A-Z]:\\Users\\[^\\\s]+", re.I)),
)


@dataclass(frozen=True)
class PrivacyFinding:
    kind: str
    source: str
    count: int


@dataclass(frozen=True)
class CorpusManifest:
    schema_version: str
    seed: int
    counts: dict[str, int]
    hashes: dict[str, str]
    source_root: str
    privacy_findings: int


def repo_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "aulaTEX" / "aulatex").is_dir() and (candidate / "aulaTEX/base").is_dir():
            return candidate
    return Path(__file__).resolve().parents[2]


def environment_report() -> dict[str, Any]:
    report: dict[str, Any] = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "executable": sys.executable,
        "cuda_available": False,
        "gpu_count": 0,
    }
    try:
        import torch

        report.update({"torch": torch.__version__, "cuda_available": torch.cuda.is_available()})
        if torch.cuda.is_available():
            report.update({
                "cuda": torch.version.cuda,
                "gpu_count": torch.cuda.device_count(),
                "gpus": [
                    {
                        "name": torch.cuda.get_device_name(index),
                        "vram_gib": round(torch.cuda.get_device_properties(index).total_memory / 2**30, 2),
                        "bf16": bool(torch.cuda.is_bf16_supported()),
                    }
                    for index in range(torch.cuda.device_count())
                ],
            })
    except ImportError:
        report["torch"] = None
    for package in ("transformers", "datasets", "peft", "trl", "bitsandbytes"):
        try:
            module = __import__(package)
            report[package] = getattr(module, "__version__", "instalado")
        except (ImportError, OSError):
            report[package] = None
    return report


def iter_activity_tex(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*.tex")):
        if EXCLUDED_PARTS.intersection(path.relative_to(root).parts):
            continue
        lowered = path.name.lower()
        if lowered.startswith(("reporte-", "presentacion-")) and "actividad-" in lowered:
            yield path


def inventory_sources(root: Path) -> dict[str, list[Path]]:
    def safe(pattern: str) -> list[Path]:
        return [
            path for path in sorted(root.rglob(pattern))
            if not EXCLUDED_PARTS.intersection(path.relative_to(root).parts)
        ]

    return {
        "activities": list(iter_activity_tex(root)),
        "programs": safe("programa-analitico-*.md"),
        "plans": [p for p in safe("*.md") if "planeacion" in p.as_posix().lower()],
        "extractor": [p for p in safe("*.json") if "extractor-aulatex" in p.as_posix()],
        "bibliographies": safe("*.bib"),
    }


def read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def document_body(text: str) -> str:
    match = re.search(r"\\begin\{document\}", text)
    body = text[match.end():] if match else text
    body = re.sub(r"\\end\{document\}.*", "", body, flags=re.DOTALL)
    body = "\n".join(line for line in body.splitlines() if not line.lstrip().startswith("%"))
    return re.sub(r"\n{3,}", "\n\n", body).strip()


def _section_key(title: str) -> str:
    """Normaliza un título para reconocer variantes acentuadas."""
    import unicodedata

    plain = unicodedata.normalize("NFKD", title)
    return "".join(char for char in plain if not unicodedata.combining(char)).strip().lower()


def _clip_latex_block(text: str, limit: int) -> str:
    """Recorta en frontera de párrafo y evita dejar grupos/entornos abiertos."""
    text = text.strip()
    if len(text) <= limit:
        return text
    candidate = text[:limit]
    boundary = candidate.rfind("\n\n")
    if boundary >= limit // 2:
        candidate = candidate[:boundary]
    lines = candidate.rstrip().splitlines()
    while lines:
        value = "\n".join(lines).rstrip()
        active = re.sub(r"(?<!\\)%.*$", "", value, flags=re.MULTILINE)
        brace_balance = active.count("{") - active.count("}")
        begins = re.findall(r"\\begin\{([^}]+)\}", active)
        ends = re.findall(r"\\end\{([^}]+)\}", active)
        if brace_balance == 0 and sorted(begins) == sorted(ends):
            return value
        lines.pop()
    return ""


def compact_training_body(text: str, max_chars: int = 3600) -> str:
    """Construye un objetivo corto con introducción, desarrollo y conclusión.

    La selección ocurre por secciones completas para que el cierre permanezca
    dentro de una ventana de 2048 tokens y no se enseñen fragmentos truncados.
    """
    matches = list(re.finditer(r"\\section\*?\{([^{}]+)\}", text, re.IGNORECASE))
    if not matches:
        return _clip_latex_block(text, max_chars)

    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match.group(1).strip(), text[match.end():end].strip()))

    intro_index = next(
        (index for index, (title, _) in enumerate(sections) if _section_key(title).startswith("introduc")),
        None,
    )
    conclusion_index = next(
        (index for index, (title, _) in reversed(list(enumerate(sections)))
         if _section_key(title).startswith("conclusion")),
        None,
    )
    if intro_index is None or conclusion_index is None or intro_index >= conclusion_index:
        head = _clip_latex_block(text, int(max_chars * 0.65))
        tail = _clip_latex_block(text[-int(max_chars * 0.35):], int(max_chars * 0.35))
        return head + "\n\n% [CONTENIDO INTERMEDIO OMITIDO]\n\n" + tail

    middle_index = next(
        (index for index in range(intro_index + 1, conclusion_index)),
        intro_index,
    )
    middle_title, middle_content = sections[middle_index]
    prefix = _clip_latex_block(text[:matches[intro_index].start()], 300)
    introduction = _clip_latex_block(sections[intro_index][1], 750)
    development = _clip_latex_block(middle_content, 1550)
    conclusion = _clip_latex_block(sections[conclusion_index][1], 850)
    parts = [prefix] if prefix else []
    parts.extend([
        "\\section{Introducción}\n" + introduction,
        f"\\section{{{middle_title}}}\n" + development,
        "\\section{Conclusiones}\n" + conclusion,
    ])
    return "\n\n".join(part.rstrip() for part in parts if part.strip())[:max_chars].rstrip()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def privacy_findings(text: str, source: str = "") -> list[PrivacyFinding]:
    findings: list[PrivacyFinding] = []
    for kind, pattern in (*_SECRET_PATTERNS, *_PII_PATTERNS):
        count = len(pattern.findall(text))
        if count:
            findings.append(PrivacyFinding(kind=kind, source=source, count=count))
    return findings


def redact_text(text: str) -> tuple[str, list[PrivacyFinding]]:
    findings = privacy_findings(text)
    redacted = text
    for kind, pattern in (*_SECRET_PATTERNS, *_PII_PATTERNS):
        redacted = pattern.sub(f"[REDACTED_{kind.upper()}]", redacted)
    return redacted, findings


def extract_bib_keys(text: str) -> list[str]:
    keys: set[str] = set()
    for group in re.findall(r"\\cite\w*\{([^}]+)\}", text):
        keys.update(key.strip() for key in group.split(",") if key.strip())
    return sorted(keys)


def detect_technique(text: str) -> str:
    lowered = text.lower()
    aliases = (
        ("mapa_conceptual", ("mapa conceptual", "tikzpicture")),
        ("tabla_didactica", ("cuadro comparativo", "longtable", "tabular")),
        ("cuestionario_diagnostico", ("cuestionario", "reactivo")),
        ("estudio_de_caso", ("estudio de caso", "caso práctico", "caso practico")),
        ("foro_diagnostico", ("foro diagnóstico", "foro diagnostico")),
    )
    return next((name for name, values in aliases if any(value in lowered for value in values)), "actividad_academica")


def make_instruction(path: Path, root: Path, text: str) -> str:
    relative = path.relative_to(root).as_posix()
    institution = relative.split("/", 1)[0]
    technique = detect_technique(text)
    citation_keys = extract_bib_keys(text)
    return (
        f"Genera una actividad para la institución {institution}. "
        f"Técnica didáctica: {technique}. Conserva el contrato editorial AulaTeX, "
        "estructura de tres actos y trazabilidad bibliográfica. "
        f"Claves bibliográficas permitidas: {', '.join(citation_keys) if citation_keys else 'ninguna'}."
    )


def build_sft_rows(root: Path, *, strict_privacy: bool = True,
                   min_score: float = 0.0) -> tuple[list[dict[str, Any]], list[PrivacyFinding]]:
    rows: list[dict[str, Any]] = []
    findings: list[PrivacyFinding] = []
    seen: set[str] = set()
    score_of = None
    if min_score > 0:
        sys.path.insert(0, str(root / "aulaTEX"))
        from aulatex.activity_optimizer import ActivityOptimizer

        optimizer = ActivityOptimizer.__new__(ActivityOptimizer)
        optimizer._current_concepts = None
        score_of = optimizer._quality_score
    for path in iter_activity_tex(root):
        full_text = read_utf8(path)
        if "POR DEFINIR" in full_text:
            continue
        score = float(score_of(full_text)) if score_of is not None else None
        if score is not None and score < min_score:
            continue
        body = document_body(full_text)
        if len(body) < MIN_DOCUMENT_CHARS:
            continue
        source = path.relative_to(root).as_posix()
        current = privacy_findings(body, source)
        findings.extend(current)
        if current and strict_privacy:
            continue
        clean, _ = redact_text(body)
        clean = compact_training_body(clean)
        fingerprint = sha256_text(re.sub(r"\s+", " ", clean).strip())
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        rows.append({
            "schema_version": SCHEMA_VERSION,
            "id": fingerprint[:16],
            "target": source,
            "group": str(path.parent.relative_to(root).as_posix()),
            "technique": detect_technique(clean),
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": make_instruction(path, root, clean)},
                {"role": "assistant", "content": clean},
            ],
            "allowed_citation_keys": extract_bib_keys(clean),
            "content_sha256": fingerprint,
            "validation_score": round(score, 2) if score is not None else None,
            "validation_rule": f"quality_score>={min_score:g}" if min_score > 0 else "unfiltered",
            "compacted_for_training": len(body) > len(clean),
        })
    return rows, findings


def validate_sft_row(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if row.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version inválida")
    messages = row.get("messages")
    if not isinstance(messages, list) or [m.get("role") for m in messages] != ["system", "user", "assistant"]:
        errors.append("messages debe contener system, user y assistant")
    elif any(not str(message.get("content", "")).strip() for message in messages):
        errors.append("hay mensajes vacíos")
    if not str(row.get("target", "")).strip():
        errors.append("target vacío")
    return errors


def grouped_split(rows: Sequence[dict[str, Any]], *, seed: int = 42,
                  train_ratio: float = 0.8, validation_ratio: float = 0.1) -> dict[str, list[dict[str, Any]]]:
    if train_ratio <= 0 or validation_ratio < 0 or train_ratio + validation_ratio >= 1:
        raise ValueError("Las proporciones deben dejar una partición de prueba positiva")
    groups = sorted({str(row.get("group") or row.get("target")) for row in rows})
    random.Random(seed).shuffle(groups)
    if not groups:
        return {"train": [], "validation": [], "test": []}
    n_train = max(1, int(len(groups) * train_ratio))
    n_validation = int(len(groups) * validation_ratio)
    if len(groups) >= 3:
        n_validation = max(1, n_validation)
        n_train = min(n_train, len(groups) - 2)
    train_groups = set(groups[:n_train])
    validation_groups = set(groups[n_train:n_train + n_validation])
    result = {"train": [], "validation": [], "test": []}
    for row in rows:
        group = str(row.get("group") or row.get("target"))
        split = "train" if group in train_groups else "validation" if group in validation_groups else "test"
        result[split].append(row)
    return result


def assert_no_group_leakage(splits: dict[str, Sequence[dict[str, Any]]]) -> None:
    group_sets = {
        name: {str(row.get("group") or row.get("target")) for row in rows}
        for name, rows in splits.items()
    }
    names = list(group_sets)
    for index, left in enumerate(names):
        for right in names[index + 1:]:
            overlap = group_sets[left] & group_sets[right]
            if overlap:
                raise ValueError(f"Fuga entre {left} y {right}: {sorted(overlap)[:3]}")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    materialized = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in materialized:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(materialized)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number} no contiene un objeto JSON")
        rows.append(value)
    return rows


def write_splits(out_dir: Path, splits: dict[str, Sequence[dict[str, Any]]], *, seed: int = 42,
                 source_root: Path | None = None, privacy_count: int = 0) -> CorpusManifest:
    assert_no_group_leakage(splits)
    counts: dict[str, int] = {}
    hashes: dict[str, str] = {}
    for name, rows in splits.items():
        path = out_dir / f"sft-{name}.jsonl"
        counts[name] = write_jsonl(path, rows)
        hashes[path.name] = sha256_file(path)
    manifest = CorpusManifest(
        schema_version=SCHEMA_VERSION,
        seed=seed,
        counts=counts,
        hashes=hashes,
        source_root=str((source_root or repo_root()).resolve()),
        privacy_findings=privacy_count,
    )
    (out_dir / "manifest.json").write_text(
        json.dumps(asdict(manifest), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def dataset_stats(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    techniques = Counter(str(row.get("technique", "")) for row in rows)
    lengths = [len(row["messages"][-1]["content"]) for row in rows if row.get("messages")]
    return {
        "rows": len(rows),
        "groups": len({str(row.get("group")) for row in rows}),
        "techniques": dict(techniques),
        "min_chars": min(lengths, default=0),
        "max_chars": max(lengths, default=0),
        "mean_chars": round(sum(lengths) / len(lengths), 1) if lengths else 0,
    }


def latex_generation_checks(text: str, allowed_citation_keys: Sequence[str] = ()) -> dict[str, Any]:
    cited = set(extract_bib_keys(text))
    allowed = set(allowed_citation_keys)
    manual_images = bool(re.search(r"\\includegraphics", text))
    native_images = any(command in text for command in NATIVE_IMAGE_COMMANDS)
    starts_with_latex = bool(re.match(r"\s*(?:```(?:latex|tex)?\s*)?\\", text, re.I))
    reasoning_prefix = bool(re.match(r"\s*(?:Okay|We need|I need|Let me|First,|Alright)", text, re.I))
    mojibake = bool(re.search(r"(?:A[?0-9][A-Za-z]|\ufffd|Ã.|Â.)", text))
    return {
        "has_introduction": bool(re.search(r"\\section\*?\{Introducci[oó]n\}", text, re.I)),
        "has_conclusion": bool(re.search(r"\\section\*?\{Conclusi(?:[oó]n|ones)\}", text, re.I)),
        "has_literal_development_heading": bool(re.search(r"\\section\*?\{Desarrollo\}", text, re.I)),
        "unknown_citation_keys": sorted(cited - allowed) if allowed else [],
        "uses_manual_includegraphics": manual_images,
        "uses_native_image_commands": native_images,
        "native_image_rule_ok": not manual_images or native_images,
        "has_placeholders": bool(re.search(r"\b(?:TODO|TBD|pendiente|lorem ipsum)\b", text, re.I)),
        "starts_with_latex": starts_with_latex,
        "has_reasoning_prefix": reasoning_prefix,
        "has_mojibake": mojibake,
    }
