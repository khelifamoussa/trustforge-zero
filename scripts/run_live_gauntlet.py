#!/usr/bin/env python3
"""Run the TRUSTFORGE ZERO live certification gauntlet.

This is a synthetic defensive demo.  It executes real deterministic controls,
emits a hash-chained event stream for the UI, replays the hardened tests, and
issues a Trust Passport only from observed evidence.
"""

from __future__ import annotations

import json
from pathlib import Path

from trustforge_zero.events import build_event, event_to_dict, verify_chain
from trustforge_zero.security_engine import (
    apply_least_privilege_patch,
    certify_after_retest,
    run_security_gauntlet,
)

OUTPUT = Path("artifacts/latest_gauntlet.json")


def main() -> None:
    events = []

    def emit(event_type: str, actor: str, phase: str, status: str, summary: str, payload=None):
        previous_hash = events[-1].event_hash if events else "GENESIS"
        event = build_event(
            seq=len(events) + 1,
            event_type=event_type,
            actor=actor,
            phase=phase,
            status=status,
            summary=summary,
            payload=payload or {},
            previous_hash=previous_hash,
        )
        events.append(event)
        print(f"[{event.seq:02d}] {event.event_type:<22} {event.actor:<16} {event.status:<24} {event.summary}", flush=True)
        return event

    print("\n" + "=" * 96)
    print("TRUSTFORGE ZERO // LIVE AUTONOMOUS SECURITY GAUNTLET")
    print("Synthetic enterprise sandbox | Evidence-first certification | Hash-chained audit trail")
    print("=" * 96)

    emit(
        "CERTIFICATION_STARTED",
        "governor",
        "discover",
        "RUNNING",
        "Governor opened a new certification run for the synthetic procurement agent.",
        {"target": "synthetic_procurement_agent", "mode": "defensive_sandbox"},
    )

    before = run_security_gauntlet(hardened=False)
    for item in before:
        decision = item["result"]["decision"]
        compromised = decision == "ALLOWED" and item["test"] != "high_risk_human_approval"
        status = "COMPROMISED" if compromised else decision
        emit(
            "ATTACK_OBSERVED",
            "red_agent",
            "attack",
            status,
            f"Baseline scenario {item['test']} produced {decision}.",
            item,
        )

    failed = [
        item for item in before
        if item["result"]["decision"] == "ALLOWED"
    ]
    emit(
        "ROOT_CAUSE_FOUND",
        "forensic_agent",
        "diagnose",
        "CRITICAL" if failed else "CLEAN",
        f"Forensic analysis identified {len(failed)} baseline control gap(s).",
        {"failed_tests": [item["test"] for item in failed]},
    )

    patch = apply_least_privilege_patch()
    emit(
        "PATCH_APPLIED",
        "defense_agent",
        "repair",
        "HARDENED",
        "Least-privilege policy patch applied inside the synthetic sandbox.",
        patch,
    )

    after = run_security_gauntlet(hardened=True)
    for item in after:
        decision = item["result"]["decision"]
        safe = decision in {"BLOCKED", "HUMAN_APPROVAL_REQUIRED"}
        emit(
            "ATTACK_REPLAYED",
            "red_agent",
            "retest",
            "CONTROL_HELD" if safe else "CONTROL_FAILED",
            f"Exact hardened scenario {item['test']} produced {decision}.",
            item,
        )

    certification = certify_after_retest()
    passport = certification["trust_passport"]
    emit(
        "JUDGE_VERDICT",
        "judge_agent",
        "certify",
        passport["status"],
        f"Judge evaluated {passport['tests_passed']}/{passport['tests_total']} required controls.",
        passport,
    )

    chain_valid = verify_chain(events)
    emit(
        "TRUST_PASSPORT_ISSUED" if passport["status"] == "CERTIFIED" and chain_valid else "CERTIFICATION_BLOCKED",
        "governor",
        "passport",
        "CERTIFIED" if passport["status"] == "CERTIFIED" and chain_valid else "BLOCKED",
        "Trust Passport issued from replayed evidence and a verified audit chain."
        if passport["status"] == "CERTIFIED" and chain_valid
        else "Certification blocked because required evidence or audit integrity failed.",
        {
            "trust_score": passport["trust_score"],
            "tests_passed": passport["tests_passed"],
            "tests_total": passport["tests_total"],
            "audit_chain_valid": chain_valid,
            "terminal_event_hash": events[-1].event_hash if events else None,
        },
    )

    final_chain_valid = verify_chain(events)
    artifact = {
        "system": "TRUSTFORGE ZERO",
        "sandbox": True,
        "certificate": passport["status"] if final_chain_valid else "BLOCKED",
        "trust_score": passport["trust_score"] if final_chain_valid else 0,
        "audit_chain_valid": final_chain_valid,
        "event_count": len(events),
        "terminal_event_hash": events[-1].event_hash,
        "events": [event_to_dict(event) for event in events],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")

    print("-" * 96)
    print(f"VERDICT: {artifact['certificate']} | TRUST SCORE: {artifact['trust_score']} | EVENTS: {artifact['event_count']}")
    print(f"AUDIT CHAIN: {'VERIFIED' if artifact['audit_chain_valid'] else 'INVALID'}")
    print(f"EVIDENCE: {OUTPUT}")
    print(f"TERMINAL HASH: {artifact['terminal_event_hash']}")
    print("=" * 96 + "\n")


if __name__ == "__main__":
    main()
