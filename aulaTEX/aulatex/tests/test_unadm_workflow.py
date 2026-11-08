"""Pruebas unitarias e integrales para el flujo de trabajo académico UnADM en AulaTeX.

Verifica:
1. Confinamiento de origen seguro y sanitización en NavegacionUnadmAgent (navegación-itesca, tipo navegación-plataforma).
2. Generación de planeación canónica PCA v1.0.0 (JSON + MD) con RealizarPlaneacionUnadmAgent (realizar-planeación).
3. Localización, organización y hash SHA-256 de recursos con EncontrarRecursosAgent (encontrar-recursos).
4. Extracción de conceptos académicos en notas de actividad con ExtraerConceptosAgent (extraer-conceptos).
5. Realización de actividad con plantilla UnADM y colaboración con EstiloEscribirAgent (realizar-actividad).
6. Orquestación secuencial estricta y compuerta fail-closed con UnadmWorkflowOrchestrator (aulatex).
7. Verificación de bóveda de credenciales, DNS de UnADM y ausencia total de fugas de secretos.
"""
from __future__ import annotations

import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from aulaTEX.aulatex.encontrar_recursos import (
    AGENT_ID_ENCONTRAR_RECURSOS,
    EncontrarRecursosAgent,
    EncontrarRecursosRequest,
)
from aulaTEX.aulatex.estilo_escribir import AGENT_ID_ESTILO_ESCRIBIR, EstiloEscribirAgent
from aulaTEX.aulatex.extraer_conceptos import (
    AGENT_ID_EXTRAER_CONCEPTOS,
    ExtraerConceptosAgent,
    ExtraerConceptosRequest,
)
from aulaTEX.aulatex.navegacion_plataforma import (
    AGENT_TYPE_NAVEGACION_PLATAFORMA,
    PlatformNavigationError,
    assert_no_credential_leak,
    ensure_same_https_host,
    load_vault_account,
    sanitize_platform_text,
)
from aulaTEX.aulatex.navegacion_unadm import (
    AGENT_ID_NAVEGACION_ITESCA,
    AGENT_ID_NAVEGACION_UNADM,
    COURSES_UNADM,
    NavegacionUnadmAgent,
    UNADM_BASE_URL,
    UNADM_HOST,
    UnadmNavigationRequest,
)
from aulaTEX.aulatex.realizar_actividad import (
    AGENT_ID_REALIZAR_ACTIVIDAD,
    RealizarActividadAgent,
    RealizarActividadRequest,
)
from aulaTEX.aulatex.realizar_planeacion_unadm import (
    AGENT_ID_REALIZAR_PLANEACION,
    RealizarPlaneacionUnadmAgent,
    RealizarPlaneacionUnadmRequest,
    UNADM_SUBJECTS_CATALOG,
)
from aulaTEX.aulatex.unadm_workflow import (
    AGENT_ID_ORQUESTADOR_AULATEX,
    UnadmWorkflowOrchestrator,
    UnadmWorkflowRequest,
)
from aulaTEX.aulatex.workspace import AulaTeXWorkspace


class UnadmWorkflowUnitTests(unittest.TestCase):
    """Batería de pruebas unitarias para agentes individuales de UnADM."""

    def setUp(self) -> None:
        self.workspace = AulaTeXWorkspace()

    def test_01_navegacion_unadm_confinement_and_sanitization(self) -> None:
        """Verifica que el agente confina a aulavirtual.unadmexico.mx y sanitiza secretos."""
        # Host confinement
        valid_url = f"https://{UNADM_HOST}/course/view.php?id=3482"
        self.assertEqual(ensure_same_https_host(valid_url, UNADM_HOST, UNADM_BASE_URL), valid_url)

        with self.assertRaises(PlatformNavigationError):
            ensure_same_https_host("https://otro-sitio.com/curso", UNADM_HOST, UNADM_BASE_URL)

        with self.assertRaises(PlatformNavigationError):
            ensure_same_https_host(f"http://{UNADM_HOST}/curso", UNADM_HOST, UNADM_BASE_URL)

        # Sanitización de texto
        raw_text = "Estudiante: Juan Pérez López, matrícula: ES19200000, sesskey=UNADM_SECRET_KEY"
        sanitized = sanitize_platform_text(raw_text, identities=("Juan Pérez López",))
        self.assertNotIn("Juan Pérez López", sanitized)
        self.assertNotIn("UNADM_SECRET_KEY", sanitized)
        self.assertIn("[estudiante]", sanitized)
        self.assertIn("[dato omitido]", sanitized)

        # Assert no credential leak
        safe_payload = {"title": "Actividad 1", "platform": "UnADM"}
        assert_no_credential_leak(safe_payload)

        leak_payload = {"title": "Actividad 1", "password": "vault_password_123"}
        with self.assertRaises(ValueError):
            assert_no_credential_leak(leak_payload)

    def test_02_navegacion_unadm_agent_metadata(self) -> None:
        """Verifica los atributos de agente de NavegacionUnadmAgent."""
        agent = NavegacionUnadmAgent(self.workspace, agent_id=AGENT_ID_NAVEGACION_ITESCA)
        self.assertEqual(agent.agent_id, AGENT_ID_NAVEGACION_ITESCA)
        self.assertEqual(agent.agent_type, AGENT_TYPE_NAVEGACION_PLATAFORMA)
        self.assertEqual(agent.courses, COURSES_UNADM)
        self.assertIn(3482, agent.courses)
        self.assertIn(3432, agent.courses)
        self.assertIn(3441, agent.courses)

    def test_03_realizar_planeacion_unadm_canonical(self) -> None:
        """Verifica que realizar-planeación genere PCA v1.0.0 canónica en JSON y Markdown."""
        agent = RealizarPlaneacionUnadmAgent(self.workspace)
        req = RealizarPlaneacionUnadmRequest(
            subject_slug="derecho-penal-especial-mexicano",
            activity_number=1,
            module_snapshot=None,
        )
        res = agent.plan(req)
        self.assertTrue(res.ok)
        self.assertTrue(res.plan_json_path.is_file())
        self.assertTrue(res.plan_md_path.is_file())
        self.assertTrue(res.consigna_path.is_file())

        plan_data = json.loads(res.plan_json_path.read_text(encoding="utf-8-sig"))
        self.assertEqual(plan_data["schema_version"], "1.0.0")
        self.assertEqual(plan_data["identity"]["institution"], "UnADM")
        self.assertIn("activities", plan_data)
        act = plan_data["activities"][0]
        self.assertIn("notes_directory", act["bindings"])
        self.assertTrue(act["bindings"]["notes_directory"].startswith("referencias-"))

        # Validar ausencia de fugas
        assert_no_credential_leak(plan_data)
        assert_no_credential_leak(res.plan_md_path.read_text(encoding="utf-8"))

    def test_04_encontrar_recursos_unadm(self) -> None:
        """Verifica que encontrar-recursos organice archivos en material-docente y corpus-extractor."""
        agent = EncontrarRecursosAgent(self.workspace)
        plan_path = (
            self.workspace.repo_root
            / "UnADM"
            / "licenciatura-en-derecho-unadm"
            / "derecho-penal-especial-mexicano-lde"
            / "planeaciones-derecho-penal-especial-mexicano"
            / "planeacion-derecho-penal-especial-mexicano-Actividad-1.json"
        )
        self.assertTrue(plan_path.is_file(), f"Planeación requerida para test: {plan_path}")

        req = EncontrarRecursosRequest(
            target="UnADM/licenciatura-en-derecho-unadm/derecho-penal-especial-mexicano-lde",
            activity_number=1,
            plan_json_path=plan_path,
            download_from_platform=False,
        )
        res = agent.run(req)
        self.assertEqual(res.agent_id, AGENT_ID_ENCONTRAR_RECURSOS)
        self.assertTrue(res.manifest_path.is_file())
        self.assertTrue(res.corpus_dir.is_dir())
        self.assertGreater(res.total_resources, 0)
        self.assertGreater(res.organized_files_count, 0)

        # Validar manifiesto de recursos
        manifest_data = json.loads(res.manifest_path.read_text(encoding="utf-8-sig"))
        self.assertEqual(manifest_data["schema_version"], "1.0.0")
        self.assertIn("corpus_extractor_files", manifest_data)
        self.assertTrue(all("sha256" in r for r in manifest_data["corpus_extractor_files"]))
        assert_no_credential_leak(manifest_data)

    def test_05_extraer_conceptos_unadm(self) -> None:
        """Verifica que extraer-conceptos genere artefactos en notas y extractor-aulatex."""
        plan_path = (
            self.workspace.repo_root
            / "UnADM"
            / "licenciatura-en-derecho-unadm"
            / "derecho-penal-especial-mexicano-lde"
            / "planeaciones-derecho-penal-especial-mexicano"
            / "planeacion-derecho-penal-especial-mexicano-Actividad-1.json"
        )
        # Asegurar que recursos-actividad.json exista previamente (prerrequisito de secuencia)
        rec_agent = EncontrarRecursosAgent(self.workspace)
        rec_agent.run(EncontrarRecursosRequest(
            target="UnADM/licenciatura-en-derecho-unadm/derecho-penal-especial-mexicano-lde",
            activity_number=1,
            plan_json_path=plan_path,
            download_from_platform=False,
        ))

        agent = ExtraerConceptosAgent(self.workspace)
        req = ExtraerConceptosRequest(
            target="UnADM/licenciatura-en-derecho-unadm/derecho-penal-especial-mexicano-lde",
            activity_number=1,
            plan_json_path=plan_path,
        )
        res = agent.run(req)
        self.assertEqual(res.agent_id, AGENT_ID_EXTRAER_CONCEPTOS)
        self.assertTrue(res.ok)
        self.assertTrue(res.notes_concepts_dir.is_dir())
        self.assertTrue(res.synced_extractor_dir.is_dir())
        self.assertGreater(res.concepts_count, 0)
        self.assertTrue(any(res.notes_concepts_dir.glob("*.json")))

    def test_06_estilo_escribir_collaboration(self) -> None:
        """Verifica la auditoría de estilo académico de estilo-escribir."""
        agent = EstiloEscribirAgent(self.workspace)
        eval_result = agent.evaluate_plain_prose(
            "El presente análisis aborda los delitos contra la seguridad colectiva en el derecho penal mexicano. "
            "Se examinan los elementos constitutivos de la tipicidad conforme al Código Penal Federal y la doctrina."
        )
        self.assertEqual(agent.agent_id, AGENT_ID_ESTILO_ESCRIBIR)
        self.assertGreaterEqual(eval_result.score, 70.0)


class UnadmWorkflowIntegrationTests(unittest.TestCase):
    """Batería de pruebas integrales para el orquestador aulatex de UnADM."""

    def setUp(self) -> None:
        self.workspace = AulaTeXWorkspace()
        self.orchestrator = UnadmWorkflowOrchestrator(self.workspace)

    def test_07_vault_unadm_account_and_dns_readiness(self) -> None:
        """Verifica que la bóveda contenga la cuenta UnADM y que el DNS resuelva."""
        # 1. DNS check
        try:
            ip = socket.gethostbyname(UNADM_HOST)
            self.assertTrue(bool(ip), f"{UNADM_HOST} debe resolver por DNS.")
        except socket.gaierror as err:
            self.fail(f"Fallo en resolución DNS para {UNADM_HOST}: {err}")

        # 2. Vault decryption check
        vault_account = load_vault_account(self.workspace.repo_root, "UnADM", UNADM_HOST)
        self.assertIsNotNone(vault_account, "Debe existir la cuenta de UnADM en la bóveda local.")
        self.assertIn("username", vault_account)
        self.assertIn("password", vault_account)
        # Verificar que las credenciales no son vacías sin exponerlas
        self.assertGreater(len(vault_account["username"]), 3)
        self.assertGreater(len(vault_account["password"]), 3)

    def test_08_full_unadm_workflow_execution(self) -> None:
        """Verifica la ejecución de la secuencia completa: planeación -> recursos -> conceptos -> actividad."""
        req = UnadmWorkflowRequest(
            subject_slug="derecho-penal-especial-mexicano",
            activity_number=1,
            course_id=3482,
            inspect_platform=False,
            download_online_resources=False,
            compile_pdf=False,  # En prueba integral rápida validamos el pipeline sin compilación TeX completa
        )
        res = self.orchestrator.run(req)

        self.assertEqual(self.orchestrator.agent_id, AGENT_ID_ORQUESTADOR_AULATEX)
        self.assertEqual(res.subject_slug, "derecho-penal-especial-mexicano")
        self.assertEqual(res.activity_number, 1)

        stage_names = [s.stage_name for s in res.stages]
        self.assertIn("planeacion", stage_names)
        self.assertIn("recopilacion_recursos", stage_names)
        self.assertIn("extraccion_conceptos", stage_names)
        self.assertIn("monitoreo_entregas", stage_names)
        self.assertIn("realizacion_actividad", stage_names)
        self.assertIn("propuesta_entrega", stage_names)

        # Verificar orden estricto de las etapas
        self.assertEqual(
            stage_names,
            [
                "planeacion",
                "recopilacion_recursos",
                "extraccion_conceptos",
                "monitoreo_entregas",
                "realizacion_actividad",
                "propuesta_entrega",
            ],
        )

        # Verificar recomendación de entrega emitida por monitor-unadm
        self.assertIsNotNone(res.delivery_recommendation)
        self.assertEqual(res.delivery_recommendation.institution, "UnADM")

        # Verificar persistencia de manifiesto y resumen Markdown
        self.assertTrue(res.manifest_path.is_file())
        self.assertTrue(res.summary_md_path.is_file())

        manifest = json.loads(res.manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], "1.0.0")
        self.assertEqual(manifest["orchestrator_agent_id"], "aulatex")
        self.assertEqual(manifest["institution"], "UnADM")
        self.assertEqual(len(manifest["stages"]), 6)

        # Verificar que el manifiesto no contenga secretos
        assert_no_credential_leak(manifest)
        assert_no_credential_leak(res.summary_md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
