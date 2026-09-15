"""
ModelProvider abstraction.

Every AI backend (Ollama, a future local runtime, a future API) implements
this interface. The rest of HOMELANDER never talks to a specific backend
directly -- only to this interface -- so new providers can be added without
touching the orchestrator, the API routes, or the frontend contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator, Optional


class ProviderStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass
class ModelInfo:
    name: str
    provider: str
    context_size: Optional[int] = None
    size_bytes: Optional[int] = None
    is_installed: bool = True
    status: ProviderStatus = ProviderStatus.OFFLINE
    family: Optional[str] = None
    details: dict = field(default_factory=dict)


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class GenerationChunk:
    """A single streamed piece of a model response."""
    text: str
    done: bool = False
    # populated only on the final chunk, when available
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_duration_ms: Optional[int] = None


class ProviderError(Exception):
    """Raised when a provider cannot fulfill a request.

    `user_message` is safe, friendly text for the UI (per HOMELANDER's
    "never show raw stack traces" rule). `detail` is the technical reason,
    logged server-side only.
    """

    def __init__(self, user_message: str, detail: str = ""):
        super().__init__(detail or user_message)
        self.user_message = user_message
        self.detail = detail or user_message


class ModelProvider(ABC):
    """Base class every model backend must implement."""

    name: str = "base"

    @abstractmethod
    async def health_check(self) -> ProviderStatus:
        """Return whether this provider's backend is reachable right now."""
        raise NotImplementedError

    @abstractmethod
    async def list_models(self) -> list[ModelInfo]:
        """Return models this provider currently has installed/available."""
        raise NotImplementedError

    @abstractmethod
    async def generate(
        self,
        model: str,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[GenerationChunk]:
        """Stream a chat completion. Must raise ProviderError on failure,
        never let a raw exception escape to the API layer."""
        raise NotImplementedError

    async def pull_model(self, model: str) -> AsyncIterator[dict]:
        """Optional: download/install a model. Providers that don't support
        this (e.g. a hosted provider) should just not override it; the base
        implementation raises a clear, typed error."""
        raise ProviderError(
            f"{self.name} does not support installing new models from HOMELANDER.",
        )
        yield {}  # pragma: no cover - keeps this an async generator

    async def delete_model(self, model: str) -> None:
        raise ProviderError(
            f"{self.name} does not support deleting models from HOMELANDER.",
        )
