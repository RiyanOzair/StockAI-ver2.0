"""Agent endpoints — list, detail, analytics, custom creation, decisions."""
import uuid
import random
import logging
from fastapi import APIRouter, HTTPException
import backend.app.state as state
from backend.app.state import STOCKS, ALL_SYMBOLS
from backend.app.agents.behavioral_agent import BehavioralAgent, RuleBasedAgent, AGENT_PERSONAS
from backend.app.models.types import CustomAgentRequest

router = APIRouter(prefix="/agents", tags=["agents"])
logger = logging.getLogger("api.agents")


@router.get("")
async def get_agents():
    prices = {s: (b.last_price or 100.0) for s, b in state.market_books.items()}
    return [a.get_snapshot(prices) for a in state.agents]


@router.get("/{agent_id}/decisions")
async def get_decisions(agent_id: str):
    for a in state.agents:
        if str(a.id) == agent_id:
            return {"agent_id": agent_id, "decisions": a.decision_log}
    raise HTTPException(404, "Agent not found")


@router.get("/{agent_id}/analytics")
async def get_analytics(agent_id: str):
    for a in state.agents:
        if str(a.id) == agent_id:
            return a.get_analytics()
    raise HTTPException(404, "Agent not found")


@router.post("/custom")
async def create_custom_agent(req: CustomAgentRequest):
    """Inject a user-defined agent into the running simulation."""
    initial_prices = {sym: (state.market_books[sym].last_price or STOCKS[sym].initial_price) for sym in STOCKS}
    cash = 100_000.0
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
    return {"message": f"Agent '{req.name}' created", "id": new_id}


@router.get("/explainability")
async def get_explainability():
    """Aggregate bias counts, decision distributions, and per-agent summaries."""
    bias_counts: dict = {}
    action_counts = {"buy": 0, "sell": 0, "hold": 0}
    top_stocks_global: dict = {}
    per_agent = []

    for a in state.agents:
        agent_action_counts = {"buy": 0, "sell": 0, "hold": 0}
        agent_top_stocks: dict = {}

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

        per_agent.append({
            "id": str(a.id),
            "name": a.persona.get("name", f"Agent {a.id}"),
            "type": a.persona.get("type", "Balanced"),
            "kind": a.agent_kind,
            "bias_profile": a.persona.get("bias_profile", {}),
            "risk_tolerance": a.persona.get("risk_tolerance", "Medium"),
            "decisions": len(a.decision_log),
            "action_counts": agent_action_counts,
            "top_stocks": dict(sorted(agent_top_stocks.items(), key=lambda x: -x[1])[:5]),
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
    }
