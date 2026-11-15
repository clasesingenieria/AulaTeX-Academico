from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from aulatex.subir_drive import (
    DriveUploadRequest,
    GoogleDriveInteractiveUploader,
    resolve_drive_profile_dir,
    validate_drive_folder_url,
)
from aulatex.workspace import AulaTeXWorkspace


def test_validate_drive_folder_url() -> None:
    url = "https://drive.google.com/drive/folders/11t7MGMNuMRCMJnfmcp_XAnmjFHO5qkWH?usp=sharing"
    assert validate_drive_folder_url(url) == url

    with pytest.raises(ValueError):
        validate_drive_folder_url("http://drive.google.com/drive/folders/abc")
    with pytest.raises(ValueError):
        validate_drive_folder_url("https://example.com/drive/folders/abc")


def test_profile_dir_is_isolated_outside_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    profile = resolve_drive_profile_dir("Mi Perfil UAS")
    assert profile.is_dir()
    assert str(tmp_path / "local") in str(profile)


def test_fail_closed_without_user_validation(tmp_path: Path) -> None:
    ws = AulaTeXWorkspace(repo_root=tmp_path)
    uploader = GoogleDriveInteractiveUploader(ws)
    sample = tmp_path / "EXCEL_CONTA.xlsx"
    sample.write_bytes(b"demo-excel")

    res = uploader.upload(
        DriveUploadRequest(
            folder_url="https://drive.google.com/drive/folders/11t7MGMNuMRCMJnfmcp_XAnmjFHO5qkWH",
            artifact_path=sample,
            user_validated=False,
            dry_run=True,
            output_dir=str(tmp_path / "out"),
        )
    )
    assert not res.ok
    assert res.status == "blocked_missing_user_validation"


def test_dry_run_validates_hash_and_writes_receipt(tmp_path: Path) -> None:
    ws = AulaTeXWorkspace(repo_root=tmp_path)
    uploader = GoogleDriveInteractiveUploader(ws)
    sample = tmp_path / "EXCEL_CONTA.xlsx"
    payload = b"xlsx-bytes-verified"
    sample.write_bytes(payload)
    expected_sha = hashlib.sha256(payload).hexdigest()

    res = uploader.upload(
        DriveUploadRequest(
            folder_url="https://drive.google.com/drive/folders/11t7MGMNuMRCMJnfmcp_XAnmjFHO5qkWH",
            artifact_path=sample,
            user_validated=True,
            dry_run=True,
            expected_sha256=expected_sha,
            profile_dir=str(tmp_path / "profile"),
            output_dir=str(tmp_path / "out"),
        )
    )
    assert res.ok
    assert res.status == "dry_run_validated"
    assert res.sha256 == expected_sha
    assert res.receipt_path is not None and res.receipt_path.is_file()
