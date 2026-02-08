"""
StockAI Simulation Engine
=========================
Bridge between the UI and the backend simulation logic.
Provides a clean interface for running and managing simulations.
"""

import sys
import os
import random
import json
import copy
import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

log = logging.getLogger(__name__)

# ===============================
# DATA CLASSES
# ===============================

@dataclass
class AgentState:
    """Represents the current state of an agent."""
    id: int
    name: str
    character: str  # Conservative, Aggressive, Balanced, Growth-Oriented
    cash: float
    stock_a_amount: int
    stock_b_amount: int
    total_value: float
    initial_value: float
    pnl_percent: float
    loans: List[Dict]
    is_bankrupt: bool
    quit: bool
    action_history: List[Dict] = field(default_factory=list)
    
    # Behavioral biases (simulated based on character and market conditions)
    herding_level: str = "Low"  # Low, Medium, High
    loss_aversion_level: str = "Medium"
    overconfidence_level: str = "Low"
    anchoring_level: str = "Medium"


@dataclass
class StockState:
    """Represents the current state of a stock."""
    name: str
    price: float
    initial_price: float
    price_history: List[Dict] = field(default_factory=list)  # [{day, session, price}]
    
    @property
    def change_percent(self) -> float:
        if self.initial_price == 0:
            return 0
        return ((self.price - self.initial_price) / self.initial_price) * 100


@dataclass
class MarketEvent:
    """Represents a market event."""
    day: int
    event_type: str  # "macro", "sentiment", "corporate"
    title: str
    description: str
    severity: str  # "LOW", "MEDIUM", "HIGH"
    impact: str  # Description of market impact


@dataclass
class TradeRecord:
    """Represents a completed trade."""
    day: int
    session: int
    stock: str
    buyer_id: int
    seller_id: int
    amount: int
    price: float


@dataclass 
class ForumMessage:
    """Represents a BBS forum message from an agent."""
    day: int
    agent_id: int
    agent_name: str
    message: str
    sentiment: str  # "bullish", "bearish", "neutral"


@dataclass
class SimulationState:
    """Complete simulation state."""
    # Status
    status: str = "IDLE"  # IDLE, CONFIGURED, RUNNING, PAUSED, COMPLETED
    run_id: Optional[str] = None
    current_day: int = 0
    current_session: int = 0
    
    # Configuration
    agent_count: int = 50
    total_days: int = 30
    sessions_per_day: int = 3
    volatility: str = "Medium"
    event_intensity: int = 5
    loan_market_enabled: bool = True
    random_seed: int = 42
    
    # Data
    agents: List[AgentState] = field(default_factory=list)
    stock_a: Optional[StockState] = None
    stock_b: Optional[StockState] = None
    extra_stocks: List[StockState] = field(default_factory=list)
    events: List[MarketEvent] = field(default_factory=list)
    manual_events: List[MarketEvent] = field(default_factory=list)
    trades: List[TradeRecord] = field(default_factory=list)
    forum_messages: List[ForumMessage] = field(default_factory=list)

    # Snapshots for rewind
    snapshots: List[Dict[str, Any]] = field(default_factory=list)

    # Custom agent configuration (optional)
    custom_agent: Optional[Dict[str, Any]] = None
    
    # Metrics
    total_capital: float = 0
    active_agents: int = 0
    total_trades: int = 0
    market_sentiment: str = "neutral"  # bullish, bearish, neutral
    herding_percentage: float = 0
    system_risk: str = "LOW"
    
    # LLM Mode
    llm_mode: bool = False
    llm_calls_made: int = 0


# ===============================
# AGENT NAME GENERATOR
# ===============================

AGENT_FIRST_NAMES = [
    "Rajesh", "Amina", "Sofia", "Lucas", "Zara", "Mateo", "Chen", "Elena",
    "Arjun", "Nora", "Kai", "Maya", "Omar", "Lucia", "Noah", "Rina",
    "Ibrahim", "Lea", "Hugo", "Priya", "Ezra", "Lina", "Yusuf", "Ava",
    "Diego", "Amir", "Sara", "Min", "Tariq", "Anya", "Hana", "Ethan",
    "Mei", "Leo", "Farah", "Jin", "Mariam", "Rafael", "Nia", "Zain"
]

AGENT_MODIFIERS = [
    "The Fox", "Ironhands", "Whisper", "Storm", "Lion", "Oracle", "Falcon",
    "Shadow", "Viper", "Anchor", "Rocket", "Sage", "Blaze", "Onyx", "Nova",
    "Cipher", "Maverick", "Pulse", "Quartz", "Echo"
]

def generate_agent_name(agent_id: int) -> str:
    """Generate a unique, human-like agent name with a modifier."""
    first = AGENT_FIRST_NAMES[agent_id % len(AGENT_FIRST_NAMES)]
    modifier = AGENT_MODIFIERS[(agent_id // len(AGENT_FIRST_NAMES)) % len(AGENT_MODIFIERS)]
    cycle = agent_id // (len(AGENT_FIRST_NAMES) * len(AGENT_MODIFIERS))
    suffix = f" #{cycle + 1}" if cycle > 0 else ""
    return f"{first} \"{modifier}\"{suffix}"


# ===============================
# OFF-BRAND STOCK UNIVERSE
# ===============================
# A comprehensive market simulation with parody stocks across multiple sectors

# Primary tradeable stocks (replacing generic A and B)
PRIMARY_STOCKS = {
    "Chevaco": {  # Chevron + Exxon parody - established chemical/energy
        "sector": "Energy",
        "initial_price": 30.0,
        "volatility": 0.8,
        "description": "Established chemical and energy conglomerate. 10 years in the market.",
        "emoji": "⛽",
        "color": "#f59e0b"
    },
    "ZapTech": {  # Emerging tech startup
        "sector": "Tech",
        "initial_price": 40.0,
        "volatility": 1.3,
        "description": "Fast-growing tech startup. 3 years old, high volatility.",
        "emoji": "⚡",
        "color": "#3b82f6"
    }
}

# Extended universe of off-brand stocks across sectors
STOCK_UNIVERSE = {
    # Tech Giants
    "Pear Inc": {
        "sector": "Tech",
        "initial_price": 175.0,
        "volatility": 1.1,
        "description": "Premium consumer electronics and services company.",
        "emoji": "🍐",
        "color": "#a1a1aa"
    },
    "Macrohard": {
        "sector": "Tech", 
        "initial_price": 145.0,
        "volatility": 0.9,
        "description": "Enterprise software and cloud computing giant.",
        "emoji": "🪟",
        "color": "#0ea5e9"
    },
    "Froogle": {
        "sector": "Tech",
        "initial_price": 128.0,
        "volatility": 1.0,
        "description": "Search engine, advertising, and AI leader.",
        "emoji": "🔍",
        "color": "#22c55e"
    },
    "Feta": {
        "sector": "Tech",
        "initial_price": 62.0,
        "volatility": 1.4,
        "description": "Social media and virtual reality metaverse company.",
        "emoji": "👓",
        "color": "#3b82f6"
    },
    "Tweeter": {
        "sector": "Tech",
        "initial_price": 28.0,
        "volatility": 1.8,
        "description": "Microblogging platform. Volatile since acquisition.",
        "emoji": "🐦",
        "color": "#38bdf8"
    },
    
    # AI & Chips
    "ENVIDIA": {
        "sector": "Semiconductors",
        "initial_price": 480.0,
        "volatility": 1.6,
        "description": "AI chip manufacturer. The backbone of modern AI.",
        "emoji": "🎮",
        "color": "#84cc16"
    },
    "OpenEye": {
        "sector": "AI",
        "initial_price": 200.0,
        "volatility": 1.5,
        "description": "Leading artificial intelligence research company.",
        "emoji": "🤖",
        "color": "#8b5cf6"
    },
    
    # Auto & EV
    "Papa Motors": {
        "sector": "Automotive",
        "initial_price": 38.0,
        "volatility": 1.5,
        "description": "Electric vehicles and clean energy. CEO is... eccentric.",
        "emoji": "🚗",
        "color": "#ef4444"
    },
    "Riviana": {
        "sector": "Automotive",
        "initial_price": 15.0,
        "volatility": 1.7,
        "description": "Electric adventure vehicle startup.",
        "emoji": "🏔️",
        "color": "#f97316"
    },
    
    # E-commerce & Retail
    "Nile Inc": {
        "sector": "Retail",
        "initial_price": 54.0,
        "volatility": 1.05,
        "description": "E-commerce everything store. Cloud services subsidiary.",
        "emoji": "📦",
        "color": "#f59e0b"
    },
    "Wally World": {
        "sector": "Retail",
        "initial_price": 142.0,
        "volatility": 0.7,
        "description": "Brick and mortar retail giant. Steady performer.",
        "emoji": "🏪",
        "color": "#3b82f6"
    },
    
    # Crypto & Finance
    "Pit-Coin": {
        "sector": "Crypto",
        "initial_price": 42.5,
        "volatility": 2.5,
        "description": "The original cryptocurrency. Digital gold or bubble?",
        "emoji": "₿",
        "color": "#f59e0b"
    },
    "Dogey Coin": {
        "sector": "Crypto",
        "initial_price": 0.12,
        "volatility": 3.0,
        "description": "Meme cryptocurrency. Much wow. Very volatile.",
        "emoji": "🐕",
        "color": "#eab308"
    },
    "Boinbase": {
        "sector": "Finance",
        "initial_price": 85.0,
        "volatility": 1.8,
        "description": "Cryptocurrency exchange platform.",
        "emoji": "🏦",
        "color": "#0ea5e9"
    },
    
    # Entertainment & Streaming
    "Netflux": {
        "sector": "Entertainment",
        "initial_price": 420.0,
        "volatility": 1.2,
        "description": "Streaming entertainment pioneer. Content is king.",
        "emoji": "📺",
        "color": "#dc2626"
    },
    "Dizzy": {
        "sector": "Entertainment",
        "initial_price": 95.0,
        "volatility": 0.9,
        "description": "Theme parks, movies, and streaming. Family entertainment.",
        "emoji": "🏰",
        "color": "#3b82f6"
    },
    "Spotifly": {
        "sector": "Entertainment",
        "initial_price": 145.0,
        "volatility": 1.1,
        "description": "Music and podcast streaming platform.",
        "emoji": "🎵",
        "color": "#22c55e"
    },
}

# Sector correlations (stocks in same sector move together)
SECTOR_CORRELATIONS = {
    "Tech": ["Tech", "AI", "Semiconductors"],
    "AI": ["Tech", "AI", "Semiconductors"],
    "Semiconductors": ["Tech", "AI", "Semiconductors"],
    "Crypto": ["Crypto", "Finance"],
    "Finance": ["Crypto", "Finance"],
    "Entertainment": ["Entertainment"],
    "Automotive": ["Automotive", "Energy"],
    "Energy": ["Automotive", "Energy"],
    "Retail": ["Retail"],
}

def get_all_stocks():
    """Get combined dictionary of all stocks."""
    all_stocks = {}
    all_stocks.update(PRIMARY_STOCKS)
    all_stocks.update(STOCK_UNIVERSE)
    return all_stocks

def get_stock_sectors():
    """Get list of unique sectors."""
    all_stocks = get_all_stocks()
    return list(set(s["sector"] for s in all_stocks.values()))

def get_stocks_by_sector(sector: str):
    """Get all stocks in a given sector."""
    all_stocks = get_all_stocks()
    return {name: data for name, data in all_stocks.items() if data["sector"] == sector}


# Legacy compatibility - these still work but now point to the new structure
EXTRA_STOCKS = [
    (name, data["initial_price"]) 
    for name, data in STOCK_UNIVERSE.items()
]

EXTRA_STOCK_VOLATILITY = {
    name: data["volatility"] 
    for name, data in STOCK_UNIVERSE.items()
}


# ===============================
# SIMULATION ENGINE
# ===============================

class SimulationEngine:
    """
    Main simulation engine that manages the market simulation.
    Supports both demo mode (random) and LLM mode (Groq-powered decisions).
    """
    
    def __init__(self):
        self.state = SimulationState()
        self._random = random.Random()
        self._groq_client = None
        self._agent_chat_histories: Dict[int, list] = {}
        self._last_llm_call_time = 0
        self._init_groq()
    
    def _init_groq(self):
        """Initialize Groq client if API key is available."""
        api_key = os.getenv("GROQ_API_KEY", "")
        if api_key and GROQ_AVAILABLE:
            try:
                self._groq_client = Groq(api_key=api_key)
            except Exception as e:
                log.warning(f"Failed to initialize Groq client: {e}")
                self._groq_client = None
    
    def is_llm_available(self) -> bool:
        """Check if LLM mode can be enabled."""
        return self._groq_client is not None
    
    def configure(self, 
                  agent_count: int = 50,
                  total_days: int = 30,
                  volatility: str = "Medium",
                  event_intensity: int = 5,
                  loan_market_enabled: bool = True,
                  random_seed: int = 42,
                  custom_agent: Optional[Dict[str, Any]] = None,
                  manual_events: Optional[List[Dict[str, Any]]] = None,
                  llm_mode: bool = False) -> SimulationState:
        """Configure the simulation parameters.
        
        Args:
            agent_count: Number of agents (1-500)
            total_days: Simulation duration in days (1-365)
            volatility: Market volatility level ("Low", "Medium", "High", "Extreme")
            event_intensity: Event frequency (1-10)
            loan_market_enabled: Whether loan market is active
            random_seed: Seed for reproducibility
            custom_agent: Custom agent configuration dict
            manual_events: List of manually triggered events
            llm_mode: Whether to use LLM-powered agent decisions
            
        Returns:
            Configured SimulationState
            
        Raises:
            ValueError: If parameters are out of valid range
        """
        # Input validation
        if not 1 <= agent_count <= 500:
            raise ValueError(f"agent_count must be between 1 and 500, got {agent_count}")
        if not 1 <= total_days <= 365:
            raise ValueError(f"total_days must be between 1 and 365, got {total_days}")
        if volatility not in ["Low", "Medium", "High", "Extreme"]:
            raise ValueError(f"volatility must be 'Low', 'Medium', 'High', or 'Extreme', got '{volatility}'")
        if not 1 <= event_intensity <= 10:
            raise ValueError(f"event_intensity must be between 1 and 10, got {event_intensity}")
        
        # Validate LLM mode
        if llm_mode and not self.is_llm_available():
            raise ValueError("LLM mode requires a valid GROQ_API_KEY in your .env file")
        if llm_mode and agent_count > 20:
            raise ValueError("LLM mode supports max 20 agents due to API rate limits. Reduce agent count.")
        
        self._random.seed(random_seed)
        random.seed(random_seed)
        
        # Reset LLM chat histories
        self._agent_chat_histories = {}
        
        self.state = SimulationState(
            status="CONFIGURED",
            run_id=f"RUN-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            agent_count=agent_count,
            total_days=total_days,
            volatility=volatility,
            event_intensity=event_intensity,
            loan_market_enabled=loan_market_enabled,
            random_seed=random_seed,
            custom_agent=custom_agent,
            llm_mode=llm_mode,
        )
        
        # Initialize primary stocks (off-brand parodies)
        chevaco = PRIMARY_STOCKS["Chevaco"]
        self.state.stock_a = StockState(
            name="Chevaco",
            price=chevaco["initial_price"],
            initial_price=chevaco["initial_price"],
            price_history=[{"day": 0, "session": 0, "price": chevaco["initial_price"]}]
        )
        
        zaptech = PRIMARY_STOCKS["ZapTech"]
        self.state.stock_b = StockState(
            name="ZapTech", 
            price=zaptech["initial_price"],
            initial_price=zaptech["initial_price"],
            price_history=[{"day": 0, "session": 0, "price": zaptech["initial_price"]}]
        )

        # Initialize extra stocks
        self.state.extra_stocks = [
            StockState(
                name=name,
                price=price,
                initial_price=price,
                price_history=[{"day": 0, "session": 0, "price": price}]
            )
            for name, price in EXTRA_STOCKS
        ]
        
        # Initialize agents
        self.state.agents = []
        characters = ["Conservative", "Aggressive", "Balanced", "Growth-Oriented"]
        
        for i in range(agent_count):
            # Random initial portfolio
            cash = self._random.uniform(100000, 500000)
            stock_a = self._random.randint(50, 500)
            stock_b = self._random.randint(50, 500)
            character = characters[i % len(characters)]
            
            initial_value = cash + stock_a * 30.0 + stock_b * 40.0
            
            # Initialize loans based on character
            loans = []
            if self._random.random() < 0.3:  # 30% chance of initial loan
                loans.append({
                    "loan": "yes",
                    "amount": self._random.uniform(50000, 200000),
                    "loan_type": self._random.randint(0, 2),
                    "repayment_date": self._random.choice([22, 44, 66])
                })
            
            agent = AgentState(
                id=i,
                name=generate_agent_name(i),
                character=character,
                cash=cash,
                stock_a_amount=stock_a,
                stock_b_amount=stock_b,
                total_value=initial_value,
                initial_value=initial_value,
                pnl_percent=0.0,
                loans=loans,
                is_bankrupt=False,
                quit=False,
                herding_level=self._random.choice(["Low", "Medium", "High"]),
                loss_aversion_level=self._random.choice(["Low", "Medium", "High"]),
                overconfidence_level=self._random.choice(["Low", "Medium", "High"]),
                anchoring_level=self._random.choice(["Low", "Medium", "High"]),
            )
            self.state.agents.append(agent)

        # Apply custom agent personalization if provided
        if custom_agent and self.state.agents:
            target = self.state.agents[0]
            display_name = custom_agent.get("display_name") or custom_agent.get("name")
            if display_name:
                target.name = display_name
            if custom_agent.get("character"):
                target.character = custom_agent["character"]
            if custom_agent.get("herding_level"):
                target.herding_level = custom_agent["herding_level"]
            if custom_agent.get("loss_aversion_level"):
                target.loss_aversion_level = custom_agent["loss_aversion_level"]
            if custom_agent.get("overconfidence_level"):
                target.overconfidence_level = custom_agent["overconfidence_level"]
            if custom_agent.get("anchoring_level"):
                target.anchoring_level = custom_agent["anchoring_level"]
        
        # Manual events from UI
        self.state.manual_events = []
        if manual_events:
            for e in manual_events:
                try:
                    self.state.manual_events.append(MarketEvent(**e))
                except Exception:
                    continue

        # Generate events based on intensity (includes manual events)
        self._generate_events()
        
        # Calculate initial metrics
        self._update_metrics()
        
        return self.state
    
    def _generate_events(self):
        """Generate market events based on event intensity."""
        self.state.events = []

        # Start with manually injected events
        if self.state.manual_events:
            self.state.events.extend(self.state.manual_events)
        
        # Base events that always happen
        base_events = [
            MarketEvent(
                day=max(1, self.state.total_days // 4),
                event_type="macro",
                title="Interest Rate Decision",
                description="Central bank announces monetary policy decision",
                severity="MEDIUM",
                impact="Market volatility expected around announcement"
            ),
            MarketEvent(
                day=max(1, self.state.total_days // 2),
                event_type="corporate",
                title="Earnings Season",
                description="Major companies release quarterly earnings",
                severity="MEDIUM", 
                impact="Stock-specific movements expected"
            ),
        ]
        
        self.state.events.extend(base_events)
        
        # Additional events based on intensity
        num_additional = self.state.event_intensity - 2
        
        event_templates = [
            ("macro", "Policy Announcement", "Government announces new economic policy", "HIGH"),
            ("macro", "Trade Agreement", "New international trade deal signed", "MEDIUM"),
            ("sentiment", "Market Sentiment Shift", "Investor sentiment turns cautious", "MEDIUM"),
            ("sentiment", "Social Media Buzz", "Viral discussion affects market perception", "LOW"),
            ("corporate", "M&A Announcement", "Major merger/acquisition announced", "HIGH"),
            ("corporate", "Product Launch", "Company announces new product line", "LOW"),
            ("macro", "Economic Data Release", "Key economic indicators published", "MEDIUM"),
            ("sentiment", "Analyst Downgrade", "Major analyst downgrades sector outlook", "MEDIUM"),
        ]
        
        used_days = set(e.day for e in self.state.events)
        
        for i in range(max(0, num_additional)):
            template = self._random.choice(event_templates)
            
            # Find unused day
            day = self._random.randint(1, self.state.total_days)
            attempts = 0
            while day in used_days and attempts < 20:
                day = self._random.randint(1, self.state.total_days)
                attempts += 1
            
            used_days.add(day)
            
            self.state.events.append(MarketEvent(
                day=day,
                event_type=template[0],
                title=template[1],
                description=template[2],
                severity=template[3],
                impact=f"Expected {template[3].lower()} impact on market dynamics"
            ))
        
        # Sort by day
        self.state.events.sort(key=lambda e: e.day)

    def add_manual_event(self, event: MarketEvent):
        """Add a manual event and include it in the active event list."""
        self.state.manual_events.append(event)
        self.state.events.append(event)
        self.state.events.sort(key=lambda e: e.day)
    
    def _update_metrics(self):
        """Update simulation metrics based on current state."""
        active = [a for a in self.state.agents if not a.quit and not a.is_bankrupt]
        self.state.active_agents = len(active)
        
        if active:
            self.state.total_capital = sum(a.total_value for a in active)
            
            # Calculate herding percentage
            characters = [a.character for a in active]
            most_common = max(set(characters), key=characters.count)
            self.state.herding_percentage = (characters.count(most_common) / len(active)) * 100
            
            # Determine market sentiment from price trends
            if self.state.stock_a and len(self.state.stock_a.price_history) > 1:
                recent_prices = [p["price"] for p in self.state.stock_a.price_history[-5:]]
                if len(recent_prices) >= 2:
                    trend = recent_prices[-1] - recent_prices[0]
                    if trend > 1:
                        self.state.market_sentiment = "bullish"
                    elif trend < -1:
                        self.state.market_sentiment = "bearish"
                    else:
                        self.state.market_sentiment = "neutral"
            
            # Calculate system risk
            volatility_scores = {"Low": 1, "Medium": 2, "High": 3, "Extreme": 4}
            vol_score = volatility_scores.get(self.state.volatility, 2)
            
            bankruptcies = len([a for a in self.state.agents if a.is_bankrupt])
            bankruptcy_rate = bankruptcies / self.state.agent_count
            
            risk_score = vol_score + (self.state.event_intensity / 3) + (bankruptcy_rate * 5)
            
            if risk_score < 4:
                self.state.system_risk = "LOW"
            elif risk_score < 7:
                self.state.system_risk = "ELEVATED"
            else:
                self.state.system_risk = "HIGH"
    
    def run_day(self) -> SimulationState:
        """Run a single simulation day (all sessions)."""
        if self.state.status not in ["CONFIGURED", "RUNNING", "PAUSED"]:
            return self.state
        
        self.state.status = "RUNNING"
        self.state.current_day += 1
        
        # Check for events today
        today_events = [e for e in self.state.events if e.day == self.state.current_day]
        
        # Volatility multiplier based on settings and events
        volatility_mult = {
            "Low": 0.01,
            "Medium": 0.02,
            "High": 0.035,
            "Extreme": 0.05
        }.get(self.state.volatility, 0.02)
        
        # Increase volatility on event days
        if today_events:
            volatility_mult *= 1.5
        
        # Run 3 trading sessions
        for session in range(1, 4):
            self.state.current_session = session
            self._run_session(volatility_mult, today_events)
        
        # End of day processing
        self._process_end_of_day()
        
        # Generate forum messages (BBS)
        self._generate_forum_messages()

        # Save snapshot for rewind
        self._save_snapshot()
        
        # Check if simulation is complete
        if self.state.current_day >= self.state.total_days:
            self.state.status = "COMPLETED"
        
        return self.state
    
    def _run_session(self, volatility_mult: float, events: List[MarketEvent]):
        """Run a single trading session."""
        
        # Update stock prices with random walk + event impact
        event_impact = 0
        if events:
            for event in events:
                if event.severity == "HIGH":
                    event_impact = self._random.uniform(-0.03, 0.03)
                elif event.severity == "MEDIUM":
                    event_impact = self._random.uniform(-0.015, 0.015)
                else:
                    event_impact = self._random.uniform(-0.005, 0.005)
        
        # Stock A price update
        change_a = self._random.gauss(0, volatility_mult) + event_impact * 0.7
        self.state.stock_a.price = max(1, self.state.stock_a.price * (1 + change_a))
        self.state.stock_a.price_history.append({
            "day": self.state.current_day,
            "session": self.state.current_session,
            "price": self.state.stock_a.price
        })
        
        # Stock B price update (more volatile)
        change_b = self._random.gauss(0, volatility_mult * 1.3) + event_impact
        self.state.stock_b.price = max(1, self.state.stock_b.price * (1 + change_b))
        self.state.stock_b.price_history.append({
            "day": self.state.current_day,
            "session": self.state.current_session,
            "price": self.state.stock_b.price
        })

        # Extra stocks price update
        for stock in self.state.extra_stocks:
            mult = EXTRA_STOCK_VOLATILITY.get(stock.name, 1.0)
            change = self._random.gauss(0, volatility_mult * mult) + event_impact * 0.6
            stock.price = max(1, stock.price * (1 + change))
            stock.price_history.append({
                "day": self.state.current_day,
                "session": self.state.current_session,
                "price": stock.price
            })
        
        # Simulate agent trading
        active_agents = [a for a in self.state.agents if not a.quit and not a.is_bankrupt]
        self._random.shuffle(active_agents)
        
        for agent in active_agents:
            if self.state.llm_mode and self._groq_client:
                self._llm_agent_action(agent)
            else:
                self._simulate_agent_action(agent)
        
        # Update agent values
        for agent in self.state.agents:
            if not agent.quit:
                agent.total_value = (
                    agent.cash + 
                    agent.stock_a_amount * self.state.stock_a.price +
                    agent.stock_b_amount * self.state.stock_b.price
                )
                agent.pnl_percent = ((agent.total_value - agent.initial_value) / agent.initial_value) * 100
    
    def _simulate_agent_action(self, agent: AgentState):
        """Simulate a trading action for an agent (without LLM)."""
        
        # Decision based on character and market conditions
        action_prob = self._random.random()
        
        # Character-based trading tendency
        if agent.character == "Conservative":
            buy_threshold = 0.7
            sell_threshold = 0.2
            trade_size_mult = 0.1
        elif agent.character == "Aggressive":
            buy_threshold = 0.4
            sell_threshold = 0.5
            trade_size_mult = 0.3
        elif agent.character == "Growth-Oriented":
            buy_threshold = 0.5
            sell_threshold = 0.3
            trade_size_mult = 0.2
        else:  # Balanced
            buy_threshold = 0.55
            sell_threshold = 0.35
            trade_size_mult = 0.15
        
        # Adjust based on market sentiment
        if self.state.market_sentiment == "bullish":
            buy_threshold -= 0.1
        elif self.state.market_sentiment == "bearish":
            sell_threshold += 0.1
        
        # Determine action
        if action_prob > buy_threshold and agent.cash > 1000:
            # Buy
            stock = "A" if self._random.random() > 0.4 else "B"
            price = self.state.stock_a.price if stock == "A" else self.state.stock_b.price
            max_amount = int((agent.cash * trade_size_mult) / price)
            
            if max_amount > 0:
                amount = self._random.randint(1, max(1, max_amount))
                cost = amount * price
                
                if cost <= agent.cash:
                    agent.cash -= cost
                    if stock == "A":
                        agent.stock_a_amount += amount
                    else:
                        agent.stock_b_amount += amount
                    
                    agent.action_history.append({
                        "day": self.state.current_day,
                        "session": self.state.current_session,
                        "action": "BUY",
                        "stock": stock,
                        "amount": amount,
                        "price": price,
                        "reasoning": self._generate_reasoning(agent, "BUY", stock)
                    })
                    
        elif action_prob < sell_threshold:
            # Sell
            stock = "A" if self._random.random() > 0.4 else "B"
            holdings = agent.stock_a_amount if stock == "A" else agent.stock_b_amount
            
            if holdings > 0:
                amount = self._random.randint(1, max(1, int(holdings * trade_size_mult)))
                price = self.state.stock_a.price if stock == "A" else self.state.stock_b.price
                
                if stock == "A":
                    agent.stock_a_amount -= amount
                else:
                    agent.stock_b_amount -= amount
                agent.cash += amount * price
                
                agent.action_history.append({
                    "day": self.state.current_day,
                    "session": self.state.current_session,
                    "action": "SELL",
                    "stock": stock,
                    "amount": amount,
                    "price": price,
                    "reasoning": self._generate_reasoning(agent, "SELL", stock)
                })
    
    def _generate_reasoning(self, agent: AgentState, action: str, stock: str) -> str:
        """Generate a reasoning explanation for an agent's action."""
        
        reasons = {
            "BUY": [
                f"Bullish on {stock} based on recent price momentum",
                f"Undervalued relative to fundamentals",
                f"Following market sentiment indicators",
                f"Portfolio rebalancing - increasing {stock} exposure",
                f"Technical indicators suggest upward trend",
                f"Contrarian play after recent dip",
            ],
            "SELL": [
                f"Taking profits on {stock} position",
                f"Risk management - reducing exposure",
                f"Bearish outlook based on macro conditions",
                f"Portfolio rebalancing - decreasing {stock} weight",
                f"Stop-loss triggered by price movement",
                f"Liquidity needs for other opportunities",
            ]
        }
        
        base_reason = self._random.choice(reasons.get(action, ["Market analysis"]))
        
        # Add character-specific context
        if agent.character == "Conservative":
            base_reason += " (conservative risk approach)"
        elif agent.character == "Aggressive":
            base_reason += " (aggressive growth strategy)"
        
        return base_reason
    
    def _call_groq(self, agent_id: int, prompt: str) -> str:
        """Call Groq API with rate limiting (max ~25/min to stay safe)."""
        if not self._groq_client:
            return ""
        
        # Rate limit: at least 2.5s between calls
        now = time.time()
        elapsed = now - self._last_llm_call_time
        if elapsed < 2.5:
            time.sleep(2.5 - elapsed)
        
        # Manage per-agent chat history
        if agent_id not in self._agent_chat_histories:
            self._agent_chat_histories[agent_id] = []
        
        history = self._agent_chat_histories[agent_id]
        history.append({"role": "user", "content": prompt})
        
        # Keep history manageable (last 6 messages)
        if len(history) > 6:
            history = history[-6:]
            self._agent_chat_histories[agent_id] = history
        
        try:
            response = self._groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=history,
                temperature=0.8,
                max_tokens=300,
            )
            reply = response.choices[0].message.content or ""
            history.append({"role": "assistant", "content": reply})
            self._last_llm_call_time = time.time()
            self.state.llm_calls_made += 1
            return reply
        except Exception as e:
            log.warning(f"Groq API error for agent {agent_id}: {e}")
            time.sleep(3)  # Back off on error
            return ""
    
    def _llm_agent_action(self, agent: AgentState):
        """Use LLM (Groq) to decide an agent's trading action."""
        
        # Build context-rich prompt
        recent_events = [e for e in self.state.events if e.day >= max(1, self.state.current_day - 2)]
        events_text = "; ".join([f"{e.title} ({e.severity})" for e in recent_events[-3:]]) or "No major events"
        
        # Recent forum sentiment
        recent_msgs = [m for m in self.state.forum_messages if m.day >= max(1, self.state.current_day - 1)]
        forum_text = "; ".join([f"{m.agent_name}: {m.message}" for m in recent_msgs[-3:]]) or "No forum chatter"
        
        # Price trends
        stock_a_prices = [p["price"] for p in (self.state.stock_a.price_history or [])[-6:]]
        stock_b_prices = [p["price"] for p in (self.state.stock_b.price_history or [])[-6:]]
        
        a_trend = "rising" if len(stock_a_prices) >= 2 and stock_a_prices[-1] > stock_a_prices[0] else "falling" if len(stock_a_prices) >= 2 else "stable"
        b_trend = "rising" if len(stock_b_prices) >= 2 and stock_b_prices[-1] > stock_b_prices[0] else "falling" if len(stock_b_prices) >= 2 else "stable"
        
        prompt = f"""You are a stock trading agent in a market simulation.

Your profile:
- Name: {agent.name}
- Strategy: {agent.character}
- Cash: ${agent.cash:,.0f}
- {self.state.stock_a.name} holdings: {agent.stock_a_amount} shares @ ${self.state.stock_a.price:.2f} (trend: {a_trend})
- {self.state.stock_b.name} holdings: {agent.stock_b_amount} shares @ ${self.state.stock_b.price:.2f} (trend: {b_trend})
- Portfolio P&L: {agent.pnl_percent:+.1f}%

Market context:
- Day {self.state.current_day}, Session {self.state.current_session}/3
- Volatility: {self.state.volatility}
- Sentiment: {self.state.market_sentiment}
- Recent events: {events_text}
- Forum chatter: {forum_text}

Decide your action. Respond with ONLY a JSON object (no explanation):
{{
  "action_type": "buy" | "sell" | "hold",
  "stock": "A" | "B",
  "amount": <integer number of shares>,
  "reasoning": "<one sentence>"
}}

Rules:
- You can only buy if you have enough cash
- You can only sell shares you own
- Amount must be a positive integer
- If unsure, choose hold"""
        
        resp = self._call_groq(agent.id, prompt)
        if not resp:
            return  # API failed, skip this agent
        
        # Parse LLM response
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_str = resp
            if "```" in json_str:
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            json_str = json_str.strip()
            
            action = json.loads(json_str)
            action_type = action.get("action_type", "hold").lower()
            stock = action.get("stock", "A").upper()
            amount = int(action.get("amount", 0))
            reasoning = action.get("reasoning", "LLM decision")
            
            if stock not in ["A", "B"]:
                stock = "A"
            
            price = self.state.stock_a.price if stock == "A" else self.state.stock_b.price
            
            if action_type == "buy" and amount > 0:
                cost = amount * price
                if cost <= agent.cash:
                    agent.cash -= cost
                    if stock == "A":
                        agent.stock_a_amount += amount
                    else:
                        agent.stock_b_amount += amount
                    
                    agent.action_history.append({
                        "day": self.state.current_day,
                        "session": self.state.current_session,
                        "action": "BUY",
                        "stock": stock,
                        "amount": amount,
                        "price": price,
                        "reasoning": f"[LLM] {reasoning}"
                    })
                    
            elif action_type == "sell" and amount > 0:
                holdings = agent.stock_a_amount if stock == "A" else agent.stock_b_amount
                amount = min(amount, holdings)  # Can't sell more than held
                
                if amount > 0:
                    if stock == "A":
                        agent.stock_a_amount -= amount
                    else:
                        agent.stock_b_amount -= amount
                    agent.cash += amount * price
                    
                    agent.action_history.append({
                        "day": self.state.current_day,
                        "session": self.state.current_session,
                        "action": "SELL",
                        "stock": stock,
                        "amount": amount,
                        "price": price,
                        "reasoning": f"[LLM] {reasoning}"
                    })
                    
            # else: hold — no action needed
            
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            log.warning(f"Failed to parse LLM response for agent {agent.id}: {e}")
            # Fall back to demo behavior for this agent
            self._simulate_agent_action(agent)
    
    def _process_end_of_day(self):
        """Process end-of-day activities."""
        
        # Check for loan repayments
        if self.state.loan_market_enabled:
            for agent in self.state.agents:
                if agent.quit or agent.is_bankrupt:
                    continue
                
                for loan in agent.loans[:]:
                    if loan.get("repayment_date") == self.state.current_day:
                        repayment = loan["amount"] * 1.03  # 3% interest
                        agent.cash -= repayment
                        agent.loans.remove(loan)
                        
                        if agent.cash < 0:
                            # Bankruptcy check
                            total_stock_value = (
                                agent.stock_a_amount * self.state.stock_a.price +
                                agent.stock_b_amount * self.state.stock_b.price
                            )
                            if total_stock_value + agent.cash < 0:
                                agent.is_bankrupt = True
                            else:
                                # Forced liquidation
                                self._force_liquidation(agent)
        
        # Update metrics
        self._update_metrics()
    
    def _force_liquidation(self, agent: AgentState):
        """Force liquidation of agent's positions to cover debt."""
        while agent.cash < 0 and (agent.stock_a_amount > 0 or agent.stock_b_amount > 0):
            if agent.stock_a_amount > 0:
                sell_amount = min(agent.stock_a_amount, 
                                 max(1, int(-agent.cash / self.state.stock_a.price) + 1))
                agent.stock_a_amount -= sell_amount
                agent.cash += sell_amount * self.state.stock_a.price
            elif agent.stock_b_amount > 0:
                sell_amount = min(agent.stock_b_amount,
                                 max(1, int(-agent.cash / self.state.stock_b.price) + 1))
                agent.stock_b_amount -= sell_amount
                agent.cash += sell_amount * self.state.stock_b.price
    
    def _generate_forum_messages(self):
        """Generate BBS forum messages for the day."""
        
        # Select random agents to post
        active_agents = [a for a in self.state.agents if not a.quit and not a.is_bankrupt]
        posters = self._random.sample(active_agents, min(5, len(active_agents)))
        
        if self.state.llm_mode and self._groq_client:
            # LLM-generated forum messages (only for 2-3 agents to save API calls)
            llm_posters = posters[:2]
            for agent in llm_posters:
                prompt = f"""You are {agent.name}, a {agent.character} trader. Day {self.state.current_day} just ended.
Your P&L is {agent.pnl_percent:+.1f}%. Market sentiment: {self.state.market_sentiment}.
Write a short 1-sentence forum post about the market (casual trader talk). No JSON, just the message."""
                resp = self._call_groq(agent.id, prompt)
                if resp:
                    sentiment = "bullish" if agent.pnl_percent > 5 else "bearish" if agent.pnl_percent < -5 else "neutral"
                    self.state.forum_messages.append(ForumMessage(
                        day=self.state.current_day,
                        agent_id=agent.id,
                        agent_name=agent.name,
                        message=resp.strip().strip('"'),
                        sentiment=sentiment
                    ))
            # Fill rest with template messages
            remaining = [a for a in posters if a not in llm_posters]
            self._generate_template_forum(remaining)
            return
        
        self._generate_template_forum(posters)
    
    def _generate_template_forum(self, posters: List[AgentState]):
        """Generate template-based forum messages."""
        
        message_templates = {
            "bullish": [
                "Market looking strong today! 📈",
                "Great buying opportunity in the current dip",
                "Technical indicators are all pointing up",
                "Fundamentals remain solid despite volatility",
                "Loading up on more shares today",
            ],
            "bearish": [
                "Taking some profits here, be careful 📉",
                "Market seems overextended, staying cautious",
                "Not liking the macro headwinds",
                "Reducing exposure until clarity improves",
                "Seeing some warning signs in the charts",
            ],
            "neutral": [
                "Holding steady, watching the market closely",
                "Mixed signals today, staying patient",
                "Waiting for better entry points",
                "No major moves planned for now",
                "Keeping powder dry for opportunities",
            ]
        }
        
        for agent in posters:
            # Sentiment based on recent performance
            if agent.pnl_percent > 5:
                sentiment = "bullish"
            elif agent.pnl_percent < -5:
                sentiment = "bearish"
            else:
                sentiment = "neutral"
            
            message = self._random.choice(message_templates[sentiment])
            
            self.state.forum_messages.append(ForumMessage(
                day=self.state.current_day,
                agent_id=agent.id,
                agent_name=agent.name,
                message=message,
                sentiment=sentiment
            ))
    
    def pause(self):
        """Pause the simulation."""
        if self.state.status == "RUNNING":
            self.state.status = "PAUSED"
        return self.state
    
    def resume(self):
        """Resume the simulation."""
        if self.state.status == "PAUSED":
            self.state.status = "RUNNING"
        return self.state
    
    def reset(self):
        """Reset the simulation."""
        self.state = SimulationState()
        return self.state
    
    def get_state(self) -> SimulationState:
        """Get the current simulation state."""
        return self.state
    
    def get_agent(self, agent_id: int) -> Optional[AgentState]:
        """Get a specific agent by ID."""
        for agent in self.state.agents:
            if agent.id == agent_id:
                return agent
        return None
    
    def get_price_history_df(self):
        """Get price history as a format suitable for charts."""
        if not self.state.stock_a or not self.state.stock_b:
            return None
        
        # Get unique days
        days = sorted(set(p["day"] for p in self.state.stock_a.price_history))
        
        # Get end-of-day prices
        price_a = []
        price_b = []
        
        for day in days:
            day_prices_a = [p["price"] for p in self.state.stock_a.price_history if p["day"] == day]
            day_prices_b = [p["price"] for p in self.state.stock_b.price_history if p["day"] == day]
            
            price_a.append(day_prices_a[-1] if day_prices_a else None)
            price_b.append(day_prices_b[-1] if day_prices_b else None)
        
        extra = {}
        for stock in self.state.extra_stocks:
            series = []
            for day in days:
                day_prices = [p["price"] for p in stock.price_history if p["day"] == day]
                series.append(day_prices[-1] if day_prices else None)
            extra[stock.name] = series

        return {
            "days": days,
            "stock_a": price_a,
            "stock_b": price_b,
            "extra_stocks": extra
        }
    
    def get_strategy_performance(self):
        """Get performance breakdown by strategy type."""
        strategies = {}
        
        for agent in self.state.agents:
            if agent.character not in strategies:
                strategies[agent.character] = {
                    "agents": [],
                    "total_pnl": 0,
                    "avg_pnl": 0,
                    "count": 0
                }
            
            strategies[agent.character]["agents"].append(agent)
            strategies[agent.character]["total_pnl"] += agent.pnl_percent
            strategies[agent.character]["count"] += 1
        
        for strategy in strategies.values():
            if strategy["count"] > 0:
                strategy["avg_pnl"] = strategy["total_pnl"] / strategy["count"]
        
        return strategies
    
    def get_today_events(self) -> List[MarketEvent]:
        """Get events for the current day."""
        return [e for e in self.state.events if e.day == self.state.current_day]
    
    def get_recent_messages(self, count: int = 10) -> List[ForumMessage]:
        """Get the most recent forum messages."""
        return self.state.forum_messages[-count:]

    def _save_snapshot(self):
        """Save a deep snapshot of the current state for rewind."""
        snapshot = {
            "day": self.state.current_day,
            "state": copy.deepcopy(self.state)
        }
        self.state.snapshots.append(snapshot)
        # Keep last 60 snapshots to limit memory
        if len(self.state.snapshots) > 60:
            self.state.snapshots = self.state.snapshots[-60:]

    def rewind_to_day(self, day: int) -> SimulationState:
        """Rewind simulation state to a previous day if snapshot exists."""
        candidates = [s for s in self.state.snapshots if s["day"] == day]
        if not candidates:
            return self.state
        self.state = copy.deepcopy(candidates[-1]["state"])
        return self.state


# ===============================
# SINGLETON INSTANCE
# ===============================

_engine_instance: Optional[SimulationEngine] = None

def get_engine() -> SimulationEngine:
    """Get or create the simulation engine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = SimulationEngine()
    return _engine_instance

def reset_engine() -> SimulationEngine:
    """Reset the simulation engine."""
    global _engine_instance
    _engine_instance = SimulationEngine()
    return _engine_instance
