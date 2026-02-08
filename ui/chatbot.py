"""
Lightweight UI adapter for the chatbot used by the Streamlit app and tests.

Provides a minimal `StockAIAdvisor` wrapper that selects an available LLM
provider (Groq / Gemini / Mock) and exposes small helper methods used by
unit tests (`get_provider_name`, `get_connection_status`).

This module intentionally keeps behavior simple so tests can import and
instantiate the advisor without requiring external API keys.
"""
from typing import Optional
import os

try:
    # Prefer Groq when available/configured
    from chatbot.llm.groq_llm import GroqLLM
except Exception:
    GroqLLM = None

try:
    # Prefer Gemini (Google) when available/configured
    from chatbot.llm.gemini_llm import GeminiLLM
except Exception:
    GeminiLLM = None

from chatbot.llm.mock_llm import MockLLM
from chatbot.core.chat_engine import ChatEngine


class StockAIAdvisor:
    """Simple adapter exposing a consistent interface for the UI/tests.

    Behavior:
    - If `GROQ_API_KEY` env var is set and `GroqLLM` imported, use GroqLLM.
    - Else if `GOOGLE_API_KEY` env var is set and `GeminiLLM` imported, use GeminiLLM.
    - Otherwise fall back to `MockLLM` (always available for tests).
    """

    def __init__(self, llm_provider: Optional[str] = None):
        self.llm = None

        # Allow explicit provider override
        provider = (llm_provider or os.getenv("PREFERRED_LLM", "")).lower()

        # Try explicit preference first
        if provider == "groq" and GroqLLM is not None:
            self.llm = GroqLLM()
        elif provider == "gemini" and GeminiLLM is not None:
            self.llm = GeminiLLM()

        # Auto-detect based on env vars
        if self.llm is None:
            groq_key = os.getenv("GROQ_API_KEY", "")
            google_key = os.getenv("GOOGLE_API_KEY", "")
            if groq_key and GroqLLM is not None:
                try:
                    self.llm = GroqLLM(api_key=groq_key)
                except Exception:
                    self.llm = None
            elif google_key and GeminiLLM is not None:
                try:
                    self.llm = GeminiLLM(api_key=google_key)
                except Exception:
                    self.llm = None

        # Fallback to mock for offline/dev/test usage
        if self.llm is None:
            self.llm = MockLLM()

        # Initialize a simple ChatEngine wrapper (not strictly required by tests)
        try:
            self.engine = ChatEngine(llm=self.llm)
        except Exception:
            self.engine = None

    def get_provider_name(self) -> str:
        """Return provider name (string)."""
        try:
            return self.llm.get_provider_name()
        except Exception:
            return "Unknown (no provider)"

    def get_connection_status(self) -> str:
        """Return a short status string mentioning connection and provider."""
        available = False
        try:
            available = bool(self.llm.is_available())
        except Exception:
            available = False

        provider = self.get_provider_name()
        return f"connected: {str(available).lower()}, provider: {provider}"

    def ask(self, question: str, context: str = "") -> str:
        """Convenience method to produce a response via the underlying LLM.

        Returns the generated text. If the engine/llm fails, returns an error message.
        """
        try:
            if self.engine is not None:
                # Use engine if available
                return self.engine.llm.generate_response(question, context)
            return self.llm.generate_response(question, context)
        except Exception as e:
            return f"Error: {str(e)}"


__all__ = ["StockAIAdvisor"]
