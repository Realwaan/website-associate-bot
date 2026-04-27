"""NVIDIA NIM AI Client — OpenAI-compatible SDK edition."""
from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import Any

try:
    from openai import OpenAI, APIStatusError, APIConnectionError, APITimeoutError
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

logger = logging.getLogger(__name__)


class AIClientError(Exception):
    """Raised when the AI provider request fails or returns invalid data."""


@dataclass
class AIProfile:
    """Configuration for one AI use-case profile."""
    api_key: str | None
    model: str | None
    base_url: str
    timeout_seconds: int
    # Extra body params forwarded verbatim to the SDK (e.g. reasoning_budget)
    extra_body: dict[str, Any] = field(default_factory=dict)

    def is_configured(self) -> bool:
        return bool(self.api_key and self.model)

    def safe_status(self) -> dict[str, Any]:
        return {
            "configured": self.is_configured(),
            "has_api_key": bool(self.api_key),
            "model": self.model,
            "invoke_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }


class NvidiaAIClient:
    """
    NVIDIA Inference Microservices (NIM) Client.
    Uses the OpenAI-compatible SDK.

    Profile priority (per env key):
        AI_<PROFILE>_*  →  NVIDIA_*  (legacy fallback)

    Profiles
    --------
    answer    /ask-ai command  — llama-3.3-nemotron-super-49b (thinking)
    code      reserved         — same key as answer by default
    scan_docs /scan-pdf        — nemotron-3-nano-30b (thinking, reasoning_budget)
    rag       reserved         — same key as answer by default
    """

    PROFILE_PREFIXES = {
        "scan_docs": "AI_SCAN_DOCS",
        "code":      "AI_CODE",
        "answer":    "AI_ANSWER",
        "rag":       "AI_RAG",
    }

    _DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"

    # extra_body applied automatically for profiles whose model supports
    # the NVIDIA reasoning_budget / enable_thinking extension.
    _THINKING_EXTRA_BODY: dict[str, Any] = {
        "reasoning_budget": 16384,
        "chat_template_kwargs": {"enable_thinking": True},
    }

    def __init__(self) -> None:
        if not _OPENAI_AVAILABLE:
            raise AIClientError(
                "The 'openai' package is required. Run: pip install openai>=1.30.0"
            )
        self.default_profile = "answer"
        self.active_profile = "answer"
        self._load_from_env()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_from_env(self) -> None:
        if load_dotenv is not None:
            load_dotenv(override=True)
        self.default_profile = (
            os.getenv("AI_DEFAULT_PROFILE", self.default_profile).strip().lower()
            or self.default_profile
        )
        self.active_profile = self.default_profile

    def _get_profile(self, profile_name: str) -> AIProfile:
        prefix = self.PROFILE_PREFIXES.get(profile_name, self.PROFILE_PREFIXES["answer"])

        api_key  = os.getenv(f"{prefix}_API_KEY") or os.getenv("NVIDIA_API_KEY") or ""
        model    = os.getenv(f"{prefix}_MODEL")   or os.getenv("NVIDIA_MODEL")
        base_url = (
            os.getenv(f"{prefix}_INVOKE_URL")
            or os.getenv("NVIDIA_INVOKE_URL")
            or self._DEFAULT_BASE_URL
        )
        timeout  = int(
            os.getenv(f"{prefix}_TIMEOUT_SECONDS")
            or os.getenv("NVIDIA_TIMEOUT_SECONDS")
            or 60
        )

        # Strip any accidental "Bearer " prefix stored in the env value
        token = api_key.strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()

        # The OpenAI SDK automatically appends /chat/completions to base_url.
        # Strip it here if someone stored the full URL in their env so we don't
        # end up with .../v1/chat/completions/chat/completions → 404.
        clean_url = base_url.rstrip("/")
        if clean_url.endswith("/chat/completions"):
            clean_url = clean_url[: -len("/chat/completions")]

        # scan_docs uses nemotron-nano which requires reasoning_budget.
        # answer/code/rag use nemotron-super which also supports thinking
        # but we leave extra_body empty so callers can opt in via enable_thinking.
        extra_body: dict[str, Any] = {}
        if profile_name == "scan_docs":
            extra_body = dict(self._THINKING_EXTRA_BODY)

        return AIProfile(
            api_key=token or None,
            model=model,
            base_url=clean_url,
            timeout_seconds=timeout,
            extra_body=extra_body,
        )

    def _make_client(self, profile: AIProfile) -> "OpenAI":
        return OpenAI(
            base_url=profile.base_url,
            api_key=profile.api_key,
            timeout=profile.timeout_seconds,
        )

    @property
    def model(self) -> str | None:
        """Backwards-compatible property used by the startup log in main.py."""
        return self._get_profile(self.active_profile).model

    @property
    def invoke_url(self) -> str:
        """Backwards-compatible property used by the startup log in main.py."""
        return self._get_profile(self.active_profile).base_url

    @property
    def timeout_seconds(self) -> int:
        """Backwards-compatible property used by the startup log in main.py."""
        return self._get_profile(self.active_profile).timeout_seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_configured(self, profile: str | None = None) -> bool:
        self._load_from_env()
        return self._get_profile(profile or self.active_profile).is_configured()

    def get_status(self, profile: str | None = None) -> dict[str, Any]:
        self._load_from_env()
        p = profile or self.active_profile
        return self._get_profile(p).safe_status() | {"active_profile": p}

    def chat(
        self,
        prompt: str,
        profile: str | None = None,
        *,
        system: str | None = None,
        temperature: float = 0.6,
        top_p: float = 0.95,
        max_tokens: int = 4096,
        enable_thinking: bool | None = None,
        # absorb any legacy/future kwargs passed by callers
        **_kwargs: Any,
    ) -> str:
        """
        Send a text prompt and return the assistant's reply.

        Parameters
        ----------
        enable_thinking:
            None  — use the profile default (on for scan_docs, off for others)
            True  — force reasoning_budget extra_body on
            False — strip reasoning_budget extra_body (useful for JSON-output prompts)
        """
        self._load_from_env()
        pname = profile or self.active_profile
        prof = self._get_profile(pname)

        if not prof.is_configured():
            raise AIClientError(
                f"Profile '{pname}' is not configured. "
                "Check NVIDIA_API_KEY and NVIDIA_MODEL in .env."
            )

        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # Resolve extra_body — caller can override the profile default
        extra_body = dict(prof.extra_body)
        if enable_thinking is False:
            # Caller explicitly wants no thinking (e.g. JSON-only prompts)
            extra_body.pop("reasoning_budget", None)
            extra_body.pop("chat_template_kwargs", None)
        elif enable_thinking is True and not extra_body:
            extra_body = dict(self._THINKING_EXTRA_BODY)

        client = self._make_client(prof)

        try:
            create_kwargs: dict[str, Any] = dict(
                model=prof.model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stream=False,
            )
            if extra_body:
                create_kwargs["extra_body"] = extra_body

            response = client.chat.completions.create(**create_kwargs)

        except APIStatusError as e:
            logger.error(
                "NVIDIA API status error: %s %s | model=%s base_url=%s",
                e.status_code, e.message, prof.model, prof.base_url,
            )
            raise AIClientError(
                f"AI API error {e.status_code} (model={prof.model} url={prof.base_url}): {e.message}"
            ) from e
        except (APIConnectionError, APITimeoutError) as e:
            logger.error("NVIDIA API connection/timeout: %s", e)
            raise AIClientError(f"AI connection error: {e}") from e
        except Exception as e:
            logger.error("Unexpected AI error: %s", e)
            raise AIClientError(f"AI request failed: {e}") from e

        return self._extract_text(response, pname)

    def scan_image(
        self,
        image_url: str,
        prompt: str = "Describe this document in detail.",
        profile: str = "scan_docs",
    ) -> str:
        """Send a multimodal (image + text) request. Uses the scan_docs profile by default."""
        self._load_from_env()
        prof = self._get_profile(profile)

        if not prof.is_configured():
            raise AIClientError(f"Profile '{profile}' is not configured.")

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ]

        client = self._make_client(prof)

        try:
            create_kwargs: dict[str, Any] = dict(
                model=prof.model,
                messages=messages,
                max_tokens=4096,
                stream=False,
            )
            if prof.extra_body:
                create_kwargs["extra_body"] = prof.extra_body

            response = client.chat.completions.create(**create_kwargs)

        except APIStatusError as e:
            raise AIClientError(f"AI API error {e.status_code}: {e.message}") from e
        except Exception as e:
            raise AIClientError(f"AI request failed: {e}") from e

        return self._extract_text(response, profile)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_text(self, response: Any, profile: str) -> str:
        """
        Pull the final answer from a completion response.

        Thinking models surface the chain-of-thought in `reasoning_content`
        and the polished answer in `content`. We prefer `content`; if it is
        empty (can happen on very short prompts with thinking models) we fall
        back to the reasoning trace so the caller always receives something.
        """
        choices = getattr(response, "choices", None) or []
        if not choices:
            raise AIClientError("AI returned no choices.")

        message = choices[0].message
        content  = (message.content or "").strip()
        reasoning = (getattr(message, "reasoning_content", None) or "").strip()

        if reasoning:
            logger.debug(
                "[%s] reasoning_content (%d chars): %.300s…",
                profile, len(reasoning), reasoning,
            )

        result = content or reasoning
        if not result:
            raise AIClientError("AI returned an empty response.")

        return result