from dataclasses import replace

import pytest

from trustforge_zero.memory_bank import build_memory_record, verify_memory_record


def test_memory_requires_provenance():
    with pytest.raises(ValueError):
        build_memory_record(
            namespace="regression",
            subject="indirect_prompt_injection",
            value={"decision": "BLOCKED"},
            classification="internal",
            source_run_id="",
            source_event_hash="",
            written_by="memory_guard_agent",
        )


def test_memory_record_is_hash_attested():
    record = build_memory_record(
        namespace="regression",
        subject="indirect_prompt_injection",
        value={"decision": "BLOCKED", "promote_to_regression": True},
        classification="internal",
        source_run_id="tfz-test",
        source_event_hash="abc123",
        written_by="memory_guard_agent",
    )
    assert record.memory_id.startswith("mem-")
    assert verify_memory_record(record) is True


def test_memory_tampering_is_detected():
    record = build_memory_record(
        namespace="regression",
        subject="tool_schema_poisoning",
        value={"decision": "BLOCKED"},
        classification="confidential",
        source_run_id="tfz-test",
        source_event_hash="def456",
        written_by="memory_guard_agent",
    )
    tampered = replace(record, value={"decision": "ALLOWED"})
    assert verify_memory_record(tampered) is False
