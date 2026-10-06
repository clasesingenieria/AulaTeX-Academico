from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from .workspace import AulaTeXWorkspace


SCHEMA_VERSION = "1.0"
SELECTION_FILENAME = "seleccion-plantillas-aulatex.json"
CATALOG_FILENAME = "catalogo-plantillas-aulatex.json"
REPORT_FILENAME = "AUDITORIA-PLANTILLAS.md"


def _files(root: Path):
    for directory, folders, names in os.walk(root, followlinks=False):
        folders[:] = sorted(name for name in folders if not name.startswith(".")
                            and name not in {"node_modules", "__pycache__"}
                            and not (Path(directory) / name).is_symlink())
        for name in sorted(names):
            path = Path(directory) / name
            if not path.is_symlink():
                yield path


def _hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _json(path: Path) -> dict:
    with path.open(encoding="utf-8-sig") as stream:
        result = json.load(stream)
    if not isinstance(result, dict):
        raise ValueError("Se requiere un objeto JSON.")
    return result


def _local_path(root: Path, value: str) -> Path | None:
    candidate = (root / value).resolve()
    return candidate if candidate.is_relative_to(root.resolve()) else None


def _kind(path: Path, slug: str, folder: str) -> tuple[str, str] | None:
    name = path.stem.casefold()
    if "plantilla" in name or name.startswith("formato-"):
        role = "presentation" if name.startswith("presentacion-") else "activity" if "actividad" in name else "report"
        return role, "adapter_candidate"
    for prefix, role in (("reporte", "report"), ("presentacion", "presentation")):
        if name in {f"{prefix}-{slug}".casefold(), f"{prefix}-{folder}".casefold()}:
            return role, "base_candidate"
    return None


def _inspect(path: Path, root: Path, index: dict) -> dict:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    text = re.sub(r"(?<!\\)%[^\n]*", "", text)
    dependencies = []
    pattern = r"\\(input|include|bibliography|addbibresource)\s*(?:\[[^\]]*\])?\s*\{([^{}]+)\}"
    for command, argument in re.findall(pattern, text):
        if "\\" in argument or "#" in argument:
            dependencies.append({"command": command, "status": "dynamic_not_checked"})
            continue
        for value in argument.split(","):
            value = value.strip()
            extension = ".bib" if command in {"bibliography", "addbibresource"} else ".tex"
            if not Path(value).suffix:
                value += extension
            direct = [_local_path(root, value), _local_path(root, str(path.parent / value))]
            candidates = sorted({candidate.relative_to(root).as_posix() for candidate in direct
                                 if candidate is not None and candidate.is_file()})
            if not candidates:
                candidates = sorted(candidate.relative_to(root).as_posix()
                                    for candidate in index.get(Path(value).name.casefold(), [])
                                    if candidate.as_posix().casefold().endswith("/" + value.replace("\\", "/").casefold()))
            dependencies.append({"command": command, "target": value,
                                 "status": "unresolved" if not candidates else "ambiguous" if len(candidates) > 1 else "found",
                                 "candidates": candidates})
    engine = "xelatex_or_lualatex" if re.search(r"\\(?:setmainfont|setsansfont)|\{fontspec\}", text) else "not_declared"
    bibliography = "biber" if re.search(r"backend\s*=\s*biber", text) else "biblatex_backend_not_declared" if "biblatex" in text else "bibtex" if "\\bibliography{" in text else "not_declared"
    return {"path": path.relative_to(root).as_posix(), "sha256": _hash(path), "engine_hint": engine,
            "bibliography_hint": bibliography, "dependencies": dependencies,
            "compilation": "not_run", "validation_scope": "literal_tex_and_bib_references_only"}


def _manifest_issues(root: Path, directory: Path) -> list[dict]:
    path = directory / "estructura-aulatex.json"
    if not path.is_file():
        return []
    relative = path.relative_to(root).as_posix()
    try:
        payload = _json(path)
    except (OSError, ValueError):
        return [{"code": "invalid_manifest", "path": relative}]
    issues = []
    if "schema_version" not in payload:
        issues.append({"code": "unversioned_manifest", "path": relative})
    for field in ("files", "folders"):
        values = payload.get(field, [])
        if not isinstance(values, list):
            issues.append({"code": "invalid_manifest_field", "path": relative, "field": field})
            continue
        for value in values:
            candidate = _local_path(root, str(directory / value)) if isinstance(value, str) else None
            if candidate is None:
                issues.append({"code": "unsafe_manifest_path", "path": relative, "field": field})
            elif not (candidate.is_file() if field == "files" else candidate.is_dir()):
                issues.append({"code": "missing_declared_path", "path": relative,
                               "missing": candidate.relative_to(root).as_posix(), "field": field})
    return issues


def audit_temporaries(workspace: AulaTeXWorkspace, institutional_files: list[Path]) -> list[dict]:
    root = workspace.repo_root
    folders = sorted(path for path in root.iterdir() if path.is_dir() and not path.is_symlink()
                     and (path.name.startswith(".tmp") or path.name in {"tmp", ".aulatex-temp", ".build"}))
    if not folders:
        return []
    tracked = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--", *[path.name for path in folders]],
                             capture_output=True, check=False)
    tracked_paths = tracked.stdout.decode("utf-8", errors="replace").split("\0") if tracked.returncode == 0 else []
    archive = defaultdict(list)
    for path in institutional_files:
        archive[path.name].append(path)
    summaries = []
    for folder in folders:
        files = list(_files(folder))
        evidence = []
        for path in files:
            if not re.search(r"receipt|after-save|confirmacion|signed-review", path.name, re.IGNORECASE):
                continue
            copies = [candidate.relative_to(root).as_posix() for candidate in archive.get(path.name, [])
                      if candidate.stat().st_size == path.stat().st_size and _hash(candidate) == _hash(path)]
            evidence.append({"path": path.relative_to(root).as_posix(), "identical_institutional_copies": copies,
                             "status": "copy_verified" if copies else "preserve_pending_review"})
        summaries.append({"path": folder.name, "files": len(files), "bytes": sum(path.stat().st_size for path in files),
                          "tracked_files": sum(value.startswith(folder.name + "/") for value in tracked_paths) if tracked.returncode == 0 else None,
                          "extensions": dict(sorted(Counter(path.suffix.lower() for path in files).items())),
                          "evidence": evidence, "automatic_deletion": False})
    return summaries


def build_template_catalog(workspace: AulaTeXWorkspace) -> dict:
    root = workspace.repo_root.resolve()
    scopes = workspace.scan_editorial_scopes()
    institutions = [root / scope.relative_path for scope in scopes if scope.level == "institucion"]
    institutional_files = [path for institution in institutions for path in _files(institution)]
    index = defaultdict(list)
    for path in [*institutional_files, *_files(root / "base")]:
        if path.suffix.lower() in {".tex", ".bib"}:
            index[path.name.casefold()].append(path)
    issues = []
    selection_path = root / SELECTION_FILENAME
    selections = {}
    if selection_path.is_file():
        try:
            payload = _json(selection_path)
            if payload.get("schema_version") != SCHEMA_VERSION or not isinstance(payload.get("subjects"), dict):
                raise ValueError("Esquema de seleccion no compatible.")
            selections = payload["subjects"]
        except (OSError, ValueError):
            issues.append({"code": "invalid_selection_registry", "path": SELECTION_FILENAME})
    artifacts = {}
    subjects = []
    directories = {root, *institutions}
    for scope in scopes:
        if scope.level != "materia":
            continue
        directory = root / scope.relative_path
        directories.add(directory)
        slug = re.sub(r"-(lde|lad|mga|isc|imtc)$", "", directory.name, flags=re.IGNORECASE)
        candidates = []
        for path in sorted(directory.glob("*.tex")):
            if path.is_symlink():
                continue
            kind = _kind(path, slug, directory.name)
            if kind is None:
                continue
            relative = path.relative_to(root).as_posix()
            artifacts[relative] = _inspect(path, root, index)
            candidates.append({"path": relative, "role": kind[0], "kind": kind[1]})
        declared = selections.get(scope.relative_path, {})
        active = {}
        if not isinstance(declared, dict):
            issues.append({"code": "invalid_subject_selection", "path": scope.relative_path})
            declared = {}
        for role, value in declared.items():
            if role not in {"report", "presentation", "activity"} or not isinstance(value, str) or not any(
                    item["path"] == value and item["role"] == role for item in candidates):
                issues.append({"code": "invalid_template_selection", "path": scope.relative_path, "role": role})
                continue
            active[role] = value
        if not candidates:
            issues.append({"code": "no_template_candidates", "path": scope.relative_path})
        subjects.append({"id": scope.key, "path": scope.relative_path, "institution": scope.institution,
                         "program": scope.career, "candidates": candidates, "selected": active,
                         "selection_status": "declared_not_compilation_verified" if active else "pending_review"})
    for directory in sorted(directories):
        issues.extend(_manifest_issues(root, directory))
    known = {item["path"] for item in subjects}
    for unknown in sorted(set(selections) - known):
        issues.append({"code": "unknown_subject_selection", "path": unknown})
    return {"schema_version": SCHEMA_VERSION, "mode": "read_only_inventory", "subjects": subjects,
            "artifacts": artifacts, "issues": issues, "temporaries": audit_temporaries(workspace, institutional_files),
            "limits": ["No compilation or academic validation performed.",
                       "Candidate names do not establish current or official status.",
                       "Graphics, dynamic TeX paths and system package resolution are not validated.",
                       "Temporary evidence matching uses identical filenames and SHA-256; absence of a match does not prove uniqueness."]}


def render_catalog_markdown(catalog: dict) -> str:
    lines = ["# Auditoria de plantillas y temporales", "", "Inventario de solo lectura. No acredita compilacion, vigencia docente ni entrega.",
             "", "| Institucion | Materias | Con candidatos | Con seleccion declarada |", "|---|---:|---:|---:|"]
    institutions = sorted({item["institution"] for item in catalog["subjects"]})
    for institution in institutions:
        items = [item for item in catalog["subjects"] if item["institution"] == institution]
        lines.append(f"| {institution} | {len(items)} | {sum(bool(item['candidates']) for item in items)} | {sum(bool(item['selected']) for item in items)} |")
    lines.extend(["", "## Discrepancias", ""])
    for issue in catalog["issues"]:
        lines.append(f"- {issue['code']}: {issue['path']}" + (f" -> {issue['missing']}" if "missing" in issue else ""))
    lines.extend(["", "## Temporales", "", "No se autoriza borrado automatico, ni siquiera cuando existe una copia.", ""])
    for item in catalog["temporaries"]:
        pending = sum(evidence["status"] == "preserve_pending_review" for evidence in item["evidence"])
        lines.append(f"- {item['path']}: {item['files']} archivos; {item['tracked_files']} registrados en Git; {pending} evidencias requieren revision.")
    lines.extend(["", "## Limites", "", *[f"- {item}" for item in catalog["limits"]], "",
                  f"Detalle verificable: {CATALOG_FILENAME}. Seleccion explicita: {SELECTION_FILENAME}.", ""])
    return "\n".join(lines)


def _write_atomic(path: Path, text: str) -> None:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".aulatex-catalog-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def export_catalog(workspace: AulaTeXWorkspace, catalog: dict) -> tuple[Path, Path]:
    paths = workspace.repo_root / CATALOG_FILENAME, workspace.repo_root / REPORT_FILENAME
    _write_atomic(paths[0], json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
    _write_atomic(paths[1], render_catalog_markdown(catalog))
    return paths


def select_template(workspace: AulaTeXWorkspace, subject_path: str, template_path: str, role: str) -> None:
    root = workspace.repo_root.resolve()
    directory = _local_path(root, subject_path)
    template = _local_path(root, template_path)
    known = {scope.relative_path for scope in workspace.scan_editorial_scopes() if scope.level == "materia"}
    if subject_path not in known or directory is None or template is None or template.parent != directory or not template.is_file():
        raise ValueError("La plantilla debe existir dentro de una materia reconocida.")
    slug = re.sub(r"-(lde|lad|mga|isc|imtc)$", "", directory.name, flags=re.IGNORECASE)
    kind = _kind(template, slug, directory.name)
    if template.suffix.lower() != ".tex" or kind is None or kind[0] != role:
        raise ValueError("El archivo no es un candidato del tipo solicitado.")
    path = root / SELECTION_FILENAME
    payload = _json(path) if path.exists() else {"schema_version": SCHEMA_VERSION, "subjects": {}}
    if payload.get("schema_version") != SCHEMA_VERSION or not isinstance(payload.get("subjects"), dict):
        raise ValueError("El registro de seleccion existente no es compatible; se conserva sin cambios.")
    current = payload["subjects"].get(subject_path, {})
    if not isinstance(current, dict):
        raise ValueError("La seleccion existente de la materia no es un objeto; se conserva sin cambios.")
    payload["subjects"][subject_path] = {**current, role: template_path}
    _write_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")