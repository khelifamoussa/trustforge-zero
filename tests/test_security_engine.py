from trustforge_zero.security_engine import certify_after_retest


def test_injection_succeeds_before_and_is_blocked_after_patch():
    report = certify_after_retest()
    assert report["before"]["result"]["decision"] == "ALLOWED"
    assert report["after"]["result"]["decision"] == "BLOCKED"
    assert report["certificate"] == "CERTIFIED"
