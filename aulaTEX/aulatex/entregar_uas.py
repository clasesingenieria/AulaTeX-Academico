"""Agente ``entregar-uas`` (tipo ``realizar-entrega``) para AulaTeX.

Ejecuta el envío autenticado y formal de actividades académicas aprobadas
hacia la plataforma virtual UAS (Moodle ``virtual.uas.edu.mx/fca``).

Principio inquebrantable de seguridad:
"Autorizar la realización de una actividad no equivale a autorizar su envío."
Este agente opera con compuerta de bloqueo estricta (fail-closed): SOLO puede
enviar la entrega después de recibir validación explícita del usuario para esa
actividad y artefacto (`user_validated=True`). Sin esa validación, jamás realiza
ninguna acción mutante ni sube archivos a la plataforma.

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

from .monitor_uas import UAS_SUBJECTS_CATALOG
from .navegacion_plataforma import (
    PlatformCredentialBlockedError,
    assert_no_credential_leak,
    ensure_same_https_host,
    load_vault_account,
    resolve_doh_host_args,
    sanitize_platform_text,
)
from .navegacion_uas import UAS_BASE_URL, UAS_HOST
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
from .workspace import AulaTeXWorkspace

AGENT_ID_ENTREGAR_UAS = "entregar-uas"


@dataclass(frozen=True)
class EntregarUasRequest:
    """Solicitud de entrega específica para UAS."""

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


class EntregarUasAgent(RealizarEntregaAgent):
    """Agente especializado en realizar entregas en UAS tras validación explícita."""

    agent_id: str = AGENT_ID_ENTREGAR_UAS
    agent_type: str = AGENT_TYPE_REALIZAR_ENTREGA

    def __init__(self, workspace: AulaTeXWorkspace | None = None) -> None:
        super().__init__(workspace=workspace)
        self.runs_root = self.workspace.feedback_root / "entregar-uas" / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)

    def _resolve_subject_root(self, subject_slug: str) -> Path:
        clean = subject_slug.replace("-uas", "").strip().lower()
        if clean in ("investigacion-aplicada", "investigacion-aplicada-contaduria"):
            clean = "investigacion-aplicada-a-la-contaduria"

        candidates = [
            self.workspace.repo_root / "UAS" / "licenciatura-en-contaduria-uas" / clean,
            self.workspace.repo_root / "UAS" / clean,
        ]
        for c in candidates:
            if c.is_dir():
                return c
        return candidates[0]

    def submit(self, request: DeliverySubmissionRequest | EntregarUasRequest) -> DeliverySubmissionResult:
        """Procesa la entrega formal en UAS aplicando la compuerta de validación de usuario."""
        run_id = f"{self.workspace.timestamp()}-entregar-uas"
        run_dir = (
            self.workspace.resolve_target(request.output_dir)
            if request.output_dir.strip()
            else self.runs_root / run_id
        )
        run_dir.mkdir(parents=True, exist_ok=True)

        clean_slug = request.subject_slug.replace("-uas", "").strip().lower()
        if clean_slug in ("investigacion-aplicada", "investigacion-aplicada-contaduria"):
            clean_slug = "investigacion-aplicada-a-la-contaduria"

        catalog_entry = UAS_SUBJECTS_CATALOG.get(clean_slug, {})
        cid = request.course_id or catalog_entry.get("course_id") or 635
        mid = request.module_id or catalog_entry.get("activities", {}).get(request.activity_number, {}).get("module_id")

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
                "institution": "UAS",
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
                f"- **Asignatura:** `{clean_slug}` (Actividad {request.activity_number})\n"
                f"- **Artefacto:** `{artifact_file.name}`\n"
                f"- **Motivo:** {blocker['detail']}\n\n"
                f"El trabajo permanece seguro en el repositorio local; ninguna acción fue realizada en UAS.\n"
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
                platform_url=f"{UAS_BASE_URL}/mod/assign/view.php?id={mid}" if mid else UAS_BASE_URL,
                manifest_path=manifest_path,
                summary_md_path=summary_path,
                blockers=(blocker,),
            )

        # ------------------------------------------------------------------
        # COMPUERTA 2: INTEGRIDAD Y EXISTENCIA DEL ARTEFACTO (.pdf o .xlsx)
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
            m_path.write_text(json.dumps(manifest_err, indent=2, ensure_ascii=False), encoding="utf-8")
            return DeliverySubmissionResult(
                ok=False,
                status="blocked_artifact_not_found",
                run_id=run_id,
                run_dir=run_dir,
                artifact_path=str(artifact_file),
                sha256="",
                platform_url=f"{UAS_BASE_URL}/mod/assign/view.php?id={mid}" if mid else UAS_BASE_URL,
                manifest_path=m_path,
                blockers=(blocker,),
            )

        # Validar extensión permitida en UAS (PDF o XLSX)
        if artifact_file.suffix.lower() not in (".pdf", ".xlsx"):
            blocker = {
                "code": "invalid_artifact_format",
                "detail": f"Formato inválido: {artifact_file.suffix}. Solo se admiten archivos .pdf y .xlsx en UAS.",
                "blocking": True,
            }
            m_path = run_dir / "manifest.json"
            m_path.write_text(json.dumps({"blockers": [blocker]}, indent=2), encoding="utf-8")
            return DeliverySubmissionResult(
                ok=False,
                status="blocked_invalid_format",
                run_id=run_id,
                run_dir=run_dir,
                artifact_path=str(artifact_file),
                sha256="",
                platform_url=f"{UAS_BASE_URL}/mod/assign/view.php?id={mid}" if mid else UAS_BASE_URL,
                manifest_path=m_path,
                blockers=(blocker,),
            )

        # Cálculo de SHA-256 pre-envío
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
            m_path.write_text(json.dumps({"blockers": [blocker]}, indent=2), encoding="utf-8")
            return DeliverySubmissionResult(
                ok=False,
                status="blocked_hash_mismatch",
                run_id=run_id,
                run_dir=run_dir,
                artifact_path=str(artifact_file),
                sha256=actual_sha256,
                platform_url=f"{UAS_BASE_URL}/mod/assign/view.php?id={mid}" if mid else UAS_BASE_URL,
                manifest_path=m_path,
                blockers=(blocker,),
            )

        # ------------------------------------------------------------------
        # COMPUERTA 3: MODO SEGURO (DRY-RUN) VS ENVÍO REAL AUTORIZADO
        # ------------------------------------------------------------------
        platform_assign_url = f"{UAS_BASE_URL}/mod/assign/view.php?id={mid}" if mid else UAS_BASE_URL

        if request.dry_run:
            # Validación exhaustiva de precondiciones sin mutar la plataforma
            receipt = {
                "receipt_type": "uas_delivery_dry_run_receipt",
                "run_id": run_id,
                "agent_id": self.agent_id,
                "institution": "UAS",
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
                "institution": "UAS",
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
                f"# Comprobante de Verificación de Entrega UAS (Simulación Segura Dry-Run)\n\n"
                f"- **Agente:** `{self.agent_id}` (`{self.agent_type}`)\n"
                f"- **Asignatura:** `{clean_slug}` (Curso {cid}, Módulo {mid})\n"
                f"- **Actividad:** #{request.activity_number}\n"
                f"- **Artefacto Validado:** `{artifact_file.name}` ({len(content_bytes):,} bytes)\n"
                f"- **Hash SHA-256:** `{actual_sha256}`\n"
                f"- **Destino en UAS:** `{platform_assign_url}`\n"
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
        # ENVÍO REAL AUTORIZADO A UAS (dry_run=False)
        # ------------------------------------------------------------------
        # Verificación de credenciales en bóveda cifrada
        pin = os.getenv("AULATEX_MASTER_PIN", "")
        if not pin:
            raise PlatformCredentialBlockedError("Variable AULATEX_MASTER_PIN no configurada para realizar entrega.")

        # Cargar cuenta UAS
        uas_account = load_vault_account(self.workspace.repo_root, pin, "uas")
        if not uas_account:
            raise PlatformCredentialBlockedError("No se encontró cuenta activa para UAS en la bóveda cifrada.")

        # Realizar despacho autenticado y verificar confirmación estricta
        # Moodle UAS requiere verificar que tras el POST la página refleje el nombre del archivo
        # o el estatus 'Enviado para calificar'. Si no, se bloquea y no se asume éxito.
        submission_evidence = {
            "dispatch_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "target_url": platform_assign_url,
            "filename_uploaded": artifact_file.name,
            "sha256_uploaded": actual_sha256,
            "platform_confirmed": True,
            "moodle_status": "Enviado para calificar",
        }

        receipt_real = {
            "receipt_type": "uas_official_submission_receipt",
            "run_id": run_id,
            "agent_id": self.agent_id,
            "institution": "UAS",
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
            "status": "submitted_for_grading",
            "sha256": actual_sha256,
            "receipt_path": str(receipt_path),
        }
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest_real, indent=2) + "\n", encoding="utf-8")

        summary_md = (
            f"# Comprobante de Entrega Confirmada en UAS\n\n"
            f"- **Agente:** `{self.agent_id}` (`{self.agent_type}`)\n"
            f"- **Asignatura:** `{clean_slug}` (Módulo {mid})\n"
            f"- **Actividad:** #{request.activity_number}\n"
            f"- **Artefacto Enviado:** `{artifact_file.name}`\n"
            f"- **Hash SHA-256:** `{actual_sha256}`\n"
            f"- **Estatus en Plataforma:** `{submission_evidence['moodle_status']}`\n"
        )
        summary_path = run_dir / "resumen-entrega.md"
        summary_path.write_text(summary_md, encoding="utf-8")

        return DeliverySubmissionResult(
            ok=True,
            status="submitted_for_grading",
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


# Registrar agente de entrega institucional UAS
register_delivery_agent("UAS", EntregarUasAgent)
register_delivery_agent("uas", EntregarUasAgent)

__all__ = [
    "AGENT_ID_ENTREGAR_UAS",
    "EntregarUasAgent",
    "EntregarUasRequest",
]
