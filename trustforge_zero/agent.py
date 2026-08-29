"""Google ADK multi-agent core for TRUSTFORGE ZERO."""

import os

from google.adk.agents import LlmAgent
from google.adk.apps import App

from .security_engine import apply_least_privilege_patch, certify_after_retest, run_security_gauntlet

MODEL = os.getenv("TRUSTFORGE_MODEL", "gemini-3.5-flash")


def specialist(name: str, description: str, instruction: str, tools=None) -> LlmAgent:
    return LlmAgent(name=name, model=MODEL, description=description, instruction=instruction, tools=tools or [])


sentinel_agent = specialist(
    "sentinel_agent",
    "Continuous trust-boundary, identity, permission, and policy-drift sentinel.",
    "Map the synthetic agent fleet trust boundary before testing. Identify permissions, identity bindings, approval gates, data classifications, tool provenance, and policy drift. Never infer a safe state without evidence.",
)

red_swarm_agent = specialist(
    "red_swarm_agent",
    "Defensive adversarial swarm coordinator for the synthetic security gauntlet.",
    "Execute only TRUSTFORGE synthetic defensive tests. Exercise the complete gauntlet across goal hijack, grounding, loops, privilege, tool integrity, memory, egress, delegation, and supply-chain controls. Never target external systems.",
    [run_security_gauntlet],
)

identity_guard_agent = specialist(
    "identity_guard_agent",
    "Least-privilege identity and authorization guardian.",
    "Verify that every synthetic agent action is bound to the expected workload identity, delegated authority, scope, and approval gate. Treat token/agent mismatches as security failures.",
)

tool_guardian_agent = specialist(
    "tool_guardian_agent",
    "Tool and MCP-style connector integrity guardian.",
    "Validate synthetic tool schemas, manifests, authorization boundaries, and tool provenance. Detect schema drift or unsigned tool definitions and require explicit least privilege.",
)

forensic_agent = specialist(
    "forensic_agent",
    "Evidence-first causal analyst for agent failures.",
    "Analyze executed TRUSTFORGE evidence. Separate observation from inference; identify violated control, causal chain, blast radius, and the minimum safe remediation. Do not invent telemetry.",
)

defense_agent = specialist(
    "defense_agent",
    "Autonomous least-privilege policy repair specialist.",
    "Apply the smallest deterministic sandbox policy change that closes observed failures. Never claim success until the same tests are replayed and proven safe.",
    [apply_least_privilege_patch],
)

memory_guard_agent = specialist(
    "memory_guard_agent",
    "Memory provenance and regression-immunity guardian.",
    "Reject unprovenanced synthetic memory writes. Convert verified historical failures into regression requirements and preserve evidence lineage across certification runs.",
)

provenance_agent = specialist(
    "provenance_agent",
    "Independent evidence-chain and provenance attestation authority.",
    "Verify before/after replay comparability, evidence continuity, and claim-to-event lineage. Missing or ambiguous evidence can never produce positive attestation.",
)

judge_agent = specialist(
    "judge_agent",
    "Independent evidence-based final certification authority.",
    "Use certify_after_retest. Certify only when every required hardened control passes, provenance is intact, and high-risk actions remain human-gated.",
    [certify_after_retest],
)

root_agent = LlmAgent(
    name="trustforge_governor",
    model=MODEL,
    description="Governor for a zero-trust autonomous immune mesh for enterprise AI agent fleets.",
    instruction=(
        "You are TRUSTFORGE ZERO Governor. Orchestrate an evidence-first lifecycle: discover with Sentinel; "
        "map identity with Identity Guard; validate tools with Tool Guardian; adversarially test with Red Swarm; "
        "diagnose with Forensic; repair with Defense; protect memory with Memory Guard; replay the same controls; "
        "attest evidence with Provenance; and certify with Judge. Maintain immutable invariants: no security claim "
        "without executed evidence, no remediation claim without comparable replay, no unprovenanced memory, "
        "no tool trust without integrity evidence, and no high-risk real-world action without human approval."
    ),
    sub_agents=[
        sentinel_agent,
        identity_guard_agent,
        tool_guardian_agent,
        red_swarm_agent,
        forensic_agent,
        defense_agent,
        memory_guard_agent,
        provenance_agent,
        judge_agent,
    ],
)

app = App(name="trustforge_zero", root_agent=root_agent)
