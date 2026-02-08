"""
Mock LLM implementation - for testing and development.
Returns deterministic responses without calling real APIs.
"""

import time
import random
from typing import Optional
from .llm_interface import LLMInterface


class MockLLM(LLMInterface):
    """
    Mock LLM for testing - returns pre-defined responses.
    
    This is useful for:
    - Development without API keys
    - Testing chatbot logic
    - Demonstrations
    - CI/CD pipelines
    """
    
    # Pre-defined response patterns
    RESPONSES = {
        "greeting": [
            "Hello! I'm your AI assistant. How can I help you today?",
            "Hi there! What would you like to know?",
            "Hey! I'm here to assist you. What's on your mind?"
        ],
        "help": [
            "I can help you with various tasks like answering questions, explaining concepts, and providing information.",
            "I'm here to assist! You can ask me questions, get explanations, or just chat.",
            "I'm an AI assistant ready to help with information, explanations, and answers to your questions."
        ],
        "market": [
            "Based on the current market data, there are several interesting trends to observe.",
            "The market is showing dynamic behavior today with various factors at play.",
            "Let me analyze the market situation for you..."
        ],
        "agent": [
            "The trading agents are performing according to their strategies and behavioral patterns.",
            "Each agent has unique characteristics that influence their trading decisions.",
            "Agent performance varies based on market conditions and their configured behaviors."
        ],
        "analysis": [
            "Let me break that down for you in simple terms...",
            "Here's what the data is telling us...",
            "Looking at the patterns, we can observe..."
        ],
        "default": [
            "That's an interesting question! Let me think about that...",
            "I understand what you're asking. Based on the available information...",
            "Good question! Here's what I can tell you..."
        ]
    }
    
    def __init__(self, simulate_delay: bool = True, delay_range: tuple = (0.3, 0.8)):
        """
        Initialize mock LLM.
        
        Args:
            simulate_delay: Whether to simulate API latency
            delay_range: Min and max delay in seconds (if simulating)
        """
        self.simulate_delay = simulate_delay
        self.delay_range = delay_range
    
    def generate_response(self, prompt: str, context: str) -> str:
        """
        Generate a mock response based on keywords in the prompt.
        
        Args:
            prompt: User's message
            context: Conversation context (analyzed for better responses)
        
        Returns:
            Mock response text
        """
        # Simulate API latency
        if self.simulate_delay:
            delay = random.uniform(*self.delay_range)
            time.sleep(delay)
        
        # Analyze prompt for keywords
        prompt_lower = prompt.lower()
        
        # Determine response category
        if any(word in prompt_lower for word in ["hello", "hi", "hey", "greetings"]):
            category = "greeting"
        elif any(word in prompt_lower for word in ["help", "what can you", "how do you"]):
            category = "help"
        elif any(word in prompt_lower for word in ["market", "stock", "price", "trading"]):
            category = "market"
        elif any(word in prompt_lower for word in ["agent", "trader", "strategy"]):
            category = "agent"
        elif any(word in prompt_lower for word in ["analyze", "explain", "why", "how"]):
            category = "analysis"
        else:
            category = "default"
        
        # Select a random response from the category
        responses = self.RESPONSES.get(category, self.RESPONSES["default"])
        base_response = random.choice(responses)
        
        # Add contextual awareness (simulate understanding)
        if "?" in prompt:
            # It's a question
            response = base_response
        else:
            # It's a statement
            response = f"I understand. {base_response}"
        
        return response
    
    def is_available(self) -> bool:
        """Mock LLM is always available."""
        return True
    
    def get_provider_name(self) -> str:
        """Return the provider name."""
        return "MockLLM (Development/Testing)"
