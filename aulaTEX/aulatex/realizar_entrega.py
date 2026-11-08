"""Contrato base del tipo de agente ``realizar-entrega`` en AulaTeX.

Define la interfaz canónica y las compuertas de seguridad para el envío formal
de artefactos académicos (PDFs de entrega) a plataformas virtuales institucionales.

Principio fundamental de seguridad y soberanía del usuario:
"Autorizar la realización de una actividad no equivale a autorizar su envío."
Ninguna acción mutante ni envío a plataforma puede ejecutarse sin la validación
explícita del usuario para esa actividad y artefacto específico (`user_validated=True`).

Garantiza aislamiento de credenciales con PlatformCredentialVault y ausencia
total de exposición de contraseñas, PINs o tokens en registros y artefactos.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .navegacion_plataforma import assert_no_credential_leak
from .workspace import AulaTeXWorkspace

AGENT_TYPE_REALIZAR_ENTREGA = "realizar-entrega"


class DeliveryError(RuntimeError):
    """Error base de entrega de actividades académicas."""


class DeliveryValidationError(DeliveryError):
    """Bloqueo estricto cuando falta la validación explícita del usuario para el artefacto."""


class DeliveryGateBlockedError(DeliveryError):
    """Bloqueo por integridad (hash no coincide, archivo ausente o estado en plataforma incompatible)."""


@dataclass(frozen=True)
class DeliverySubmissionRequest:
    """Solicitud de entrega formal a plataforma."""

    institution: str
    subject_slug: str
    activity_number: int
    artifact_path: str | Path
    expected_sha256: str | None = None
    user_validated: bool = False  # Compuerta de seguridad: DEBE ser True para permitir el envío
    user_confirmation: str = ""
    course_id: int | None = None
    module_id: int | None = None
    dry_run: bool = True  # Modo seguro por omisión: valida requisitos sin alterar la plataforma
    finalize: bool = False  # True para 'Enviar para calificar', False para borrador
    output_dir: str = ""


@dataclass(frozen=True)
class DeliverySubmissionResult:
    """Resultado estructurado de la operación de entrega."""

    ok: bool
    status: str  # "submitted_for_grading", "draft_saved", "dry_run_validated", "blocked_missing_user_validation", "blocked_hash_mismatch", etc.
    run_id: str
    run_dir: Path
    artifact_path: str
    sha256: str
    platform_url: str
    receipt_path: Path | None = None
    manifest_path: Path | None = None
    summary_md_path: Path | None = None
    platform_evidence: dict[str, Any] = field(default_factory=dict)
    blockers: tuple[dict[str, Any], ...] = field(default_factory=tuple)


class RealizarEntregaAgent(ABC):
    """Clase base abstracta para agentes del tipo ``realizar-entrega``."""

    agent_type: str = AGENT_TYPE_REALIZAR_ENTREGA

    def __init__(self, workspace: AulaTeXWorkspace | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Identificador canónico del agente de entrega (ej. 'entregar-unadm')."""

    @abstractmethod
    def submit(self, request: DeliverySubmissionRequest) -> DeliverySubmissionResult:
        """Procesa la entrega verificando validación de usuario e integridad del artefacto."""


# ---------------------------------------------------------------------------
# Registro Institucional de Agentes de Entrega
# ---------------------------------------------------------------------------
_DELIVERY_AGENTS: dict[str, type[RealizarEntregaAgent]] = {}


def register_delivery_agent(institution: str, agent_cls: type[RealizarEntregaAgent]) -> None:
    """Registra una clase de agente de entrega para una institución dada."""
    if not issubclass(agent_cls, RealizarEntregaAgent):
        raise TypeError(f"La clase {agent_cls} debe heredar de RealizarEntregaAgent.")
    _DELIVERY_AGENTS[institution.casefold().strip()] = agent_cls


def get_delivery_agent_class(institution: str) -> type[RealizarEntregaAgent] | None:
    """Obtiene la clase de agente de entrega registrada para la institución."""
    return _DELIVERY_AGENTS.get(institution.casefold().strip())


def get_delivery_agent(
    institution: str,
    workspace: AulaTeXWorkspace | None = None,
    **kwargs: Any,
) -> RealizarEntregaAgent:
    """Instancia el agente de entrega registrado para la institución."""
    cls = get_delivery_agent_class(institution)
    if cls is None:
        raise ValueError(f"No hay agente de entrega registrado para la institución '{institution}'.")
    return cls(workspace=workspace, **kwargs)


__all__ = [
    "AGENT_TYPE_REALIZAR_ENTREGA",
    "DeliveryError",
    "DeliveryGateBlockedError",
    "DeliverySubmissionRequest",
    "DeliverySubmissionResult",
    "DeliveryValidationError",
    "RealizarEntregaAgent",
    "get_delivery_agent",
    "get_delivery_agent_class",
    "register_delivery_agent",
]
