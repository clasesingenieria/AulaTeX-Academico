from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .planning_layout import _reject_credentials, _require_versionable, catalogued_plan_paths, subject_layout
from .workspace import AulaTeXWorkspace, EditorialScope


SCHEMA_PATH = Path(__file__).with_name("planeacion-nodo.schema.json")
PEDAGOGICAL_SCHEMA_PATH = Path(__file__).with_name("planeacion-canonica.schema.json")
PROFILE_FIELDS = {
    "interinstitucional": {"purpose": None, "editorial_principles": [], "quality_gates": [], "roadmap": [], "institution_keys": []},
    "institucion": {"mission": None, "academic_policies": [], "platforms": [], "calendar_framework": None, "program_keys": [], "subject_keys": []},
    "carrera": {"graduate_profile": None, "competencies": [], "curriculum_map": [], "progression": [], "subject_keys": []},
    "materia": {"purpose": None, "outcomes": [], "units": [], "assessment_strategy": None, "offerings": [], "activity_keys": []},
    "actividad": {"activity_id": None, "offering_id": None, "purpose": None, "product_ids": [], "completion_checks": []},
}


def validate_schema(payload: dict[str, Any], schema_path: Path = SCHEMA_PATH) -> None:
    _reject_credentials(payload)
    from jsonschema import Draft7Validator
    from referencing import Registry, Resource

    registry = Registry()
    for path in (SCHEMA_PATH, PEDAGOGICAL_SCHEMA_PATH):
        registry = registry.with_resource(path.name, Resource.from_contents(json.loads(path.read_text(encoding="utf-8"))))
    Draft7Validator(json.loads(schema_path.read_text(encoding="utf-8")), registry=registry).validate(payload)


def plan_id(scope: EditorialScope) -> str:
    return "nodo-" + hashlib.sha256(scope.key.encode("utf-8")).hexdigest()[:20]


def plan_directory(workspace: AulaTeXWorkspace, scope: EditorialScope, revision: int = 1) -> Path:
    root = workspace.resolve_target(scope.relative_path)
    base = subject_layout(root)["plans"] if scope.level in {"materia", "actividad"} else root / "planeaciones-aulatex"
    return base / "canonicas" / plan_id(scope) / f"r{revision:04d}"


def draft_plan(scope: EditorialScope) -> dict[str, Any]:
    profile = json.loads(json.dumps(PROFILE_FIELDS[scope.level]))
    return {
        "schema_version": "1.0.0-node", "plan_id": plan_id(scope), "revision": 1,
        "node": {key: getattr(scope, key) for key in ("key", "level", "parent_key", "relative_path", "label")},
        "profile": profile, "editorial_rules": {},
        "provenance": [{"path": "/profile", "state": "unknown", "reason": "Perfil pendiente de fuentes y cotejo; no es una planeacion ejecutable.", "evidence": [], "alternatives": []}],
        "review": {"state": "draft", "semantic_validation": "not_run", "critical_gaps": ["Completar y cotejar el perfil del nodo"]},
        "bindings": {"parent_plan": None, "pedagogical_plan": None},
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [f"# Planeacion de nodo: {payload['node']['label']}", "", f"Estado: {payload['review']['state']}. Nivel: {payload['node']['level']}.", "", "Vista derivada del JSON; no acredita aprobacion docente ni autoriza envio."]
    for key, value in payload.items():
        lines.extend(["", f"## {key}", "", "```json", json.dumps(value, ensure_ascii=False, indent=2), "```"])
    return "\n".join(lines) + "\n"


def publish_plan(workspace: AulaTeXWorkspace, scope: EditorialScope, payload: dict[str, Any]) -> tuple[Path, Path]:
    validate_schema(payload)
    if payload["node"] != draft_plan(scope)["node"] or payload["plan_id"] != plan_id(scope):
        raise ValueError("La planeacion no corresponde a la identidad del nodo.")
    directory = plan_directory(workspace, scope, payload["revision"])
    root = workspace.repo_root.resolve()
    if not directory.resolve().is_relative_to(root):
        raise ValueError("La planeacion debe permanecer dentro del proyecto.")
    outputs = {
        directory / "planeacion.json": (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        directory / "planeacion.md": render_markdown(payload).encode("utf-8"),
    }
    _require_versionable(root, list(outputs))
    for path, content in outputs.items():
        if path.exists() and path.read_bytes() != content:
            raise FileExistsError("Revision existente: publicar una revision nueva, no sobrescribirla.")
    directory.mkdir(parents=True, exist_ok=True)
    for path, content in outputs.items():
        if not path.exists():
            with path.open("xb") as stream:
                stream.write(content)
    return tuple(outputs)


@dataclass(frozen=True)
class ResolvedNodePlan:
    plan: dict[str, Any]
    chain: tuple[dict[str, str], ...]
    editorial_rules: dict[str, Any]
    rule_origins: dict[str, str]
    pedagogical_plan: dict[str, Any] | None
    selected_activity_id: str | None = None

    def context_markdown(self) -> str:
        context = {"node_plan": self.plan, "chain": list(self.chain), "effective_editorial_rules": self.editorial_rules, "rule_origins": self.rule_origins, "pedagogical_plan": self.pedagogical_plan, "selected_activity_id": self.selected_activity_id}
        return "## Planeacion canonica resuelta\n\n```json\n" + json.dumps(context, ensure_ascii=False, indent=2) + "\n```\n"

    def extractor_markdown(self) -> str:
        if self.pedagogical_plan is None:
            raise ValueError("No hay perfil pedagogico para el extractor.")
        document = self.pedagogical_plan
        activities = [item for item in document["activities"] if self.selected_activity_id is None or item["id"] == self.selected_activity_id]
        lines = ["# Proyeccion para extractor", "", "Vista derivada; la consigna completa permanece en planeacion-resuelta.json."]
        sections = {
            "Tema": json.dumps(document["curriculum"]["topics"], ensure_ascii=False),
            "Objetivo": document["curriculum"]["purpose"] or "No documentado",
            "Aprendizajes": "; ".join(item["text"] for item in document["curriculum"]["outcomes"]),
            "Actividad": "\n".join((activity["instruction"] or "No documentada") + "\n" + "\n".join(item["text"] for item in activity["requirements"]) + "\n" + "\n".join(item["text"] for item in activity["questions"]) for activity in activities),
            "Criterios de evaluacion": "\n".join(item["text"] for activity in activities for item in activity["assessment"]["criteria"]),
            "Referencias": "\n".join(item["title"] for item in document["sources"] if item["authority"] == "scholarly"),
        }
        for heading, text in sections.items():
            lines.extend(["", heading + ":", text or "No documentado"])
        return "\n".join(lines) + "\n"


class NodePlanLoader:
    def __init__(self, workspace: AulaTeXWorkspace) -> None:
        self.workspace = workspace

    def _read(self, relative_path: str, expected_hash: str | None = None) -> tuple[dict[str, Any], str]:
        path = Path(relative_path)
        if path.is_absolute():
            raise ValueError("La vinculacion debe ser relativa al proyecto.")
        path = self.workspace.resolve_target(path)
        if not path.is_relative_to(self.workspace.repo_root):
            raise ValueError("La vinculacion sale del proyecto.")
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if expected_hash and digest != expected_hash:
            raise ValueError("Cambio de huella en la planeacion vinculada.")
        payload = json.loads(raw.decode("utf-8-sig"))
        return payload, digest

    def load(self, relative_path: str, scope: EditorialScope, *, require_ready: bool = False) -> ResolvedNodePlan:
        by_key, _children = self.workspace.editorial_scope_index()
        current_path = relative_path
        current_scope = scope
        expected_hash = None
        chain: list[dict[str, str]] = []
        documents: list[dict[str, Any]] = []
        seen: set[str] = set()
        while True:
            payload, digest = self._read(current_path, expected_hash)
            validate_schema(payload)
            if payload["plan_id"] in seen:
                raise ValueError("Ciclo en las planeaciones padre.")
            seen.add(payload["plan_id"])
            if payload["node"] != draft_plan(current_scope)["node"] or payload["plan_id"] != plan_id(current_scope):
                raise ValueError("Planeacion de otro nodo o nivel.")
            if payload["review"]["state"] == "superseded":
                raise ValueError("Revision sustituida; seleccionar una revision vigente explicitamente.")
            if require_ready and payload["review"]["state"] != "ready":
                raise ValueError("Planeacion pendiente de validacion; no ejecutar.")
            documents.append(payload)
            chain.append({"path": current_path, "sha256": digest, "plan_id": payload["plan_id"], "revision": str(payload["revision"]), "node_key": current_scope.key})
            parent = payload["bindings"]["parent_plan"]
            if parent is None:
                break
            if parent["activity_id"] is not None or not current_scope.parent_key or current_scope.parent_key not in by_key:
                raise ValueError("Vinculacion padre incompatible con el catalogo.")
            current_scope = by_key[current_scope.parent_key]
            current_path, expected_hash = parent["path"], parent["sha256"]

        rules: dict[str, Any] = {}
        origins: dict[str, str] = {}
        for payload in reversed(documents):
            for key, value in payload["editorial_rules"].items():
                if value is not None:
                    rules[key] = value
                    origins[key] = payload["node"]["key"]
        local = documents[0]
        pedagogical = None
        selected_activity_id = None
        binding = local["bindings"]["pedagogical_plan"]
        if binding is not None:
            if scope.level not in {"materia", "actividad"}:
                raise ValueError("Un nodo estrategico no puede vincular una consigna como perfil propio.")
            pedagogical, _digest = self._read(binding["path"], binding["sha256"])
            validate_schema(pedagogical, PEDAGOGICAL_SCHEMA_PATH)
            subject_key = scope.parent_key if scope.level == "actividad" else scope.key
            subject_id = by_key[subject_key].subject
            if pedagogical["identity"]["subject_id"] != subject_id:
                raise ValueError("La materia del perfil pedagogico no coincide con el catalogo.")
            if scope.level == "actividad":
                activity_id = binding["activity_id"]
                selected_activity_id = activity_id
                activities = [item for item in pedagogical["activities"] if item["id"] == activity_id]
                if len(activities) != 1 or local["profile"]["activity_id"] != activity_id:
                    raise ValueError("Actividad pedagogica ausente o ambigua.")
                if local["profile"]["offering_id"] != pedagogical["identity"]["offering_id"]:
                    raise ValueError("La oferta de la actividad no coincide.")
            if require_ready and pedagogical["review"]["state"] != "ready":
                raise ValueError("Perfil pedagogico pendiente de validacion.")
            if require_ready:
                from .planning_validation import validate_pedagogical

                subject_root = self.workspace.resolve_target(by_key[subject_key].relative_path)
                active_paths = catalogued_plan_paths(subject_root)
                if active_paths is not None:
                    catalog = json.loads((subject_layout(subject_root)["plans"] / "catalogo-editorial.json").read_text(encoding="utf-8-sig"))
                    entries = [item for item in catalog["activities"] if str(item["module_id"]) == selected_activity_id]
                    if len(entries) != 1 or entries[0].get("execution_allowed") is not True:
                        raise ValueError("Actividad excluida o pendiente en el catalogo editorial; no ejecutar.")
                    entry = entries[0]
                    active = subject_root / entry["json"]
                    if scope.key.rsplit("/", 1)[-1] != f"actividad-{entry['number']}" or hashlib.sha256(active.read_bytes()).hexdigest() != binding["sha256"]:
                        raise ValueError("La vinculacion no corresponde a la revision editorial activa.")
                    if pedagogical.get("extensions", {}).get("editorial", {}).get("already_completed_evidence"):
                        raise ValueError("Actividad ya realizada; no repetir ejecucion.")
                report = validate_pedagogical(pedagogical, subject_root, selected_activity_id)
                if not report["passed"]:
                    raise ValueError("La validacion semantica detecto bloqueos en la planeacion pedagogica.")
        elif require_ready and scope.level == "actividad":
            raise ValueError("Una actividad ejecutable requiere su perfil pedagogico local.")
        return ResolvedNodePlan(local, tuple(chain), rules, origins, pedagogical, selected_activity_id)


def prepare_propagation(workspace: AulaTeXWorkspace) -> dict[str, Any]:
    scopes = workspace.scan_editorial_scopes()
    keys = {scope.key for scope in scopes}
    if len(keys) != len(scopes):
        raise ValueError("El catalogo contiene identidades duplicadas; resolver antes de propagar.")
    rows = []
    for scope in scopes:
        if scope.parent_key and scope.parent_key not in keys:
            raise ValueError("Nodo sin padre en el catalogo.")
        model = draft_plan(scope)
        children = [child for child in scopes if child.parent_key == scope.key]
        child_fields = {"interinstitucional": {"institution_keys": "institucion"}, "institucion": {"program_keys": "carrera", "subject_keys": "materia"}, "carrera": {"subject_keys": "materia"}, "materia": {"activity_keys": "actividad"}}.get(scope.level, {})
        for field, level in child_fields.items():
            model["profile"][field] = [child.key for child in children if child.level == level]
        directory = plan_directory(workspace, scope)
        existing = sorted(directory.parent.glob("r*/planeacion.json"))
        rows.append({"node": asdict(scope), "plan_id": plan_id(scope), "proposed_json": workspace.relative(directory / "planeacion.json"), "proposed_markdown": workspace.relative(directory / "planeacion.md"), "existing_revisions": [workspace.relative(path) for path in existing], "state": "review_existing" if existing else "pending_generation", "draft": model})
    return {"kind": "node-planning-propagation", "version": "1.0", "mode": "prepare_only", "counts": {level: sum(scope.level == level for scope in scopes) for level in PROFILE_FIELDS}, "limitations": ["Catalogo editorial: actividades reconocidas por fuentes TEX o marcadores; no acredita cobertura de todas las actividades de plataforma.", "Los borradores no estan aprobados y no se publican en los nodos.", "Cotejar fuentes y descubrir actividades sin nodo antes de convertir."], "nodes": rows}


def write_propagation(workspace: AulaTeXWorkspace, output: Path) -> tuple[Path, Path]:
    payload = prepare_propagation(workspace)
    output = output.resolve()
    if not output.is_relative_to(workspace.repo_root):
        raise ValueError("La preparacion debe permanecer dentro del proyecto.")
    lines = ["# Preparacion de planeaciones por nodo", "", "Modo: prepare_only. No se publicaron planeaciones ni se ejecutaron actividades.", "", "## Cobertura", ""]
    lines.extend(f"- {level}: {count}" for level, count in payload["counts"].items())
    lines.extend(["", "## Limites", ""] + ["- " + item for item in payload["limitations"]])
    lines.extend(["", "## Nodos", "", "| Nodo | Nivel | Estado | JSON propuesto |", "| --- | --- | --- | --- |"])
    lines.extend(f"| {row['node']['key']} | {row['node']['level']} | {row['state']} | {row['proposed_json']} |" for row in payload["nodes"])
    outputs = {output / "propagacion-planeaciones.json": (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"), output / "propagacion-planeaciones.md": ("\n".join(lines) + "\n").encode("utf-8")}
    if any(path.exists() for path in outputs):
        raise FileExistsError("Preparacion existente: usar otra carpeta de salida.")
    output.mkdir(parents=True, exist_ok=True)
    for path, content in outputs.items():
        with path.open("xb") as stream:
            stream.write(content)
    return tuple(outputs)