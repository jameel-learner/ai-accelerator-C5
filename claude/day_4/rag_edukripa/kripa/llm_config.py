import os
from dataclasses import dataclass
from typing import Optional, Literal

ProviderName = Literal["groq", "claude", "huggingface", "gemini", "openrouter"]


def _as_bool(raw: Optional[str], default: bool = False) -> bool:
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class LLMSettings:
    name: ProviderName
    enabled: bool
    model: str
    api_key: Optional[str] = None


def _provider_order() -> list[ProviderName]:
    return ["openrouter", "gemini", "huggingface", "groq", "claude"]


def get_active_provider_settings() -> LLMSettings:
    legacy_provider = (os.environ.get("LLM_PROVIDER") or "").strip().lower()
    raw_active_provider = (os.environ.get("ACTIVE_PROVIDER") or "").strip().lower()

    if raw_active_provider in {"groq", "claude", "huggingface", "gemini", "openrouter"}:
        provider = raw_active_provider
    elif legacy_provider in {"groq", "claude", "huggingface", "gemini", "openrouter"}:
        provider = legacy_provider
    else:
        provider = "gemini"

    if provider == "openrouter":
        return LLMSettings(
            name="openrouter",
            enabled=_as_bool(os.environ.get("OPENROUTER_ENABLED"), default=True),
            model=os.environ.get("OPENROUTER_MODEL") or "openai/gpt-oss-20b:free",
            api_key=os.environ.get("OPENROUTER_API_KEY"),
        )

    if provider == "gemini":
        return LLMSettings(
            name="gemini",
            enabled=_as_bool(os.environ.get("GEMINI_ENABLED"), default=True),
            model=os.environ.get("GEMINI_MODEL") or "gemini-flash-latest",
            api_key=os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"),
        )

    if provider == "huggingface":
        return LLMSettings(
            name="huggingface",
            enabled=_as_bool(os.environ.get("HUGGINGFACE_ENABLED"), default=False),
            model=os.environ.get("HUGGINGFACE_MODEL") or "Qwen/Qwen2.5-3B-Instruct",
            api_key=os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY") or os.environ.get("HUGGINGFACEHUB_API_TOKEN"),
        )

    if provider == "groq":
        return LLMSettings(
            name="groq",
            enabled=_as_bool(os.environ.get("GROQ_ENABLED"), default=True),
            model=os.environ.get("GROQ_MODEL") or "llama-3.3-70b-versatile",
            api_key=os.environ.get("GROQ_API_KEY"),
        )

    return LLMSettings(
        name="claude",
        enabled=_as_bool(os.environ.get("CLAUDE_ENABLED"), default=True),
        model=os.environ.get("CLAUDE_MODEL") or "claude-sonnet-4-6",
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
    )


def build_provider_options() -> list[tuple[str, str]]:
    options = [
        ("openrouter", "OpenRouter"),
        ("gemini", "Google Gemini"),
        ("huggingface", "Hugging Face"),
        ("groq", "Groq"),
        ("claude", "Claude"),
    ]
    return options


def get_model_choices_for_provider(provider: str) -> list[str]:
    provider = (provider or "gemini").lower()
    if provider == "openrouter":
        return [
            "openai/gpt-oss-20b",
            "google/gemma-4-26b-a4b-it:free",
            "google/gemma-4-31b-it:free",
            "nvidia/nemotron-nano-12b-v2-vl:free",
            "nvidia/nemotron-3-ultra-550b-a55b:free",
        ]
    if provider == "gemini":
        return [
            "gemini-flash-latest",
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
        ]
    if provider == "huggingface":
        return [
            "Qwen/Qwen2.5-3B-Instruct",
            "Qwen/Qwen2.5-7B-Instruct",
        ]
    if provider == "groq":
        return ["llama-3.3-70b-versatile"]
    if provider == "claude":
        return ["claude-sonnet-4-6"]
    return []


def get_model_list_for_active_provider() -> list[str]:
    settings = get_active_provider_settings()
    return get_model_choices_for_provider(settings.name)
