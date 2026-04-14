import uuid
import json
import math
import asyncio
import logging
import random
from typing import Dict, Any, Optional, List
from backend.app.core.prompt_factory import PromptFactory
from backend.app.models.types import Order, OrderSide, OrderType, Loan, LoanStatus
from backend.app.core.llm_provider import LLMFactory

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  CHARACTER THRESHOLDS  (v1.0 parity)
# ═══════════════════════════════════════════════════════════════

CHARACTER_PROFILES = {
    "Conservative":    {"buy_threshold": 0.70, "sell_threshold": 0.20, "trade_size_pct": 0.10, "loan_prob": 0.10},
    "Aggressive":      {"buy_threshold": 0.40, "sell_threshold": 0.50, "trade_size_pct": 0.30, "loan_prob": 0.50},
    "Balanced":        {"buy_threshold": 0.55, "sell_threshold": 0.35, "trade_size_pct": 0.15, "loan_prob": 0.25},
    "Growth-Oriented": {"buy_threshold": 0.50, "sell_threshold": 0.30, "trade_size_pct": 0.20, "loan_prob": 0.35},
}

CHARACTER_LIST = list(CHARACTER_PROFILES.keys())

# ═══════════════════════════════════════════════════════════════
#  PREDEFINED LLM PERSONAS  (6 named agents)
# ═══════════════════════════════════════════════════════════════

AGENT_PERSONAS = [
    {
        "name": "Warren", "type": "Conservative",
        "description": "A cautious value investor who prefers stable, established companies.",
        "strategy_style": "value",
        "risk_tolerance": "Low",
        "bias_profile": {"herding": "Low", "loss_aversion": "High", "overconfidence": "Low", "anchoring": "High"},
    },
    {
        "name": "Catherine", "type": "Aggressive",
        "description": "A bold trader who seeks high returns through active trading and momentum plays.",
        "strategy_style": "momentum",
        "risk_tolerance": "High",
        "bias_profile": {"herding": "High", "loss_aversion": "Low", "overconfidence": "High", "anchoring": "Low"},
    },
    {
        "name": "Ray", "type": "Balanced",
        "description": "A diversified investor who balances risk and reward carefully.",
        "strategy_style": "quality",
        "risk_tolerance": "Medium",
        "bias_profile": {"herding": "Medium", "loss_aversion": "Medium", "overconfidence": "Low", "anchoring": "Medium"},
    },
    {
        "name": "Satoshi", "type": "Growth-Oriented",
        "description": "A growth chaser who targets emerging sectors and high-growth opportunities.",
        "strategy_style": "event_driven",
        "risk_tolerance": "Medium-High",
        "bias_profile": {"herding": "Medium", "loss_aversion": "Low", "overconfidence": "Medium", "anchoring": "Low"},
    },
    {
        "name": "Janet", "type": "Conservative",
        "description": "An institutional investor focused on capital preservation and dividend income.",
        "strategy_style": "macro",
        "risk_tolerance": "Low",
        "bias_profile": {"herding": "Low", "loss_aversion": "High", "overconfidence": "Low", "anchoring": "High"},
    },
    {
        "name": "Elon", "type": "Aggressive",
        "description": "A high-conviction trader who makes concentrated bets based on bold visions.",
        "strategy_style": "contrarian",
        "risk_tolerance": "Very High",
        "bias_profile": {"herding": "Low", "loss_aversion": "Low", "overconfidence": "High", "anchoring": "Low"},
    },
]


# ═══════════════════════════════════════════════════════════════
#  BASE AGENT  (shared logic for both LLM and Rule-Based)
# ═══════════════════════════════════════════════════════════════

class BaseAgent:
    """Common logic shared by BehavioralAgent (LLM) and RuleBasedAgent."""

    agent_kind: str = "base"  # overridden by subclasses

    def __init__(self, agent_id: str, persona: Dict[str, Any],
                 initial_cash: float, initial_holdings: Dict[str, int],
                 initial_prices: Dict[str, float]):
        self.id = agent_id
        self.persona = persona

        self.wallet = {
            "cash": float(initial_cash),
            "holdings": dict(initial_holdings),
            "initial_cash": float(initial_cash),
            "initial_holdings": dict(initial_holdings),
        }
        self.initial_prices = dict(initial_prices)
        self.pnl = 0.0
        self.total_value = float(initial_cash)
        self.trade_count = 0
        self.status = "active"  # active / bankrupt
        self.logger = logging.getLogger(f"agent.{agent_id}")

        # ── Loans ──
        self.loans: List[Loan] = []

        # ── Decision Log (explainability) ──
        self.decision_log: List[Dict] = []

        # ── Analytics tracking ──
        self._pnl_history: List[float] = []   # PnL at end of each session
        self._portfolio_history: List[float] = []
        self._peak_value: float = float(initial_cash)
        self._max_drawdown: float = 0.0
        self._profitable_sessions: int = 0    # sessions where PnL improved
        self._sessions_count: int = 0         # total sessions measured
        self._total_trade_qty: int = 0
        self._last_action: str = "hold"
        self._strategy_drift_count: int = 0
        self._thesis_reversal_count: int = 0
        self._consistency_score: float = 100.0
        self._regime_performance: Dict[str, Dict[str, float]] = {}

    # ── Character profile lookup ──
    @property
    def _char(self) -> Dict:
        return CHARACTER_PROFILES.get(self.persona.get("type", "Balanced"), CHARACTER_PROFILES["Balanced"])

    # ── PnL ──
    def _initial_total_value(self, current_prices: Dict[str, float]) -> float:
        ih = self.wallet["initial_holdings"]
        return self.wallet["initial_cash"] + sum(
            ih.get(s, 0) * self.initial_prices.get(s, 100.0) for s in current_prices
        )

    def _update_pnl(self, current_prices: Dict[str, float]):
        assets_value = sum(
            self.wallet["holdings"].get(s, 0) * p for s, p in current_prices.items()
        )
        self.total_value = self.wallet["cash"] + assets_value - self.total_debt
        initial_total = self._initial_total_value(current_prices)
        self.pnl = self.total_value - initial_total

        # Analytics: track peak + drawdown
        if self.total_value > self._peak_value:
            self._peak_value = self.total_value
        drawdown = (self._peak_value - self.total_value) / self._peak_value if self._peak_value > 0 else 0
        if drawdown > self._max_drawdown:
            self._max_drawdown = drawdown

        # FIX H7: Track win rate as sessions with positive portfolio return (value increased vs prior session)
        if self._portfolio_history:
            self._sessions_count += 1
            if self.total_value > self._portfolio_history[-1]:
                self._profitable_sessions += 1
        self._pnl_history.append(self.pnl)
        self._portfolio_history.append(self.total_value)

    # ── Loans ──
    @property
    def total_debt(self) -> float:
        return sum(l.remaining for l in self.loans if l.status == LoanStatus.ACTIVE)

    def add_loan(self, loan: Loan):
        self.loans.append(loan)
        self.wallet["cash"] += loan.amount

    def process_loan_repayment(self, current_day: int, current_prices: Dict[str, float]):
        for loan in self.loans:
            if loan.status != LoanStatus.ACTIVE:
                continue
            if current_day >= loan.due_day:
                repayment = loan.remaining * (1 + loan.interest_rate)
                if self.wallet["cash"] >= repayment:
                    self.wallet["cash"] -= repayment
                    loan.remaining = 0
                    loan.status = LoanStatus.REPAID
                else:
                    # Default → bankruptcy
                    loan.status = LoanStatus.DEFAULTED
                    self._bankrupt(current_prices)

    def _bankrupt(self, current_prices: Dict[str, float]):
        """Forced liquidation on bankruptcy."""
        self.status = "bankrupt"
        for sym in list(self.wallet["holdings"].keys()):
            held = self.wallet["holdings"].get(sym, 0)
            if held > 0:
                price = current_prices.get(sym, 0)
                self.wallet["cash"] += held * price
                self.wallet["holdings"][sym] = 0
        # Pay off as much debt as possible
        for loan in self.loans:
            if loan.status == LoanStatus.ACTIVE:
                payable = min(self.wallet["cash"], loan.remaining)
                self.wallet["cash"] -= payable
                loan.remaining -= payable
                if loan.remaining <= 0:
                    loan.status = LoanStatus.REPAID
                else:
                    loan.status = LoanStatus.DEFAULTED

    # ── Decision Logging ──
    def _log_decision(self, day: int, session: int, action: str,
                      stock: Optional[str], qty: int, price: float,
                      reasoning: str, biases: List[str], memo: Optional[Dict[str, Any]] = None):
        memo = memo or {
            "thesis": reasoning,
            "catalyst": "technical setup",
            "risk": "market noise",
            "horizon_days": 5,
            "conviction": 50,
            "exposure_impact": "maintain",
        }
        if self._last_action and action != "hold" and self._last_action != "hold" and action != self._last_action:
            self._strategy_drift_count += 1
            self._thesis_reversal_count += 1
            self._consistency_score = max(0.0, self._consistency_score - 4.5)
        elif action == self._last_action and action != "hold":
            self._consistency_score = min(100.0, self._consistency_score + 0.5)
        elif action == "hold":
            self._consistency_score = min(100.0, self._consistency_score + 0.2)
        self._last_action = action
        entry = {
            "day": day, "session": session,
            "action": action, "stock": stock,
            "quantity": qty, "price": round(price, 2),
            "reasoning": reasoning, "biases": biases,
            "memo": memo,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }
        self.decision_log.append(entry)

    def _record_trade(self, qty: int):
        self.trade_count += 1
        self._total_trade_qty += qty

    # ── Snapshot ──
    def get_snapshot(self, current_prices: Dict[str, float]) -> Dict:
        self._update_pnl(current_prices)
        init_total = self._initial_total_value(current_prices)
        return {
            "id": str(self.id),
            "name": self.persona.get("name", f"Agent {self.id}"),
            "character_type": self.persona.get("type", "Balanced"),
            "agent_kind": self.agent_kind,
            "cash": round(self.wallet["cash"], 2),
            "holdings": dict(self.wallet["holdings"]),
            "pnl": round(self.pnl, 2),
            "pnl_pct": round((self.pnl / init_total * 100) if init_total else 0, 2),
            "total_value": round(self.total_value, 2),
            "trades": self.trade_count,
            "status": self.status,
            "debt": round(self.total_debt, 2),
            "bias_profile": self.persona.get("bias_profile", {}),
            "description": self.persona.get("description", ""),
            "strategy_style": self.persona.get("strategy_style", "balanced"),
            "risk_tolerance": self.persona.get("risk_tolerance", "Medium"),
            "consistency_score": round(self._consistency_score, 1),
        }

    # ── Analytics ──
    def get_analytics(self) -> Dict:
        # FIX C3: Sharpe ratio now uses portfolio returns (not PnL diffs) and √1008 annualization (4 sessions/day)
        sharpe = 0.0
        if len(self._portfolio_history) > 2:
            returns = []
            for i in range(1, len(self._portfolio_history)):
                prev = self._portfolio_history[i - 1]
                if prev > 0:
                    returns.append((self._portfolio_history[i] - prev) / prev)
            mean_r = sum(returns) / len(returns) if returns else 0
            std_r = (sum((r - mean_r) ** 2 for r in returns) / len(returns)) ** 0.5 if returns else 1
            sharpe = round((mean_r / std_r) * math.sqrt(1008) if std_r > 0 else 0, 3)

        return {
            "agent_id": str(self.id),
            "sharpe_ratio": sharpe,
            "max_drawdown": round(self._max_drawdown * 100, 2),
            # FIX H7: Win rate = sessions with positive portfolio return / total sessions (standard per-period definition)
            "win_rate": round(self._profitable_sessions / self._sessions_count * 100, 1) if self._sessions_count else 0,
            "avg_trade_size": round(self._total_trade_qty / self.trade_count, 1) if self.trade_count else 0,
            "total_trades": self.trade_count,
            "consistency_score": round(self._consistency_score, 1),
            "strategy_drift_count": self._strategy_drift_count,
            "thesis_reversal_count": self._thesis_reversal_count,
        }


# ═══════════════════════════════════════════════════════════════
#  BEHAVIORAL AGENT  (LLM-powered)
# ═══════════════════════════════════════════════════════════════

class BehavioralAgent(BaseAgent):
    agent_kind = "llm"

    def __init__(self, agent_id: str, persona: Dict[str, Any],
                 initial_cash: float, initial_holdings: Dict[str, int],
                 initial_prices: Dict[str, float]):
        super().__init__(agent_id, persona, initial_cash, initial_holdings, initial_prices)
        try:
            self.llm = LLMFactory.create_provider()
        except Exception:
            self.logger.warning("LLM Provider failed to init, agent will use demo mode.")
            self.llm = None

    # ── Bias determination ──
    def _determine_biases(self, market_state: Dict[str, Any]) -> List[str]:
        active_biases = []
        bp = self.persona.get("bias_profile", {})

        if self.pnl < 0 and bp.get("loss_aversion", "Medium") != "Low":
            active_biases.append("loss_aversion")
        if market_state.get("is_high_volume", False) and bp.get("herding", "Medium") != "Low":
            active_biases.append("herding")

        init_val = self._initial_total_value(market_state["prices"])
        if init_val > 0 and (self.pnl / init_val) > 0.15 and bp.get("overconfidence", "Medium") != "Low":
            active_biases.append("overconfidence")

        if bp.get("anchoring", "Medium") != "Low":
            for sym, price in market_state["prices"].items():
                init_p = self.initial_prices.get(sym, 100.0)
                if init_p > 0 and abs(price - init_p) / init_p > 0.10:
                    active_biases.append("anchoring")
                    break
        return active_biases

    # ── Demo fallback ──
    def _demo_act(self, market_state: Dict[str, Any]) -> Optional[Order]:
        self._update_pnl(market_state["prices"])
        cp = self._char
        buy_threshold = cp["buy_threshold"]
        trade_pct = cp["trade_size_pct"]

        trends = market_state.get("trends", {})
        bullish = sum(1 for t in trends.values() if t == "Bullish")
        bearish = sum(1 for t in trends.values() if t == "Bearish")
        if bullish > bearish:
            buy_threshold -= 0.10
        elif bearish > bullish:
            buy_threshold += 0.10

        available = [s for s in market_state["prices"] if s not in market_state.get("halted", set())]
        if not available:
            return None

        roll = random.random()
        symbol = random.choice(available)
        price = market_state["prices"].get(symbol, 100.0)

        if roll < buy_threshold * 0.6:
            held = self.wallet["holdings"].get(symbol, 0)
            if held <= 0:
                return None
            qty = max(1, int(held * trade_pct))
            sell_price = round(price * random.uniform(0.98, 1.02), 2)
            self._record_trade(qty)
            memo = {
                "thesis": f"Trim exposure in {symbol} as simulated momentum softens.",
                "catalyst": market_state.get("regime", "neutral").replace("_", " "),
                "risk": "missing a rebound in crowded selling",
                "horizon_days": 3,
                "conviction": 48,
                "exposure_impact": "reduce",
            }
            self._log_decision(market_state.get("day", 0), market_state.get("session", 0),
                               "sell", symbol, qty, sell_price, "Demo fallback sell", [], memo)
            return Order(id=str(uuid.uuid4()), agent_id=str(self.id),
                         stock_symbol=symbol, side=OrderSide.SELL,
                         type=OrderType.LIMIT, price=sell_price, quantity=qty,
                         timestamp=market_state.get("timestamp"))
        elif roll > buy_threshold:
            budget = self.wallet["cash"] * trade_pct
            if budget < price:
                return None
            qty = max(1, int(budget / price))
            buy_price = round(price * random.uniform(0.98, 1.02), 2)
            self._record_trade(qty)
            memo = {
                "thesis": f"Add to {symbol} on supportive simulated trend and breadth.",
                "catalyst": market_state.get("regime", "neutral").replace("_", " "),
                "risk": "trend could reverse before thesis horizon",
                "horizon_days": 5,
                "conviction": 62,
                "exposure_impact": "increase",
            }
            self._log_decision(market_state.get("day", 0), market_state.get("session", 0),
                               "buy", symbol, qty, buy_price, "Demo fallback buy", [], memo)
            return Order(id=str(uuid.uuid4()), agent_id=str(self.id),
                         stock_symbol=symbol, side=OrderSide.BUY,
                         type=OrderType.LIMIT, price=buy_price, quantity=qty,
                         timestamp=market_state.get("timestamp"))

        memo = {
            "thesis": "Hold current exposure while signal quality stays mixed.",
            "catalyst": market_state.get("regime", "neutral").replace("_", " "),
            "risk": "opportunity cost from inactivity",
            "horizon_days": 2,
            "conviction": 35,
            "exposure_impact": "maintain",
        }
        self._log_decision(market_state.get("day", 0), market_state.get("session", 0),
                           "hold", None, 0, 0, "Demo fallback hold", [], memo)
        return None

    # ── LLM Mode ──
    async def act(self, market_state: Dict[str, Any], news: str) -> Optional[Order]:
        if self.status == "bankrupt":
            return None
        if not self.llm:
            return self._demo_act(market_state)

        self._update_pnl(market_state["prices"])
        biases = self._determine_biases(market_state)
        profile_snapshot = {**self.persona, "wallet": self.wallet, "pnl": self.pnl}
        profile_snapshot["total_debt"] = self.total_debt
        available_stocks = [s for s in market_state["prices"] if s not in market_state.get("halted", set())]

        prompt = PromptFactory.create_trade_prompt(
            agent_profile=profile_snapshot,
            market_state=market_state,
            active_biases=biases,
            news=news,
            available_stocks=available_stocks,
        )

        try:
            response_str = await asyncio.to_thread(
                self.llm.generate,
                prompt=prompt,
                system_message="You are a realistic trading agent. Output JSON only."
            )
            data = json.loads(response_str)
            action = data.get("action", "hold").lower()
            reasoning = data.get("reasoning", "LLM decision")
            memo = {
                "thesis": data.get("thesis", reasoning),
                "catalyst": data.get("catalyst", market_state.get("regime", "neutral").replace("_", " ")),
                "risk": data.get("risk", "market volatility"),
                "horizon_days": int(data.get("horizon_days", 5) or 5),
                "conviction": max(1, min(100, int(data.get("conviction", 55) or 55))),
                "exposure_impact": data.get("exposure_impact", "maintain"),
            }

            if action == "hold" or data.get("stock") not in available_stocks:
                self._log_decision(market_state.get("day", 0), market_state.get("session", 0),
                                   "hold", data.get("stock"), 0, 0, reasoning, biases, memo)
                return None

            price = float(data.get("price", 0.0))
            qty = int(data.get("quantity", 0))
            stock = data["stock"]

            if qty <= 0 or price <= 0:
                return None

            conviction_scale = max(0.25, memo["conviction"] / 100.0)
            max_budget = self.wallet["cash"] * min(0.35, self._char["trade_size_pct"] * (0.7 + conviction_scale))
            if action == "buy" and price * qty > self.wallet["cash"]:
                qty = int(self.wallet["cash"] / price)
                if qty <= 0:
                    return None
            elif action == "buy" and price * qty > max_budget:
                qty = max(1, int(max_budget / price))
            if action == "sell" and qty > self.wallet["holdings"].get(stock, 0):
                qty = self.wallet["holdings"].get(stock, 0)
                if qty <= 0:
                    return None
            if action == "sell":
                qty = min(qty, max(1, int(self.wallet["holdings"].get(stock, 0) * 0.6)))

            self._record_trade(qty)
            self._log_decision(market_state.get("day", 0), market_state.get("session", 0),
                               action, stock, qty, price, reasoning, biases, memo)
            return Order(
                id=str(uuid.uuid4()), agent_id=str(self.id),
                stock_symbol=stock,
                side=OrderSide.BUY if action == "buy" else OrderSide.SELL,
                type=OrderType.LIMIT, price=price, quantity=qty,
                timestamp=market_state.get("timestamp"),
            )
        except Exception as e:
            self.logger.error(f"Agent {self.id} LLM error: {e}, falling back to demo")
            return self._demo_act(market_state)


# ═══════════════════════════════════════════════════════════════
#  RULE-BASED AGENT  (no LLM, pure thresholds)
# ═══════════════════════════════════════════════════════════════

class RuleBasedAgent(BaseAgent):
    agent_kind = "rule"

    def __init__(self, agent_id: str, character_type: str, name: str,
                 initial_cash: float, initial_holdings: Dict[str, int],
                 initial_prices: Dict[str, float]):
        persona = {
            "name": name,
            "type": character_type,
            "description": f"Rule-based {character_type} trader",
            "strategy_style": {
                "Conservative": "value",
                "Aggressive": "momentum",
                "Balanced": "quality",
                "Growth-Oriented": "event_driven",
            }.get(character_type, "balanced"),
            "risk_tolerance": {"Conservative": "Low", "Aggressive": "High",
                               "Balanced": "Medium", "Growth-Oriented": "Medium-High"}.get(character_type, "Medium"),
            "bias_profile": {},
        }
        super().__init__(agent_id, persona, initial_cash, initial_holdings, initial_prices)

    def demo_act(self, market_state: Dict[str, Any]) -> Optional[Order]:
        """Pure rule-based trading decision."""
        if self.status == "bankrupt":
            return None

        self._update_pnl(market_state["prices"])
        cp = self._char
        buy_threshold = cp["buy_threshold"]
        sell_threshold = cp["sell_threshold"]
        trade_pct = cp["trade_size_pct"]

        # Sentiment adjustments (matching v1.0)
        sentiment = market_state.get("sentiment", "neutral")
        if sentiment == "bullish":
            buy_threshold -= 0.10
        elif sentiment == "bearish":
            sell_threshold += 0.10

        # Trend-based adjustments
        trends = market_state.get("trends", {})
        bullish = sum(1 for t in trends.values() if t == "Bullish")
        bearish = sum(1 for t in trends.values() if t == "Bearish")
        if bullish > bearish:
            buy_threshold -= 0.05
        elif bearish > bullish:
            buy_threshold += 0.05

        available = [s for s in market_state["prices"] if s not in market_state.get("halted", set())]
        if not available:
            return None

        roll = random.random()

        if roll > buy_threshold:
            # BUY — pick stock with best recent trend
            symbol = self._pick_stock(available, market_state, prefer_bullish=True)
            price = market_state["prices"].get(symbol, 100.0)
            budget = self.wallet["cash"] * trade_pct
            if budget < price:
                memo = {
                    "thesis": "Maintain posture until enough cash is available for a sized position.",
                    "catalyst": market_state.get("regime", "neutral").replace("_", " "),
                    "risk": "cash drag during a rally",
                    "horizon_days": 2,
                    "conviction": 30,
                    "exposure_impact": "maintain",
                }
                self._log_decision(market_state.get("day", 0), market_state.get("session", 0),
                                   "hold", None, 0, 0, "Insufficient cash", [], memo)
                return None
            qty = max(1, int(budget / price))
            buy_price = round(price * random.uniform(0.98, 1.02), 2)
            self._record_trade(qty)
            memo = {
                "thesis": f"Increase {symbol} exposure as rule-based signals align with {sentiment} tape.",
                "catalyst": market_state.get("regime", "neutral").replace("_", " "),
                "risk": "false positive trend signal",
                "horizon_days": 4,
                "conviction": int(min(85, max(40, roll * 100))),
                "exposure_impact": "increase",
            }
            self._log_decision(market_state.get("day", 0), market_state.get("session", 0),
                               "buy", symbol, qty, buy_price,
                               f"Rule: roll={roll:.2f} > buy_threshold={buy_threshold:.2f}", [], memo)
            return Order(id=str(uuid.uuid4()), agent_id=str(self.id),
                         stock_symbol=symbol, side=OrderSide.BUY,
                         type=OrderType.LIMIT, price=buy_price, quantity=qty,
                         timestamp=market_state.get("timestamp"))

        elif roll < sell_threshold:
            # SELL — pick held stock
            held_stocks = [s for s in available if self.wallet["holdings"].get(s, 0) > 0]
            if not held_stocks:
                memo = {
                    "thesis": "No risk can be reduced because the current book is empty.",
                    "catalyst": market_state.get("regime", "neutral").replace("_", " "),
                    "risk": "staying underinvested",
                    "horizon_days": 1,
                    "conviction": 20,
                    "exposure_impact": "maintain",
                }
                self._log_decision(market_state.get("day", 0), market_state.get("session", 0),
                                   "hold", None, 0, 0, "Nothing to sell", [], memo)
                return None
            symbol = random.choice(held_stocks)
            price = market_state["prices"].get(symbol, 100.0)
            held = self.wallet["holdings"][symbol]
            qty = max(1, int(held * min(trade_pct, 0.5)))
            sell_price = round(price * random.uniform(0.98, 1.02), 2)
            self._record_trade(qty)
            memo = {
                "thesis": f"Reduce {symbol} after a weaker signal profile and tighter risk conditions.",
                "catalyst": market_state.get("regime", "neutral").replace("_", " "),
                "risk": "selling too early into strength",
                "horizon_days": 3,
                "conviction": int(min(80, max(35, (1 - roll) * 100))),
                "exposure_impact": "reduce",
            }
            self._log_decision(market_state.get("day", 0), market_state.get("session", 0),
                               "sell", symbol, qty, sell_price,
                               f"Rule: roll={roll:.2f} < sell_threshold={sell_threshold:.2f}", [], memo)
            return Order(id=str(uuid.uuid4()), agent_id=str(self.id),
                         stock_symbol=symbol, side=OrderSide.SELL,
                         type=OrderType.LIMIT, price=sell_price, quantity=qty,
                         timestamp=market_state.get("timestamp"))

        memo = {
            "thesis": "Signal quality is balanced, so hold current book.",
            "catalyst": market_state.get("regime", "neutral").replace("_", " "),
            "risk": "missed move while staying neutral",
            "horizon_days": 2,
            "conviction": 42,
            "exposure_impact": "maintain",
        }
        self._log_decision(market_state.get("day", 0), market_state.get("session", 0),
                           "hold", None, 0, 0,
                           f"Rule: {sell_threshold:.2f} <= roll={roll:.2f} <= {buy_threshold:.2f}", [], memo)
        return None

    async def act(self, market_state: Dict[str, Any], news: str) -> Optional[Order]:
        """Rule-based agents always use demo_act regardless of news."""
        return self.demo_act(market_state)

    def _pick_stock(self, available: List[str], market_state: Dict, prefer_bullish: bool) -> str:
        """Pick a stock based on trend preference."""
        trends = market_state.get("trends", {})
        if prefer_bullish:
            bullish = [s for s in available if trends.get(s) == "Bullish"]
            if bullish:
                return random.choice(bullish)
        else:
            bearish = [s for s in available if trends.get(s) == "Bearish"]
            if bearish:
                return random.choice(bearish)
        return random.choice(available)
