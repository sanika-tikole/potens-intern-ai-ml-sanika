from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.config import settings
from app.utils.errors import LLMServiceError

try:  # pragma: no cover - optional dependency fallback
    from groq import Groq
except ImportError:  # pragma: no cover - optional dependency fallback
    Groq = None  # type: ignore[assignment]


DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_TOKENS = 500
DEFAULT_REQUEST_TIMEOUT = 30.0


@dataclass(slots=True)
class LLMResult:
    text: str
    raw: Any | None = None


@lru_cache(maxsize=4)
def _get_client(api_key: str):
    if Groq is None or not api_key:
        return None
    try:
        return Groq(api_key=api_key, timeout=DEFAULT_REQUEST_TIMEOUT)
    except Exception:
        return None


def generate_text(
    prompt: str,
    system_prompt: str | None = None,
    *,
    model: str | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    api_key = settings.groq_api_key
    if not api_key or not prompt.strip():
        return ""

    client = _get_client(api_key)
    if client is None:
        return ""

    model_name = model or getattr(settings, "groq_model_name", DEFAULT_GROQ_MODEL)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=messages,
        )
    except Exception as exc:
        raise LLMServiceError(f"Failed to generate text from Groq: {exc}") from exc

    try:
        return (response.choices[0].message.content or "").strip()
    except Exception as exc:
        raise LLMServiceError(f"Unexpected response format from Groq: {exc}") from exc


class GroqLLMClient:
    """Backward-compatible client wrapper used by the existing service layer."""

    def __init__(self, app_settings=settings) -> None:
        self.settings = app_settings

    @property
    def available(self) -> bool:
        return bool(self.settings.groq_api_key and _get_client(self.settings.groq_api_key) is not None)

    def generate_text(self, prompt: str, system_prompt: str | None = None) -> str:
        return generate_text(prompt, system_prompt=system_prompt)

    def chat(
        self,
        *,
        system: str,
        user: str,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> LLMResult | None:
        text = generate_text(
            user,
            system_prompt=system,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if not text:
            return None
        return LLMResult(text=text)
