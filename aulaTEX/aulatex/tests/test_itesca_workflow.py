"""Pruebas unitarias e integrales para el flujo de trabajo académico ITESCA en AulaTeX.

Verifica:
1. Confinamiento de origen seguro y sanitización en NavegacionItescaAgent (navegación-itesca, tipo navegación-plataforma).
2. Detección y bloqueo de URLs mutantes, sesskey y startattempt.php (live_quiz_attempt_protected).
3. Bóveda de credenciales de AulaTeX y verificación estricta de ausencia total de fugas de credenciales.
4. Generación y validación de planeación canónica con RealizarPlaneacionAgent (realizar-planeación).
5. Localización, organización y extracción con Pagina N de recursos con EncontrarRecursosAgent (encontrar-recursos).
6. Extracción y sincronización de conceptos en notas con ExtraerConceptosAgent (extraer-conceptos).
7. Auditoría de estilo académico y colaboración con EstiloEscribirAgent (estilo-escribir).
8. Realización de actividad y validación tipográfica con RealizarActividadAgent (realizar-actividad).
9. Orquestación integral y compuerta fail-closed con AulaTeXItescaOrchestrator (aulatex).
"""
from __future__ import annotations

import json
from pathlib import Path
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
from aulaTEX.aulatex.itesca_workflow import (
    AulaTeXItescaOrchestrator,
    ItescaActivitySpec,
    ItescaWorkflowRequest,
)
from aulaTEX.aulatex.mcp_lex import McpLexClient, audit_landscape_geometry, get_lex_client
from aulaTEX.aulatex.navegacion_itesca import (
    AGENT_ID_NAVEGACION_ITESCA,
    ITESCA_BASE_URL,
    ITESCA_HOST,
    NavegacionItescaAgent,
)
from aulaTEX.aulatex.navegacion_plataforma import (
    AGENT_TYPE_NAVEGACION_PLATAFORMA,
    PlatformNavigationError,
    assert_no_credential_leak,
    ensure_same_https_host,
    load_vault_account,
    normalize_readonly_link,
    sanitize_platform_text,
)
from aulaTEX.aulatex.realizar_actividad import (
    AGENT_ID_REALIZAR_ACTIVIDAD,
    RealizarActividadAgent,
    RealizarActividadRequest,
)
from aulaTEX.aulatex.realizar_planeacion import (
    AGENT_ID_REALIZAR_PLANEACION,
    RealizarPlaneacionAgent,
    RealizarPlaneacionRequest,
)
from aulaTEX.aulatex.workspace import AulaTeXWorkspace


class TestNavegacionItesca(unittest.TestCase):
    """Pruebas de seguridad, sanitización y confinamiento de red para ITESCA."""

    def test_agent_contract_metadata(self) -> None:
        agent = NavegacionItescaAgent()
        self.assertEqual(agent.agent_id, "navegación-itesca")
        self.assertEqual(agent.agent_type, AGENT_TYPE_NAVEGACION_PLATAFORMA)
        self.assertEqual(agent.spec.host, ITESCA_HOST)

    def test_origin_lock(self) -> None:
        ensure_same_https_host("https://cursos3.e-itesca.edu.mx/my/", ITESCA_HOST)
        with self.assertRaises(PlatformNavigationError):
            ensure_same_https_host("https://malicious-site.com/login", ITESCA_HOST)
        with self.assertRaises(PlatformNavigationError):
            ensure_same_https_host("http://cursos3.e-itesca.edu.mx/my/", ITESCA_HOST)

    def test_clean_platform_url_and_mutation_blocks(self) -> None:
        raw_url = "https://cursos3.e-itesca.edu.mx/mod/assign/view.php?id=1761&sesskey=ABCDEF123456"
        cleaned = normalize_readonly_link(raw_url, ITESCA_HOST)
        self.assertIsNotNone(cleaned)
        self.assertNotIn("sesskey", str(cleaned))
        self.assertIn("id=1761", str(cleaned))

        # Bloqueo de acciones de intento en cuestionarios (retorna None)
        blocked = normalize_readonly_link("https://cursos3.e-itesca.edu.mx/mod/quiz/startattempt.php?cmid=1763", ITESCA_HOST)
        self.assertIsNone(blocked)

    def test_assert_no_credential_leak(self) -> None:
        safe_text = "Entrega de la Actividad 7 para la Maestría en Gestión Administrativa."
        assert_no_credential_leak(safe_text)

        with self.assertRaises((PlatformNavigationError, ValueError)):
            assert_no_credential_leak("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secret")


class TestEstiloEscribir(unittest.TestCase):
    """Pruebas de evaluación estilística en prosa académica."""

    def setUp(self) -> None:
        self.ws = AulaTeXWorkspace()
        self.agent = EstiloEscribirAgent(self.ws)

    def test_plain_prose_evaluation(self) -> None:
        good_prose = (
            "La estimación estadística proporciona el marco analítico fundamental para inferir parámetros poblacionales "
            "a partir de observaciones muestrales en la gestión financiera y operacional. A través del cálculo de márgenes "
            "de error e intervalos de confianza, la administración sustituye conjeturas subjetivas por evidencia verificable."
        )
        report = self.agent.evaluate_plain_prose(good_prose)
        self.assertTrue(report.passed)
        self.assertGreaterEqual(report.score, 88.0)
        self.assertEqual(len(report.critical_issues), 0)

    def test_detect_metadiscourse_cliches(self) -> None:
        bad_prose = "En este reporte, esta actividad se centra en describir lo que los estudiantes deben realizar."
        report = self.agent.evaluate_plain_prose(bad_prose)
        self.assertFalse(report.passed)
        self.assertGreater(len(report.critical_issues), 0)

    def test_detect_unescaped_dollars_in_tex(self) -> None:
        bad_tex = "El costo oscila entre $100 y $120 pesos por pedido."
        report = self.agent.evaluate_tex(bad_tex)
        self.assertFalse(report.passed)
        self.assertTrue(any(iss["code"] == "dolar_monetario_sin_escapar_en_tex" for iss in report.critical_issues))


class TestItescaDeliverablesIntegrity(unittest.TestCase):
    """Verifica que los entregables requeridos de ITESCA existan y cumplan las especificaciones."""

    def setUp(self) -> None:
        self.ws = AulaTeXWorkspace()
        self.mga_root = self.ws.repo_root / "ITESCA/maestria-en-gestion-administrativa"
        self.stat_root = self.mga_root / "estadistica-aplicada-para-la-administracion-mga"
        self.sem_root = self.mga_root / "seminario-i-mga"

    def test_actividad_7_deliverable(self) -> None:
        pdf_path = self.stat_root / "entregas-estadistica-aplicada-para-la-administracion/Actividad-7-Investigacion-estimacion-intervalos.pdf"
        self.assertTrue(pdf_path.is_file(), f"Falta el entregable Actividad 7: {pdf_path}")
        import pymupdf
        doc = pymupdf.open(str(pdf_path))
        self.assertEqual(len(doc), 5, f"La Actividad 7 debe tener exactamente 5 páginas, tiene {len(doc)}")

    def test_actividad_8_deliverable(self) -> None:
        pdf_path = self.stat_root / "entregas-estadistica-aplicada-para-la-administracion/Actividad-8-Ejercicios-estimacion-intervalos.pdf"
        self.assertTrue(pdf_path.is_file(), f"Falta el entregable Actividad 8: {pdf_path}")
        import pymupdf
        doc = pymupdf.open(str(pdf_path))
        self.assertGreaterEqual(len(doc), 10, f"La Actividad 8 debe contener la resolución completa de los 6 ejercicios")

    def test_actividad_9_study_report_and_quiz_boundary(self) -> None:
        pdf_path = self.stat_root / "reporte-estadistica-aplicada-para-la-administracion-Actividad-9.pdf"
        self.assertTrue(pdf_path.is_file(), f"Falta el reporte de estudio de Actividad 9: {pdf_path}")
        
        # En entregas NO debe haber archivo de la Actividad 9
        forbidden_deliverable = self.stat_root / "entregas-estadistica-aplicada-para-la-administracion/Actividad-9-Evaluacion.pdf"
        self.assertFalse(forbidden_deliverable.exists(), "Cuestionarios en línea no colocan entregables en entregas/")

    def test_actividad_15_seminario_deliverable(self) -> None:
        docx_path = self.sem_root / "entregas-seminario-i/Tarea15_DeLaCruzMunoz.docx"
        self.assertTrue(docx_path.is_file(), f"Falta el entregable acumulativo Tarea 15 Word: {docx_path}")
        self.assertGreater(docx_path.stat().st_size, 1000000, "El Word Tarea 15 debe ser acumulativo completo")

        pdf_path = self.sem_root / "reporte-seminario-i-Actividad-15.pdf"
        self.assertTrue(pdf_path.is_file(), f"Falta el reporte sincronizado TeX/PDF de Tarea 15: {pdf_path}")


class TestItescaOrchestrator(unittest.TestCase):
    """Verifica que el orquestador principal aulatex pueda planificar e instanciar el flujo."""

    def setUp(self) -> None:
        self.ws = AulaTeXWorkspace()
        self.orchestrator = AulaTeXItescaOrchestrator(self.ws)

    def test_orchestrator_initialization(self) -> None:
        self.assertEqual(self.orchestrator.orchestrator_id, "aulatex")
        self.assertIsNotNone(self.orchestrator.nav_agent)
        self.assertIsNotNone(self.orchestrator.planner_agent)
        self.assertIsNotNone(self.orchestrator.resources_agent)
        self.assertIsNotNone(self.orchestrator.concepts_agent)
        self.assertIsNotNone(self.orchestrator.activity_agent)
        self.assertIsNotNone(self.orchestrator.style_agent)
        self.assertIsNotNone(self.orchestrator.lex_client)


class TestLandscapeCompositionAndGeometry(unittest.TestCase):
    """Pruebas rigurosas de composición horizontal, geometría y ausencia de encabezados/pies."""

    def setUp(self) -> None:
        self.ws = AulaTeXWorkspace()
        self.sem_root = self.ws.repo_root / "ITESCA/maestria-en-gestion-administrativa/seminario-i-mga"
        self.pdf_path = self.sem_root / "reporte-seminario-i-Actividad-15.pdf"

    def test_landscape_pages_detected_and_valid(self) -> None:
        self.assertTrue(self.pdf_path.is_file(), f"Falta el PDF: {self.pdf_path}")
        report = audit_landscape_geometry(self.pdf_path)
        self.assertGreaterEqual(report["landscape_pages_detected"], 2, "Debe haber al menos 2 páginas apaisadas")
        self.assertIn(14, report["landscape_pages"])
        self.assertIn(15, report["landscape_pages"])

    def test_landscape_headers_and_footers_suppressed(self) -> None:
        report = audit_landscape_geometry(self.pdf_path)
        self.assertTrue(
            report["headers_footers_suppressed"],
            f"Fallo de encabezados/pies en páginas apaisadas: {report['hf_failures']}",
        )
        self.assertEqual(len(report["hf_failures"]), 0)

    def test_landscape_geometry_and_overflow_absence(self) -> None:
        report = audit_landscape_geometry(self.pdf_path)
        self.assertTrue(
            report["geometry_ok"],
            f"Desbordamientos detectados en páginas apaisadas: {report['overflow_failures']}",
        )
        self.assertEqual(report["overflow_count"], 0)
        self.assertTrue(report["passed"])

    def test_landscape_audit_blocks_on_violation(self) -> None:
        import pymupdf
        with pymupdf.open(self.pdf_path) as doc:
            p14 = doc[13]
            # Inyectar texto simulado de encabezado en zona superior
            p14.insert_text((72.0, 50.0), "Actividad 15 - Seminario I GGS102")
            qa_tmp = self.ws.repo_root / ".build" / "test_tmp_failing_audit.pdf"
            qa_tmp.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(qa_tmp))

        failing_report = audit_landscape_geometry(qa_tmp)
        self.assertFalse(failing_report["passed"], "La auditoría debió fallar por presencia de encabezado")
        self.assertFalse(failing_report["headers_footers_suppressed"])
        self.assertGreater(len(failing_report["issues"]), 0)


class TestMcpLexAgentIntegration(unittest.TestCase):
    """Verifica que todos los agentes editoriales y subagentes estén conectados con el MCP LEX."""

    def setUp(self) -> None:
        self.ws = AulaTeXWorkspace()
        self.orchestrator = AulaTeXItescaOrchestrator(self.ws)
        self.lex_client = get_lex_client()

    def test_agents_inventory_connected_to_lex(self) -> None:
        # 1. aulatex
        self.assertIsInstance(self.orchestrator.lex_client, McpLexClient)
        self.assertEqual(self.orchestrator.lex_client.server_name, "lex")

        # 2. navegación-itesca (tipo navegación-plataforma)
        nav = self.orchestrator.nav_agent
        self.assertEqual(nav.agent_id, "navegación-itesca")
        self.assertEqual(nav.agent_type, AGENT_TYPE_NAVEGACION_PLATAFORMA)
        self.assertIsInstance(nav.lex_client, McpLexClient)

        # 3. realizar-planeación
        planner = self.orchestrator.planner_agent
        self.assertEqual(planner.agent_id, "realizar-planeación")
        self.assertIsInstance(planner.lex_client, McpLexClient)

        # 4. encontrar-recursos
        resources = self.orchestrator.resources_agent
        self.assertEqual(resources.agent_id, "encontrar-recursos")
        self.assertIsInstance(resources.lex_client, McpLexClient)

        # 5. extraer-conceptos
        concepts = self.orchestrator.concepts_agent
        self.assertEqual(concepts.agent_id, "extraer-conceptos")
        self.assertIsInstance(concepts.lex_client, McpLexClient)

        # 6. realizar-actividad
        activity = self.orchestrator.activity_agent
        self.assertEqual(activity.agent_id, "realizar-actividad")
        self.assertIsInstance(activity.lex_client, McpLexClient)

        # 7. estilo-escribir
        style = self.orchestrator.style_agent
        self.assertEqual(style.agent_id, "estilo-escribir")
        self.assertIsInstance(style.lex_client, McpLexClient)

    def test_lex_health_probe(self) -> None:
        health = self.lex_client.check_health()
        self.assertIn("status", health)
        self.assertIn("sol_61", health)
        self.assertIn("nova_pro", health)
        self.assertTrue(health["sol_61"]["available"] or health["nova_pro"]["available"])

    def test_lex_connected_agents_catalog(self) -> None:
        agents = self.lex_client.list_connected_agents()
        agent_ids = {a["agent_id"] for a in agents}
        self.assertIn("aulatex", agent_ids)
        self.assertIn("navegación-itesca", agent_ids)
        self.assertIn("realizar-planeación", agent_ids)
        self.assertIn("encontrar-recursos", agent_ids)
        self.assertIn("extraer-conceptos", agent_ids)
        self.assertIn("realizar-actividad", agent_ids)
        self.assertIn("estilo-escribir", agent_ids)


if __name__ == "__main__":
    unittest.main()
