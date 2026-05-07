import abc
import time
import logging
import json
from typing import Any, Dict, Optional
from backend.app.core.config import settings

# FIX C2: Lazy try/except so app doesn't crash at startup if groq is not installed
try:
    from groq import Groq
    _groq_available = True
except ImportError:
    Groq = None  # type: ignore
    _groq_available = False

logger = logging.getLogger("llm.provider")
if not _groq_available:
    logger.warning("groq package is not installed — GroqProvider will be unavailable")

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
        if not _groq_available:
            raise RuntimeError("groq package not installed — use mock provider instead")
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
        # Return a random valid JSON based on what is being requested
        import random
        
        # 1. NEWS INJECTION MOCK
        if "financial analyst engine" in system_message.lower():
            return json.dumps({
                "title": "Mock Market Shock",
                "description": f"A simulated event triggered by: {prompt[:30]}...",
                "severity": random.choice(["LOW", "MEDIUM", "HIGH"]),
                "impact_pct": round(random.uniform(-10.0, 5.0), 2),
                "affected_stocks": ["AAPL", "MSFT", "NVDA"]
            })
            
        # 2. DEBATE MOCK
        if "war room" in system_message.lower():
            return json.dumps({
                "bull": "This is a massive buying opportunity. Fundamentals are strong.",
                "bear": "The bubble is about to burst. We need to exit all long positions.",
                "risk": "Volatility is increasing. I recommend tightening stop-losses and reducing leverage."
            })

        # 3. BRIEFING MOCK
        if "strategist" in system_message.lower():
            regime = prompt.split('Regime: ')[-1].split('\n')[0]
            return json.dumps({
                "briefing": f"Market pulse is currently {regime}. Global telemetry indicates stable liquidity across all primary nodes."
            })

        # 4. CHAT MOCK (Optional check, but default handles it)
        if "assistant" in system_message.lower():
             return json.dumps({"response": "I am a mock assistant. I see the market is moving.", "confidence": "high"})

        # 4. DEFAULT AGENT ACTION MOCK
        actions = ["buy", "sell", "hold"]
        stocks = ["AAPL", "MSFT", "NVDA", "JPM", "XOM"]
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
