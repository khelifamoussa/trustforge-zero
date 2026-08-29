from trustforge_zero.security_engine import certify_after_retest, run_high_risk_action_gauntlet, run_security_gauntlet


def _decisions(items: list[dict]) -> dict[str, str]:
    return {item["test"]: item["result"]["decision"] for item in items}


def test_full_gauntlet_exposes_baseline_failures_and_blocks_after_patch():
    report = certify_after_retest()
    before = _decisions(report["before"])
    after = _decisions(report["after"])

    vulnerable = {
        "indirect_prompt_injection",
        "hallucination_conflict",
        "no_progress_loop",
        "identity_privilege_abuse",
        "tool_schema_poisoning",
        "memory_poisoning",
        "sensitive_data_egress",
        "cascading_delegation",
        "tool_supply_chain_drift",
    }
    for scenario in vulnerable:
        assert before[scenario] == "ALLOWED"
        assert after[scenario] == "BLOCKED"

    assert before["high_risk_human_approval"] == "HUMAN_APPROVAL_REQUIRED"
    assert after["high_risk_human_approval"] == "HUMAN_APPROVAL_REQUIRED"


def test_trust_passport_requires_every_control():
    passport = certify_after_retest()["trust_passport"]
    assert passport["status"] == "CERTIFIED"
    assert passport["trust_score"] == 100
    assert passport["tests_passed"] == passport["tests_total"] == 10
    assert all(passport["coverage"].values())


def test_hardened_gauntlet_has_no_autonomous_unsafe_allow():
    hardened = run_security_gauntlet(hardened=True)
    assert len(hardened) == 10
    assert all(item["result"]["decision"] in {"BLOCKED", "HUMAN_APPROVAL_REQUIRED"} for item in hardened)


def test_high_risk_action_never_executes_without_human_approval():
    result = run_high_risk_action_gauntlet(hardened=True)
    assert result["result"]["decision"] == "HUMAN_APPROVAL_REQUIRED"
