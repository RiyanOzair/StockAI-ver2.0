"""
LLM Interface - abstract base class for all LLM providers.
This allows easy swapping of different AI providers (OpenAI, Groq, Gemini, etc.)
"""

from abc import ABC, abstractmethod
from typing import Optional


class LLMInterface(ABC):
    """
    Abstract interface for Language Model providers.
    
    Any LLM implementation must implement this interface.
    This ensures the ChatEngine remains provider-agnostic.
    
    All methods are synchronous to avoid event-loop conflicts
    with Streamlit's own async runtime.
    """
    
    @abstractmethod
    def generate_response(self, prompt: str, context: str) -> str:
        """
        Generate a response to a user prompt with conversation context.
        
        Args:
            prompt: The user's current message/question
            context: Formatted conversation history
        
        Returns:
            Generated response text
        
        Raises:
            Exception: If generation fails
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the LLM provider is available and configured.
        
        Returns:
            True if the provider can be used, False otherwise
        """
        pass
    
    def get_provider_name(self) -> str:
        """Get the name of the LLM provider."""
        return self.__class__.__name__
