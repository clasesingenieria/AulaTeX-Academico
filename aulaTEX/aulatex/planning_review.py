from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .node_planning import NodePlanLoader
from .planning_layout import _require_versionable
from .planning_validation import validate_pedagogical
from .workspace import AulaTeXWorkspace


def _write_pair(workspace: AulaTeXWorkspace, output: Path, name: str, payload: dict[str, Any], markdown: str) -> None:
    output = output.resolve()
    if not output.is_relative_to(workspace.repo_root):
        raise ValueError("review_output_outside_project")
    paths = [output / (name + suffix) for suffix in (".json", ".md")]
    _require_versionable(workspace.repo_root, paths)
    if any(path.exists() for path in paths):
        raise FileExistsError("review_output_exists")
    output.mkdir(parents=True, exist_ok=True)
    for path, text in zip(paths, (json.dumps(payload, ensure_ascii=False, indent=2) + "\n", markdown)):
        with path.open("x", encoding="utf-8") as stream:
            stream.write(text)


def review_batch(workspace: AulaTeXWorkspace, batch: str, output: Path, *, revisions: tuple[str, ...] = ()) -> dict[str, Any]:
    directory = workspace.resolve_target(batch)
    manifest_path = directory / "resultado-conversion.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    scopes, _children = workspace.editorial_scope_index()
    selected = {}
    for relative in revisions:
        path = workspace.resolve_target(relative)
        document = json.loads(path.read_text(encoding="utf-8-sig"))
        if document["plan_id"] in selected:
            raise ValueError("duplicate_revision_selection")
        selected[document["plan_id"]] = relative
    available = {record["plan_id"] for record in manifest["records"] if "pedagogical_json" in record}
    if selected.keys() - available:
        raise ValueError("revision_not_in_batch")
    rows = []
    for record in manifest["records"]:
        if "pedagogical_json" not in record:
            continue
        path = workspace.resolve_target(selected.get(record["plan_id"], record["pedagogical_json"]))
        document = json.loads(path.read_text(encoding="utf-8-sig"))
        subject = scopes[record["subject_key"]]
        if document["identity"]["subject_id"] != subject.subject:
            raise ValueError("revision_subject_mismatch")
        for activity in document["activities"]:
            report = validate_pedagogical(document, workspace.resolve_target(subject.relative_path), activity["id"])
            rows.append({"subject_key": subject.key, "activity_id": activity["id"], "path": workspace.relative(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "state": document["review"]["state"], "semantic_passed": report["passed"], "findings": report["findings"], "verified_source_ids": report["verified_source_ids"], "unsegmented": document.get("extensions", {}).get("conversion", {}).get("unsegmented_document", False)})
    index_path = directory / "indice-planeaciones.json"
    index = json.loads(index_path.read_text(encoding="utf-8-sig"))
    approved = []
    blocked = []
    for entry in index.get("pending", []) + index.get("approved", []):
        if entry["level"] != "actividad":
            continue
        try:
            scope = scopes[entry["scope_key"]]
            path = workspace.resolve_target(entry["path"])
            if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
                raise ValueError("node_hash_changed")
            NodePlanLoader(workspace).load(entry["path"], scope, require_ready=True)
        except (ValueError, OSError, KeyError):
            blocked.append({"scope_key": entry["scope_key"], "path": entry["path"], "state": "blocked"})
        else:
            approved.append(entry)
    payload = {"kind": "activity-planning-review", "version": "1.0", "input_batch": batch, "input_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(), "selected_revisions": selected, "records": rows, "approved": approved, "blocked_nodes": blocked, "counts": {"activity_records": len(rows), "semantic_passed": sum(row["semantic_passed"] for row in rows), "unsegmented": sum(row["unsegmented"] for row in rows), "approved_nodes": len(approved)}, "automatic_execution": False}
    lines = ["# Cotejo de planeaciones por actividad", "", "Cotejo local determinista; no acredita vigencia de plataforma ni fidelidad visual de tablas.", "", "```json", json.dumps(payload["counts"], indent=2), "```", "", "| Materia | Actividad | Sin segmentar | Incidencias |", "| --- | --- | --- | --- |"]
    lines.extend(f"| {row['subject_key']} | {row['activity_id']} | {row['unsegmented']} | {len(row['findings'])} |" for row in rows)
    _write_pair(workspace, output, "cotejo-actividades", payload, "\n".join(lines) + "\n")
    return payload


def observe_planning(workspace: AulaTeXWorkspace, review_path: str, output: Path) -> dict[str, Any]:
    path = workspace.resolve_target(review_path)
    review = json.loads(path.read_text(encoding="utf-8-sig"))
    if review.get("kind") != "activity-planning-review":
        raise ValueError("diagnostic_requires_review")
    scopes, _children = workspace.editorial_scope_index()
    rows = []
    for entry in review["records"]:
        findings = []
        try:
            document_path = workspace.resolve_target(entry["path"])
            raw = document_path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
                findings.append({"code": "reviewed_plan_hash_changed", "path": "/"})
            else:
                document = json.loads(raw.decode("utf-8-sig"))
                scope = scopes[entry["subject_key"]]
                if scope.level != "materia" or scope.subject != document["identity"]["subject_id"]:
                    raise ValueError("diagnostic_subject_mismatch")
                findings.extend(validate_pedagogical(document, workspace.resolve_target(scope.relative_path), entry["activity_id"])["findings"])
        except (OSError, ValueError, KeyError):
            findings.append({"code": "diagnostic_input_unavailable", "path": "/"})
        previous = sorted((item["code"], item["path"]) for item in entry["findings"])
        current = sorted((item["code"], item["path"]) for item in findings)
        rows.append({"subject_key": entry["subject_key"], "activity_id": entry["activity_id"], "path": entry["path"], "blocked": bool(findings), "findings_changed": previous != current, "findings": findings})
    counts = {"observed_records": len(rows), "blocked_records": sum(row["blocked"] for row in rows), "changed_records": sum(row["findings_changed"] for row in rows)}
    payload = {"kind": "planning-diagnostic-monitor", "version": "1.0", "mode": "observe_only", "review_path": review_path, "review_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "counts": counts, "records": rows, "academic_approval": False, "editorial_execution": False, "platform_submission": False}
    lines = ["# Monitor diagnostico de planeaciones", "", "Instantanea local de hashes y bloqueos; no aprueba ni ejecuta actividades.", "", "```json", json.dumps(counts, indent=2), "```", "", "| Materia | Actividad | Bloqueada | Cambio de hallazgos |", "| --- | --- | --- | --- |"]
    lines.extend(f"| {row['subject_key']} | {row['activity_id']} | {row['blocked']} | {row['findings_changed']} |" for row in rows)
    _write_pair(workspace, output, "monitor-planeaciones", payload, "\n".join(lines) + "\n")
    return payload


def prepare_campaign(workspace: AulaTeXWorkspace, review_path: str, output: Path, *, max_activities: int = 1, max_cycles: int = 1) -> dict[str, Any]:
    if not 1 <= max_activities <= 5 or not 1 <= max_cycles <= 2:
        raise ValueError("pilot_limits_exceeded")
    path = workspace.resolve_target(review_path)
    review = json.loads(path.read_text(encoding="utf-8-sig"))
    scopes, _children = workspace.editorial_scope_index()
    admitted = []
    for entry in review["approved"][:max_activities]:
        scope = scopes[entry["scope_key"]]
        if scope.level != "actividad":
            raise ValueError("pilot_requires_activity")
        node_path = workspace.resolve_target(entry["path"])
        if hashlib.sha256(node_path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError("pilot_node_hash_changed")
        resolved = NodePlanLoader(workspace).load(entry["path"], scope, require_ready=True)
        admitted.append({"scope_key": scope.key, "target": scope.relative_path, "node_plan": entry["path"], "sha256": entry["sha256"], "activity_id": resolved.selected_activity_id, "chain": list(resolved.chain)})
    payload = {"kind": "validated-planning-pilot", "version": "1.0", "state": "enabled" if admitted else "blocked", "review_path": review_path, "review_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "max_activities": max_activities, "max_cycles": max_cycles, "activities": admitted, "diagnostic_monitor": {"enabled": True, "mode": "observe_only"}, "monitor": {"enabled": bool(admitted), "apply_revision_patches": False, "apply_bibliography_repair": False, "run_extractor": False}, "automatic_execution": False, "platform_submission": False}
    lines = ["# Campana piloto JSON y Markdown", "", f"Estado: {payload['state']}. Actividades admitidas: {len(admitted)}.", "", "Sin envios a plataforma. Monitor sin modificaciones ni extractor; ejecucion explicita y revalidacion requerida.", "", "```json", json.dumps(payload, ensure_ascii=False, indent=2), "```", ""]
    _write_pair(workspace, output, "campana-piloto", payload, "\n".join(lines))
    return payload


def run_campaign(workspace: AulaTeXWorkspace, campaign_path: str, output: Path) -> dict[str, Any]:
    path = workspace.resolve_target(campaign_path)
    campaign = json.loads(path.read_text(encoding="utf-8-sig"))
    if campaign["kind"] != "validated-planning-pilot" or campaign["state"] != "enabled" or not campaign["activities"]:
        raise ValueError("campaign_blocked")
    if not 1 <= len(campaign["activities"]) <= campaign["max_activities"] <= 5 or not 1 <= campaign["max_cycles"] <= 2:
        raise ValueError("pilot_limits_exceeded")
    review_path = workspace.resolve_target(campaign["review_path"])
    if hashlib.sha256(review_path.read_bytes()).hexdigest() != campaign["review_sha256"]:
        raise ValueError("pilot_review_hash_changed")
    approved = json.loads(review_path.read_text(encoding="utf-8-sig"))["approved"]
    scopes, _children = workspace.editorial_scope_index()
    selected = []
    for entry in campaign["activities"]:
        scope = scopes[entry["scope_key"]]
        if scope.level != "actividad" or entry["target"] != scope.relative_path:
            raise ValueError("pilot_scope_mismatch")
        if not any(item["scope_key"] == scope.key and item["path"] == entry["node_plan"] and item["sha256"] == entry["sha256"] for item in approved):
            raise ValueError("pilot_not_approved")
        node_path = workspace.resolve_target(entry["node_plan"])
        if hashlib.sha256(node_path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError("pilot_node_hash_changed")
        resolved = NodePlanLoader(workspace).load(entry["node_plan"], scope, require_ready=True)
        if list(resolved.chain) != entry["chain"] or resolved.selected_activity_id != entry["activity_id"]:
            raise ValueError("pilot_binding_changed")
        if scope.key in {item[0].key for item in selected}:
            raise ValueError("duplicate_pilot_activity")
        selected.append((scope, entry))
    output = output.resolve()
    if not output.is_relative_to(workspace.repo_root) or output.exists():
        raise ValueError("pilot_requires_new_output")
    from .activity_monitor import ActivityMonitor, ActivityMonitorRequest

    results = []
    monitor = ActivityMonitor(workspace)
    for scope, entry in selected:
        result = monitor.run(ActivityMonitorRequest(target=scope.relative_path, activity_number=int(scope.key.rsplit("-", 1)[1]), output=str(output / "monitor"), node_plan=entry["node_plan"], max_cycles=campaign["max_cycles"], run_detail_planner=False, run_extractor=False, apply_revision_patches=False, apply_bibliography_repair=False))
        results.append({"scope_key": scope.key, "ok": result.ok, "manifest": workspace.relative(result.manifest_path), "report": workspace.relative(result.report_path)})
        if not result.ok:
            break
    payload = {"kind": "validated-pilot-result", "campaign": campaign_path, "campaign_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "results": results, "stopped_on_blocker": any(not result["ok"] for result in results), "platform_submission": False}
    _write_pair(workspace, output, "resultado-piloto", payload, "# Resultado del piloto\n\n```json\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n```\n")
    return payload