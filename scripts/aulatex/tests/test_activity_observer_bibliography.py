from pathlib import Path

import pytest

from scripts.aulatex.activity_observer import ActivityObserver


@pytest.mark.parametrize(
    ("folder", "canonical"),
    [
        ("fundamentos-de-gestion-administrativa-mga", "fundamentos-de-gestion-administrativa"),
        ("filosofia-del-derecho-lde", "filosofia-del-derecho"),
        ("materia", "materia"),
    ],
)
def test_canonical_subject_bib_precedes_auxiliary(
    tmp_path: Path, folder: str, canonical: str
) -> None:
    root = tmp_path / folder
    root.mkdir()
    expected = root / f"{canonical}.bib"
    expected.write_text("@book{primary, title={Primary}}", encoding="utf-8")
    (root / "aaa-auxiliar.bib").write_text("", encoding="utf-8")
    observer = object.__new__(ActivityObserver)
    assert observer._find_canonical_bib(root) == expected


def test_exact_folder_name_keeps_priority(tmp_path: Path) -> None:
    root = tmp_path / "materia-mga"
    root.mkdir()
    exact = root / "materia-mga.bib"
    exact.touch()
    (root / "materia.bib").touch()
    observer = object.__new__(ActivityObserver)
    assert observer._find_canonical_bib(root) == exact


def test_fallback_excludes_clean_bibliography(tmp_path: Path) -> None:
    (tmp_path / "aaa-clean.bib").touch()
    expected = tmp_path / "bibliografia.bib"
    expected.touch()
    observer = object.__new__(ActivityObserver)
    assert observer._find_canonical_bib(tmp_path) == expected