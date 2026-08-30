"""Live Google ADK orchestration probe for TRUSTFORGE ZERO.

This module deliberately separates LLM/agent reasoning from deterministic
security certification. Gemini + ADK may analyze, delegate, and recommend, but
only the deterministic evidence gates may issue a Trust Passport.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import asdict, dataclass
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .agent import app


@dataclass
class AdkTraceEvent:
    seq: int
    author: str
    text: str
    is_final: bool


@dataclass
class AdkRunEvidence:
    run_id: str
    session_id: str
    app_name: str
    model: str
    prompt: str
    events: list[AdkTraceEvent]
    final_text: str
    authors_seen: list[str]
    live_model_called: bool

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["events"] = [asdict(e) for e in self.events]
        return data


def _event_text(event: Any) -> str:
    content = getattr(event, "content", None)
    parts = getattr(content, "parts", None) or []
    chunks: list[str] = []
    for part in parts:
        text = getattr(part, "text", None)
        if text:
            chunks.append(text)
    return "\n".join(chunks).strip()


def _is_final(event: Any) -> bool:
    method = getattr(event, "is_final_response", None)
    if callable(method):
        try:
            return bool(method())
        except Exception:
            return False
    return False


async def run_live_governor_probe(
    prompt: str | None = None,
    *,
    user_id: str = "trustforge-demo",
    session_id: str | None = None,
) -> AdkRunEvidence:
    """Execute the real ADK App against Gemini and capture its event trace.

    This is a non-destructive reasoning probe. It instructs the Governor to
    describe delegation and certification invariants without running attacks or
    external actions. The resulting authors/text become proof that the ADK app
    and Gemini model were actually invoked.
    """

    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required for live ADK execution")

    run_id = f"adk-{uuid.uuid4().hex[:12]}"
    session_id = session_id or f"session-{uuid.uuid4().hex[:12]}"
    prompt = prompt or (
        "TRUSTFORGE ZERO live orchestration proof. Identify yourself as the Governor. "
        "Explain which specialist agents you would delegate to for: trust-boundary discovery, "
        "identity verification, tool integrity, defensive adversarial testing, forensic diagnosis, "
        "least-privilege repair, memory provenance, evidence attestation, and independent judgment. "
        "State the invariant that certification must remain deterministic and fail-closed. "
        "Do not execute any attack or external action. Keep the answer concise."
    )

    sessions = InMemorySessionService()
    session = await sessions.create_session(
        app_name=app.name,
        user_id=user_id,
        session_id=session_id,
        state={"trustforge_run_id": run_id, "mode": "live_adk_probe"},
    )
    runner = Runner(app=app, session_service=sessions)
    message = types.Content(role="user", parts=[types.Part(text=prompt)])

    trace: list[AdkTraceEvent] = []
    final_text = ""
    authors: list[str] = []

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=message,
    ):
        author = str(getattr(event, "author", "unknown"))
        text = _event_text(event)
        final = _is_final(event)
        if author not in authors:
            authors.append(author)
        if text or final:
            trace.append(
                AdkTraceEvent(
                    seq=len(trace) + 1,
                    author=author,
                    text=text,
                    is_final=final,
                )
            )
        if final and text:
            final_text = text
        elif text and not final_text:
            final_text = text

    return AdkRunEvidence(
        run_id=run_id,
        session_id=session.id,
        app_name=app.name,
        model=os.getenv("TRUSTFORGE_MODEL", "gemini-3.5-flash"),
        prompt=prompt,
        events=trace,
        final_text=final_text,
        authors_seen=authors,
        live_model_called=bool(trace),
    )


def run_live_governor_probe_sync(prompt: str | None = None) -> dict[str, Any]:
    """Synchronous helper for scripts, smoke tests, and later API integration."""

    return asyncio.run(run_live_governor_probe(prompt)).to_dict()
