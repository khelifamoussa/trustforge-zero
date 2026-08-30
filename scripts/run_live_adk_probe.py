"""Run a real TRUSTFORGE ZERO Google ADK + Gemini orchestration proof."""

import json

from trustforge_zero.live_adk import run_live_governor_probe_sync


if __name__ == "__main__":
    evidence = run_live_governor_probe_sync()
    print("[TRUSTFORGE] LIVE_ADK_PROBE_COMPLETE")
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
