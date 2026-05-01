from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from backend.app.agents.behavioral_agent import BaseAgent
from backend.app.models.types import Order, OrderSide, OrderType
from backend.app.sdk.strategy import (
    BaseStrategy,
    EvaluationMetricSet,
    FillEvent,
    MarketMicrostructureSnapshot,
    NewsEvent,
    ObservationFrame,
    STRATEGY_LIBRARY,
    StrategyContext,
)


class StrategyAgent(BaseAgent):
    agent_kind = "strategy"

    def __init__(
        self,
        agent_id: str,
        name: str,
        strategy: BaseStrategy,
        strategy_id: str,
        initial_cash: float,
        initial_holdings: Dict[str, int],
        initial_prices: Dict[str, float],
        dataset_version: str,
        scenario_id: str,
        universe_id: str,
        seed: Optional[int] = None,
        training_mode: str = "deterministic",
    ):
        persona = {
            "name": name,
            "type": "Strategy",
            "description": f"Python SDK strategy agent ({strategy_id})",
            "strategy_style": strategy_id,
            "risk_tolerance": "Programmatic",
            "bias_profile": {},
        }
        super().__init__(agent_id, persona, initial_cash, initial_holdings, initial_prices)
        self.strategy = strategy
        self.strategy_id = strategy_id
        self.context = StrategyContext(
            run_id="pending",
            agent_id=str(agent_id),
            dataset_version=dataset_version,
            scenario_id=scenario_id,
            universe_id=universe_id,
            seed=seed,
            training_mode=training_mode,
        )
        self.strategy.on_run_start(self.context)

    def set_run_id(self, run_id: str):
        self.context.run_id = run_id

    def _microstructure(self, market_state: Dict[str, Any]) -> Dict[str, MarketMicrostructureSnapshot]:
        prices = market_state.get("prices", {})
        spreads = market_state.get("spreads_bps", {})
        order_imbalance = market_state.get("order_imbalance", {})
        halted = market_state.get("halted", set())
        micro: Dict[str, MarketMicrostructureSnapshot] = {}
        for symbol, price in prices.items():
            imbalance = abs(order_imbalance.get(symbol, 0))
            micro[symbol] = MarketMicrostructureSnapshot(
                symbol=symbol,
                last_price=price,
                bid_depth=max(50, int(500 - imbalance * 10)),
                ask_depth=max(50, int(500 + imbalance * 10)),
                spread_bps=float(spreads.get(symbol, 8.0)),
                liquidity_regime=market_state.get("liquidity_regime", "core"),
                latency_ms=int(market_state.get("latency_ms", 0)),
                halted=symbol in halted,
            )
        return micro

    def _events(self, market_state: Dict[str, Any]) -> List[NewsEvent]:
        news_events: List[NewsEvent] = []
        for idx, event in enumerate(market_state.get("full_events", [])):
            news_events.append(
                NewsEvent(
                    id=event.get("id", f"evt-{idx}"),
                    title=event.get("title", "Market Event"),
                    severity=event.get("severity", "MEDIUM"),
                    event_type=event.get("event_type", "market"),
                    impact_pct=float(event.get("impact_pct", 0.0)),
                    affected_symbols=list(event.get("affected_stocks", []) or []),
                )
            )
        return news_events

    def demo_act(self, market_state: Dict[str, Any]) -> Optional[Order]:
        self._update_pnl(market_state["prices"])
        observation = ObservationFrame(
            timestamp=market_state.get("timestamp"),
            day=market_state.get("day", 0),
            session=market_state.get("session", 0),
            session_phase=market_state.get("session_phase", "continuous"),
            regime=market_state.get("regime", "risk_on"),
            sentiment=market_state.get("sentiment", "neutral"),
            prices=market_state.get("prices", {}),
            trends=market_state.get("trends", {}),
            benchmark_return_pct=float(market_state.get("benchmark_return_pct", 0.0)),
            breadth_ratio=float(market_state.get("breadth_ratio", 0.5)),
            realized_vol_pct=float(market_state.get("realized_vol_pct", 0.0)),
            liquidity_regime=market_state.get("liquidity_regime", "core"),
        )
        self.strategy.on_session_start(self.context, observation)
        intents = self.strategy.on_observation(self.context, observation, self._microstructure(market_state), self._events(market_state))
        if not intents:
            self._log_decision(
                market_state.get("day", 0),
                market_state.get("session", 0),
                "hold",
                None,
                0,
                0,
                f"{self.strategy.display_name} held position.",
                [],
                {
                    "thesis": "Awaiting stronger signal alignment.",
                    "catalyst": market_state.get("regime", "neutral").replace("_", " "),
                    "risk": "opportunity cost",
                    "horizon_days": 1,
                    "conviction": 35,
                    "exposure_impact": "maintain",
                },
            )
            return None

        intent = intents[0]
        symbol = intent.symbol
        price = market_state["prices"].get(symbol, 100.0)
        limit_price = intent.limit_price or round(price, 2)
        if intent.side == "buy":
            max_affordable = int(self.wallet["cash"] / max(limit_price, 0.01))
            quantity = min(intent.quantity, max_affordable)
            if quantity <= 0:
                return None
            side = OrderSide.BUY
        else:
            quantity = min(intent.quantity, self.wallet["holdings"].get(symbol, 0))
            if quantity <= 0:
                return None
            side = OrderSide.SELL

        self._record_trade(quantity)
        self._log_decision(
            market_state.get("day", 0),
            market_state.get("session", 0),
            intent.side,
            symbol,
            quantity,
            limit_price,
            intent.thesis or f"{self.strategy.display_name} decision.",
            [],
            {
                "thesis": intent.thesis or f"{self.strategy.display_name} signal",
                "catalyst": market_state.get("regime", "neutral").replace("_", " "),
                "risk": "execution drift",
                "horizon_days": 2,
                "conviction": intent.conviction,
                "exposure_impact": "increase" if intent.side == "buy" else "reduce",
            },
        )
        return Order(
            id=str(uuid.uuid4()),
            agent_id=str(self.id),
            stock_symbol=symbol,
            side=side,
            type=OrderType.MARKET if intent.order_type == "market" else OrderType.LIMIT,
            price=limit_price,
            quantity=quantity,
            timestamp=market_state.get("timestamp"),
        )

    async def act(self, market_state: Dict[str, Any], news: str) -> Optional[Order]:
        return self.demo_act(market_state)

    def on_fill_event(self, trade_id: str, symbol: str, side: str, quantity: int, price: float, timestamp):
        self.strategy.on_fill(
            self.context,
            FillEvent(
                trade_id=trade_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                timestamp=timestamp,
            ),
        )

    def finalize_metrics(self) -> EvaluationMetricSet:
        initial_total = self._initial_total_value(self.initial_prices)
        pnl_pct = (self.pnl / initial_total * 100) if initial_total else 0.0
        return EvaluationMetricSet(
            pnl=round(self.pnl, 2),
            pnl_pct=round(pnl_pct, 2),
            sharpe_ratio=float(self.get_analytics().get("sharpe_ratio", 0.0)),
            win_rate=float(self.get_analytics().get("win_rate", 0.0)),
            max_drawdown=round(self._max_drawdown * 100, 2),
            turnover=0.0,
        )


def build_strategy(strategy_id: str, config: Optional[Dict[str, Any]] = None) -> BaseStrategy:
    strategy_cls = STRATEGY_LIBRARY.get(strategy_id)
    if strategy_cls is None:
        raise ValueError(f"Unknown strategy_id: {strategy_id}")
    return strategy_cls(config=config or {})
