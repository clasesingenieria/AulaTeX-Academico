"""Automatización Playwright con apertura de ventana visible para autenticación en Google Drive.

Permite al usuario autenticarse directamente de forma interactiva en una ventana
real de navegador (perfil persistente fuera del repositorio) sin capturar ni
almacenar contraseñas, para luego automatizar la subida verificada de archivos a
carpetas compartidas de Google Drive (p. ej. EXCEL_CONTA en UAS Semana 4).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any
from urllib.parse import urlsplit

from .navegacion_plataforma import assert_no_credential_leak
from .workspace import AulaTeXWorkspace

DRIVE_HOST = "drive.google.com"
ALLOWED_AUTH_HOSTS = frozenset({"drive.google.com", "accounts.google.com"})

_NEW_BUTTON_SELECTORS = (
    'button[guidedhelpid="new_menu_button"]:visible',
    'button[aria-label="Nuevo"]:visible',
    'button[aria-label="New"]:visible',
    'button:has-text("Nuevo"):visible',
    'button:has-text("New"):visible',
)

_FILE_UPLOAD_ITEM_SELECTORS = (
    '[role="menuitem"]:has-text("Subir archivo"):visible',
    '[role="menuitem"]:has-text("Cargar archivo"):visible',
    '[role="menuitem"]:has-text("File upload"):visible',
    'div[role="menuitem"]:has-text("Subir"):visible',
)


@dataclass(frozen=True)
class DriveUploadRequest:
    """Solicitud de carga autenticada a una carpeta de Google Drive."""

    folder_url: str
    artifact_path: str | Path
    user_validated: bool = False
    dry_run: bool = True
    profile_name: str = "google-drive"
    profile_dir: str = ""
    channel: str = "chrome"  # "chrome", "msedge" o "chromium"
    auth_timeout_seconds: int = 300
    upload_timeout_seconds: int = 120
    expected_sha256: str | None = None
    replace_existing: bool = True
    output_dir: str = ""


@dataclass(frozen=True)
class DriveUploadResult:
    """Resultado estructurado y auditado de una subida a Google Drive."""

    ok: bool
    status: str
    run_id: str
    run_dir: Path
    folder_url: str
    artifact_path: str
    sha256: str
    receipt_path: Path | None = None
    manifest_path: Path | None = None
    summary_md_path: Path | None = None
    screenshot_path: Path | None = None
    blockers: tuple[dict[str, Any], ...] = ()
    evidence: dict[str, Any] = field(default_factory=dict)


def validate_drive_folder_url(folder_url: str) -> str:
    """Valida que la URL objetivo pertenezca estrictamente a Google Drive por HTTPS."""
    clean = (folder_url or "").strip()
    parts = urlsplit(clean)
    if parts.scheme.lower() != "https" or (parts.hostname or "").lower() != DRIVE_HOST:
        raise ValueError(
            f"URL inválida para Google Drive (se requiere https://{DRIVE_HOST}/...): {clean!r}"
        )
    if "/drive/" not in parts.path and "/folders/" not in parts.path:
        raise ValueError(f"La URL no apunta a una carpeta válida de Google Drive: {clean!r}")
    return clean


def resolve_drive_profile_dir(profile_name: str = "google-drive", explicit_dir: str | Path | None = None) -> Path:
    """Resuelve el directorio de perfil persistente de Playwright fuera del repositorio Git."""
    if explicit_dir and str(explicit_dir).strip():
        target = Path(explicit_dir).expanduser().resolve()
    else:
        base_root = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / ".local" / "share"))
        safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "-", (profile_name or "google-drive").strip()).strip("-") or "google-drive"
        target = (base_root / "AulaTeX" / "playwright-profiles" / safe_name).resolve()
    target.mkdir(parents=True, exist_ok=True)
    return target


def _is_authenticated_drive_folder(page: Any) -> bool:
    """Determina si la pestaña ya muestra la carpeta autenticada lista para subir archivos."""
    host = (urlsplit(page.url).hostname or "").lower()
    if host != DRIVE_HOST:
        return False

    try:
        body_text = page.locator("body").inner_text(timeout=2000)
    except Exception:
        body_text = ""

    unauth_markers = (
        "Accede para agregar archivos",
        "Inicia sesión para agregar archivos",
        "Sign in to add files",
    )
    if any(m.lower() in body_text.lower() for m in unauth_markers):
        return False

    for sel in _NEW_BUTTON_SELECTORS:
        try:
            if page.locator(sel).count() > 0:
                return True
        except Exception:
            continue
    return False


def launch_persistent_headed_context(playwright: Any, user_data_dir: Path, preferred_channel: str) -> tuple[Any, str]:
    """Lanza un contexto persistente con ventana visible usando el canal disponible."""
    candidates: list[str | None] = []
    pref = (preferred_channel or "chrome").strip().lower()
    if pref and pref != "chromium":
        candidates.append(pref)
    for fallback in ("chrome", "msedge", None):
        if fallback not in candidates:
            candidates.append(fallback)

    last_exc: Exception | None = None
    for ch in candidates:
        kwargs: dict[str, Any] = {
            "user_data_dir": str(user_data_dir),
            "headless": False,
            "viewport": {"width": 1360, "height": 900},
            "accept_downloads": True,
            "ignore_default_args": ["--enable-automation"],
            "args": ["--disable-blink-features=AutomationControlled"],
        }
        if ch is not None:
            kwargs["channel"] = ch
        try:
            ctx = playwright.chromium.launch_persistent_context(**kwargs)
            return ctx, (ch or "chromium")
        except Exception as exc:
            last_exc = exc
            continue
    raise RuntimeError(f"No fue posible abrir la ventana de navegador Playwright: {last_exc}")


_launch_persistent_headed_context = launch_persistent_headed_context


class GoogleDriveInteractiveUploader:
    """Orquestador de subida a Google Drive con apertura de ventana para autenticación humana."""

    agent_id: str = "subir-drive"

    def __init__(self, workspace: AulaTeXWorkspace | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.runs_root = self.workspace.feedback_root / "subir-drive" / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)

    def _write_blocked_result(
        self,
        *,
        run_id: str,
        run_dir: Path,
        status: str,
        folder_url: str,
        artifact_path: Path,
        sha256: str,
        blocker: dict[str, Any],
    ) -> DriveUploadResult:
        manifest = {
            "schema_version": "1.0.0",
            "run_id": run_id,
            "agent_id": self.agent_id,
            "status": status,
            "folder_url": folder_url,
            "artifact_path": str(artifact_path),
            "sha256": sha256,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "blockers": [blocker],
        }
        assert_no_credential_leak(manifest)
        m_path = run_dir / "manifest.json"
        m_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        summary_md = (
            f"# Subida a Google Drive Bloqueada (`{status}`)\n\n"
            f"- **Carpeta:** `{folder_url}`\n"
            f"- **Archivo:** `{artifact_path.name}`\n"
            f"- **Motivo:** {blocker['detail']}\n"
        )
        assert_no_credential_leak(summary_md)
        s_path = run_dir / "resumen-drive.md"
        s_path.write_text(summary_md, encoding="utf-8")

        return DriveUploadResult(
            ok=False,
            status=status,
            run_id=run_id,
            run_dir=run_dir,
            folder_url=folder_url,
            artifact_path=str(artifact_path),
            sha256=sha256,
            manifest_path=m_path,
            summary_md_path=s_path,
            blockers=(blocker,),
        )

    def upload(self, request: DriveUploadRequest) -> DriveUploadResult:
        """Valida compuertas y ejecuta la subida con ventana interactiva para login."""
        run_id = f"{self.workspace.timestamp()}-subir-drive"
        run_dir = (
            self.workspace.resolve_target(request.output_dir)
            if request.output_dir.strip()
            else self.runs_root / run_id
        )
        run_dir.mkdir(parents=True, exist_ok=True)

        artifact_file = Path(request.artifact_path)
        if not artifact_file.is_absolute():
            artifact_file = (self.workspace.repo_root / artifact_file).resolve()

        # Compuerta 1: validación explícita del usuario (fail-closed)
        if not request.user_validated:
            return self._write_blocked_result(
                run_id=run_id,
                run_dir=run_dir,
                status="blocked_missing_user_validation",
                folder_url=request.folder_url,
                artifact_path=artifact_file,
                sha256="",
                blocker={
                    "code": "missing_user_validation",
                    "detail": (
                        "Subida a Google Drive bloqueada por seguridad: se requiere "
                        f"autorización explícita (`user_validated=True`) para subir {artifact_file.name}."
                    ),
                    "blocking": True,
                },
            )

        # Compuerta 2: URL válida de Google Drive + existencia y hash del artefacto
        try:
            clean_folder_url = validate_drive_folder_url(request.folder_url)
        except ValueError as exc:
            return self._write_blocked_result(
                run_id=run_id,
                run_dir=run_dir,
                status="blocked_invalid_folder_url",
                folder_url=request.folder_url,
                artifact_path=artifact_file,
                sha256="",
                blocker={"code": "invalid_folder_url", "detail": str(exc), "blocking": True},
            )

        if not artifact_file.is_file():
            return self._write_blocked_result(
                run_id=run_id,
                run_dir=run_dir,
                status="blocked_artifact_not_found",
                folder_url=clean_folder_url,
                artifact_path=artifact_file,
                sha256="",
                blocker={
                    "code": "artifact_not_found",
                    "detail": f"No se encontró el archivo a subir: {artifact_file}",
                    "blocking": True,
                },
            )

        content_bytes = artifact_file.read_bytes()
        actual_sha256 = hashlib.sha256(content_bytes).hexdigest()
        if request.expected_sha256 and actual_sha256.lower() != request.expected_sha256.lower():
            return self._write_blocked_result(
                run_id=run_id,
                run_dir=run_dir,
                status="blocked_hash_mismatch",
                folder_url=clean_folder_url,
                artifact_path=artifact_file,
                sha256=actual_sha256,
                blocker={
                    "code": "hash_mismatch",
                    "detail": f"SHA-256 distinto al esperado ({request.expected_sha256} != {actual_sha256}).",
                    "blocking": True,
                },
            )

        profile_dir = resolve_drive_profile_dir(request.profile_name, request.profile_dir or None)

        # Compuerta 3: Simulación segura dry-run
        if request.dry_run:
            receipt = {
                "receipt_type": "google_drive_dry_run_receipt",
                "run_id": run_id,
                "agent_id": self.agent_id,
                "folder_url": clean_folder_url,
                "artifact_name": artifact_file.name,
                "artifact_path": str(artifact_file),
                "size_bytes": len(content_bytes),
                "sha256": actual_sha256,
                "profile_dir": str(profile_dir),
                "channel": request.channel,
                "dry_run": True,
                "user_validated": True,
                "status": "dry_run_validated_ready_for_drive_upload",
                "validation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            }
            assert_no_credential_leak(receipt)
            receipt_path = run_dir / "comprobante_dry_run.json"
            receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

            manifest = {
                "schema_version": "1.0.0",
                "run_id": run_id,
                "agent_id": self.agent_id,
                "status": "dry_run_validated",
                "folder_url": clean_folder_url,
                "artifact_path": str(artifact_file),
                "sha256": actual_sha256,
                "receipt_path": str(receipt_path),
            }
            m_path = run_dir / "manifest.json"
            m_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

            summary_md = (
                f"# Verificación de Subida a Google Drive (Dry-Run)\n\n"
                f"- **Carpeta:** `{clean_folder_url}`\n"
                f"- **Archivo:** `{artifact_file.name}` ({len(content_bytes):,} bytes)\n"
                f"- **SHA-256:** `{actual_sha256}`\n"
                f"- **Perfil persistente:** `{profile_dir}`\n"
            )
            s_path = run_dir / "resumen-drive.md"
            s_path.write_text(summary_md, encoding="utf-8")
            return DriveUploadResult(
                ok=True,
                status="dry_run_validated",
                run_id=run_id,
                run_dir=run_dir,
                folder_url=clean_folder_url,
                artifact_path=str(artifact_file),
                sha256=actual_sha256,
                receipt_path=receipt_path,
                manifest_path=m_path,
                summary_md_path=s_path,
                evidence={"dry_run": True, "profile_dir": str(profile_dir)},
            )

        # Envío real con ventana visible de navegador para autenticación interactiva
        from playwright.sync_api import sync_playwright

        evidence_dir = run_dir / "evidencia_plataforma"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = evidence_dir / "drive-upload-confirmado.png"

        used_channel = request.channel
        authenticated_during_run = False
        upload_confirmed = False

        with sync_playwright() as p:
            context, used_channel = _launch_persistent_headed_context(p, profile_dir, request.channel)
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.set_default_timeout(30000)
                page.goto(clean_folder_url, wait_until="domcontentloaded")
                page.wait_for_timeout(1500)

                if not _is_authenticated_drive_folder(page):
                    print(
                        f"\n[subir-drive] Ventana abierta ({used_channel}) para autenticación en Google Drive.\n"
                        f"[subir-drive] Inicia sesión en la ventana abierta; esperando hasta "
                        f"{request.auth_timeout_seconds}s a que cargue la carpeta con permisos de edición...",
                        flush=True,
                    )
                    deadline = time.monotonic() + max(10, int(request.auth_timeout_seconds))
                    while time.monotonic() < deadline:
                        if _is_authenticated_drive_folder(page):
                            authenticated_during_run = True
                            break
                        # Si el usuario quedó en accounts.google.com y ya regresó a drive, o si sigue en carpeta pública sin botón
                        host = (urlsplit(page.url).hostname or "").lower()
                        if host == DRIVE_HOST:
                            # Intentar clic en "Acceder" sólo si aparece botón directo de login en carpeta pública
                            login_link = page.locator('a:has-text("Acceder"):visible, a:has-text("Iniciar sesión"):visible, a:has-text("Sign in"):visible').first
                            if login_link.count():
                                try:
                                    login_link.click()
                                except Exception:
                                    pass
                        page.wait_for_timeout(1500)

                if not _is_authenticated_drive_folder(page):
                    try:
                        page.screenshot(path=str(screenshot_path), full_page=True)
                    except Exception:
                        pass
                    return self._write_blocked_result(
                        run_id=run_id,
                        run_dir=run_dir,
                        status="blocked_auth_timeout",
                        folder_url=clean_folder_url,
                        artifact_path=artifact_file,
                        sha256=actual_sha256,
                        blocker={
                            "code": "auth_timeout",
                            "detail": (
                                f"No se completó la autenticación en Google Drive dentro de "
                                f"{request.auth_timeout_seconds}s (perfil conservado en {profile_dir})."
                            ),
                            "blocking": True,
                        },
                    )

                # Autenticado dentro de la carpeta: abrir "+ Nuevo" -> "Subir archivo"
                new_clicked = False
                for sel in _NEW_BUTTON_SELECTORS:
                    btn = page.locator(sel).first
                    if btn.count():
                        btn.click()
                        new_clicked = True
                        break
                if not new_clicked:
                    raise RuntimeError("No se localizó el botón '+ Nuevo' en la interfaz de Google Drive.")

                page.wait_for_timeout(600)
                upload_item = None
                for sel in _FILE_UPLOAD_ITEM_SELECTORS:
                    loc = page.locator(sel).first
                    if loc.count():
                        upload_item = loc
                        break
                if upload_item is None:
                    raise RuntimeError("No se encontró la opción 'Subir archivo' en el menú '+ Nuevo'.")

                with page.expect_file_chooser(timeout=15000) as fc_info:
                    upload_item.click()
                fc_info.value.set_files(str(artifact_file))

                # Esperar confirmación de carga y resolver diálogo de reemplazo si ya existe el archivo
                up_deadline = time.monotonic() + max(20, int(request.upload_timeout_seconds))
                done_markers = (
                    "1 upload complete",
                    "Se subió 1 elemento",
                    "Se completó 1 subida",
                    "Subida completa",
                )
                while time.monotonic() < up_deadline:
                    if request.replace_existing:
                        rep_radio = page.locator(
                            'label:has-text("Reemplazar archivo existente"):visible, '
                            'label:has-text("Replace existing file"):visible'
                        ).first
                        if rep_radio.count():
                            rep_radio.click()
                        up_confirm = page.locator(
                            'div[role="dialog"] button:has-text("Subir"):visible, '
                            'div[role="dialog"] button:has-text("Upload"):visible, '
                            'div[role="dialog"] button:has-text("Reemplazar"):visible, '
                            'div[role="dialog"] button:has-text("Replace"):visible'
                        ).first
                        if up_confirm.count():
                            up_confirm.click()
                            page.wait_for_timeout(1200)

                    try:
                        full_text = page.locator("body").inner_text(timeout=2000)
                    except Exception:
                        full_text = ""

                    if any(m.lower() in full_text.lower() for m in done_markers):
                        upload_confirmed = True
                        break
                    # Comprobar también si el archivo ya aparece visible en la lista principal y no hay indicador activo de subida
                    if (
                        artifact_file.name in full_text
                        and "Subiendo" not in full_text
                        and "Uploading" not in full_text
                        and time.monotonic() > (up_deadline - request.upload_timeout_seconds + 4)
                    ):
                        upload_confirmed = True
                        break
                    page.wait_for_timeout(1000)

                page.wait_for_timeout(1000)
                page.screenshot(path=str(screenshot_path), full_page=True)
            finally:
                context.close()

        evidence = {
            "dispatch_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "folder_url": clean_folder_url,
            "filename_uploaded": artifact_file.name,
            "sha256_uploaded": actual_sha256,
            "channel_used": used_channel,
            "profile_dir": str(profile_dir),
            "authenticated_during_run": authenticated_during_run,
            "upload_confirmed": upload_confirmed,
            "screenshot_path": str(screenshot_path),
        }
        assert_no_credential_leak(evidence)

        status = "uploaded_to_drive" if upload_confirmed else "upload_unconfirmed"
        receipt_real = {
            "receipt_type": "google_drive_official_upload_receipt",
            "run_id": run_id,
            "agent_id": self.agent_id,
            "folder_url": clean_folder_url,
            "artifact_name": artifact_file.name,
            "sha256": actual_sha256,
            "user_validated": True,
            "status": status,
            "evidence": evidence,
        }
        receipt_path = run_dir / "comprobante_drive_oficial.json"
        receipt_path.write_text(json.dumps(receipt_real, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        manifest_real = {
            "schema_version": "1.0.0",
            "run_id": run_id,
            "status": status,
            "sha256": actual_sha256,
            "receipt_path": str(receipt_path),
        }
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest_real, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        summary_md = (
            f"# Comprobante de Subida a Google Drive\n\n"
            f"- **Carpeta:** `{clean_folder_url}`\n"
            f"- **Archivo:** `{artifact_file.name}`\n"
            f"- **SHA-256:** `{actual_sha256}`\n"
            f"- **Navegador / Canal:** `{used_channel}` (perfil `{profile_dir}`)\n"
            f"- **Confirmado en UI:** `{upload_confirmed}`\n"
        )
        summary_path = run_dir / "resumen-drive.md"
        summary_path.write_text(summary_md, encoding="utf-8")

        return DriveUploadResult(
            ok=upload_confirmed,
            status=status,
            run_id=run_id,
            run_dir=run_dir,
            folder_url=clean_folder_url,
            artifact_path=str(artifact_file),
            sha256=actual_sha256,
            receipt_path=receipt_path,
            manifest_path=manifest_path,
            summary_md_path=summary_path,
            screenshot_path=screenshot_path,
            evidence=evidence,
        )


__all__ = [
    "DriveUploadRequest",
    "DriveUploadResult",
    "GoogleDriveInteractiveUploader",
    "resolve_drive_profile_dir",
    "validate_drive_folder_url",
]
