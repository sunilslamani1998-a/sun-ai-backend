
import os
from google import genai
from google.genai import types


SYSTEM_INSTRUCTION = """
You are SUN.AI Advanced, with Bittu as the user's personal AI assistant.

Be helpful, accurate, and practical.
Use relevant supplied memories when answering.
Never claim you accessed a video, website, or file unless its
contents were actually provided to you.

For YouTube Shorts:
- Suggest engaging hooks, titles, and caption lines.
- Never invent video timestamps or transcript quotations.
- Treat engagement scores as estimates, not guarantees.
- Never promise viral views or earnings.
- Recommend original or authorized content.
- Never claim a video was rendered or uploaded unless confirmed.
"""


def _make_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing from environment variables."
        )
    return genai.Client(api_key=api_key)


async def ask_ai(prompt: str, memories=None) -> str:
    """Generate a Gemini response using an optional list of memories."""

    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt must be a non-empty string.")

    memory_text = ""

    if memories:
        if isinstance(memories, str):
            memories = [memories]

        if isinstance(memories, (list, tuple)):
            safe_memories = [
                str(item)[:2000]
                for item in memories[:20]
                if item is not None
            ]
            if safe_memories:
                memory_text = (
                    "\n\nRelevant memories:\n"
                    + "\n".join(f"- {item}" for item in safe_memories)
                )
        else:
            memory_text = f"\n\nRelevant memory:\n{str(memories)[:4000]}"

    client = _make_client()

    response = await client.aio.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=prompt.strip() + memory_text,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.5,
            max_output_tokens=4096,
        ),
    )

    answer = getattr(response, "text", None)

    if not answer or not answer.strip():
        raise RuntimeError("Gemini returned an empty response.")

    return answer.strip()
