"""Direct Google ADK Runner smoke test for TRUSTFORGE ZERO.

This bypasses agents-cli so we can prove the core path independently:
Google ADK Runner -> TRUSTFORGE Governor -> Gemini -> final response.
"""

from __future__ import annotations

import asyncio
import os

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from trustforge_zero.agent import root_agent

APP_NAME = "trustforge_zero"
USER_ID = "trustforge-smoke-user"
SESSION_ID = "trustforge-smoke-session"
PROMPT = (
    "Identify yourself as TRUSTFORGE ZERO Governor. List your specialist agents "
    "and state the certification invariant. Do not execute any security test or attack."
)


def _text_from_event(event: object) -> str:
    content = getattr(event, "content", None)
    parts = getattr(content, "parts", None) or []
    texts = [getattr(part, "text", "") for part in parts]
    return "".join(text for text in texts if text).strip()


async def main() -> None:
    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
        raise SystemExit("Missing GEMINI_API_KEY or GOOGLE_API_KEY in the environment.")

    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )

    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    message = types.Content(role="user", parts=[types.Part(text=PROMPT)])

    print("[TRUSTFORGE] ADK Governor smoke test starting...")
    print(f"[TRUSTFORGE] Governor: {root_agent.name}")
    print(f"[TRUSTFORGE] Specialists: {[agent.name for agent in root_agent.sub_agents]}")

    final_text = ""
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=message,
    ):
        text = _text_from_event(event)
        if text:
            final_text = text

    if not final_text:
        raise SystemExit("ADK completed without a textual Governor response.")

    print("\n[TRUSTFORGE] GOVERNOR RESPONSE")
    print(final_text)
    print("\n[TRUSTFORGE] ADK_GOVERNOR_ONLINE")


if __name__ == "__main__":
    asyncio.run(main())
