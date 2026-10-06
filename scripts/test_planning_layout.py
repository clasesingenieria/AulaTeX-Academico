import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from aulatex.planning_layout import generate_plans, subject_layout


class PlanningLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.subject = self.root / "plan-de-negocios-mga"
        self.subject.mkdir()
        self.source = self.root / "input.json"
        self.payload = {"subject": "Plan de Negocios", "sources": [{"id": "W"}], "activities": [
            {"id": 6545, "title": "Imagen", "requirements": ["Word con logotipo"], "source_ids": ["W"]}
        ]}
        self.source.write_text(json.dumps(self.payload), encoding="utf-8")

    def test_local_layout_preserves_requirements_and_is_idempotent(self):
        paths = generate_plans(self.subject, self.source)
        self.assertEqual(paths, generate_plans(self.subject, self.source))
        model = json.loads(paths[0].read_text(encoding="utf-8"))
        self.assertEqual(model["activity"], self.payload["activities"][0])
        self.assertEqual(model["sources"], self.payload["sources"])
        self.assertTrue(all(path.is_relative_to(self.subject) for path in paths))
        self.assertTrue((self.subject / "referencias-plan-de-negocios/notas-plan-de-negocios").is_dir())
        self.assertFalse(list(self.subject.rglob(".gitignore")))
        self.assertTrue((self.subject / "referencias-plan-de-negocios/notas-plan-de-negocios/README.md").is_file())

    def test_conflict_does_not_overwrite_or_partially_publish(self):
        generate_plans(self.subject, self.source)
        original = (self.subject / "planeaciones-plan-de-negocios/planeacion-modulo-6545.json").read_bytes()
        self.payload["activities"][0]["title"] = "Otro título"
        self.source.write_text(json.dumps(self.payload), encoding="utf-8")
        with self.assertRaises(FileExistsError):
            generate_plans(self.subject, self.source)
        self.assertEqual(original, (self.subject / "planeaciones-plan-de-negocios/planeacion-modulo-6545.json").read_bytes())

    def test_invalid_identifier_does_not_create_outputs(self):
        self.payload["activities"][0]["id"] = "../../escape"
        self.source.write_text(json.dumps(self.payload), encoding="utf-8")
        with self.assertRaises(ValueError):
            generate_plans(self.subject, self.source)
        self.assertFalse(list(self.subject.iterdir()))

    def test_three_reference_subjects_use_same_pattern(self):
        for slug in ("filosofia-del-derecho", "garantias-constitucionales", "derecho-a-la-seguridad-social"):
            paths = subject_layout(self.root / f"{slug}-lde")
            self.assertEqual(paths["notes"].parts[-2:], (f"referencias-{slug}", f"notas-{slug}"))

    def test_credentials_are_rejected_before_writing(self):
        self.payload["sources"][0]["url"] = "https://example.org/?sesskey=not-a-real-secret"
        self.source.write_text(json.dumps(self.payload), encoding="utf-8")
        with self.assertRaises(ValueError):
            generate_plans(self.subject, self.source)
        self.assertFalse(list(self.subject.iterdir()))

    def test_ignored_outputs_are_rejected(self):
        subprocess.run(["git", "init", str(self.subject)], capture_output=True, check=True)
        (self.subject / ".gitignore").write_text("planeaciones-plan-de-negocios/\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Git excluye"):
            generate_plans(self.subject, self.source)
        self.assertFalse((self.subject / "planeaciones-plan-de-negocios").exists())

    def test_duplicate_identifier_is_rejected_before_writing(self):
        self.payload["activities"].append(dict(self.payload["activities"][0]))
        self.source.write_text(json.dumps(self.payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicado"):
            generate_plans(self.subject, self.source)
        self.assertFalse(list(self.subject.iterdir()))

    def test_existing_reference_index_is_preserved(self):
        references = subject_layout(self.subject)["references"]
        references.mkdir()
        index = references / "README.md"
        index.write_text("Catálogo revisado por el usuario", encoding="utf-8")
        generate_plans(self.subject, self.source)
        self.assertEqual(index.read_text(encoding="utf-8"), "Catálogo revisado por el usuario")

    def test_separate_index_preserves_existing_unit_navigation(self):
        plans = subject_layout(self.subject)["plans"]
        plans.mkdir()
        readme = plans / "README.md"
        readme.write_text("Índice por unidades", encoding="utf-8")
        generate_plans(self.subject, self.source, index_name="INDICE-GENERADAS.md")
        self.assertEqual(readme.read_text(encoding="utf-8"), "Índice por unidades")
        self.assertTrue((plans / "INDICE-GENERADAS.md").is_file())

    def test_index_cannot_escape_or_overwrite_activity(self):
        for name in ("../README.md", "planeacion-modulo-6545.md"):
            with self.assertRaises(ValueError):
                generate_plans(self.subject, self.source, index_name=name)
        self.assertFalse(list(self.subject.iterdir()))

    def test_materializer_uses_same_layout_and_preserves_existing_files(self):
        from aulatex.template_materializer import TemplateMaterializer
        from aulatex.workspace import AulaTeXWorkspace

        self.subject = self.root / "UnADM" / "licenciatura-en-derecho-unadm" / "filosofia-del-derecho-lde"
        self.subject.mkdir(parents=True)
        readme = self.subject / "README.md"
        readme.write_text("Materia revisada", encoding="utf-8")
        result = TemplateMaterializer(AulaTeXWorkspace(self.root)).materialize_subject(self.subject, force=False)
        self.assertTrue(result.ok)
        self.assertEqual(readme.read_text(encoding="utf-8"), "Materia revisada")
        structure = json.loads((self.subject / "estructura-aulatex.json").read_text(encoding="utf-8"))
        self.assertEqual(structure["schema_version"], "1.0")
        self.assertEqual(structure["kind"], "subject_file_inventory")
        for folder in subject_layout(self.subject).values():
            self.assertTrue(folder.is_dir())
            self.assertIn(folder.relative_to(self.subject).as_posix(), structure["folders"])

    def test_materializer_rejects_other_institutions_without_writing(self):
        from aulatex.template_materializer import TemplateMaterializer
        from aulatex.workspace import AulaTeXWorkspace

        materializer = TemplateMaterializer(AulaTeXWorkspace(self.root))
        for institution in ("ITESCA", "UCNL", "UANL", "UAS", "IIIEPE", "tecnmNL"):
            target = self.root / institution / "programa" / "materia"
            result = materializer.materialize_subject(target, force=True)
            self.assertFalse(result.ok)
            self.assertFalse(target.exists())
            self.assertFalse(result.artifacts)

    def test_materializer_preserves_existing_deliverable_by_default(self):
        from aulatex.template_materializer import TemplateMaterializer
        from aulatex.workspace import AulaTeXWorkspace

        target = self.root / "UnADM" / "licenciatura-en-derecho-unadm" / "filosofia-del-derecho-lde"
        target.mkdir(parents=True)
        report = target / "reporte-filosofia-del-derecho-Actividad-1.tex"
        report.write_bytes(b"Documento revisado por el usuario")
        result = TemplateMaterializer(AulaTeXWorkspace(self.root)).materialize_subject(target)
        self.assertTrue(result.ok)
        self.assertEqual(report.read_bytes(), b"Documento revisado por el usuario")

    def test_materializer_rejects_similarly_named_external_program(self):
        from aulatex.template_materializer import TemplateMaterializer
        from aulatex.workspace import AulaTeXWorkspace

        target = self.root / "otra-carpeta" / "UnADM" / "licenciatura-en-derecho-unadm" / "materia"
        result = TemplateMaterializer(AulaTeXWorkspace(self.root)).materialize_subject(target)
        self.assertFalse(result.ok)
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()