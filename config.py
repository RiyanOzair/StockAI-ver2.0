"""
StockAI Configuration
=====================
Centralized configuration for the StockAI simulation platform.
All magic numbers and tunable parameters are defined here with documentation.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# ═══════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class APIConfig:
    """API keys and endpoints configuration."""
    
    # LLM Provider API Keys (loaded from environment)
    OPENAI_API_KEY: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    GROQ_API_KEY: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    GOOGLE_API_KEY: str = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    
    # Ollama (local)
    OLLAMA_HOST: str = field(default_factory=lambda: os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    
    # Default models per provider
    DEFAULT_MODELS: Dict[str, str] = field(default_factory=lambda: {
        "groq": "llama-3.1-70b-versatile",
        "gemini": "gemini-1.5-flash",
        "ollama": "llama3.1",
        "openai": "gpt-4o-mini"
    })


# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATION DEFAULTS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SimulationDefaults:
    """Default values for simulation configuration."""
    
    # Agent settings
    MIN_AGENTS: int = 1
    MAX_AGENTS: int = 500
    DEFAULT_AGENTS: int = 50
    
    # Time settings
    MIN_DAYS: int = 1
    MAX_DAYS: int = 365
    DEFAULT_DAYS: int = 30
    TRADING_DAYS_PER_YEAR: int = 264  # Standard trading calendar
    SESSIONS_PER_DAY: int = 3  # Morning, Afternoon, Closing
    
    # Financial settings
    MIN_INITIAL_CASH: float = 100_000.0
    MAX_INITIAL_CASH: float = 500_000.0
    MAX_INITIAL_PROPERTY: float = 5_000_000.0
    
    # Stock holdings
    MIN_INITIAL_SHARES: int = 50
    MAX_INITIAL_SHARES: int = 500
    
    # Event settings
    MIN_EVENT_INTENSITY: int = 1
    MAX_EVENT_INTENSITY: int = 10
    DEFAULT_EVENT_INTENSITY: int = 5
    
    # Loan settings
    INITIAL_LOAN_PROBABILITY: float = 0.3  # 30% chance of starting with a loan
    MIN_LOAN_AMOUNT: float = 50_000.0
    MAX_LOAN_AMOUNT: float = 200_000.0
    LOAN_REPAYMENT_DAYS: List[int] = field(default_factory=lambda: [22, 44, 66])
    
    # Random seed
    DEFAULT_SEED: int = 42


# ═══════════════════════════════════════════════════════════════════════════════
# TRADING BEHAVIOR THRESHOLDS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass 
class TradingThresholds:
    """Thresholds that control agent trading behavior in mock simulation."""
    
    # Buy/Sell decision thresholds (used in simulation_engine.py)
    BUY_THRESHOLD: float = 0.7   # Probability above which agent buys
    SELL_THRESHOLD: float = 0.2  # Probability below which agent sells
    HOLD_RANGE: tuple = (0.2, 0.7)  # Range where agent holds
    
    # Trade sizing
    TRADE_SIZE_MULTIPLIER: float = 0.1  # Fraction of holdings to trade
    MIN_TRADE_SIZE: int = 1
    MAX_TRADE_SIZE: int = 100
    
    # Character-based adjustments
    CHARACTER_AGGRESSION: Dict[str, float] = field(default_factory=lambda: {
        "Conservative": 0.3,    # Less likely to trade
        "Balanced": 0.5,        # Moderate trading
        "Growth-Oriented": 0.7, # Active trading
        "Aggressive": 0.9       # Frequent trading
    })
    
    # Bias impact weights
    HERDING_IMPACT: Dict[str, float] = field(default_factory=lambda: {
        "Low": 0.1,
        "Medium": 0.3,
        "High": 0.5
    })
    
    LOSS_AVERSION_IMPACT: Dict[str, float] = field(default_factory=lambda: {
        "Low": 0.1,
        "Medium": 0.25,
        "High": 0.4
    })


# ═══════════════════════════════════════════════════════════════════════════════
# PRICE MOVEMENT PARAMETERS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PriceConfig:
    """Parameters controlling stock price movements."""
    
    # Volatility multipliers
    VOLATILITY_MULTIPLIERS: Dict[str, float] = field(default_factory=lambda: {
        "Low": 0.01,      # 1% max movement
        "Medium": 0.025,  # 2.5% max movement
        "High": 0.05,     # 5% max movement
        "Extreme": 0.10   # 10% max movement
    })
    
    # Event impact on prices
    EVENT_SEVERITY_IMPACT: Dict[str, tuple] = field(default_factory=lambda: {
        "LOW": (-0.02, 0.02),      # ±2% price impact
        "MEDIUM": (-0.05, 0.05),   # ±5% price impact
        "HIGH": (-0.10, 0.10)      # ±10% price impact
    })
    
    # Mean reversion factor (pulls extreme prices back toward initial)
    MEAN_REVERSION_FACTOR: float = 0.02


# ═══════════════════════════════════════════════════════════════════════════════
# UI CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class UIConfig:
    """UI-related configuration."""
    
    # Auto-run speeds (seconds between simulation steps)
    AUTO_RUN_DELAYS: Dict[str, float] = field(default_factory=lambda: {
        "Slow": 2.5,
        "Normal": 1.5,
        "Fast": 0.7,
        "Ultra": 0.25
    })
    
    # Snapshot limits (for rewind functionality)
    MAX_SNAPSHOTS: int = 60
    
    # Chart settings
    CHART_HEIGHT_MAIN: int = 450
    CHART_HEIGHT_MINI: int = 200
    
    # Leaderboard
    TOP_PERFORMERS_COUNT: int = 10
    MAX_AGENTS_DISPLAY: int = 30
    
    # Chat settings
    MAX_CHAT_HISTORY: int = 50
    
    # Data export
    EXPORT_FILENAME_PREFIX: str = "stockai_export"


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCES
# ═══════════════════════════════════════════════════════════════════════════════

# Create singleton instances for easy import
api_config = APIConfig()
simulation_defaults = SimulationDefaults()
trading_thresholds = TradingThresholds()
price_config = PriceConfig()
ui_config = UIConfig()


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def validate_api_keys() -> Dict[str, bool]:
    """Check which API keys are configured."""
    return {
        "openai": bool(api_config.OPENAI_API_KEY),
        "groq": bool(api_config.GROQ_API_KEY),
        "google": bool(api_config.GOOGLE_API_KEY),
        "ollama": True  # Local, always "available"
    }


def get_available_providers() -> List[str]:
    """Get list of providers with valid API keys."""
    keys = validate_api_keys()
    return [provider for provider, available in keys.items() if available]
