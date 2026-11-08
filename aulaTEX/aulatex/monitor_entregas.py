"""Contrato base del tipo de agente ``monitor-entregas`` en AulaTeX.

Define la interfaz canónica para supervisar el estado de entregas académicas,
identificar actividades pendientes de entrega en plataformas virtuales (ej. Moodle UnADM),
evaluar requisitos satisfechos frente a bloqueos detectados y emitir recomendaciones
fundamentadas al orquestador ``aulatex`` para la realización y preparación de actividades.

Garantiza aislamiento estricto de credenciales y ausencia total de fugas de secretos.
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

AGENT_TYPE_MONITOR_ENTREGAS = "monitor-entregas"


@dataclass(frozen=True)
class PendingDeliveryItem:
    """Información estructurada de una actividad y su estado de entrega."""

    institution: str
    subject_slug: str
    activity_number: int
    activity_title: str
    module_id: int | None = None
    course_id: int | None = None
    platform_status: str = "sin_inspeccion_remota"  # "Aún no se ha hecho ninguna tarea", "Borrador (no enviado)", "Enviado para calificar", etc.
    due_date: str | None = None
    cutoff_date: str | None = None
    local_planning_ready: bool = False
    local_resources_ready: bool = False
    local_concepts_ready: bool = False
    local_deliverable_ready: bool = False
    local_deliverable_path: str | None = None
    local_deliverable_sha256: str | None = None
    satisfied_requirements: tuple[str, ...] = ()
    detected_blockers: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class DeliveryRecommendation:
    """Recomendación técnica emitida por el monitor hacia el orquestador aulatex."""

    institution: str
    subject_slug: str
    activity_number: int
    recommended_action: str  # "solicitar-realizar-actividad", "esperar-autorizacion-entrega", "ya_entregado", "bloqueado_falta_prerrequisitos"
    prerequisites_satisfied: tuple[str, ...]
    blockers: tuple[dict[str, Any], ...]
    rationale: str
    proposed_delivery_artifact: str | None = None
    proposed_delivery_sha256: str | None = None
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True)
class PendingSubmissionsReport:
    """Informe consolidado de monitoreo de entregas institucionales."""

    run_id: str
    run_dir: Path
    institution: str
    timestamp_utc: str
    pending_deliveries: tuple[PendingDeliveryItem, ...]
    recommendations: tuple[DeliveryRecommendation, ...]
    blockers: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    manifest_path: Path | None = None
    summary_md_path: Path | None = None

    @property
    def ok(self) -> bool:
        return not any(b.get("blocking", False) for b in self.blockers)


class MonitorEntregasAgent(ABC):
    """Clase base abstracta para agentes especializados del tipo ``monitor-entregas``."""

    agent_type: str = AGENT_TYPE_MONITOR_ENTREGAS

    def __init__(self, workspace: AulaTeXWorkspace | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Identificador canónico del agente monitor (ej. 'monitor-unadm')."""

    @abstractmethod
    def evaluate_activity(
        self,
        subject_slug: str,
        activity_number: int,
        **kwargs: Any,
    ) -> DeliveryRecommendation:
        """Evalúa una actividad específica y emite recomendación técnica a aulatex."""

    @abstractmethod
    def monitor_deliveries(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> PendingSubmissionsReport:
        """Genera el informe general de entregas pendientes para una asignatura o programa."""


# ---------------------------------------------------------------------------
# Registro Institucional de Monitores de Entregas
# ---------------------------------------------------------------------------
_DELIVERY_MONITORS: dict[str, type[MonitorEntregasAgent]] = {}


def register_delivery_monitor(institution: str, monitor_cls: type[MonitorEntregasAgent]) -> None:
    """Registra una clase de agente monitor para una institución dada."""
    if not issubclass(monitor_cls, MonitorEntregasAgent):
        raise TypeError(f"La clase {monitor_cls} debe heredar de MonitorEntregasAgent.")
    _DELIVERY_MONITORS[institution.casefold().strip()] = monitor_cls


def get_delivery_monitor_class(institution: str) -> type[MonitorEntregasAgent] | None:
    """Obtiene la clase de monitor registrada para la institución."""
    return _DELIVERY_MONITORS.get(institution.casefold().strip())


def get_delivery_monitor(
    institution: str,
    workspace: AulaTeXWorkspace | None = None,
    **kwargs: Any,
) -> MonitorEntregasAgent:
    """Instancia el agente monitor registrado para la institución."""
    cls = get_delivery_monitor_class(institution)
    if cls is None:
        raise ValueError(f"No hay monitor de entregas registrado para la institución '{institution}'.")
    return cls(workspace=workspace, **kwargs)


__all__ = [
    "AGENT_TYPE_MONITOR_ENTREGAS",
    "DeliveryRecommendation",
    "MonitorEntregasAgent",
    "PendingDeliveryItem",
    "PendingSubmissionsReport",
    "get_delivery_monitor",
    "get_delivery_monitor_class",
    "register_delivery_monitor",
]
