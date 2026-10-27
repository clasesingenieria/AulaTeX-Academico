from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .node_planning import PEDAGOGICAL_SCHEMA_PATH, validate_schema
from .planning_layout import subject_layout


def _pointer(document: Any, path: str) -> Any:
    value = document
    for token in path.lstrip("/").split("/"):
        key = token.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def relocated_source(source_root: Path, relative: str, sha256: str) -> Path | None:
    manifest = subject_layout(source_root)["plans"] / "reubicaciones-documentales.json"
    if not manifest.is_file():
        return None
    payload = json.loads(manifest.read_text(encoding="utf-8-sig"))
    for movement in payload.get("moves", []):
        if movement.get("from") != relative or movement.get("sha256", "").lower() != sha256.lower():
            continue
        destination = Path(movement["to"])
        target = (source_root / destination).resolve()
        if destination.is_absolute() or not target.is_relative_to(source_root.resolve()):
            continue
        if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == sha256.lower():
            return target
    return None


def validate_pedagogical(document: dict[str, Any], source_root: Path, activity_id: str | None = None) -> dict[str, Any]:
    validate_schema(document, PEDAGOGICAL_SCHEMA_PATH)
    findings: list[dict[str, str]] = []

    def issue(code: str, path: str) -> None:
        findings.append({"code": code, "path": path})

    def identifiers(items: list[dict[str, Any]], path: str) -> set[str]:
        keys = [item["id"] for item in items]
        if len(set(keys)) != len(keys):
            issue("duplicate_id", path)
        return set(keys)

    def links(values: list[str], allowed: set[str], path: str) -> None:
        if any(value not in allowed for value in values):
            issue("unresolved_reference", path)

    source_root = source_root.resolve()
    source_ids = identifiers(document["sources"], "/sources")
    sources = {item["id"]: item for item in document["sources"]}
    verified_sources: set[str] = set()
    for index, source in enumerate(document["sources"]):
        path = f"/sources/{index}"
        embedded = document.get("extensions", {}).get("embedded_sources", {}).get(source["id"])
        if source["path"] is None and isinstance(embedded, dict) and embedded.get("encoding") == "utf-8" and isinstance(embedded.get("text"), str):
            if hashlib.sha256(embedded["text"].encode("utf-8")).hexdigest() != (source["sha256"] or "").lower():
                issue("source_hash_changed", path)
            else:
                verified_sources.add(source["id"])
            continue
        if source["path"] is None or source["sha256"] is None:
            issue("source_not_archived", path)
            continue
        relative = Path(source["path"])
        target = (source_root / relative).resolve()
        if relative.is_absolute() or not target.is_relative_to(source_root):
            issue("unsafe_source_path", path)
        elif (not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest().lower() != source["sha256"].lower()) and relocated_source(source_root, source["path"], source["sha256"]) is not None:
            verified_sources.add(source["id"])
        elif not target.is_file():
            issue("missing_source", path)
        elif hashlib.sha256(target.read_bytes()).hexdigest().lower() != source["sha256"].lower():
            issue("source_hash_changed", path)
        else:
            verified_sources.add(source["id"])

    status_by_path = {}
    for index, status in enumerate(document["field_status"]):
        path = f"/field_status/{index}"
        if status["path"] in status_by_path:
            issue("duplicate_field_status", path)
        status_by_path[status["path"]] = status
        try:
            _pointer(document, status["path"])
        except (KeyError, IndexError, ValueError, TypeError):
            issue("unresolved_pointer", path)
        if status["state"] == "conflict":
            issue("unresolved_conflict", status["path"])
        for evidence in status["evidence"]:
            if evidence["source_id"] not in source_ids:
                issue("unresolved_evidence_source", path)

    def status_for(path: str) -> dict[str, Any] | None:
        candidates = [key for key in status_by_path if path == key or path.startswith(key + "/")]
        return status_by_path[max(candidates, key=len)] if candidates else None

    def documented(path: str) -> None:
        status = status_for(path)
        if status is None or status["state"] != "confirmed":
            issue("instruction_not_confirmed", path)
        elif not any(evidence["source_id"] in verified_sources and sources[evidence["source_id"]]["authority"] == "instructional" for evidence in status["evidence"]):
            issue("instruction_without_archived_authority", path)

    outcomes = identifiers(document["curriculum"]["outcomes"], "/curriculum/outcomes")
    topics: list[dict[str, Any]] = []

    def collect(items: list[dict[str, Any]]) -> None:
        for item in items:
            topics.append(item)
            collect(item["children"])

    collect(document["curriculum"]["topics"])
    topic_ids = identifiers(topics, "/curriculum/topics")
    activity_ids = identifiers(document["activities"], "/activities")
    selected = [(index, activity) for index, activity in enumerate(document["activities"]) if activity_id is None or activity["id"] == activity_id]
    if not selected:
        issue("activity_not_found", "/activities")
    for index, activity in selected:
        path = f"/activities/{index}"
        requirements = identifiers(activity["requirements"], path + "/requirements")
        questions = identifiers(activity["questions"], path + "/questions")
        steps = identifiers(activity["sequence"], path + "/sequence")
        products = identifiers(activity["products"], path + "/products")
        criteria = identifiers(activity["assessment"]["criteria"], path + "/assessment/criteria")
        identifiers(activity["resources"], path + "/resources")
        if not activity["instruction"] or not activity["instruction"].strip():
            issue("missing_instruction", path + "/instruction")
        documented(path + "/instruction")
        if not requirements:
            issue("requirements_not_segmented", path + "/requirements")
        for requirement_index, _requirement in enumerate(activity["requirements"]):
            documented(path + f"/requirements/{requirement_index}")
        links(activity["outcome_ids"], outcomes, path + "/outcome_ids")
        links(activity["topic_ids"], topic_ids, path + "/topic_ids")
        links(activity["dependencies"], activity_ids - {activity["id"]}, path + "/dependencies")
        for item in activity["questions"] + activity["sequence"] + activity["products"] + activity["assessment"]["criteria"]:
            links(item["requirement_ids"], requirements, path)
        for step in activity["sequence"]:
            links(step["depends_on"], steps - {step["id"]}, path + "/sequence")
        orders = [item["order"] for item in activity["sequence"]]
        if len(set(orders)) != len(orders):
            issue("duplicate_step_order", path + "/sequence")
        for question_index, _question in enumerate(activity["questions"]):
            documented(path + f"/questions/{question_index}")
        for product_index, _product in enumerate(activity["products"]):
            documented(path + f"/products/{product_index}")
        for criterion_index, _criterion in enumerate(activity["assessment"]["criteria"]):
            documented(path + f"/assessment/criteria/{criterion_index}")
        for field in ("kind", "scale_total", "weight", "weight_unit"):
            if activity["assessment"].get(field) is not None:
                documented(path + "/assessment/" + field)
        covered: set[str] = set()
        for alignment in activity["alignment"]:
            links([alignment["outcome_id"]], outcomes, path + "/alignment")
            for field, allowed in (("requirement_ids", requirements), ("step_ids", steps), ("product_ids", products), ("criterion_ids", criteria)):
                links(alignment[field], allowed, path + "/alignment")
            covered.update(alignment["requirement_ids"])
        if requirements - covered and activity["role"] not in {"support", "diagnostic"}:
            issue("incomplete_alignment", path + "/alignment")
        if not activity["products"] and activity["role"] not in {"support", "diagnostic"}:
            issue("missing_product_definition", path + "/products")
        assessment = activity["assessment"]
        points = [item["points"] for item in assessment["criteria"]]
        if assessment["scale_total"] is not None and points and all(value is not None for value in points):
            if abs(sum(points) - assessment["scale_total"]) > 0.000001:
                issue("rubric_total_mismatch", path + "/assessment")
        for resource_index, resource in enumerate(activity["resources"]):
            if resource["source_id"] not in source_ids:
                issue("unresolved_resource_source", path + f"/resources/{resource_index}")
            if resource["required"] and (resource["source_id"] not in verified_sources or resource["access"] in {"unavailable", "unknown"}):
                issue("required_resource_not_verified", path + f"/resources/{resource_index}")
        calendar = activity["calendar"]
        for field in ("opens_at", "expected_at", "due_at", "closes_at"):
            if calendar[field]:
                documented(path + "/calendar/" + field)
        if any(calendar[key] for key in ("opens_at", "expected_at", "due_at", "closes_at")) and not calendar["timezone"]:
            issue("calendar_timezone_unknown", path + "/calendar")

    if document["review"]["critical_gaps"]:
        issue("declared_critical_gaps", "/review/critical_gaps")
    return {"kind": "pedagogical-semantic-validation", "passed": not findings, "activity_id": activity_id, "findings": findings, "verified_source_ids": sorted(verified_sources), "automatic_approval": False}