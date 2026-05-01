"""
Chat Engine - core conversational logic.
Framework-agnostic orchestrator for the chatbot.
Coordinates memory, prompts, and LLM interface.
"""

import time
from typing import Optional, Dict, Any, List
from .message_types import Message, MessageRole, ChatResponse
from .memory_manager import MemoryManager
from .prompt_manager import PromptManager
from ..llm.llm_interface import LLMInterface


class ChatEngine:
    """
    Core chat orchestrator - handles conversation flow.
    
    This is the main entry point for chatbot functionality.
    It's completely framework-agnostic and can be used in any Python app.
    
    Usage:
        engine = ChatEngine(llm=MyLLMProvider())
        response = await engine.process_message("Hello!")
    """
    
    def __init__(
        self,
        llm: LLMInterface,
        memory_size: int = 10,
        custom_system_prompt: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the chat engine.
        
        Args:
            llm: LLM provider implementing LLMInterface
            memory_size: Number of messages to retain in context
            custom_system_prompt: Override default system prompt
            context_data: Additional context for the chatbot
        """
        self.llm = llm
        self.memory = MemoryManager(max_messages=memory_size)
        self.prompt_manager = PromptManager(custom_system_prompt)
        self.context_data = context_data or {}
        
        # Set system prompt in memory
        self._initialize_system_prompt()
    
    def _initialize_system_prompt(self) -> None:
        """Set up the initial system prompt."""
        system_message = Message(
            role=MessageRole.SYSTEM,
            content=self.prompt_manager.get_system_prompt()
        )
        self.memory.add_message(system_message)
    
    def process_message(self, user_input: str) -> ChatResponse:
        """
        Process a user message and generate a response.
        
        This is the main entry point for chatbot interaction.
        Fully synchronous to work within Streamlit's event loop.
        
        Args:
            user_input: The user's message text
        
        Returns:
            ChatResponse with text, confidence, and optional follow-up
        """
        start_time = time.time()
        
        # Add user message to memory
        user_message = Message(role=MessageRole.USER, content=user_input)
        self.memory.add_message(user_message)
        
        # Get conversation context
        context_messages = self.memory.get_context()
        
        # Format context for LLM (includes system prompt + simulation data)
        formatted_context = self._format_context_for_llm(context_messages)
        
        # Generate response from LLM (synchronous)
        try:
            response_text = self.llm.generate_response(
                prompt=user_input,
                context=formatted_context
            )
            confidence = "high"
        except Exception as e:
            # Fallback response on error
            response_text = self.prompt_manager.get_template("error")
            confidence = "low"
        
        # Add assistant response to memory
        assistant_message = Message(role=MessageRole.ASSISTANT, content=response_text)
        self.memory.add_message(assistant_message)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Build response object
        response = ChatResponse(
            text=response_text,
            confidence=confidence,
            suggested_followup=self._generate_followup(user_input, response_text),
            processing_time=processing_time
        )
        
        return response
    
    def _format_context_for_llm(self, messages: List[Message]) -> str:
        """
        Format conversation context into a string for the LLM.
        Includes system prompt, simulation data, and conversation history.
        
        Args:
            messages: List of messages to format
        
        Returns:
            Formatted context string
        """
        context_parts = []
        
        # Add system prompt
        system_prompt = self.prompt_manager.get_system_prompt()
        if system_prompt:
            context_parts.append(system_prompt)
        
        # Add simulation context if available
        if self.context_data:
            sim_context = self.prompt_manager.format_simulation_context(self.context_data)
            if sim_context:
                context_parts.append(f"\n--- CURRENT SIMULATION DATA ---\n{sim_context}")
        
        # Add conversation history
        context_parts.append("\n--- CONVERSATION ---")
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                continue  # Already added above
            role_label = msg.role.value.upper()
            context_parts.append(f"{role_label}: {msg.content}")
        
        return "\n".join(context_parts)
    
    def _generate_followup(self, user_input: str, response: str) -> Optional[str]:
        """
        Generate a follow-up question suggestion (optional).
        
        Args:
            user_input: Original user question
            response: Bot's response
        
        Returns:
            Follow-up question or None
        """
        # Simple heuristic: suggest follow-up for short queries
        if len(user_input.split()) <= 3:
            return "Would you like more details?"
        return None
    
    def get_conversation_history(self) -> List[Message]:
        """Get all messages in current conversation."""
        return self.memory.get_context(include_system=False)
    
    def clear_conversation(self) -> None:
        """Clear conversation history (keeps system prompt)."""
        self.memory.clear(preserve_system=True)
    
    def update_context(self, context_data: Dict[str, Any]) -> None:
        """
        Update chatbot context dynamically.
        
        Args:
            context_data: New context information
        """
        self.context_data.update(context_data)
    
    def export_session(self) -> dict:
        """Export entire chat session for persistence."""
        return {
            "memory": self.memory.export_conversation(),
            "context_data": self.context_data,
            "system_prompt": self.prompt_manager.get_system_prompt()
        }
    
    def import_session(self, session_data: dict) -> None:
        """
        Import a previously exported session.
        
        Args:
            session_data: Dictionary from export_session()
        """
        if "memory" in session_data:
            self.memory.import_conversation(session_data["memory"])
        
        if "context_data" in session_data:
            self.context_data = session_data["context_data"]
        
        if "system_prompt" in session_data:
            self.prompt_manager.set_system_prompt(session_data["system_prompt"])
