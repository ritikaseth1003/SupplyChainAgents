"""
OpenAI GPT-4 client wrapper with chain-of-thought reasoning support.
Uses the OPENAI_API_KEY environment variable for authentication.
"""

import os
import json
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Singleton async client
# ---------------------------------------------------------------------------
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY not set. Export it or add it to a .env file."
            )
        _client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )
    return _client


async def ask_gpt(
    system_prompt: str,
    user_prompt: str,
    model: str = "llama-3.3-70b-versatile",
    temperature: float = 0.4,
    max_tokens: int = 1024,
) -> str:
    """
    Send a prompt to GPT-4 with chain-of-thought reasoning instructions
    baked into the system prompt. Returns the assistant's reply text.
    """
    cot_system = (
        f"{system_prompt}\n\n"
        "Always reason step-by-step before giving your final answer. "
        "Show your reasoning chain clearly, then provide your conclusion "
        "after a line that says 'CONCLUSION:'."
    )

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": cot_system},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        # Graceful fallback so the simulation keeps running without an API key
        return (
            f"[LLM unavailable – fallback reasoning] "
            f"Error: {exc}. Using heuristic logic instead."
        )
