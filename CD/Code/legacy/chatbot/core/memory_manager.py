"""
Memory Manager - handles conversation context and history.
Stores messages with configurable retention limits.
Easily replaceable with database or vector store later.
"""

from typing import List, Optional
from .message_types import Message, MessageRole


class MemoryManager:
    """
    Manages conversation history with smart context retention.
    
    Features:
    - Stores last N messages (configurable)
    - Preserves system prompts separately
    - Clean context retrieval for LLM
    - Optional persistence hooks (for future DB integration)
    """
    
    def __init__(self, max_messages: int = 10):
        """
        Initialize memory manager.
        
        Args:
            max_messages: Maximum number of user/assistant messages to retain
        """
        self.max_messages = max_messages
        self._messages: List[Message] = []
        self._system_prompt: Optional[Message] = None
    
    def add_message(self, message: Message) -> None:
        """
        Add a message to memory.
        
        Args:
            message: The message to store
        """
        if message.role == MessageRole.SYSTEM:
            # System prompts are stored separately
            self._system_prompt = message
        else:
            self._messages.append(message)
            
            # Enforce memory limit (keep last N messages)
            if len(self._messages) > self.max_messages:
                self._messages = self._messages[-self.max_messages:]
    
    def get_context(self, include_system: bool = True) -> List[Message]:
        """
        Get conversation context for LLM.
        
        Args:
            include_system: Whether to include system prompt
        
        Returns:
            List of messages in chronological order
        """
        context = []
        
        if include_system and self._system_prompt:
            context.append(self._system_prompt)
        
        context.extend(self._messages)
        return context
    
    def get_last_n_messages(self, n: int) -> List[Message]:
        """
        Get the last N messages.
        
        Args:
            n: Number of messages to retrieve
        
        Returns:
            Last N messages
        """
        return self._messages[-n:] if len(self._messages) >= n else self._messages
    
    def clear(self, preserve_system: bool = True) -> None:
        """
        Clear conversation history.
        
        Args:
            preserve_system: Whether to keep the system prompt
        """
        self._messages = []
        if not preserve_system:
            self._system_prompt = None
    
    def get_message_count(self) -> int:
        """Get total number of stored messages (excluding system)."""
        return len(self._messages)
    
    def has_messages(self) -> bool:
        """Check if there are any messages in memory."""
        return len(self._messages) > 0
    
    def export_conversation(self) -> dict:
        """
        Export conversation for persistence/analysis.
        
        Returns:
            Dictionary with all messages and metadata
        """
        return {
            "system_prompt": self._system_prompt.to_dict() if self._system_prompt else None,
            "messages": [msg.to_dict() for msg in self._messages],
            "total_messages": len(self._messages),
            "max_messages": self.max_messages
        }
    
    def import_conversation(self, data: dict) -> None:
        """
        Import conversation from exported data.
        
        Args:
            data: Dictionary from export_conversation()
        """
        if data.get("system_prompt"):
            self._system_prompt = Message.from_dict(data["system_prompt"])
        
        self._messages = [Message.from_dict(msg) for msg in data.get("messages", [])]
        
        # Enforce memory limit
        if len(self._messages) > self.max_messages:
            self._messages = self._messages[-self.max_messages:]
