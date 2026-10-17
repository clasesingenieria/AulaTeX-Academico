from __future__ import annotations

import json
from pathlib import Path
import pytest

from aulaTEX.aulatex.subject_manifest import (
    find_subject_root,
    load_subject_manifest,
    save_subject_manifest,
    propagate_career_manifests,
    propagate_institution_manifests,
    MANIFEST_FILENAME,
    SCHEMA_VERSION,
    VALID_TRIGGERS,
)


@pytest.fixture
def subject_dir(tmp_path: Path) -> Path:
    # Simular UANL/ingeniero-agronomo/algebra-lineal
    subj = tmp_path / "UANL" / "ingeniero-agronomo" / "algebra-lineal"
    subj.mkdir(parents=True)
    (subj / "reporte-algebra-lineal.tex").write_text("\\documentclass{article}", encoding="utf-8")
    (subj / "algebra-lineal.bib").write_text("@misc{ref, title={Title}}", encoding="utf-8")
    (subj / "entregas-algebra-lineal").mkdir()
    (subj / "planeaciones-algebra-lineal").mkdir()
    return subj


def test_find_subject_root_from_child_file_and_folder(subject_dir: Path):
    child_file = subject_dir / "reporte-algebra-lineal.tex"
    subfolder_file = subject_dir / "planeaciones-algebra-lineal" / "actividad-1.md"
    subfolder_file.parent.mkdir(parents=True, exist_ok=True)
    subfolder_file.write_text("Consigna", encoding="utf-8")

    assert find_subject_root(child_file) == subject_dir
    assert find_subject_root(subfolder_file) == subject_dir
    assert find_subject_root(subject_dir) == subject_dir


def test_save_subject_manifest_trigger_materia(subject_dir: Path):
    manifest = save_subject_manifest(
        subject_dir,
        trigger="materia",
        detail="compilacion_ok",
        compilation={"ok": True, "target": "reporte.tex"},
    )
    manifest_file = subject_dir / MANIFEST_FILENAME
    assert manifest_file.is_file()
    assert manifest["schema_version"] == SCHEMA_VERSION
    assert manifest["slug"] == "algebra-lineal"
    assert manifest["institution"] == "UANL"
    assert manifest["career"] == "ingeniero-agronomo"
    assert manifest["audit"]["trigger"] == "materia"
    assert manifest["audit"]["trigger_detail"] == "compilacion_ok"
    assert manifest["compilation"]["ok"] is True
    assert "reporte-algebra-lineal.tex" in manifest["files"]
    assert "entregas-algebra-lineal" in manifest["folders"]


def test_save_subject_manifest_trigger_validation(subject_dir: Path):
    for valid_trigger in VALID_TRIGGERS:
        manifest = save_subject_manifest(subject_dir, trigger=valid_trigger, detail=f"test_{valid_trigger}")
        assert manifest["audit"]["trigger"] == valid_trigger

    with pytest.raises(ValueError, match="no es válido"):
        save_subject_manifest(subject_dir, trigger="trigger_invalido")


def test_save_subject_manifest_preserves_existing_data(subject_dir: Path):
    save_subject_manifest(
        subject_dir,
        trigger="sistema",
        detail="extraccion",
        metadata_updates={"docente": "Dr. Miranda", "matricula": "1977875"},
    )
    manifest_1 = load_subject_manifest(subject_dir)
    assert manifest_1["docente"] == "Dr. Miranda"
    assert manifest_1["matricula"] == "1977875"

    # Segunda actualización con trigger 'materia'
    save_subject_manifest(
        subject_dir,
        trigger="materia",
        detail="compilacion",
        compilation={"ok": True},
    )
    manifest_2 = load_subject_manifest(subject_dir)
    assert manifest_2["docente"] == "Dr. Miranda"  # Conservado
    assert manifest_2["matricula"] == "1977875"     # Conservado
    assert manifest_2["compilation"]["ok"] is True
    assert manifest_2["audit"]["trigger"] == "materia"


def test_propagate_career_manifests_only_updates_existing(tmp_path: Path):
    career_dir = tmp_path / "UANL" / "ingeniero-agronomo"
    active_subj = career_dir / "algebra-lineal"
    inactive_subj = career_dir / "quimica-organica"
    active_subj.mkdir(parents=True)
    inactive_subj.mkdir(parents=True)

    # Solo active_subj tiene manifest
    save_subject_manifest(active_subj, trigger="materia", detail="inicio")
    assert (active_subj / MANIFEST_FILENAME).is_file()
    assert not (inactive_subj / MANIFEST_FILENAME).exists()

    # Propagar cambios de carrera
    updated = propagate_career_manifests(
        career_dir,
        detail="cambio_plan_estudios",
        metadata_updates={"periodo": "2026-B"},
    )
    assert active_subj in updated
    assert inactive_subj not in updated

    # El sujeto inactivo no fue inflado con archivos
    assert not (inactive_subj / MANIFEST_FILENAME).exists()

    # El sujeto activo se actualizó con trigger 'carrera'
    active_manifest = load_subject_manifest(active_subj)
    assert active_manifest["audit"]["trigger"] == "carrera"
    assert active_manifest["periodo"] == "2026-B"

