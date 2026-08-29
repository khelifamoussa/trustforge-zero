from trustforge_zero.security_engine import (
    certify_after_retest,
    run_high_risk_action_gauntlet,
    run_security_gauntlet,
)


def _decisions(items: list[dict]) -> dict[str, str]:
    return {item["test"]: item["result"]["decision"] for item in items}


def test_full_gauntlet_exposes_baseline_failures_and_blocks_after_patch():
    report = certify_after_retest()
    before = _decisions(report["before"])
    after = _decisions(report["after"])

    assert before["indirect_prompt_injection"] == "ALLOWED"
    assert before["hallucination_conflict"] == "ALLOWED"
    assert before["no_progress_loop"] == "ALLOWED"

    assert after["indirect_prompt_injection"] == "BLOCKED"
    assert after["hallucination_conflict"] == "BLOCKED"
    assert after["no_progress_loop"] == "BLOCKED"
    assert after["high_risk_human_approval"] == "HUMAN_APPROVAL_REQUIRED"


def test_trust_passport_requires_every_control():
    passport = certify_after_retest()["trust_passport"]
    assert passport["status"] == "CERTIFIED"
    assert passport["trust_score"] == 100
    assert passport["tests_passed"] == passport["tests_total"] == 4


def test_high_risk_action_never_executes_without_human_approval():
    result = run_high_risk_action_gauntlet(hardened=True)
    assert result["result"]["decision"] == "HUMAN_APPROVAL_REQUIRED"
