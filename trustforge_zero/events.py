"""Hash-chained event primitives for TRUSTFORGE ZERO live demos.

Events are deterministic, JSON-serializable, and safe to stream to a UI.  Each
record includes the previous event hash so a demo run can be independently
verified for tampering.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class TrustforgeEvent:
    seq: int
    timestamp: str
    event_type: str
    actor: str
    phase: str
    status: str
    summary: str
    payload: dict[str, Any]
    previous_hash: str
    event_hash: str


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def build_event(
    *,
    seq: int,
    event_type: str,
    actor: str,
    phase: str,
    status: str,
    summary: str,
    payload: dict[str, Any] | None = None,
    previous_hash: str = "GENESIS",
) -> TrustforgeEvent:
    timestamp = datetime.now(timezone.utc).isoformat()
    body = {
        "seq": seq,
        "timestamp": timestamp,
        "event_type": event_type,
        "actor": actor,
        "phase": phase,
        "status": status,
        "summary": summary,
        "payload": payload or {},
        "previous_hash": previous_hash,
    }
    event_hash = hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest()
    return TrustforgeEvent(**body, event_hash=event_hash)


def event_to_dict(event: TrustforgeEvent) -> dict[str, Any]:
    return asdict(event)


def event_to_json(event: TrustforgeEvent) -> str:
    return json.dumps(event_to_dict(event), ensure_ascii=False, sort_keys=True)


def verify_chain(events: list[TrustforgeEvent]) -> bool:
    previous = "GENESIS"
    for event in events:
        if event.previous_hash != previous:
            return False
        body = event_to_dict(event)
        claimed_hash = body.pop("event_hash")
        expected = hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest()
        if claimed_hash != expected:
            return False
        previous = event.event_hash
    return True
