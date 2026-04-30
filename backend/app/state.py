"""
Global simulation state for StockAI's local-first research platform.

This module owns the active market world, the persistent research store,
and the seeded US equities universe used by the simulator, bot lab, and
research workspace.
"""

from __future__ import annotations

import logging
import os
import random
from typing import Dict, List, Optional

from backend.app.agents.behavioral_agent import (
    AGENT_PERSONAS,
    CHARACTER_LIST,
    BaseAgent,
    BehavioralAgent,
    RuleBasedAgent,
)
from backend.app.agents.strategy_agent import StrategyAgent, build_strategy
from backend.app.core.job_manager import BackgroundJobManager
from backend.app.core.research_store import ResearchStore
from backend.app.engine.order_book import OrderBook
from backend.app.engine.simulation_loop import SimulationLoop
from backend.app.models.types import SimulationConfig, StockMeta

logger = logging.getLogger("state")

UNIVERSE_ID = "us-equities-core-v1"
DEFAULT_DATASET_ID = "dataset-us-equities-core-v1"
DEFAULT_SCENARIO_ID = "scenario-hybrid-baseline-v1"
DEFAULT_EXPERIMENT_ID = "experiment-default-research-v1"
DEFAULT_POPULATION_ID = "population-core-mixed-v1"


US_STOCKS: Dict[str, StockMeta] = {
    "AAPL": StockMeta(symbol="AAPL", name="Apple", sector="Technology", initial_price=192.0, volatility_multiplier=1.0, emoji="AP", benchmark="QQQ", liquidity_profile="deep", market_cap_bucket="mega", beta=1.05, average_daily_volume_millions=58.0, description="Consumer devices and software platform leader."),
    "MSFT": StockMeta(symbol="MSFT", name="Microsoft", sector="Technology", initial_price=418.0, volatility_multiplier=0.9, emoji="MS", benchmark="QQQ", liquidity_profile="deep", market_cap_bucket="mega", beta=0.95, average_daily_volume_millions=26.0, description="Cloud and enterprise software heavyweight."),
    "NVDA": StockMeta(symbol="NVDA", name="NVIDIA", sector="Technology", initial_price=912.0, volatility_multiplier=1.5, emoji="NV", benchmark="QQQ", liquidity_profile="deep", market_cap_bucket="mega", beta=1.65, average_daily_volume_millions=48.0, description="AI compute and semiconductor leader."),
    "AMZN": StockMeta(symbol="AMZN", name="Amazon", sector="Technology", initial_price=181.0, volatility_multiplier=1.15, emoji="AM", benchmark="QQQ", liquidity_profile="deep", market_cap_bucket="mega", beta=1.18, average_daily_volume_millions=34.0, description="Cloud, logistics, and consumer commerce platform."),
    "GOOGL": StockMeta(symbol="GOOGL", name="Alphabet", sector="Technology", initial_price=165.0, volatility_multiplier=1.05, emoji="GO", benchmark="QQQ", liquidity_profile="deep", market_cap_bucket="mega", beta=1.08, average_daily_volume_millions=23.0, description="Search, ads, and cloud ecosystem."),
    "META": StockMeta(symbol="META", name="Meta", sector="Technology", initial_price=503.0, volatility_multiplier=1.25, emoji="ME", benchmark="QQQ", liquidity_profile="deep", market_cap_bucket="mega", beta=1.22, average_daily_volume_millions=19.0, description="Social, ads, and applied AI platform."),
    "XOM": StockMeta(symbol="XOM", name="Exxon Mobil", sector="Energy", initial_price=118.0, volatility_multiplier=0.8, emoji="XO", benchmark="XLE", liquidity_profile="deep", market_cap_bucket="mega", beta=0.88, average_daily_volume_millions=18.0, description="Integrated energy major."),
    "CVX": StockMeta(symbol="CVX", name="Chevron", sector="Energy", initial_price=157.0, volatility_multiplier=0.82, emoji="CV", benchmark="XLE", liquidity_profile="core", market_cap_bucket="mega", beta=0.84, average_daily_volume_millions=12.0, description="Integrated energy and downstream operations."),
    "SLB": StockMeta(symbol="SLB", name="SLB", sector="Energy", initial_price=51.0, volatility_multiplier=1.1, emoji="SL", benchmark="XLE", liquidity_profile="core", market_cap_bucket="large", beta=1.10, average_daily_volume_millions=13.0, description="Oilfield services and drilling technology."),
    "FSLR": StockMeta(symbol="FSLR", name="First Solar", sector="Energy", initial_price=174.0, volatility_multiplier=1.45, emoji="FS", benchmark="ICLN", liquidity_profile="satellite", market_cap_bucket="mid", beta=1.35, average_daily_volume_millions=3.6, description="Utility-scale solar manufacturer."),
    "JPM": StockMeta(symbol="JPM", name="JPMorgan Chase", sector="Financials", initial_price=207.0, volatility_multiplier=0.76, emoji="JP", benchmark="XLF", liquidity_profile="deep", market_cap_bucket="mega", beta=0.92, average_daily_volume_millions=10.0, description="Large-cap US universal bank."),
    "BAC": StockMeta(symbol="BAC", name="Bank of America", sector="Financials", initial_price=38.0, volatility_multiplier=0.86, emoji="BA", benchmark="XLF", liquidity_profile="deep", market_cap_bucket="mega", beta=1.02, average_daily_volume_millions=39.0, description="Consumer and corporate bank."),
    "GS": StockMeta(symbol="GS", name="Goldman Sachs", sector="Financials", initial_price=431.0, volatility_multiplier=0.92, emoji="GS", benchmark="XLF", liquidity_profile="core", market_cap_bucket="large", beta=1.01, average_daily_volume_millions=2.5, description="Capital markets and trading franchise."),
    "V": StockMeta(symbol="V", name="Visa", sector="Financials", initial_price=276.0, volatility_multiplier=0.65, emoji="VI", benchmark="XLF", liquidity_profile="core", market_cap_bucket="mega", beta=0.86, average_daily_volume_millions=7.5, description="Global payments network."),
    "TSLA": StockMeta(symbol="TSLA", name="Tesla", sector="Auto", initial_price=171.0, volatility_multiplier=1.7, emoji="TS", benchmark="XLY", liquidity_profile="deep", market_cap_bucket="mega", beta=1.85, average_daily_volume_millions=92.0, description="EV and autonomy-heavy growth name."),
    "GM": StockMeta(symbol="GM", name="General Motors", sector="Auto", initial_price=44.0, volatility_multiplier=0.92, emoji="GM", benchmark="XLY", liquidity_profile="core", market_cap_bucket="large", beta=1.08, average_daily_volume_millions=14.0, description="Legacy OEM with EV transition exposure."),
    "F": StockMeta(symbol="F", name="Ford", sector="Auto", initial_price=12.0, volatility_multiplier=1.0, emoji="FO", benchmark="XLY", liquidity_profile="deep", market_cap_bucket="large", beta=1.12, average_daily_volume_millions=55.0, description="Mass-market automotive manufacturer."),
    "WMT": StockMeta(symbol="WMT", name="Walmart", sector="Consumer", initial_price=68.0, volatility_multiplier=0.62, emoji="WM", benchmark="XLP", liquidity_profile="deep", market_cap_bucket="mega", beta=0.54, average_daily_volume_millions=11.0, description="Defensive consumer giant."),
    "COST": StockMeta(symbol="COST", name="Costco", sector="Consumer", initial_price=726.0, volatility_multiplier=0.68, emoji="CO", benchmark="XLP", liquidity_profile="core", market_cap_bucket="mega", beta=0.74, average_daily_volume_millions=2.4, description="Membership-led consumer staple retailer."),
    "MCD": StockMeta(symbol="MCD", name="McDonald's", sector="Consumer", initial_price=286.0, volatility_multiplier=0.58, emoji="MC", benchmark="XLP", liquidity_profile="core", market_cap_bucket="large", beta=0.61, average_daily_volume_millions=3.2, description="Global quick-service franchise."),
    "SBUX": StockMeta(symbol="SBUX", name="Starbucks", sector="Consumer", initial_price=92.0, volatility_multiplier=0.84, emoji="SB", benchmark="XLY", liquidity_profile="core", market_cap_bucket="large", beta=0.96, average_daily_volume_millions=8.1, description="Global branded coffee chain."),
    "NFLX": StockMeta(symbol="NFLX", name="Netflix", sector="Media", initial_price=608.0, volatility_multiplier=1.18, emoji="NF", benchmark="XLC", liquidity_profile="core", market_cap_bucket="large", beta=1.07, average_daily_volume_millions=3.9, description="Streaming platform and content franchise."),
    "DIS": StockMeta(symbol="DIS", name="Disney", sector="Media", initial_price=112.0, volatility_multiplier=0.92, emoji="DI", benchmark="XLC", liquidity_profile="core", market_cap_bucket="mega", beta=0.95, average_daily_volume_millions=12.0, description="Media, parks, and streaming ecosystem."),
    "SPOT": StockMeta(symbol="SPOT", name="Spotify", sector="Media", initial_price=296.0, volatility_multiplier=1.28, emoji="SP", benchmark="XLC", liquidity_profile="satellite", market_cap_bucket="large", beta=1.21, average_daily_volume_millions=1.8, description="Music and audio platform."),
    "RBLX": StockMeta(symbol="RBLX", name="Roblox", sector="Media", initial_price=41.0, volatility_multiplier=1.62, emoji="RB", benchmark="XLC", liquidity_profile="satellite", market_cap_bucket="mid", beta=1.42, average_daily_volume_millions=7.1, description="User-generated gaming and social platform."),
}

INDIA_STOCKS: Dict[str, StockMeta] = {
    "RELIANCE": StockMeta(symbol="RELIANCE", name="Reliance Industries", sector="Energy", initial_price=2900.0, volatility_multiplier=1.2, emoji="🇮🇳", benchmark="NIFTY", liquidity_profile="deep", market_cap_bucket="mega", beta=1.1, average_daily_volume_millions=7.0, description="Indian multinational conglomerate."),
    "TCS": StockMeta(symbol="TCS", name="Tata Consultancy", sector="Technology", initial_price=3900.0, volatility_multiplier=0.8, emoji="🇮🇳", benchmark="NIFTY", liquidity_profile="deep", market_cap_bucket="mega", beta=0.9, average_daily_volume_millions=2.5, description="Global IT services and consulting."),
    "HDFCBANK": StockMeta(symbol="HDFCBANK", name="HDFC Bank", sector="Financials", initial_price=1400.0, volatility_multiplier=1.0, emoji="🇮🇳", benchmark="NIFTY", liquidity_profile="deep", market_cap_bucket="mega", beta=1.1, average_daily_volume_millions=18.0, description="Largest private sector bank in India."),
    "INFY": StockMeta(symbol="INFY", name="Infosys", sector="Technology", initial_price=1450.0, volatility_multiplier=1.1, emoji="🇮🇳", benchmark="NIFTY", liquidity_profile="deep", market_cap_bucket="mega", beta=1.0, average_daily_volume_millions=6.0, description="Information technology company."),
    "ICICIBANK": StockMeta(symbol="ICICIBANK", name="ICICI Bank", sector="Financials", initial_price=1050.0, volatility_multiplier=1.2, emoji="🇮🇳", benchmark="NIFTY", liquidity_profile="deep", market_cap_bucket="mega", beta=1.2, average_daily_volume_millions=14.0, description="Multinational bank and financial services."),
    "HINDUNILVR": StockMeta(symbol="HINDUNILVR", name="Hindustan Unilever", sector="Consumer", initial_price=2200.0, volatility_multiplier=0.7, emoji="🇮🇳", benchmark="NIFTY", liquidity_profile="deep", market_cap_bucket="mega", beta=0.6, average_daily_volume_millions=1.5, description="Consumer goods company."),
    "ITC": StockMeta(symbol="ITC", name="ITC Limited", sector="Consumer", initial_price=420.0, volatility_multiplier=0.8, emoji="🇮🇳", benchmark="NIFTY", liquidity_profile="deep", market_cap_bucket="mega", beta=0.7, average_daily_volume_millions=12.0, description="Conglomerate with FMCG, hotels, packaging."),
    "BHARTIARTL": StockMeta(symbol="BHARTIARTL", name="Bharti Airtel", sector="Media", initial_price=1200.0, volatility_multiplier=1.1, emoji="🇮🇳", benchmark="NIFTY", liquidity_profile="deep", market_cap_bucket="mega", beta=1.0, average_daily_volume_millions=5.0, description="Global telecommunications services."),
}

STOCKS: Dict[str, StockMeta] = US_STOCKS.copy()
ALL_SYMBOLS: List[str] = sorted(STOCKS.keys())

market_books: Dict[str, OrderBook] = {}
agents: List[BaseAgent] = []
simulation: Optional[SimulationLoop] = None
active_session_id: Optional[str] = None
chat_engine = None
research_store = ResearchStore()
job_manager = BackgroundJobManager(research_store)


def _random_holdings(symbols: List[str], budget_hint: float) -> Dict[str, int]:
    count = random.randint(2, min(6, len(symbols)))
    chosen = random.sample(symbols, count)
    holdings: Dict[str, int] = {}
    for sym in chosen:
        price = STOCKS[sym].initial_price
        max_qty = max(1, int(budget_hint * 0.05 / max(price, 1.0)))
        holdings[sym] = random.randint(1, max_qty)
    return holdings


def _normalize_agent_mix(cfg: dict) -> dict[str, float]:
    raw = dict(cfg.get("agent_mix") or {"llm": 0.35, "rule": 0.45, "strategy": 0.20})
    llm_ratio = max(0.0, float(raw.get("llm", 0.0))) if cfg.get("use_llm", True) else 0.0
    rule_ratio = max(0.0, float(raw.get("rule", 0.45)))
    strategy_ratio = max(0.0, float(raw.get("strategy", 0.20)))
    total = llm_ratio + rule_ratio + strategy_ratio
    if total <= 0:
        return {"llm": 0.0, "rule": 1.0, "strategy": 0.0}
    return {"llm": llm_ratio / total, "rule": rule_ratio / total, "strategy": strategy_ratio / total}


def _resolve_agent_counts(num_agents: int, cfg: dict) -> dict[str, int]:
    mix = _normalize_agent_mix(cfg)
    counts = {key: int(num_agents * ratio) for key, ratio in mix.items()}
    allocated = sum(counts.values())
    order = sorted(mix.items(), key=lambda item: item[1], reverse=True)
    idx = 0
    while allocated < num_agents:
        counts[order[idx % len(order)][0]] += 1
        allocated += 1
        idx += 1
    if num_agents >= 4 and counts["strategy"] == 0:
        counts["strategy"] = 1
        counts["rule"] = max(1, counts["rule"] - 1)
    if not cfg.get("use_llm", True):
        counts["rule"] += counts["llm"]
        counts["llm"] = 0
    return counts


def _create_strategy_agent(
    *,
    agent_id: str,
    index: int,
    cfg: dict,
    initial_prices: Dict[str, float],
) -> StrategyAgent:
    strategy_ids = ["mean_reversion", "benchmark_vwap"]
    strategy_id = strategy_ids[index % len(strategy_ids)]
    strategy = build_strategy(strategy_id, {"lookback": 5, "z_entry": 1.2, "z_exit": 0.4})
    cash = round(random.uniform(100_000, 220_000), 2)
    holdings = _random_holdings(ALL_SYMBOLS, cash)
    return StrategyAgent(
        agent_id=agent_id,
        name=f"{strategy.display_name} #{index + 1}",
        strategy=strategy,
        strategy_id=strategy_id,
        initial_cash=cash,
        initial_holdings=holdings,
        initial_prices=initial_prices,
        dataset_version=cfg.get("dataset_version", DEFAULT_DATASET_ID),
        scenario_id=cfg.get("scenario_id", DEFAULT_SCENARIO_ID),
        universe_id=cfg.get("universe_id", UNIVERSE_ID),
        seed=cfg.get("seed"),
        training_mode=cfg.get("training_mode", "hybrid"),
    )


def build_world_bundle(config: Optional[dict] = None, extra_agents: Optional[List[BaseAgent]] = None) -> dict:
    global STOCKS, ALL_SYMBOLS
    cfg = SimulationConfig(**(config or {})).model_dump()
    
    market_context = cfg.get("market_context", "us_equities")
    STOCKS.clear()
    if market_context == "india_nse_bse":
        STOCKS.update(INDIA_STOCKS)
    elif market_context == "global":
        STOCKS.update(US_STOCKS)
        STOCKS.update(INDIA_STOCKS)
    else:
        STOCKS.update(US_STOCKS)
    ALL_SYMBOLS.clear()
    ALL_SYMBOLS.extend(sorted(STOCKS.keys()))

    seed = cfg.get("seed")
    if seed is not None:
        random.seed(seed)

    books = {sym: OrderBook(sym) for sym in STOCKS}
    for sym, meta in STOCKS.items():
        books[sym].last_price = meta.initial_price
    initial_prices = {sym: meta.initial_price for sym, meta in STOCKS.items()}

    counts = _resolve_agent_counts(cfg["num_agents"], cfg)
    local_agents: List[BaseAgent] = []
    agent_index = 0

    for idx in range(counts["llm"]):
        persona = AGENT_PERSONAS[idx % len(AGENT_PERSONAS)].copy()
        if idx >= len(AGENT_PERSONAS):
            persona["name"] = f"{persona['name']}_{idx}"
        cash = round(random.uniform(90_000, 210_000), 2)
        holdings = _random_holdings(ALL_SYMBOLS, cash)
        local_agents.append(
            BehavioralAgent(
                agent_id=str(agent_index),
                persona=persona,
                initial_cash=cash,
                initial_holdings=holdings,
                initial_prices=initial_prices,
            )
        )
        agent_index += 1

    for idx in range(counts["rule"]):
        char_type = CHARACTER_LIST[idx % len(CHARACTER_LIST)]
        cash = round(random.uniform(80_000, 200_000), 2)
        holdings = _random_holdings(ALL_SYMBOLS, cash)
        local_agents.append(
            RuleBasedAgent(
                agent_id=str(agent_index),
                character_type=char_type,
                name=f"Baseline-{char_type[:4]}-{agent_index}",
                initial_cash=cash,
                initial_holdings=holdings,
                initial_prices=initial_prices,
            )
        )
        agent_index += 1

    for idx in range(counts["strategy"]):
        local_agents.append(
            _create_strategy_agent(
                agent_id=str(agent_index),
                index=idx,
                cfg=cfg,
                initial_prices=initial_prices,
            )
        )
        agent_index += 1

    if extra_agents:
        local_agents.extend(extra_agents)

    sim = SimulationLoop(local_agents, books, stock_meta=STOCKS)
    sim.configure(cfg)
    sim.attach_store(research_store)

    return {
        "config": cfg,
        "market_books": books,
        "agents": local_agents,
        "simulation": sim,
    }


def _build_world(config: Optional[dict] = None):
    global market_books, agents, simulation

    bundle = build_world_bundle(config=config)
    old_broadcast = simulation.ws_broadcast if simulation is not None else None

    market_books = bundle["market_books"]
    agents = bundle["agents"]
    simulation = bundle["simulation"]
    if old_broadcast:
        simulation.ws_broadcast = old_broadcast

    cfg = bundle["config"]
    run = research_store.create_run(
        id=f"run-{os.urandom(4).hex()}",
        name=cfg.get("config_snapshot_label") or f"Research Run seed={cfg.get('seed') if cfg.get('seed') is not None else 'auto'}",
        experiment_id=cfg.get("experiment_id", DEFAULT_EXPERIMENT_ID),
        scenario_id=cfg.get("scenario_id", DEFAULT_SCENARIO_ID),
        dataset_id=cfg.get("dataset_version", DEFAULT_DATASET_ID),
        agent_population_id=cfg.get("agent_population_id", DEFAULT_POPULATION_ID),
        seed=cfg.get("seed"),
        status="configured",
        config_snapshot=cfg,
        summary={
            "active_agents": len(agents),
            "symbols": len(STOCKS),
            "training_mode": cfg.get("training_mode", "hybrid"),
            "liquidity_model": cfg.get("liquidity_model", "adaptive"),
            "latency_ms": cfg.get("latency_ms", 120),
            "slippage_bps": cfg.get("slippage_bps", 6.0),
        },
    )
    simulation.activate_run(run)
    for agent in agents:
        if isinstance(agent, StrategyAgent):
            agent.set_run_id(run["id"])

    logger.info(
        "World built: %s agents (%s llm / %s rule / %s strategy), %s symbols, run=%s",
        len(agents),
        sum(1 for a in agents if a.agent_kind == "llm"),
        sum(1 for a in agents if a.agent_kind == "rule"),
        sum(1 for a in agents if a.agent_kind == "strategy"),
        len(STOCKS),
        run["id"],
    )


def _init_chat_engine():
    global chat_engine
    if chat_engine is not None:
        return

    try:
        import sys

        legacy_dir = os.path.join(os.path.dirname(__file__), "..", "..", "legacy")
        if legacy_dir not in sys.path:
            sys.path.insert(0, legacy_dir)

        from chatbot.core.chat_engine import ChatEngine
        from chatbot.llm.groq_llm import GroqLLM
        from backend.app.core.config import settings

        llm = GroqLLM(api_key=settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY", ""))
        chat_engine = ChatEngine(
            llm=llm,
            memory_size=15,
            custom_system_prompt=(
                "You are StockAI's research copilot. The platform simulates US equities cash markets "
                "with mixed LLM, deterministic, and strategy agents. Explain market state, microstructure, "
                "agent behavior, run metadata, and research findings clearly."
            ),
        )
        logger.info("ChatEngine initialized successfully")
    except Exception as exc:
        logger.warning("ChatEngine init failed (chatbot features disabled): %s", exc)
        chat_engine = None


_build_world()
