import json
import tempfile
import unittest
from pathlib import Path

from aulatex.node_planning import PEDAGOGICAL_SCHEMA_PATH
from aulatex.planning_conversion import render_pedagogical_markdown
from aulatex.planning_layout import catalogued_plan_paths
from organizar_planeaciones_unadm import SPECS, SUBJECTS, build_model, segment


class UnadmPlanningTests(unittest.TestCase):
    def test_segments_preserve_text_and_pdf_spacing(self):
        text = "Inicio\nActividad    5: Cuadro\nTabla y hechos\nActividad 6: Parcial\nCinco reactivos\nEvidencia de la evaluacion"
        self.assertEqual(segment(text, "Actividad 5:", "Actividad 6:"), "Actividad    5: Cuadro\nTabla y hechos\n")
        self.assertEqual(segment(text, "Actividad 6:", "Evidencia de la evaluaci"), "Actividad 6: Parcial\nCinco reactivos\n")
        with self.assertRaises(ValueError):
            segment(text, "Actividad 7:", "Actividad 8:")

    def test_explicit_scope_and_correspondences(self):
        self.assertEqual(len(SUBJECTS), 3)
        antecedents = SPECS["antecedentes-de-los-derechos-humanos"]
        self.assertEqual([row[0] for row in antecedents], list(range(1, 9)))
        self.assertEqual([(row[0], row[1]) for row in antecedents if row[0] in (3, 5, 7)], [(3, 1), (5, 3), (7, 5)])
        self.assertEqual(antecedents[7][5], "platform_response")

    def test_model_preserves_history_and_remains_blocked(self):
        with tempfile.TemporaryDirectory() as temporary:
            subject = Path(temporary) / "derecho-penal-especial-mexicano-lde"
            subject.mkdir()
            (subject / "README.md").write_text("Control de fixture", encoding="utf-8")
            document = json.loads(PEDAGOGICAL_SCHEMA_PATH.with_name("planeacion-canonica.ejemplo.json").read_text(encoding="utf-8"))
            document["extensions"] = {"conversion": {"unsegmented_document": False, "source_blocks": [], "activity_mapping": []}}
            document["activities"][0]["calendar"]["due_at"] = "2026-10-18T23:55:00"
            previous = subject / "previous.json"
            previous.write_text(json.dumps(document), encoding="utf-8")
            original = json.dumps(document, sort_keys=True)
            spec = (3, None, 3, "216751", "Estudio de casos", "report", "fixture", None)
            model = build_model(subject, "derecho-penal-especial-mexicano", spec, {"fixture": (previous, document)})
            self.assertEqual(json.dumps(document, sort_keys=True), original)
            self.assertIsNone(model["activities"][0]["calendar"]["due_at"])
            self.assertEqual(model["extensions"]["organizacion_interna"]["original_calendar"]["due_at"], "2026-10-18T23:55:00")
            self.assertEqual(model["review"]["state"], "needs_review")
            self.assertFalse(model["extensions"]["organizacion_interna"]["integration_complete"])

    def test_markdown_has_blank_operational_dates_and_all_blocks(self):
        document = json.loads(PEDAGOGICAL_SCHEMA_PATH.with_name("planeacion-canonica.ejemplo.json").read_text(encoding="utf-8"))
        calendar = document["activities"][0]["calendar"]
        calendar.update(opens_at=None, expected_at=None, due_at=None, closes_at=None, timezone=None, literal="Fecha historica: 18 octubre")
        original = json.dumps(document, sort_keys=True)
        markdown = render_pedagogical_markdown(document)
        for field in ("opens_at", "expected_at", "due_at", "closes_at", "timezone"):
            self.assertIn(f"| {field} |  |", markdown)
        for field in ("alignment", "bindings", "dependencies", "outcome_ids", "topic_ids", "curriculum", "artifact_contract"):
            self.assertIn("# " + field, markdown)
        self.assertIn("Fecha historica: 18 octubre", markdown)
        self.assertEqual(json.dumps(document, sort_keys=True), original)

    def test_editorial_view_is_textual_and_does_not_change_json(self):
        document = json.loads(PEDAGOGICAL_SCHEMA_PATH.with_name("planeacion-canonica.ejemplo.json").read_text(encoding="utf-8"))
        document["extensions"]["editorial_view"] = {"version": "2.0"}
        original = json.dumps(document, sort_keys=True)
        markdown = render_pedagogical_markdown(document)
        self.assertNotIn("```", markdown)
        self.assertNotIn("schema_version", markdown)
        self.assertNotIn("source_blocks", markdown)
        self.assertNotIn("sha256", markdown)
        for heading in ("Consigna docente", "Objetivos", "Temas", "Requisitos", "Preguntas y casos", "Productos y formato", "Evaluacion y rubrica", "Politicas", "Calendario operativo", "Alineacion editorial propuesta"):
            self.assertIn(heading, markdown)
        self.assertEqual(json.dumps(document, sort_keys=True), original)

    def test_historical_source_relocation_requires_exact_hash_and_safe_destination(self):
        import hashlib
        from aulatex.planning_validation import relocated_source

        with tempfile.TemporaryDirectory() as temporary:
            subject = Path(temporary) / "materia-lde"
            folder = subject / "planeaciones-materia"
            folder.mkdir(parents=True)
            destination = subject / "notas/original.pdf"
            destination.parent.mkdir()
            destination.write_bytes(b"original docente")
            sha256 = hashlib.sha256(destination.read_bytes()).hexdigest()
            movement = {"from": "planeaciones-materia/original.pdf", "to": "notas/original.pdf", "sha256": sha256}
            manifest = folder / "reubicaciones-documentales.json"
            manifest.write_text(json.dumps({"moves": [movement]}), encoding="utf-8")
            self.assertEqual(relocated_source(subject, movement["from"], sha256), destination)
            self.assertIsNone(relocated_source(subject, movement["from"], "0" * 64))
            movement["to"] = "../outside.pdf"
            manifest.write_text(json.dumps({"moves": [movement]}), encoding="utf-8")
            self.assertIsNone(relocated_source(subject, movement["from"], sha256))
            movement["to"] = "notas/original.pdf"
            manifest.write_text(json.dumps({"moves": [movement]}), encoding="utf-8")
            destination.write_bytes(b"contenido cambiado")
            self.assertIsNone(relocated_source(subject, movement["from"], sha256))

    def test_theory_history_lookup_does_not_recreate_retired_directories(self):
        from organizar_planeaciones_unadm import latest_documents, theory_history_directory

        with tempfile.TemporaryDirectory() as temporary:
            subject = Path(temporary)
            old = subject / "planeaciones-teoria-del-estado-y-constitucion"
            self.assertEqual(theory_history_directory(subject), old)
            archive = subject / "referencias-teoria-del-estado-y-constitucion/notas-teoria-del-estado-y-constitucion/materiales-generales/historico-planeaciones"
            revision = archive / "importaciones/pca-fixture/r0001"
            revision.mkdir(parents=True)
            path = revision / "planeacion.json"
            path.write_text('{"revision": 1}', encoding="utf-8")
            self.assertEqual(theory_history_directory(subject), archive)
            self.assertEqual(latest_documents(subject, "teoria-del-estado-y-constitucion")["pca-fixture"][0], path)
            self.assertFalse(old.exists())

    def test_catalog_accepts_no_moodle_and_rejects_duplicate_internal_numbers(self):
        with tempfile.TemporaryDirectory() as temporary:
            subject = Path(temporary) / "materia-lde"
            folder = subject / "planeaciones-materia"
            folder.mkdir(parents=True)
            paths = [folder / f"planeacion-materia-Actividad-{number}.json" for number in (1, 2)]
            for path in paths:
                path.write_text("{}", encoding="utf-8")
            entries = [{"number": number, "module_id": None, "json": path.relative_to(subject).as_posix()} for number, path in enumerate(paths, 1)]
            catalog = {"activities": entries}
            catalog_path = folder / "catalogo-editorial.json"
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
            self.assertEqual(catalogued_plan_paths(subject), tuple(paths))
            entries[1]["number"] = 1
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
            with self.assertRaises(ValueError):
                catalogued_plan_paths(subject)


if __name__ == "__main__":
    unittest.main()