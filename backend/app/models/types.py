from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime


# ═══════════════════════════════════════════════════════════════
#  ENUMS
# ═══════════════════════════════════════════════════════════════

class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(str, Enum):
    LIMIT = "limit"
    MARKET = "market"

class OrderStatus(str, Enum):
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"

class LoanStatus(str, Enum):
    ACTIVE = "active"
    REPAID = "repaid"
    DEFAULTED = "defaulted"


# ═══════════════════════════════════════════════════════════════
#  CORE TRADING MODELS
# ═══════════════════════════════════════════════════════════════

class Order(BaseModel):
    id: str
    agent_id: str
    stock_symbol: str
    side: OrderSide
    type: OrderType
    price: float
    quantity: int
    filled_quantity: int = 0
    status: OrderStatus = OrderStatus.OPEN
    timestamp: Optional[datetime] = None

    def model_post_init(self, __context):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class Trade(BaseModel):
    trade_id: str
    buy_order_id: str
    sell_order_id: str
    buyer_agent_id: str
    seller_agent_id: str
    stock_symbol: str
    price: float
    quantity: int
    timestamp: Optional[datetime] = None

    def model_post_init(self, __context):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class MarketDepth(BaseModel):
    price: float
    quantity: int

class MarketState(BaseModel):
    symbol: str
    bids: List[MarketDepth]
    asks: List[MarketDepth]
    last_price: Optional[float] = None


# ═══════════════════════════════════════════════════════════════
#  STOCK METADATA
# ═══════════════════════════════════════════════════════════════

class StockMeta(BaseModel):
    symbol: str
    name: str
    sector: str
    initial_price: float
    volatility_multiplier: float = 1.0
    emoji: str = "📈"


# ═══════════════════════════════════════════════════════════════
#  MARKET EVENT & FORUM
# ═══════════════════════════════════════════════════════════════

class MarketEvent(BaseModel):
    id: str
    day: int
    session: int = 1
    title: str
    description: str
    severity: str  # LOW, MEDIUM, HIGH
    event_type: str
    impact_pct: float = 0.0
    affected_stocks: List[str] = Field(default_factory=list)

class ForumMessage(BaseModel):
    agent_id: str
    agent_name: str
    message: str
    sentiment: str  # bullish, bearish, neutral
    day: int
    timestamp: Optional[datetime] = None

    def model_post_init(self, __context):
        if self.timestamp is None:
            self.timestamp = datetime.now()


# ═══════════════════════════════════════════════════════════════
#  LOAN SYSTEM
# ═══════════════════════════════════════════════════════════════

LOAN_TERMS = [
    {"term_days": 22, "rate": 0.027, "label": "22-day (2.7%)"},
    {"term_days": 44, "rate": 0.030, "label": "44-day (3.0%)"},
    {"term_days": 66, "rate": 0.033, "label": "66-day (3.3%)"},
]

class Loan(BaseModel):
    id: str
    agent_id: str
    amount: float
    interest_rate: float
    term_days: int
    start_day: int
    due_day: int
    remaining: float
    status: LoanStatus = LoanStatus.ACTIVE


# ═══════════════════════════════════════════════════════════════
#  FINANCIAL REPORTS
# ═══════════════════════════════════════════════════════════════

REPORT_DAYS = [12, 78, 144, 210]

class FinancialReport(BaseModel):
    stock_symbol: str
    day: int
    quarter: int
    revenue_growth: float      # YoY %
    gross_margin: float        # %
    net_profit_millions: float
    cash_flow_millions: float
    sentiment_score: float     # -1.0 to 1.0


# ═══════════════════════════════════════════════════════════════
#  AGENT SNAPSHOTS & ANALYTICS
# ═══════════════════════════════════════════════════════════════

class AgentSnapshot(BaseModel):
    id: str
    name: str
    character_type: str
    agent_kind: str = "llm"    # "llm" or "rule"
    cash: float
    holdings: Dict[str, int]
    pnl: float
    pnl_pct: float
    total_value: float
    trades: int = 0
    status: str = "active"
    debt: float = 0.0

class AgentAnalytics(BaseModel):
    agent_id: str
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    avg_trade_size: float = 0.0
    total_trades: int = 0


# ═══════════════════════════════════════════════════════════════
#  SIMULATION SNAPSHOTS (REWIND)
# ═══════════════════════════════════════════════════════════════

class DaySnapshot(BaseModel):
    day: int
    prices: Dict[str, float]
    agent_summaries: List[Dict]
    total_trades: int
    events_count: int


# ═══════════════════════════════════════════════════════════════
#  PRICE HISTORY
# ═══════════════════════════════════════════════════════════════

class PricePoint(BaseModel):
    time: str
    price: float
    day: int
    session: int


# ═══════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════

class SimulationConfig(BaseModel):
    num_agents: int = Field(default=10, ge=2, le=100)
    num_days: int = Field(default=30, ge=1, le=264)
    volatility: str = "Medium"
    event_intensity: int = Field(default=5, ge=1, le=10)
    use_llm: bool = True
    enable_loans: bool = True
    speed: float = Field(default=2.0, ge=0.1, le=30.0)
    seed: Optional[int] = None


# ═══════════════════════════════════════════════════════════════
#  EVENT INJECTION (REQUEST BODY)
# ═══════════════════════════════════════════════════════════════

class EventInjection(BaseModel):
    title: str = "Custom Event"
    description: str = ""
    severity: str = "MEDIUM"
    impact_pct: float = 0.0
    affected_stocks: List[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
#  CHAT REQUEST
# ═══════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    message: str


# ═══════════════════════════════════════════════════════════════
#  CUSTOM AGENT REQUEST
# ═══════════════════════════════════════════════════════════════

class CustomAgentRequest(BaseModel):
    name: str
    character_type: str = "Balanced"
    risk_tolerance: str = "Medium"
    description: str = ""
    initial_cash: float = Field(default=100000, ge=10000, le=500000)
    use_llm: bool = False
