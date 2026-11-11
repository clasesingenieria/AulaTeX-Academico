"""Pruebas unitarias e integrales para el flujo académico de UAS en AulaTeX.

Verifica:
1. Confinamiento seguro de origen y sanitización en NavegacionUasAgent.
2. Generación canónica de planeación (JSON + MD) con RealizarPlaneacionUasAgent.
3. Localización y trazabilidad SHA-256 de recursos con EncontrarRecursosUasAgent.
4. Extracción ontológica de conceptos con ExtraerConceptosUasAgent en la carpeta de notas.
5. Realización de actividad con plantilla UAS, estilo-escribir y EMS con RealizarActividadUasAgent.
6. Orquestación secuencial completa mediante FlujoUasOrchestrator.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from aulaTEX.aulatex.encontrar_recursos_uas import (
    EncontrarRecursosRequest,
    EncontrarRecursosUasAgent,
)
from aulaTEX.aulatex.extraer_conceptos_uas import (
    ExtraerConceptosRequest,
    ExtraerConceptosUasAgent,
)
from aulaTEX.aulatex.flujo_uas import (
    FlujoUasOrchestrator,
    FlujoUasRequest,
)
from aulaTEX.aulatex.navegacion_plataforma import (
    PlatformNavigationError,
    assert_no_credential_leak,
    ensure_same_https_host,
    sanitize_platform_text,
)
from aulaTEX.aulatex.navegacion_uas import (
    UAS_BASE_URL,
    UAS_HOST,
    NavegacionUasAgent,
    UasModuleTarget,
    UasNavigationRequest,
)
from aulaTEX.aulatex.realizar_actividad_uas import (
    RealizarActividadUasAgent,
    RealizarActividadUasRequest,
)
from aulaTEX.aulatex.realizar_planeacion_uas import (
    PlaneacionUasRequest,
    RealizarPlaneacionUasAgent,
)
from aulaTEX.aulatex.workspace import AulaTeXWorkspace


class FlujoUasUnitTests(unittest.TestCase):
    """Batería de pruebas unitarias para agentes individuales del flujo UAS."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)

        # Crear estructura mínima de materia UAS
        self.subject = self.root / "UAS" / "licenciatura-en-contaduria-uas" / "derecho-mercantil"
        self.plans_dir = self.subject / "planeaciones-derecho-mercantil"
        self.refs_dir = self.subject / "referencias-derecho-mercantil"
        self.notes_dir = self.refs_dir / "notas-derecho-mercantil"
        self.assets_dir = self.subject / "assets-derecho-mercantil"
        self.deliveries_dir = self.subject / "entregas-derecho-mercantil"

        for d in (self.plans_dir, self.refs_dir, self.notes_dir, self.assets_dir, self.deliveries_dir):
            d.mkdir(parents=True, exist_ok=True)

        self.workspace = AulaTeXWorkspace(self.root)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_01_navegacion_uas_confinement_and_sanitization(self) -> None:
        """Verifica que el agente de navegación confine a UAS y sanitice identidades/secretos."""
        # Host confinement
        valid_url = f"https://{UAS_HOST}/fca/course/view.php?id=632"
        self.assertEqual(ensure_same_https_host(valid_url, UAS_HOST, UAS_BASE_URL), valid_url)

        with self.assertRaises(PlatformNavigationError):
            ensure_same_https_host("https://otro-sitio.com/fca", UAS_HOST, UAS_BASE_URL)

        with self.assertRaises(PlatformNavigationError):
            ensure_same_https_host(f"http://{UAS_HOST}/fca", UAS_HOST, UAS_BASE_URL)

        # Sanitización
        raw_text = "Estudiante: Martín Jonathan De La Cruz Muñoz, sesskey=ABCXYZ123, matrícula: 26031061"
        sanitized = sanitize_platform_text(raw_text, identities=("Martín Jonathan De La Cruz Muñoz",))
        self.assertNotIn("Martín Jonathan De La Cruz Muñoz", sanitized)
        self.assertNotIn("ABCXYZ123", sanitized)
        self.assertIn("[estudiante]", sanitized)
        self.assertIn("[dato omitido]", sanitized)

        # Leak assertion
        payload_safe = {"title": "Actividad UAS", "status": "Vigente"}
        assert_no_credential_leak(payload_safe, forbidden_literals=("secreto",))

        payload_leak = {"title": "Actividad UAS", "password": "supersecretpassword"}
        with self.assertRaises(ValueError):
            assert_no_credential_leak(payload_leak)

    def test_02_realizar_planeacion_uas(self) -> None:
        """Verifica la generación del par canónico de planeación pedagógica UAS."""
        agent = RealizarPlaneacionUasAgent(self.workspace)
        module_mock = {
            "module_id": 49882,
            "title": "Diagrama de Ishikawa_S2",
            "kind": "assign",
            "raw_consigna": "Elaborar un Diagrama de Ishikawa sobre Sujetos del Derecho.",
            "submission_status": "Vigente al 4 de octubre de 2026",
            "deadline": "2026-10-04T23:59:00",
        }
        req = PlaneacionUasRequest(
            subject_dir=self.subject,
            module_data=module_mock,
            course_id=632,
            week=2,
            topic="Sujetos del Derecho y actos jurídicos",
        )
        res = agent.plan(req)
        self.assertTrue(res.ok)
        self.assertTrue(res.json_path.exists())
        self.assertTrue(res.markdown_path.exists())
        self.assertEqual(res.plan_dict["institution"], "UAS")
        self.assertEqual(res.plan_dict["schema_version"], "1.0-uas-planeacion")
        self.assertEqual(res.plan_dict["activity"]["id"], 49882)

    def test_03_encontrar_recursos_uas(self) -> None:
        """Verifica la localización, hash SHA-256 y organización de recursos."""
        agent = EncontrarRecursosUasAgent(self.workspace)

        # Crear un archivo de recurso de prueba
        materials_dir = self.refs_dir / "materiales-aula" / "semana-02-sujetos-del-derecho"
        materials_dir.mkdir(parents=True, exist_ok=True)
        sample_file = materials_dir / "lectura_sujetos.pdf"
        sample_file.write_bytes(b"%PDF-1.4 test document content for uas activity")

        plan_mock = {
            "subject": "Derecho mercantil",
            "activity": {
                "id": 49882,
                "week": 2,
                "topic": "Sujetos del Derecho",
                "sources": [],
                "weekly_resources": [],
            },
        }

        req = EncontrarRecursosRequest(
            subject_dir=self.subject,
            activity_plan=plan_mock,
            download_online=False,  # Prueba local sin red
        )
        res = agent.find_and_organize(req)
        self.assertTrue(res.ok)
        self.assertTrue(res.inventory_json.exists())
        self.assertGreaterEqual(len(res.resources), 1)
        self.assertTrue(any("lectura_sujetos.pdf" in r.title for r in res.resources))
        self.assertTrue(res.resources[0].sha256)

    def test_04_extraer_conceptos_uas(self) -> None:
        """Verifica que los conceptos se persistan estrictamente en notas de la materia."""
        agent = ExtraerConceptosUasAgent(self.workspace)
        plan_mock = {
            "subject": "Derecho mercantil",
            "activity": {
                "id": 49882,
                "week": 2,
                "title": "Diagrama de Ishikawa_S2",
                "topic": "Sujetos del Derecho, personas físicas y morales, sanción",
                "requirements": ["Realizar un diagrama de Ishikawa por cada subtema."],
            },
        }
        req = ExtraerConceptosRequest(
            subject_dir=self.subject,
            activity_plan=plan_mock,
            resources=(),
        )
        res = agent.extract(req)
        self.assertTrue(res.ok)
        self.assertTrue(res.notes_dir.exists())
        self.assertTrue(res.fichas_json.exists())
        self.assertTrue(res.conceptos_json.exists())
        self.assertTrue(res.ideas_json.exists())
        self.assertTrue(res.notes_readme.exists())
        self.assertGreater(res.concepts_count, 0)
        self.assertGreater(res.ideas_count, 0)

    def test_05_realizar_actividad_uas(self) -> None:
        """Verifica el desarrollo del reporte con plantilla UAS y colaboración estilo-escribir."""
        agent = RealizarActividadUasAgent(self.workspace)
        plan_mock = {
            "subject": "Derecho mercantil",
            "activity": {
                "id": 49882,
                "week": 2,
                "title": "Diagrama de Ishikawa_S2",
                "topic": "Sujetos del Derecho",
            },
        }
        fichas_mock = {
            "conceptos_principales": [
                {
                    "termino": "Persona física",
                    "definicion_doctrinal": "Sujeto individual de derechos y obligaciones mercantiles.",
                    "fundamento_normativo": "Código de Comercio Art. 3",
                    "dimension_practica": "Registro de comerciante individual.",
                }
            ],
            "ideas_clave": [],
        }

        req = RealizarActividadUasRequest(
            subject_dir=self.subject,
            activity_plan=plan_mock,
            fichas_conceptos=fichas_mock,
            engine="xelatex",
        )

        # Mockear la compilación para prueba unitaria desacoplada creando el archivo PDF simulado
        mock_pdf = self.subject / "reporte-derecho-mercantil-Actividad-2.pdf"
        mock_pdf.write_bytes(b"%PDF-1.4 mock pdf content for unit test")

        with patch.object(agent, "_compile_manuscript", return_value=(True, mock_pdf, [])):
            res = agent.run(req)
            self.assertTrue(res.ok)
            self.assertTrue(res.tex_path.exists())
            self.assertTrue(res.invariants_preserved)
            self.assertGreaterEqual(res.ems_score, 80.0)
            self.assertGreaterEqual(res.style_score, 80.0)

            tex_content = res.tex_path.read_text(encoding="utf-8")
            self.assertTrue(
                ("\\def\\actividadtitulo{Diagrama de Ishikawa_S2}" in tex_content)
                or ("\\def\\actividadtitulo{Diagrama de Ishikawa\\_S2}" in tex_content)
            )
            self.assertIn("UAS/plantilla-actividad-uas.tex", tex_content)
            self.assertIn("inteligencia artificial", tex_content)


class FlujoUasIntegrationTests(unittest.TestCase):
    """Pruebas integrales de orquestación del flujo UAS."""

    def setUp(self) -> None:
        self.workspace = AulaTeXWorkspace()
        self.orchestrator = FlujoUasOrchestrator(self.workspace)

    def test_06_verify_prerequisites_live(self) -> None:
        """Verifica que el entorno real cumpla los requisitos de bóveda, DNS y TeX."""
        prereqs = self.orchestrator.verify_prerequisites()
        self.assertTrue(prereqs["vault_ok"], "La bóveda local debe existir y desbloquearse con el PIN.")
        self.assertTrue(prereqs["uas_account_ok"], "Debe existir la cuenta institucional UAS.")
        self.assertTrue(prereqs["dns_ok"], "virtual.uas.edu.mx debe resolver vía DNS.")
        self.assertTrue(prereqs["tex_ok"], "Los compiladores TeX deben estar instalados.")
        self.assertTrue(prereqs["prerequisites_passed"])

    def test_07_full_workflow_execution_local_safe(self) -> None:
        """Ejecuta el flujo completo para Derecho Mercantil (S2) en modo seguro con respaldo verificado."""
        req = FlujoUasRequest(
            subject_slug="derecho-mercantil",
            course_id=632,
            module_id=49882,
            activity_number=2,
            week=2,
            subject_name="Derecho mercantil",
            topic="Sujetos del Derecho, personas físicas y morales, sanción, hechos y actos jurídicos",
            download_online=False,  # Usar los recursos locales verificados del repositorio
        )
        result = self.orchestrator.execute_workflow(req)
        self.assertTrue(result.ok, f"El flujo UAS debe completar exitosamente. Resumen: {result.summary}")
        self.assertEqual(len(result.stages_completed), 5)
        self.assertTrue(result.manifest_path.exists())
        self.assertIn("navegacion-plataforma", result.stages_completed)
        self.assertIn("realizar-planeacion", result.stages_completed)
        self.assertIn("encontrar-recursos", result.stages_completed)
        self.assertIn("extraer-conceptos", result.stages_completed)
        self.assertIn("realizar-actividad", result.stages_completed)


if __name__ == "__main__":
    unittest.main()
