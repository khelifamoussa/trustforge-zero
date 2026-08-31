"""Resilience and recovery primitives for TRUSTFORGE ZERO.

This module models the production behaviors the demo must prove before a Trust
Passport can be issued: failure detection, isolation, checkpoint continuity,
retry/reassignment, replay safety, and an explicit recovery gate.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RecoveryPolicy:
    max_retries: int = 2
    require_checkpoint: bool = True
    require_isolation: bool = True
    require_replay_after_recovery: bool = True
    block_certification_on_failure: bool = True


@dataclass(frozen=True)
class RecoveryReport:
    agent: str
    failure_mode: str
    detected: bool
    isolated: bool
    checkpoint_id: str | None
    retries: int
    reassigned_to: str | None
    resumed: bool
    replay_verified: bool
    recovery_succeeded: bool
    certification_gate: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_recovery_drill(
    *,
    agent: str = "forensic_agent",
    failure_mode: str = "timeout",
    inject_failure: bool = True,
    recovery_available: bool = True,
    policy: RecoveryPolicy | None = None,
) -> RecoveryReport:
    """Run a deterministic, non-destructive recovery drill.

    The drill intentionally does not execute external actions. It proves the
    control plane semantics needed by the live demo. A failed recovery must
    close the certification gate.
    """

    policy = policy or RecoveryPolicy()

    if not inject_failure:
        return RecoveryReport(
            agent=agent,
            failure_mode="none",
            detected=False,
            isolated=False,
            checkpoint_id="cp-pre-diagnose",
            retries=0,
            reassigned_to=None,
            resumed=True,
            replay_verified=True,
            recovery_succeeded=True,
            certification_gate="OPEN",
        )

    detected = True
    isolated = policy.require_isolation
    checkpoint_id = "cp-pre-diagnose" if policy.require_checkpoint else None
    retries = 1 if recovery_available else policy.max_retries
    reassigned_to = "forensic_agent_recovery_slot" if recovery_available else None
    resumed = bool(recovery_available and (checkpoint_id or not policy.require_checkpoint))
    replay_verified = bool(resumed and policy.require_replay_after_recovery)
    recovery_succeeded = bool(detected and isolated and resumed and replay_verified)
    gate = "OPEN" if recovery_succeeded else "BLOCKED"

    return RecoveryReport(
        agent=agent,
        failure_mode=failure_mode,
        detected=detected,
        isolated=isolated,
        checkpoint_id=checkpoint_id,
        retries=retries,
        reassigned_to=reassigned_to,
        resumed=resumed,
        replay_verified=replay_verified,
        recovery_succeeded=recovery_succeeded,
        certification_gate=gate,
    )


def certification_recovery_gate(report: RecoveryReport) -> bool:
    """Return True only when runtime/recovery evidence is certification-safe.

    A healthy run with no injected failure does not need failure detection or
    isolation. A run that actually encountered a failure must prove detection,
    isolation, resume, and replay before certification can proceed.
    """

    base_safe = bool(
        report.recovery_succeeded
        and report.certification_gate == "OPEN"
        and report.resumed
        and report.replay_verified
    )
    if not base_safe:
        return False

    if report.failure_mode == "none":
        return True

    return bool(report.detected and report.isolated)
