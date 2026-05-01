"""
Message type definitions and data structures.
Clean, typed interfaces for all message handling.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Literal


class MessageRole(Enum):
    """Role of the message sender."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    """
    Represents a single message in a conversation.
    
    Attributes:
        role: Who sent the message (user, assistant, system)
        content: The message text
        timestamp: When the message was created
        metadata: Optional additional data (e.g., confidence, emotion)
    """
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert message to dictionary for serialization."""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        """Create message from dictionary."""
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {})
        )


@dataclass
class ChatResponse:
    """
    Represents the chatbot's response with metadata.
    
    Attributes:
        text: The response message
        confidence: How confident the model is in the response
        suggested_followup: Optional follow-up question suggestion
        processing_time: Time taken to generate response (seconds)
    """
    text: str
    confidence: Literal["high", "medium", "low"] = "medium"
    suggested_followup: Optional[str] = None
    processing_time: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert response to dictionary."""
        return {
            "text": self.text,
            "confidence": self.confidence,
            "suggested_followup": self.suggested_followup,
            "processing_time": self.processing_time
        }
