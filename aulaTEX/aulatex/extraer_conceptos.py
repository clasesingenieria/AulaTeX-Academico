"""Agente ``extraer-conceptos`` integrado al flujo académico ITESCA de AulaTeX.

Procesa los recursos organizados por ``encontrar-recursos`` y la planeación de
``realizar-planeación`` para generar los conceptos en la carpeta de notas
correspondiente a cada actividad (``referencias-<slug>/notas-<slug>/<actividad>/conceptos/``),
sincronizándolos además con ``extractor-aulatex/conceptos-<slug>-actividad-<N>/``
para compatibilidad plena con ``ActivityObserver`` y ``ActivityOptimizer``.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
from typing import Any

from .extractor_adapter import CORE_EXTRACTOR_ARTIFACTS, ExtractorAdapter, ExtractorRequest
from .mcp_lex import McpLexClient, get_lex_client
from .navegacion_plataforma import assert_no_credential_leak
from .planning_layout import subject_layout
from .workspace import AulaTeXWorkspace

AGENT_ID_EXTRAER_CONCEPTOS = "extraer-conceptos"


@dataclass(frozen=True)
class ExtraerConceptosRequest:
    target: str
    activity_number: int
    plan_json_path: str | Path = ""
    motors: tuple[str, ...] = ("novapro", "tfidf")
    top_k: int = 10
    max_citas: int = 6
    force_rerun: bool = False
    timeout_seconds: int = 600


@dataclass(frozen=True)
class ExtraerConceptosResult:
    agent_id: str
    activity_number: int
    subject_root: Path
    notes_concepts_dir: Path
    synced_extractor_dir: Path
    selected_motor: str
    ok: bool
    concepts_count: int
    artifacts: tuple[str, ...]


def _core_artifacts_complete(folder: Path) -> bool:
    if not folder.is_dir():
        return False
    return all((folder / fname).is_file() and (folder / fname).stat().st_size > 2 for fname in CORE_EXTRACTOR_ARTIFACTS.values())


class ExtraerConceptosAgent:
    """Agente ``extraer-conceptos`` que materializa conceptos en notas de actividad."""

    agent_id: str = AGENT_ID_EXTRAER_CONCEPTOS

    def __init__(
        self,
        workspace: AulaTeXWorkspace | None = None,
        adapter: ExtractorAdapter | None = None,
        lex_client: McpLexClient | None = None,
    ) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.lex_client = lex_client or get_lex_client()
        self.adapter = adapter or ExtractorAdapter(self.workspace)

    def run(self, request: ExtraerConceptosRequest) -> ExtraerConceptosResult:
        subject_root = self.workspace.resolve_target(request.target)
        layout = subject_layout(subject_root)
        slug = subject_root.name
        for suffix in ("-mga", "-lde", "-lae", "-iias"):
            if slug.endswith(suffix):
                slug = slug[: -len(suffix)]
                break

        plan_path = (
            Path(request.plan_json_path).resolve()
            if str(request.plan_json_path).strip()
            else layout["plans"] / f"planeacion-{slug}-Actividad-{int(request.activity_number)}.json"
        )
        if not plan_path.is_file():
            raise FileNotFoundError(f"Planeación requerida no encontrada para extraer-conceptos: {plan_path}")

        plan_doc = json.loads(plan_path.read_text(encoding="utf-8-sig"))
        act = plan_doc["activities"][0]
        notes_rel = act["bindings"].get("notes_directory")
        if not notes_rel:
            raise ValueError("La planeación no define bindings.notes_directory.")
        notes_dir = (subject_root / notes_rel).resolve()

        resources_manifest_path = notes_dir / "recursos-actividad.json"
        if not resources_manifest_path.is_file():
            raise FileNotFoundError(
                f"Manifiesto de recursos requerido no encontrado ({resources_manifest_path}); "
                "ejecuta primero encontrar-recursos."
            )

        focalizado_dir = notes_dir / "corpus-extractor-focalizado"
        corpus_dir = focalizado_dir if focalizado_dir.is_dir() and any(focalizado_dir.glob("*.txt")) else (notes_dir / "corpus-extractor")
        if not corpus_dir.is_dir() or not any(corpus_dir.glob("*.txt")):
            raise ValueError(f"No hay archivos .txt de entrada en {corpus_dir} para extraer-conceptos.")

        extractor_plan_md = notes_dir / f"planeacion-actividad-{int(request.activity_number)}-extractor.md"
        if not extractor_plan_md.is_file():
            extractor_plan_md = layout["plans"] / f"planeacion-{slug}-Actividad-{int(request.activity_number)}.md"

        seed_candidates = sorted(notes_dir.glob("conceptos-semilla*.txt"))
        seed_path = str(seed_candidates[0].resolve()) if seed_candidates else ""

        notes_concepts_dir = notes_dir / "conceptos"
        notes_concepts_dir.mkdir(parents=True, exist_ok=True)
        synced_extractor_dir = subject_root / "extractor-aulatex" / f"conceptos-{slug}-actividad-{int(request.activity_number)}"
        synced_extractor_dir.mkdir(parents=True, exist_ok=True)

        selected_motor = "cached"
        ok = False
        if not request.force_rerun and _core_artifacts_complete(notes_concepts_dir):
            ok = True
        else:
            for motor in request.motors:
                attempt = self.adapter.run(
                    ExtractorRequest(
                        target=str(subject_root),
                        activity_number=int(request.activity_number),
                        fuentes=str(corpus_dir),
                        planeacion=str(extractor_plan_md) if extractor_plan_md.is_file() else "",
                        conceptos=seed_path,
                        salida=str(notes_concepts_dir),
                        motor=motor,
                        recursive=True,
                        top_k=request.top_k,
                        max_citas=request.max_citas,
                        timeout_seconds=request.timeout_seconds,
                    )
                )
                if attempt.ok and _core_artifacts_complete(notes_concepts_dir):
                    selected_motor = motor
                    ok = True
                    break

        if not ok:
            raise RuntimeError(
                f"extraer-conceptos no logró materializar los artefactos nucleares en {notes_concepts_dir}"
            )

        # Verificar ausencia de credenciales y sincronizar hacia extractor-aulatex/conceptos-<slug>-actividad-<N>/
        artifacts_written: list[str] = []
        for fpath in sorted(notes_concepts_dir.iterdir()):
            if not fpath.is_file():
                continue
            if fpath.suffix.lower() in {".json", ".md", ".txt"}:
                assert_no_credential_leak(fpath.read_text(encoding="utf-8", errors="replace"))
            shutil.copy2(fpath, synced_extractor_dir / fpath.name)
            artifacts_written.append(fpath.relative_to(subject_root).as_posix())

        fichas_payload: Any = json.loads((notes_concepts_dir / "fichas_conceptos.json").read_text(encoding="utf-8"))
        if isinstance(fichas_payload, dict):
            concepts_list = fichas_payload.get("fichas") or fichas_payload.get("concepts") or []
        elif isinstance(fichas_payload, list):
            concepts_list = fichas_payload
        else:
            concepts_list = []

        return ExtraerConceptosResult(
            agent_id=self.agent_id,
            activity_number=int(request.activity_number),
            subject_root=subject_root,
            notes_concepts_dir=notes_concepts_dir,
            synced_extractor_dir=synced_extractor_dir,
            selected_motor=selected_motor,
            ok=True,
            concepts_count=len(concepts_list),
            artifacts=tuple(artifacts_written),
        )


__all__ = [
    "AGENT_ID_EXTRAER_CONCEPTOS",
    "ExtraerConceptosAgent",
    "ExtraerConceptosRequest",
    "ExtraerConceptosResult",
]
