import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    text: str
    raw: Dict[str, Any]


class OpenAIClient:
    """Minimal OpenAI chat client for hackathon usage.

    Env:
    - OPENAI_API_KEY (optional in mock mode)
    - OPENAI_MODEL (optional; default: gpt-4o-mini)
    - USE_MOCK_LLM (optional; set to "true" to use mock responses)

    Strict behavior: raise on any API error (unless in mock mode).
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.use_mock = os.getenv("USE_MOCK_LLM", "false").lower() == "true"

        if not self.use_mock and not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set (or set USE_MOCK_LLM=true for testing)")

        if not self.use_mock:
            self.client = OpenAI(api_key=self.api_key)
        else:
            logger.info("Using MOCK LLM mode - no API calls will be made")

    def generate_response(self, prompt: str, temperature: float = 0.2, max_tokens: int = 200) -> LLMResponse:
        if self.use_mock:
            return self._generate_mock_response(prompt)

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": "You are a secure dependency remediation AI."},
                    {"role": "user", "content": prompt},
                ],
            )
        except Exception as exc:
            logger.exception("OpenAI API call failed")
            raise

        text = (resp.choices[0].message.content or "").strip() if resp.choices else ""
        raw: Dict[str, Any] = resp.model_dump()  # type: ignore[no-any-return]
        return LLMResponse(text=text, raw=raw)

    def _generate_mock_response(self, prompt: str) -> LLMResponse:
        """Generate mock responses for testing without API key."""
        logger.info("[MOCK] Generating mock LLM response")
        
        # Check if this is an axios vulnerability
        if "axios" in prompt.lower():
            text = """Based on the vulnerability analysis, I recommend upgrading axios to version 1.6.0 or later.

The vulnerability CVE-2023-45857 in axios 0.21.1 allows for SSRF attacks through improper handling of URLs.
Upgrading to axios@1.6.0 fixes this critical security issue.

Recommended version: 1.6.0"""
        else:
            # Generic response for other vulnerabilities
            text = "Upgrade to the latest stable version to fix security vulnerabilities."
        
        mock_raw = {
            "id": "mock-response",
            "model": "mock-gpt-4o-mini",
            "choices": [{"message": {"content": text}}],
            "usage": {"total_tokens": 100}
        }
        
        return LLMResponse(text=text, raw=mock_raw)
