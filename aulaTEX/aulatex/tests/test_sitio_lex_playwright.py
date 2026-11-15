from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from aulatex.agente_sitio_lex import (
    AgenteSitioLex,
    DEFAULT_EDITOR_URL,
    DEFAULT_SITE_URL,
    DisenoSitioLexAuditResult,
    GoogleSitesInteractiveRequest,
    _is_authenticated_sites_editor,
    validate_google_sites_urls,
)
from aulatex.workspace import AulaTeXWorkspace


def test_validate_google_sites_urls() -> None:
    ed, pub = validate_google_sites_urls(DEFAULT_EDITOR_URL, DEFAULT_SITE_URL)
    assert ed == DEFAULT_EDITOR_URL
    assert pub == DEFAULT_SITE_URL

    with pytest.raises(ValueError):
        validate_google_sites_urls("http://sites.google.com/d/123/edit", DEFAULT_SITE_URL)
    with pytest.raises(ValueError):
        validate_google_sites_urls("https://example.com/d/123/edit", DEFAULT_SITE_URL)
    with pytest.raises(ValueError):
        validate_google_sites_urls(DEFAULT_EDITOR_URL, "https://sites.google.com/d/123/edit")


def test_fail_closed_without_user_validation(tmp_path: Path) -> None:
    agent = AgenteSitioLex(AulaTeXWorkspace(repo_root=tmp_path))
    res = agent.run_interactive_session(
        GoogleSitesInteractiveRequest(
            user_validated=False,
            dry_run=True,
            output_dir=str(tmp_path / "out"),
        )
    )
    assert not res.ok
    assert res.status == "blocked_missing_user_validation"
    assert res.manifest_path is not None and res.manifest_path.is_file()


def test_dry_run_writes_receipt_with_shared_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    agent = AgenteSitioLex(AulaTeXWorkspace(repo_root=tmp_path))
    monkeypatch.setattr(
        agent,
        "audit_published_site",
        lambda site_url=None: DisenoSitioLexAuditResult(
            site_url=site_url or DEFAULT_SITE_URL,
            http_status=200,
            is_live=True,
            has_forbidden_iframes=False,
            forbidden_iframe_sources=(),
            matched_sections=("header", "core_services", "footer_cta"),
            missing_sections=(),
            compliance_score=100.0,
            raw_html_snippet="<html>Lex Contable</html>",
            timestamp="2026-11-15T00:00:00+00:00",
        ),
    )

    res = agent.run_interactive_session(
        GoogleSitesInteractiveRequest(
            user_validated=True,
            dry_run=True,
            profile_name="google-drive",
            ensure_pages=("Inicio", "Servicios", "Quiénes Somos", "Ubicación", "Contacto"),
            output_dir=str(tmp_path / "out"),
        )
    )
    assert res.ok
    assert res.status == "dry_run_validated"
    assert res.compliance_score == 100.0
    assert not res.has_forbidden_iframes
    assert res.receipt_path is not None and res.receipt_path.is_file()
    assert res.summary_md_path is not None and res.summary_md_path.is_file()
    assert str(tmp_path / "local") in str(res.evidence["profile_dir"])


def test_is_authenticated_sites_editor_and_page_inspection() -> None:
    class _FakeLocator:
        def __init__(self, count_val: int = 0, texts: list[str] | None = None) -> None:
            self._count = count_val
            self._texts = texts or []
            self.first = self

        def count(self) -> int:
            return self._count

        def click(self) -> None:
            return None

        def all_inner_texts(self) -> list[str]:
            return self._texts

    class _FakePage:
        def __init__(self, url: str) -> None:
            self.url = url

        def locator(self, selector: str) -> _FakeLocator:
            if "Páginas" in selector:
                return _FakeLocator(count_val=1)
            if "treeitem" in selector:
                return _FakeLocator(texts=["Inicio\nPágina principal", "Servicios", "Contacto"])
            return _FakeLocator(count_val=0)

        def wait_for_timeout(self, ms: int) -> None:
            return None

    unauth_page = _FakePage("https://accounts.google.com/v3/signin/identifier")
    assert not _is_authenticated_sites_editor(unauth_page)

    auth_page = _FakePage(DEFAULT_EDITOR_URL)
    assert _is_authenticated_sites_editor(auth_page)

    existing, created = AgenteSitioLex._inspect_and_sync_editor_pages(
        auth_page,
        ("Inicio", "Servicios"),
    )
    assert existing == ["Inicio", "Servicios", "Contacto"]
    assert created == []
