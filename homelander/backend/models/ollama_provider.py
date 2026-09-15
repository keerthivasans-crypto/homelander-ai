"""
OllamaProvider

Talks to a locally running Ollama daemon (default http://localhost:11434).
This is the primary, real, working provider for HOMELANDER. No API key,
no cloud call, no mock data -- if Ollama isn't running, we report that
honestly instead of pretending to generate a response.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Optional

import httpx

from backend.models.base_provider import (
    ChatMessage,
    GenerationChunk,
    ModelInfo,
    ModelProvider,
    ProviderError,
    ProviderStatus,
)

logger = logging.getLogger("homelander.ollama")


class OllamaProvider(ModelProvider):
    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def health_check(self) -> ProviderStatus:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/version")
                if resp.status_code == 200:
                    return ProviderStatus.ONLINE
                return ProviderStatus.ERROR
        except (httpx.ConnectError, httpx.TimeoutException):
            return ProviderStatus.OFFLINE
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ollama health check failed: %s", exc)
            return ProviderStatus.ERROR

    async def list_models(self) -> list[ModelInfo]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
        except (httpx.ConnectError, httpx.TimeoutException):
            # Offline is not an error state for listing -- just no models.
            return []
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ollama list_models failed: %s", exc)
            return []

        models = []
        for m in data.get("models", []):
            details = m.get("details", {}) or {}
            models.append(
                ModelInfo(
                    name=m.get("name") or m.get("model", "unknown"),
                    provider=self.name,
                    context_size=None,  # Ollama /api/tags doesn't expose this; see /api/show
                    size_bytes=m.get("size"),
                    is_installed=True,
                    status=ProviderStatus.ONLINE,
                    family=details.get("family"),
                    details=details,
                )
            )
        return models

    async def model_context_size(self, model: str) -> Optional[int]:
        """Fetch context length via /api/show (best-effort)."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(f"{self.base_url}/api/show", json={"name": model})
                resp.raise_for_status()
                data = resp.json()
                params = data.get("parameters", "") or ""
                for line in params.splitlines():
                    if line.strip().startswith("num_ctx"):
                        parts = line.split()
                        if len(parts) >= 2 and parts[1].isdigit():
                            return int(parts[1])
        except Exception:  # noqa: BLE001
            pass
        return None

    async def generate(
        self,
        model: str,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[GenerationChunk]:
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "options": {"temperature": temperature},
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST", f"{self.base_url}/api/chat", json=payload
                ) as resp:
                    if resp.status_code == 404:
                        raise ProviderError(
                            f"The model '{model}' is not installed. "
                            f"Run: ollama pull {model}",
                            detail=f"Ollama 404 for model {model}",
                        )
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        msg = obj.get("message", {}) or {}
                        text = msg.get("content", "")
                        done = obj.get("done", False)
                        yield GenerationChunk(
                            text=text,
                            done=done,
                            prompt_tokens=obj.get("prompt_eval_count") if done else None,
                            completion_tokens=obj.get("eval_count") if done else None,
                            total_duration_ms=(
                                round(obj["total_duration"] / 1_000_000)
                                if done and "total_duration" in obj
                                else None
                            ),
                        )
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise ProviderError(
                "HOMELANDER cannot connect to the local AI engine. "
                "Please start Ollama and try again.",
                detail=str(exc),
            ) from exc
        except ProviderError:
            raise
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                "The local AI engine returned an error while generating a response.",
                detail=str(exc),
            ) from exc

    async def pull_model(self, model: str) -> AsyncIterator[dict]:
        payload = {"name": model, "stream": True}
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST", f"{self.base_url}/api/pull", json=payload
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            continue
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise ProviderError(
                "HOMELANDER cannot connect to the local AI engine. "
                "Please start Ollama and try again.",
                detail=str(exc),
            ) from exc

    async def delete_model(self, model: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.request(
                    "DELETE", f"{self.base_url}/api/delete", json={"name": model}
                )
                if resp.status_code not in (200, 404):
                    resp.raise_for_status()
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise ProviderError(
                "HOMELANDER cannot connect to the local AI engine. "
                "Please start Ollama and try again.",
                detail=str(exc),
            ) from exc
