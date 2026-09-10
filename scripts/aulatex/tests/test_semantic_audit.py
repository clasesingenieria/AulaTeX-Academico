from __future__ import annotations

import json

from scripts.aulatex.activity_optimizer import ActivityOptimizeRequest, ActivityOptimizer
from scripts.aulatex.llm_bridge import LLMCallResult
from scripts.aulatex.semantic_audit import SemanticAuditResult, SemanticAuditor, SemanticFinding


class FakeLLM:
    def __init__(self, payload: dict | None = None, *, error: str = "") -> None:
        self.payload = payload
        self.error = error
        self.prompt = ""

    def call(self, engine: str, prompt: str, **_: object) -> LLMCallResult:
        self.prompt = prompt
        if self.error:
            return LLMCallResult(engine, False, "", self.error)
        return LLMCallResult(engine, True, json.dumps(self.payload or {}, ensure_ascii=False))

    def call_with_safety_net(self, prompt: str, *, engine: str, **kwargs: object) -> LLMCallResult:
        return self.call(engine, prompt, **kwargs)


def test_audit_reports_unavailable_when_llm_fails(tmp_path) -> None:
    result = SemanticAuditor(FakeLLM(error="Sin servicio")).audit(
        "Una afirmacion pendiente de verificar.", tmp_path, engine="fake",
    )

    assert result.ok is False
    assert result.audit_available is False
    assert result.error == "Sin servicio"


def test_audit_grounds_blocking_finding_in_local_passages(tmp_path) -> None:
    extractor = tmp_path / "extractor-aulatex"
    extractor.mkdir()
    (extractor / "fichas_conceptos.json").write_text(
        json.dumps(
            [
                {
                    "fuente": "manual.pdf",
                    "ubicacion": "p. 12",
                    "cita_textual": (
                        "El modelo contributivo se financia mediante primas o cuotas pagadas "
                        "por las personas aseguradas y sus empleadores."
                    ),
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    llm = FakeLLM(
        {
            "claims_checked": 1,
            "findings": [
                {
                    "kind": "source_conflict",
                    "severity": "blocking",
                    "claim": "El régimen voluntario corresponde al modelo latino.",
                    "explanation": "La clasificación no concuerda con su financiamiento por cuotas.",
                    "evidence": [
                        {
                            "source": "manual.pdf",
                            "location": "p. 12",
                            "quote": "El modelo contributivo se financia mediante primas o cuotas.",
                        }
                    ],
                    "suggested_fix": "Clasificarlo como cercano al modelo germano contributivo.",
                }
            ],
        }
    )

    result = SemanticAuditor(llm).audit(
        "El régimen voluntario corresponde al modelo latino porque el asegurado paga cuotas.",
        tmp_path,
        engine="fake",
    )

    assert result.audit_available is True
    assert result.ok is False
    assert len(result.blocking_findings) == 1
    assert "manual.pdf" in llm.prompt
    assert "primas o cuotas" in llm.prompt


def test_external_feedback_is_included_as_evaluative_evidence(tmp_path) -> None:
    feedback = tmp_path / "feedback.json"
    feedback.write_text(
        json.dumps({"observacion": "El régimen voluntario se aproxima al modelo germano."}),
        encoding="utf-8",
    )
    llm = FakeLLM({"claims_checked": 1, "findings": []})

    result = SemanticAuditor(llm).audit(
        "El régimen voluntario se aproxima al modelo germano.",
        tmp_path,
        engine="fake",
        feedback_path=feedback,
    )

    assert result.audit_available is True
    assert result.evidence_count == 1
    assert "RETROALIMENTACIÓN DOCENTE" in llm.prompt
    assert "modelo germano" in llm.prompt


def test_methodological_delimitation_is_not_a_blocking_fact_claim() -> None:
    auditor = SemanticAuditor(FakeLLM({"claims_checked": 1, "findings": []}))

    findings = auditor._normalize_findings(
        [
            {
                "kind": "unsupported_claim",
                "severity": "blocking",
                "claim": "La denominación germano-latina se emplea aquí como criterio comparativo.",
                "explanation": "Es una decisión metodológica del autor.",
            }
        ]
    )

    assert findings[0].severity == "warning"


def test_feedback_conflicts_are_blocking_even_when_llm_omits_them(tmp_path) -> None:
    extractor = tmp_path / "extractor-aulatex"
    extractor.mkdir()
    (extractor / "fichas_conceptos.json").write_text(
        json.dumps(
            [
                {
                    "fuente": "fuente.pdf",
                    "ubicacion": "p. 1",
                    "cita_textual": "Las trabajadoras del hogar pertenecen al régimen obligatorio.",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    feedback = tmp_path / "feedback.json"
    feedback.write_text(
        json.dumps({"observacion": "El régimen voluntario es más similar al modelo germano."}),
        encoding="utf-8",
    )
    llm = FakeLLM({"claims_checked": 1, "findings": []})

    result = SemanticAuditor(llm).audit(
        "El régimen voluntario y las trabajadoras del hogar se acercan al modelo latino.",
        tmp_path,
        engine="fake",
        feedback_path=feedback,
    )

    assert result.ok is False
    assert len(result.blocking_findings) == 1
    assert result.blocking_findings[0].origin == "deterministic-feedback"


def test_deterministic_audit_blocks_incompatible_classifications() -> None:
    auditor = SemanticAuditor(FakeLLM({"claims_checked": 2, "findings": []}))

    findings = auditor._detect_internal_contradictions(
        [
            "El régimen voluntario se clasifica como germano contributivo.",
            "El régimen voluntario se clasifica como latino contributivo.",
        ]
    )

    assert len(findings) == 1
    assert findings[0].kind == "internal_contradiction"
    assert findings[0].severity == "blocking"


def test_semantic_gate_fails_closed_and_requires_fewer_blockers() -> None:
    optimizer = object.__new__(ActivityOptimizer)
    request = ActivityOptimizeRequest(target=".")
    unavailable = SemanticAuditResult(False, False, 0, 0, error="sin servicio")
    one_blocker = SemanticAuditResult(
        False,
        True,
        1,
        1,
        findings=(SemanticFinding("unsupported_claim", "blocking", "A", "Sin respaldo"),),
    )
    clean = SemanticAuditResult(True, True, 1, 1)

    assert optimizer._semantic_gate_passed(request, unavailable) is False
    assert optimizer._semantic_gate_passed(request, one_blocker) is False
    assert optimizer._semantic_gate_passed(request, clean) is True
    assert optimizer._semantic_candidate_acceptable(request, one_blocker, clean) is True
    assert optimizer._semantic_candidate_acceptable(request, one_blocker, one_blocker) is False