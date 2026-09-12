from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


INSTITUTIONS = ("UnADM", "UCNL", "UANL", "ITESCA", "IIIEPE")
GENERATION_MARKER_FILENAME = ".aulatex-node.json"
SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    ".venv-linux",
    "__pycache__",
    "node_modules",
    ".build",
    "assets-itesca",
    "assets-ucnl",
    "assets-uanl",
    "assets-unadm",
    "logs-compilacion-tex",
}

CAREER_PREFIXES = (
    "licenciatura-",
    "ingenieria-",
    "ingeniero-",
    "maestria-",
    "doctorado-",
    "especialidad-",
    "tecnico-",
    "tsu-",
)


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class TemplateInventoryNode:
    level: str
    name: str
    relative_path: str
    bibliography_files: tuple[str, ...]
    presentation_files: tuple[str, ...]
    report_files: tuple[str, ...]
    children: tuple["TemplateInventoryNode", ...] = ()

    @property
    def has_bibliography(self) -> bool:
        return bool(self.bibliography_files)

    @property
    def has_presentation(self) -> bool:
        return bool(self.presentation_files)

    @property
    def has_report(self) -> bool:
        return bool(self.report_files)

    @property
    def is_complete(self) -> bool:
        return self.has_bibliography and self.has_presentation and self.has_report


@dataclass(frozen=True)
class EditorialScope:
    key: str
    level: str
    label: str
    relative_path: str
    institution: str = ""
    career: str = ""
    subject: str = ""
    activity: str = ""
    parent_key: str = ""

    @property
    def depth(self) -> int:
        order = {
            "interinstitucional": 0,
            "institucion": 1,
            "carrera": 2,
            "materia": 3,
            "actividad": 4,
        }
        return order.get(self.level, -1)


class AulaTeXWorkspace:
    def __init__(self, repo_root: str | Path | None = None) -> None:
        self.repo_root = Path(repo_root or Path(__file__).resolve().parents[2]).resolve()
        self.scripts_dir = self.repo_root / "scripts"
        self.feedback_root = self.repo_root / "retroalimentacion-editorial" / "aulatex"
        self.feedback_root.mkdir(parents=True, exist_ok=True)
        self.temp_root = self.repo_root / ".aulatex-temp"
        self.temp_root.mkdir(parents=True, exist_ok=True)

    def timestamp(self) -> str:
        return time.strftime("%Y%m%d-%H%M%S")

    def relative(self, path: str | Path) -> str:
        p = Path(path).resolve()
        try:
            return p.relative_to(self.repo_root).as_posix()
        except ValueError:
            return str(p)

    def resolve_target(self, target: str | Path | None) -> Path:
        if not target:
            return self.repo_root
        p = Path(target)
        if not p.is_absolute():
            p = self.repo_root / p
        return p.resolve()

    def _list_visible_dirs(self, root: Path, exclude_prefixes: tuple[str, ...] = ()) -> list[Path]:
        if not root.exists():
            return []
        return [
            path
            for path in sorted(root.iterdir())
            if path.is_dir()
            and path.name not in SKIP_DIR_NAMES
            and not path.name.startswith(".")
            and not any(path.name.startswith(prefix) for prefix in exclude_prefixes)
        ]

    def _match_direct_files(self, root: Path, pattern: str) -> tuple[str, ...]:
        if not root.exists():
            return ()
        return tuple(path.name for path in sorted(root.glob(pattern)) if path.is_file())

    def _is_career_dir(self, path: Path) -> bool:
        marker = self._read_generation_marker(path)
        if marker:
            return marker.get("level") == "carrera"
        name = path.name.lower()
        if any(name.startswith(prefix) for prefix in CAREER_PREFIXES):
            return True
        if (path / "README.md").exists() or (path / "COMPILACION.md").exists():
            if list(self._list_visible_dirs(path, exclude_prefixes=("referencias-",))):
                return True
        has_program_files = bool(self._match_direct_files(path, "reporte*.tex") or self._match_direct_files(path, "presentacion*.tex") or self._match_direct_files(path, "*.bib"))
        has_children = bool(self._list_visible_dirs(path, exclude_prefixes=("referencias-",)))
        return has_program_files and has_children

    def _read_generation_marker(self, root: Path) -> dict:
        marker_path = root / GENERATION_MARKER_FILENAME
        if not marker_path.exists() or not marker_path.is_file():
            return {}
        try:
            payload = json.loads(marker_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _institution_roots(self) -> list[Path]:
        ordered: list[Path] = []
        seen: set[str] = set()

        for institution in INSTITUTIONS:
            root = self.repo_root / institution
            if root.exists() and root.is_dir():
                ordered.append(root)
                seen.add(root.name.lower())

        for root in self._list_visible_dirs(self.repo_root, exclude_prefixes=("referencias-",)):
            if root.name.lower() in seen:
                continue
            marker = self._read_generation_marker(root)
            if marker.get("level") == "institucion":
                ordered.append(root)
                seen.add(root.name.lower())
                continue
            children = self._list_visible_dirs(root, exclude_prefixes=("referencias-",))
            has_career_children = any(self._is_career_dir(child) for child in children)
            has_assets = any(child.name.startswith("assets-") for child in children)
            has_program_files = bool(
                self._match_direct_files(root, "reporte*.tex")
                or self._match_direct_files(root, "presentacion*.tex")
                or self._match_direct_files(root, "*.bib")
            )
            if has_assets and (has_career_children or has_program_files):
                ordered.append(root)
                seen.add(root.name.lower())
        return ordered

    def _extract_activity_labels(self, root: Path) -> tuple[str, ...]:
        labels: dict[int, str] = {}
        for tex in sorted(root.glob("*.tex")):
            match = re.search(r"actividad[-_\s]*(\d+)", tex.stem, re.IGNORECASE)
            if not match:
                continue
            number = int(match.group(1))
            labels[number] = f"Actividad {number}"
        for child in self._list_visible_dirs(root, exclude_prefixes=("referencias-",)):
            marker = self._read_generation_marker(child)
            if marker.get("level") != "actividad":
                continue
            label = str(marker.get("label") or "").strip()
            match = re.search(r"Actividad\s+(\d+)", label, re.IGNORECASE)
            if not match:
                continue
            number = int(match.group(1))
            labels[number] = f"Actividad {number}"
        return tuple(labels[number] for number in sorted(labels))

    def _scope_key(
        self,
        level: str,
        institution: str = "",
        career: str = "",
        subject: str = "",
        activity: str = "",
    ) -> str:
        if level == "interinstitucional":
            return "interinstitucional"
        parts = [institution]
        if career:
            parts.append(career)
        if subject:
            parts.append(subject)
        if activity:
            parts.append(activity.lower().replace(" ", "-"))
        return "/".join(part for part in parts if part)

    def scan_editorial_scopes(self) -> list[EditorialScope]:
        scopes: list[EditorialScope] = [
            EditorialScope(
                key="interinstitucional",
                level="interinstitucional",
                label="Interinstitucional",
                relative_path=".",
            )
        ]

        for institution_root in self._institution_roots():
            institution = institution_root.name

            institution_scope = EditorialScope(
                key=self._scope_key("institucion", institution=institution),
                level="institucion",
                label=institution,
                relative_path=self.relative(institution_root),
                institution=institution,
                parent_key="interinstitucional",
            )
            scopes.append(institution_scope)

            for child in self._list_visible_dirs(institution_root, exclude_prefixes=("referencias-",)):
                child_marker = self._read_generation_marker(child)
                if self._is_career_dir(child):
                    career_scope = EditorialScope(
                        key=self._scope_key("carrera", institution=institution, career=child.name),
                        level="carrera",
                        label=child.name,
                        relative_path=self.relative(child),
                        institution=institution,
                        career=child.name,
                        parent_key=institution_scope.key,
                    )
                    scopes.append(career_scope)
                    subject_dirs = self._list_visible_dirs(child, exclude_prefixes=("referencias-",))
                    for subject_dir in subject_dirs:
                        subject_marker = self._read_generation_marker(subject_dir)
                        if subject_marker and subject_marker.get("level") not in {"materia", "actividad"}:
                            continue
                        subject_scope = EditorialScope(
                            key=self._scope_key("materia", institution=institution, career=child.name, subject=subject_dir.name),
                            level="materia",
                            label=subject_dir.name,
                            relative_path=self.relative(subject_dir),
                            institution=institution,
                            career=child.name,
                            subject=subject_dir.name,
                            parent_key=career_scope.key,
                        )
                        scopes.append(subject_scope)
                        for activity in self._extract_activity_labels(subject_dir):
                            scopes.append(
                                EditorialScope(
                                    key=self._scope_key(
                                        "actividad",
                                        institution=institution,
                                        career=child.name,
                                        subject=subject_dir.name,
                                        activity=activity,
                                    ),
                                    level="actividad",
                                    label=activity,
                                    relative_path=self.relative(subject_dir),
                                    institution=institution,
                                    career=child.name,
                                    subject=subject_dir.name,
                                    activity=activity,
                                    parent_key=subject_scope.key,
                                )
                            )
                    continue

                if child_marker and child_marker.get("level") not in {"materia", "actividad"}:
                    continue

                subject_scope = EditorialScope(
                    key=self._scope_key("materia", institution=institution, subject=child.name),
                    level="materia",
                    label=child.name,
                    relative_path=self.relative(child),
                    institution=institution,
                    subject=child.name,
                    parent_key=institution_scope.key,
                )
                scopes.append(subject_scope)
                for activity in self._extract_activity_labels(child):
                    scopes.append(
                        EditorialScope(
                            key=self._scope_key(
                                "actividad",
                                institution=institution,
                                subject=child.name,
                                activity=activity,
                            ),
                            level="actividad",
                            label=activity,
                            relative_path=self.relative(child),
                            institution=institution,
                            subject=child.name,
                            activity=activity,
                            parent_key=subject_scope.key,
                        )
                    )
        return scopes

    def editorial_scope_index(self) -> tuple[dict[str, EditorialScope], dict[str, list[EditorialScope]]]:
        scopes = self.scan_editorial_scopes()
        by_key = {scope.key: scope for scope in scopes}
        children: dict[str, list[EditorialScope]] = {}
        for scope in scopes:
            children.setdefault(scope.parent_key, []).append(scope)
        for items in children.values():
            items.sort(key=lambda item: (item.depth, item.label.lower()))
        return by_key, children

    def scope_chain(self, scope_key: str) -> list[EditorialScope]:
        by_key, _children = self.editorial_scope_index()
        current = by_key.get(scope_key)
        chain: list[EditorialScope] = []
        while current is not None:
            chain.append(current)
            current = by_key.get(current.parent_key)
        return chain

    def find_scope_for_target(self, target: str | Path | None, activity_number: int | None = None) -> EditorialScope | None:
        resolved = self.resolve_target(target)
        relative = self.relative(resolved)
        if resolved.is_file():
            relative = self.relative(resolved.parent)

        scopes = self.scan_editorial_scopes()
        activity_label = f"Actividad {activity_number}" if activity_number else ""
        candidates = []
        for scope in scopes:
            if scope.level == "actividad" and activity_label and scope.activity != activity_label:
                continue
            if relative == scope.relative_path or relative.startswith(scope.relative_path + "/"):
                candidates.append(scope)

        if not candidates:
            return None

        exact_matches = [scope for scope in candidates if scope.relative_path == relative]
        if exact_matches and not activity_label:
            exact_matches.sort(key=lambda scope: scope.depth)
            non_activity = [scope for scope in exact_matches if scope.level != "actividad"]
            if non_activity:
                return non_activity[-1]

        candidates.sort(key=lambda scope: (scope.depth, len(scope.relative_path)), reverse=True)
        return candidates[0]

    def _inventory_node(self, root: Path, level: str, children: list[TemplateInventoryNode]) -> TemplateInventoryNode:
        return TemplateInventoryNode(
            level=level,
            name=root.name,
            relative_path=self.relative(root),
            bibliography_files=self._match_direct_files(root, "*.bib"),
            presentation_files=self._match_direct_files(root, "presentacion*.tex"),
            report_files=self._match_direct_files(root, "reporte*.tex"),
            children=tuple(children),
        )

    def scan_tree(self) -> dict[str, dict[str, list[str]]]:
        tree: dict[str, dict[str, list[str]]] = {}
        for root in self._institution_roots():
            institution = root.name
            careers: dict[str, list[str]] = {}
            for career in self._list_visible_dirs(root, exclude_prefixes=("referencias-",)):
                marker = self._read_generation_marker(career)
                if marker and marker.get("level") not in {"carrera", "materia"}:
                    continue
                subjects = [
                    child.name
                    for child in self._list_visible_dirs(career, exclude_prefixes=("referencias-",))
                ]
                careers[career.name] = subjects
            tree[institution] = careers
        return tree

    def scan_template_inventory(self) -> list[TemplateInventoryNode]:
        inventory: list[TemplateInventoryNode] = []
        for institution_root in self._institution_roots():

            careers: list[TemplateInventoryNode] = []
            for career_root in self._list_visible_dirs(institution_root, exclude_prefixes=("referencias-",)):
                marker = self._read_generation_marker(career_root)
                if marker and marker.get("level") == "materia":
                    continue
                subjects = [
                    self._inventory_node(subject_root, "materia", [])
                    for subject_root in self._list_visible_dirs(career_root, exclude_prefixes=("referencias-",))
                ]
                careers.append(self._inventory_node(career_root, "carrera", subjects))

            inventory.append(self._inventory_node(institution_root, "institucion", careers))
        return inventory

    def find_tex_files(self, target: str | Path | None = None, limit: int = 200) -> list[Path]:
        root = self.resolve_target(target)
        if root.is_file() and root.suffix.lower() == ".tex":
            return [root]
        if not root.exists():
            return []
        files: list[Path] = []
        for path in sorted(root.rglob("*.tex")):
            if any(part in SKIP_DIR_NAMES for part in path.relative_to(root).parts):
                continue
            files.append(path)
            if len(files) >= limit:
                break
        return files

    def context_summary(self, target: str | Path | None, max_chars: int = 9000) -> str:
        root = self.resolve_target(target)
        chunks: list[str] = [f"Target: {self.relative(root)}"]
        if not root.exists():
            chunks.append("Target does not exist yet.")
            return "\n".join(chunks)

        if root.is_file():
            candidates = [root]
        else:
            names = ("README.md", "COMPILACION.md")
            candidates = [root / name for name in names if (root / name).exists()]
            candidates.extend(sorted(root.glob("programa-analitico*.md"))[:3])
            candidates.extend(sorted(root.glob("*.bib"))[:3])
            candidates.extend(sorted(root.glob("reporte-*.tex"))[:2])
            candidates.extend(sorted(root.glob("presentacion-*.tex"))[:2])

        for candidate in candidates:
            if not candidate.exists() or not candidate.is_file():
                continue
            if candidate.suffix.lower() not in {".md", ".txt", ".tex", ".bib"}:
                continue
            try:
                text = candidate.read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                chunks.append(f"## {self.relative(candidate)}\n[read error: {exc}]")
                continue
            remaining = max_chars - sum(len(c) for c in chunks)
            if remaining <= 0:
                break
            chunks.append(f"## {self.relative(candidate)}\n{text[:remaining]}")
        return "\n\n".join(chunks)

    def _terminate_process_tree(self, proc: subprocess.Popen[str]) -> None:
        if os.name != "nt":
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            return
        if proc.poll() is not None:
            return
        try:
            if proc.args and str(proc.args[0]).lower().endswith(("powershell", "powershell.exe")):
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=15,
                )
                return
        except Exception:
            pass
        try:
            proc.kill()
        except Exception:
            pass

    def compile_tex(self, tex_file: str | Path, clean_mode: str = "safe", timeout_seconds: int = 360) -> CommandResult:
        tex = self.resolve_target(tex_file)
        script = self.scripts_dir / "latexmk-build.ps1"
        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            str(tex),
            "-CleanMode",
            clean_mode,
        ]
        process_options = {}
        if os.name != "nt":
            script = self.scripts_dir / "latexmk-build.sh"
            cmd = ["bash", str(script), str(tex), "--clean-mode", clean_mode]
            process_options["start_new_session"] = True
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(self.repo_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                **process_options,
            )
        except OSError as exc:
            return CommandResult(False, 127, "", f"No se pudo iniciar {script.name}: {exc}")
        try:
            stdout, stderr = proc.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            self._terminate_process_tree(proc)
            try:
                stdout, stderr = proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                stdout, stderr = "", ""
            message = (
                f"Tiempo de espera agotado tras {timeout_seconds}s al compilar "
                f"{self.relative(tex)} con {script.name}."
            )
            return CommandResult(False, 124, (stdout or "") + "\n" + message + "\n", stderr or "")
        return CommandResult(proc.returncode == 0, proc.returncode, stdout, stderr)

    def append_bitacora(self, run_id: str, title: str, data: dict) -> None:
        path = self.feedback_root / "bitacora.md"
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        prefix = ""
        if not path.exists() or not path.read_text(encoding="utf-8", errors="replace").strip():
            prefix = "# Bitacora AulaTeX\n\n"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"{prefix}\n## {run_id} - {title}\n\n```json\n{payload}\n```\n")
