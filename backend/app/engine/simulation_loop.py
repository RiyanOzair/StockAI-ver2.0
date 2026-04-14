from __future__ import annotations

import asyncio
import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from backend.app.agents.behavioral_agent import BaseAgent
from backend.app.agents.strategy_agent import StrategyAgent
from backend.app.core.analytics import compute_index_level, compute_market_analytics, compute_sector_indices
from backend.app.core.live_market import live_market_service
from backend.app.core.research_store import ResearchStore
from backend.app.models.research import RunEventRecord
from backend.app.models.types import DaySnapshot, FinancialReport, ForumMessage, LOAN_TERMS, Loan, MarketEvent, Order, OrderSide, REPORT_DAYS

logger = logging.getLogger("simulation.loop")

EVENT_TEMPLATES = [
    {"title": "Fed Path Shift", "type": "monetary_policy", "severity": "HIGH", "impact": (-0.03, 0.03)},
    {"title": "Earnings Revision Wave", "type": "earnings", "severity": "MEDIUM", "impact": (-0.02, 0.02)},
    {"title": "Risk Appetite Rotation", "type": "sentiment", "severity": "MEDIUM", "impact": (-0.015, 0.015)},
    {"title": "Macro Print Surprise", "type": "macro", "severity": "MEDIUM", "impact": (-0.015, 0.015)},
    {"title": "Strategic Acquisition", "type": "corporate", "severity": "HIGH", "impact": (-0.01, 0.04)},
    {"title": "Regulatory Shock", "type": "regulation", "severity": "HIGH", "impact": (-0.03, 0.01)},
]
VOLATILITY_MAP = {"Low": 0.008, "Medium": 0.015, "High": 0.027, "Extreme": 0.045}
SESSION_PHASES = [("pre_open", "08:45:00"), ("open_auction", "09:30:00"), ("continuous", "13:00:00"), ("close_auction", "15:55:00")]
SECTOR_NAMES = ["Technology", "Energy", "Financials", "Auto", "Consumer", "Media"]
SECTOR_CORR = {
    ("Technology", "Technology"): 1.0, ("Technology", "Energy"): 0.18, ("Technology", "Financials"): 0.31, ("Technology", "Auto"): 0.34, ("Technology", "Consumer"): 0.27, ("Technology", "Media"): 0.43,
    ("Energy", "Energy"): 1.0, ("Energy", "Financials"): 0.29, ("Energy", "Auto"): 0.26, ("Energy", "Consumer"): 0.16, ("Energy", "Media"): 0.08,
    ("Financials", "Financials"): 1.0, ("Financials", "Auto"): 0.22, ("Financials", "Consumer"): 0.34, ("Financials", "Media"): 0.18,
    ("Auto", "Auto"): 1.0, ("Auto", "Consumer"): 0.25, ("Auto", "Media"): 0.12,
    ("Consumer", "Consumer"): 1.0, ("Consumer", "Media"): 0.28,
    ("Media", "Media"): 1.0,
}
REGIME_LIBRARY = {
    "risk_on": {"headline": "Risk-on expansion", "sector_bias": {"Technology": 0.8, "Media": 0.35, "Financials": 0.2}, "event_bias": {"sentiment", "corporate"}, "vol_multiplier": 1.0, "liquidity_regime": "deep"},
    "risk_off": {"headline": "Risk-off defensive rotation", "sector_bias": {"Technology": -0.45, "Energy": 0.08, "Consumer": 0.2, "Financials": -0.18}, "event_bias": {"macro", "policy", "regulation"}, "vol_multiplier": 1.18, "liquidity_regime": "core"},
    "inflation_shock": {"headline": "Inflation shock repricing", "sector_bias": {"Energy": 0.72, "Consumer": -0.42, "Technology": -0.22, "Auto": -0.38}, "event_bias": {"macro", "monetary_policy"}, "vol_multiplier": 1.34, "liquidity_regime": "satellite"},
    "policy_tightening": {"headline": "Policy tightening", "sector_bias": {"Financials": 0.32, "Technology": -0.35, "Auto": -0.2}, "event_bias": {"monetary_policy", "policy", "regulation"}, "vol_multiplier": 1.15, "liquidity_regime": "core"},
    "earnings_repricing": {"headline": "Earnings repricing", "sector_bias": {"Technology": 0.45, "Media": 0.24, "Consumer": -0.1}, "event_bias": {"earnings", "corporate"}, "vol_multiplier": 1.1, "liquidity_regime": "deep"},
    "sector_rotation": {"headline": "Cross-sector rotation", "sector_bias": {"Financials": 0.28, "Energy": 0.25, "Technology": -0.18, "Media": -0.15}, "event_bias": {"sentiment", "macro"}, "vol_multiplier": 1.05, "liquidity_regime": "core"},
}
CIRCUIT_BREAKER_PCT = 0.10
LLM_BATCH_SIZE = 4
LLM_BATCH_DELAY = 1.2


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _corr(s1: str, s2: str) -> float:
    return SECTOR_CORR.get((s1, s2), SECTOR_CORR.get((s2, s1), 0.0))


class SimulationLoop:
    def __init__(self, agents: List[BaseAgent], order_books: Dict, stock_meta: Dict):
        self.agents = agents
        self.order_books = order_books
        self.stock_meta = stock_meta
        self.is_running = False
        self.is_paused = False
        self.day = 0
        self.session = 0
        self.session_phase = SESSION_PHASES[0][0]
        self.total_days = 30
        self.sessions_per_day = len(SESSION_PHASES)
        self._run_id = 0
        self._step_index = 0
        self.speed = 2.0
        self.volatility = "Medium"
        self.event_intensity = 5
        self.use_llm = True
        self.enable_loans = True
        self.regime_sensitivity = 1.0
        self.benchmark_mode = "equal_weight"
        self.analytics_detail = "professional"
        self.universe_id = "us-equities-core-v1"
        self.dataset_version = "dataset-us-equities-core-v1"
        self.scenario_id = "scenario-hybrid-baseline-v1"
        self.experiment_id = "experiment-default-research-v1"
        self.agent_population_id = "population-core-mixed-v1"
        self.calendar_mode = "us_equities_cash"
        self.session_model = "auction_continuous_close"
        self.liquidity_model = "adaptive"
        self.liquidity_regime = "core"
        self.latency_ms = 120
        self.slippage_bps = 6.0
        self.training_mode = "hybrid"
        self.real_world_sync = False
        self.config_snapshot_label: Optional[str] = None
        self.notes: Dict[str, str] = {}
        self.all_trades = []
        self.events: List[MarketEvent] = []
        self.forum_messages: List[ForumMessage] = []
        self.financial_reports: List[FinancialReport] = []
        self.price_history: Dict[str, list] = {s: [] for s in order_books}
        self.total_trade_count = 0
        self.halted_stocks: Set[str] = set()
        self.snapshots: List[DaySnapshot] = []
        self.run_event_log: List[Dict] = []
        self.ws_broadcast = None
        self.research_store: Optional[ResearchStore] = None
        self.active_run: Optional[Dict] = None
        self.active_run_id: Optional[str] = None
        self.calibration_profile: Dict = {}
        self._event_sequence = 0
        self._pending_orders: List[Dict] = []
        self._injected_event_queue: List[MarketEvent] = []  # FIX H3: Queue for events injected via API
        self._session_open: Dict[str, float] = {}
        self._run_stop_reason = "completed"
        self.base_prices = {s: getattr(m, "initial_price", 100.0) for s, m in stock_meta.items()}
        self.current_regime = "risk_on"
        self.current_regime_profile = REGIME_LIBRARY[self.current_regime]
        self.regime_history: List[Dict] = [{"day": 0, "regime": self.current_regime, "headline": self.current_regime_profile["headline"]}]
        self.benchmark_history: List[Dict] = [{"day": 0, "session": 0, "value": 100.0}]
        self.sector_index_history: List[Dict] = []
        self.market_metrics_history: List[Dict] = []
        self.turnover = 0.0
        self.market_sentiment = "neutral"
        self.session_risk = "Normal"
        self._session_trade_notional = 0.0
        self.order_imbalance: Dict[str, float] = {symbol: 0.0 for symbol in self.order_books}

    def attach_store(self, store: ResearchStore):
        self.research_store = store
        self._load_calibration_profile()

    def activate_run(self, run_record: Dict):
        self.active_run = run_record
        self.active_run_id = run_record["id"]
        self._event_sequence = 0
        self.run_event_log = []
        self._load_calibration_profile()
        self._emit_run_event("run_configured", {"run_id": self.active_run_id, "config": run_record.get("config_snapshot", {})}, "configured")

    def _load_calibration_profile(self):
        if not self.research_store:
            self.calibration_profile = {}
            return
        dataset = self.research_store.get_record("datasets", self.dataset_version)
        self.calibration_profile = dataset.get("calibration", {}) if dataset else {}

    def configure(self, cfg: dict):
        self.total_days = cfg.get("num_days", self.total_days)
        self.volatility = str(cfg.get("volatility", self.volatility)).title()
        self.event_intensity = cfg.get("event_intensity", self.event_intensity)
        self.use_llm = cfg.get("use_llm", self.use_llm)
        self.speed = cfg.get("speed", self.speed)
        self.enable_loans = cfg.get("enable_loans", self.enable_loans)
        self.regime_sensitivity = cfg.get("regime_sensitivity", self.regime_sensitivity)
        self.benchmark_mode = cfg.get("benchmark_mode", self.benchmark_mode)
        self.analytics_detail = cfg.get("analytics_detail", self.analytics_detail)
        self.universe_id = cfg.get("universe_id", self.universe_id)
        self.dataset_version = cfg.get("dataset_version", self.dataset_version)
        self.scenario_id = cfg.get("scenario_id", self.scenario_id)
        self.experiment_id = cfg.get("experiment_id", self.experiment_id)
        self.agent_population_id = cfg.get("agent_population_id", self.agent_population_id)
        self.calendar_mode = cfg.get("calendar_mode", self.calendar_mode)
        self.session_model = cfg.get("session_model", self.session_model)
        self.liquidity_model = cfg.get("liquidity_model", self.liquidity_model)
        self.liquidity_regime = cfg.get("liquidity_regime", self.liquidity_regime)
        self.latency_ms = int(cfg.get("latency_ms", self.latency_ms))
        self.slippage_bps = float(cfg.get("slippage_bps", self.slippage_bps))
        self.training_mode = cfg.get("training_mode", self.training_mode)
        self.real_world_sync = cfg.get("real_world_sync", self.real_world_sync)
        self.config_snapshot_label = cfg.get("config_snapshot_label", self.config_snapshot_label)
        self.notes = dict(cfg.get("notes") or {})
        self._load_calibration_profile()

    def _phase_clock(self, session: int) -> tuple[str, str]:
        return SESSION_PHASES[max(0, min(session - 1, len(SESSION_PHASES) - 1))]

    def _emit_run_event(self, event_type: str, payload: Dict, phase: Optional[str] = None):
        if not self.active_run_id:
            return
        self._event_sequence += 1
        record = RunEventRecord(run_id=self.active_run_id, sequence=self._event_sequence, event_type=event_type, phase=phase or self.session_phase, payload=payload)
        dumped = record.model_dump(mode="json")
        self.run_event_log.append(dumped)
        if len(self.run_event_log) > 600:
            self.run_event_log = self.run_event_log[-600:]
        if self.research_store:
            self.research_store.append_run_event(record)

    def _roll_regime(self, day: int):
        if day == 1 or (day - 1) % 6 == 0:
            # FIX C4: Use calibrated regime_transition_bias weights instead of equal-probability random.choice
            regimes = list(REGIME_LIBRARY.keys())
            bias = self.calibration_profile.get("regime_transition_bias", {})
            weights = [bias.get(r, 1.0) for r in regimes]
            self.current_regime = random.choices(regimes, weights=weights, k=1)[0]
            self.current_regime_profile = REGIME_LIBRARY[self.current_regime]
            self.liquidity_regime = self.current_regime_profile.get("liquidity_regime", self.liquidity_regime)
            entry = {"day": day, "regime": self.current_regime, "headline": self.current_regime_profile["headline"]}
            self.regime_history.append(entry)
            self._emit_run_event("regime_shift", entry)

    def _sector_of(self, symbol: str) -> str:
        meta = self.stock_meta.get(symbol)
        return meta.sector if meta else "Technology"

    def _spread_bps(self, symbol: str) -> float:
        liquidity = getattr(self.stock_meta.get(symbol), "liquidity_profile", "core")
        spreads = self.calibration_profile.get("spread_bps", {})
        base = float(spreads.get(liquidity, {"deep": 4.0, "core": 8.0, "satellite": 15.0, "thin": 28.0}.get(liquidity, 8.0)))
        phase_mult = {"pre_open": 1.8, "open_auction": 1.2, "continuous": 1.0, "close_auction": 1.1}.get(self.session_phase, 1.0)
        regime_mult = 1.2 if self.current_regime in {"inflation_shock", "risk_off"} else 1.0
        return round(base * phase_mult * regime_mult, 2)

    def _calculate_trend(self, symbol: str, window: int = 6) -> str:
        history = self.price_history.get(symbol, [])
        if len(history) < 2:
            return "Neutral"
        recent = history[-window:]
        change = (recent[-1]["price"] - recent[0]["price"]) / max(recent[0]["price"], 1.0)
        if change > 0.01:
            return "Bullish"
        if change < -0.01:
            return "Bearish"
        return "Neutral"

    def _generate_events(self, day: int) -> List[MarketEvent]:
        events = []
        if day == max(1, int(self.total_days * 0.25)):
            events.append(MarketEvent(id=str(uuid.uuid4()), day=day, title="Fed Path Shift", description="Rates expectations are repricing across the curve.", severity="HIGH", event_type="monetary_policy", impact_pct=random.uniform(-0.03, 0.03)))
        if day == max(1, int(self.total_days * 0.5)):
            events.append(MarketEvent(id=str(uuid.uuid4()), day=day, title="Earnings Revision Wave", description="Street estimates are resetting for leadership names.", severity="HIGH", event_type="earnings", impact_pct=random.uniform(-0.02, 0.02)))
        if random.random() < (self.event_intensity / 15.0):
            preferred = self.current_regime_profile.get("event_bias", set())
            pool = [tmpl for tmpl in EVENT_TEMPLATES if tmpl["type"] in preferred] or EVENT_TEMPLATES
            tmpl = random.choice(pool)
            sector = random.choice(SECTOR_NAMES)
            affected = [s for s, m in self.stock_meta.items() if m.sector == sector]
            events.append(MarketEvent(id=str(uuid.uuid4()), day=day, title=tmpl["title"], description=f"Day {day}: {tmpl['title']} reprices the {sector} complex.", severity=tmpl["severity"], event_type=tmpl["type"], impact_pct=random.uniform(*tmpl["impact"]), affected_stocks=affected))
        for event in events:
            self._emit_run_event("market_event", {"id": event.id, "title": event.title, "severity": event.severity, "event_type": event.event_type, "impact_pct": event.impact_pct, "affected_stocks": event.affected_stocks})
        return events

    def _event_impact_by_sector(self, events: List[MarketEvent]) -> Dict[str, float]:
        impacts: Dict[str, float] = {}
        for event in events:
            if event.affected_stocks:
                for sym in event.affected_stocks:
                    sector = self._sector_of(sym)
                    impacts[sector] = impacts.get(sector, 0.0) + event.impact_pct
            else:
                for sector in SECTOR_NAMES:
                    impacts[sector] = impacts.get(sector, 0.0) + event.impact_pct
        return impacts

    def _generate_sector_drifts(self, sector_impacts: Dict[str, float]) -> Dict[str, float]:
        raw = {}
        for sector in SECTOR_NAMES:
            regime_bias = self.current_regime_profile.get("sector_bias", {}).get(sector, 0.0) * self.regime_sensitivity
            raw[sector] = random.gauss(0, 1) + sector_impacts.get(sector, 0.0) * 18 + regime_bias
        # FIX C5: Use calibrated sector_correlation when available, fallback to hardcoded SECTOR_CORR
        cal_corr = self.calibration_profile.get("sector_correlation", {})
        blended = {}
        for sector in SECTOR_NAMES:
            val = raw[sector]
            for other in SECTOR_NAMES:
                if other != sector:
                    corr_value = cal_corr.get(sector, {}).get(other, _corr(sector, other))
                    val += raw[other] * corr_value * 0.25
            blended[sector] = val
        return blended

    def _apply_correlated_walk(self, sector_drifts: Dict[str, float]):
        vol_bands = self.calibration_profile.get("volatility_bands", {})
        base_vol = float(vol_bands.get(self.volatility.lower(), VOLATILITY_MAP.get(self.volatility, 0.015)))
        vol = base_vol * self.current_regime_profile.get("vol_multiplier", 1.0)
        phase_mult = {"pre_open": 0.6, "open_auction": 1.1, "continuous": 1.0, "close_auction": 0.85}.get(self.session_phase, 1.0)
        for symbol, book in self.order_books.items():
            if symbol in self.halted_stocks:
                continue
            meta = self.stock_meta.get(symbol)
            vm = meta.volatility_multiplier if meta else 1.0
            current = book.last_price or self.base_prices.get(symbol, 100.0)
            drift = sector_drifts.get(self._sector_of(symbol), 0.0) * vol * 0.38
            noise = random.gauss(0, vol * vm * phase_mult)
            new_price = round(max(1.0, current * (1 + drift + noise)), 2)
            book.update_price(new_price, self.day, self.session)
            self.price_history.setdefault(symbol, []).append({"time": utcnow().isoformat(), "price": new_price, "day": self.day, "session": self.session, "phase": self.session_phase})

    async def _sync_real_world_prices(self):
        """Fetch real-world prices and inject them into the simulation order books."""
        try:
            snapshot = await live_market_service.get_snapshot()
            watchlist = {item["symbol"]: item["price"] for item in snapshot.get("watchlist", [])}
            movers = snapshot.get("major_movers", {})
            for mlist in movers.values():
                for item in mlist:
                    watchlist[item["symbol"]] = item["price"]

            applied_count = 0
            for symbol, book in self.order_books.items():
                if symbol in watchlist:
                    real_price = watchlist[symbol]
                    book.update_price(real_price, self.day, self.session)
                    self.price_history.setdefault(symbol, []).append({
                        "time": utcnow().isoformat(),
                        "price": real_price,
                        "day": self.day,
                        "session": self.session,
                        "phase": self.session_phase,
                        "source": "real_world"
                    })
                    applied_count += 1
                else:
                    # FIX H6: Prevent flatline for symbols absent from Yahoo Finance by substituting synthetic walk
                    import random
                    drift = self.current_regime_profile.get("base_drift", 0.0)
                    vol = self.current_regime_profile.get("volatility", 0.01)
                    move = random.gauss(drift, vol) / (252 * 4) ** 0.5  # Approximate session volatility slice
                    last_price = book.last_price or self.base_prices.get(symbol, 100.0)
                    new_price = max(0.01, last_price * (1 + move))
                    book.update_price(new_price, self.day, self.session)
                    self.price_history.setdefault(symbol, []).append({
                        "time": utcnow().isoformat(),
                        "price": new_price,
                        "day": self.day,
                        "session": self.session,
                        "phase": self.session_phase,
                        "source": "synthetic_fallback"
                    })
            if applied_count > 0:
                self._emit_run_event("real_world_sync", {"symbols_synced": applied_count})
        except Exception as exc:
            logger.warning("Real-world sync failed: %s", exc)

    def _check_circuit_breakers(self) -> List[MarketEvent]:
        events = []
        for symbol, book in self.order_books.items():
            if symbol in self.halted_stocks:
                continue
            open_price = self._session_open.get(symbol)
            if not open_price:
                continue
            current = book.last_price or open_price
            move = abs(current - open_price) / max(open_price, 1.0)
            if move >= CIRCUIT_BREAKER_PCT:
                self.halted_stocks.add(symbol)
                direction = "up" if current > open_price else "down"
                event = MarketEvent(id=str(uuid.uuid4()), day=self.day, session=self.session, title=f"Circuit Breaker: {symbol}", description=f"{symbol} halted after a {move:.1%} move {direction} during {self.session_phase}.", severity="HIGH", event_type="circuit_breaker", impact_pct=0.0, affected_stocks=[symbol])
                events.append(event)
                self._emit_run_event("trading_halt", {"symbol": symbol, "move_pct": round(move * 100, 2), "direction": direction})
        return events

    def _generate_financial_reports(self, day: int) -> Optional[Dict[str, Dict]]:
        if day not in REPORT_DAYS:
            return None
        quarter = REPORT_DAYS.index(day) + 1
        report_data: Dict[str, Dict] = {}
        for symbol in self.stock_meta:
            rev_growth = random.uniform(-0.10, 0.25)
            margin = random.uniform(0.05, 0.40)
            profit = random.uniform(-50, 200)
            cash_flow = random.uniform(-30, 150)
            sentiment = max(-1.0, min(1.0, (0.5 if rev_growth > 0 else -0.5) + (0.5 if profit > 0 else -0.5) + random.uniform(-0.2, 0.2)))
            report = FinancialReport(stock_symbol=symbol, day=day, quarter=quarter, revenue_growth=round(rev_growth, 3), gross_margin=round(margin, 3), net_profit_millions=round(profit, 1), cash_flow_millions=round(cash_flow, 1), sentiment_score=round(sentiment, 2))
            self.financial_reports.append(report)
            report_data[symbol] = {"revenue": profit * 1_000_000 / max(0.01, margin), "profit": profit * 1_000_000, "margin": margin}
        return report_data

    def _process_loans(self, day: int):
        if not self.enable_loans:
            return
        prices = {s: (b.last_price or 100.0) for s, b in self.order_books.items()}
        for agent in self.agents:
            if agent.status == "bankrupt":
                continue
            agent.process_loan_repayment(day, prices)
            if random.random() < agent._char.get("loan_prob", 0.2) and len(agent.loans) < 3:
                term_info = random.choice(LOAN_TERMS)
                amount = round(random.uniform(10_000, 50_000), 2)
                agent.add_loan(Loan(id=str(uuid.uuid4()), agent_id=str(agent.id), amount=amount, interest_rate=term_info["rate"], term_days=term_info["term_days"], start_day=day, due_day=day + term_info["term_days"], remaining=amount))

    def _generate_forum_posts(self, day: int):
        active_agents = [a for a in self.agents if a.status == "active"]
        if not active_agents:
            return
        prices = {s: (b.last_price or 100.0) for s, b in self.order_books.items()}
        for agent in random.sample(active_agents, min(3, len(active_agents))):
            init = agent._initial_total_value(prices)
            pnl_pct = (agent.pnl / init * 100) if init else 0
            if pnl_pct > 5:
                sentiment, pool = "bullish", [f"Benchmark leadership looks durable in {self.current_regime}.", f"Up {pnl_pct:.1f}% and still leaning into winners.", "Breadth is supportive; staying constructive."]
            elif pnl_pct < -5:
                sentiment, pool = "bearish", [f"Drawdown control matters in {self.current_regime}.", "Reducing exposure until regime conditions stabilize.", "Risk budget is tighter than expected today."]
            else:
                sentiment, pool = "neutral", ["Positioning stays balanced while conviction is mixed.", "Waiting for cleaner catalyst alignment before resizing.", "No need to force risk when dispersion is doing the work."]
            self.forum_messages.append(ForumMessage(agent_id=str(agent.id), agent_name=agent.persona.get("name", f"Trader {agent.id}"), message=random.choice(pool), sentiment=sentiment, day=day))

    def _take_snapshot(self):
        prices = {s: (b.last_price or 100.0) for s, b in self.order_books.items()}
        self.snapshots.append(DaySnapshot(day=self.day, prices=prices, agent_summaries=[a.get_snapshot(prices) for a in self.agents], total_trades=self.total_trade_count, events_count=len([e for e in self.events if e.day == self.day])))

    def _update_market_analytics(self):
        current_prices = {s: (b.last_price or self.base_prices.get(s, 100.0)) for s, b in self.order_books.items()}
        benchmark_value = compute_index_level(current_prices, self.base_prices)
        self.benchmark_history.append({"day": self.day, "session": self.session, "value": benchmark_value})
        self.sector_index_history.append({"day": self.day, "session": self.session, "indices": compute_sector_indices(current_prices, self.stock_meta, self.base_prices)})
        current_notional = sum(price * sum(agent.wallet["holdings"].get(sym, 0) for agent in self.agents) for sym, price in current_prices.items())
        self.turnover = self._session_trade_notional / max(current_notional, 1.0)
        analytics = compute_market_analytics(self, current_prices, self.stock_meta)
        self.market_sentiment = analytics["market_sentiment"]
        self.session_risk = "Elevated" if analytics["realized_vol_pct"] > 18 or analytics["benchmark"]["drawdown_pct"] > 5 else "Normal"
        self.market_metrics_history.append({"day": self.day, "session": self.session, **analytics})
        if self.research_store and self.active_run_id:
            self.research_store.update_run(self.active_run_id, summary={"day": self.day, "session": self.session, "session_phase": self.session_phase, "total_trades": self.total_trade_count, "regime": self.current_regime, "benchmark_return_pct": analytics["benchmark"]["return_pct"], "market_sentiment": self.market_sentiment, "session_risk": self.session_risk}, status="running" if self.is_running else "configured")

    def _latency_steps(self) -> int:
        if self.latency_ms < 100:
            return 0
        if self.latency_ms < 350:
            return 1
        return 2

    def _queue_order(self, order: Order):
        execute_step = self._step_index + self._latency_steps()
        self._pending_orders.append({"order": order, "execute_step": execute_step, "submitted_at": utcnow()})
        self._emit_run_event("order_submitted", {"order_id": order.id, "agent_id": order.agent_id, "symbol": order.stock_symbol, "side": order.side.value, "order_type": order.type.value, "price": order.price, "quantity": order.quantity, "execute_step": execute_step})

    def _apply_execution_slippage(self, trades, aggressing_side: OrderSide):
        for trade in trades:
            liquidity = getattr(self.stock_meta.get(trade.stock_symbol), "liquidity_profile", "core")
            liquidity_factor = {"deep": 0.7, "core": 1.0, "satellite": 1.5, "thin": 2.0}.get(liquidity, 1.0)
            phase_factor = {"pre_open": 1.5, "open_auction": 1.1, "continuous": 1.0, "close_auction": 1.15}.get(self.session_phase, 1.0)
            slip = (self.slippage_bps / 10_000.0) * liquidity_factor * phase_factor
            multiplier = 1 + slip if aggressing_side == OrderSide.BUY else max(0.01, 1 - slip)
            trade.price = round(trade.price * multiplier, 2)
            self.order_books[trade.stock_symbol].last_price = trade.price

    def _process_pending_orders(self):
        due, pending = [], []
        for payload in self._pending_orders:
            (due if payload["execute_step"] <= self._step_index else pending).append(payload)
        self._pending_orders = pending
        for item in due:
            order: Order = item["order"]
            if order.stock_symbol in self.halted_stocks or order.stock_symbol not in self.order_books:
                continue
            before = self.order_books[order.stock_symbol].last_price or self.base_prices.get(order.stock_symbol, 100.0)
            trades = self.order_books[order.stock_symbol].add_order(order)
            self.order_imbalance[order.stock_symbol] = float(order.quantity - order.filled_quantity)
            if trades:
                self._apply_execution_slippage(trades, order.side)
                self._process_trades(trades, order.side)
                self.all_trades.extend(trades)
                self.total_trade_count += len(trades)
                after = self.order_books[order.stock_symbol].last_price or before
                self._emit_run_event("order_executed", {"order_id": order.id, "symbol": order.stock_symbol, "filled_quantity": order.filled_quantity, "status": order.status.value, "before_price": before, "after_price": after})

    async def step(self, market_state: Dict, news: str):
        active_agents = [a for a in self.agents if a.status == "active"]
        results = []
        if self.use_llm:
            llm_agents = [a for a in active_agents if a.agent_kind == "llm"]
            other_agents = [a for a in active_agents if a.agent_kind != "llm"]
            for agent in other_agents:
                try:
                    results.append(agent.demo_act(market_state) if hasattr(agent, "demo_act") else None)
                except Exception as exc:
                    logger.error("Agent %s error: %s", agent.id, exc)
            for idx in range(0, len(llm_agents), LLM_BATCH_SIZE):
                batch = llm_agents[idx: idx + LLM_BATCH_SIZE]
                results.extend(await asyncio.gather(*[a.act(market_state, news) for a in batch], return_exceptions=True))
                if idx + LLM_BATCH_SIZE < len(llm_agents):
                    await asyncio.sleep(LLM_BATCH_DELAY)
        else:
            for agent in active_agents:
                try:
                    results.append(agent.demo_act(market_state) if hasattr(agent, "demo_act") else None)
                except Exception as exc:
                    logger.error("Agent %s error: %s", agent.id, exc)
        for res in results:
            if isinstance(res, BaseException):
                logger.error("Agent error: %s", res)
                continue
            if res is not None and isinstance(res, Order) and res.stock_symbol not in self.halted_stocks:
                self._queue_order(res)
        self._process_pending_orders()

    def _process_trades(self, trades, aggressing_side: OrderSide):
        agent_map = {str(a.id): a for a in self.agents}
        for trade in trades:
            buyer = agent_map.get(trade.buyer_agent_id)
            seller = agent_map.get(trade.seller_agent_id)
            cost = round(trade.price * trade.quantity, 2)
            if buyer and buyer.wallet["cash"] >= cost:
                buyer.wallet["cash"] -= cost
                buyer.wallet["holdings"][trade.stock_symbol] = buyer.wallet["holdings"].get(trade.stock_symbol, 0) + trade.quantity
            if seller:
                seller.wallet["cash"] += cost
                seller.wallet["holdings"][trade.stock_symbol] = max(0, seller.wallet["holdings"].get(trade.stock_symbol, 0) - trade.quantity)
            if isinstance(buyer, StrategyAgent):
                buyer.on_fill_event(trade.trade_id, trade.stock_symbol, "buy", trade.quantity, trade.price, trade.timestamp)
            if isinstance(seller, StrategyAgent):
                seller.on_fill_event(trade.trade_id, trade.stock_symbol, "sell", trade.quantity, trade.price, trade.timestamp)
            self._session_trade_notional += cost
            self._emit_run_event("fill", {"trade_id": trade.trade_id, "symbol": trade.stock_symbol, "price": trade.price, "quantity": trade.quantity, "buyer_agent_id": trade.buyer_agent_id, "seller_agent_id": trade.seller_agent_id, "aggressing_side": aggressing_side.value})

    async def run_simulation(self, steps: Optional[int] = None):
        # FIX C1: Seed RNG at simulation start so runs are deterministic when a seed is configured
        run_seed = (self.active_run or {}).get("config_snapshot", {}).get("seed")
        if run_seed is not None:
            random.seed(run_seed)
        self._run_id += 1
        my_run_id = self._run_id
        self.is_running = True
        self.is_paused = False
        self._run_stop_reason = "completed"
        total_steps = steps or (self.total_days * self.sessions_per_day)
        start_step = self.day * self.sessions_per_day
        self._emit_run_event("run_started", {"run_id": self.active_run_id, "total_steps": total_steps}, "configured")
        if self.research_store and self.active_run_id:
            self.research_store.update_run(self.active_run_id, status="running")
        try:
            for step_index in range(start_step, total_steps):
                self._step_index = step_index
                if not self.is_running or self._run_id != my_run_id:
                    break
                while self.is_paused:
                    await asyncio.sleep(0.5)
                    if not self.is_running:
                        return
                self.day = (step_index // self.sessions_per_day) + 1
                self.session = (step_index % self.sessions_per_day) + 1
                self.session_phase, clock_time = self._phase_clock(self.session)
                day_events: List[MarketEvent] = []
                try:
                    if self.session == 1:
                        self.halted_stocks.clear()
                        self._roll_regime(self.day)
                    self._session_open = {s: (b.last_price or self.base_prices.get(s, 100.0)) for s, b in self.order_books.items()}
                    self._session_trade_notional = 0.0
                    self._emit_run_event("phase_start", {"day": self.day, "session": self.session, "session_phase": self.session_phase, "clock_time": clock_time})
                    report_data = None
                    if self.session == 1:
                        day_events = self._generate_events(self.day)
                        self.events.extend(day_events)
                        self._process_loans(self.day)
                        # FIX H5: Early termination — all agents bankrupt. Prevents silent empty simulation output.
                        if len(self.agents) > 0 and all(getattr(a, "status", None) == "bankrupt" for a in self.agents):
                            msg = "All agents are bankrupt. Simulation ending early."
                            self._emit_run_event("all_agents_bankrupt", {"day": self.day, "message": msg})
                            self._run_stop_reason = "all_agents_bankrupt"
                            self.is_running = False
                            break
                        report_data = self._generate_financial_reports(self.day)
                    # FIX H3: Drain injected events so agents see them in their market_state for this session
                    while self._injected_event_queue:
                        injected = self._injected_event_queue.pop(0)
                        day_events.append(injected)
                        if injected not in self.events:
                            self.events.append(injected)
                    
                    if self.real_world_sync:
                        await self._sync_real_world_prices()
                    else:
                        sector_impacts = self._event_impact_by_sector(day_events)
                        self._apply_correlated_walk(self._generate_sector_drifts(sector_impacts))
                    cb_events = self._check_circuit_breakers()
                    if cb_events:
                        self.events.extend(cb_events)
                        day_events.extend(cb_events)
                    self._process_pending_orders()
                    prices = {s: (b.last_price or self.base_prices.get(s, 100.0)) for s, b in self.order_books.items()}
                    trends = {s: self._calculate_trend(s) for s in self.order_books}
                    bullish = sum(1 for t in trends.values() if t == "Bullish")
                    bearish = sum(1 for t in trends.values() if t == "Bearish")
                    self.market_sentiment = "bullish" if bullish > bearish else ("bearish" if bearish > bullish else "neutral")
                    self._update_market_analytics()
                    latest_metrics = self.market_metrics_history[-1] if self.market_metrics_history else {}
                    benchmark_value = self.benchmark_history[-1]["value"] if self.benchmark_history else 100.0
                    market_state = {
                        "day": self.day,
                        "session": self.session,
                        "session_phase": self.session_phase,
                        "time": clock_time,
                        "prices": prices,
                        "trends": trends,
                        "sentiment": self.market_sentiment,
                        "volume_level": "High" if day_events else "Normal",
                        "is_high_volume": bool(day_events),
                        "timestamp": utcnow(),
                        "events": [{"title": e.title, "severity": e.severity} for e in day_events],
                        "full_events": [e.model_dump(mode="json") for e in day_events],
                        "halted": self.halted_stocks,
                        "financial_report": report_data,
                        "regime": self.current_regime,
                        "regime_headline": self.current_regime_profile["headline"],
                        "benchmark_return_pct": benchmark_value - 100.0,
                        "breadth_ratio": latest_metrics.get("breadth", {}).get("breadth_ratio", 0.5),
                        "realized_vol_pct": latest_metrics.get("realized_vol_pct", 0.0),
                        "liquidity_regime": self.liquidity_regime,
                        "latency_ms": self.latency_ms,
                        "spreads_bps": {symbol: self._spread_bps(symbol) for symbol in self.order_books},
                        "order_imbalance": dict(self.order_imbalance),
                    }
                    news = "; ".join(f"{e.title} ({e.severity})" for e in day_events) if day_events else "Tape is balanced; no new catalyst shock."
                    await self.step(market_state, news)
                    for agent in self.agents:
                        agent._regime_performance[self.current_regime] = {"portfolio_value": agent.total_value}
                    if self.session == self.sessions_per_day:
                        self._generate_forum_posts(self.day)
                        self._take_snapshot()
                except Exception as exc:
                    logger.error("Step %s (day %s session %s) error: %s", step_index, self.day, self.session, exc, exc_info=True)
                    self._emit_run_event("step_error", {"day": self.day, "session": self.session, "error": str(exc)})
                if self.ws_broadcast:
                    try:
                        await self.ws_broadcast({"type": "tick", "run_id": self.active_run_id, "day": self.day, "session": self.session, "session_phase": self.session_phase, "prices": {s: (b.last_price or 100.0) for s, b in self.order_books.items()}, "trades": self.total_trade_count, "agents": len([a for a in self.agents if a.status == "active"]), "halted": list(self.halted_stocks), "events": [{"title": e.title, "severity": e.severity} for e in day_events], "regime": self.current_regime, "benchmark": self.benchmark_history[-1] if self.benchmark_history else {"value": 100.0}})
                    except Exception:
                        pass
                await asyncio.sleep(max(self.speed, 0.0))
        finally:
            if self._run_id != my_run_id:
                return
            self.is_running = False
            final_status = "completed" if self._run_stop_reason == "completed" else "stopped"
            if self.research_store and self.active_run_id:
                self.research_store.update_run(self.active_run_id, status=final_status, summary={"day": self.day, "session": self.session, "session_phase": self.session_phase, "total_trades": self.total_trade_count, "regime": self.current_regime, "market_sentiment": self.market_sentiment})
            final_event = "run_completed" if final_status == "completed" else "run_stopped"
            self._emit_run_event(final_event, {"day": self.day, "total_days": self.total_days})
            for agent in self.agents:
                if isinstance(agent, StrategyAgent):
                    agent.strategy.on_run_end(agent.context, agent.finalize_metrics())
            if self.ws_broadcast:
                try:
                    await self.ws_broadcast({"type": "complete", "run_id": self.active_run_id, "day": self.day, "total_days": self.total_days})
                except Exception:
                    pass
