"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     StockAI - Modular Chatbot System                        ║
║         Production-ready conversational AI inspired by WhatsApp Meta AI     ║
╚══════════════════════════════════════════════════════════════════════════════╝

A clean, framework-agnostic chatbot architecture with:
- Layered abstraction (core, llm, ui, adapters)
- Provider-agnostic LLM interface
- Memory management with context retention
- Floating orb UI for web integration
"""

from .core.chat_engine import ChatEngine
from .core.memory_manager import MemoryManager
from .core.message_types import Message, MessageRole, ChatResponse
from .llm.llm_interface import LLMInterface
from .llm.mock_llm import MockLLM
from .llm.groq_llm import GroqLLM
from .llm.gemini_llm import GeminiLLM
from .config.chatbot_config import ChatbotConfig

__version__ = "2.0.0"
__all__ = [
    "ChatEngine",
    "MemoryManager",
    "Message",
    "MessageRole",
    "ChatResponse",
    "LLMInterface",
    "MockLLM",
    "GroqLLM",
    "GeminiLLM",
    "ChatbotConfig"
]
