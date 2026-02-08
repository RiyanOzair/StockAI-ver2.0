"""
Chatbot configuration - all settings in one place.
No magic values, everything is configurable.
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass
class ChatbotConfig:
    """
    Centralized chatbot configuration.
    
    All customizable aspects of the chatbot in one class.
    Makes it easy to create different chatbot profiles.
    """
    
    # Memory settings
    memory_size: int = 10  # Number of messages to retain
    
    # UI settings
    bot_name: str = "StockAI Assistant"
    bot_avatar: str = "🤖"
    user_avatar: str = "👤"
    welcome_message: str = "Hi! I'm your StockAI Assistant. How can I help you today?"
    
    # Behavior settings
    typing_speed: float = 0.05  # Seconds per character for typing simulation
    show_confidence: bool = False  # Show confidence levels in UI
    enable_followups: bool = True  # Show suggested follow-up questions
    
    # Quick action buttons
    quick_actions: Optional[List[str]] = None
    
    # LLM settings (auto-detects Groq > Gemini > Mock)
    llm_provider: Optional[str] = "auto"  # "mock", "groq", "gemini", etc.
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None
    
    # UI appearance
    theme: str = "dark"  # "dark" or "light"
    accent_color: str = "#8b5cf6"  # Purple by default
    orb_position: Tuple[int, int] = (30, 30)  # (right, bottom) in pixels
    
    def __post_init__(self):
        """Initialize default quick actions if not provided."""
        if self.quick_actions is None:
            self.quick_actions = [
                "What's happening in the market?",
                "Explain this to me",
                "Show me the trends",
                "Help me understand"
            ]
    
    @classmethod
    def for_stock_ai(cls) -> "ChatbotConfig":
        """
        Create a configuration optimized for StockAI.
        Uses auto-detection for LLM (Groq > Gemini > Mock).
        """
        return cls(
            bot_name="StockAI Advisor",
            bot_avatar="📊",
            welcome_message="Hello! I'm your StockAI Advisor. I can help you understand market dynamics, analyze agent behavior, and interpret trading patterns. Ask me anything!",
            quick_actions=[
                "Which strategy is performing best?",
                "What's the current market sentiment?",
                "Explain the latest market event",
                "Who are the top performing agents?"
            ],
            memory_size=15,  # Larger context for market analysis
            enable_followups=True,
            accent_color="#26a69a",  # StockAI green
            llm_provider="auto"  # Auto-detect best available LLM
        )
    
    @classmethod
    def minimal(cls) -> "ChatbotConfig":
        """
        Create a minimal configuration for simple use cases.
        
        Returns:
            ChatbotConfig with minimal settings
        """
        return cls(
            bot_name="AI",
            bot_avatar="💬",
            welcome_message="Hi! How can I help?",
            quick_actions=[],
            memory_size=5,
            enable_followups=False,
            show_confidence=False
        )
