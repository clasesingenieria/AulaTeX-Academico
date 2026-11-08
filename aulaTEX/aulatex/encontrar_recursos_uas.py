"""Agente ``encontrar-recursos`` para el flujo académico UAS en AulaTeX.

Localiza, descarga de forma segura y organiza los recursos documentales
y bibliográficos necesarios para las actividades definidas en la planeación,
computando hashes SHA-256 y actualizando las fuentes de la materia.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import unquote, urlsplit

from .navegacion_uas import DownloadedUasFile, NavegacionUasAgent, UasNavigationRequest, UasModuleTarget
from .planning_layout import _reject_credentials, subject_layout
from .workspace import AulaTeXWorkspace

AGENT_ID_ENCONTRAR_RECURSOS = "encontrar-recursos"


@dataclass(frozen=True)
class RecursoOrganizado:
    id: str
    title: str
    url: str
    local_path: str
    sha256: str
    size_bytes: int
    mime: str
    bib_key: str | None = None


@dataclass(frozen=True)
class EncontrarRecursosRequest:
    subject_dir: str | Path
    activity_plan: dict[str, Any]
    download_online: bool = True
    output_dir: str = ""


@dataclass(frozen=True)
class EncontrarRecursosResult:
    total_found: int
    total_downloaded: int
    resources: tuple[RecursoOrganizado, ...]
    inventory_json: Path
    bib_file: Path | None
    missing_resources: tuple[str, ...] = field(default_factory=tuple)
    ok: bool = True


class EncontrarRecursosUasAgent:
    """Agente para localizar, descargar y estructurar recursos académicos de UAS."""

    agent_id: str = AGENT_ID_ENCONTRAR_RECURSOS

    def __init__(self, workspace: AulaTeXWorkspace | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()

    def find_and_organize(
        self, request: EncontrarRecursosRequest, nav_agent: NavegacionUasAgent | None = None
    ) -> EncontrarRecursosResult:
        subject_dir = Path(request.subject_dir).resolve()
        layout = subject_layout(subject_dir)
        ref_dir = layout["references"]
        ref_dir.mkdir(parents=True, exist_ok=True)

        plan = request.activity_plan
        act = plan.get("activity", {})
        act_id = act.get("id", 0)
        week = act.get("week", 1)
        topic_slug = re.sub(r"[^a-zA-Z0-9-]", "", re.sub(r"\s+", "-", act.get("topic", f"semana-{week}").lower()))[:30]

        target_materials_dir = (
            Path(request.output_dir).resolve()
            if request.output_dir
            else ref_dir / "materiales-aula" / f"semana-{week:02d}-{topic_slug}"
        )
        target_materials_dir.mkdir(parents=True, exist_ok=True)

        weekly_resources = act.get("weekly_resources", [])
        sources = act.get("sources", [])
        candidates = list(weekly_resources) + list(sources)

        organized_items: list[RecursoOrganizado] = []
        missing: list[str] = []

        # 1. Escaneo de archivos ya presentes en local
        existing_files = list(target_materials_dir.glob("*")) + list(ref_dir.glob("*.pdf"))
        existing_by_name = {f.name.lower(): f for f in existing_files if f.is_file()}

        # 2. Descarga desde UAS si se requiere y está habilitada
        if request.download_online and candidates:
            navigator = nav_agent or NavegacionUasAgent(self.workspace)
            # Extraer IDs de módulos para inspeccionar y descargar adjuntos
            module_targets = []
            for item in candidates:
                item_url = item.get("url", "")
                parsed = urlsplit(item_url)
                match = re.search(r"[?&]id=(\d+)", parsed.query)
                if match:
                    mid = int(match.group(1))
                    kind = "resource" if "/mod/resource/" in parsed.path else ("page" if "/mod/page/" in parsed.path else "assign")
                    module_targets.append(UasModuleTarget(module_id=mid, kind=kind))

            if module_targets:
                try:
                    nav_req = UasNavigationRequest(
                        inspect_dashboard=False,
                        course_ids=(),
                        modules=tuple(module_targets),
                        output_dir=str(target_materials_dir / ".nav_temp"),
                        download_resources=True,
                    )
                    nav_res = navigator.inspect(nav_req)
                    for dl in nav_res.downloaded_files:
                        src_path = Path(dl.saved_path)
                        final_path = target_materials_dir / dl.filename
                        if src_path.exists() and not final_path.exists():
                            src_path.replace(final_path)
                        organized_items.append(
                            RecursoOrganizado(
                                id=hashlib.md5(dl.source_url.encode()).hexdigest()[:8],
                                title=dl.filename,
                                url=dl.source_url,
                                local_path=str(final_path.relative_to(subject_dir)),
                                sha256=dl.sha256,
                                size_bytes=dl.size_bytes,
                                mime=dl.mime_hint,
                                bib_key=self._generate_bib_key(dl.filename),
                            )
                        )
                except Exception as err:
                    missing.append(f"No se pudo descargar en línea ({type(err).__name__}); operando con archivos locales.")

        # 3. Incorporar los archivos existentes no descargados
        for f in target_materials_dir.glob("*"):
            if f.is_file() and not f.name.startswith(".") and f.name != "fuentes.json":
                sha = hashlib.sha256(f.read_bytes()).hexdigest()
                if not any(item.sha256 == sha for item in organized_items):
                    organized_items.append(
                        RecursoOrganizado(
                            id=hashlib.md5(f.name.encode()).hexdigest()[:8],
                            title=f.name,
                            url=f"archivo-local:{f.name}",
                            local_path=str(f.relative_to(subject_dir)),
                            sha256=sha,
                            size_bytes=f.stat().st_size,
                            mime="application/pdf" if f.suffix.lower() == ".pdf" else "application/octet-stream",
                            bib_key=self._generate_bib_key(f.name),
                        )
                    )

        # 4. Guardar fuentes.json
        inv_payload = {
            "actividad_id": act_id,
            "semana": week,
            "materia": plan.get("subject", ""),
            "actualizado_al": datetime.now(timezone.utc).isoformat(),
            "fuentes": [asdict(r) for r in organized_items],
        }
        _reject_credentials(inv_payload)
        inv_json = target_materials_dir / "fuentes.json"
        inv_json.write_text(json.dumps(inv_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        # 5. Generar o actualizar archivo .bib en referencias
        bib_file = self._update_bib_file(ref_dir, plan.get("subject", "materia"), organized_items)

        return EncontrarRecursosResult(
            total_found=len(candidates),
            total_downloaded=len(organized_items),
            resources=tuple(organized_items),
            inventory_json=inv_json,
            bib_file=bib_file,
            missing_resources=tuple(missing),
            ok=True,
        )

    def _generate_bib_key(self, filename: str) -> str:
        stem = Path(filename).stem
        clean = re.sub(r"[^a-zA-Z0-9]", "", stem)
        return f"uasRecurso{clean[:20]}"

    def _update_bib_file(
        self, ref_dir: Path, subject_name: str, resources: list[RecursoOrganizado]
    ) -> Path:
        bib_path = ref_dir / f"fuentes-aula-{datetime.now().strftime('%Y-%m-%d')}.bib"
        if not bib_path.exists():
            candidate_bibs = list(ref_dir.glob("*.bib"))
            if candidate_bibs:
                bib_path = candidate_bibs[0]

        existing_text = bib_path.read_text(encoding="utf-8", errors="replace") if bib_path.exists() else ""
        new_entries: list[str] = []

        for r in resources:
            if not r.bib_key or r.bib_key in existing_text:
                continue
            entry = (
                f"@misc{{{r.bib_key},\n"
                f"  title = {{{{{r.title}}}}},\n"
                f"  author = {{{{Universidad Autónoma de Sinaloa}}}},\n"
                f"  year = {{{datetime.now().year}}},\n"
                f"  note = {{Material didáctico y normativo de {subject_name}, plataforma virtual UAS}}\n"
                f"}}"
            )
            new_entries.append(entry)

        if new_entries:
            combined = existing_text.rstrip() + "\n\n" + "\n\n".join(new_entries) + "\n"
            bib_path.write_text(combined, encoding="utf-8")

        return bib_path


__all__ = [
    "AGENT_ID_ENCONTRAR_RECURSOS",
    "EncontrarRecursosRequest",
    "EncontrarRecursosResult",
    "EncontrarRecursosUasAgent",
    "RecursoOrganizado",
]
