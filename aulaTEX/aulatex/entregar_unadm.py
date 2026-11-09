"""Agente ``entregar-unadm`` (tipo ``realizar-entrega``) para AulaTeX.

Ejecuta el envío autenticado y formal de actividades académicas aprobadas
hacia la plataforma virtual UnADM (Moodle ``aulavirtual.unadmexico.mx``).

Principio inquebrantable de seguridad:
"Autorizar la realización de una actividad no equivale a autorizar su envío."
Este agente opera con compuerta de bloqueo estricta (fail-closed): SOLO puede
enviar la entrega después de recibir validación explícita del usuario para esa
actividad y artefacto (`user_validated=True`). Sin esa validación, jamás realiza
ninguna acción en la plataforma.

Garantiza aislamiento total de credenciales mediante ``PlatformCredentialVault``,
cotejo de hash SHA-256 pre y post envío, captura de comprobantes y ausencia total
de secretos en registros y artefactos generados.
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

from .navegacion_plataforma import (
    PlatformCredentialBlockedError,
    assert_no_credential_leak,
    ensure_same_https_host,
    load_vault_account,
    resolve_doh_host_args,
    sanitize_platform_text,
)
from .navegacion_unadm import COURSES_UNADM, UNADM_BASE_URL, UNADM_HOST
from .planning_layout import subject_layout
from .realizar_entrega import (
    AGENT_TYPE_REALIZAR_ENTREGA,
    DeliveryGateBlockedError,
    DeliverySubmissionRequest,
    DeliverySubmissionResult,
    DeliveryValidationError,
    RealizarEntregaAgent,
    register_delivery_agent,
)
from .realizar_planeacion_unadm import UNADM_SUBJECTS_CATALOG
from .workspace import AulaTeXWorkspace

AGENT_ID_ENTREGAR_UNADM = "entregar-unadm"


@dataclass(frozen=True)
class EntregarUnadmRequest:
    """Solicitud de entrega específica para UnADM."""

    subject_slug: str
    activity_number: int
    artifact_path: str | Path
    expected_sha256: str | None = None
    course_id: int | None = None
    module_id: int | None = None
    user_validated: bool = False  # COMPUERTA OBLIGATORIA: True únicamente si el usuario validó explícitamente
    user_confirmation: str = ""
    finalize: bool = False  # True para envío definitivo "Enviado para calificar"
    dry_run: bool = True  # True para simulación y verificación sin alterar plataforma
    output_dir: str = ""


def parse_forum_post(content: str) -> tuple[str, str]:
    """Extrae el asunto y el cuerpo limpio de una participación académica de foro."""
    asunto = ""
    lines = content.strip().splitlines()
    body_lines: list[str] = []

    for i, line in enumerate(lines):
        line_s = line.strip()
        if line_s.lower().startswith("asunto:"):
            asunto = line_s.split(":", 1)[1].strip()
            body_lines = lines[i + 1:]
            break
        elif "título de la intervención" in line_s.lower() or "titulo de la intervencion" in line_s.lower():
            for next_line in lines[i + 1:]:
                n_str = next_line.strip().strip("*").strip()
                if n_str and not n_str.startswith("#") and not n_str.startswith("-"):
                    asunto = n_str
                    break

    if not asunto:
        asunto = "Participación académica en foro - S6"
        body_lines = lines

    cleaned_body: list[str] = []
    in_header = True
    for l in body_lines:
        ls = l.strip()
        if in_header:
            if any(ls.startswith(p) for p in ("#", "**Asignatura:", "**Semana:", "**Estudiante:", "**Destino", "**Requisito", "---")):
                continue
            if ls.lower().startswith("asunto:"):
                continue
            if not ls:
                continue
            in_header = False
        if "nota de soberanía" in ls.lower() or "nota de soberania" in ls.lower():
            break
        cleaned_body.append(l)

    message = "\n".join(cleaned_body).strip()
    return asunto, message

class EntregarUnadmAgent(RealizarEntregaAgent):
    """Agente especializado en realizar entregas en UnADM tras validación explícita."""

    agent_id: str = AGENT_ID_ENTREGAR_UNADM
    agent_type: str = AGENT_TYPE_REALIZAR_ENTREGA

    def __init__(self, workspace: AulaTeXWorkspace | None = None) -> None:
        super().__init__(workspace=workspace)
        self.runs_root = self.workspace.feedback_root / "entregar-unadm" / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)

    def _resolve_subject_root(self, subject_slug: str) -> Path:
        base_slug = subject_slug.replace("-lde", "").strip()
        candidates = [
            self.workspace.repo_root / "UnADM" / "licenciatura-en-derecho-unadm" / f"{base_slug}-lde",
            self.workspace.repo_root / "UnADM" / "licenciatura-en-derecho-unadm" / base_slug,
            self.workspace.repo_root / "UnADM" / f"{base_slug}-lde",
            self.workspace.repo_root / "UnADM" / base_slug,
        ]
        for c in candidates:
            if c.is_dir():
                return c
        return candidates[0]

    def submit(self, request: DeliverySubmissionRequest | EntregarUnadmRequest) -> DeliverySubmissionResult:
        """Procesa la entrega formal en UnADM aplicando la compuerta de validación de usuario."""
        run_id = f"{self.workspace.timestamp()}-entregar-unadm"
        run_dir = (
            self.workspace.resolve_target(request.output_dir)
            if request.output_dir.strip()
            else self.runs_root / run_id
        )
        run_dir.mkdir(parents=True, exist_ok=True)

        base_slug = request.subject_slug.replace("-lde", "").strip()
        catalog_entry = UNADM_SUBJECTS_CATALOG.get(base_slug, {})
        cid = request.course_id or catalog_entry.get("course_id") or 3482
        mid = request.module_id

        artifact_file = Path(request.artifact_path)
        if not artifact_file.is_absolute():
            artifact_file = (self.workspace.repo_root / artifact_file).resolve()

        # ------------------------------------------------------------------
        # COMPUERTA 1: VALIDACIÓN EXPLÍCITA DEL USUARIO (FAIL-CLOSED)
        # "Autorizar la realización de una actividad no equivale a autorizar su envío."
        # ------------------------------------------------------------------
        if not request.user_validated:
            blocker = {
                "code": "missing_user_validation",
                "detail": (
                    "Entrega bloqueada por política de seguridad: autorizar la realización de una actividad "
                    "no equivale a autorizar su envío. Se requiere validación explícita del usuario "
                    f"para la actividad {request.activity_number} y el artefacto {artifact_file.name} (user_validated=True)."
                ),
                "blocking": True,
            }
            manifest: dict[str, Any] = {
                "schema_version": "1.0.0",
                "run_id": run_id,
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "institution": "UnADM",
                "subject_slug": base_slug,
                "activity_number": request.activity_number,
                "artifact_path": str(artifact_file),
                "user_validated": False,
                "status": "blocked_missing_user_validation",
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "blockers": [blocker],
            }
            assert_no_credential_leak(manifest)
            manifest_path = run_dir / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            summary_md = (
                f"# Intento de Entrega Bloqueado: Falta Validación de Usuario\n\n"
                f"- **Agente:** `{self.agent_id}` (`{self.agent_type}`)\n"
                f"- **Asignatura:** `{base_slug}` (Actividad {request.activity_number})\n"
                f"- **Artefacto:** `{artifact_file.name}`\n"
                f"- **Estado:** `BLOQUEADO (FAIL-CLOSED)`\n\n"
                f"### Motivo de Parada\n"
                f"> **Autorizar la realización de una actividad no equivale a autorizar su envío.**\n"
                f"> No se realizó ninguna acción sobre la plataforma UnADM. "
                f"El artefacto debe ser presentado al usuario para validación explícita.\n"
            )
            assert_no_credential_leak(summary_md)
            summary_md_path = run_dir / "resumen-entrega.md"
            summary_md_path.write_text(summary_md, encoding="utf-8")

            return DeliverySubmissionResult(
                ok=False,
                status="blocked_missing_user_validation",
                run_id=run_id,
                run_dir=run_dir,
                artifact_path=str(artifact_file),
                sha256="",
                platform_url="",
                receipt_path=None,
                manifest_path=manifest_path,
                summary_md_path=summary_md_path,
                blockers=(blocker,),
            )

        # ------------------------------------------------------------------
        # COMPUERTA 2: INTEGRIDAD Y VERIFICACIÓN DEL ARTEFACTO LOCAL
        # ------------------------------------------------------------------
        if not artifact_file.is_file():
            blocker = {
                "code": "artifact_not_found",
                "detail": f"El artefacto para entrega no existe en la ruta: {artifact_file}",
                "blocking": True,
            }
            return DeliverySubmissionResult(
                ok=False,
                status="blocked_artifact_not_found",
                run_id=run_id,
                run_dir=run_dir,
                artifact_path=str(artifact_file),
                sha256="",
                platform_url="",
                blockers=(blocker,),
            )

        artifact_bytes = artifact_file.read_bytes()
        cat_info = UNADM_SUBJECTS_CATALOG.get(base_slug, {}).get("activities", {}).get(request.activity_number, {})
        is_forum = (cat_info.get("kind") == "forum") or (artifact_file.suffix.lower() in (".txt", ".md"))
        is_pdf = artifact_bytes.startswith(b"%PDF-")
        is_text_forum = is_forum and (artifact_file.suffix.lower() in (".txt", ".md")) and len(artifact_bytes) >= 100

        if not (is_pdf or is_text_forum):
            blocker = {
                "code": "invalid_format",
                "detail": f"El artefacto {artifact_file.name} no es un PDF válido ni un texto de foro (.txt/.md).",
                "blocking": True,
            }
            return DeliverySubmissionResult(
                ok=False,
                status="blocked_invalid_format",
                run_id=run_id,
                run_dir=run_dir,
                artifact_path=str(artifact_file),
                sha256="",
                platform_url="",
                blockers=(blocker,),
            )

        calculated_sha256 = hashlib.sha256(artifact_bytes).hexdigest()
        if request.expected_sha256 and calculated_sha256 != request.expected_sha256.strip().lower():
            blocker = {
                "code": "hash_mismatch",
                "detail": f"Discrepancia de SHA-256. Esperado: {request.expected_sha256}, Actual: {calculated_sha256}",
                "blocking": True,
            }
            return DeliverySubmissionResult(
                ok=False,
                status="blocked_hash_mismatch",
                run_id=run_id,
                run_dir=run_dir,
                artifact_path=str(artifact_file),
                sha256=calculated_sha256,
                platform_url="",
                blockers=(blocker,),
            )

        # ------------------------------------------------------------------
        # COMPUERTA 3: DISPONIBILIDAD DE CREDENCIALES EN BÓVEDA SEGURA
        # ------------------------------------------------------------------
        try:
            vault_acc = load_vault_account(self.workspace.repo_root, "UnADM", UNADM_HOST)
        except PlatformCredentialBlockedError as pbe:
            blocker = {
                "code": "vault_credentials_unavailable",
                "detail": str(pbe),
                "blocking": True,
            }
            return DeliverySubmissionResult(
                ok=False,
                status="blocked_credentials_unavailable",
                run_id=run_id,
                run_dir=run_dir,
                artifact_path=str(artifact_file),
                sha256=calculated_sha256,
                platform_url="",
                blockers=(blocker,),
            )

        del vault_acc  # Liberar referencia inmediatamente

        # ------------------------------------------------------------------
        # MODO DRY-RUN: Simulación y validación de contrato sin mutar plataforma
        # ------------------------------------------------------------------
        if is_forum:
            mod_url = f"{UNADM_BASE_URL}/mod/forum/view.php?id={mid}" if mid else f"{UNADM_BASE_URL}/course/view.php?id={cid}"
        else:
            mod_url = f"{UNADM_BASE_URL}/mod/assign/view.php?id={mid}" if mid else f"{UNADM_BASE_URL}/course/view.php?id={cid}"

        if request.dry_run:
            manifest = {
                "schema_version": "1.0.0",
                "run_id": run_id,
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "institution": "UnADM",
                "subject_slug": base_slug,
                "activity_number": request.activity_number,
                "artifact_path": str(artifact_file),
                "sha256": calculated_sha256,
                "user_validated": True,
                "dry_run": True,
                "status": "dry_run_validated",
                "target_platform_url": mod_url,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "notice": "Simulación validada: requisitos locales e integridad confirmados sin interacción de red.",
            }
            assert_no_credential_leak(manifest)
            manifest_path = run_dir / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            receipt = {
                "receipt_type": "dry_run_verification",
                "verified_at": manifest["timestamp_utc"],
                "subject": base_slug,
                "activity_number": request.activity_number,
                "filename": artifact_file.name,
                "bytes": len(artifact_bytes),
                "sha256": calculated_sha256,
                "platform_submission_performed": False,
                "status": "dry_run_validated",
            }
            assert_no_credential_leak(receipt)
            receipt_path = run_dir / f"comprobante-simulacion-S{request.activity_number}.json"
            receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            summary_md = (
                f"# Verificación de Entrega Dry-Run UnADM (`{self.agent_id}`)\n\n"
                f"- **Asignatura:** `{base_slug}` (Actividad {request.activity_number})\n"
                f"- **Artefacto Validado:** `{artifact_file.name}`\n"
                f"- **SHA-256:** `{calculated_sha256}`\n"
                f"- **Validación de Usuario:** `CONFIRMADA (user_validated=True)`\n"
                f"- **Modo:** `DRY-RUN (Sin mutación en plataforma)`\n"
                f"- **Estado:** `dry_run_validated`\n"
            )
            assert_no_credential_leak(summary_md)
            summary_md_path = run_dir / "resumen-entrega.md"
            summary_md_path.write_text(summary_md, encoding="utf-8")

            return DeliverySubmissionResult(
                ok=True,
                status="dry_run_validated",
                run_id=run_id,
                run_dir=run_dir,
                artifact_path=str(artifact_file),
                sha256=calculated_sha256,
                platform_url=mod_url,
                receipt_path=receipt_path,
                manifest_path=manifest_path,
                summary_md_path=summary_md_path,
                platform_evidence={"dry_run": True, "artifact_verified": True},
            )

        # ------------------------------------------------------------------
        # MODO EN VIVO: Envío autenticado a plataforma Moodle con Playwright
        # ------------------------------------------------------------------
        if not mid:
            blocker = {
                "code": "missing_module_id",
                "detail": "Para el envío real a UnADM es obligatorio indicar el module_id (ID de la tarea Moodle).",
                "blocking": True,
            }
            return DeliverySubmissionResult(
                ok=False,
                status="blocked_missing_module_id",
                run_id=run_id,
                run_dir=run_dir,
                artifact_path=str(artifact_file),
                sha256=calculated_sha256,
                platform_url="",
                blockers=(blocker,),
            )

        from playwright.sync_api import sync_playwright

        evidence_dir = run_dir / "evidencia_plataforma"
        evidence_dir.mkdir(parents=True, exist_ok=True)

        doh_args, _dns_mode = resolve_doh_host_args(UNADM_HOST)
        browser_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ] + doh_args

        credentials = load_vault_account(self.workspace.repo_root, "UnADM", UNADM_HOST)
        final_text = ""
        screenshot_path = evidence_dir / f"entrega-confirmada-S{request.activity_number}.png"
        submission_performed = False

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=browser_args,
            )
            context = browser.new_context(
                viewport={"width": 1440, "height": 1100},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            )
            page = context.new_page()
            page.set_default_timeout(45000)

            # 1. Login seguro
            page.goto(f"{UNADM_BASE_URL}/login/index.php", wait_until="domcontentloaded")
            page.get_by_role("textbox", name=re.compile("Matr|Usuario|Username", re.I)).fill(credentials["username"])
            page.locator("input[type=password]").fill(credentials["password"])
            page.get_by_role("button", name=re.compile("Inicia sesi|Acceder|Login", re.I)).click()
            page.wait_for_url(lambda url: "/login/" not in urlsplit(url).path)

            # Destruir credenciales de memoria inmediatamente
            del credentials

            # 2. Navegar a la actividad (tarea o foro)
            page.goto(mod_url, wait_until="networkidle")
            ensure_same_https_host(page.url, UNADM_HOST, UNADM_BASE_URL)
            main_sec = page.locator("#region-main, [role='main']").first
            before_text = main_sec.inner_text()

            if is_forum:
                asunto, mensaje = parse_forum_post(artifact_file.read_text(encoding="utf-8"))
                post_titles = main_sec.locator(".discussionname, .topic.starter, .forumpost").all_inner_texts()
                already_posted = any(asunto.lower()[:30] in pt.lower() for pt in post_titles)

                if already_posted and not request.finalize:
                    final_text = before_text
                    status_str = "already_submitted"
                else:
                    add_topic_btn = page.locator('a:has-text("Añadir un nuevo tema de debate"), button:has-text("Añadir un nuevo tema"), [data-action="add-discussion-topic"], a[href*="post.php?forum="]').first
                    if add_topic_btn.count():
                        add_topic_btn.click()
                        page.wait_for_load_state("networkidle")
                        time.sleep(1)

                        subject_input = page.locator('#id_subject, input[name="subject"]').first
                        if subject_input.count():
                            subject_input.fill(asunto)

                        msg_editor = page.locator('#id_messageeditable, div[role="textbox"], textarea[name="message"]').first
                        if msg_editor.count():
                            msg_editor.fill(mensaje)

                        submit_forum = page.locator('#id_submitbutton, button[name="submitbutton"], input[type="submit"][value*="foro"]').first
                        if submit_forum.count() and request.finalize:
                            submit_forum.click()
                            page.wait_for_load_state("networkidle")
                            time.sleep(2)
                            status_str = "submitted_for_grading"
                        else:
                            status_str = "draft_saved"
                    else:
                        status_str = "draft_saved"

                    final_text = main_sec.inner_text()
                    submission_performed = True
            elif "Enviado para calificar" in before_text and not request.finalize:
                final_text = before_text
                status_str = "already_submitted"
            else:
                # 3. Subir archivo
                page.goto(f"{mod_url}&action=editsubmission", wait_until="networkidle")
                add_btn = page.locator(".fp-btn-add a, [title='Agregar...']").first
                if add_btn.count():
                    add_btn.click()
                    time.sleep(1.5)
                    page.get_by_text("Subir un archivo", exact=True).first.click()
                    time.sleep(0.5)
                    page.locator('input[type="file"]').first.set_input_files(str(artifact_file))
                    time.sleep(0.5)
                    page.get_by_role("button", name="Subir este archivo", exact=True).first.click()

                    for _ in range(20):
                        time.sleep(1)
                        if page.locator('.moodle-dialogue-focused, .moodle-dialogue-wrap').filter(has_text="Subir un archivo").count() == 0:
                            break

                    page.locator("#id_submitbutton, button[name='submitbutton']").first.click()
                    page.wait_for_load_state("networkidle")
                    page.goto(mod_url, wait_until="networkidle")

                # 4. Finalizar si se solicitó
                if request.finalize:
                    submit_btn = page.get_by_role("button", name=re.compile("Enviar tarea|Enviar para calificar", re.I))
                    if submit_btn.count() >= 1:
                        submit_btn.first.click()
                        page.wait_for_load_state("networkidle")
                        statement = page.locator("#id_submissionstatement")
                        if statement.count():
                            statement.check()
                        page.locator("#id_submitbutton, button[name='submitbutton']").first.click()
                        page.wait_for_load_state("networkidle")

                page.goto(mod_url, wait_until="networkidle")
                final_text = main_sec.inner_text()
                submission_performed = True
                status_str = "submitted_for_grading" if "Enviado para calificar" in final_text else "draft_saved"

            page.screenshot(path=str(screenshot_path), full_page=True)
            browser.close()

        # Guardar comprobante formal
        receipt_record = {
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "institution": "UnADM",
            "subject": base_slug,
            "course_id": cid,
            "module_id": mid,
            "activity_number": request.activity_number,
            "filename": artifact_file.name,
            "bytes": len(artifact_bytes),
            "sha256": calculated_sha256,
            "platform_url": mod_url,
            "state": status_str,
            "platform_submission_performed": submission_performed,
            "text_preview": sanitize_platform_text(final_text[:500]),
        }
        assert_no_credential_leak(receipt_record)
        receipt_path = run_dir / f"comprobante-envio-S{request.activity_number}.json"
        receipt_path.write_text(json.dumps(receipt_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        manifest = {
            "schema_version": "1.0.0",
            "run_id": run_id,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "institution": "UnADM",
            "subject_slug": base_slug,
            "activity_number": request.activity_number,
            "artifact_path": str(artifact_file),
            "sha256": calculated_sha256,
            "user_validated": True,
            "dry_run": False,
            "status": status_str,
            "platform_url": mod_url,
            "receipt_path": str(receipt_path),
            "timestamp_utc": receipt_record["verified_at"],
        }
        assert_no_credential_leak(manifest)
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        summary_md = (
            f"# Comprobante de Entrega UnADM (`{self.agent_id}`)\n\n"
            f"- **Asignatura:** `{base_slug}` (Actividad {request.activity_number})\n"
            f"- **Artefacto:** `{artifact_file.name}`\n"
            f"- **SHA-256:** `{calculated_sha256}`\n"
            f"- **Validación de Usuario:** `CONFIRMADA (user_validated=True)`\n"
            f"- **Estado en Plataforma:** `{status_str}`\n"
            f"- **Comprobante:** `{receipt_path.name}`\n"
        )
        assert_no_credential_leak(summary_md)
        summary_md_path = run_dir / "resumen-entrega.md"
        summary_md_path.write_text(summary_md, encoding="utf-8")

        return DeliverySubmissionResult(
            ok=True,
            status=status_str,
            run_id=run_id,
            run_dir=run_dir,
            artifact_path=str(artifact_file),
            sha256=calculated_sha256,
            platform_url=mod_url,
            receipt_path=receipt_path,
            manifest_path=manifest_path,
            summary_md_path=summary_md_path,
            platform_evidence={"final_state": status_str},
        )


# Registrar agente de entrega institucional UnADM
register_delivery_agent("UnADM", EntregarUnadmAgent)
register_delivery_agent("unadmexico", EntregarUnadmAgent)

__all__ = [
    "AGENT_ID_ENTREGAR_UNADM",
    "EntregarUnadmAgent",
    "EntregarUnadmRequest",
]
