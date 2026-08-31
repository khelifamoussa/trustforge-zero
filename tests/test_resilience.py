from trustforge_zero.resilience import certification_recovery_gate, run_recovery_drill


def test_runtime_failure_recovers_with_checkpoint_reassignment_and_replay():
    report = run_recovery_drill(inject_failure=True, recovery_available=True)
    assert report.detected is True
    assert report.isolated is True
    assert report.checkpoint_id is not None
    assert report.reassigned_to is not None
    assert report.resumed is True
    assert report.replay_verified is True
    assert report.recovery_succeeded is True
    assert certification_recovery_gate(report) is True


def test_failed_recovery_closes_certification_gate():
    report = run_recovery_drill(inject_failure=True, recovery_available=False)
    assert report.detected is True
    assert report.recovery_succeeded is False
    assert report.certification_gate == "BLOCKED"
    assert certification_recovery_gate(report) is False


def test_no_failure_path_remains_certification_safe():
    report = run_recovery_drill(inject_failure=False)
    assert report.failure_mode == "none"
    assert report.recovery_succeeded is True
    assert report.certification_gate == "OPEN"
    assert report.resumed is True
    assert report.replay_verified is True
    assert certification_recovery_gate(report) is True
