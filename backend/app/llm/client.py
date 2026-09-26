"""LiteLLM call via OpenRouter with Cerebras as the inference provider."""

from __future__ import annotations

import asyncio

from litellm import completion

from .schemas import LLMResponse

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}


def _call_llm_sync(messages: list[dict]) -> LLMResponse:
    response = completion(
        model=MODEL,
        messages=messages,
        response_format=LLMResponse,
        reasoning_effort="low",
        extra_body=EXTRA_BODY,
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("Empty response from LLM")
    return LLMResponse.model_validate_json(content)


async def call_llm(messages: list[dict]) -> LLMResponse:
    """Call the LLM and parse its structured output. Raises on network/parse errors."""
    return await asyncio.to_thread(_call_llm_sync, messages)
