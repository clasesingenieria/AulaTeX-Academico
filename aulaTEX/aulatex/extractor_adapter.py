from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import load_aulatex_env
from .workspace import AulaTeXWorkspace, EditorialScope


EXTRACTOR_MOTORS = ("tfidf", "tfhub", "azure", "openai", "anthropicfoundry")
CORE_EXTRACTOR_ARTIFACTS = {
    "fichas_json": "fichas_conceptos.json",
    "conceptos": "conceptos_detectados.json",
    "ideas": "ideas_detectadas.json",
    "trazabilidad": "trazabilidad_fuentes.json",
    "planeacion": "resumen_planeacion.json",
}


@dataclass(frozen=True)
class ExtractorRequest:
    target: str = "."
    activity_number: int = 0
    fuentes: str = ""
    planeacion: str = ""
    conceptos: str = ""
    salida: str = ""
    motor: str = "anthropicfoundry"
    recursive: bool = True
    top_k: int = 12
    max_citas: int = 8
    probe_only: bool = False
    timeout_seconds: int = 3600


@dataclass(frozen=True)
class ExtractorRunResult:
    run_id: str
    run_dir: Path
    ok: bool
    manifest_path: Path
    stdout_path: Path
    stderr_path: Path
    output_dir: Path


@dataclass(frozen=True)
class ResolvedExtractorRequest:
    scope: EditorialScope | None
    target_path: Path
    fuentes_path: Path | None
    planeacion_path: Path | None
    conceptos_path: Path | None
    output_dir: Path
    missing_inputs: tuple[str, ...]


class ExtractorAdapter:
    def __init__(self, workspace: AulaTeXWorkspace | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.extractor_root = self.workspace.scripts_dir / "extractor-conceptos-ideas"
        self.run_root = self.workspace.feedback_root / "extractor" / "runs"
        self.run_root.mkdir(parents=True, exist_ok=True)

    def preview_markdown(self, request: ExtractorRequest) -> str:
        resolved = self._resolve_request(request)
        scope = resolved.scope
        command = self._build_command(request, resolved)
        lines = ["# Preview del adaptador del extractor", ""]
        if scope is not None:
            lines.extend(
                [
                    f"- Scope: {scope.level} | {scope.key}",
                    f"- Ruta objetivo: {self.workspace.relative(resolved.target_path)}",
                ]
            )
        else:
            lines.extend(
                [
                    "- Scope: no resuelto desde el catalogo editorial.",
                    f"- Ruta objetivo: {self.workspace.relative(resolved.target_path)}",
                ]
            )
        lines.extend(
            [
                f"- Fuentes: {self._render_optional_path(resolved.fuentes_path)}",
                f"- Planeacion: {self._render_optional_path(resolved.planeacion_path)}",
                f"- Conceptos: {self._render_optional_path(resolved.conceptos_path)}",
                f"- Salida: {self.workspace.relative(resolved.output_dir)}",
                f"- Motor: {request.motor}",
                f"- Modo: {'probar-configuracion' if request.probe_only else 'ejecucion'}",
                "",
            ]
        )
        if resolved.missing_inputs:
            lines.append("## Faltantes")
            lines.append("")
            lines.extend(f"- {item}" for item in resolved.missing_inputs)
            lines.append("")
        lines.append("## Comando previsto")
        lines.append("")
        lines.append("```text")
        lines.append(" ".join(command))
        lines.append("```")
        lines.append("")
        lines.append("## Artefactos nucleares esperados")
        lines.append("")
        lines.extend(f"- {self.workspace.relative(resolved.output_dir / filename)}" for filename in CORE_EXTRACTOR_ARTIFACTS.values())
        return "\n".join(lines)

    def run(self, request: ExtractorRequest) -> ExtractorRunResult:
        load_aulatex_env(override=False)
        resolved = self._resolve_request(request)
        if resolved.missing_inputs and not request.probe_only:
            missing = ", ".join(resolved.missing_inputs)
            raise ValueError(f"No se puede ejecutar el extractor sin resolver: {missing}")

        run_id = f"{self.workspace.timestamp()}-extractor"
        run_dir = self.run_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        command = self._build_command(request, resolved)
        proc = subprocess.run(
            command,
            cwd=str(self.extractor_root),
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(30, int(request.timeout_seconds)),
        )

        stdout_path = run_dir / "stdout.txt"
        stderr_path = run_dir / "stderr.txt"
        stdout_path.write_text(proc.stdout, encoding="utf-8")
        stderr_path.write_text(proc.stderr, encoding="utf-8")

        artifacts = self._collect_artifacts(resolved.output_dir)
        missing_artifacts = sorted(name for name, present in artifacts.items() if not present)
        ok = proc.returncode == 0 and (request.probe_only or not missing_artifacts)

        manifest = {
            "run_id": run_id,
            "scope_key": resolved.scope.key if resolved.scope is not None else "",
            "target": self.workspace.relative(resolved.target_path),
            "fuentes": self._manifest_path(resolved.fuentes_path),
            "planeacion": self._manifest_path(resolved.planeacion_path),
            "conceptos": self._manifest_path(resolved.conceptos_path),
            "output_dir": self.workspace.relative(resolved.output_dir),
            "motor": request.motor,
            "probe_only": request.probe_only,
            "recursive": bool(request.recursive),
            "top_k": int(request.top_k),
            "max_citas": int(request.max_citas),
            "returncode": int(proc.returncode),
            "ok": ok,
            "missing_inputs": list(resolved.missing_inputs),
            "artifacts": {
                name: {
                    "present": present,
                    "path": self.workspace.relative(resolved.output_dir / CORE_EXTRACTOR_ARTIFACTS[name]),
                }
                for name, present in artifacts.items()
            },
            "missing_artifacts": missing_artifacts,
            "stdout_path": self.workspace.relative(stdout_path),
            "stderr_path": self.workspace.relative(stderr_path),
            "command": command,
        }
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        self.workspace.append_bitacora(run_id, "extractor", manifest)
        return ExtractorRunResult(run_id, run_dir, ok, manifest_path, stdout_path, stderr_path, resolved.output_dir)

    def _resolve_request(self, request: ExtractorRequest) -> ResolvedExtractorRequest:
        scope = self.workspace.find_scope_for_target(request.target, activity_number=request.activity_number or None)
        target_path = self.workspace.resolve_target(scope.relative_path if scope is not None else request.target)
        fuentes_path = self._resolve_optional_existing_path(request.fuentes) or self._infer_sources_path(target_path, scope)
        planeacion_path = self._resolve_optional_existing_path(request.planeacion) or self._infer_planeacion_path(target_path, scope, request.activity_number)
        conceptos_path = self._resolve_optional_existing_path(request.conceptos)
        output_dir = self._resolve_output_dir(request, target_path)

        missing_inputs: list[str] = []
        if fuentes_path is None:
            missing_inputs.append("fuentes")
        if planeacion_path is None:
            missing_inputs.append("planeacion")
        return ResolvedExtractorRequest(
            scope=scope,
            target_path=target_path,
            fuentes_path=fuentes_path,
            planeacion_path=planeacion_path,
            conceptos_path=conceptos_path,
            output_dir=output_dir,
            missing_inputs=tuple(missing_inputs),
        )

    def _resolve_optional_existing_path(self, value: str) -> Path | None:
        if not value.strip():
            return None
        candidate = self.workspace.resolve_target(value)
        return candidate if candidate.exists() else None

    def _infer_sources_path(self, target_path: Path, scope: EditorialScope | None) -> Path | None:
        candidates: list[Path] = []
        # Cuando el target es un archivo (p. ej. un reporte .tex de actividad), las
        # fuentes REALES no son el propio .tex, sino las carpetas de referencias/libros
        # de la materia. Se prioriza subir al directorio de la materia y localizar
        # 'referencias-*/libros-*', 'referencias-*', 'fuentes-*', etc.
        search_dirs: list[Path] = []
        if target_path.exists() and target_path.is_dir():
            search_dirs.append(target_path)
        if target_path.exists() and target_path.is_file():
            search_dirs.append(target_path.parent)
        for base in search_dirs:
            # 'referencias-*/libros-*' es la fuente más rica (bibliografía en PDF).
            for ref_dir in sorted(base.glob("referencias*")):
                if ref_dir.is_dir():
                    for libros in sorted(ref_dir.glob("libros*")):
                        if libros.is_dir():
                            candidates.append(libros)
                    candidates.append(ref_dir)
            for name in ("fuentes", "documentos-base", "libros", "bibliografia", "investigacion-aulatex"):
                candidates.extend(path for path in sorted(base.glob(f"{name}*")) if path.exists())
            candidates.extend(path for path in sorted(base.glob("*.bib")) if path.is_file())
        # Como último recurso, el propio archivo target (si es fuente soportada).
        if target_path.exists() and target_path.is_file():
            candidates.append(target_path)
        if scope is not None and scope.institution:
            institution_root = self.workspace.resolve_target(scope.institution)
            candidates.extend(path for path in sorted(institution_root.glob("*.bib")) if path.is_file())
        for candidate in candidates:
            if self._contains_supported_source(candidate):
                return candidate
        return None

    def _infer_planeacion_path(self, target_path: Path, scope: EditorialScope | None, activity_number: int) -> Path | None:
        candidates: list[Path] = []
        # PRIORIDAD 1: la planeacion OFICIAL de la actividad, ubicada en la carpeta de
        # la materia (p. ej. 'planeaciones-*/Planificacion de actividades SN - ...pdf').
        # Cuando el target es un .tex de reporte, NO usar el propio .tex como planeacion:
        # subir al directorio de la materia y localizar por numero de actividad/semana.
        base_dir = target_path.parent if target_path.is_file() else target_path
        if activity_number > 0 and base_dir.is_dir():
            act_pat = re.compile(rf"(actividad|semana|[\bsS])[-_\s]*0?{int(activity_number)}\b", re.IGNORECASE)
            s_pat = re.compile(rf"\bs{int(activity_number)}\b", re.IGNORECASE)
            for plan_dir in sorted(base_dir.glob("planeaciones*")):
                if plan_dir.is_dir():
                    for path in sorted(plan_dir.glob("*")):
                        if path.is_file() and path.suffix.lower() in {".pdf", ".md", ".txt", ".docx"} and (
                            act_pat.search(path.stem) or s_pat.search(path.stem)
                        ):
                            candidates.append(path)
        # PRIORIDAD 2: comportamiento previo (target archivo/dir con patrones de actividad).
        if target_path.is_file() and target_path.suffix.lower() in {".md", ".txt", ".tex", ".pdf", ".docx"}:
            # El propio target solo como ULTIMO recurso (se agrega al final).
            pass
        if target_path.is_dir():
            if activity_number > 0:
                activity_pattern = re.compile(rf"actividad[-_\s]*0?{int(activity_number)}", re.IGNORECASE)
                candidates.extend(path for path in sorted(target_path.glob("*")) if path.is_file() and activity_pattern.search(path.stem))
            for pattern in ("plan.md", "programa-analitico*.md", "planeacion*.md", "planeacion*.txt", "planeacion*.pdf", "*actividad*.md", "*actividad*.txt", "*actividad*.tex"):
                candidates.extend(path for path in sorted(target_path.glob(pattern)) if path.is_file())
        if scope is not None and scope.relative_path:
            scope_path = self.workspace.resolve_target(scope.relative_path)
            if scope_path != target_path and scope_path.is_dir():
                candidates.extend(path for path in sorted(scope_path.glob("plan.md")) if path.is_file())
        # ULTIMO recurso: el propio target si es un documento soportado.
        if target_path.is_file() and target_path.suffix.lower() in {".md", ".txt", ".tex", ".pdf", ".docx"}:
            candidates.append(target_path)
        for candidate in candidates:
            if candidate.exists() and candidate.suffix.lower() in {".md", ".txt", ".tex", ".pdf", ".docx"}:
                return candidate
        return None

    def _contains_supported_source(self, candidate: Path) -> bool:
        if candidate.is_file():
            return candidate.suffix.lower() in {".pdf", ".docx", ".txt", ".md", ".markdown", ".bib", ".tex"}
        if not candidate.is_dir():
            return False
        supported = {".pdf", ".docx", ".txt", ".md", ".markdown", ".bib", ".tex"}
        return any(path.is_file() and path.suffix.lower() in supported for path in candidate.rglob("*"))

    def _resolve_output_dir(self, request: ExtractorRequest, target_path: Path) -> Path:
        if request.salida.strip():
            resolved = self.workspace.resolve_target(request.salida)
            resolved.mkdir(parents=True, exist_ok=True)
            return resolved
        base = (target_path / "extractor-aulatex").resolve()
        # CONTRATO DE CARPETA DEL EXTRACTOR: cada ACTIVIDAD conserva su propia base
        # conceptual en una subcarpeta 'conceptos-<materia>-actividad-N', evitando que
        # una corrida sobrescriba la base de otra semana. El motor IDENTIFICA el número
        # de actividad, LOCALIZA una carpeta existente que matchee el patrón (aunque el
        # slug varíe) y, si no existe, la CREA. Coincide con el patrón del repo
        # (p. ej. 'conceptos-interaprendizaje-en-ambientes-virtuales-actividad-3').
        activity_number = int(request.activity_number or 0)
        if activity_number <= 0:
            base.mkdir(parents=True, exist_ok=True)
            return base
        target_dir = self._activity_concept_dir(base, target_path, activity_number)
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    def _activity_concept_dir(self, base: Path, target_path: Path, activity_number: int) -> Path:
        """Localiza (o define para crear) la carpeta de conceptos de la actividad.

        Prioridad: (1) reutilizar una carpeta existente 'conceptos-*-actividad-N' /
        'conceptos-*-sN' bajo extractor-aulatex; (2) si no existe, definir el nombre
        canónico 'conceptos-<materia>-actividad-N'.
        """
        materia_slug = self._materia_slug(target_path)
        canonical = base / f"conceptos-{materia_slug}-actividad-{activity_number}"
        if canonical.exists():
            return canonical.resolve()
        # Localizar cualquier carpeta existente que corresponda a esta actividad.
        if base.is_dir():
            act_pat = re.compile(
                rf"conceptos-.*-(?:actividad-0?{activity_number}|s0?{activity_number})\b",
                re.IGNORECASE,
            )
            for candidate in sorted(base.glob("conceptos-*")):
                if candidate.is_dir() and act_pat.search(candidate.name):
                    return candidate.resolve()
        return canonical.resolve()

    def _materia_slug(self, target_path: Path) -> str:
        """Deriva el slug de materia desde la carpeta objetivo (nombre sin sufijo de programa)."""
        materia_dir = target_path if target_path.is_dir() else target_path.parent
        name = materia_dir.name
        for suffix in ("-lde", "-lic", "-mga", "-mem", "-mtia", "-lgc"):
            if name.endswith(suffix):
                name = name[: -len(suffix)]
                break
        return name or "materia"

    def _build_command(self, request: ExtractorRequest, resolved: ResolvedExtractorRequest) -> list[str]:
        python_executable = self._python_executable()
        command = [python_executable, "run.py"]
        if resolved.fuentes_path is not None:
            command.extend(["--fuentes", str(resolved.fuentes_path)])
        if resolved.planeacion_path is not None:
            command.extend(["--planeacion", str(resolved.planeacion_path)])
        if resolved.conceptos_path is not None:
            command.extend(["--conceptos", str(resolved.conceptos_path)])
        command.extend(["--salida", str(resolved.output_dir)])
        command.extend(["--motor", request.motor])
        command.extend(["--top-k", str(max(1, int(request.top_k)))])
        command.extend(["--max-citas", str(max(1, int(request.max_citas)))])
        command.append("--recursivo" if request.recursive else "--no-recursivo")
        if request.probe_only:
            command.append("--probar-config")
        return command

    def _python_executable(self) -> str:
        venv_python = self.extractor_root / ".venv" / "Scripts" / "python.exe"
        if venv_python.exists():
            return str(venv_python)
        return sys.executable or "python"

    def _collect_artifacts(self, output_dir: Path) -> dict[str, bool]:
        return {
            name: (output_dir / filename).exists()
            for name, filename in CORE_EXTRACTOR_ARTIFACTS.items()
        }

    def _render_optional_path(self, path: Path | None) -> str:
        if path is None:
            return "pendiente"
        return self.workspace.relative(path)

    def _manifest_path(self, path: Path | None) -> str:
        return self.workspace.relative(path) if path is not None else ""