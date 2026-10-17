from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import re
from typing import Any

from .planning_layout import subject_artifact_contract, subject_layout

MANIFEST_FILENAME = "estructura-aulatex.json"
SCHEMA_VERSION = "2.0"
VALID_TRIGGERS = {"materia", "carrera", "institucion", "sistema"}


def find_subject_root(path: Path) -> Path | None:
    """Dado un archivo o subdirectorio, localiza la raíz de la materia que lo contiene.

    Busca de abajo hacia arriba la carpeta que coincide con el patrón de materia:
    - Que contenga un manifest existente, o
    - Que contenga archivos .tex/.bib o carpetas canónicas (entregas-*, planeaciones-*, etc.).
    """
    candidate = path.resolve()
    if candidate.is_file():
        candidate = candidate.parent

    while candidate and candidate.parent != candidate:
        if (candidate / MANIFEST_FILENAME).is_file():
            return candidate
        if any(candidate.glob("reporte*.tex")) or any(candidate.glob("presentacion*.tex")):
            return candidate
        slug = re.sub(r"-(lde|lad|mga|isc|imtc)$", "", candidate.name, flags=re.IGNORECASE)
        if (candidate / f"entregas-{slug}").is_dir() or (candidate / f"planeaciones-{slug}").is_dir():
            return candidate
        candidate = candidate.parent
    return None


def deduce_subject_identity(subject_dir: Path) -> dict[str, str]:
    """Deduce institución, carrera, slug y título a partir de la ruta del directorio."""
    subject_dir = subject_dir.resolve()
    folder_slug = subject_dir.name
    slug = re.sub(r"-(lde|lad|mga|isc|imtc)$", "", folder_slug, flags=re.IGNORECASE)

    career_dir = subject_dir.parent
    institution_dir = career_dir.parent if career_dir else None

    institution = institution_dir.name if institution_dir and institution_dir.name not in {"", "."} else ""
    career = career_dir.name if career_dir and career_dir.name not in {"", "."} else ""

    words = [w.capitalize() for w in slug.split("-") if w]
    title = " ".join(words)

    return {
        "institution": institution,
        "career": career,
        "node": folder_slug,
        "slug": slug,
        "title": title,
    }


def scan_subject_files_and_folders(subject_dir: Path) -> tuple[list[str], list[str]]:
    """Escanea los archivos y carpetas clave presentes en la materia sin recursión profunda."""
    subject_dir = subject_dir.resolve()
    files: list[str] = []
    folders: list[str] = []

    try:
        for item in sorted(subject_dir.iterdir()):
            if item.name.startswith(".") and item.name not in {".memoria-aulatex"}:
                continue
            if item.is_file():
                if item.name.endswith((".tex", ".bib", ".md", ".pdf", ".json", ".ps1", ".sh")):
                    files.append(item.name)
            elif item.is_dir():
                folders.append(item.name)
                if item.name.startswith(("planeaciones-", "entregas-")):
                    try:
                        for sub in sorted(item.iterdir()):
                            if sub.is_file():
                                files.append(f"{item.name}/{sub.name}")
                    except OSError:
                        pass
    except OSError:
        pass

    return sorted(set(files)), sorted(set(folders))


def load_subject_manifest(subject_dir: Path) -> dict[str, Any] | None:
    """Carga el manifiesto de la materia si existe en disco."""
    manifest_path = subject_dir / MANIFEST_FILENAME
    if not manifest_path.is_file():
        return None
    try:
        with manifest_path.open(encoding="utf-8-sig") as stream:
            data = json.load(stream)
            if isinstance(data, dict):
                return data
    except (OSError, json.JSONDecodeError):
        pass
    return None


def save_subject_manifest(
    subject_dir: Path,
    trigger: str,
    detail: str = "",
    *,
    compilation: dict[str, Any] | None = None,
    editorial_memory: dict[str, Any] | None = None,
    actividades: dict[str, Any] | None = None,
    metadata_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Crea o actualiza el archivo único .json de la materia ante una modificación real.

    Disparadores admitidos:
    - 'materia': cambios directos en la materia (compilación, entregas, notas, consignas).
    - 'carrera': cambios en el contexto curricular o plan de estudios de la carrera.
    - 'institucion': cambios en lineamientos, periodos o logos institucionales.
    - 'sistema': cambios generados por scrapers, agentes LLM o herramientas del sistema.
    """
    if trigger not in VALID_TRIGGERS:
        raise ValueError(f"Trigger '{trigger}' no es válido. Debe ser uno de: {sorted(VALID_TRIGGERS)}")

    subject_dir = subject_dir.resolve()
    existing = load_subject_manifest(subject_dir) or {}
    identity = deduce_subject_identity(subject_dir)

    now = datetime.now().astimezone().isoformat()
    files, folders = scan_subject_files_and_folders(subject_dir)
    contract = subject_artifact_contract(subject_dir)

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": "subject_manifest",
        "node": existing.get("node") or identity["node"],
        "slug": existing.get("slug") or identity["slug"],
        "title": existing.get("title") or identity["title"],
        "institution": existing.get("institution") or identity["institution"],
        "career": existing.get("career") or identity["career"],
        "codigo_referencia": existing.get("codigo_referencia", ""),
        "docente": existing.get("docente", ""),
        "estudiante": existing.get("estudiante", ""),
        "matricula": existing.get("matricula", ""),
        "periodo": existing.get("periodo", ""),
        "modalidad": existing.get("modalidad", ""),
        "files": files if files else existing.get("files", []),
        "folders": folders if folders else existing.get("folders", []),
        "artifact_contract": contract,
    }

    # Conservar o actualizar memoria editorial
    memory_summary = existing.get("memory_summary", [])
    if editorial_memory:
        if "summary" in editorial_memory and isinstance(editorial_memory["summary"], list):
            memory_summary = editorial_memory["summary"]
        manifest["editorial_memory"] = editorial_memory
    elif "editorial_memory" in existing:
        manifest["editorial_memory"] = existing["editorial_memory"]
    manifest["memory_summary"] = memory_summary

    # Conservar o actualizar compilación
    if compilation:
        manifest["compilation"] = compilation
    elif "compilation" in existing:
        manifest["compilation"] = existing["compilation"]

    # Conservar o actualizar actividades
    if actividades:
        manifest["actividades"] = actividades
    elif "actividades" in existing:
        manifest["actividades"] = existing["actividades"]

    # Aplicar cualquier metadato adicional
    if metadata_updates:
        for k, v in metadata_updates.items():
            if v is not None:
                manifest[k] = v

    # Auditoría de origen del cambio
    audit = existing.get("audit") or {}
    manifest["audit"] = {
        "created_at": audit.get("created_at") or now,
        "updated_at": now,
        "trigger": trigger,
        "trigger_detail": detail or f"Modificación por {trigger}",
    }

    manifest_path = subject_dir / MANIFEST_FILENAME
    temp_path = manifest_path.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    temp_path.replace(manifest_path)

    return manifest


def propagate_career_manifests(
    career_dir: Path,
    detail: str = "Actualización curricular de carrera",
    *,
    metadata_updates: dict[str, Any] | None = None,
) -> list[Path]:
    """Actualiza con trigger='carrera' las materias activas bajo la carpeta de carrera."""
    updated: list[Path] = []
    career_dir = career_dir.resolve()
    if not career_dir.is_dir():
        return updated
    for child in career_dir.iterdir():
        if child.is_dir() and (child / MANIFEST_FILENAME).is_file():
            save_subject_manifest(
                child,
                trigger="carrera",
                detail=detail,
                metadata_updates=metadata_updates,
            )
            updated.append(child)
    return updated


def propagate_institution_manifests(
    institution_dir: Path,
    detail: str = "Actualización institucional",
    *,
    metadata_updates: dict[str, Any] | None = None,
) -> list[Path]:
    """Actualiza con trigger='institucion' las materias activas bajo la carpeta institucional."""
    updated: list[Path] = []
    institution_dir = institution_dir.resolve()
    if not institution_dir.is_dir():
        return updated
    for career_child in institution_dir.iterdir():
        if career_child.is_dir():
            for subject_child in career_child.iterdir():
                if subject_child.is_dir() and (subject_child / MANIFEST_FILENAME).is_file():
                    save_subject_manifest(
                        subject_child,
                        trigger="institucion",
                        detail=detail,
                        metadata_updates=metadata_updates,
                    )
                    updated.append(subject_child)
    return updated
