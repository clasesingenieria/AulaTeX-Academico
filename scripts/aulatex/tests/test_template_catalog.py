from pathlib import Path
import json
import pytest

from scripts.aulatex.workspace import AulaTeXWorkspace
from scripts.aulatex.template_catalog import build_template_catalog, render_catalog_markdown, select_template, export_catalog, SELECTION_FILENAME


def subject(root: Path, relative: str) -> Path:
    path = root / relative
    path.mkdir(parents=True)
    (path / "reporte-materia.tex").write_text("Contenido ficticio", encoding="utf-8")
    return path


def test_discovery_includes_tecnm_and_excludes_support_and_empty_nodes(tmp_path):
    subject(tmp_path, "tecnmNL/ingeniero-industrial/inferencial-i")
    subject(tmp_path, "UAS/licenciatura-en-contaduria-uas/derecho-mercantil")
    subject(tmp_path, "UAS/assets")
    materials = tmp_path / "UAS" / "GRUPO 101"
    materials.mkdir()
    (materials / "lectura.pdf").touch()
    (tmp_path / "UAS/licenciatura-en-contaduria-uas/duplicado-vacio").mkdir()
    workspace = AulaTeXWorkspace(tmp_path)
    scopes = workspace.scan_editorial_scopes()
    paths = {scope.relative_path for scope in scopes}
    assert "tecnmNL/ingeniero-industrial/inferencial-i" in paths
    assert "UAS/assets" not in paths
    assert "UAS/GRUPO 101" not in paths
    assert not any(path.endswith("duplicado-vacio") for path in paths)


def test_inventory_and_editorial_index_agree_on_levels(tmp_path):
    subject(tmp_path, "UAS/derecho-mercantil")
    subject(tmp_path, "UAS/licenciatura-en-contaduria-uas/contabilidad")
    workspace = AulaTeXWorkspace(tmp_path)
    expected = {scope.relative_path: scope.level for scope in workspace.scan_editorial_scopes()
                if scope.level in ("institucion", "carrera", "materia")}
    actual = {}

    def visit(node):
        actual[node.relative_path] = node.level
        for child in node.children:
            visit(child)

    for node in workspace.scan_template_inventory():
        visit(node)
    assert actual == expected
    assert workspace.scan_tree()["UAS"][""] == ["derecho-mercantil"]


def test_explicit_empty_subject_marker_is_respected(tmp_path):
    path = tmp_path / "ITESCA/maestria-prueba/materia-nueva"
    path.mkdir(parents=True)
    (path / ".aulatex-node.json").write_text('{"level":"materia"}', encoding="utf-8")
    assert any(scope.relative_path.endswith("materia-nueva") for scope in AulaTeXWorkspace(tmp_path).scan_editorial_scopes())


def test_catalog_requires_explicit_selection_and_preserves_documents(tmp_path):
    path = subject(tmp_path, "UCNL/licenciatura-prueba/materia")
    (path / "reporte-materia-plantilla-2026-3.tex").write_text("\\input{missing-template}", encoding="utf-8")
    (path / "reporte-materia-Actividad-1.tex").write_text("Trabajo terminado", encoding="utf-8")
    workspace = AulaTeXWorkspace(tmp_path)
    before = {file: file.read_bytes() for file in path.iterdir()}
    catalog = build_template_catalog(workspace)
    node = catalog["subjects"][0]
    assert node["selection_status"] == "pending_review"
    assert len(node["candidates"]) == 2
    assert all("Actividad-1" not in item["path"] for item in node["candidates"])
    assert before == {file: file.read_bytes() for file in path.iterdir()}
    assert any(dependency["status"] == "unresolved" for artifact in catalog["artifacts"].values() for dependency in artifact["dependencies"])
    assert "UCNL" in render_catalog_markdown(catalog)


def test_catalog_validates_declared_selection_and_manifest_paths(tmp_path):
    path = subject(tmp_path, "UAS/licenciatura-prueba/materia")
    relative = path.relative_to(tmp_path).as_posix()
    (tmp_path / SELECTION_FILENAME).write_text(json.dumps({"schema_version": "1.0", "subjects": {
        relative: {"report": relative + "/reporte-materia.tex", "presentation": "../../private.tex"}}}), encoding="utf-8")
    (path / "estructura-aulatex.json").write_text(json.dumps({"files": ["ausente.tex", "../../../../outside.tex"]}), encoding="utf-8")
    catalog = build_template_catalog(AulaTeXWorkspace(tmp_path))
    assert catalog["subjects"][0]["selected"] == {"report": relative + "/reporte-materia.tex"}
    codes = {item["code"] for item in catalog["issues"]}
    assert {"missing_declared_path", "unsafe_manifest_path", "invalid_template_selection"} <= codes


def test_temporary_evidence_is_compared_without_deleting(tmp_path):
    path = subject(tmp_path, "ITESCA/maestria-prueba/materia")
    temporary = tmp_path / ".tmp-prueba"
    temporary.mkdir()
    (temporary / "receipt.json").write_bytes(b"fictitious receipt")
    (temporary / "other-receipt.txt").write_bytes(b"keep this")
    (path / "receipt.json").write_bytes(b"fictitious receipt")
    catalog = build_template_catalog(AulaTeXWorkspace(tmp_path))
    result = next(item for item in catalog["temporaries"] if item["path"] == temporary.name)
    evidence = {Path(item["path"]).name: item for item in result["evidence"]}
    assert evidence["receipt.json"]["status"] == "copy_verified"
    assert evidence["other-receipt.txt"]["status"] == "preserve_pending_review"
    assert result["automatic_deletion"] is False
    assert result["tracked_files"] is None
    assert len(list(temporary.iterdir())) == 2


def test_duplicate_dependency_names_remain_ambiguous(tmp_path):
    path = subject(tmp_path, "UANL/ingeniero-prueba/materia")
    (path / "reporte-materia.tex").write_text("\\input{template}", encoding="utf-8")
    for name in ("one", "two"):
        base = tmp_path / "base" / name
        base.mkdir(parents=True)
        (base / "template.tex").write_text("Shared template", encoding="utf-8")
    catalog = build_template_catalog(AulaTeXWorkspace(tmp_path))
    artifact = next(iter(catalog["artifacts"].values()))
    assert artifact["dependencies"][0]["status"] == "ambiguous"
    assert artifact["compilation"] == "not_run"


def test_selection_is_atomic_and_does_not_modify_template(tmp_path):
    path = subject(tmp_path, "UCNL/licenciatura-prueba/materia")
    workspace = AulaTeXWorkspace(tmp_path)
    relative = path.relative_to(tmp_path).as_posix()
    report = path / "reporte-materia.tex"
    before = report.read_bytes()
    select_template(workspace, relative, relative + "/reporte-materia.tex", "report")
    catalog = build_template_catalog(workspace)
    assert catalog["subjects"][0]["selected"]["report"].endswith("reporte-materia.tex")
    assert report.read_bytes() == before
    assert not list(tmp_path.glob(".aulatex-catalog-*"))
    paths = export_catalog(workspace, catalog)
    assert json.loads(paths[0].read_text(encoding="utf-8"))["schema_version"] == "1.0"
    assert paths[1].is_file()


def test_selection_rejects_wrong_role_and_preserves_invalid_registry(tmp_path):
    path = subject(tmp_path, "UAS/licenciatura-prueba/materia")
    workspace = AulaTeXWorkspace(tmp_path)
    relative = path.relative_to(tmp_path).as_posix()
    with pytest.raises(ValueError):
        select_template(workspace, relative, relative + "/reporte-materia.tex", "presentation")
    registry = tmp_path / SELECTION_FILENAME
    registry.write_text('{"schema_version":"unsupported"}', encoding="utf-8")
    before = registry.read_bytes()
    with pytest.raises(ValueError):
        select_template(workspace, relative, relative + "/reporte-materia.tex", "report")
    assert registry.read_bytes() == before


def test_catalog_cli_export_has_no_llm_calls(tmp_path, capsys):
    from scripts.aulatex.cli import main

    subject(tmp_path, "tecnmNL/ingeniero-industrial/materia")
    main(["catalogo-plantillas", "--root", str(tmp_path), "--export"])
    result = json.loads(capsys.readouterr().out)
    assert result["subjects"] == 1
    assert result["candidates"] == 1