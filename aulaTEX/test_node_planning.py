import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from aulatex.node_planning import NodePlanLoader, draft_plan, plan_directory, prepare_propagation, publish_plan, validate_schema, write_propagation
from aulatex.workspace import AulaTeXWorkspace


class NodePlanningTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        subject = self.root / "UnADM/licenciatura-ejemplo/materia-lde"
        subject.mkdir(parents=True)
        (subject / "reporte-materia-Actividad-1.tex").write_text("test", encoding="utf-8")
        self.workspace = AulaTeXWorkspace(self.root)
        self.scopes = {scope.level: scope for scope in self.workspace.scan_editorial_scopes()}

    def test_all_five_profiles_validate_and_wrong_profile_is_rejected(self):
        from jsonschema import ValidationError

        self.assertEqual(len(self.scopes), 5)
        for scope in self.scopes.values():
            validate_schema(draft_plan(scope))
        payload = draft_plan(self.scopes["actividad"])
        payload["profile"] = draft_plan(self.scopes["interinstitucional"])["profile"]
        with self.assertRaises(ValidationError):
            validate_schema(payload)

    def test_publication_is_idempotent_and_preserves_revision(self):
        scope = self.scopes["materia"]
        payload = draft_plan(scope)
        paths = publish_plan(self.workspace, scope, payload)
        self.assertEqual(paths, publish_plan(self.workspace, scope, payload))
        previous = paths[0].read_bytes()
        payload["profile"]["purpose"] = "changed"
        with self.assertRaises(FileExistsError):
            publish_plan(self.workspace, scope, payload)
        self.assertEqual(paths[0].read_bytes(), previous)
        self.assertEqual(paths[1].suffix, ".md")

    def test_inheritance_only_merges_editorial_rules_and_pins_hash(self):
        parent_scope = self.scopes["materia"]
        parent = draft_plan(parent_scope)
        parent["profile"]["purpose"] = "Must not become an activity instruction"
        parent["editorial_rules"] = {"language": "es", "citation_style": "APA7"}
        parent_path, _markdown = publish_plan(self.workspace, parent_scope, parent)
        child_scope = self.scopes["actividad"]
        child = draft_plan(child_scope)
        child["editorial_rules"] = {"citation_style": "Chicago"}
        child["bindings"]["parent_plan"] = {"path": self.workspace.relative(parent_path), "sha256": hashlib.sha256(parent_path.read_bytes()).hexdigest(), "activity_id": None}
        child_path, _markdown = publish_plan(self.workspace, child_scope, child)
        resolved = NodePlanLoader(self.workspace).load(self.workspace.relative(child_path), child_scope)
        self.assertEqual(resolved.editorial_rules, {"language": "es", "citation_style": "Chicago"})
        self.assertIsNone(resolved.plan["profile"]["purpose"])
        self.assertIsNone(resolved.pedagogical_plan)
        parent_path.write_bytes(parent_path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "huella"):
            NodePlanLoader(self.workspace).load(self.workspace.relative(child_path), child_scope)

    def test_draft_cannot_execute_and_different_node_cannot_load(self):
        scope = self.scopes["actividad"]
        path, _markdown = publish_plan(self.workspace, scope, draft_plan(scope))
        with self.assertRaisesRegex(ValueError, "pendiente"):
            NodePlanLoader(self.workspace).load(self.workspace.relative(path), scope, require_ready=True)
        with self.assertRaisesRegex(ValueError, "otro nodo"):
            NodePlanLoader(self.workspace).load(self.workspace.relative(path), self.scopes["materia"])

    def test_paths_and_credentials_are_rejected(self):
        scope = self.scopes["actividad"]
        with self.assertRaises(ValueError):
            NodePlanLoader(self.workspace).load("../escape.json", scope)
        payload = draft_plan(scope)
        payload["profile"]["purpose"] = "https://example.org/?sesskey=fake"
        with self.assertRaises(ValueError):
            publish_plan(self.workspace, scope, payload)
        self.assertFalse(plan_directory(self.workspace, scope).exists())

    def test_propagation_prepares_each_node_without_publishing(self):
        payload = prepare_propagation(self.workspace)
        self.assertEqual(payload["mode"], "prepare_only")
        self.assertEqual(len(payload["nodes"]), 5)
        self.assertEqual(len({row["proposed_json"] for row in payload["nodes"]}), 5)
        for row in payload["nodes"]:
            validate_schema(row["draft"])
            self.assertFalse(self.workspace.resolve_target(row["proposed_json"]).exists())
        self.assertEqual(payload["nodes"][0]["draft"]["profile"]["institution_keys"], ["UnADM"])

    def test_agent_rejects_draft_before_planner_or_llm(self):
        from aulatex.agent import AgentRequest, AulaTeXAgent

        scope = self.scopes["actividad"]
        path, _markdown = publish_plan(self.workspace, scope, draft_plan(scope))
        agent = AulaTeXAgent.__new__(AulaTeXAgent)
        agent.workspace = self.workspace
        request = AgentRequest(target=scope.relative_path, level="actividad", action="realizar-actividad", node_plan=self.workspace.relative(path))
        with self.assertRaisesRegex(ValueError, "pendiente"):
            agent.run(request)
        self.assertFalse((self.workspace.feedback_root / "runs").exists())

    def test_preparation_writes_only_manifest_and_preserves_existing(self):
        output = self.root / "preparation"
        paths = write_propagation(self.workspace, output)
        self.assertEqual(len(paths), 2)
        self.assertEqual(len(json.loads(paths[0].read_text(encoding="utf-8"))["nodes"]), 5)
        with self.assertRaises(FileExistsError):
            write_propagation(self.workspace, output)
        self.assertFalse(any(self.root.rglob("planeacion.json")))

    def test_direct_subject_does_not_become_a_career(self):
        subject = self.root / "UnADM/direct-subject"
        subject.mkdir()
        (subject / "reporte.tex").write_text("fixture", encoding="utf-8")
        payload = prepare_propagation(self.workspace)
        institution = next(row for row in payload["nodes"] if row["node"]["level"] == "institucion")
        self.assertEqual(institution["draft"]["profile"]["subject_keys"], ["UnADM/direct-subject"])
        self.assertNotIn("UnADM/direct-subject", institution["draft"]["profile"]["program_keys"])

    def test_uadec_medical_career_is_included_in_propagation(self):
        subject = self.root / "UAdeC/medico-cirujano/anatomia"
        subject.mkdir(parents=True)
        (subject / "reporte-Actividad-1.tex").write_text("fixture", encoding="utf-8")
        payload = prepare_propagation(self.workspace)
        keys = {row["node"]["key"] for row in payload["nodes"]}
        self.assertIn("UAdeC", keys)
        self.assertIn("UAdeC/medico-cirujano", keys)
        self.assertIn("UAdeC/medico-cirujano/anatomia/actividad-1", keys)

    def test_pedagogical_profile_is_selected_locally_and_checks_identity(self):
        from aulatex.node_planning import PEDAGOGICAL_SCHEMA_PATH

        document = json.loads(PEDAGOGICAL_SCHEMA_PATH.with_name("planeacion-canonica.ejemplo.json").read_text(encoding="utf-8"))
        document["identity"]["subject_id"] = self.scopes["materia"].subject
        another = json.loads(json.dumps(document["activities"][0]))
        another["id"] = "act-002"
        another["instruction"] = "Instruccion de otra actividad; no mezclar en el extractor."
        document["activities"].append(another)
        document_path = self.root / "pedagogical.json"
        document_path.write_text(json.dumps(document), encoding="utf-8")
        scope = self.scopes["actividad"]
        model = draft_plan(scope)
        model["profile"]["activity_id"] = "act-001"
        model["profile"]["offering_id"] = document["identity"]["offering_id"]
        model["bindings"]["pedagogical_plan"] = {"path": "pedagogical.json", "sha256": hashlib.sha256(document_path.read_bytes()).hexdigest(), "activity_id": "act-001"}
        path, _markdown = publish_plan(self.workspace, scope, model)
        resolved = NodePlanLoader(self.workspace).load(self.workspace.relative(path), scope)
        self.assertEqual(len(resolved.pedagogical_plan["activities"]), 2)
        self.assertEqual(resolved.selected_activity_id, "act-001")
        self.assertNotIn(another["instruction"], resolved.extractor_markdown())
        self.assertIn("Actividad:", resolved.extractor_markdown())
        self.assertIn("req-001", resolved.context_markdown())
        model["profile"]["offering_id"] = "another-offering"
        model["revision"] = 2
        path, _markdown = publish_plan(self.workspace, scope, model)
        with self.assertRaisesRegex(ValueError, "oferta"):
            NodePlanLoader(self.workspace).load(self.workspace.relative(path), scope)

    def test_semantic_validation_rejects_ready_label_without_evidence(self):
        from aulatex.node_planning import PEDAGOGICAL_SCHEMA_PATH
        from aulatex.planning_validation import validate_pedagogical

        document = json.loads(PEDAGOGICAL_SCHEMA_PATH.with_name("planeacion-canonica.ejemplo.json").read_text(encoding="utf-8"))
        document["review"] = {"state": "ready", "semantic_validation": "passed", "critical_gaps": [], "reviewed_at": "2026-10-26", "reviewer_role": "fixture"}
        report = validate_pedagogical(document, self.root, "act-001")
        self.assertFalse(report["passed"])
        self.assertIn("instruction_not_confirmed", {item["code"] for item in report["findings"]})

    def test_semantic_validation_checks_ids_rubric_and_pointers(self):
        from aulatex.node_planning import PEDAGOGICAL_SCHEMA_PATH
        from aulatex.planning_validation import validate_pedagogical

        document = json.loads(PEDAGOGICAL_SCHEMA_PATH.with_name("planeacion-canonica.ejemplo.json").read_text(encoding="utf-8"))
        activity = document["activities"][0]
        activity["requirements"].append(dict(activity["requirements"][0]))
        activity["assessment"]["scale_total"] = 15
        activity["assessment"]["criteria"] = [{"id": "criterion-1", "text": "fixture", "points": 2, "descriptors": [], "requirement_ids": ["missing-id"]}]
        document["field_status"][0]["path"] = "/does-not-exist"
        codes = {item["code"] for item in validate_pedagogical(document, self.root)["findings"]}
        self.assertTrue({"duplicate_id", "rubric_total_mismatch", "unresolved_pointer", "unresolved_reference"}.issubset(codes))

    def test_semantic_validation_requires_product_rubric_and_calendar_evidence(self):
        from aulatex.node_planning import PEDAGOGICAL_SCHEMA_PATH
        from aulatex.planning_validation import validate_pedagogical

        document = json.loads(PEDAGOGICAL_SCHEMA_PATH.with_name("planeacion-canonica.ejemplo.json").read_text(encoding="utf-8"))
        activity = document["activities"][0]
        activity["assessment"]["scale_total"] = 2
        activity["assessment"]["criteria"] = [{"id": "criterion-1", "text": "fixture", "points": 2, "descriptors": [], "requirement_ids": []}]
        activity["calendar"]["due_at"] = "2026-10-26T12:00:00"
        paths = {item["path"] for item in validate_pedagogical(document, self.root)["findings"] if item["code"] == "instruction_not_confirmed"}
        self.assertIn("/activities/0/products/0", paths)
        self.assertIn("/activities/0/assessment/criteria/0", paths)
        self.assertIn("/activities/0/assessment/scale_total", paths)
        self.assertIn("/activities/0/calendar/due_at", paths)

    def test_ready_publication_requires_archived_review_and_preserves_markdown_state(self):
        from jsonschema import ValidationError
        from aulatex.node_planning import PEDAGOGICAL_SCHEMA_PATH
        from aulatex.planning_conversion import publish_conversion

        subject = self.scopes["materia"]
        root = self.workspace.resolve_target(subject.relative_path)
        source = root / "instruction.txt"
        source.write_text("Verified fixture instruction", encoding="utf-8")
        document = json.loads(PEDAGOGICAL_SCHEMA_PATH.with_name("planeacion-canonica.ejemplo.json").read_text(encoding="utf-8"))
        document["identity"]["subject_id"] = subject.subject
        document["sources"][0].update(authority="instructional", path="instruction.txt", sha256=hashlib.sha256(source.read_bytes()).hexdigest())
        document["field_status"] = [{"path": "/activities/0", "state": "confirmed", "reason": "Isolated test fixture", "evidence": [{"source_id": "src-001", "locator": "document", "quoted_text": "Verified fixture instruction"}], "alternatives": []}]
        document["review"] = {"state": "ready", "semantic_validation": "passed", "critical_gaps": [], "reviewed_at": "2026-10-26", "reviewer_role": "test-fixture"}
        result = publish_conversion(self.workspace, subject, document)
        self.assertEqual(result["state"], "ready")
        self.assertIn("Estado: ready", self.workspace.resolve_target(result["artifacts"][1]).read_text(encoding="utf-8"))
        document["revision"] = 2
        document["review"]["reviewed_at"] = None
        with self.assertRaises(ValidationError):
            publish_conversion(self.workspace, subject, document)
        document["review"]["reviewed_at"] = "2026-10-26"
        document["sources"][0]["authority"] = "editorial"
        with self.assertRaisesRegex(ValueError, "review_not_validated"):
            publish_conversion(self.workspace, subject, document)

    def test_activity_review_and_empty_pilot_do_not_approve_drafts(self):
        from aulatex.planning_conversion import convert_local_batch
        from aulatex.planning_review import observe_planning, prepare_campaign, review_batch, run_campaign

        subject = self.scopes["materia"]
        root = self.workspace.resolve_target(subject.relative_path)
        folder = root / "planeaciones-materia"
        folder.mkdir()
        (folder / "consigna.md").write_text("Fixture sin segmentar", encoding="utf-8")
        convert_local_batch(self.workspace, self.root / "batch", publish_bindings=True)
        result = review_batch(self.workspace, "batch", self.root / "review")
        self.assertEqual(result["counts"]["activity_records"], 1)
        self.assertEqual(result["counts"]["approved_nodes"], 0)
        pilot = prepare_campaign(self.workspace, "review/cotejo-actividades.json", self.root / "pilot")
        self.assertEqual(pilot["state"], "blocked")
        self.assertFalse(pilot["monitor"]["enabled"])
        with self.assertRaisesRegex(ValueError, "campaign_blocked"):
            run_campaign(self.workspace, "pilot/campana-piloto.json", self.root / "runs")
        self.assertFalse((self.root / "runs").exists())
        snapshot = observe_planning(self.workspace, "review/cotejo-actividades.json", self.root / "diagnostic")
        self.assertEqual(snapshot["counts"]["observed_records"], 1)
        self.assertEqual(snapshot["counts"]["changed_records"], 0)
        self.assertFalse(snapshot["editorial_execution"])
        reviewed_path = self.workspace.resolve_target(result["records"][0]["path"])
        reviewed_path.write_bytes(reviewed_path.read_bytes() + b" ")
        changed = observe_planning(self.workspace, "review/cotejo-actividades.json", self.root / "changed-diagnostic")
        self.assertEqual(changed["counts"]["changed_records"], 1)
        self.assertIn("reviewed_plan_hash_changed", {item["code"] for item in changed["records"][0]["findings"]})
        with self.assertRaises(ValueError):
            prepare_campaign(self.workspace, "review/cotejo-actividades.json", self.root / "too-wide", max_activities=6)

    def test_monitor_rejects_draft_before_creating_run_or_planning(self):
        from aulatex.activity_monitor import ActivityMonitor, ActivityMonitorRequest

        scope = self.scopes["actividad"]
        path, _markdown = publish_plan(self.workspace, scope, draft_plan(scope))
        monitor = ActivityMonitor.__new__(ActivityMonitor)
        monitor.workspace = self.workspace
        with self.assertRaisesRegex(ValueError, "pendiente"):
            monitor.run(ActivityMonitorRequest(target=scope.relative_path, node_plan=self.workspace.relative(path)))
        self.assertFalse((self.workspace.feedback_root / "activity-monitor").exists())

    def test_pilot_admits_ready_revision_and_revalidates_source_before_monitor(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from aulatex.node_planning import PEDAGOGICAL_SCHEMA_PATH
        from aulatex.planning_conversion import publish_conversion
        from aulatex.planning_review import prepare_campaign, run_campaign

        subject = self.scopes["materia"]
        source = self.workspace.resolve_target(subject.relative_path) / "instruction.txt"
        source.write_text("Instruction for isolated fixture", encoding="utf-8")
        document = json.loads(PEDAGOGICAL_SCHEMA_PATH.with_name("planeacion-canonica.ejemplo.json").read_text(encoding="utf-8"))
        document["identity"]["subject_id"] = subject.subject
        document["sources"][0].update(authority="instructional", path="instruction.txt", sha256=hashlib.sha256(source.read_bytes()).hexdigest())
        document["field_status"] = [{"path": "/activities/0", "state": "confirmed", "reason": "Isolated fixture", "evidence": [{"source_id": "src-001", "locator": "document", "quoted_text": "Instruction for isolated fixture"}], "alternatives": []}]
        document["review"] = {"state": "ready", "semantic_validation": "passed", "critical_gaps": [], "reviewed_at": "2026-10-26", "reviewer_role": "test-fixture"}
        publication = publish_conversion(self.workspace, subject, document)
        scope = self.scopes["actividad"]
        model = draft_plan(scope)
        model["review"] = {"state": "ready", "semantic_validation": "passed", "critical_gaps": []}
        model["profile"].update(activity_id="act-001", offering_id=document["identity"]["offering_id"])
        pedagogical_path = self.workspace.resolve_target(publication["pedagogical_json"])
        model["bindings"]["pedagogical_plan"] = {"path": publication["pedagogical_json"], "sha256": hashlib.sha256(pedagogical_path.read_bytes()).hexdigest(), "activity_id": "act-001"}
        node_path, _markdown = publish_plan(self.workspace, scope, model)
        entry = {"scope_key": scope.key, "level": "actividad", "path": self.workspace.relative(node_path), "sha256": hashlib.sha256(node_path.read_bytes()).hexdigest()}
        (self.root / "review.json").write_text(json.dumps({"approved": [entry]}), encoding="utf-8")
        pilot = prepare_campaign(self.workspace, "review.json", self.root / "pilot")
        self.assertEqual(pilot["state"], "enabled")
        self.assertEqual(pilot["activities"][0]["activity_id"], "act-001")
        (self.root / "monitor.json").write_text("{}", encoding="utf-8")
        (self.root / "monitor.md").write_text("Fixture", encoding="utf-8")
        with patch("aulatex.activity_monitor.ActivityMonitor") as monitor:
            monitor.return_value.run.return_value = SimpleNamespace(ok=True, manifest_path=self.root / "monitor.json", report_path=self.root / "monitor.md")
            result = run_campaign(self.workspace, "pilot/campana-piloto.json", self.root / "result")
            self.assertFalse(result["stopped_on_blocker"])
            request = monitor.return_value.run.call_args.args[0]
            self.assertEqual(request.node_plan, entry["path"])
            self.assertFalse(request.apply_revision_patches)
            self.assertFalse(request.run_detail_planner)
            source.write_text("Changed source", encoding="utf-8")
            monitor.reset_mock()
            with self.assertRaises(ValueError):
                run_campaign(self.workspace, "pilot/campana-piloto.json", self.root / "changed")
            monitor.assert_not_called()
        self.assertFalse((self.root / "changed").exists())

    def test_classic_monitor_stops_on_observed_blocker_without_undefined_action(self):
        from unittest.mock import Mock
        from aulatex.activity_monitor import ActivityMonitor, ActivityMonitorRequest

        monitor = ActivityMonitor.__new__(ActivityMonitor)
        record = {"next_action": "blocked", "executed_action": "", "action_result": {}}
        monitor._observe_cycle = Mock(return_value=(record, {"passed": False}))
        cycles, passed = monitor._run_classic(ActivityMonitorRequest(target=".", max_cycles=1, run_detail_planner=False), self.root / "classic")
        self.assertFalse(passed)
        self.assertEqual(len(cycles), 1)

    def test_penal_later_segmentation_preserves_questions_and_rubric_conflicts(self):
        from aulatex.node_planning import PEDAGOGICAL_SCHEMA_PATH
        from aulatex.planning_validation import validate_pedagogical
        from cotejar_penal_s3 import segment_later_document

        for week in (4, 5):
            with self.subTest(week=week):
                document = json.loads(PEDAGOGICAL_SCHEMA_PATH.with_name("planeacion-canonica.ejemplo.json").read_text(encoding="utf-8"))
                document["extensions"] = {"conversion": {"unsegmented_document": True, "activity_mapping": []}}
                if week == 4:
                    content = "Caso 1. Uno\nHechos uno\nResponde:\na) Pregunta uno\nb) Pregunta dos\nCaso 2. Dos\nHechos dos\nResponde:\na) Pregunta tres\nb) Pregunta cuatro\nCaso 3. Tres\nHechos tres\nResponde:\na) Pregunta cinco\nb) Pregunta seis\n3. Decisión fundamentada\nCierre"
                else:
                    content = "Para estudiar cualquier hecho, sigue este orden:\nA. Quién\nB. Conducta\nC. Requisito\nD. Evidencia\nE. Clasificación\nEjemplo: ficticio\nFicha 1. Uno\nHechos uno\nFicha 2. Dos\nHechos dos\nFicha 3. Tres\nHechos tres\n4. Informe breve y entrega\nCierre"
                blocks = [{"locator": f"page:{number}", "text": content if number == 6 else "Fixture"} for number in (4, 6, 7, 8, 9)]
                revised = segment_later_document(document, blocks, week)
                validate_schema(revised, PEDAGOGICAL_SCHEMA_PATH)
                self.assertTrue(document["extensions"]["conversion"]["unsegmented_document"])
                self.assertFalse(revised["extensions"]["conversion"]["unsegmented_document"])
                self.assertEqual(len(revised["activities"][0]["questions"]), 6 if week == 4 else 15)
                self.assertEqual(revised["extensions"]["cotejo"]["rubric_points"], 10 if week == 4 else 17)
                self.assertEqual(revised["review"]["state"], "needs_review")
                codes = {item["code"] for item in validate_pedagogical(revised, self.root)["findings"]}
                self.assertIn("unresolved_conflict", codes)
                if week == 5:
                    self.assertIn("rubric_total_mismatch", codes)
                    self.assertEqual(len(revised["activities"][0]["assessment"]["criteria"]), 7)
                    self.assertIn("Hechos conocidos / Elementos legales identificados", revised["activities"][0]["requirements"][1]["text"])

    def test_markdown_renders_null_calendar_blank_and_preserves_formal_blocks(self):
        from aulatex.node_planning import PEDAGOGICAL_SCHEMA_PATH
        from aulatex.planning_conversion import render_pedagogical_markdown

        document = json.loads(PEDAGOGICAL_SCHEMA_PATH.with_name("planeacion-canonica.ejemplo.json").read_text(encoding="utf-8"))
        calendar = document["activities"][0]["calendar"]
        calendar.update(opens_at=None, expected_at=None, due_at=None, closes_at=None, timezone=None, literal="Fecha documental historica: 18 octubre")
        original = json.dumps(document, sort_keys=True)
        markdown = render_pedagogical_markdown(document)
        for field in ("opens_at", "expected_at", "due_at", "closes_at", "timezone"):
            self.assertIn(f"| {field} |  |", markdown)
        for field in ("alignment", "bindings", "dependencies", "outcome_ids", "topic_ids", "curriculum", "artifact_contract"):
            self.assertIn("# " + field, markdown)
        self.assertIn("Evidencia historica del calendario (no programacion operativa)", markdown)
        self.assertIn(calendar["literal"], markdown)
        self.assertEqual(json.dumps(document, sort_keys=True), original)

    def test_conversion_preserves_source_without_inventing_rubric_or_deadline(self):
        from aulatex.planning_conversion import convert_source, publish_conversion

        subject = self.scopes["materia"]
        source = self.workspace.resolve_target(subject.relative_path) / "planeacion.json"
        payload = {"institution": "UnADM", "period": "2026-2", "activity": {"id": "6545", "title": "fixture", "requirements": ["Primer requisito", "Segundo requisito"], "proposed_objective": "Objetivo propuesto", "topic": "Tema documentado", "proposed_sequence": ["Propuesta editorial"], "calendar": {"expected_at": "2026-10-26T12:00:00"}}}
        source.write_text(json.dumps(payload), encoding="utf-8")
        original = source.read_bytes()
        document, mapping = convert_source(self.workspace, subject, source)
        self.assertEqual(document["extensions"]["conversion"]["source_payload"], payload)
        self.assertEqual(document["activities"][0]["instruction"], "Primer requisito\nSegundo requisito")
        self.assertIsNone(document["activities"][0]["calendar"]["closes_at"])
        self.assertIsNone(document["activities"][0]["assessment"]["scale_total"])
        self.assertEqual(mapping[0]["activity_id"], "6545")
        self.assertEqual(document["curriculum"]["outcomes"][0]["text"], "Objetivo propuesto")
        self.assertEqual(document["activities"][0]["outcome_ids"], ["outcome-6545"])
        status = next(item for item in document["field_status"] if item["path"] == "/curriculum/outcomes/0")
        self.assertEqual(status["state"], "inferred")
        result = publish_conversion(self.workspace, subject, document)
        self.assertEqual(result["state"], "needs_review")
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(result, publish_conversion(self.workspace, subject, document))
        payload["activity"]["requirements"].append("Nuevo requisito")
        source.write_text(json.dumps(payload), encoding="utf-8")
        changed, _mapping = convert_source(self.workspace, subject, source)
        self.assertEqual(changed["plan_id"], document["plan_id"])
        self.assertEqual(changed["revision"], 2)
        publish_conversion(self.workspace, subject, changed)
        self.assertEqual(self.workspace.resolve_target(result["pedagogical_json"]).read_text(encoding="utf-8"), json.dumps(document, ensure_ascii=False, indent=2) + "\n")

    def test_conversion_batch_maps_only_explicit_activity_number(self):
        from aulatex.planning_conversion import convert_local_batch
        from aulatex.planning_layout import subject_layout

        subject = self.scopes["materia"]
        folder = subject_layout(self.workspace.resolve_target(subject.relative_path))["plans"]
        folder.mkdir()
        payload = {"activity": {"id": 6545, "title": "fixture", "requirements": "Texto completo"}, "chronological_numbering": {"local_number": 1}}
        (folder / "planeacion-actividad-1.json").write_text(json.dumps(payload), encoding="utf-8")
        result = convert_local_batch(self.workspace, self.root / "batch")
        self.assertEqual(result["converted"], 1)
        self.assertEqual(result["ready"], 0)
        self.assertEqual(result["records"][0]["candidate_node_bindings"][0]["scope_key"], self.scopes["actividad"].key)
        with self.assertRaises(FileExistsError):
            convert_local_batch(self.workspace, self.root / "batch")

    def test_catalog_batch_reuses_json_and_excludes_history_without_publishing(self):
        from aulatex.planning_conversion import convert_local_batch, convert_source
        from aulatex.planning_layout import catalogued_plan_paths, subject_layout
        from aulatex.planning_review import review_batch

        subject = self.scopes["materia"]
        root = self.workspace.resolve_target(subject.relative_path)
        folder = subject_layout(root)["plans"]
        folder.mkdir()
        original = folder / "planeacion-modulo-6545.json"
        original.write_text(json.dumps({"activity": {"id": 6545, "title": "fixture", "requirements": "Teacher text"}}), encoding="utf-8")
        document, _mapping = convert_source(self.workspace, subject, original)
        active = folder / "planeacion-materia-Actividad-1.json"
        active.write_text(json.dumps(document), encoding="utf-8")
        active.with_suffix(".md").write_text("Derived, not a source", encoding="utf-8")
        forum = folder / "planeacion-modulo-1726.json"
        forum.write_text(json.dumps({"activity": {"id": 1726, "title": "Avisos", "requirements": "History only"}}), encoding="utf-8")
        catalog = {"activities": [{"number": 1, "module_id": "6545", "json": active.relative_to(root).as_posix()}], "antecedents": [{"module_id": "1726"}]}
        (folder / "catalogo-editorial.json").write_text(json.dumps(catalog), encoding="utf-8")
        before = {path: path.read_bytes() for path in folder.rglob("*") if path.is_file()}
        self.assertEqual(catalogued_plan_paths(root), (active,))
        result = convert_local_batch(self.workspace, self.root / "batch", publish_bindings=True)
        self.assertEqual(result["converted"], 0)
        self.assertEqual(result["catalogued"], 1)
        self.assertEqual(result["node_plans_published"], 0)
        self.assertEqual([row["source"] for row in result["records"]], [self.workspace.relative(active)])
        review = review_batch(self.workspace, "batch", self.root / "review")
        self.assertEqual([row["activity_id"] for row in review["records"]], ["6545"])
        self.assertEqual(before, {path: path.read_bytes() for path in folder.rglob("*") if path.is_file()})

    def test_catalog_accepts_archived_instructions_without_moodle_ids(self):
        from aulatex.planning_layout import catalogued_plan_paths, subject_layout

        root = self.workspace.resolve_target(self.scopes["materia"].relative_path)
        folder = subject_layout(root)["plans"]
        folder.mkdir()
        paths = []
        entries = []
        for number in (1, 2):
            path = folder / f"planeacion-materia-Actividad-{number}.json"
            path.write_text("{}", encoding="utf-8")
            paths.append(path)
            entries.append({"number": number, "module_id": None, "json": path.relative_to(root).as_posix()})
        catalog = {"activities": entries, "antecedents": [{"module_id": None}]}
        (folder / "catalogo-editorial.json").write_text(json.dumps(catalog), encoding="utf-8")
        self.assertEqual(catalogued_plan_paths(root), tuple(paths))
        catalog["activities"][1]["number"] = 1
        (folder / "catalogo-editorial.json").write_text(json.dumps(catalog), encoding="utf-8")
        with self.assertRaises(ValueError):
            catalogued_plan_paths(root)

    def test_catalog_rejects_duplicates_excluded_modules_and_unsafe_paths(self):
        from aulatex.planning_layout import catalogued_plan_paths, subject_layout

        root = self.workspace.resolve_target(self.scopes["materia"].relative_path)
        folder = subject_layout(root)["plans"]
        folder.mkdir()
        active = folder / "planeacion-materia-Actividad-1.json"
        active.write_text("{}", encoding="utf-8")
        entry = {"number": 1, "module_id": "1726", "json": active.relative_to(root).as_posix()}
        for catalog in (
            {"activities": [entry, entry]},
            {"activities": [entry], "antecedents": [{"module_id": "1726"}]},
            {"activities": [dict(entry, json="../../outside.json")]},
            {"activities": [dict(entry, json="planeaciones-materia/missing.json")]},
        ):
            with self.subTest(catalog=catalog):
                (folder / "catalogo-editorial.json").write_text(json.dumps(catalog), encoding="utf-8")
                with self.assertRaises(ValueError):
                    catalogued_plan_paths(root)
        (folder / "catalogo-editorial.json").write_text('{"activities": []}', encoding="utf-8")
        self.assertEqual(catalogued_plan_paths(root), ())

    def test_catalog_includes_unnumbered_forum_without_omitting_it(self):
        from aulatex.planning_layout import catalogued_plan_paths, subject_layout

        root = self.workspace.resolve_target(self.scopes["materia"].relative_path)
        folder = subject_layout(root)["plans"]
        folder.mkdir()
        forum = folder / "planeacion-materia-Foro-presentacion.json"
        forum.write_text("{}", encoding="utf-8")
        entry = {"number": None, "module_id": "2876", "json": forum.relative_to(root).as_posix()}
        catalog = {"activities": [], "complementary_plans": [entry], "antecedents": []}
        catalog_path = folder / "catalogo-editorial.json"
        catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
        self.assertEqual(catalogued_plan_paths(root), (forum,))
        catalog["antecedents"] = [{"module_id": "2876"}]
        catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "excluded"):
            catalogued_plan_paths(root)
        catalog["antecedents"] = []
        entry["number"] = 1
        catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
        with self.assertRaises(ValueError):
            catalogued_plan_paths(root)

    def test_text_conversion_preserves_full_document_and_marks_unsegmented(self):
        from aulatex.planning_conversion import convert_source

        subject = self.scopes["materia"]
        source = self.workspace.resolve_target(subject.relative_path) / "consigna.md"
        text = "Tema: uno\nActividad: dos\nPreguntas completas en otro PDF: pendiente.\n"
        source.write_text(text, encoding="utf-8")
        document, _mapping = convert_source(self.workspace, subject, source)
        self.assertEqual(document["extensions"]["conversion"]["source_blocks"][0]["text"], text)
        self.assertTrue(document["extensions"]["conversion"]["unsegmented_document"])
        self.assertEqual(document["review"]["state"], "needs_review")
        self.assertIsNone(document["activities"][0]["platform"])

    def test_legacy_root_activity_is_converted_but_index_is_not(self):
        from aulatex.planning_conversion import convert_source, publish_candidate_nodes, publish_conversion

        subject = self.scopes["materia"]
        source = self.workspace.resolve_target(subject.relative_path) / "planeacion-actividad-1.json"
        payload = {"activity_id_local": 1, "moodle_module_id": 7780, "title": "fixture", "product": {"type": "audio", "content_requirements": [{"description": "Requisito de audio"}]}, "sequence": [{"phase": "preparacion", "student": "Leer consigna"}]}
        source.write_text(json.dumps(payload), encoding="utf-8")
        document, mapping = convert_source(self.workspace, subject, source)
        self.assertEqual(document["activities"][0]["id"], "7780")
        self.assertEqual(document["activities"][0]["requirements"][0]["text"], "Requisito de audio")
        self.assertEqual(document["activities"][0]["sequence"][0]["phase"], "preparation")
        result = publish_conversion(self.workspace, subject, document)
        result["candidate_node_bindings"] = [{"scope_key": self.scopes["actividad"].key, "activity_id": "7780", "offering_id": document["identity"]["offering_id"]}]
        registry = publish_candidate_nodes(self.workspace, [result])
        self.assertEqual(len(registry["pending"]), 5)
        self.assertFalse(registry["approved"])
        node = next(row for row in registry["pending"] if row["level"] == "actividad")
        loaded = NodePlanLoader(self.workspace).load(node["path"], self.scopes["actividad"])
        self.assertEqual(loaded.selected_activity_id, "7780")
        self.assertEqual(len(loaded.chain), 5)
        with self.assertRaisesRegex(ValueError, "pendiente"):
            NodePlanLoader(self.workspace).load(node["path"], self.scopes["actividad"], require_ready=True)
        source.write_text(json.dumps({"document_type": "planning_index", "activities": []}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "auxiliary_planning_index"):
            convert_source(self.workspace, subject, source)

    def test_pdf_conversion_preserves_all_pages_without_silent_approval(self):
        import pymupdf
        from aulatex.planning_conversion import convert_source

        subject = self.scopes["materia"]
        source = self.workspace.resolve_target(subject.relative_path) / "planificacion.pdf"
        with pymupdf.open() as document:
            document.new_page().insert_text((72, 72), "Primera consigna completa")
            document.new_page().insert_text((72, 72), "Segunda consigna y preguntas")
            document.save(source)
        payload, _mapping = convert_source(self.workspace, subject, source)
        blocks = payload["extensions"]["conversion"]["source_blocks"]
        self.assertEqual([item["locator"] for item in blocks], ["page:1", "page:2"])
        self.assertIn("Segunda consigna", blocks[1]["text"])
        self.assertTrue(payload["extensions"]["conversion"]["unsegmented_document"])

    def test_unadm_segmentation_preserves_text_and_handles_pdf_spacing(self):
        from organizar_planeaciones_unadm import segment

        text = "Preliminares\nActividad    5: Cuadro\nTabla y hechos intactos\nActividad 6: Parcial\nCinco reactivos\nEvidencia de la evaluacion"
        self.assertEqual(segment(text, "Actividad 5:", "Actividad 6:"), "Actividad    5: Cuadro\nTabla y hechos intactos\n")
        self.assertEqual(segment(text, "Actividad 6:", "Evidencia de la evaluaci"), "Actividad 6: Parcial\nCinco reactivos\n")
        with self.assertRaises(ValueError):
            segment(text, "Actividad 7:", "Actividad 8:")

    def test_unadm_scope_and_official_numbers_are_explicit(self):
        from organizar_planeaciones_unadm import SPECS, SUBJECTS

        self.assertEqual(len(SUBJECTS), 3)
        self.assertNotIn("ITESCA", str(SUBJECTS))
        antecedents = SPECS["antecedentes-de-los-derechos-humanos"]
        self.assertEqual([row[0] for row in antecedents], list(range(1, 9)))
        self.assertEqual([(row[0], row[1]) for row in antecedents if row[0] in (3, 5, 7)], [(3, 1), (5, 3), (7, 5)])
        self.assertEqual(antecedents[7][5], "platform_response")

    def test_unadm_model_preserves_original_and_never_approves_calendar_cleanup(self):
        from aulatex.node_planning import PEDAGOGICAL_SCHEMA_PATH
        from organizar_planeaciones_unadm import build_model

        slug = "derecho-penal-especial-mexicano"
        subject = self.root / f"{slug}-lde"
        subject.mkdir()
        (subject / "README.md").write_text("Control editorial de fixture", encoding="utf-8")
        document = json.loads(PEDAGOGICAL_SCHEMA_PATH.with_name("planeacion-canonica.ejemplo.json").read_text(encoding="utf-8"))
        document["extensions"] = {"conversion": {"unsegmented_document": False, "source_blocks": [], "activity_mapping": []}}
        document["activities"][0]["calendar"]["due_at"] = "2026-10-18T23:55:00"
        original_path = subject / "previous.json"
        original_path.write_text(json.dumps(document), encoding="utf-8")
        original = json.dumps(document, sort_keys=True)
        spec = (3, None, 3, "216751", "Estudio de casos", "report", "fixture", None)
        model = build_model(subject, slug, spec, {"fixture": (original_path, document)})
        self.assertEqual(json.dumps(document, sort_keys=True), original)
        self.assertIsNone(model["activities"][0]["calendar"]["due_at"])
        self.assertEqual(model["extensions"]["organizacion_interna"]["original_calendar"]["due_at"], "2026-10-18T23:55:00")
        self.assertEqual(model["review"]["state"], "needs_review")
        self.assertFalse(model["extensions"]["organizacion_interna"]["integration_complete"])

    def test_review_queue_covers_activity_without_guessing_binding(self):
        from aulatex.planning_conversion import convert_local_batch

        output = self.root / "queue"
        convert_local_batch(self.workspace, output)
        queue = json.loads((output / "cola-cotejo.json").read_text(encoding="utf-8"))
        self.assertEqual(len(queue["activities"]), 1)
        self.assertEqual(queue["activities"][0]["state"], "pending_source_mapping")
        self.assertFalse(queue["activities"][0]["ready"])


if __name__ == "__main__":
    unittest.main()