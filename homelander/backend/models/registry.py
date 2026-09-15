"""
Provider registry.

Central, single place where HOMELANDER knows which ModelProviders exist.
Adding a new backend later (a future local runtime, etc.) means writing one
class that implements ModelProvider and registering it here -- nothing else
in the app needs to change.
"""

from __future__ import annotations

from backend.core.config import settings
from backend.models.base_provider import ModelProvider
from backend.models.ollama_provider import OllamaProvider


class ProviderRegistry:
    def __init__(self):
        self._providers: dict[str, ModelProvider] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(OllamaProvider(base_url=settings.OLLAMA_BASE_URL))
        # Future providers (LocalProvider running e.g. llama.cpp directly,
        # or any additional backend) get added here with one line:
        # self.register(LocalProvider(...))

    def register(self, provider: ModelProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> ModelProvider:
        try:
            return self._providers[name]
        except KeyError as exc:
            raise ValueError(f"Unknown model provider: {name}") from exc

    def all(self) -> list[ModelProvider]:
        return list(self._providers.values())

    def default(self) -> ModelProvider:
        return self._providers[settings.DEFAULT_PROVIDER]


registry = ProviderRegistry()
