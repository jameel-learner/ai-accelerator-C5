from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ProviderSpec:
    name: str
    model: str
    enabled: bool
    api_key_name: str
    runner: Callable[..., str]


PROVIDERS: dict[str, ProviderSpec] = {}


def register_provider(spec: ProviderSpec) -> None:
    PROVIDERS[spec.name] = spec


def get_provider_spec(name: str) -> ProviderSpec | None:
    return PROVIDERS.get(name)


def list_provider_names() -> list[str]:
    return list(PROVIDERS.keys())
