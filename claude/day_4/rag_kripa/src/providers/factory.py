from __future__ import annotations

import os
from typing import Callable

from llm_config import get_active_provider_settings


def call_openrouter(prompt: str, *, system_prompt: str | None = None) -> str:
    import requests

    settings = get_active_provider_settings()
    if settings.name != "openrouter":
        raise ValueError("OpenRouter is not the active provider.")

    api_key = settings.api_key or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is missing.")

    payload = {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": system_prompt or "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
    }
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://localhost",
            "X-Title": "Edukripa RAG",
        },
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def call_gemini(prompt: str, *, system_prompt: str | None = None) -> str:
    from google import genai

    settings = get_active_provider_settings()
    if settings.name != "gemini":
        raise ValueError("Gemini is not the active provider.")
    if not settings.api_key:
        raise ValueError("GOOGLE_API_KEY is missing.")

    client = genai.Client(api_key=settings.api_key)
    response = client.models.generate_content(
        model=settings.model,
        contents=prompt,
        config={"system_instruction": system_prompt or "You are a helpful assistant."},
    )
    return (getattr(response, "text", None) or "").strip() or str(response)


def call_provider_text(prompt: str, *, system_prompt: str | None = None) -> str:
    settings = get_active_provider_settings()
    if settings.name == "openrouter":
        return call_openrouter(prompt, system_prompt=system_prompt)
    if settings.name == "gemini":
        return call_gemini(prompt, system_prompt=system_prompt)
    raise NotImplementedError(f"Provider '{settings.name}' is not supported by the simple provider wrapper.")


def get_provider_runner() -> Callable[[str], str]:
    return call_provider_text
