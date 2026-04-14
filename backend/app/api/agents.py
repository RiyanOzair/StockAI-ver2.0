"""Agent endpoints — list, detail, analytics, custom creation, decisions."""
import uuid
import random
import logging
from fastapi import APIRouter, HTTPException
import backend.app.state as state
from backend.app.state import STOCKS, ALL_SYMBOLS
from backend.app.agents.behavioral_agent import BehavioralAgent, RuleBasedAgent, AGENT_PERSONAS
from backend.app.agents.strategy_agent import StrategyAgent, build_strategy
from backend.app.models.types import CustomAgentRequest
from backend.app.core.analytics import compute_agent_metrics

router = APIRouter(prefix="/agents", tags=["agents"])
logger = logging.getLogger("api.agents")


@router.get("")
async def get_agents():
    prices = {s: (b.last_price or 100.0) for s, b in state.market_books.items()}
    return [a.get_snapshot(prices) for a in state.agents]


@router.get("/{agent_id}/decisions")
async def get_decisions(agent_id: str, offset: int = 0, limit: int = 200):
    for a in state.agents:
        if str(a.id) == agent_id:
            decisions = a.decision_log[offset : offset + limit] if offset or limit != 200 else a.decision_log
            return {"agent_id": agent_id, "decisions": decisions}
    raise HTTPException(404, "Agent not found")


@router.get("/{agent_id}/analytics")
async def get_analytics(agent_id: str):
    prices = {s: (b.last_price or STOCKS[s].initial_price) for s, b in state.market_books.items()}
    for a in state.agents:
        if str(a.id) == agent_id:
            return compute_agent_metrics(a, state.simulation, prices, STOCKS)
    raise HTTPException(404, "Agent not found")


@router.post("/custom")
async def create_custom_agent(req: CustomAgentRequest):
    """Inject a user-defined agent into the running simulation."""
    initial_prices = {sym: (state.market_books[sym].last_price or STOCKS[sym].initial_price) for sym in STOCKS}
    cash = float(req.initial_cash)
    holdings = {}
    chosen = random.sample(ALL_SYMBOLS, min(3, len(ALL_SYMBOLS)))
    for sym in chosen:
        price = initial_prices[sym]
        holdings[sym] = max(1, int(5000 / price))

    new_id = str(uuid.uuid4())
    persona = {
        "name": req.name,
        "type": req.character_type,
        "description": req.description or f"Custom {req.character_type} agent",
        "risk_tolerance": req.risk_tolerance,
        "bias_profile": {},
    }
    agent_kind = (req.agent_kind or ("llm" if req.use_llm else "rule")).lower()
    if agent_kind == "strategy" or req.strategy_id:
        strategy_id = req.strategy_id or "mean_reversion"
        agent = StrategyAgent(
            agent_id=new_id,
            name=req.name,
            strategy=build_strategy(strategy_id, req.config),
            strategy_id=strategy_id,
            initial_cash=cash,
            initial_holdings=holdings,
            initial_prices=initial_prices,
            dataset_version=state.simulation.dataset_version,
            scenario_id=state.simulation.scenario_id,
            universe_id=state.simulation.universe_id,
            seed=getattr(state.simulation, "seed", None),
            training_mode=state.simulation.training_mode,
        )
        agent.set_run_id(state.simulation.active_run_id or "ad-hoc")
    elif agent_kind == "rule" or not req.use_llm:
        agent = RuleBasedAgent(
            agent_id=new_id,
            character_type=req.character_type,
            name=req.name,
            initial_cash=cash,
            initial_holdings=holdings,
            initial_prices=initial_prices,
        )
    else:
        agent = BehavioralAgent(
            agent_id=new_id,
            persona=persona,
            initial_cash=cash,
            initial_holdings=holdings,
            initial_prices=initial_prices,
        )
    state.agents.append(agent)
    state.simulation.agents.append(agent)
    logger.info(f"Custom agent created: {req.name} (id={new_id})")
    return {"message": f"Agent '{req.name}' created", "id": new_id, "agent_kind": agent.agent_kind}


@router.get("/explainability")
async def get_explainability():
    """Aggregate bias counts, decision distributions, and per-agent summaries."""
    bias_counts: dict = {}
    action_counts = {"buy": 0, "sell": 0, "hold": 0}
    top_stocks_global: dict = {}
    per_agent = []
    conviction_total = 0
    conviction_count = 0
    thesis_drift_total = 0
    consistency_total = 0

    for a in state.agents:
        agent_action_counts = {"buy": 0, "sell": 0, "hold": 0}
        agent_top_stocks: dict = {}
        active_convictions = []

        for d in a.decision_log:
            act = d.get("action", "hold")
            action_counts[act] = action_counts.get(act, 0) + 1
            agent_action_counts[act] = agent_action_counts.get(act, 0) + 1
            for b in d.get("biases", []):
                bias_counts[b] = bias_counts.get(b, 0) + 1
            stock = d.get("stock")
            if stock:
                top_stocks_global[stock] = top_stocks_global.get(stock, 0) + 1
                agent_top_stocks[stock] = agent_top_stocks.get(stock, 0) + 1
            memo = d.get("memo", {})
            if memo.get("conviction") is not None:
                conviction = float(memo.get("conviction", 0))
                conviction_total += conviction
                conviction_count += 1
                active_convictions.append(conviction)

        thesis_drift_total += getattr(a, "_strategy_drift_count", 0)
        consistency_total += getattr(a, "_consistency_score", 100.0)
        per_agent.append({
            "id": str(a.id),
            "name": a.persona.get("name", f"Agent {a.id}"),
            "type": a.persona.get("type", "Balanced"),
            "kind": a.agent_kind,
            "strategy_style": a.persona.get("strategy_style", "balanced"),
            "bias_profile": a.persona.get("bias_profile", {}),
            "risk_tolerance": a.persona.get("risk_tolerance", "Medium"),
            "decisions": len(a.decision_log),
            "action_counts": agent_action_counts,
            "top_stocks": dict(sorted(agent_top_stocks.items(), key=lambda x: -x[1])[:5]),
            "avg_conviction": round(sum(active_convictions) / len(active_convictions), 1) if active_convictions else 0.0,
            "thesis_drift_count": getattr(a, "_strategy_drift_count", 0),
            "thesis_reversal_count": getattr(a, "_thesis_reversal_count", 0),
            "consistency_score": round(getattr(a, "_consistency_score", 100.0), 1),
        })

    top_stocks_sorted = dict(sorted(top_stocks_global.items(), key=lambda x: -x[1])[:10])
    most_active = max(per_agent, key=lambda x: x["decisions"], default=None)

    return {
        "bias_counts": bias_counts,
        "action_distribution": action_counts,
        "total_decisions": sum(action_counts.values()),
        "per_agent": per_agent,
        "top_stocks_global": top_stocks_sorted,
        "most_active_agent": most_active["name"] if most_active and most_active["decisions"] > 0 else None,
        "avg_conviction": round(conviction_total / conviction_count, 1) if conviction_count else 0.0,
        "thesis_drift_total": thesis_drift_total,
        "decision_consistency_avg": round(consistency_total / len(per_agent), 1) if per_agent else 0.0,
    }
