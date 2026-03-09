import abc
import time
import logging
import json
from typing import Any, Dict, Optional
from groq import Groq
from backend.app.core.config import settings

logger = logging.getLogger("llm.provider")

class LLMProvider(abc.ABC):
    """
    Abstract Base Class for LLM Providers.
    Enforces a standard interface for all AI models.
    """
    @abc.abstractmethod
    def generate(self, prompt: str, system_message: str = "") -> str:
        pass

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("openai package not installed or outdated. Run: pip install openai>=1.12.0")
        self.model = model

    def generate(self, prompt: str, system_message: str = "") -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}, # Force JSON
                temperature=0.7
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI Error: {e}")
            raise

class GroqProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.client = Groq(api_key=api_key)
        self.model = model
        self._rate_limited_until = 0.0  # timestamp when rate limit expires

    def generate(self, prompt: str, system_message: str = "") -> str:
        # Skip API call if we know we're rate-limited
        if time.time() < self._rate_limited_until:
            raise RuntimeError("Rate limited — using demo mode")
        try:
            return self._call_api(prompt, system_message) or ""
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                self._rate_limited_until = time.time() + 60  # back off 60s
            logger.error(f"Groq Error: {e}")
            raise

    def _call_api(self, prompt, system_message, retries=3):
        for attempt in range(retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                logger.warning(f"Groq Attempt {attempt+1} failed: {e}")
                # Don't retry rate limit errors — they won't clear within seconds
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    raise
                if attempt == retries - 1:
                    raise
                time.sleep(1 * (attempt + 1))

class MockProvider(LLMProvider):
    def generate(self, prompt: str, system_message: str = "") -> str:
        # Return a random valid JSON action for testing without API keys
        import random
        actions = ["buy", "sell", "hold"]
        stocks = ["A", "B"]
        action = random.choice(actions)
        return json.dumps({
            "action": action,
            "stock": random.choice(stocks) if action != "hold" else None,
            "quantity": random.randint(1, 10),
            "price": round(random.uniform(90, 110), 2),
            "reasoning": "Mock reasoning for testing."
        })

class LLMFactory:
    """
    Factory to create the correct provider based on config.
    """
    @staticmethod
    def create_provider() -> LLMProvider:
        provider_type = settings.DEFAULT_MODEL_PROVIDER.lower()
        
        # Check for Mock provider explicitly or fallback if keys are missing
        if provider_type == "mock" or (not settings.GROQ_API_KEY and not settings.OPENAI_API_KEY):
            logger.warning("Using Mock Provider (No API Key found or explicitly set to mock)")
            return MockProvider()

        if provider_type == "groq":
            if not settings.GROQ_API_KEY:
                # Fallback or raise
                # logger.warning("GROQ_API_KEY missing, check .env")
                pass
            return GroqProvider(api_key=settings.GROQ_API_KEY, model=settings.DEFAULT_MODEL_NAME)
            
        elif provider_type == "openai":
            if not settings.OPENAI_API_KEY:
                pass
            return OpenAIProvider(api_key=settings.OPENAI_API_KEY, model=settings.DEFAULT_MODEL_NAME)
        
        else:
            raise ValueError(f"Unsupported provider: {provider_type}")
