from __future__ import annotations

from datetime import datetime
from statistics import mean
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ObservationFrame(BaseModel):
    timestamp: datetime
    day: int
    session: int
    session_phase: str
    regime: str
    sentiment: str
    prices: Dict[str, float]
    trends: Dict[str, str]
    benchmark_return_pct: float = 0.0
    breadth_ratio: float = 0.5
    realized_vol_pct: float = 0.0
    liquidity_regime: str = "core"


class MarketMicrostructureSnapshot(BaseModel):
    symbol: str
    last_price: float
    bid_depth: int
    ask_depth: int
    spread_bps: float
    liquidity_regime: str
    latency_ms: int
    halted: bool = False


class NewsEvent(BaseModel):
    id: str
    title: str
    severity: str
    event_type: str
    impact_pct: float = 0.0
    affected_symbols: List[str] = Field(default_factory=list)


class OrderIntent(BaseModel):
    symbol: str
    side: Literal["buy", "sell"]
    quantity: int = Field(..., gt=0)
    limit_price: Optional[float] = None
    order_type: Literal["limit", "market"] = "limit"
    thesis: str = ""
    conviction: int = Field(default=50, ge=1, le=100)


class FillEvent(BaseModel):
    trade_id: str
    symbol: str
    side: Literal["buy", "sell"]
    quantity: int
    price: float
    timestamp: datetime


class EvaluationMetricSet(BaseModel):
    pnl: float = 0.0
    pnl_pct: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    max_drawdown: float = 0.0
    turnover: float = 0.0


class StrategyContext(BaseModel):
    run_id: str
    agent_id: str
    dataset_version: str
    scenario_id: str
    universe_id: str
    seed: Optional[int] = None
    training_mode: str = "hybrid"


class BaseStrategy:
    strategy_id = "base_strategy"
    display_name = "Base Strategy"

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    def on_run_start(self, context: StrategyContext):
        return None

    def on_session_start(self, context: StrategyContext, observation: ObservationFrame):
        return None

    def on_observation(
        self,
        context: StrategyContext,
        observation: ObservationFrame,
        market: Dict[str, MarketMicrostructureSnapshot],
        events: List[NewsEvent],
    ) -> Optional[List[OrderIntent]]:
        return None

    def on_market_event(self, context: StrategyContext, event: NewsEvent):
        return None

    def on_fill(self, context: StrategyContext, fill: FillEvent):
        return None

    def on_run_end(self, context: StrategyContext, metrics: EvaluationMetricSet):
        return None


class MeanReversionStrategy(BaseStrategy):
    strategy_id = "mean_reversion"
    display_name = "Mean Reversion"

    def on_observation(
        self,
        context: StrategyContext,
        observation: ObservationFrame,
        market: Dict[str, MarketMicrostructureSnapshot],
        events: List[NewsEvent],
    ) -> Optional[List[OrderIntent]]:
        lookback = max(3, int(self.config.get("lookback", 5)))
        z_entry = float(self.config.get("z_entry", 1.2))
        z_exit = float(self.config.get("z_exit", 0.3))
        if observation.session_phase not in {"continuous", "close_auction"}:
            return None

        prices = list(observation.prices.items())
        if len(prices) < lookback:
            return None

        avg_price = mean(observation.prices.values())
        intents: List[OrderIntent] = []
        for symbol, price in prices[: min(4, len(prices))]:
            micro = market.get(symbol)
            if not micro or micro.halted:
                continue
            deviation = (price - avg_price) / max(avg_price, 1.0)
            if deviation <= -(z_entry / 100):
                intents.append(
                    OrderIntent(
                        symbol=symbol,
                        side="buy",
                        quantity=6,
                        limit_price=round(price * 0.998, 2),
                        thesis=f"{symbol} is trading below the basket mean.",
                        conviction=60,
                    )
                )
            elif deviation >= (max(z_exit, z_entry) / 100):
                intents.append(
                    OrderIntent(
                        symbol=symbol,
                        side="sell",
                        quantity=4,
                        limit_price=round(price * 1.002, 2),
                        thesis=f"{symbol} is extended versus the basket mean.",
                        conviction=55,
                    )
                )
        return intents[:1] or None


class VWAPBenchmarkStrategy(BaseStrategy):
    strategy_id = "benchmark_vwap"
    display_name = "VWAP Benchmark"

    def on_observation(
        self,
        context: StrategyContext,
        observation: ObservationFrame,
        market: Dict[str, MarketMicrostructureSnapshot],
        events: List[NewsEvent],
    ) -> Optional[List[OrderIntent]]:
        if observation.session_phase != "continuous":
            return None
        symbol = next(iter(observation.prices.keys()), None)
        if not symbol:
            return None
        price = observation.prices[symbol]
        side = "buy" if observation.benchmark_return_pct >= 0 else "sell"
        return [
            OrderIntent(
                symbol=symbol,
                side=side,
                quantity=3,
                limit_price=round(price, 2),
                thesis="Benchmark participation aligned with the tape.",
                conviction=45,
            )
        ]


STRATEGY_LIBRARY = {
    MeanReversionStrategy.strategy_id: MeanReversionStrategy,
    VWAPBenchmarkStrategy.strategy_id: VWAPBenchmarkStrategy,
}
