"""
Groq LLM Provider - real AI responses via Groq API.
Uses Llama 3.3 70B for fast, high-quality market analysis.
"""

import os
import time
from typing import Optional
from .llm_interface import LLMInterface

# Lazy imports for optional dependencies
_groq_client_class = None
_groq_available = False

try:
    from groq import Groq
    _groq_client_class = Groq
    _groq_available = True
except ImportError:
    pass

# Rate limiter (optional)
_groq_limiter = None
try:
    from utils.rate_limiter import groq_limiter
    _groq_limiter = groq_limiter
except ImportError:
    pass


class GroqLLM(LLMInterface):
    """
    Groq LLM provider - fast inference via Llama 3.3 70B.
    
    Features:
    - Real AI responses with simulation context awareness
    - Rate limiting to stay within free tier
    - Automatic fallback on errors
    - Configurable model and parameters
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.7,
        max_tokens: int = 500
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None
        
        # Resolve API key
        key = api_key or os.getenv("GROQ_API_KEY", "")
        if key and _groq_available:
            try:
                self._client = _groq_client_class(api_key=key)
            except Exception:
                self._client = None
    
    def generate_response(self, prompt: str, context: str) -> str:
        """
        Generate a response using Groq API.
        
        Args:
            prompt: User's current message
            context: Formatted conversation history + system prompt
            
        Returns:
            Generated response text
        """
        if not self._client:
            return "AI Advisor is not available. Please configure GROQ_API_KEY in your .env file."
        
        # Rate limiting
        if _groq_limiter:
            wait_time = _groq_limiter.acquire()
            if wait_time > 0:
                time.sleep(min(wait_time, 5))  # Cap wait at 5s
        
        # Build messages for chat completion
        messages = [{"role": "user", "content": f"{context}\n\n--- USER QUESTION ---\n{prompt}"}]
        
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            content = response.choices[0].message.content
            return content if content else "No response generated."
        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "limit" in error_str:
                return "Rate limit reached. Please wait a moment before asking another question."
            return f"Error generating response: {str(e)}"
    
    def is_available(self) -> bool:
        """Check if Groq client is configured."""
        return self._client is not None
    
    def get_provider_name(self) -> str:
        return f"Groq ({self.model.split('-')[0].title()})"
