from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path


CONTRACT_VERSION = "1.0"


def subject_layout(target: Path) -> dict[str, Path]:
    target = target.resolve()
    slug = re.sub(r"-(lde|lad|mga|isc|imtc)$", "", target.name, flags=re.IGNORECASE)
    references = target / f"referencias-{slug}"
    return {
        "plans": target / f"planeaciones-{slug}",
        "references": references,
        "notes": references / f"notas-{slug}",
        "assets": target / f"assets-{slug}",
        "extractions": target / "extractor-aulatex",
        "research": target / "investigacion-aulatex",
    }


def _safe_child(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise ValueError("La salida debe permanecer dentro de la materia.")
    return candidate


def _reject_credentials(value: object) -> None:
    if isinstance(value, dict):
        forbidden = {"password", "api_key", "access_token", "refresh_token", "cookie", "cookies", "authorization", "secret", "sesskey"}
        if forbidden.intersection(str(key).lower() for key in value):
            raise ValueError("El modelo contiene campos de credenciales; no se publicará.")
        for child in value.values():
            _reject_credentials(child)
    elif isinstance(value, list):
        for child in value:
            _reject_credentials(child)
    elif isinstance(value, str) and re.search(r"(?i)([?&](sesskey|access_token|token|api_key)=|bearer\s+\S+|-----BEGIN .*PRIVATE KEY-----)", value):
        raise ValueError("El modelo contiene datos de acceso; no se publicará.")


def _require_versionable(target: Path, paths: list[Path]) -> None:
    probe = subprocess.run(["git", "-C", str(target), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if probe.returncode:
        if "not a git repository" in probe.stderr.lower():
            return
        raise ValueError("No se pudo comprobar el repositorio Git; revise acceso y safe.directory.")
    result = subprocess.run(
        ["git", "-C", str(target), "check-ignore", "--no-index", "--stdin"],
        input="\n".join(str(path) for path in paths) + "\n", capture_output=True, text=True,
    )
    if result.returncode == 0:
        raise ValueError("Git excluye artefactos académicos de esta materia; revise .gitignore antes de generar.")
    if result.returncode != 1:
        raise ValueError("No se pudo verificar la inclusión de artefactos en Git.")


def generate_plans(target: Path, source: Path, *, index_name: str = "README.md") -> tuple[Path, ...]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.md", index_name):
        raise ValueError("El índice debe ser un nombre Markdown sin directorios.")
    target = target.resolve()
    if not target.is_dir():
        raise ValueError("La carpeta de materia debe existir.")
    payload = json.loads(source.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("Se requiere un objeto JSON con activity o activities.")
    _reject_credentials(payload)
    activities = payload.get("activities")
    if activities is None:
        activities = [payload.get("activity")]
    if not isinstance(activities, list) or not activities:
        raise ValueError("Se requiere al menos una actividad.")
    layout = subject_layout(target)
    for folder in layout.values():
        _safe_child(target, folder.relative_to(target).as_posix())
    context = {key: value for key, value in payload.items() if key not in ("activity", "activities")}
    planned: dict[Path, bytes] = {}
    rows = []
    for activity in activities:
        if not isinstance(activity, dict) or not isinstance(activity.get("title"), str) or not activity["title"].strip():
            raise ValueError("Cada actividad requiere title e id.")
        identifier = str(activity.get("id", ""))
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", identifier):
            raise ValueError("Identificador de actividad ausente o inseguro.")
        if not activity.get("requirements") and not activity.get("observed_questions"):
            raise ValueError("Cada actividad requiere requisitos o reactivos documentados.")
        filename = f"planeacion-modulo-{identifier}"
        document = dict(context, activity=activity)
        document["artifact_contract"] = {
            "version": CONTRACT_VERSION,
            "academic_materials_versioned": True,
            "paths_relative_to_subject": {key: path.relative_to(target).as_posix() for key, path in layout.items()},
            "deliverables_directory": ".",
            "mode": "normalizar_modelo_aportado",
        }
        title = " ".join(activity["title"].splitlines())
        markdown = f"# Planeación - {title}\n\nModelo aportado; no implica aprobación docente ni entrega.\n"
        for key, value in document.items():
            markdown += f"\n## {key}\n\n```json\n{json.dumps(value, ensure_ascii=False, indent=2)}\n```\n"
        for suffix, text in ((".json", json.dumps(document, ensure_ascii=False, indent=2) + "\n"), (".md", markdown)):
            destination = _safe_child(target, (layout["plans"] / (filename + suffix)).relative_to(target).as_posix())
            if destination in planned:
                raise ValueError("Identificador de actividad duplicado.")
            planned[destination] = text.encode("utf-8")
        rows.append(f"- [{identifier}: {title}]({filename}.md) · [JSON]({filename}.json)")
    index = _safe_child(target, (layout["plans"] / index_name).relative_to(target).as_posix())
    if index in planned:
        raise ValueError("El índice no puede reemplazar una planeación.")
    planned[index] = ("# Planeaciones de la materia\n\n" + "\n".join(rows) + "\n").encode("utf-8")
    descriptions = {
        "references": "Fuentes, originales y manifiestos. Organizar por tipo o revisión; no guardar credenciales.",
        "notes": "Notas por unidad o actividad. Distinguir interpretaciones propias de extractos de fuentes.",
        "assets": "Imágenes y recursos gráficos de la materia, con procedencia y derechos de uso.",
        "extractions": "Extracciones y fichas con su fuente y localizador. Este índice no acredita una extracción realizada.",
        "research": "Análisis y evidencias de investigación. Este índice no acredita trabajo de campo ni resultados.",
    }
    for key, description in descriptions.items():
        support_index = _safe_child(target, (layout[key] / "README.md").relative_to(target).as_posix())
        if not support_index.exists():
            planned[support_index] = f"# {layout[key].name}\n\n{description}\n\nMaterial académico versionable dentro de la materia.\n".encode("utf-8")
    _require_versionable(target, list(planned) + [folder / "material-academico.json" for folder in layout.values()])
    for path, content in planned.items():
        if path.exists() and path.read_bytes() != content:
            raise FileExistsError(f"Se conserva la versión existente: {path.name}")
    for folder in layout.values():
        folder.mkdir(parents=True, exist_ok=True)
    for path, content in planned.items():
        if not path.exists():
            path.write_bytes(content)
        if hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(content).digest():
            raise OSError(f"Verificación fallida: {path.name}")
    return tuple(path for path in planned if path.parent == layout["plans"])