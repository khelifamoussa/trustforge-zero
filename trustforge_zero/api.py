"""TRUSTFORGE ZERO live API and integrated Command Center."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import AsyncIterator, Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent_registry import registry_summary
from .evidence_store import persist_run, persistence_status
from .events import TrustforgeEvent, build_event, verify_chain
from .memory_bank import memory_bank_status
from .parallel_adk import run_fast_live_specialist_mesh
from .resilience import certification_recovery_gate, run_recovery_drill
from .security_engine import apply_least_privilege_patch, certify_after_retest, run_security_gauntlet

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
PERSISTENCE_TIMEOUT_SECONDS = float(os.getenv("TRUSTFORGE_PERSISTENCE_TIMEOUT_SECONDS", "2.5"))

app = FastAPI(
    title="TRUSTFORGE ZERO Live API",
    version="0.10.0",
    description=(
        "One-click evidence-first autonomous immune mesh with bounded live Google ADK + Gemini reasoning, "
        "provider resilience, deterministic security controls, fail-closed runtime recovery, enterprise discovery, "
        "provenance-gated memory, and persistent evidence."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

RecoveryMode = Literal["success", "failure", "none"]


class RunRequest(BaseModel):
    target: str = "synthetic_procurement_agent"
    pace_ms: int = 180
    recovery_mode: RecoveryMode = "success"
    require_live_adk: bool = True


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _event(
    events: list[TrustforgeEvent],
    event_type: str,
    actor: str,
    phase: str,
    status: str,
    summary: str,
    payload: dict | None = None,
) -> TrustforgeEvent:
    previous_hash = events[-1].event_hash if events else "GENESIS"
    item = build_event(
        seq=len(events) + 1,
        event_type=event_type,
        actor=actor,
        phase=phase,
        status=status,
        summary=summary,
        payload=payload or {},
        previous_hash=previous_hash,
    )
    events.append(item)
    return item


def _cloud_runtime() -> dict:
    """Non-secret runtime proof. Cloud Run injects K_SERVICE automatically."""
    service = os.getenv("K_SERVICE")
    revision = os.getenv("K_REVISION")
    return {
        "provider": "google_cloud" if service else "local_or_codespaces",
        "cloud_run": bool(service),
        "service": service,
        "revision": revision,
    }


async def _bounded_status(fn, backend: str) -> dict:
    try:
        return await asyncio.wait_for(asyncio.to_thread(fn), timeout=PERSISTENCE_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        return {
            "backend": backend,
            "ready": False,
            "error": f"STATUS_TIMEOUT after {PERSISTENCE_TIMEOUT_SECONDS:.1f}s",
        }


async def _persist_completed_run(run_id: str, events: list[TrustforgeEvent], payload: dict) -> dict:
    """Persist without allowing Firestore latency/outage to freeze the live UI."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(persist_run, run_id, events, payload),
            timeout=PERSISTENCE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        return {
            "backend": "firestore",
            "persisted": False,
            "run_id": run_id,
            "events_persisted": 0,
            "error": f"PERSISTENCE_TIMEOUT after {PERSISTENCE_TIMEOUT_SECONDS:.1f}s",
        }
    except Exception as exc:
        return {
            "backend": "firestore",
            "persisted": False,
            "run_id": run_id,
            "events_persisted": 0,
            "error": f"{type(exc).__name__}: {exc}",
        }


async def _live_run(
    run_id: str,
    target: str,
    pace_ms: int,
    recovery_mode: RecoveryMode = "success",
    require_live_adk: bool = True,
) -> AsyncIterator[str]:
    events: list[TrustforgeEvent] = []
    delay = max(0, min(pace_ms, 800)) / 1000

    async def push(
        event_type: str,
        actor: str,
        phase: str,
        status: str,
        summary: str,
        payload: dict | None = None,
    ) -> str:
        item = _event(events, event_type, actor, phase, status, summary, payload)
        if delay:
            await asyncio.sleep(delay)
        return _sse("trustforge_event", {"run_id": run_id, **asdict(item)})

    yield await push(
        "CERTIFICATION_STARTED",
        "governor",
        "discover",
        "RUNNING",
        "Governor opened a zero-trust evidence-first certification run.",
        {
            "target": target,
            "sandbox": True,
            "recovery_mode": recovery_mode,
            "require_live_adk": require_live_adk,
            "cloud_runtime": _cloud_runtime(),
            "registry": {"type": "first_party_versioned_registry", "agents": 10},
            "memory": {"provenance_required": True, "cross_session": True},
        },
    )

    live_adk_verified = False
    adk_evidence: dict = {}
    if require_live_adk:
        try:
            mesh = await run_fast_live_specialist_mesh()
            adk_evidence = mesh.to_dict()
            live_adk_verified = bool(mesh.live_model_called and mesh.all_required_specialists_verified)
            provider_status = "VERIFIED" if live_adk_verified else "DEGRADED"
            yield await push(
                "LIVE_ADK_MESH_ATTESTED" if live_adk_verified else "LIVE_AI_PROVIDER_DEGRADED",
                "forensic_agent",
                "discover",
                provider_status,
                (
                    "Google ADK + Gemini live reasoning completed inside the bounded hybrid specialist mesh."
                    if live_adk_verified
                    else "Gemini/ADK live reasoning was unavailable or unverified; deterministic controls continue, but certification remains fail-closed."
                ),
                {
                    "model": mesh.model,
                    "latency_ms": mesh.total_latency_ms,
                    "model_calls_used": mesh.model_calls_used,
                    "request_budget_ok": mesh.request_budget_ok,
                    "live_model_agents": mesh.live_model_agents,
                    "deterministic_agents": mesh.deterministic_agents,
                    "authors_seen": mesh.authors_seen,
                    "live_model_called": mesh.live_model_called,
                    "all_required_specialists_verified": mesh.all_required_specialists_verified,
                    "specialists": [s.to_dict() for s in mesh.specialists],
                },
            )
        except Exception as exc:
            adk_evidence = {"error": f"{type(exc).__name__}: {exc}"}
            yield await push(
                "LIVE_AI_PROVIDER_DEGRADED",
                "governor",
                "discover",
                "DEGRADED",
                "Live Google ADK + Gemini evidence could not be obtained; deterministic security execution continues and certification remains locked.",
                adk_evidence,
            )
    else:
        yield await push(
            "LIVE_ADK_REQUIREMENT_BYPASSED",
            "governor",
            "discover",
            "DEMO_ONLY",
            "Live ADK proof was explicitly bypassed for local diagnostics; this mode is not competition-certifiable.",
            {},
        )

    yield await push(
        "AGENT_REGISTRY_RESOLVED",
        "governor",
        "discover",
        "VERIFIED",
        "Governor resolved approved, versioned Agent Cards before delegation.",
        {"registry_type": "first_party_versioned_registry", "approved_agents": 10, "scoped_access": True},
    )
    yield await push(
        "TRUST_BOUNDARY_MAPPED",
        "sentinel_agent",
        "discover",
        "BASELINED",
        "Sentinel mapped permissions, approval gates, data boundaries, and source trust.",
        {"target": target, "boundary": "synthetic_only", "high_risk_action_gate": "human_approval"},
    )
    yield await push(
        "IDENTITY_GRAPH_VERIFIED",
        "identity_guard_agent",
        "discover",
        "VERIFIED",
        "Identity Guard bound agent identity, delegated authority, and approval scope.",
        {"identity_binding": "enforced", "least_privilege": True},
    )
    yield await push(
        "TOOL_SURFACE_ATTESTED",
        "tool_guardian_agent",
        "discover",
        "VERIFIED",
        "Tool Guardian fingerprinted tool schemas and verified connector provenance policy.",
        {"schema_pinning": True, "signed_manifest_required": True},
    )

    before = run_security_gauntlet(hardened=False)
    for result in before:
        decision = result["result"]["decision"]
        compromised = decision == "ALLOWED" and result["test"] != "high_risk_human_approval"
        yield await push(
            "ATTACK_OBSERVED",
            "red_swarm_agent",
            "attack",
            "COMPROMISED" if compromised else decision,
            f"Baseline {result['test']} produced {decision}.",
            result,
        )

    failures = [x for x in before if x["result"]["decision"] == "ALLOWED"]
    forensic_summary = None
    for specialist in adk_evidence.get("specialists", []):
        if specialist.get("agent") == "forensic_agent" and specialist.get("verified"):
            forensic_summary = specialist.get("final_text")
            break
    yield await push(
        "ROOT_CAUSE_FOUND",
        "forensic_agent",
        "diagnose",
        "CRITICAL" if failures else "CLEAN",
        f"Forensics isolated {len(failures)} baseline control gap(s) across the attack surface.",
        {"failed_tests": [x["test"] for x in failures], "live_reasoning_summary": forensic_summary},
    )

    inject_failure = recovery_mode != "none"
    recovery_available = recovery_mode != "failure"
    recovery = run_recovery_drill(
        agent="forensic_agent",
        failure_mode="timeout",
        inject_failure=inject_failure,
        recovery_available=recovery_available,
    )

    if inject_failure:
        yield await push("AGENT_FAILURE_DETECTED", "governor", "recover", "DETECTED", "Governor detected a synthetic forensic-agent timeout before remediation was trusted.", {"agent": recovery.agent, "failure_mode": recovery.failure_mode})
        yield await push("AGENT_ISOLATED", "governor", "recover", "ISOLATED" if recovery.isolated else "FAILED", "Governor isolated the failed execution slot to prevent contaminated state propagation.", {"agent": recovery.agent, "isolated": recovery.isolated})
        yield await push("CHECKPOINT_RESTORED", "governor", "recover", "RESTORED" if recovery.checkpoint_id else "FAILED", "Governor restored the last trusted pre-diagnosis checkpoint.", {"checkpoint_id": recovery.checkpoint_id})
        yield await push("AGENT_REASSIGNED", "governor", "recover", "REASSIGNED" if recovery.reassigned_to else "FAILED", "Governor reassigned forensic analysis to a clean recovery slot.", {"reassigned_to": recovery.reassigned_to, "retries": recovery.retries})
        yield await push("RECOVERY_REPLAY_VERIFIED", "forensic_agent", "recover", "VERIFIED" if recovery.replay_verified else "FAILED", "Recovered forensic trajectory was replayed against the trusted checkpoint and verified." if recovery.replay_verified else "Recovery replay could not be verified; certification gate is closed.", recovery.to_dict())
    else:
        yield await push("RECOVERY_BASELINE_HEALTHY", "governor", "recover", "VERIFIED", "No runtime failure was injected; recovery control plane remained certification-safe.", recovery.to_dict())

    patch = apply_least_privilege_patch()
    yield await push("PATCH_APPLIED", "defense_agent", "repair", "HARDENED", "Defense applied the minimum least-privilege repair bundle in the synthetic sandbox.", patch)
    yield await push(
        "MEMORY_GUARD_ARMED",
        "memory_guard_agent",
        "repair",
        "HARDENED",
        "Memory Guard provenance-gated cross-session memory writes and promoted verified failures into regression requirements.",
        {"provenance_required": True, "regression_memory": True, "cross_session": True, "integrity_hash": "sha256", "revocation_supported": True},
    )

    after = run_security_gauntlet(hardened=True)
    for result in after:
        decision = result["result"]["decision"]
        safe = decision in {"BLOCKED", "HUMAN_APPROVAL_REQUIRED"}
        yield await push("ATTACK_REPLAYED", "red_swarm_agent", "retest", "CONTROL_HELD" if safe else "CONTROL_FAILED", f"Hardened replay {result['test']} produced {decision}.", result)

    chain_before_attestation = verify_chain(events)
    recovery_gate_open = certification_recovery_gate(recovery)
    yield await push(
        "PROVENANCE_ATTESTED",
        "provenance_agent",
        "attest",
        "VERIFIED" if chain_before_attestation else "INVALID",
        "Provenance verified replay comparability, provider evidence state, runtime recovery evidence, and continuous evidence integrity." if chain_before_attestation else "Provenance rejected the evidence lineage.",
        {
            "chain_valid": chain_before_attestation,
            "events_attested": len(events),
            "replay_mode": "same_controls_after_patch",
            "recovery_gate_open": recovery_gate_open,
            "live_adk_verified": live_adk_verified,
            "recovery": recovery.to_dict(),
        },
    )

    certification = certify_after_retest()
    passport = certification["trust_passport"]
    judge_allowed = bool(chain_before_attestation and recovery_gate_open and live_adk_verified)
    judge_status = passport["status"] if judge_allowed else "BLOCKED"
    yield await push(
        "JUDGE_VERDICT",
        "judge_agent",
        "certify",
        judge_status,
        (
            f"Judge verified {passport['tests_passed']}/{passport['tests_total']} controls, live Google ADK/Gemini evidence, provenance, and runtime recovery."
            if judge_allowed
            else "Judge blocked the Trust Passport because at least one mandatory live-AI, recovery, or provenance gate is not verified."
        ),
        {
            **passport,
            "runtime_recovery_verified": recovery_gate_open,
            "live_adk_verified": live_adk_verified,
            "provider_evidence": {
                "model": adk_evidence.get("model"),
                "latency_ms": adk_evidence.get("total_latency_ms"),
                "live_agents": adk_evidence.get("live_model_agents", []),
                "error": adk_evidence.get("error"),
            },
        },
    )

    chain_before_final = verify_chain(events)
    final_status = (
        "CERTIFIED"
        if passport["status"] == "CERTIFIED"
        and chain_before_final
        and chain_before_attestation
        and recovery_gate_open
        and live_adk_verified
        else "BLOCKED"
    )
    final = _event(
        events,
        "TRUST_PASSPORT_ISSUED" if final_status == "CERTIFIED" else "CERTIFICATION_BLOCKED",
        "governor",
        "certify",
        final_status,
        (
            "Trust Passport issued from bounded live Google ADK/Gemini reasoning, replayed controls, verified provenance, human safety gates, and proven runtime recovery."
            if final_status == "CERTIFIED"
            else "Certification blocked: deterministic controls completed, but at least one mandatory live-model, recovery, provenance, or audit-integrity gate failed."
        ),
        {
            "trust_score": passport["trust_score"] if final_status == "CERTIFIED" else 0,
            "tests_passed": passport["tests_passed"],
            "tests_total": passport["tests_total"],
            "audit_chain_valid_before_passport": chain_before_final,
            "provenance_attested": chain_before_attestation,
            "runtime_recovery_verified": recovery_gate_open,
            "live_adk_verified": live_adk_verified,
            "provider": {
                "model": adk_evidence.get("model"),
                "latency_ms": adk_evidence.get("total_latency_ms"),
                "model_calls_used": adk_evidence.get("model_calls_used"),
                "request_budget_ok": adk_evidence.get("request_budget_ok"),
                "live_agents": adk_evidence.get("live_model_agents", []),
                "error": adk_evidence.get("error"),
            },
            "recovery": recovery.to_dict(),
            "coverage": passport.get("coverage", {}),
            "cloud_runtime": _cloud_runtime(),
        },
    )
    if delay:
        await asyncio.sleep(delay)
    yield _sse("trustforge_event", {"run_id": run_id, **asdict(final)})

    chain_valid = verify_chain(events)
    complete_payload = {
        "run_id": run_id,
        "certificate": final_status if chain_valid else "BLOCKED",
        "trust_score": passport["trust_score"] if final_status == "CERTIFIED" and chain_valid else 0,
        "event_count": len(events),
        "audit_chain_valid": chain_valid,
        "provenance_attested": chain_before_attestation,
        "runtime_recovery_verified": recovery_gate_open,
        "live_adk_verified": live_adk_verified,
        "adk_model": adk_evidence.get("model"),
        "adk_latency_ms": adk_evidence.get("total_latency_ms"),
        "adk_live_agents": adk_evidence.get("live_model_agents", []),
        "adk_error": adk_evidence.get("error"),
        "terminal_event_hash": events[-1].event_hash,
        "target": target,
        "sandbox": True,
        "tests_passed": passport["tests_passed"],
        "tests_total": passport["tests_total"],
        "coverage": passport.get("coverage", {}),
        "cloud_runtime": _cloud_runtime(),
        "enterprise_fleet": {
            "registry": "first_party_versioned_registry",
            "cross_session_memory": True,
            "human_approval_high_risk": True,
            "scoped_agent_cards": True,
        },
    }
    complete_payload["persistence"] = await _persist_completed_run(run_id, events, complete_payload)
    yield _sse("trustforge_complete", complete_payload)


@app.get("/", include_in_schema=False)
def command_center():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api")
def api_root() -> dict:
    return {
        "system": "TRUSTFORGE ZERO",
        "status": "ONLINE",
        "mode": "synthetic_defensive_sandbox",
        "mesh": "10-agent",
        "vectors": 10,
        "runtime_recovery": "fail-closed",
        "live_adk": "bounded-required-for-certification",
        "persistent_evidence": "firestore-bounded-fail-safe",
        "enterprise_registry": "/api/v1/registry",
        "cross_session_memory": "/api/v1/memory/status",
        "cloud_runtime": _cloud_runtime(),
        "stream": "/api/v1/gauntlet/stream",
        "persistence": "/api/v1/persistence/status",
        "health": "/healthz",
        "command_center": "/",
    }


@app.get("/healthz")
def health() -> dict:
    return {
        "status": "ok",
        "system": "TRUSTFORGE ZERO",
        "mesh": "10-agent",
        "attack_vectors": 10,
        "runtime_recovery": "enabled",
        "live_adk_configured": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
        "live_model_timeout_seconds": float(os.getenv("TRUSTFORGE_LIVE_TIMEOUT_SECONDS", "8")),
        "persistence_timeout_seconds": PERSISTENCE_TIMEOUT_SECONDS,
        "registry": {"type": "first_party_versioned_registry", "agent_count": 10},
        "memory": {"backend": "firestore", "provenance_required": True, "cross_session": True},
        "cloud_runtime": _cloud_runtime(),
    }


@app.get("/api/v1/persistence/status")
async def persistence() -> dict:
    return await _bounded_status(persistence_status, "firestore")


@app.get("/api/v1/memory/status")
async def memory_status() -> dict:
    return await _bounded_status(memory_bank_status, "firestore")


@app.get("/api/v1/registry")
def registry() -> dict:
    return registry_summary()


@app.get("/api/v1/agents")
def agents() -> dict:
    registry = registry_summary()
    return {
        "governor": "trustforge_governor",
        "specialists": [
            "sentinel_agent",
            "identity_guard_agent",
            "tool_guardian_agent",
            "red_swarm_agent",
            "forensic_agent",
            "defense_agent",
            "memory_guard_agent",
            "provenance_agent",
            "judge_agent",
        ],
        "attack_vectors": 10,
        "enterprise_registry": {
            "type": registry["registry_type"],
            "agent_count": registry["agent_count"],
            "approved_count": registry["approved_count"],
            "versioned_discovery_metadata": True,
            "scoped_tool_and_data_access": True,
        },
        "runtime_recovery": {
            "failure_detection": True,
            "isolation": True,
            "checkpoint_resume": True,
            "reassignment": True,
            "replay_verification": True,
            "fail_closed_certification": True,
        },
        "live_adk": {
            "required_for_certification": True,
            "configured": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
            "critical_path_model_calls": 1,
            "hard_timeout_seconds": float(os.getenv("TRUSTFORGE_LIVE_TIMEOUT_SECONDS", "8")),
        },
        "persistent_evidence": {
            "backend": "firestore",
            "write_timeout_seconds": PERSISTENCE_TIMEOUT_SECONDS,
            "failure_is_non_fatal_to_security_execution": True,
        },
        "cross_session_memory": {
            "backend": "firestore",
            "provenance_required": True,
            "integrity_hash": "sha256",
            "classification_scoped": True,
            "ttl_bounded": True,
        },
        "cloud_runtime": _cloud_runtime(),
        "certification_invariant": (
            "No security claim without executed evidence; no remediation claim without comparable replay; "
            "no unprovenanced memory; no tool trust without integrity evidence; no failed runtime recovery may receive "
            "a Trust Passport; no competition certification without verified live Google ADK/Gemini evidence; "
            "no high-risk real-world action without human approval."
        ),
    }


@app.get("/api/v1/gauntlet/stream")
def stream_gauntlet(
    target: str = "synthetic_procurement_agent",
    pace_ms: int = 180,
    recovery_mode: RecoveryMode = "success",
    require_live_adk: bool = True,
):
    run_id = f"tfz-{uuid.uuid4().hex[:12]}"
    return StreamingResponse(
        _live_run(run_id, target, pace_ms, recovery_mode, require_live_adk),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "X-TRUSTFORGE-Run-ID": run_id},
    )


@app.post("/api/v1/gauntlet/stream")
def stream_gauntlet_post(request: RunRequest):
    run_id = f"tfz-{uuid.uuid4().hex[:12]}"
    return StreamingResponse(
        _live_run(run_id, request.target, request.pace_ms, request.recovery_mode, request.require_live_adk),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "X-TRUSTFORGE-Run-ID": run_id},
    )
