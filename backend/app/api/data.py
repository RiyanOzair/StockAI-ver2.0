"""Data endpoints — export, loans, events, forum, event injection."""
import uuid
import json
import logging
from fastapi import APIRouter
import backend.app.state as state
from backend.app.state import STOCKS
from backend.app.models.types import MarketEvent, EventInjection

router = APIRouter(prefix="/data", tags=["data"])
logger = logging.getLogger("api.data")


@router.get("/export")
async def export_data():
    """Full simulation data export as JSON blob."""
    prices = {s: (b.last_price or 100.0) for s, b in state.market_books.items()}
    return {
        "config": {
            "num_agents": len(state.agents),
            "total_days": state.simulation.total_days,
            "volatility": state.simulation.volatility,
            "use_llm": state.simulation.use_llm,
        },
        "stocks": {s: {"name": m.name, "sector": m.sector, "price": prices[s]} for s, m in STOCKS.items()},
        "agents": [a.get_snapshot(prices) for a in state.agents],
        "trades": [
            {
                "trade_id": t.trade_id, "stock": t.stock_symbol,
                "price": t.price, "quantity": t.quantity,
                "buyer": t.buyer_agent_id, "seller": t.seller_agent_id,
                "time": t.timestamp.isoformat() if t.timestamp else "",
            }
            for t in state.simulation.all_trades
        ],
        "events": [
            {"id": e.id, "day": e.day, "title": e.title, "severity": e.severity,
             "type": e.event_type, "impact": round(e.impact_pct * 100, 2)}
            for e in state.simulation.events
        ],
        "forum": [
            {"agent": m.agent_name, "message": m.message, "sentiment": m.sentiment, "day": m.day}
            for m in state.simulation.forum_messages
        ],
        "price_history": {
            sym: hist for sym, hist in state.simulation.price_history.items()
        },
        "loans": [
            {
                "id": l.id, "agent_id": l.agent_id, "amount": l.amount,
                "rate": l.interest_rate, "term": l.term_days,
                "start_day": l.start_day, "due_day": l.due_day,
                "remaining": round(l.remaining, 2), "status": l.status.value,
            }
            for a in state.agents for l in a.loans
        ],
        "financial_reports": [
            {
                "stock": r.stock_symbol, "day": r.day, "quarter": r.quarter,
                "revenue_growth": r.revenue_growth, "margin": r.gross_margin,
                "profit": r.net_profit_millions, "cash_flow": r.cash_flow_millions,
                "sentiment": r.sentiment_score,
            }
            for r in state.simulation.financial_reports
        ],
    }


@router.get("/loans")
async def get_loans():
    all_loans = []
    for a in state.agents:
        for l in a.loans:
            all_loans.append({
                "id": l.id, "agent_id": l.agent_id,
                "agent_name": a.persona.get("name", "Unknown"),
                "amount": l.amount, "rate": l.interest_rate,
                "term": l.term_days, "start": l.start_day, "due": l.due_day,
                "remaining": round(l.remaining, 2), "status": l.status.value,
            })
    return all_loans


@router.get("/events")
async def get_events():
    recent = state.simulation.events[-30:]
    return [
        {
            "id": e.id, "day": e.day, "title": e.title,
            "description": e.description, "severity": e.severity,
            "type": e.event_type, "impact": round(e.impact_pct * 100, 2),
            "affected_stocks": e.affected_stocks,
        }
        for e in reversed(recent)
    ]


@router.get("/forum")
async def get_forum():
    recent = state.simulation.forum_messages[-30:]
    return [
        {"agent_name": m.agent_name, "message": m.message,
         "sentiment": m.sentiment, "day": m.day}
        for m in reversed(recent)
    ]


@router.get("/reports")
async def get_financial_reports():
    return [
        {
            "stock": r.stock_symbol, "day": r.day, "quarter": r.quarter,
            "revenue_growth": r.revenue_growth, "margin": r.gross_margin,
            "profit": r.net_profit_millions, "cash_flow": r.cash_flow_millions,
            "sentiment": r.sentiment_score,
        }
        for r in state.simulation.financial_reports
    ]


@router.post("/event")
async def inject_event(evt: EventInjection):
    """Manually inject a market event."""
    event = MarketEvent(
        id=str(uuid.uuid4()),
        day=state.simulation.day or 1,
        title=evt.title,
        description=evt.description or f"Manually injected: {evt.title}",
        severity=evt.severity,
        event_type="manual",
        impact_pct=evt.impact_pct / 100.0,
        affected_stocks=evt.affected_stocks,
    )
    state.simulation.events.append(event)
    logger.info(f"Event injected: {evt.title}")
    return {"message": "Event injected", "event_id": event.id}
