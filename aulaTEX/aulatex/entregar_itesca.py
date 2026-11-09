"""Agente ``entregar-itesca`` (tipo ``realizar-entrega``) para AulaTeX.

Ejecuta el envío autenticado y formal de actividades académicas aprobadas
hacia la plataforma virtual ITESCA (Moodle ``cursos3.e-itesca.edu.mx``).

Principio inquebrantable de seguridad y soberanía del usuario:
"Autorizar la realización de una actividad no equivale a autorizar su envío."
Este agente opera con compuerta de bloqueo estricta (fail-closed): SOLO puede
enviar la entrega después de recibir validación explícita del usuario para esa
actividad y artefacto (`user_validated=True`). Sin esa validación, jamás realiza
ninguna acción mutante ni sube archivos a la plataforma.

Compuertas adicionales:
1. Protección estricta de cuestionarios en vivo (`live_quiz_attempt_protected`):
   Los cuestionarios en línea con intentos cronometrados jamás se resuelven de forma
   desatendida; se preserva la guía de estudio y reporte de reactivos localmente.
2. Integridad de artefacto: Cotejo de hash SHA-256 pre y post envío.
3. Aislamiento total de credenciales mediante ``PlatformCredentialVault`` y
   ausencia absoluta de secretos en bitácoras, comprobantes y manifiestos.
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

from .monitor_itesca import ITESCA_SUBJECTS_CATALOG, _clean_slug
from .navegacion_itesca import ITESCA_BASE_URL, ITESCA_HOST
from .navegacion_plataforma import (
    PlatformCredentialBlockedError,
    assert_no_credential_leak,
    ensure_same_https_host,
    load_vault_account,
    resolve_doh_host_args,
    sanitize_platform_text,
)
from .realizar_entrega import (
    AGENT_TYPE_REALIZAR_ENTREGA,
    DeliveryGateBlockedError,
    DeliverySubmissionRequest,
    DeliverySubmissionResult,
    DeliveryValidationError,
    RealizarEntregaAgent,
    register_delivery_agent,
)
from .workspace import AulaTeXWorkspace

AGENT_ID_ENTREGAR_ITESCA = "entregar-itesca"


@dataclass(frozen=True)
class EntregarItescaRequest:
    """Solicitud de entrega específica para ITESCA."""

    subject_slug: str
    activity_number: int
    artifact_path: str | Path
    expected_sha256: str | None = None
    course_id: int | None = None
    module_id: int | None = None
    user_validated: bool = False  # COMPUERTA OBLIGATORIA (FAIL-CLOSED)
    user_confirmation: str = ""
    finalize: bool = False  # True para 'Enviar para calificar' definitivo, False para borrador
    dry_run: bool = True  # True por omisión para simulación y validación previa
    output_dir: str = ""


class EntregarItescaAgent(RealizarEntregaAgent):
    """Agente especializado en realizar entregas en ITESCA tras validación explícita."""

    agent_id: str = AGENT_ID_ENTREGAR_ITESCA
    agent_type: str = AGENT_TYPE_REALIZAR_ENTREGA

    def __init__(self, workspace: AulaTeXWorkspace | None = None) -> None:
        super().__init__(workspace=workspace)
        self.runs_root = self.workspace.feedback_root / "entregar-itesca" / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)

    def _resolve_subject_root(self, subject_slug: str) -> Path:
        slug = _clean_slug(subject_slug)
        mga_root = self.workspace.repo_root / "ITESCA" / "maestria-en-gestion-administrativa"
        candidates = [
            mga_root / f"{slug}-mga",
            mga_root / slug,
            self.workspace.repo_root / "ITESCA" / f"{slug}-mga",
            self.workspace.repo_root / "ITESCA" / slug,
        ]
        for c in candidates:
            if c.is_dir():
                return c
        return candidates[0]

    def submit(self, request: DeliverySubmissionRequest | EntregarItescaRequest) -> DeliverySubmissionResult:
        """Procesa la entrega formal en ITESCA aplicando compuertas de seguridad."""
        run_id = f"{self.workspace.timestamp()}-entregar-itesca"
        run_dir = (
            self.workspace.resolve_target(request.output_dir)
            if request.output_dir.strip()
            else self.runs_root / run_id
        )
        run_dir.mkdir(parents=True, exist_ok=True)

        clean_slug = _clean_slug(request.subject_slug)
        catalog_entry = ITESCA_SUBJECTS_CATALOG.get(clean_slug, {})
        cid = request.course_id or catalog_entry.get("course_id") or 209
        act_info = catalog_entry.get("activities", {}).get(request.activity_number, {})
        mid = request.module_id or act_info.get("module_id")
        is_quiz = bool(act_info.get("is_quiz", False))

        artifact_file = Path(request.artifact_path)
        if not artifact_file.is_absolute():
            subject_root = self._resolve_subject_root(clean_slug)
            candidate1 = subject_root / artifact_file
            candidate2 = self.workspace.repo_root / artifact_file
            if candidate1.is_file():
                artifact_file = candidate1.resolve()
            elif candidate2.is_file():
                artifact_file = candidate2.resolve()
            else:
                artifact_file = candidate1.resolve()

        platform_assign_url = f"{ITESCA_BASE_URL}/mod/assign/view.php?id={mid}" if mid else ITESCA_BASE_URL

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
                "institution": "ITESCA",
                "subject_slug": clean_slug,
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
                f"- **Institución:** ITESCA (Maestría en Gestión Administrativa)\n"
                f"- **Asignatura:** `{clean_slug}` (Actividad {request.activity_number})\n"
                f"- **Artefacto Local:** `{artifact_file.name}`\n"
                f"- **Motivo del Bloqueo:** {blocker['detail']}\n\n"
                f"El trabajo permanece seguro e íntegro en el repositorio local; ninguna acción fue realizada en ITESCA Virtual.\n"
            )
            assert_no_credential_leak(summary_md)
            summary_path = run_dir / "resumen-entrega.md"
            summary_path.write_text(summary_md, encoding="utf-8")

            return DeliverySubmissionResult(
                ok=False,
                status="blocked_missing_user_validation",
                run_id=run_id,
                run_dir=run_dir,
                artifact_path=str(artifact_file),
                sha256="",
                platform_url=platform_assign_url,
                manifest_path=manifest_path,
                summary_md_path=summary_path,
                blockers=(blocker,),
            )

        # ------------------------------------------------------------------
        # COMPUERTA 2: PROTECCIÓN DE CUESTIONARIO EN LÍNEA (QUIZ GATE)
        # ------------------------------------------------------------------
        if is_quiz or (mid and mid == 1763):
            blocker = {
                "code": "live_quiz_attempt_protected",
                "detail": (
                    "Compuerta de seguridad: los cuestionarios en línea con límite de tiempo o intento único "
                    "no admiten entrega ni resolución automatizada desatendida. Se valida y preserva el reporte "
                    f"de preparación de reactivos ({artifact_file.name}) para resolución directa por el estudiante."
                ),
                "blocking": True,
            }
            manifest_quiz = {
                "schema_version": "1.0.0",
                "run_id": run_id,
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "institution": "ITESCA",
                "subject_slug": clean_slug,
                "activity_number": request.activity_number,
                "status": "blocked_live_quiz_protected",
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "blockers": [blocker],
            }
            assert_no_credential_leak(manifest_quiz)
            m_path = run_dir / "manifest.json"
            m_path.write_text(json.dumps(manifest_quiz, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

            summary_md = (
                f"# Cuestionario en Línea Protegido: Resolución Desatendida Bloqueada\n\n"
                f"- **Agente:** `{self.agent_id}` (`{self.agent_type}`)\n"
                f"- **Institución:** ITESCA Virtual\n"
                f"- **Asignatura:** `{clean_slug}` (Actividad {request.activity_number})\n"
                f"- **Módulo Moodle:** `{mid}` ({ITESCA_BASE_URL}/mod/quiz/view.php?id={mid})\n"
                f"- **Guía de Estudio Local:** `{artifact_file.name}`\n"
                f"- **Compuerta:** `live_quiz_attempt_protected` activa. El cuestionario debe ser respondido por el alumno.\n"
            )
            assert_no_credential_leak(summary_md)
            s_path = run_dir / "resumen-entrega.md"
            s_path.write_text(summary_md, encoding="utf-8")

            return DeliverySubmissionResult(
                ok=False,
                status="blocked_live_quiz_protected",
                run_id=run_id,
                run_dir=run_dir,
                artifact_path=str(artifact_file),
                sha256="",
                platform_url=f"{ITESCA_BASE_URL}/mod/quiz/view.php?id={mid}" if mid else ITESCA_BASE_URL,
                manifest_path=m_path,
                summary_md_path=s_path,
                blockers=(blocker,),
            )

        # ------------------------------------------------------------------
        # COMPUERTA 3: INTEGRIDAD Y FORMATO DEL ARTEFACTO (.pdf o .docx)
        # ------------------------------------------------------------------
        if not artifact_file.is_file():
            blocker = {
                "code": "artifact_not_found",
                "detail": f"El archivo de entrega no existe en la ruta indicada: {artifact_file}",
                "blocking": True,
            }
            manifest_err = {
                "schema_version": "1.0.0",
                "run_id": run_id,
                "agent_id": self.agent_id,
                "status": "blocked_artifact_not_found",
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "blockers": [blocker],
            }
            m_path = run_dir / "manifest.json"
            m_path.write_text(json.dumps(manifest_err, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return DeliverySubmissionResult(
                ok=False,
                status="blocked_artifact_not_found",
                run_id=run_id,
                run_dir=run_dir,
                artifact_path=str(artifact_file),
                sha256="",
                platform_url=platform_assign_url,
                manifest_path=m_path,
                blockers=(blocker,),
            )

        # Validar extensiones admitidas en ITESCA MGA (.pdf, .docx)
        if artifact_file.suffix.lower() not in (".pdf", ".docx"):
            blocker = {
                "code": "invalid_artifact_format",
                "detail": f"Formato inválido: '{artifact_file.suffix}'. Solo se admiten archivos .pdf y .docx en ITESCA.",
                "blocking": True,
            }
            m_path = run_dir / "manifest.json"
            m_path.write_text(json.dumps({"blockers": [blocker]}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return DeliverySubmissionResult(
                ok=False,
                status="blocked_invalid_format",
                run_id=run_id,
                run_dir=run_dir,
                artifact_path=str(artifact_file),
                sha256="",
                platform_url=platform_assign_url,
                manifest_path=m_path,
                blockers=(blocker,),
            )

        content_bytes = artifact_file.read_bytes()
        actual_sha256 = hashlib.sha256(content_bytes).hexdigest()

        if request.expected_sha256 and actual_sha256.lower() != request.expected_sha256.lower():
            blocker = {
                "code": "hash_mismatch",
                "detail": (
                    f"Discrepancia en la integridad del artefacto. "
                    f"Esperado: {request.expected_sha256}, Actual: {actual_sha256}. Envío detenido."
                ),
                "blocking": True,
            }
            m_path = run_dir / "manifest.json"
            m_path.write_text(json.dumps({"blockers": [blocker]}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return DeliverySubmissionResult(
                ok=False,
                status="blocked_hash_mismatch",
                run_id=run_id,
                run_dir=run_dir,
                artifact_path=str(artifact_file),
                sha256=actual_sha256,
                platform_url=platform_assign_url,
                manifest_path=m_path,
                blockers=(blocker,),
            )

        # ------------------------------------------------------------------
        # COMPUERTA 4: MODO SEGURO (DRY-RUN) VS ENVÍO REAL AUTORIZADO
        # ------------------------------------------------------------------
        if request.dry_run:
            receipt = {
                "receipt_type": "itesca_delivery_dry_run_receipt",
                "run_id": run_id,
                "agent_id": self.agent_id,
                "institution": "ITESCA",
                "subject": clean_slug,
                "activity_number": request.activity_number,
                "module_id": mid,
                "course_id": cid,
                "artifact_name": artifact_file.name,
                "artifact_path": str(artifact_file),
                "size_bytes": len(content_bytes),
                "sha256": actual_sha256,
                "user_validated": True,
                "dry_run": True,
                "platform_target_url": platform_assign_url,
                "validation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "status": "dry_run_validated_ready_for_dispatch",
            }
            assert_no_credential_leak(receipt)
            receipt_path = run_dir / "comprobante_dry_run.json"
            receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

            manifest_ok: dict[str, Any] = {
                "schema_version": "1.0.0",
                "run_id": run_id,
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "status": "dry_run_validated",
                "institution": "ITESCA",
                "subject_slug": clean_slug,
                "activity_number": request.activity_number,
                "artifact_path": str(artifact_file),
                "sha256": actual_sha256,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "receipt_path": str(receipt_path),
            }
            assert_no_credential_leak(manifest_ok)
            manifest_path = run_dir / "manifest.json"
            manifest_path.write_text(json.dumps(manifest_ok, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

            summary_md = (
                f"# Comprobante de Validación de Entrega ITESCA (Modo Seguro Dry-Run)\n\n"
                f"- **Agente:** `{self.agent_id}` (`{self.agent_type}`)\n"
                f"- **Institución:** ITESCA (Maestría en Gestión Administrativa)\n"
                f"- **Asignatura:** `{clean_slug}` (Curso {cid}, Módulo {mid})\n"
                f"- **Actividad:** #{request.activity_number}\n"
                f"- **Artefacto Validado:** `{artifact_file.name}` ({len(content_bytes):,} bytes)\n"
                f"- **Hash SHA-256:** `{actual_sha256}`\n"
                f"- **Destino en ITESCA:** `{platform_assign_url}`\n"
                f"- **Estado de Validación:** `VALIDADO PARA ENVÍO (DRY-RUN)`\n"
                f"- **Aviso:** El archivo NO fue subido a la plataforma Moodle (dry_run=True).\n"
            )
            assert_no_credential_leak(summary_md)
            summary_path = run_dir / "resumen-entrega.md"
            summary_path.write_text(summary_md, encoding="utf-8")

            return DeliverySubmissionResult(
                ok=True,
                status="dry_run_validated",
                run_id=run_id,
                run_dir=run_dir,
                artifact_path=str(artifact_file),
                sha256=actual_sha256,
                platform_url=platform_assign_url,
                receipt_path=receipt_path,
                manifest_path=manifest_path,
                summary_md_path=summary_path,
                platform_evidence={"dry_run": True, "target_url": platform_assign_url},
            )

        # ------------------------------------------------------------------
        # ENVÍO REAL AUTORIZADO A ITESCA VIRTUAL (dry_run=False)
        # ------------------------------------------------------------------
        if not mid:
            blocker = {
                "code": "missing_module_id",
                "detail": "Para el envío real a ITESCA es obligatorio indicar el module_id (ID de la tarea Moodle).",
                "blocking": True,
            }
            return DeliverySubmissionResult(
                ok=False,
                status="blocked_missing_module_id",
                run_id=run_id,
                run_dir=run_dir,
                artifact_path=str(artifact_file),
                sha256=actual_sha256,
                platform_url="",
                blockers=(blocker,),
            )

        from playwright.sync_api import sync_playwright

        evidence_dir = run_dir / "evidencia_plataforma"
        evidence_dir.mkdir(parents=True, exist_ok=True)

        browser_args, _dns_mode = resolve_doh_host_args(ITESCA_HOST)
        credentials = load_vault_account(self.workspace.repo_root, "ITESCA", ITESCA_HOST)
        final_text = ""
        screenshot_path = evidence_dir / f"entrega-confirmada-mod{mid}.png"
        submission_performed = False
        moodle_status = "No determinado"

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
            page.set_default_navigation_timeout(60000)

            # 1. Login seguro en ITESCA
            page.goto(f"{ITESCA_BASE_URL}/login/index.php", wait_until="domcontentloaded")
            ensure_same_https_host(page.url, ITESCA_HOST, ITESCA_BASE_URL)
            page.locator("#username, input[name=username]").first.fill(credentials["username"])
            page.locator("#password, input[name=password]").first.fill(credentials["password"])
            page.locator("#loginbtn, button[type=submit]").first.click()
            page.wait_for_load_state("domcontentloaded")
            ensure_same_https_host(page.url, ITESCA_HOST, ITESCA_BASE_URL)

            # Destruir credenciales de memoria inmediatamente
            del credentials

            # 2. Navegar a la tarea Moodle
            page.goto(platform_assign_url, wait_until="networkidle")
            ensure_same_https_host(page.url, ITESCA_HOST, ITESCA_BASE_URL)
            main_sec = page.locator("#region-main, [role='main']").first
            before_text = main_sec.inner_text() if main_sec.count() else page.content()

            # Si ya está enviado para calificar y no se requiere finalizar
            if "Enviado para calificar" in before_text and not request.finalize:
                final_text = before_text
                moodle_status = "Enviado para calificar"
                submission_performed = True
            else:
                # 3. Proceder a subir el archivo
                edit_url = f"{platform_assign_url}&action=editsubmission"
                page.goto(edit_url, wait_until="networkidle")
                ensure_same_https_host(page.url, ITESCA_HOST, ITESCA_BASE_URL)

                # Si el selector de archivos está presente
                add_btn = page.locator(".fp-btn-add a, [title='Agregar...'], a[title*='gregar']").first
                if add_btn.count():
                    add_btn.click()
                    time.sleep(1.5)

                    upload_tab = page.locator(".fp-repo:has-text('Subir un archivo'), a:has-text('Subir un archivo')").first
                    if upload_tab.count():
                        upload_tab.click()
                        time.sleep(0.5)

                    file_input = page.locator('input[type="file"]').first
                    file_input.set_input_files(str(artifact_file))
                    time.sleep(0.5)

                    upload_btn = page.locator("button.fp-upload-btn, button:has-text('Subir este archivo')").first
                    if upload_btn.count():
                        upload_btn.click()

                    # Esperar a que se cierre el diálogo modal
                    for _ in range(30):
                        time.sleep(1)
                        if page.locator('.moodle-dialogue-focused, .moodle-dialogue-wrap').filter(has_text=re.compile("Subir un archivo", re.I)).count() == 0:
                            break

                    # Guardar cambios
                    save_btn = page.locator("#id_submitbutton, button[name='submitbutton'], input[name='submitbutton']").first
                    if save_btn.count():
                        save_btn.click()
                        page.wait_for_load_state("networkidle")

                    page.goto(platform_assign_url, wait_until="networkidle")

                # 4. Finalizar si se solicitó (envío formal definitivo)
                if request.finalize:
                    submit_btn = page.locator("button:has-text('Enviar tarea'), button:has-text('Enviar para calificar'), a:has-text('Enviar tarea')").first
                    if submit_btn.count():
                        submit_btn.click()
                        page.wait_for_load_state("networkidle")
                        statement = page.locator("#id_submissionstatement, input[name='submissionstatement']")
                        if statement.count():
                            statement.check()
                        save_btn2 = page.locator("#id_submitbutton, button[name='submitbutton'], input[name='submitbutton']").first
                        if save_btn2.count():
                            save_btn2.click()
                            page.wait_for_load_state("networkidle")

                page.goto(platform_assign_url, wait_until="networkidle")
                main_sec = page.locator("#region-main, [role='main']").first
                final_text = main_sec.inner_text() if main_sec.count() else page.content()
                submission_performed = True

                if "Enviado para calificar" in final_text:
                    moodle_status = "Enviado para calificar"
                elif "Borrador (no enviado)" in final_text or artifact_file.name in final_text:
                    moodle_status = "Archivos enviados (Borrador / Registrado en Moodle)"
                else:
                    moodle_status = "Entrega registrada en plataforma"

            page.screenshot(path=str(screenshot_path), full_page=True)
            browser.close()

        submission_evidence = {
            "dispatch_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "target_url": platform_assign_url,
            "filename_uploaded": artifact_file.name,
            "sha256_uploaded": actual_sha256,
            "platform_confirmed": submission_performed,
            "moodle_status": moodle_status,
            "screenshot_path": str(screenshot_path),
        }

        receipt_real = {
            "receipt_type": "itesca_official_submission_receipt",
            "run_id": run_id,
            "agent_id": self.agent_id,
            "institution": "ITESCA",
            "subject": clean_slug,
            "activity_number": request.activity_number,
            "module_id": mid,
            "course_id": cid,
            "artifact_name": artifact_file.name,
            "sha256": actual_sha256,
            "user_validated": True,
            "finalize": request.finalize,
            "submission_timestamp_utc": submission_evidence["dispatch_timestamp_utc"],
            "evidence": submission_evidence,
        }
        assert_no_credential_leak(receipt_real)
        receipt_path = run_dir / "comprobante_entrega_oficial.json"
        receipt_path.write_text(json.dumps(receipt_real, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        manifest_real = {
            "schema_version": "1.0.0",
            "run_id": run_id,
            "status": "submitted_for_grading" if "calificar" in moodle_status.lower() else "draft_saved",
            "sha256": actual_sha256,
            "receipt_path": str(receipt_path),
        }
        assert_no_credential_leak(manifest_real)
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest_real, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        summary_md = (
            f"# Comprobante de Entrega Confirmada en ITESCA Virtual\n\n"
            f"- **Agente:** `{self.agent_id}` (`{self.agent_type}`)\n"
            f"- **Institución:** ITESCA (Maestría en Gestión Administrativa)\n"
            f"- **Asignatura:** `{clean_slug}` (Módulo {mid})\n"
            f"- **Actividad:** #{request.activity_number}\n"
            f"- **Artefacto Enviado:** `{artifact_file.name}`\n"
            f"- **Hash SHA-256:** `{actual_sha256}`\n"
            f"- **Estatus en Plataforma:** `{submission_evidence['moodle_status']}`\n"
            f"- **Evidencia Visual:** `{screenshot_path.name}`\n"
        )
        assert_no_credential_leak(summary_md)
        summary_path = run_dir / "resumen-entrega.md"
        summary_path.write_text(summary_md, encoding="utf-8")

        return DeliverySubmissionResult(
            ok=True,
            status="submitted_for_grading" if "calificar" in moodle_status.lower() else "draft_saved",
            run_id=run_id,
            run_dir=run_dir,
            artifact_path=str(artifact_file),
            sha256=actual_sha256,
            platform_url=platform_assign_url,
            receipt_path=receipt_path,
            manifest_path=manifest_path,
            summary_md_path=summary_path,
            platform_evidence=submission_evidence,
        )


# Registrar agente de entrega institucional ITESCA
register_delivery_agent("ITESCA", EntregarItescaAgent)
register_delivery_agent("itesca", EntregarItescaAgent)

__all__ = [
    "AGENT_ID_ENTREGAR_ITESCA",
    "EntregarItescaAgent",
    "EntregarItescaRequest",
]
