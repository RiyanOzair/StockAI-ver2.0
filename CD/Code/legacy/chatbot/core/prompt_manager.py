"""
Prompt Manager - handles system prompts, templates, and simulation context formatting.
Configurable behavior without hardcoding.
"""

from typing import Dict, Optional, Any


class PromptManager:
    """
    Manages system prompts, message templates, and simulation context.
    
    Allows dynamic prompt customization without code changes.
    """
    
    # StockAI-optimized system prompt
    DEFAULT_SYSTEM_PROMPT = """You are StockAI Advisor, an expert AI assistant for the StockAI Market Simulation platform.
You help users understand market dynamics, agent behavior, and trading strategies within the simulation.

Your personality:
- Professional but approachable
- Data-driven and analytical
- Clear and concise in explanations
- Use relevant market terminology
- Offer actionable insights when possible

Current simulation context will be provided with each query. Use this data to give relevant, specific answers.
Keep responses concise (2-4 sentences for simple queries, up to a paragraph for complex analysis).
If the simulation hasn't started, let the user know and offer general guidance.
"""
    
    # Prompt templates for different contexts
    TEMPLATES = {
        "greeting": "Hello! I'm your StockAI Advisor. How can I help you today?",
        "error": "I apologize, but I encountered an error processing your request. Could you try rephrasing?",
        "clarification": "I'm not sure I understood that correctly. Could you provide more details?",
        "thinking": "Let me analyze that for you...",
        "followup": "Would you like to know more about {topic}?",
        "no_provider": "AI Advisor is not available. Please configure GROQ_API_KEY or GOOGLE_API_KEY in your .env file."
    }
    
    def __init__(self, custom_system_prompt: Optional[str] = None):
        """
        Initialize prompt manager.
        
        Args:
            custom_system_prompt: Override default system prompt
        """
        self.system_prompt = custom_system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.templates = self.TEMPLATES.copy()
    
    def get_system_prompt(self) -> str:
        """Get the current system prompt."""
        return self.system_prompt
    
    def set_system_prompt(self, prompt: str) -> None:
        """Update the system prompt."""
        self.system_prompt = prompt
    
    def get_template(self, template_name: str, **kwargs) -> str:
        """
        Get a prompt template with variable substitution.
        
        Args:
            template_name: Name of the template
            **kwargs: Variables to substitute in template
        
        Returns:
            Formatted template string
        """
        template = self.templates.get(template_name, "")
        try:
            return template.format(**kwargs) if template else ""
        except (KeyError, IndexError):
            return template
    
    def add_template(self, name: str, template: str) -> None:
        """Add or update a prompt template."""
        self.templates[name] = template
    
    def format_simulation_context(self, state: Any) -> str:
        """
        Format simulation state into rich context for the LLM.
        
        Ported from the original StockAI chatbot's generate_context().
        Extracts stock prices, agent performance, events, and strategy data.
        
        Args:
            state: Simulation engine state object, or dict with context data
            
        Returns:
            Formatted context string with all relevant simulation data
        """
        # Handle dict with app_context key (from ChatEngine.context_data)
        if isinstance(state, dict):
            state = state.get("app_context", state)
        
        # If it's a string already, return it
        if isinstance(state, str):
            return state if state else "Simulation not yet started."
        
        # If state is None or doesn't have status attribute
        if state is None:
            return "Simulation not yet started. No market data available."
        
        # Check for IDLE state
        status = getattr(state, 'status', None)
        if not status or status == "IDLE":
            return "Simulation not yet started. No market data available."
        
        context_parts = []
        
        # Basic simulation info
        context_parts.append(f"Simulation Status: {status}")
        
        current_day = getattr(state, 'current_day', None)
        total_days = getattr(state, 'total_days', None)
        if current_day is not None and total_days is not None:
            context_parts.append(f"Current Day: {current_day} / {total_days}")
        
        volatility = getattr(state, 'volatility', None)
        if volatility is not None:
            context_parts.append(f"Volatility Setting: {volatility}")
        
        system_risk = getattr(state, 'system_risk', None)
        if system_risk is not None:
            context_parts.append(f"System Risk Level: {system_risk}")
        
        market_sentiment = getattr(state, 'market_sentiment', None)
        if market_sentiment is not None:
            context_parts.append(f"Market Sentiment: {market_sentiment}")
        
        # Stock prices
        stock_a = getattr(state, 'stock_a', None)
        stock_b = getattr(state, 'stock_b', None)
        if stock_a and stock_b:
            context_parts.append(f"\nPrimary Stocks:")
            _add_stock_info(context_parts, stock_a)
            _add_stock_info(context_parts, stock_b)
        
        # Extra stocks summary
        extra_stocks = getattr(state, 'extra_stocks', None)
        if extra_stocks:
            context_parts.append(f"\nExtended Market ({len(extra_stocks)} stocks):")
            for stock in extra_stocks[:5]:  # Top 5
                _add_stock_info(context_parts, stock)
        
        # Agent summary
        agents = getattr(state, 'agents', [])
        active_agents = getattr(state, 'active_agents', None)
        agent_count = getattr(state, 'agent_count', None)
        
        if agents:
            context_parts.append(f"\nAgents:")
            if active_agents is not None and agent_count is not None:
                context_parts.append(f"  - Active: {active_agents} / {agent_count}")
            
            bankruptcies = len([a for a in agents if getattr(a, 'is_bankrupt', False)])
            if bankruptcies > 0:
                context_parts.append(f"  - Bankruptcies: {bankruptcies}")
            
            # Strategy performance
            strategies: Dict[str, list] = {}
            for agent in agents:
                char = getattr(agent, 'character', 'Unknown')
                pnl = getattr(agent, 'pnl_percent', 0)
                if char not in strategies:
                    strategies[char] = []
                strategies[char].append(pnl)
            
            if strategies:
                context_parts.append(f"\nStrategy Performance (Avg P&L):")
                for strategy, pnls in strategies.items():
                    avg_pnl = sum(pnls) / len(pnls) if pnls else 0
                    context_parts.append(f"  - {strategy}: {avg_pnl:+.2f}%")
            
            # Top agents
            sorted_agents = sorted(agents, key=lambda a: getattr(a, 'pnl_percent', 0), reverse=True)[:3]
            if sorted_agents:
                context_parts.append(f"\nTop Agents:")
                for i, agent in enumerate(sorted_agents, 1):
                    name = getattr(agent, 'name', f'Agent {i}')
                    char = getattr(agent, 'character', 'Unknown')
                    pnl = getattr(agent, 'pnl_percent', 0)
                    context_parts.append(f"  {i}. {name} ({char}): {pnl:+.2f}%")
        
        # Recent events
        events = getattr(state, 'events', [])
        if events and current_day:
            recent_events = [e for e in events if getattr(e, 'day', 0) <= current_day][-3:]
            if recent_events:
                context_parts.append(f"\nRecent Events:")
                for event in recent_events:
                    day = getattr(event, 'day', '?')
                    title = getattr(event, 'title', 'Unknown')
                    severity = getattr(event, 'severity', 'Unknown')
                    context_parts.append(f"  - Day {day}: {title} ({severity})")
        
        return "\n".join(context_parts)
    
    def format_context_prompt(self, context_data: Dict) -> str:
        """
        Format contextual information into a prompt (legacy support).
        
        Args:
            context_data: Dictionary with context information
        
        Returns:
            Formatted context prompt
        """
        return self.format_simulation_context(context_data)


def _add_stock_info(parts: list, stock: Any) -> None:
    """Helper to add stock info to context parts."""
    name = getattr(stock, 'name', 'Unknown')
    price = getattr(stock, 'price', 0)
    change = getattr(stock, 'change_percent', 0)
    parts.append(f"  - {name}: ${price:.2f} ({change:+.2f}%)")
