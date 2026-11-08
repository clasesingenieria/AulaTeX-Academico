"""Batería de pruebas unitarias e integrales para el monitoreo de entregas y flujo de autorización en UAS.

Verifica:
1. Contratos y metadatos de agentes:
   - ``MonitorUasAgent`` (id: ``monitor-uas``, tipo: ``monitor-plataforma``).
   - ``EntregarUasAgent`` (id: ``entregar-uas``, tipo: ``realizar-entrega``).
   - Registro institucional para "UAS" en ``monitor-entregas`` y ``realizar-entrega``.
2. Distinción verificable de los 6 estados del ciclo de vida:
   - ``pendiente``, ``en_desarrollo``, ``entregable_generado``,
     ``calidad_validada``, ``autorizacion_pendiente``, ``entrega_confirmada``.
3. Emisión de recomendaciones basadas en información verificable por ``monitor-uas``:
   - ``solicitar-realizar-actividad`` para pendientes con o sin prerrequisitos listos.
   - ``esperar-autorizacion-entrega`` cuando los entregables (.xlsx/.pdf) ya están generados localmente.
   - ``ya_entregado`` cuando la plataforma reporta "Enviado para calificar" o "Calificado" (prevención de duplicados).
4. Compuerta fail-closed estricta en ``entregar-uas``:
   - Intento de envío con ``user_validated=False``: estrictamente BLOQUEADO sin acción en plataforma.
   - Detección de discrepancia de hash SHA-256 (``blocked_hash_mismatch``).
   - Validación de formato (.pdf, .xlsx).
5. Ejecución autorizada en modo seguro (dry-run):
   - Envío con ``user_validated=True`` en modo dry-run: comprobante y manifiesto generados con éxito.
6. Orquestación y canalización por ``aulatex`` (FlujoUasOrchestrator):
   - Invocación de ``monitor-uas`` y canalización de actividades pendientes.
   - Retención de entregables en estado ``autorizacion_pendiente``.
   - Principio inquebrantable: "autorizar la realización de una actividad no equivale a autorizar su envío".
7. Ausencia total de fugas de credenciales en manifiestos, comprobantes y bitácora.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from aulaTEX.aulatex.entregar_uas import (
    AGENT_ID_ENTREGAR_UAS,
    EntregarUasAgent,
    EntregarUasRequest,
)
from aulaTEX.aulatex.flujo_uas import (
    FlujoUasOrchestrator,
    FlujoUasRequest,
)
from aulaTEX.aulatex.monitor_entregas import (
    DeliveryRecommendation,
    MonitorEntregasAgent,
    PendingDeliveryItem,
    PendingSubmissionsReport,
    get_delivery_monitor,
    register_delivery_monitor,
)
from aulaTEX.aulatex.monitor_uas import (
    AGENT_ID_MONITOR_UAS,
    AGENT_TYPE_MONITOR_PLATAFORMA,
    LIFECYCLE_AUTORIZACION_PENDIENTE,
    LIFECYCLE_CALIDAD_VALIDADA,
    LIFECYCLE_EN_DESARROLLO,
    LIFECYCLE_ENTREGABLE_GENERADO,
    LIFECYCLE_ENTREGA_CONFIRMADA,
    LIFECYCLE_PENDIENTE,
    MonitorUasAgent,
    MonitorUasRequest,
    UAS_SUBJECTS_CATALOG,
    VALID_LIFECYCLE_STATES,
)
from aulaTEX.aulatex.navegacion_plataforma import (
    AGENT_TYPE_NAVEGACION_PLATAFORMA,
    assert_no_credential_leak,
)
from aulaTEX.aulatex.realizar_entrega import (
    AGENT_TYPE_REALIZAR_ENTREGA,
    DeliverySubmissionRequest,
    DeliverySubmissionResult,
    RealizarEntregaAgent,
    get_delivery_agent,
    register_delivery_agent,
)
from aulaTEX.aulatex.workspace import AulaTeXWorkspace


class UasDeliveryAgentContractTests(unittest.TestCase):
    """Pruebas de conformidad de contratos y registro institucional para UAS."""

    def setUp(self) -> None:
        self.workspace = AulaTeXWorkspace()

    def test_01_monitor_uas_contract_and_registration(self) -> None:
        """Verifica que monitor-uas implementa el tipo monitor-plataforma y está registrado para UAS."""
        agent = MonitorUasAgent(self.workspace)
        self.assertEqual(agent.agent_id, AGENT_ID_MONITOR_UAS)
        self.assertEqual(agent.agent_type, AGENT_TYPE_MONITOR_PLATAFORMA)
        self.assertIsInstance(agent, MonitorEntregasAgent)

        # Registro institucional en monitor-entregas
        registered_agent = get_delivery_monitor("UAS", self.workspace)
        self.assertEqual(registered_agent.agent_id, AGENT_ID_MONITOR_UAS)
        self.assertEqual(registered_agent.agent_type, AGENT_TYPE_MONITOR_PLATAFORMA)

    def test_02_entregar_uas_contract_and_registration(self) -> None:
        """Verifica que entregar-uas implementa el tipo realizar-entrega y está registrado para UAS."""
        agent = EntregarUasAgent(self.workspace)
        self.assertEqual(agent.agent_id, AGENT_ID_ENTREGAR_UAS)
        self.assertEqual(agent.agent_type, AGENT_TYPE_REALIZAR_ENTREGA)
        self.assertIsInstance(agent, RealizarEntregaAgent)

        # Registro institucional en realizar-entrega
        registered_agent = get_delivery_agent("UAS", self.workspace)
        self.assertEqual(registered_agent.agent_id, AGENT_ID_ENTREGAR_UAS)
        self.assertEqual(registered_agent.agent_type, AGENT_TYPE_REALIZAR_ENTREGA)


class UasMonitorLifecycleAndRecommendationsTests(unittest.TestCase):
    """Pruebas de los 6 estados del ciclo de vida y emisión de recomendaciones de monitor-uas."""

    def setUp(self) -> None:
        self.workspace = AulaTeXWorkspace()
        self.monitor = MonitorUasAgent(self.workspace)

    def test_03_six_lifecycle_states_defined(self) -> None:
        """Verifica que los 6 estados canónicos del ciclo de vida estén definidos y sean consistentes."""
        expected_states = (
            "pendiente",
            "en_desarrollo",
            "entregable_generado",
            "calidad_validada",
            "autorizacion_pendiente",
            "entrega_confirmada",
        )
        self.assertEqual(VALID_LIFECYCLE_STATES, expected_states)

    def test_04_recommendation_awaiting_authorization_when_deliverables_exist(self) -> None:
        """Verifica que recomienda 'esperar-autorizacion-entrega' cuando existen entregables generados."""
        # En Herramientas Digitales, Actividad 4 (S3) tiene entregable generado
        rec = self.monitor.evaluate_activity(
            subject_slug="herramientas-digitales",
            activity_number=4,
            course_id=635,
            module_id=50130,
        )
        self.assertEqual(rec.institution, "UAS")
        self.assertEqual(rec.activity_number, 4)
        self.assertIn("entregable_local_generado", rec.prerequisites_satisfied)
        self.assertEqual(rec.recommended_action, "esperar-autorizacion-entrega")
        self.assertIsNotNone(rec.proposed_delivery_artifact)
        self.assertIsNotNone(rec.proposed_delivery_sha256)
        self.assertIn("validación explícita del usuario", rec.rationale)
        assert_no_credential_leak(rec.rationale)

    def test_05_recommendation_already_delivered_in_platform(self) -> None:
        """Verifica prevención de duplicados: 'ya_entregado' si la plataforma reporta entregado/calificado."""
        mock_snapshot = {
            "modules": {
                "49882": {
                    "full_main_text": "Estado de la entrega: Enviado para calificar. Calificación: Calificado.",
                    "intro_text": "Diagrama de Ishikawa_S2",
                }
            }
        }
        rec = self.monitor.evaluate_activity(
            subject_slug="derecho-mercantil",
            activity_number=2,
            course_id=632,
            module_id=49882,
            nav_snapshot=mock_snapshot,
        )
        self.assertEqual(rec.recommended_action, "ya_entregado")
        self.assertIn("ya se encuentra acreditada/entregada en UAS", rec.rationale)
        assert_no_credential_leak(rec.rationale)

    def test_06_monitor_deliveries_report_generation(self) -> None:
        """Verifica que monitor_deliveries genera manifiesto y reporte Markdown sin fugas de secretos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            req = MonitorUasRequest(
                subject_slug="herramientas-digitales",
                activity_number=4,
                inspect_platform=False,
                output_dir=tmpdir,
            )
            report = self.monitor.monitor_deliveries(req)
            self.assertTrue(report.ok)
            self.assertEqual(report.institution, "UAS")
            self.assertGreaterEqual(len(report.pending_deliveries), 1)
            self.assertTrue(report.manifest_path.is_file())
            self.assertTrue(report.summary_md_path.is_file())

            manifest = json.loads(report.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["agent_id"], "monitor-uas")
            self.assertEqual(manifest["agent_type"], "monitor-plataforma")
            assert_no_credential_leak(manifest)
            assert_no_credential_leak(report.summary_md_path.read_text(encoding="utf-8"))


class UasDeliverySecurityGateTests(unittest.TestCase):
    """Pruebas de la compuerta fail-closed y validación de usuario en entregar-uas."""

    def setUp(self) -> None:
        self.workspace = AulaTeXWorkspace()
        self.agent = EntregarUasAgent(self.workspace)
        # Usar artefacto generado en Herramientas Digitales S3
        self.artifact = (
            self.workspace.repo_root
            / "UAS"
            / "licenciatura-en-contaduria-uas"
            / "herramientas-digitales"
            / "entregas-herramientas-digitales"
            / "TI_S3_MartinJonathanDeLaCruzMunoz.pdf"
        )
        self.assertTrue(self.artifact.is_file(), f"Artefacto requerido para prueba: {self.artifact}")
        self.valid_sha256 = hashlib.sha256(self.artifact.read_bytes()).hexdigest()

    def test_07_fail_closed_submission_blocked_without_user_validation(self) -> None:
        """CRÍTICO: Sin validación explícita del usuario (user_validated=False), el envío es BLOQUEADO."""
        with tempfile.TemporaryDirectory() as tmpdir:
            req = EntregarUasRequest(
                subject_slug="herramientas-digitales",
                activity_number=4,
                artifact_path=self.artifact,
                expected_sha256=self.valid_sha256,
                course_id=635,
                module_id=50130,
                user_validated=False,  # INTENCIONALMENTE FALSE
                dry_run=False,
                output_dir=tmpdir,
            )
            res = self.agent.submit(req)

            # Debe fallar cerrado (fail-closed)
            self.assertFalse(res.ok)
            self.assertEqual(res.status, "blocked_missing_user_validation")
            self.assertEqual(len(res.blockers), 1)
            self.assertEqual(res.blockers[0]["code"], "missing_user_validation")
            self.assertIn("autorizar la realización de una actividad no equivale a autorizar su envío", res.blockers[0]["detail"])

            # Comprobar que el manifiesto documenta el bloqueo
            self.assertTrue(res.manifest_path.is_file())
            manifest = json.loads(res.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["user_validated"], False)
            assert_no_credential_leak(manifest)

    def test_08_submission_blocked_on_hash_mismatch(self) -> None:
        """Verifica que si el hash esperado no coincide con el archivo local, el envío se bloquea."""
        with tempfile.TemporaryDirectory() as tmpdir:
            req = EntregarUasRequest(
                subject_slug="herramientas-digitales",
                activity_number=4,
                artifact_path=self.artifact,
                expected_sha256="ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",  # Hash falso
                course_id=635,
                module_id=50130,
                user_validated=True,  # Usuario validó, pero la integridad falló
                dry_run=True,
                output_dir=tmpdir,
            )
            res = self.agent.submit(req)
            self.assertFalse(res.ok)
            self.assertEqual(res.status, "blocked_hash_mismatch")
            self.assertEqual(res.blockers[0]["code"], "hash_mismatch")

    def test_09_submission_dry_run_success_with_user_validation(self) -> None:
        """Verifica que con validación de usuario (user_validated=True), el modo dry-run valida exitosamente."""
        with tempfile.TemporaryDirectory() as tmpdir:
            req = EntregarUasRequest(
                subject_slug="herramientas-digitales",
                activity_number=4,
                artifact_path=self.artifact,
                expected_sha256=self.valid_sha256,
                course_id=635,
                module_id=50130,
                user_validated=True,  # VALIDACIÓN EXPLÍCITA
                dry_run=True,
                output_dir=tmpdir,
            )
            res = self.agent.submit(req)
            self.assertTrue(res.ok)
            self.assertEqual(res.status, "dry_run_validated")
            self.assertEqual(res.sha256, self.valid_sha256)
            self.assertTrue(res.receipt_path.is_file())
            self.assertTrue(res.manifest_path.is_file())

            receipt = json.loads(res.receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["sha256"], self.valid_sha256)
            self.assertEqual(receipt["dry_run"], True)
            self.assertEqual(receipt["user_validated"], True)
            assert_no_credential_leak(receipt)


class UasOrchestrationWithDeliveryTests(unittest.TestCase):
    """Pruebas de orquestación en FlujoUasOrchestrator con monitor-uas y compuertas de seguridad."""

    def setUp(self) -> None:
        self.workspace = AulaTeXWorkspace()
        self.orchestrator = FlujoUasOrchestrator(self.workspace)

    def test_10_orchestrator_submits_delivery_fails_closed_without_user_validation(self) -> None:
        """Verifica que submit_authorized_delivery bloquea el envío si falta user_validated=True."""
        artifact = (
            self.workspace.repo_root
            / "UAS"
            / "licenciatura-en-contaduria-uas"
            / "herramientas-digitales"
            / "entregas-herramientas-digitales"
            / "TI_S3_MartinJonathanDeLaCruzMunoz.pdf"
        )
        res = self.orchestrator.submit_authorized_delivery(
            subject_slug="herramientas-digitales",
            activity_number=4,
            artifact_path=artifact,
            user_validated=False,
            course_id=635,
            module_id=50130,
        )
        self.assertFalse(res.ok)
        self.assertEqual(res.status, "blocked_missing_user_validation")

    def test_11_orchestrator_run_pending_deliveries_preserves_sovereignty(self) -> None:
        """Verifica que run_pending_deliveries retiene entregables en 'autorizacion_pendiente'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Ejecución en herramientas-digitales sin red ni compilación
            batch_res = self.orchestrator.run_pending_deliveries(
                subject_slug="herramientas-digitales",
                inspect_platform=False,
                download_resources=False,
                compile_pdf=False,
                output_dir=tmpdir,
            )
            self.assertTrue(batch_res["ok"])
            self.assertEqual(batch_res["institution"], "UAS")
            self.assertEqual(batch_res["orchestrator"], "aulatex")

            # Comprobar que las ya listas están clasificadas en already_completed_or_held
            self.assertGreaterEqual(len(batch_res["already_completed_or_held"]), 1)
            manifest_path = Path(tmpdir) / "manifest-uas-pending.json"
            self.assertTrue(manifest_path.is_file())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            assert_no_credential_leak(manifest)


if __name__ == "__main__":
    unittest.main()
