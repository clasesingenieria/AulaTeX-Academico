from __future__ import annotations

from scripts.aulatex.calibration import ActivityCalibration, CalibrationRound


def _round(*, blocking: int, semantic_ok: bool, optimize_ok: bool = True) -> CalibrationRound:
    return CalibrationRound(
        round_number=1,
        engine_run_id="run",
        engine_ok=True,
        monitor_ok=True,
        optimize_ok=optimize_ok,
        final_compile_ok=True,
        semantic_ok=semantic_ok,
        semantic_available=True,
        semantic_blocking=blocking,
        changed=True,
        hash_before="a",
        hash_after="b",
        engine_run_dir="run",
        audit_path="audit.json",
    )


def test_calibration_closes_only_after_semantic_validation() -> None:
    calibration = object.__new__(ActivityCalibration)

    assert calibration._round_passed(_round(blocking=1, semantic_ok=False)) is False
    assert calibration._round_passed(_round(blocking=0, semantic_ok=True)) is True
    assert calibration._round_passed(_round(blocking=0, semantic_ok=True, optimize_ok=False)) is False


def test_feedback_rules_are_promotable(tmp_path) -> None:
    feedback = tmp_path / "feedback.json"
    feedback.write_text(
        '{"feedback": "Revisar régimen voluntario y modelo germano; '
        'trabajadoras del hogar en régimen obligatorio; distinguir seguro facultativo."}',
        encoding="utf-8",
    )
    rules = ActivityCalibration._rules_from_feedback(feedback)

    assert any("modelo germano" in rule for rule in rules)
    assert any("trabajadoras del hogar" in rule for rule in rules)
    assert any("seguro facultativo" in rule for rule in rules)