"""Versioned first-party agent registry for TRUSTFORGE ZERO.

This module intentionally keeps discovery metadata deterministic and auditable.
It provides the Fortified Enterprise Fleet capability of cataloging approved
agents for cross-department discovery without pretending to be Google Agent
Registry. The Google ADK runtime remains the execution framework.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class AgentCard:
    name: str
    version: str
    owner: str
    purpose: str
    department_scope: tuple[str, ...]
    tool_scope: tuple[str, ...]
    data_scope: tuple[str, ...]
    status: str
    risk_tier: str
    requires_human_approval_for_high_risk: bool = True

    def to_dict(self) -> dict:
        data = asdict(self)
        data["department_scope"] = list(self.department_scope)
        data["tool_scope"] = list(self.tool_scope)
        data["data_scope"] = list(self.data_scope)
        return data


_REGISTRY: tuple[AgentCard, ...] = (
    AgentCard("trustforge_governor", "1.0.0", "platform-security", "Orchestrate the evidence-first certification lifecycle.", ("security", "governance"), ("agent-routing",), ("evidence-metadata",), "approved", "high"),
    AgentCard("sentinel_agent", "1.0.0", "platform-security", "Map trust boundaries, permissions, identities, and policy drift.", ("security", "governance"), (), ("identity-metadata", "policy-metadata"), "approved", "medium"),
    AgentCard("identity_guard_agent", "1.0.0", "identity-security", "Enforce least-privilege workload identity and delegation boundaries.", ("security", "iam"), (), ("identity-metadata",), "approved", "high"),
    AgentCard("tool_guardian_agent", "1.0.0", "platform-security", "Verify tool schemas, manifests, authorization boundaries, and provenance.", ("security", "platform"), (), ("tool-metadata",), "approved", "high"),
    AgentCard("red_swarm_agent", "1.0.0", "security-testing", "Run synthetic defensive attack vectors against the target fleet.", ("security",), ("run_security_gauntlet",), ("synthetic-test-data",), "approved", "high"),
    AgentCard("forensic_agent", "1.0.0", "security-operations", "Diagnose causal chains, blast radius, and minimum safe remediation from evidence.", ("security", "operations"), (), ("immutable-evidence",), "approved", "medium"),
    AgentCard("defense_agent", "1.0.0", "security-operations", "Apply the minimum sandbox least-privilege repair bundle.", ("security", "operations"), ("apply_least_privilege_patch",), ("synthetic-policy",), "approved", "high"),
    AgentCard("memory_guard_agent", "1.0.0", "data-governance", "Protect persistent memory provenance and regression immunity.", ("security", "governance"), (), ("provenanced-memory",), "approved", "high"),
    AgentCard("provenance_agent", "1.0.0", "audit-governance", "Attest evidence continuity and claim-to-event lineage.", ("audit", "governance"), (), ("immutable-evidence",), "approved", "high"),
    AgentCard("judge_agent", "1.0.0", "risk-governance", "Issue or deny the final Trust Passport from verified evidence only.", ("risk", "governance"), ("certify_after_retest",), ("attested-evidence",), "approved", "high"),
)


def list_agent_cards(status: str | None = "approved") -> list[dict]:
    cards: Iterable[AgentCard] = _REGISTRY
    if status is not None:
        cards = (card for card in cards if card.status == status)
    return [card.to_dict() for card in cards]


def registry_summary() -> dict:
    cards = list_agent_cards(status=None)
    return {
        "registry_type": "first_party_versioned_registry",
        "execution_framework": "google_adk",
        "agent_count": len(cards),
        "approved_count": sum(card["status"] == "approved" for card in cards),
        "agent_cards": cards,
        "invariants": {
            "strict_separation_of_concerns": True,
            "versioned_discovery_metadata": True,
            "scoped_tool_and_data_access": True,
            "human_gate_for_high_risk": True,
        },
    }
