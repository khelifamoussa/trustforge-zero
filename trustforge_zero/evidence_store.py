"""Persistent evidence store for TRUSTFORGE ZERO.

Firestore is preferred in Google Cloud. Persistence is deliberately fail-safe:
security/certification execution never crashes merely because the evidence
backend is unavailable; the API reports persistence state explicitly.
"""

from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Iterable

from .events import TrustforgeEvent

COLLECTION = os.getenv("TRUSTFORGE_FIRESTORE_COLLECTION", "trustforge_runs")


def _client():
    from google.cloud import firestore

    project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCLOUD_PROJECT")
    return firestore.Client(project=project) if project else firestore.Client()


def persistence_status() -> dict:
    try:
        db = _client()
        return {
            "backend": "firestore",
            "ready": True,
            "project": getattr(db, "project", None),
            "collection": COLLECTION,
        }
    except Exception as exc:
        return {
            "backend": "firestore",
            "ready": False,
            "project": os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCLOUD_PROJECT"),
            "collection": COLLECTION,
            "error": f"{type(exc).__name__}: {exc}",
        }


def persist_run(run_id: str, events: Iterable[TrustforgeEvent], final: dict) -> dict:
    """Persist immutable run summary plus every hash-chained evidence event."""
    try:
        db = _client()
        run_ref = db.collection(COLLECTION).document(run_id)
        event_list = list(events)
        batch = db.batch()
        batch.set(
            run_ref,
            {
                **final,
                "run_id": run_id,
                "event_count": len(event_list),
                "persisted_at": datetime.now(timezone.utc),
                "storage_backend": "firestore",
            },
        )
        for event in event_list:
            event_ref = run_ref.collection("events").document(f"{event.seq:04d}")
            batch.set(event_ref, asdict(event))
        batch.commit()
        return {
            "backend": "firestore",
            "persisted": True,
            "collection": COLLECTION,
            "run_id": run_id,
            "events_persisted": len(event_list),
        }
    except Exception as exc:
        return {
            "backend": "firestore",
            "persisted": False,
            "collection": COLLECTION,
            "run_id": run_id,
            "events_persisted": 0,
            "error": f"{type(exc).__name__}: {exc}",
        }
