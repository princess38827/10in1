"""Thin async wrapper around the Anthropic Messages API.

Every agent (overseer, worker, synthesizer) shares one client instance so
we get shared connection pooling and consistent retry/backoff behavior.
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Optional

import httpx

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = os.environ.get("SWARM_MODEL", "claude-sonnet-5")


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        max_retries: int = 3,
        timeout: float = 90.0,
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise LLMError(
                "No API key found. Set ANTHROPIC_API_KEY in your environment, "
                "e.g.: export ANTHROPIC_API_KEY=sk-ant-..."
            )
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)
        self._semaphore = asyncio.Semaphore(6)  # cap concurrent in-flight requests

    async def aclose(self) -> None:
        await self._client.aclose()

    async def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 1500,
        temperature: float = 0.4,
    ) -> str:
        """Send one message, return the text of Claude's reply."""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }

        last_err: Optional[Exception] = None
        async with self._semaphore:
            for attempt in range(self.max_retries):
                try:
                    resp = await self._client.post(
                        ANTHROPIC_API_URL, headers=headers, json=payload
                    )
                    if resp.status_code == 429 or resp.status_code >= 500:
                        raise LLMError(f"retryable status {resp.status_code}: {resp.text[:200]}")
                    resp.raise_for_status()
                    data = resp.json()
                    text_blocks = [
                        b["text"] for b in data.get("content", []) if b.get("type") == "text"
                    ]
                    return "\n".join(text_blocks).strip()
                except Exception as e:  # noqa: BLE001
                    last_err = e
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(1.5 * (2**attempt))
                    continue
        raise LLMError(f"LLM call failed after {self.max_retries} attempts: {last_err}")

    async def complete_json(
        self, system: str, user: str, max_tokens: int = 1500, temperature: float = 0.4
    ) -> Any:
        """Like complete(), but strips code fences and parses JSON."""
        raw = await self.complete(system, user, max_tokens=max_tokens, temperature=temperature)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Drop opening fence (```json or ```) and closing fence (```)
            start = 1
            if lines[0].startswith("```json"):
                start = 1
            end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
            cleaned = "\n".join(lines[start:end]).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise LLMError(f"Failed to parse JSON from model output: {e}\nRaw: {raw[:500]}")
