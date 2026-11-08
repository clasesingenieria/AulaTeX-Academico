"""Agente ``realizar-planeación`` para el flujo académico UAS en AulaTeX.

Genera la planeación canónica (par JSON + Markdown) a partir de la información
obtenida de la plataforma virtual UAS (virtual.uas.edu.mx/fca), respetando los
esquemas institucionales y los contratos de layout sin exponer credenciales.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .planning_layout import _reject_credentials, subject_layout
from .workspace import AulaTeXWorkspace

SCHEMA_VERSION_UAS = "1.0-uas-planeacion"
AGENT_ID_REALIZAR_PLANEACION = "realizar-planeación"


@dataclass(frozen=True)
class PlaneacionUasRequest:
    subject_dir: str | Path
    module_data: dict[str, Any]
    course_id: int = 632
    course_name_literal: str = "2026_I_Derecho mercantil_LCP"
    subject_name: str = "Derecho mercantil"
    program_name: str = "Licenciatura en Contaduría Pública"
    week: int = 1
    topic: str = ""
    override_activity_id: int | None = None
    output_dir: str = ""


@dataclass(frozen=True)
class PlaneacionUasResult:
    activity_id: int
    title: str
    json_path: Path
    markdown_path: Path
    plan_dict: dict[str, Any]
    sha256: str
    ok: bool = True
    errors: tuple[str, ...] = field(default_factory=tuple)


class RealizarPlaneacionUasAgent:
    """Agente que estructura la planeación pedagógica canónica a partir de la evidencia de UAS."""

    agent_id: str = AGENT_ID_REALIZAR_PLANEACION

    def __init__(self, workspace: AulaTeXWorkspace | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()

    def plan(self, request: PlaneacionUasRequest) -> PlaneacionUasResult:
        subject_dir = Path(request.subject_dir).resolve()
        layout = subject_layout(subject_dir)
        plans_dir = (
            Path(request.output_dir).resolve()
            if request.output_dir
            else layout["plans"]
        )
        plans_dir.mkdir(parents=True, exist_ok=True)

        mod = request.module_data
        act_id = request.override_activity_id or mod.get("module_id") or 0
        if not act_id:
            raise ValueError("Identificador de módulo no válido para realizar la planeación.")

        title = mod.get("title") or f"Actividad Módulo {act_id}"
        kind = mod.get("kind") or "assign"
        raw_consigna = mod.get("raw_consigna") or ""
        deadline = mod.get("deadline") or "Por confirmar en plataforma"
        topic = request.topic or self._infer_topic(title, raw_consigna)

        # Requisitos formateados
        requirements = self._split_requirements(raw_consigna)

        # Fuentes registradas
        sources = [
            {
                "id": str(act_id),
                "title": title,
                "url": mod.get("url") or f"https://virtual.uas.edu.mx/fca/mod/{kind}/view.php?id={act_id}",
                "locator": "Consigna visible del módulo en plataforma UAS",
                "consulted_on": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            }
        ]

        # Recursos semanales asociados
        weekly_resources = mod.get("weekly_resources") or []

        # Objetivo propuesto
        proposed_objective = (
            f"Desarrollar y fundamentar analíticamente los contenidos de {topic} "
            f"conforme a los requerimientos de {title} en {request.subject_name}."
        )

        # Secuencia propuesta
        proposed_sequence = [
            "Revisar la consigna oficial y cotejar con la guía didáctica semanal de UAS.",
            f"Localizar y descargar los recursos bibliográficos correspondientes a {topic}.",
            "Extraer los conceptos normativos, doctrinales y metodológicos clave en notas de estudio.",
            "Desarrollar el producto académico exigido utilizando la plantilla institucional UAS.",
            "Ejecutar ciclo de revisión editorial con estilo-escribir y compilar a PDF.",
        ]

        # Criterios de revisión propuestos
        proposed_review_criteria = [
            "El documento cubre exhaustivamente los aspectos y subtemas exigidos en la consigna.",
            "Cumple con la estructura de portada oficial UAS, introducción, desarrollo, conclusiones y referencias.",
            "Citas y bibliografía formal en formato APA 7ma edición sustentadas en fuentes verificables.",
            "Compilación LaTeX sin advertencias críticas ni desbordamientos; archivo menor a 2MB.",
            "Inclusión de nota ética transparente sobre asistencia de IA según directrices de la UAS.",
        ]

        # Estructura del plan canónico
        plan_dict: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION_UAS,
            "consulted_on": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "institution": "UAS",
            "program": request.program_name,
            "subject": request.subject_name,
            "course_id": request.course_id,
            "course_name_literal": request.course_name_literal,
            "course_url": f"https://virtual.uas.edu.mx/fca/course/view.php?id={request.course_id}",
            "scope": "Consignas verificadas y propuestas de planeación; no resolución, entrega ni validación docente.",
            "activity": {
                "id": act_id,
                "title": title,
                "type": kind,
                "week": request.week,
                "topic": topic,
                "requirements": requirements,
                "calendar": {
                    "literal": mod.get("submission_status") or f"Fecha de entrega: {deadline}",
                    "deadline": deadline,
                    "timezone": "America/Mazatlan",
                    "status_on_consultation": "Actividad planificada",
                },
                "sources": sources,
                "weekly_resources": weekly_resources,
                "proposed_objective": proposed_objective,
                "proposed_sequence": proposed_sequence,
                "proposed_review_criteria": proposed_review_criteria,
                "pending": [
                    "Confirmar datos de asesor docente y grupo oficial para la carátula.",
                    "Verificar vigencia del buzón antes del envío formal.",
                ],
            },
            "artifact_contract": {
                "version": "1.0",
                "academic_materials_versioned": True,
                "paths_relative_to_subject": {
                    key: path.relative_to(subject_dir).as_posix()
                    for key, path in layout.items()
                },
                "deliverables_directory": layout["deliveries"].relative_to(subject_dir).as_posix(),
                "mode": "planeacion_canonica_uas",
            },
        }

        # Rechazar cualquier fuga de credenciales en el objeto
        _reject_credentials(plan_dict)

        # Escribir par canónico JSON + MD
        json_path = plans_dir / f"planeacion-modulo-{act_id}.json"
        json_content = json.dumps(plan_dict, ensure_ascii=False, indent=2) + "\n"
        json_path.write_text(json_content, encoding="utf-8")

        md_path = plans_dir / f"planeacion-modulo-{act_id}.md"
        md_content = self._render_markdown(plan_dict)
        md_path.write_text(md_content, encoding="utf-8")

        sha = hashlib.sha256(json_content.encode("utf-8")).hexdigest()

        return PlaneacionUasResult(
            activity_id=act_id,
            title=title,
            json_path=json_path,
            markdown_path=md_path,
            plan_dict=plan_dict,
            sha256=sha,
            ok=True,
        )

    def _infer_topic(self, title: str, consigna: str) -> str:
        clean_title = re.sub(r"(?i)^(?:actividad|tarea|módulo|diagrama|foro|unidad|semana)\s*[\d_:-]*\s*", "", title).strip()
        if clean_title:
            return clean_title
        first_line = consigna.split("\n", 1)[0].strip()
        return first_line[:80] if first_line else "Contenido temático de la actividad"

    def _split_requirements(self, text: str) -> list[str]:
        if not text.strip():
            return ["Consultar instrucciones oficiales publicadas en el aula virtual."]
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return paragraphs if paragraphs else [text.strip()]

    def _render_markdown(self, plan: dict[str, Any]) -> str:
        act = plan["activity"]
        lines = [
            f"# Planeación Pedagógica UAS: {act['title']}",
            "",
            f"**Materia:** {plan['subject']} ({plan['course_name_literal']})  ",
            f"**Semana / Módulo:** Semana {act['week']} | ID Módulo: `{act['id']}`  ",
            f"**Fecha límite registrada:** {act['calendar']['deadline']}  ",
            "",
            "## Objetivo Académico Propuesto",
            f"{act['proposed_objective']}",
            "",
            "## Requisitos y Consigna Extraída",
        ]
        for req in act["requirements"]:
            lines.append(f"- {req}")
        lines.extend([
            "",
            "## Secuencia de Realización",
        ])
        for idx, step in enumerate(act["proposed_sequence"], 1):
            lines.append(f"{idx}. {step}")
        lines.extend([
            "",
            "## Criterios de Evaluación y Calidad Editorial",
        ])
        for crit in act["proposed_review_criteria"]:
            lines.append(f"- [ ] {crit}")
        lines.extend([
            "",
            "## Pendientes de Verificación",
        ])
        for pend in act["pending"]:
            lines.append(f"- [!] {pend}")
        lines.append("")
        return "\n".join(lines)


__all__ = [
    "AGENT_ID_REALIZAR_PLANEACION",
    "PlaneacionUasRequest",
    "PlaneacionUasResult",
    "RealizarPlaneacionUasAgent",
    "SCHEMA_VERSION_UAS",
]
