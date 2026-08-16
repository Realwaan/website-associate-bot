"""Unified AI Service supporting Google Gemini Free Tier and OpenAI/NVIDIA fallbacks."""
import os
import json
import logging
import requests
from typing import Optional, Dict, Any
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

class AIService:
    """Handles AI text generation and document reasoning with zero-cost Gemini support."""

    def __init__(self, api_key: Optional[str] = None):
        self.gemini_key = api_key or GEMINI_API_KEY
        self._openai_client = None
        self._init_openai_fallback()

    def _init_openai_fallback(self):
        openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("NVIDIA_API_KEY")
        if openai_key:
            try:
                from openai import OpenAI
                base_url = os.getenv("AI_BASE_URL", "https://integrate.api.nvidia.com/v1" if os.getenv("NVIDIA_API_KEY") else None)
                if base_url:
                    self._openai_client = OpenAI(api_key=openai_key, base_url=base_url)
                else:
                    self._openai_client = OpenAI(api_key=openai_key)
            except Exception as e:
                logger.warning(f"OpenAI fallback initialization failed: {e}")

    def is_configured(self) -> bool:
        return bool(self.gemini_key or self._openai_client)

    def generate_text(self, prompt: str, system_prompt: str = "You are an expert software architect and technical project manager.", temperature: float = 0.4) -> str:
        """Generates text using Google Gemini 1.5 Flash (Free), falling back to OpenAI/NVIDIA."""
        # 1. Primary: Google Gemini 1.5 Flash Free Tier
        if self.gemini_key and not self.gemini_key.startswith("your-"):
            try:
                url = f"{GEMINI_API_URL}?key={self.gemini_key}"
                payload = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": f"{system_prompt}\n\n{prompt}"}]
                        }
                    ],
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": 4096,
                    }
                }
                res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
                if res.ok:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
                else:
                    logger.warning(f"Gemini API returned error {res.status_code}: {res.text}")
            except Exception as e:
                logger.warning(f"Gemini API call failed: {e}")

        # 2. Fallback: OpenAI / NVIDIA NIM
        if self._openai_client:
            try:
                model = os.getenv("AI_MODEL", "gpt-4o-mini" if "api.openai.com" in getattr(self._openai_client, "base_url", "") else "meta/llama-3.3-70b-instruct")
                resp = self._openai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature
                )
                if resp.choices:
                    return resp.choices[0].message.content or ""
            except Exception as e:
                logger.error(f"OpenAI fallback failed: {e}")

        # 3. Offline Heuristic Fallback
        return self._heuristic_fallback(prompt)

    def _heuristic_fallback(self, prompt: str) -> str:
        """Provides a structured heuristic response if AI APIs are offline."""
        return (
            "### AI Analysis (Offline Heuristic Mode)\n\n"
            "1. **Core Problem**: Codebase modernization and ticket lifecycle tracking.\n"
            "2. **Recommended Action**: Review acceptance criteria and assign developers.\n"
            "3. **Milestone Target**: 12-week development cycle with iterative reviews."
        )

    def analyze_pdf_brief(self, brief_text: str) -> Dict[str, Any]:
        """Analyzes a project specification brief PDF text into design tokens and roadmap items."""
        prompt = (
            "Analyze this project brief and return a clean JSON object with the following structure:\n"
            "{\n"
            '  "projectTitle": string,\n'
            '  "designSystem": { "primaryColor": string, "secondaryColor": string, "fonts": string[] },\n'
            '  "coreFeatures": string[],\n'
            '  "phases": [{ "phaseNumber": int, "title": string, "deliverables": string[] }]\n'
            "}\n\n"
            f"Brief Content:\n{brief_text[:12000]}"
        )
        resp = self.generate_text(prompt, system_prompt="You are a senior technical analyst. Respond ONLY in valid JSON.")
        try:
            cleaned = resp.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned.strip())
        except Exception:
            return {
                "projectTitle": "Analyzed Project",
                "designSystem": {"primaryColor": "#38bdf8", "secondaryColor": "#818cf8", "fonts": ["Inter", "sans-serif"]},
                "coreFeatures": ["Core Authentication", "Data Pipeline", "Dashboard UI"],
                "phases": [
                    {"phaseNumber": 1, "title": "System Architecture", "deliverables": ["Data Schema", "API Contracts"]},
                    {"phaseNumber": 2, "title": "Core Implementation", "deliverables": ["Frontend Dashboard", "Backend APIs"]}
                ]
            }

# Singleton instance
ai_service = AIService()
