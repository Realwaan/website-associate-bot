"""Minimal NVIDIA chat-completions client for Discord bot commands."""
import os
from typing import Any

import requests

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional fallback
    load_dotenv = None


class AIClientError(Exception):
    """Raised when the AI provider request fails or returns invalid data."""


class NvidiaAIClient:
    """Simple wrapper for NVIDIA integrate chat/completions endpoint."""

    def __init__(self):
        self._load_from_env()

    def _load_from_env(self) -> None:
        """Load latest provider config from process/.env environment."""
        if load_dotenv is not None:
            # Pick up changes when users update .env while bot is running.
            load_dotenv(override=True)
        self.invoke_url = os.getenv("NVIDIA_INVOKE_URL", "https://integrate.api.nvidia.com/v1/chat/completions")
        self.api_key = self._normalize_api_key(os.getenv("NVIDIA_API_KEY"))
        self.model = os.getenv("NVIDIA_MODEL", "google/gemma-4-31b-it")
        self.timeout_seconds = int(os.getenv("NVIDIA_TIMEOUT_SECONDS", "45"))

    @staticmethod
    def _normalize_api_key(value: str | None) -> str | None:
        """Accept raw key or 'Bearer <key>' format and return only the token."""
        if not value:
            return value

        token = value.strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        return token

    def is_configured(self) -> bool:
        """Return whether required NVIDIA credentials are available."""
        self._load_from_env()
        return bool(self.api_key and self.invoke_url and self.model)

    def _extract_text(self, data: dict[str, Any]) -> str:
        """Extract model text from OpenAI-compatible response shape."""
        choices = data.get("choices") or []
        if not choices:
            raise AIClientError("No choices returned by AI provider.")

        message = (choices[0] or {}).get("message") or {}
        content = message.get("content")

        if isinstance(content, str) and content.strip():
            return content.strip()

        if isinstance(content, list):
            # Some providers return content chunks like [{"type":"text","text":"..."}]
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(str(part.get("text", "")))
            merged = "".join(text_parts).strip()
            if merged:
                return merged

        raise AIClientError("AI response did not contain text content.")

    def chat(
        self,
        prompt: str,
        *,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.95,
        enable_thinking: bool = True,
    ) -> str:
        """Send a user prompt and return generated text."""
        self._load_from_env()
        if not self.is_configured():
            raise AIClientError("NVIDIA AI is not configured. Set NVIDIA_API_KEY, NVIDIA_MODEL, and NVIDIA_INVOKE_URL.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": max(0.0, min(temperature, 2.0)),
            "top_p": max(0.0, min(top_p, 1.0)),
            "stream": False,
            "chat_template_kwargs": {"enable_thinking": enable_thinking},
        }

        try:
            response = requests.post(
                self.invoke_url,
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as e:
            raise AIClientError(f"Request failed: {e}") from e

        if response.status_code >= 400:
            body = response.text.strip()
            short = body[:300] + ("..." if len(body) > 300 else "")
            raise AIClientError(f"Provider error ({response.status_code}): {short}")

        try:
            data = response.json()
        except ValueError as e:
            raise AIClientError("Provider response was not valid JSON.") from e

        return self._extract_text(data)
