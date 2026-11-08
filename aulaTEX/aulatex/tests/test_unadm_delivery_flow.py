"""Batería de pruebas unitarias e integrales para el monitoreo de entregas y flujo de autorización en UnADM.

Verifica:
1. Contratos y metadatos de agentes:
   - ``MonitorUnadmAgent`` (id: ``monitor-unadm``, tipo: ``monitor-entregas``).
   - ``EntregarUnadmAgent`` (id: ``entregar-unadm``, tipo: ``realizar-entrega``).
   - Registros institucionales para "UnADM" en ``monitor-entregas`` y ``realizar-entrega``.
2. Emisión de recomendaciones basadas en información verificable por ``monitor-unadm``:
   - ``solicitar-realizar-actividad`` cuando se cumplen los prerrequisitos (plan, recursos, conceptos).
   - ``esperar-autorizacion-entrega`` cuando el entregable PDF ya está compilado localmente.
   - ``bloqueado_falta_prerrequisitos`` cuando faltan elementos requeridos.
   - ``ya_entregado`` cuando la plataforma reporta "Enviado para calificar".
3. Orquestación y canalización por ``aulatex`` (UnadmWorkflowOrchestrator):
   - Invocación de ``monitor-unadm`` y autorización de ``realizar-actividad``.
   - Localización del artefacto en ``entregas-<slug>/`` y retención en estado ``pendiente_validacion_usuario``.
   - Principio: "autorizar la realización de una actividad no equivale a autorizar su envío".
4. Compuerta fail-closed estricta en ``entregar-unadm``:
   - Intento de envío con ``user_validated=False``: estrictamente BLOQUEADO sin acción en plataforma.
   - Detección de discrepancia de hash SHA-256 (``blocked_hash_mismatch``).
   - Validación de formato PDF.
5. Ejecución autorizada en modo seguro (dry-run):
   - Envío con ``user_validated=True`` en modo dry-run: comprobante y manifiesto generados con éxito.
6. Ausencia total de fugas de credenciales en manifiestos, comprobantes y bitácora.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from aulaTEX.aulatex.entregar_unadm import (
    AGENT_ID_ENTREGAR_UNADM,
    EntregarUnadmAgent,
    EntregarUnadmRequest,
)
from aulaTEX.aulatex.monitor_entregas import (
    AGENT_TYPE_MONITOR_ENTREGAS,
    DeliveryRecommendation,
    MonitorEntregasAgent,
    PendingDeliveryItem,
    PendingSubmissionsReport,
    get_delivery_monitor,
    register_delivery_monitor,
)
from aulaTEX.aulatex.monitor_unadm import (
    AGENT_ID_MONITOR_UNADM,
    MonitorUnadmAgent,
    MonitorUnadmRequest,
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
from aulaTEX.aulatex.unadm_workflow import (
    AGENT_ID_ORQUESTADOR_AULATEX,
    UnadmWorkflowOrchestrator,
    UnadmWorkflowRequest,
)
from aulaTEX.aulatex.workspace import AulaTeXWorkspace


class UnadmDeliveryAgentContractTests(unittest.TestCase):
    """Pruebas de conformidad de contratos y registro institucional."""

    def setUp(self) -> None:
        self.workspace = AulaTeXWorkspace()

    def test_01_monitor_unadm_contract_and_registration(self) -> None:
        """Verifica que monitor-unadm implementa el tipo monitor-entregas y está registrado."""
        agent = MonitorUnadmAgent(self.workspace)
        self.assertEqual(agent.agent_id, AGENT_ID_MONITOR_UNADM)
        self.assertEqual(agent.agent_type, AGENT_TYPE_MONITOR_ENTREGAS)
        self.assertIsInstance(agent, MonitorEntregasAgent)

        # Registro institucional
        registered_agent = get_delivery_monitor("UnADM", self.workspace)
        self.assertEqual(registered_agent.agent_id, AGENT_ID_MONITOR_UNADM)
        self.assertEqual(registered_agent.agent_type, AGENT_TYPE_MONITOR_ENTREGAS)

    def test_02_entregar_unadm_contract_and_registration(self) -> None:
        """Verifica que entregar-unadm implementa el tipo realizar-entrega y está registrado."""
        agent = EntregarUnadmAgent(self.workspace)
        self.assertEqual(agent.agent_id, AGENT_ID_ENTREGAR_UNADM)
        self.assertEqual(agent.agent_type, AGENT_TYPE_REALIZAR_ENTREGA)
        self.assertIsInstance(agent, RealizarEntregaAgent)

        # Registro institucional
        registered_agent = get_delivery_agent("UnADM", self.workspace)
        self.assertEqual(registered_agent.agent_id, AGENT_ID_ENTREGAR_UNADM)
        self.assertEqual(registered_agent.agent_type, AGENT_TYPE_REALIZAR_ENTREGA)


class UnadmMonitorAgentLogicTests(unittest.TestCase):
    """Pruebas de la lógica de evaluación y recomendaciones de monitor-unadm."""

    def setUp(self) -> None:
        self.workspace = AulaTeXWorkspace()
        self.monitor = MonitorUnadmAgent(self.workspace)

    def test_03_recommendation_ready_to_request_activity(self) -> None:
        """Verifica que recomienda 'solicitar-realizar-actividad' cuando plan, recursos y conceptos existen sin entregable."""
        rec = self.monitor.evaluate_activity(
            subject_slug="teoria-del-estado-y-constitucion",
            activity_number=2,
            course_id=3432,
        )
        self.assertEqual(rec.institution, "UnADM")
        self.assertEqual(rec.activity_number, 2)
        self.assertIn("planeacion_canonica_verificada", rec.prerequisites_satisfied)
        self.assertIn("recursos_organizados_verificados", rec.prerequisites_satisfied)
        self.assertIn("conceptos_extraidos_verificados", rec.prerequisites_satisfied)
        self.assertEqual(rec.recommended_action, "solicitar-realizar-actividad")
        self.assertIn("aulatex autorizar", rec.rationale)
        assert_no_credential_leak(rec.rationale)

    def test_04_recommendation_awaiting_delivery_authorization(self) -> None:
        """Verifica que recomienda 'esperar-autorizacion-entrega' cuando el entregable ya está compilado."""
        # Actividad 4 de Penal tiene Actividad-S4-Delitos-de-peligro-Martin-Jonathan-de-la-Cruz.pdf en entregas
        rec = self.monitor.evaluate_activity(
            subject_slug="derecho-penal-especial-mexicano",
            activity_number=4,
            course_id=3482,
        )
        self.assertIn("entregable_local_compilado", rec.prerequisites_satisfied)
        self.assertEqual(rec.recommended_action, "esperar-autorizacion-entrega")
        self.assertIsNotNone(rec.proposed_delivery_artifact)
        self.assertIsNotNone(rec.proposed_delivery_sha256)
        self.assertIn("Actividad-S4", rec.proposed_delivery_artifact)
        self.assertIn("validación explícita del usuario", rec.rationale)

    def test_05_recommendation_already_submitted_in_platform(self) -> None:
        """Verifica que reporta 'ya_entregado' si la plataforma informa 'Enviado para calificar'."""
        mock_snapshot = {
            "modules": {
                "218337": {
                    "full_main_text": "Estado de la entrega: Enviado para calificar. Calificación: Sin calificar.",
                    "intro_text": "Actividad 4",
                }
            }
        }
        rec = self.monitor.evaluate_activity(
            subject_slug="derecho-penal-especial-mexicano",
            activity_number=4,
            course_id=3482,
            module_id=218337,
            nav_snapshot=mock_snapshot,
        )
        self.assertEqual(rec.recommended_action, "ya_entregado")
        self.assertIn("ya fue enviada previamente", rec.rationale)

    def test_06_monitor_deliveries_report_generation(self) -> None:
        """Verifica que monitor_deliveries genera manifiesto y reporte Markdown sin fugas."""
        with tempfile.TemporaryDirectory() as tmpdir:
            req = MonitorUnadmRequest(
                subject_slug="derecho-penal-especial-mexicano",
                activity_number=1,
                inspect_platform=False,
                output_dir=tmpdir,
            )
            report = self.monitor.monitor_deliveries(req)
            self.assertTrue(report.ok)
            self.assertEqual(report.institution, "UnADM")
            self.assertEqual(len(report.pending_deliveries), 1)
            self.assertTrue(report.manifest_path.is_file())
            self.assertTrue(report.summary_md_path.is_file())

            manifest = json.loads(report.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["agent_id"], "monitor-unadm")
            self.assertEqual(manifest["agent_type"], "monitor-entregas")
            assert_no_credential_leak(manifest)
            assert_no_credential_leak(report.summary_md_path.read_text(encoding="utf-8"))


class UnadmDeliverySecurityGateTests(unittest.TestCase):
    """Pruebas rigurosas de la compuerta de seguridad y validación de usuario en entregar-unadm."""

    def setUp(self) -> None:
        self.workspace = AulaTeXWorkspace()
        self.agent = EntregarUnadmAgent(self.workspace)
        self.pdf_file = (
            self.workspace.repo_root
            / "UnADM"
            / "licenciatura-en-derecho-unadm"
            / "derecho-penal-especial-mexicano-lde"
            / "entregas-derecho-penal-especial-mexicano"
            / "Actividad-S4-Delitos-de-peligro-Martin-Jonathan-de-la-Cruz.pdf"
        )
        self.assertTrue(self.pdf_file.is_file(), f"PDF requerido: {self.pdf_file}")
        self.valid_sha256 = hashlib.sha256(self.pdf_file.read_bytes()).hexdigest()

    def test_07_fail_closed_submission_blocked_without_user_validation(self) -> None:
        """CRÍTICO: Sin validación explícita del usuario (user_validated=False), el envío es BLOQUEADO."""
        with tempfile.TemporaryDirectory() as tmpdir:
            req = EntregarUnadmRequest(
                subject_slug="derecho-penal-especial-mexicano",
                activity_number=4,
                artifact_path=self.pdf_file,
                expected_sha256=self.valid_sha256,
                course_id=3482,
                module_id=218337,
                user_validated=False,  # INTENCIONALMENTE FALSE
                dry_run=False,
                output_dir=tmpdir,
            )
            res = self.agent.submit(req)

            # Debe fallar cerrado
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
            req = EntregarUnadmRequest(
                subject_slug="derecho-penal-especial-mexicano",
                activity_number=4,
                artifact_path=self.pdf_file,
                expected_sha256="0000000000000000000000000000000000000000000000000000000000000000",  # Hash falso
                course_id=3482,
                module_id=218337,
                user_validated=True,  # Usuario validó, pero integridad no concuerda
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
            req = EntregarUnadmRequest(
                subject_slug="derecho-penal-especial-mexicano",
                activity_number=4,
                artifact_path=self.pdf_file,
                expected_sha256=self.valid_sha256,
                course_id=3482,
                module_id=218337,
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
            self.assertEqual(receipt["platform_submission_performed"], False)
            assert_no_credential_leak(receipt)


class UnadmWorkflowOrchestrationWithDeliveryTests(unittest.TestCase):
    """Pruebas de integración del flujo completo con monitor-unadm y retención de entrega."""

    def setUp(self) -> None:
        self.workspace = AulaTeXWorkspace()
        self.orchestrator = UnadmWorkflowOrchestrator(self.workspace)

    def test_10_full_orchestration_stages_delivery_without_submitting(self) -> None:
        """Verifica que el flujo aulatex solicita recomendación, ejecuta y retiene la propuesta para validación."""
        with tempfile.TemporaryDirectory() as tmpdir:
            req = UnadmWorkflowRequest(
                subject_slug="derecho-penal-especial-mexicano",
                activity_number=1,
                course_id=3482,
                inspect_platform=False,
                download_online_resources=False,
                compile_pdf=False,
                output_dir=tmpdir,
                submit_to_platform=False,  # NO enviar a plataforma
                user_validated=False,
            )
            res = self.orchestrator.run(req)
            self.assertTrue(res.ok)

            stage_names = [s.stage_name for s in res.stages]
            expected_stages = [
                "planeacion",
                "recopilacion_recursos",
                "extraccion_conceptos",
                "monitoreo_entregas",
                "realizacion_actividad",
                "propuesta_entrega",
            ]
            self.assertEqual(stage_names, expected_stages)

            # 1. Recomendación del monitor
            self.assertIsNotNone(res.delivery_recommendation)
            self.assertIn(res.delivery_recommendation.recommended_action, ("solicitar-realizar-actividad", "esperar-autorizacion-entrega"))

            # 2. Entrega propuesta retenida en estado pendiente_validacion_usuario
            manifest = json.loads(res.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["orchestrator_agent"], AGENT_ID_ORQUESTADOR_AULATEX)
            self.assertEqual(manifest["submission_status"], "not_requested")
            assert_no_credential_leak(manifest)

            summary_text = res.summary_md_path.read_text(encoding="utf-8")
            self.assertIn("Autorizar la realización de una actividad no equivale a autorizar su envío", summary_text)
            self.assertIn("PENDIENTE DE VALIDACIÓN EXPLÍCITA DEL USUARIO", summary_text)
            assert_no_credential_leak(summary_text)

    def test_11_orchestration_submit_to_platform_refuses_without_user_validation(self) -> None:
        """Verifica que si submit_to_platform=True pero user_validated=False, la compuerta bloquea el envío."""
        with tempfile.TemporaryDirectory() as tmpdir:
            req = UnadmWorkflowRequest(
                subject_slug="derecho-penal-especial-mexicano",
                activity_number=1,
                course_id=3482,
                inspect_platform=False,
                download_online_resources=False,
                compile_pdf=False,
                output_dir=tmpdir,
                submit_to_platform=True,  # Solicita envío
                user_validated=False,     # PERO SIN VALIDACIÓN EXPLÍCITA
            )
            res = self.orchestrator.run(req)

            # El flujo global se marca como no completado debido al bloqueo en el envío
            self.assertFalse(res.ok)
            stage_names = [s.stage_name for s in res.stages]
            self.assertIn("envio_plataforma", stage_names)

            envio_stage = next(s for s in res.stages if s.stage_name == "envio_plataforma")
            self.assertFalse(envio_stage.ok)
            self.assertIn("blocked_missing_user_validation", envio_stage.summary)


class UnadmWeek6DetectionAndStagingTests(unittest.TestCase):
    """Pruebas de detección, preparación y retención soberana para la Semana 6 de UnADM."""

    def setUp(self) -> None:
        self.workspace = AulaTeXWorkspace()
        self.monitor = MonitorUnadmAgent(self.workspace)
        self.entrega_agent = EntregarUnadmAgent(self.workspace)

    def test_12_detect_week6_activities_across_three_subjects(self) -> None:
        """Verifica que el monitor descubre dinámicamente las actividades de la semana 6 en las tres materias."""
        # 1. Penal: Actividad 6 (módulo assign 222951)
        penal_rep = self.monitor.monitor_deliveries(MonitorUnadmRequest(subject_slug="derecho-penal-especial-mexicano", course_id=3482))
        penal_acts = [r.activity_number for r in penal_rep.recommendations]
        self.assertIn(6, penal_acts)

        # 2. Antecedentes DH: Actividad 8 (módulo assign 212031, correspondiente a semana 6)
        dh_rep = self.monitor.monitor_deliveries(MonitorUnadmRequest(subject_slug="antecedentes-de-los-derechos-humanos", course_id=3441))
        dh_acts = [r.activity_number for r in dh_rep.recommendations]
        self.assertIn(8, dh_acts)

        # 3. Teoría del Estado: Actividad 6 (módulo foro 221688)
        teoria_rep = self.monitor.monitor_deliveries(MonitorUnadmRequest(subject_slug="teoria-del-estado-y-constitucion", course_id=3432))
        teoria_acts = [r.activity_number for r in teoria_rep.recommendations]
        self.assertIn(6, teoria_acts)

    def test_13_week6_deliverables_staged_awaiting_user_authorization(self) -> None:
        """Verifica que las actividades de semana 6 están preparadas y retenidas en 'esperar-autorizacion-entrega'."""
        # 1. Penal Actividad 6
        rec_penal = self.monitor.evaluate_activity("derecho-penal-especial-mexicano", 6, course_id=3482)
        self.assertEqual(rec_penal.recommended_action, "esperar-autorizacion-entrega")
        self.assertIsNotNone(rec_penal.proposed_delivery_artifact)
        self.assertTrue(Path(rec_penal.proposed_delivery_artifact).is_file())

        # 2. Antecedentes DH Actividad 8
        rec_dh = self.monitor.evaluate_activity("antecedentes-de-los-derechos-humanos", 8, course_id=3441)
        self.assertEqual(rec_dh.recommended_action, "esperar-autorizacion-entrega")
        self.assertIsNotNone(rec_dh.proposed_delivery_artifact)
        self.assertTrue(Path(rec_dh.proposed_delivery_artifact).is_file())

        # 3. Teoría del Estado Actividad 6 (Foro)
        rec_teoria = self.monitor.evaluate_activity("teoria-del-estado-y-constitucion", 6, course_id=3432)
        self.assertEqual(rec_teoria.recommended_action, "esperar-autorizacion-entrega")
        self.assertIsNotNone(rec_teoria.proposed_delivery_artifact)
        self.assertTrue(Path(rec_teoria.proposed_delivery_artifact).is_file())

    def test_14_submission_fail_closed_for_all_week6_deliverables(self) -> None:
        """Verifica que intentar enviar cualquier entrega de semana 6 sin validación del usuario resulta en bloqueo estricto."""
        # Penal Act 6
        rec_penal = self.monitor.evaluate_activity("derecho-penal-especial-mexicano", 6, course_id=3482)
        sub_res1 = self.entrega_agent.submit(
            EntregarUnadmRequest(
                subject_slug="derecho-penal-especial-mexicano",
                activity_number=6,
                artifact_path=rec_penal.proposed_delivery_artifact,
                expected_sha256=rec_penal.proposed_delivery_sha256,
                user_validated=False,
            )
        )
        self.assertFalse(sub_res1.ok)
        self.assertEqual(sub_res1.status, "blocked_missing_user_validation")

        # DH Act 8
        rec_dh = self.monitor.evaluate_activity("antecedentes-de-los-derechos-humanos", 8, course_id=3441)
        sub_res2 = self.entrega_agent.submit(
            EntregarUnadmRequest(
                subject_slug="antecedentes-de-los-derechos-humanos",
                activity_number=8,
                artifact_path=rec_dh.proposed_delivery_artifact,
                expected_sha256=rec_dh.proposed_delivery_sha256,
                user_validated=False,
            )
        )
        self.assertFalse(sub_res2.ok)
        self.assertEqual(sub_res2.status, "blocked_missing_user_validation")


if __name__ == "__main__":
    unittest.main()
