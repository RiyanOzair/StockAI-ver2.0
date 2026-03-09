"""
Global simulation state — single source of truth.
Holds market books, agents, simulation loop, chatbot engine, and the 25-stock universe.
Imported by API routers.
"""
import logging
import random
from typing import Dict, List, Optional

from backend.app.engine.order_book import OrderBook
from backend.app.engine.simulation_loop import SimulationLoop
from backend.app.agents.behavioral_agent import (
    BehavioralAgent, RuleBasedAgent, AGENT_PERSONAS, CHARACTER_LIST, BaseAgent,
)
from backend.app.models.types import StockMeta

logger = logging.getLogger("state")

# ═══════════════════════════════════════════════════════════════
#  25-STOCK UNIVERSE  (parody names)
# ═══════════════════════════════════════════════════════════════

STOCKS: Dict[str, StockMeta] = {
    # ── Tech (6) ──
    "A": StockMeta(symbol="A", name="Mapple",       sector="Tech",          initial_price=150, volatility_multiplier=1.0, emoji="🍏"),
    "B": StockMeta(symbol="B", name="Macrosoft",     sector="Tech",          initial_price=140, volatility_multiplier=0.9, emoji="💻"),
    "C": StockMeta(symbol="C", name="Goggle",        sector="Tech",          initial_price=130, volatility_multiplier=1.1, emoji="🔍"),
    "D": StockMeta(symbol="D", name="Amozn",         sector="Tech",          initial_price=160, volatility_multiplier=1.2, emoji="📦"),
    "E": StockMeta(symbol="E", name="Nvidious",      sector="Tech",          initial_price=180, volatility_multiplier=1.5, emoji="🎮"),
    "F": StockMeta(symbol="F", name="Metabook",      sector="Tech",          initial_price=110, volatility_multiplier=1.3, emoji="👤"),
    # ── Energy (4) ──
    "G": StockMeta(symbol="G", name="Chevaco",       sector="Energy",        initial_price=100, volatility_multiplier=0.8, emoji="⛽"),
    "H": StockMeta(symbol="H", name="PetroNova",     sector="Energy",        initial_price=95,  volatility_multiplier=0.8, emoji="🛢️"),
    "I": StockMeta(symbol="I", name="ShellShock",    sector="Energy",        initial_price=85,  volatility_multiplier=0.9, emoji="🐚"),
    "J": StockMeta(symbol="J", name="SunRun Solar",  sector="Energy",        initial_price=45,  volatility_multiplier=1.4, emoji="☀️"),
    # ── Finance (4) ──
    "K": StockMeta(symbol="K", name="Goldmine Stacks",sector="Finance",      initial_price=120, volatility_multiplier=0.7, emoji="🏦"),
    "L": StockMeta(symbol="L", name="JPMorgana",     sector="Finance",       initial_price=130, volatility_multiplier=0.7, emoji="💰"),
    "M": StockMeta(symbol="M", name="Bankrupt of America",sector="Finance",  initial_price=40,  volatility_multiplier=0.9, emoji="🏛️"),
    "N": StockMeta(symbol="N", name="Visa-Versa",    sector="Finance",       initial_price=110, volatility_multiplier=0.6, emoji="💳"),
    # ── Auto (3) ──
    "O": StockMeta(symbol="O", name="Tesloid",       sector="Auto",          initial_price=200, volatility_multiplier=1.6, emoji="🚗"),
    "P": StockMeta(symbol="P", name="Fjord Motors",  sector="Auto",          initial_price=35,  volatility_multiplier=1.0, emoji="🏎️"),
    "Q": StockMeta(symbol="Q", name="Toyoda",        sector="Auto",          initial_price=90,  volatility_multiplier=0.8, emoji="🚙"),
    # ── Retail (4) ──
    "R": StockMeta(symbol="R", name="Bullmart",      sector="Retail",        initial_price=75,  volatility_multiplier=0.7, emoji="🛒"),
    "S": StockMeta(symbol="S", name="Costbro",       sector="Retail",        initial_price=95,  volatility_multiplier=0.6, emoji="🏪"),
    "T": StockMeta(symbol="T", name="McRonalds",     sector="Retail",        initial_price=80,  volatility_multiplier=0.5, emoji="🍔"),
    "U": StockMeta(symbol="U", name="Starbooks",     sector="Retail",        initial_price=60,  volatility_multiplier=0.9, emoji="☕"),
    # ── Entertainment (4) ──
    "V": StockMeta(symbol="V", name="Netflux",       sector="Entertainment", initial_price=120, volatility_multiplier=1.3, emoji="📺"),
    "W": StockMeta(symbol="W", name="Dizney",        sector="Entertainment", initial_price=85,  volatility_multiplier=1.0, emoji="🎬"),
    "X": StockMeta(symbol="X", name="Spotifly",      sector="Entertainment", initial_price=70,  volatility_multiplier=1.2, emoji="🎵"),
    "Y": StockMeta(symbol="Y", name="Snapchatter",   sector="Entertainment", initial_price=25,  volatility_multiplier=1.8, emoji="👻"),
}

ALL_SYMBOLS = sorted(STOCKS.keys())


# ═══════════════════════════════════════════════════════════════
#  GLOBAL MUTABLE STATE
# ═══════════════════════════════════════════════════════════════

market_books: Dict[str, OrderBook] = {}
agents: List[BaseAgent] = []
simulation: Optional[SimulationLoop] = None
chat_engine = None  # Optional ChatEngine, initialized lazily


# ═══════════════════════════════════════════════════════════════
#  WORLD BUILDER
# ═══════════════════════════════════════════════════════════════

def _random_holdings(symbols: List[str], budget_hint: float) -> Dict[str, int]:
    """Give a random subset of stocks to an agent."""
    count = random.randint(2, min(6, len(symbols)))
    chosen = random.sample(symbols, count)
    holdings: Dict[str, int] = {}
    for sym in chosen:
        price = STOCKS[sym].initial_price
        max_qty = max(1, int(budget_hint * 0.06 / price))
        holdings[sym] = random.randint(1, max_qty)
    return holdings


def _build_world(config: Optional[dict] = None):
    """Tear down and rebuild entire simulation state."""
    global market_books, agents, simulation

    cfg = config or {}
    num_agents = cfg.get("num_agents", 10)
    use_llm = cfg.get("use_llm", True)
    seed = cfg.get("seed")

    if seed is not None:
        random.seed(seed)

    # ── Order books ──
    market_books = {sym: OrderBook(sym) for sym in STOCKS}
    for sym, meta in STOCKS.items():
        market_books[sym].last_price = meta.initial_price

    initial_prices = {sym: meta.initial_price for sym, meta in STOCKS.items()}

    # ── Agent split: 40 % LLM / 60 % rule-based (when use_llm=True) ──
    llm_count = max(1, round(num_agents * 0.4)) if use_llm else 0
    rule_count = num_agents - llm_count

    agents = []
    agent_idx = 0

    # LLM agents — cycle through named personas
    for i in range(llm_count):
        persona = AGENT_PERSONAS[i % len(AGENT_PERSONAS)].copy()
        if i >= len(AGENT_PERSONAS):
            persona["name"] = f"{persona['name']}_{i}"
        cash = round(random.uniform(80_000, 200_000), 2)
        holdings = _random_holdings(ALL_SYMBOLS, cash)

        agents.append(BehavioralAgent(
            agent_id=str(agent_idx),
            persona=persona,
            initial_cash=cash,
            initial_holdings=holdings,
            initial_prices=initial_prices,
        ))
        agent_idx += 1

    # Rule-based agents — cycle through 4 character types
    for i in range(rule_count):
        char_type = CHARACTER_LIST[i % len(CHARACTER_LIST)]
        cash = round(random.uniform(80_000, 200_000), 2)
        holdings = _random_holdings(ALL_SYMBOLS, cash)

        agents.append(RuleBasedAgent(
            agent_id=str(agent_idx),
            character_type=char_type,
            name=f"Bot-{char_type[:3]}-{agent_idx}",
            initial_cash=cash,
            initial_holdings=holdings,
            initial_prices=initial_prices,
        ))
        agent_idx += 1

    # ── Simulation loop ──
    # Preserve ws_broadcast so connected clients keep receiving updates after reset/config
    old_broadcast = simulation.ws_broadcast if simulation is not None else None
    simulation = SimulationLoop(agents, market_books, stock_meta=STOCKS)
    if old_broadcast:
        simulation.ws_broadcast = old_broadcast
    if config:
        simulation.configure(cfg)

    logger.info(
        f"World built: {len(agents)} agents "
        f"({llm_count} LLM / {rule_count} rule), "
        f"{len(STOCKS)} stocks"
    )


def _init_chat_engine():
    """Lazily initialize the chatbot engine (requires Groq key)."""
    global chat_engine
    if chat_engine is not None:
        return

    try:
        import sys, os
        # Add legacy chatbot to path
        legacy_dir = os.path.join(os.path.dirname(__file__), "..", "..", "legacy")
        if legacy_dir not in sys.path:
            sys.path.insert(0, legacy_dir)

        from chatbot.llm.groq_llm import GroqLLM
        from chatbot.core.chat_engine import ChatEngine
        from backend.app.core.config import settings

        llm = GroqLLM(api_key=settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY", ""))
        chat_engine = ChatEngine(
            llm=llm,
            memory_size=15,
            custom_system_prompt=(
                "You are StockAI's market advisor. You have access to a simulated "
                "market with 25 stocks across 6 sectors. Answer questions about market "
                "conditions, agent strategies, stock performance, and trading concepts. "
                "Be concise and data-driven."
            ),
        )
        logger.info("ChatEngine initialized successfully")
    except Exception as e:
        logger.warning(f"ChatEngine init failed (chatbot features disabled): {e}")
        chat_engine = None


# ── Build default world at import time ──
_build_world()
