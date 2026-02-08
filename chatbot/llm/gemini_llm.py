"""
Google Gemini LLM Provider - fallback AI via Gemini API.
Uses Gemini 1.5 Flash for cost-effective responses.
"""

import os
import time
from typing import Optional
from .llm_interface import LLMInterface

# Lazy imports for optional dependencies
_genai = None
_gemini_available = False

try:
    import google.generativeai as genai
    _genai = genai
    _gemini_available = True
except ImportError:
    pass

# Rate limiter (optional)
_gemini_limiter = None
try:
    from utils.rate_limiter import gemini_limiter
    _gemini_limiter = gemini_limiter
except ImportError:
    pass


class GeminiLLM(LLMInterface):
    """
    Google Gemini LLM provider - reliable fallback.
    
    Features:
    - Real AI responses via Gemini 1.5 Flash
    - Rate limiting support
    - Automatic error handling
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-1.5-flash"
    ):
        self.model_name = model
        self._model = None
        
        # Resolve API key
        key = api_key or os.getenv("GOOGLE_API_KEY", "")
        if key and _gemini_available:
            try:
                _genai.configure(api_key=key)
                self._model = _genai.GenerativeModel(model)
            except Exception:
                self._model = None
    
    def generate_response(self, prompt: str, context: str) -> str:
        """
        Generate a response using Google Gemini API.
        
        Args:
            prompt: User's current message
            context: Formatted conversation history + system prompt
            
        Returns:
            Generated response text
        """
        if not self._model:
            return "AI Advisor is not available. Please configure GOOGLE_API_KEY in your .env file."
        
        # Rate limiting
        if _gemini_limiter:
            wait_time = _gemini_limiter.acquire()
            if wait_time > 0:
                time.sleep(min(wait_time, 5))
        
        # Build full prompt
        full_prompt = f"{context}\n\n--- USER QUESTION ---\n{prompt}"
        
        try:
            response = self._model.generate_content(full_prompt)
            return response.text if response.text else "No response generated."
        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "limit" in error_str or "quota" in error_str:
                return "Rate limit reached. Please wait a moment before asking another question."
            return f"Error generating response: {str(e)}"
    
    def is_available(self) -> bool:
        """Check if Gemini model is configured."""
        return self._model is not None
    
    def get_provider_name(self) -> str:
        return f"Google Gemini ({self.model_name})"
