from trustforge_zero.agent_registry import list_agent_cards, registry_summary


def test_registry_contains_governor_and_all_nine_specialists():
    cards = list_agent_cards(status="approved")
    names = {card["name"] for card in cards}

    assert len(cards) == 10
    assert names == {
        "trustforge_governor",
        "sentinel_agent",
        "identity_guard_agent",
        "tool_guardian_agent",
        "red_swarm_agent",
        "forensic_agent",
        "defense_agent",
        "memory_guard_agent",
        "provenance_agent",
        "judge_agent",
    }


def test_registry_cards_are_versioned_scoped_and_human_gated():
    for card in list_agent_cards(status=None):
        assert card["version"]
        assert card["owner"]
        assert card["purpose"]
        assert card["department_scope"]
        assert card["data_scope"]
        assert card["risk_tier"] in {"low", "medium", "high"}
        assert card["requires_human_approval_for_high_risk"] is True


def test_registry_summary_identifies_adk_without_overclaiming_google_registry():
    summary = registry_summary()

    assert summary["registry_type"] == "first_party_versioned_registry"
    assert summary["execution_framework"] == "google_adk"
    assert summary["agent_count"] == 10
    assert summary["approved_count"] == 10
    assert summary["invariants"]["strict_separation_of_concerns"] is True
    assert summary["invariants"]["scoped_tool_and_data_access"] is True
