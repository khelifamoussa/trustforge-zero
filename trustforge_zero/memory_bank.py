"""Provenance-gated cross-session memory bank for TRUSTFORGE ZERO.

The Fortified Enterprise Fleet challenge requires agents to maintain context
across long-running and asynchronous operations without bypassing enterprise
security controls. This module implements a first-party Firestore-backed memory
bank with explicit provenance, scope, classification, expiry, and revocation.

It is intentionally not branded as Google's managed Memory Bank product.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

MEMORY_COLLECTION = os.getenv("TRUSTFORGE_MEMORY_COLLECTION", "trustforge_memory")
DEFAULT_TTL_DAYS = int(os.getenv("TRUSTFORGE_MEMORY_TTL_DAYS", "30"))
ALLOWED_CLASSIFICATIONS = {"public", "internal", "confidential"}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _memory_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _client():
    from google.cloud import firestore

    project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCLOUD_PROJECT")
    return firestore.Client(project=project) if project else firestore.Client()


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    namespace: str
    subject: str
    value: dict[str, Any]
    classification: str
    source_run_id: str
    source_event_hash: str
    written_by: str
    created_at: str
    expires_at: str
    revoked: bool
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_memory_record(
    *,
    namespace: str,
    subject: str,
    value: dict[str, Any],
    classification: str,
    source_run_id: str,
    source_event_hash: str,
    written_by: str,
    ttl_days: int = DEFAULT_TTL_DAYS,
) -> MemoryRecord:
    """Create a deterministic, provenance-bound memory record.

    A write without source-run and source-event provenance is rejected. This is
    the same invariant used by the Memory Guard during certification.
    """

    if classification not in ALLOWED_CLASSIFICATIONS:
        raise ValueError(f"unsupported classification: {classification}")
    if not source_run_id.strip() or not source_event_hash.strip():
        raise ValueError("memory writes require source_run_id and source_event_hash")
    if ttl_days < 1 or ttl_days > 365:
        raise ValueError("ttl_days must be between 1 and 365")

    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=ttl_days)
    immutable_payload = {
        "namespace": namespace,
        "subject": subject,
        "value": value,
        "classification": classification,
        "source_run_id": source_run_id,
        "source_event_hash": source_event_hash,
        "written_by": written_by,
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "revoked": False,
    }
    content_hash = _memory_hash(immutable_payload)
    memory_id = f"mem-{content_hash[:20]}"
    return MemoryRecord(memory_id=memory_id, content_hash=content_hash, **immutable_payload)


def verify_memory_record(record: MemoryRecord | dict[str, Any]) -> bool:
    data = record.to_dict() if isinstance(record, MemoryRecord) else dict(record)
    stored_hash = data.pop("content_hash", None)
    data.pop("memory_id", None)
    if not stored_hash:
        return False
    return _memory_hash(data) == stored_hash


def persist_memory(record: MemoryRecord) -> dict[str, Any]:
    """Persist a verified memory item to Firestore with fail-safe reporting."""

    if not verify_memory_record(record):
        return {"persisted": False, "reason": "memory_integrity_failed"}
    try:
        db = _client()
        ref = db.collection(MEMORY_COLLECTION).document(record.memory_id)
        ref.set(record.to_dict(), merge=False)
        return {
            "backend": "firestore",
            "persisted": True,
            "collection": MEMORY_COLLECTION,
            "memory_id": record.memory_id,
            "content_hash": record.content_hash,
        }
    except Exception as exc:
        return {
            "backend": "firestore",
            "persisted": False,
            "collection": MEMORY_COLLECTION,
            "memory_id": record.memory_id,
            "error": f"{type(exc).__name__}: {exc}",
        }


def memory_bank_status() -> dict[str, Any]:
    try:
        db = _client()
        return {
            "backend": "firestore",
            "ready": True,
            "project": getattr(db, "project", None),
            "collection": MEMORY_COLLECTION,
            "provenance_required": True,
            "ttl_days": DEFAULT_TTL_DAYS,
            "classifications": sorted(ALLOWED_CLASSIFICATIONS),
            "cross_session": True,
        }
    except Exception as exc:
        return {
            "backend": "firestore",
            "ready": False,
            "project": os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCLOUD_PROJECT"),
            "collection": MEMORY_COLLECTION,
            "provenance_required": True,
            "ttl_days": DEFAULT_TTL_DAYS,
            "classifications": sorted(ALLOWED_CLASSIFICATIONS),
            "cross_session": True,
            "error": f"{type(exc).__name__}: {exc}",
        }
