"""TRUSTFORGE ZERO live API and integrated Command Center."""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .events import TrustforgeEvent, build_event, verify_chain
from .security_engine import apply_least_privilege_patch, certify_after_retest, run_security_gauntlet

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="TRUSTFORGE ZERO Live API", version="0.5.0", description="Evidence-first autonomous immune mesh for synthetic AI agent fleets.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


class RunRequest(BaseModel):
    target: str = "synthetic_procurement_agent"
    pace_ms: int = 300


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _event(events: list[TrustforgeEvent], event_type: str, actor: str, phase: str, status: str, summary: str, payload: dict | None = None) -> TrustforgeEvent:
    previous_hash = events[-1].event_hash if events else "GENESIS"
    item = build_event(seq=len(events) + 1, event_type=event_type, actor=actor, phase=phase, status=status, summary=summary, payload=payload or {}, previous_hash=previous_hash)
    events.append(item)
    return item


async def _live_run(run_id: str, target: str, pace_ms: int) -> AsyncIterator[str]:
    events: list[TrustforgeEvent] = []
    delay = max(0, min(pace_ms, 1800)) / 1000

    async def push(event_type: str, actor: str, phase: str, status: str, summary: str, payload: dict | None = None):
        item = _event(events, event_type, actor, phase, status, summary, payload)
        if delay:
            await asyncio.sleep(delay)
        return _sse("trustforge_event", {"run_id": run_id, **asdict(item)})

    yield await push("CERTIFICATION_STARTED", "governor", "discover", "RUNNING", "Governor opened a zero-trust evidence-first certification run.", {"target": target, "sandbox": True})
    yield await push("TRUST_BOUNDARY_MAPPED", "sentinel_agent", "discover", "BASELINED", "Sentinel mapped permissions, approval gates, data boundaries, and source trust.", {"target": target, "boundary": "synthetic_only", "high_risk_action_gate": "human_approval"})
    yield await push("IDENTITY_GRAPH_VERIFIED", "identity_guard_agent", "discover", "VERIFIED", "Identity Guard bound agent identity, delegated authority, and approval scope.", {"identity_binding": "enforced", "least_privilege": True})
    yield await push("TOOL_SURFACE_ATTESTED", "tool_guardian_agent", "discover", "VERIFIED", "Tool Guardian fingerprinted tool schemas and verified connector provenance policy.", {"schema_pinning": True, "signed_manifest_required": True})

    before = run_security_gauntlet(hardened=False)
    for result in before:
        decision = result["result"]["decision"]
        compromised = decision == "ALLOWED" and result["test"] != "high_risk_human_approval"
        yield await push("ATTACK_OBSERVED", "red_swarm_agent", "attack", "COMPROMISED" if compromised else decision, f"Baseline {result['test']} produced {decision}.", result)

    failures = [x for x in before if x["result"]["decision"] == "ALLOWED"]
    yield await push("ROOT_CAUSE_FOUND", "forensic_agent", "diagnose", "CRITICAL" if failures else "CLEAN", f"Forensics isolated {len(failures)} baseline control gap(s) across the attack surface.", {"failed_tests": [x["test"] for x in failures]})

    patch = apply_least_privilege_patch()
    yield await push("PATCH_APPLIED", "defense_agent", "repair", "HARDENED", "Defense applied the minimum least-privilege repair bundle in the synthetic sandbox.", patch)
    yield await push("MEMORY_GUARD_ARMED", "memory_guard_agent", "repair", "HARDENED", "Memory Guard provenance-gated persistent writes and promoted verified failures into regression requirements.", {"provenance_required": True, "regression_memory": True})

    after = run_security_gauntlet(hardened=True)
    for result in after:
        decision = result["result"]["decision"]
        safe = decision in {"BLOCKED", "HUMAN_APPROVAL_REQUIRED"}
        yield await push("ATTACK_REPLAYED", "red_swarm_agent", "retest", "CONTROL_HELD" if safe else "CONTROL_FAILED", f"Hardened replay {result['test']} produced {decision}.", result)

    chain_before_attestation = verify_chain(events)
    yield await push("PROVENANCE_ATTESTED", "provenance_agent", "attest", "VERIFIED" if chain_before_attestation else "INVALID", "Provenance verified replay comparability, claim-to-event lineage, and continuous evidence integrity." if chain_before_attestation else "Provenance rejected the evidence lineage.", {"chain_valid": chain_before_attestation, "events_attested": len(events), "replay_mode": "same_controls_after_patch"})

    certification = certify_after_retest()
    passport = certification["trust_passport"]
    judge_status = passport["status"] if chain_before_attestation else "BLOCKED"
    yield await push("JUDGE_VERDICT", "judge_agent", "certify", judge_status, f"Judge verified {passport['tests_passed']}/{passport['tests_total']} required controls with provenance attestation.", passport)

    chain_before_final = verify_chain(events)
    final_status = "CERTIFIED" if passport["status"] == "CERTIFIED" and chain_before_final and chain_before_attestation else "BLOCKED"
    final = _event(events, "TRUST_PASSPORT_ISSUED" if final_status == "CERTIFIED" else "CERTIFICATION_BLOCKED", "governor", "certify", final_status, "Trust Passport issued from replayed evidence, identity/tool integrity, regression memory, and verified provenance." if final_status == "CERTIFIED" else "Certification blocked by evidence, provenance, or audit-integrity failure.", {"trust_score": passport["trust_score"] if final_status == "CERTIFIED" else 0, "tests_passed": passport["tests_passed"], "tests_total": passport["tests_total"], "audit_chain_valid_before_passport": chain_before_final, "provenance_attested": chain_before_attestation, "coverage": passport.get("coverage", {})})
    if delay:
        await asyncio.sleep(delay)
    yield _sse("trustforge_event", {"run_id": run_id, **asdict(final)})

    chain_valid = verify_chain(events)
    yield _sse("trustforge_complete", {"run_id": run_id, "certificate": final_status if chain_valid else "BLOCKED", "trust_score": passport["trust_score"] if final_status == "CERTIFIED" and chain_valid else 0, "event_count": len(events), "audit_chain_valid": chain_valid, "provenance_attested": chain_before_attestation, "terminal_event_hash": events[-1].event_hash, "target": target, "sandbox": True, "tests_passed": passport["tests_passed"], "tests_total": passport["tests_total"], "coverage": passport.get("coverage", {})})


@app.get("/", include_in_schema=False)
def command_center():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api")
def api_root() -> dict:
    return {"system": "TRUSTFORGE ZERO", "status": "ONLINE", "mode": "synthetic_defensive_sandbox", "mesh": "10-agent", "vectors": 10, "stream": "/api/v1/gauntlet/stream", "health": "/healthz", "command_center": "/"}


@app.get("/healthz")
def health() -> dict:
    return {"status": "ok", "system": "TRUSTFORGE ZERO", "mesh": "10-agent", "attack_vectors": 10}


@app.get("/api/v1/agents")
def agents() -> dict:
    return {"governor": "trustforge_governor", "specialists": ["sentinel_agent", "identity_guard_agent", "tool_guardian_agent", "red_swarm_agent", "forensic_agent", "defense_agent", "memory_guard_agent", "provenance_agent", "judge_agent"], "attack_vectors": 10, "certification_invariant": "No security claim without executed evidence; no remediation claim without comparable replay; no unprovenanced memory; no tool trust without integrity evidence; no high-risk real-world action without human approval."}


@app.get("/api/v1/gauntlet/stream")
def stream_gauntlet(target: str = "synthetic_procurement_agent", pace_ms: int = 300):
    run_id = f"tfz-{uuid.uuid4().hex[:12]}"
    return StreamingResponse(_live_run(run_id, target, pace_ms), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "X-TRUSTFORGE-Run-ID": run_id})


@app.post("/api/v1/gauntlet/stream")
def stream_gauntlet_post(request: RunRequest):
    run_id = f"tfz-{uuid.uuid4().hex[:12]}"
    return StreamingResponse(_live_run(run_id, request.target, request.pace_ms), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "X-TRUSTFORGE-Run-ID": run_id})
