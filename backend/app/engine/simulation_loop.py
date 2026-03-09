import asyncio
import logging
import math
import random
import uuid
from typing import List, Dict, Optional, Set
from datetime import datetime
from backend.app.agents.behavioral_agent import BaseAgent
from backend.app.models.types import (
    MarketEvent, ForumMessage, Order, FinancialReport, DaySnapshot,
    Loan, LoanStatus, LOAN_TERMS, REPORT_DAYS,
)

logger = logging.getLogger("simulation.loop")

# ═══════════════════════════════════════════════════════════════
#  EVENT TEMPLATES
# ═══════════════════════════════════════════════════════════════

EVENT_TEMPLATES = [
    {"title": "Interest Rate Decision", "type": "monetary_policy", "severity": "HIGH", "impact_range": (-0.03, 0.03)},
    {"title": "Quarterly Earnings Report", "type": "earnings", "severity": "MEDIUM", "impact_range": (-0.02, 0.02)},
    {"title": "Trade Policy Announcement", "type": "policy", "severity": "HIGH", "impact_range": (-0.025, 0.025)},
    {"title": "Market Sentiment Shift", "type": "sentiment", "severity": "MEDIUM", "impact_range": (-0.015, 0.015)},
    {"title": "Product Launch News", "type": "corporate", "severity": "LOW", "impact_range": (-0.005, 0.01)},
    {"title": "Analyst Downgrade", "type": "analyst", "severity": "MEDIUM", "impact_range": (-0.02, 0.005)},
    {"title": "Social Media Buzz", "type": "social", "severity": "LOW", "impact_range": (-0.01, 0.015)},
    {"title": "Economic Data Release", "type": "macro", "severity": "MEDIUM", "impact_range": (-0.015, 0.015)},
    {"title": "M&A Announcement", "type": "corporate", "severity": "HIGH", "impact_range": (-0.01, 0.04)},
    {"title": "Regulatory Change", "type": "regulation", "severity": "HIGH", "impact_range": (-0.03, 0.01)},
]

VOLATILITY_MAP = {"Low": 0.005, "Medium": 0.015, "High": 0.03, "Extreme": 0.05}

# ═══════════════════════════════════════════════════════════════
#  SECTOR CORRELATION MATRIX
# ═══════════════════════════════════════════════════════════════
# Correlation between sectors (symmetric): how much one sector's
# drift spills into another.

SECTOR_NAMES = ["Tech", "Energy", "Finance", "Auto", "Retail", "Entertainment"]

# Upper-triangle pairwise correlations (0-1)
_SECTOR_CORR = {
    ("Tech", "Tech"): 1.0,
    ("Tech", "Energy"): 0.15,
    ("Tech", "Finance"): 0.30,
    ("Tech", "Auto"): 0.35,
    ("Tech", "Retail"): 0.25,
    ("Tech", "Entertainment"): 0.40,
    ("Energy", "Energy"): 1.0,
    ("Energy", "Finance"): 0.25,
    ("Energy", "Auto"): 0.30,
    ("Energy", "Retail"): 0.15,
    ("Energy", "Entertainment"): 0.10,
    ("Finance", "Finance"): 1.0,
    ("Finance", "Auto"): 0.20,
    ("Finance", "Retail"): 0.35,
    ("Finance", "Entertainment"): 0.20,
    ("Auto", "Auto"): 1.0,
    ("Auto", "Retail"): 0.20,
    ("Auto", "Entertainment"): 0.15,
    ("Retail", "Retail"): 1.0,
    ("Retail", "Entertainment"): 0.30,
    ("Entertainment", "Entertainment"): 1.0,
}

def _corr(s1: str, s2: str) -> float:
    return _SECTOR_CORR.get((s1, s2), _SECTOR_CORR.get((s2, s1), 0.0))

CIRCUIT_BREAKER_PCT = 0.10  # 10 % move → halt

LLM_BATCH_SIZE = 5
LLM_BATCH_DELAY = 2.0  # seconds between LLM batches


class SimulationLoop:
    """Main simulation engine with sector correlation, circuit breakers, loans, reports, snapshots."""

    def __init__(self, agents: List[BaseAgent], order_books: Dict, stock_meta: Dict):
        """
        Args:
            agents: list of BaseAgent subclass instances
            order_books: {symbol: OrderBook}
            stock_meta: {symbol: StockMeta}  (from state.py STOCKS dict)
        """
        self.agents = agents
        self.order_books = order_books
        self.stock_meta = stock_meta  # StockMeta objects with sector, volatility_multiplier, etc.

        self.is_running = False
        self.is_paused = False

        self.day = 0
        self.session = 0
        self.total_days = 30
        self.sessions_per_day = 3

        self.speed = 2.0
        self.volatility = "Medium"
        self.event_intensity = 5
        self.use_llm = True
        self.enable_loans = True

        self.all_trades = []
        self.events: List[MarketEvent] = []
        self.forum_messages: List[ForumMessage] = []
        self.financial_reports: List[FinancialReport] = []
        self.price_history: Dict[str, list] = {s: [] for s in order_books}
        self.total_trade_count = 0
        self.halted_stocks: Set[str] = set()
        self.snapshots: List[DaySnapshot] = []

        # WebSocket broadcast callback (set by api/ws.py)
        self.ws_broadcast = None

        # Track session-start prices for circuit breaker calc
        self._session_open: Dict[str, float] = {}

    # ──────────────── Configuration ────────────────

    def configure(self, cfg: dict):
        self.total_days = cfg.get("num_days", self.total_days)
        self.volatility = cfg.get("volatility", self.volatility)
        self.event_intensity = cfg.get("event_intensity", self.event_intensity)
        self.use_llm = cfg.get("use_llm", self.use_llm)
        self.speed = cfg.get("speed", self.speed)
        self.enable_loans = cfg.get("enable_loans", self.enable_loans)

    # ──────────────── Sector Correlation ────────────────

    def _sector_of(self, symbol: str) -> str:
        meta = self.stock_meta.get(symbol)
        return meta.sector if meta else "Tech"

    def _generate_sector_drifts(self, event_impact_by_sector: Dict[str, float]) -> Dict[str, float]:
        """Generate correlated sector-level drifts for one session."""
        raw = {}
        for sector in SECTOR_NAMES:
            base = random.gauss(0, 1) + event_impact_by_sector.get(sector, 0.0) * 20
            raw[sector] = base

        # Apply correlations: blend each sector with correlated sectors
        blended: Dict[str, float] = {}
        for sector in SECTOR_NAMES:
            val = raw[sector]
            for other in SECTOR_NAMES:
                if other != sector:
                    val += raw[other] * _corr(sector, other) * 0.3
            blended[sector] = val
        return blended

    # ──────────────── Price Mechanics ────────────────

    def _calculate_trend(self, symbol: str, window: int = 6) -> str:
        history = self.price_history.get(symbol, [])
        if len(history) < 2:
            return "Neutral"
        recent = history[-window:]
        change = (recent[-1]["price"] - recent[0]["price"]) / recent[0]["price"]
        if change > 0.01:
            return "Bullish"
        elif change < -0.01:
            return "Bearish"
        return "Neutral"

    def _apply_correlated_walk(self, sector_drifts: Dict[str, float]):
        """Apply sector-correlated random walk to each stock."""
        vol = VOLATILITY_MAP.get(self.volatility, 0.015)

        for symbol, book in self.order_books.items():
            if symbol in self.halted_stocks:
                continue
            meta = self.stock_meta.get(symbol)
            vm = meta.volatility_multiplier if meta else 1.0
            sector = self._sector_of(symbol)
            current = book.last_price or (meta.initial_price if meta else 100.0)

            # Sector drift + stock-specific noise
            drift = sector_drifts.get(sector, 0.0) * vol * 0.5
            noise = random.gauss(0, vol * vm)
            change = drift + noise
            new_price = round(max(1.0, current * (1 + change)), 2)

            book.update_price(new_price, self.day, self.session)
            self.price_history.setdefault(symbol, []).append({
                "time": datetime.now().isoformat(),
                "price": new_price,
                "day": self.day,
                "session": self.session,
            })

    # ──────────────── Circuit Breakers ────────────────

    def _check_circuit_breakers(self) -> List[MarketEvent]:
        """Halt stocks that moved > CIRCUIT_BREAKER_PCT in this session."""
        events = []
        for symbol, book in self.order_books.items():
            if symbol in self.halted_stocks:
                continue
            open_price = self._session_open.get(symbol)
            if not open_price or open_price <= 0:
                continue
            current = book.last_price or open_price
            move = abs(current - open_price) / open_price
            if move >= CIRCUIT_BREAKER_PCT:
                self.halted_stocks.add(symbol)
                direction = "up" if current > open_price else "down"
                evt = MarketEvent(
                    id=str(uuid.uuid4()), day=self.day, session=self.session,
                    title=f"Circuit Breaker: {symbol}",
                    description=f"{symbol} halted after {move:.1%} move {direction} in session {self.session}.",
                    severity="HIGH", event_type="circuit_breaker",
                    impact_pct=0.0, affected_stocks=[symbol],
                )
                events.append(evt)
                logger.warning(f"CIRCUIT BREAKER: {symbol} halted ({move:.1%} {direction})")
        return events

    # ──────────────── Events ────────────────

    def _generate_events(self, day: int) -> List[MarketEvent]:
        events = []
        # Milestone events
        if day == max(1, int(self.total_days * 0.25)):
            events.append(MarketEvent(
                id=str(uuid.uuid4()), day=day,
                title="Interest Rate Decision",
                description="Central bank announces rate decision — markets brace for impact.",
                severity="HIGH", event_type="monetary_policy",
                impact_pct=random.uniform(-0.03, 0.03),
            ))
        if day == max(1, int(self.total_days * 0.5)):
            events.append(MarketEvent(
                id=str(uuid.uuid4()), day=day,
                title="Earnings Season Begins",
                description="Major companies report quarterly earnings.",
                severity="HIGH", event_type="earnings",
                impact_pct=random.uniform(-0.02, 0.02),
            ))

        # Random events
        if random.random() < (self.event_intensity / 15.0):
            tmpl = random.choice(EVENT_TEMPLATES)
            # Pick affected sector/stocks
            sector = random.choice(SECTOR_NAMES)
            affected = [s for s, m in self.stock_meta.items() if m.sector == sector]
            events.append(MarketEvent(
                id=str(uuid.uuid4()), day=day,
                title=tmpl["title"],
                description=f"Day {day}: {tmpl['title']} — {sector} sector impacted.",
                severity=tmpl["severity"], event_type=tmpl["type"],
                impact_pct=random.uniform(*tmpl["impact_range"]),
                affected_stocks=affected,
            ))
        return events

    def _event_impact_by_sector(self, events: List[MarketEvent]) -> Dict[str, float]:
        """Aggregate event impacts by sector."""
        impacts: Dict[str, float] = {}
        for e in events:
            if e.affected_stocks:
                for sym in e.affected_stocks:
                    sector = self._sector_of(sym)
                    impacts[sector] = impacts.get(sector, 0) + e.impact_pct
            else:
                # Global event — apply to all sectors
                for sector in SECTOR_NAMES:
                    impacts[sector] = impacts.get(sector, 0) + e.impact_pct
        return impacts

    # ──────────────── Financial Reports ────────────────

    def _generate_financial_reports(self, day: int) -> Optional[Dict[str, Dict]]:
        """Generate quarterly reports on REPORT_DAYS."""
        if day not in REPORT_DAYS:
            return None
        quarter = REPORT_DAYS.index(day) + 1
        report_data: Dict[str, Dict] = {}
        for symbol, meta in self.stock_meta.items():
            rev_growth = random.uniform(-0.10, 0.25)
            margin = random.uniform(0.05, 0.40)
            profit = random.uniform(-50, 200)
            cash_flow = random.uniform(-30, 150)
            sentiment = 0.5 * (1 if rev_growth > 0 else -1) + 0.5 * (1 if profit > 0 else -1)
            sentiment = max(-1.0, min(1.0, sentiment + random.uniform(-0.2, 0.2)))
            report = FinancialReport(
                stock_symbol=symbol, day=day, quarter=quarter,
                revenue_growth=round(rev_growth, 3),
                gross_margin=round(margin, 3),
                net_profit_millions=round(profit, 1),
                cash_flow_millions=round(cash_flow, 1),
                sentiment_score=round(sentiment, 2),
            )
            self.financial_reports.append(report)
            report_data[symbol] = {
                "revenue": profit * 1_000_000 / max(0.01, margin),
                "profit": profit * 1_000_000,
                "margin": margin,
            }
        return report_data

    # ──────────────── Loans ────────────────

    def _process_loans(self, day: int):
        """Process loan offers and repayments for eligible agents."""
        if not self.enable_loans:
            return
        prices = {s: (b.last_price or 100) for s, b in self.order_books.items()}
        for agent in self.agents:
            if agent.status == "bankrupt":
                continue
            agent.process_loan_repayment(day, prices)

            # Offer new loans probabilistically
            if random.random() < agent._char.get("loan_prob", 0.2) and len(agent.loans) < 3:
                term_info = random.choice(LOAN_TERMS)
                amount = round(random.uniform(10000, 50000), 2)
                loan = Loan(
                    id=str(uuid.uuid4()), agent_id=str(agent.id),
                    amount=amount, interest_rate=term_info["rate"],
                    term_days=term_info["term_days"], start_day=day,
                    due_day=day + term_info["term_days"],
                    remaining=amount,
                )
                agent.add_loan(loan)
                logger.info(f"Agent {agent.persona['name']} took loan ${amount:,.0f} ({term_info['label']})")

    # ──────────────── Forum ────────────────

    def _generate_forum_posts(self, day: int):
        active_agents = [a for a in self.agents if a.status == "active"]
        if not active_agents:
            return
        count = min(3, len(active_agents))
        posters = random.sample(active_agents, count)
        prices = {s: (b.last_price or 100.0) for s, b in self.order_books.items()}

        for agent in posters:
            init = agent._initial_total_value(prices)
            pnl_pct = (agent.pnl / init * 100) if init else 0

            if pnl_pct > 5:
                sentiment, pool = "bullish", [
                    f"Market looking strong! Up {pnl_pct:.1f}%",
                    "Great opportunity — loading up on shares!",
                    "My analysis says we're heading higher.",
                ]
            elif pnl_pct < -5:
                sentiment, pool = "bearish", [
                    f"Down {abs(pnl_pct):.1f}% — considering cutting losses",
                    "Reducing exposure, risk feels elevated.",
                    "Cash is king right now.",
                ]
            else:
                sentiment, pool = "neutral", [
                    "Holding steady, waiting for clearer signals.",
                    "Interesting price action today",
                    "Balanced positioning; let's see what's next.",
                ]

            self.forum_messages.append(ForumMessage(
                agent_id=str(agent.id),
                agent_name=agent.persona.get("name", f"Trader {agent.id}"),
                message=random.choice(pool),
                sentiment=sentiment, day=day,
            ))

    # ──────────────── Snapshots ────────────────

    def _take_snapshot(self):
        """Save end-of-day snapshot for rewind."""
        prices = {s: (b.last_price or 100.0) for s, b in self.order_books.items()}
        summaries = [a.get_snapshot(prices) for a in self.agents]
        snap = DaySnapshot(
            day=self.day, prices=prices,
            agent_summaries=summaries,
            total_trades=self.total_trade_count,
            events_count=len([e for e in self.events if e.day == self.day]),
        )
        self.snapshots.append(snap)

    # ──────────────── Core Step ────────────────

    async def step(self, market_state: Dict, news: str):
        logger.info(f"-- Day {self.day}  Session {self.session} --")
        active_agents = [a for a in self.agents if a.status == "active"]

        if self.use_llm:
            # Separate LLM and rule-based agents
            llm_agents = [a for a in active_agents if a.agent_kind == "llm"]
            rule_agents = [a for a in active_agents if a.agent_kind == "rule"]

            results = []
            # Rule-based: all at once (instant)
            for a in rule_agents:
                try:
                    r = a.demo_act(market_state)
                    results.append(r)
                except Exception as e:
                    logger.error(f"Rule agent {a.id} error: {e}")

            # LLM: batched with delay
            for i in range(0, len(llm_agents), LLM_BATCH_SIZE):
                batch = llm_agents[i:i + LLM_BATCH_SIZE]
                tasks = [a.act(market_state, news) for a in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                results.extend(batch_results)
                if i + LLM_BATCH_SIZE < len(llm_agents):
                    await asyncio.sleep(LLM_BATCH_DELAY)
        else:
            results = []
            for a in active_agents:
                try:
                    r = a.demo_act(market_state) if hasattr(a, 'demo_act') else None
                    results.append(r)
                except Exception as e:
                    logger.error(f"Agent {a.id} error: {e}")

        for res in results:
            if isinstance(res, BaseException):
                logger.error(f"Agent error: {res}")
                continue
            if res is not None and isinstance(res, Order):
                symbol = res.stock_symbol
                if symbol in self.halted_stocks:
                    continue
                if symbol in self.order_books:
                    trades = self.order_books[symbol].add_order(res)
                    if trades:
                        logger.info(f"  {len(trades)} trade(s) matched on {symbol}")
                        self._process_trades(trades)
                        self.all_trades.extend(trades)
                        self.total_trade_count += len(trades)

    def _process_trades(self, trades):
        agent_map = {str(a.id): a for a in self.agents}
        for trade in trades:
            buyer = agent_map.get(trade.buyer_agent_id)
            seller = agent_map.get(trade.seller_agent_id)
            cost = trade.price * trade.quantity

            if buyer and buyer.wallet["cash"] >= cost:
                buyer.wallet["cash"] -= cost
                buyer.wallet["holdings"][trade.stock_symbol] = (
                    buyer.wallet["holdings"].get(trade.stock_symbol, 0) + trade.quantity
                )
            if seller:
                seller.wallet["cash"] += cost
                seller.wallet["holdings"][trade.stock_symbol] = max(
                    0, seller.wallet["holdings"].get(trade.stock_symbol, 0) - trade.quantity
                )

    # ──────────────── Main Loop ────────────────

    async def run_simulation(self, steps: Optional[int] = None):
        self.is_running = True
        self.is_paused = False
        total_steps = steps or (self.total_days * self.sessions_per_day)

        for step_i in range(total_steps):
            if not self.is_running:
                break
            while self.is_paused:
                await asyncio.sleep(0.5)
                if not self.is_running:
                    return

            self.day = (step_i // self.sessions_per_day) + 1
            self.session = (step_i % self.sessions_per_day) + 1

            # Circuit breakers last the full trading day — only lift at day open
            if self.session == 1:
                self.halted_stocks.clear()
            self._session_open = {s: (b.last_price or 100.0) for s, b in self.order_books.items()}

            # Events at start of each day
            day_events: List[MarketEvent] = []
            report_data = None
            if self.session == 1:
                day_events = self._generate_events(self.day)
                self.events.extend(day_events)
                # Loans at day start
                self._process_loans(self.day)
                # Financial reports
                report_data = self._generate_financial_reports(self.day)

            # Sector-correlated price movement
            sector_impacts = self._event_impact_by_sector(day_events)
            sector_drifts = self._generate_sector_drifts(sector_impacts)
            self._apply_correlated_walk(sector_drifts)

            # Circuit breakers
            cb_events = self._check_circuit_breakers()
            if cb_events:
                self.events.extend(cb_events)
                day_events.extend(cb_events)

            # Build state snapshot
            prices = {s: (b.last_price or 100.0) for s, b in self.order_books.items()}
            trends = {s: self._calculate_trend(s) for s in self.order_books}

            # Overall sentiment
            bullish = sum(1 for t in trends.values() if t == "Bullish")
            bearish = sum(1 for t in trends.values() if t == "Bearish")
            sentiment = "bullish" if bullish > bearish else ("bearish" if bearish > bullish else "neutral")

            market_state = {
                "day": self.day,
                "session": self.session,
                "time": f"{9 + self.session}:30:00",
                "prices": prices,
                "trends": trends,
                "sentiment": sentiment,
                "volume_level": "High" if day_events else "Normal",
                "is_high_volume": bool(day_events),
                "timestamp": datetime.now(),
                "events": [{"title": e.title, "severity": e.severity} for e in day_events],
                "halted": self.halted_stocks,
                "financial_report": report_data,
            }

            news = (
                "; ".join(f"{e.title} ({e.severity})" for e in day_events)
                if day_events else "Market is stable. No major events."
            )

            await self.step(market_state, news)

            # Forum at end of day
            if self.session == self.sessions_per_day:
                self._generate_forum_posts(self.day)
                self._take_snapshot()

            # WebSocket broadcast
            if self.ws_broadcast:
                try:
                    await self.ws_broadcast({
                        "type": "tick",
                        "day": self.day,
                        "session": self.session,
                        "prices": prices,
                        "trades": self.total_trade_count,
                        "agents": len([a for a in self.agents if a.status == "active"]),
                        "halted": list(self.halted_stocks),
                        "events": [{"title": e.title, "severity": e.severity} for e in day_events],
                    })
                except Exception:
                    pass

            await asyncio.sleep(self.speed)

        self.is_running = False
        logger.info("Simulation complete!")
