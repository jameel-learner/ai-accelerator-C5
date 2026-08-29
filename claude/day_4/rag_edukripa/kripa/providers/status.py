from __future__ import annotations

from typing import Any

from llm_config import get_active_provider_settings


def get_provider_status() -> dict[str, Any]:
    settings = get_active_provider_settings()
    return {
        "provider": settings.name,
        "enabled": settings.enabled,
        "model": settings.model,
        "api_key_present": bool(settings.api_key),
    }
