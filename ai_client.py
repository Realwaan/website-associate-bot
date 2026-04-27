"""NVIDIA NIM Multimodal Client for Discord - 2026 Production Edition."""
from __future__ import annotations

import os
import base64
import requests
import logging
from dataclasses import dataclass
from typing import Any

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

logger = logging.getLogger(__name__)

class AIClientError(Exception):
    """Raised when the AI provider request fails or returns invalid data."""

@dataclass
class AIProfile:
    """Configuration for one AI use case."""
    api_key: str | None
    model: str | None
    invoke_url: str | None
    timeout_seconds: int

    def is_configured(self) -> bool:
        return bool(self.api_key and self.model and self.invoke_url)

    def safe_status(self) -> dict[str, Any]:
        return {
            "configured": self.is_configured(),
            "has_api_key": bool(self.api_key),
            "model": self.model,
            "invoke_url": self.invoke_url,
            "timeout_seconds": self.timeout_seconds,
        }

class NvidiaAIClient:
    """
    NVIDIA Inference Microservices (NIM) Client.
    Supports Text-based Coding and Vision-based Image Scanning.
    """

    PROFILE_PREFIXES = {
        "scan_docs": "AI_SCAN_DOCS",
        "code": "AI_CODE",
        "answer": "AI_ANSWER",
        "rag": "AI_RAG",
    }

    def __init__(self):
        self.default_profile = os.getenv("AI_DEFAULT_PROFILE", "answer").strip().lower() or "answer"
        self.active_profile = self.default_profile
        # Default endpoint for most NIM models
        self.invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self.api_key: str | None = None
        self.model: str | None = None
        self.timeout_seconds = 45
        self._load_from_env()

    def _load_from_env(self) -> None:
        """Reload variables from environment or Render secret store."""
        if load_dotenv is not None:
            load_dotenv(override=True)

        self.default_profile = os.getenv("AI_DEFAULT_PROFILE", self.default_profile).strip().lower() or self.default_profile
        self.active_profile = self.default_profile
        profile = self._get_profile(self.default_profile)
        self._apply_profile(profile)

    def _get_profile(self, profile_name: str) -> AIProfile:
        prefix = self.PROFILE_PREFIXES.get(profile_name, self.PROFILE_PREFIXES["answer"])
        
        api_key = os.getenv(f"{prefix}_API_KEY") or os.getenv("NVIDIA_API_KEY")
        model = os.getenv(f"{prefix}_MODEL") or os.getenv("NVIDIA_MODEL")
        invoke_url = os.getenv(f"{prefix}_INVOKE_URL") or os.getenv("NVIDIA_INVOKE_URL") or self.invoke_url
        
        timeout_seconds = int(os.getenv(f"{prefix}_TIMEOUT_SECONDS") or os.getenv("NVIDIA_TIMEOUT_SECONDS") or 45)

        return AIProfile(
            api_key=self._normalize_api_key(api_key),
            model=model,
            invoke_url=invoke_url,
            timeout_seconds=timeout_seconds,
        )

    def _normalize_api_key(self, value: str | None) -> str | None:
        if not value: return value
        token = value.strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        return token

    def _apply_profile(self, profile: AIProfile) -> None:
        self.api_key = profile.api_key
        self.model = profile.model
        self.invoke_url = profile.invoke_url or self.invoke_url
        self.timeout_seconds = profile.timeout_seconds

    def set_profile(self, profile_name: str) -> None:
        """Activate a specific profile (e.g., 'code' or 'scan_docs')."""
        self._load_from_env()
        self.active_profile = profile_name if profile_name in self.PROFILE_PREFIXES else self.default_profile
        self._apply_profile(self._get_profile(self.active_profile))

    def is_configured(self, profile: str | None = None) -> bool:
        if profile:
            return self._get_profile(profile).is_configured()
        return bool(self.api_key and self.model)

    def chat(self, prompt: str, profile: str | None = None, **kwargs) -> str:
        """Main entry point for text and coding prompts."""
        content = [{"role": "user", "content": prompt}]
        return self._request(content, profile=profile, **kwargs)

    def scan_image(self, image_url: str, prompt: str = "Scan this image.", profile: str = "scan_docs") -> str:
        """
        Specialized multimodal request. 
        Uses AI_SCAN_DOCS profile by default.
        """
        content = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        ]
        return self._request(content, profile=profile)

    def _request(self, messages: list[dict], profile: str | None = None, **kwargs) -> str:
        """Internal handler for REST calls to NVIDIA."""
        self._load_from_env()
        if profile:
            self.set_profile(profile)

        if not self.is_configured():
            raise AIClientError(f"Profile '{self.active_profile}' is not configured.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 2048),
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 0.95),
            "stream": False,
        }

        try:
            response = requests.post(
                self.invoke_url,
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            return self._extract_text(data)
        except Exception as e:
            logger.error(f"NVIDIA API Error: {e}")
            raise AIClientError(f"AI Request failed: {str(e)}")

    def _extract_text(self, data: dict[str, Any]) -> str:
        choices = data.get("choices") or []
        if not choices:
            raise AIClientError("AI returned no results.")
        return choices[0].get("message", {}).get("content", "").strip()

    def get_status(self, profile: str | None = None) -> dict[str, Any]:
        self._load_from_env()
        p = profile or self.active_profile
        return self._get_profile(p).safe_status() | {"active_profile": p}