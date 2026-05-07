import logging
from typing import Optional, Dict, Any
import backend.app.state as state
from fastapi import APIRouter, HTTPException, BackgroundTasks, Header
from pydantic import BaseModel, Field
from backend.app.models.types import SimulationConfig
from backend.app.core.analytics import compute_market_analytics

class ExtendRequest(BaseModel):
    additional_days: int = Field(..., gt=0, description="Must be at least 1")

class NewsInjectionRequest(BaseModel):
    text: str

router = APIRouter(prefix="/simulation", tags=["simulation"])
logger = logging.getLogger("api.simulation")

@router.get("/status")
async def get_status():
    from backend.app.core.config import settings
    sim = state.simulation
    prices = {s: (state.market_books[s].last_price or state.STOCKS[s].initial_price) for s in state.STOCKS}
    analytics = compute_market_analytics(sim, prices, state.STOCKS)
    
    # Determine LLM mode
    provider_type = settings.DEFAULT_MODEL_PROVIDER.lower()
    llm_mode = "mock" if provider_type == "mock" or (not settings.GROQ_API_KEY and not settings.OPENAI_API_KEY) else "active"

    return {
        "is_running": sim.is_running,
        "is_paused": sim.is_paused,
        "llm_mode": llm_mode,
        "day": sim.day,
        "session": sim.session,
        "session_phase": getattr(sim, "session_phase", "pre_open"),
        "total_days": sim.total_days,
        "total_trades": sim.total_trade_count,
        "active_agents": sum(1 for a in state.agents if a.status == "active"),
        "run_id": getattr(sim, "active_run_id", None),
        "universe_id": getattr(sim, "universe_id", None),
        "dataset_version": getattr(sim, "dataset_version", None),
        "scenario_id": getattr(sim, "scenario_id", None),
        "experiment_id": getattr(sim, "experiment_id", None),
        "training_mode": getattr(sim, "training_mode", None),
        "liquidity_model": getattr(sim, "liquidity_model", None),
        "liquidity_regime": getattr(sim, "liquidity_regime", None),
        "latency_ms": getattr(sim, "latency_ms", None),
        "slippage_bps": getattr(sim, "slippage_bps", None),
        "stocks": {s: {"name": state.STOCKS[s].name, "price": prices[s]} for s in state.STOCKS},
        "market_analytics": analytics,
        "regime": analytics["regime"],
        "benchmark": analytics["benchmark"],
        "breadth": analytics["breadth"],
        "realized_vol_pct": analytics["realized_vol_pct"],
        "turnover": analytics["turnover"],
        "market_sentiment": analytics["market_sentiment"],
        "session_risk": analytics["session_risk"],
    }

def _verify_session(x_session_id: Optional[str]):
    if state.active_session_id and x_session_id and x_session_id != state.active_session_id:
        if state.simulation.is_running:
            raise HTTPException(409, f"Simulation session lock active (ID: {state.active_session_id[:8]}...). Only the session that started the run can modify it.")

@router.post("/start")
async def start_simulation(background_tasks: BackgroundTasks, x_session_id: Optional[str] = Header(None)):
    _verify_session(x_session_id)
    sim = state.simulation
    if sim.is_running and not sim.is_paused:
        return {"message": "Simulation already running"}
    if sim.is_paused:
        sim.is_paused = False
        return {"message": "Simulation resumed"}
    
    # If starting fresh, set the lock if not set
    if not state.active_session_id:
        state.active_session_id = x_session_id
        
    background_tasks.add_task(state.simulation.run_simulation)
    return {"message": "Simulation started", "agents": len(state.agents), "days": state.simulation.total_days}


@router.post("/pause")
async def pause_simulation(x_session_id: Optional[str] = Header(None)):
    _verify_session(x_session_id)
    sim = state.simulation
    if not sim.is_running:
        return {"message": "Simulation not running"}
    sim.is_paused = True
    return {"message": "Simulation paused"}


@router.post("/stop")
async def stop_simulation(x_session_id: Optional[str] = Header(None)):
    _verify_session(x_session_id)
    state.simulation._run_stop_reason = "stopped"
    state.simulation.is_running = False
    state.simulation.is_paused = False
    # Clear session lock on stop
    state.active_session_id = None
    return {"message": "Simulation stopped"}


@router.post("/reset")
async def reset_simulation(x_session_id: Optional[str] = Header(None)):
    _verify_session(x_session_id)
    state.simulation.is_running = False
    state.simulation.is_paused = False
    state.active_session_id = None
    state._build_world()
    return {"message": "Simulation reset"}


@router.post("/config")
async def update_config(cfg: SimulationConfig):
    if state.simulation.is_running:
        raise HTTPException(400, "Stop simulation before changing config")
    state._build_world(config=cfg.model_dump())
    return {"message": "Configuration updated", "config": cfg.model_dump()}


@router.post("/extend")
async def extend_simulation(req: ExtendRequest):
    """Add more days to the current simulation without rebuilding world state."""
    sim = state.simulation
    sim.total_days = sim.day + req.additional_days
    return {"message": f"Extended to {sim.total_days} days total", "total_days": sim.total_days}


@router.get("/snapshots")
async def list_snapshots():
    """List available day snapshots."""
    return [{"day": s.day, "trades": s.total_trades, "events": s.events_count}
            for s in state.simulation.snapshots]


@router.get("/snapshots/{day}")
async def get_snapshot(day: int):
    """Get full state snapshot for a specific day."""
    for s in state.simulation.snapshots:
        if s.day == day:
            return s.model_dump()
    raise HTTPException(404, f"No snapshot for day {day}")

@router.post("/inject/news")
async def inject_news(req: NewsInjectionRequest, x_session_id: Optional[str] = Header(None)):
    _verify_session(x_session_id)
    if not state.simulation.is_running:
        raise HTTPException(400, "Simulation must be running to inject news.")

    from backend.app.core.llm_provider import LLMFactory
    import json
    
    provider = LLMFactory.create_provider()
    system_prompt = (
        "You are a financial analyst engine. You read real-world news and convert it "
        "into a structured simulation market shock. "
        "Output MUST be strict JSON matching this schema:\n"
        "{\n"
        '  "title": "Short title of the event",\n'
        '  "description": "Brief description of what happened",\n'
        '  "severity": "LOW" | "MEDIUM" | "HIGH",\n'
        '  "impact_pct": float (e.g. -5.0 for negative 5 percent impact),\n'
        '  "affected_stocks": ["AAPL", "MSFT"] (list of tickers likely affected, up to 3)\n'
        "}\n"
        "Available simulation stocks are: " + ", ".join(state.STOCKS.keys())
    )
    
    try:
        response_text = provider.generate(prompt=req.text, system_message=system_prompt)
        # Parse the JSON
        data = json.loads(response_text)
        from backend.app.models.types import EventInjection
        
        # Make sure affected_stocks are actually in the simulation universe
        affected = data.get("affected_stocks", [])
        valid_affected = [s for s in affected if s in state.STOCKS]
        
        injection = EventInjection(
            title=data.get("title", "News Shock"),
            description=data.get("description", req.text[:100]),
            severity=data.get("severity", "MEDIUM"),
            impact_pct=float(data.get("impact_pct", 0.0)),
            affected_stocks=valid_affected
        )
        
        # Inject the event
        event = state.simulation.inject_event(injection)
        return {"message": "News processed and injected", "event": event.model_dump()}
    except Exception as e:
        logger.error(f"Failed to process news injection: {e}")
        raise HTTPException(500, f"Failed to parse news into event: {str(e)}")

@router.get("/debate")
async def get_debate(x_session_id: Optional[str] = Header(None)):
    _verify_session(x_session_id)
    if not state.simulation.is_running:
        raise HTTPException(400, "Simulation must be running to generate a debate.")

    from backend.app.core.llm_provider import LLMFactory
    import json
    
    # Pass current market state
    prices = {s: (state.market_books[s].last_price or 100.0) for s in state.STOCKS}
    regime = getattr(state.simulation, "liquidity_regime", "core")
    
    provider = LLMFactory.create_provider()
    system_prompt = (
        "You are an AI generating a real-time 'War Room' debate between 3 trading agents. "
        "Based on the current market data, provide exactly 3 short, punchy, argumentative statements (max 2 sentences each): "
        "1. A 'Bull' who wants to buy momentum.\n"
        "2. A 'Bear' who is extremely pessimistic and wants to short.\n"
        "3. A 'Risk Manager' who focuses on volatility, leverage, and capital preservation.\n"
        "Output MUST be strict JSON matching this schema:\n"
        "{\n"
        '  "bull": "Bull statement",\n'
        '  "bear": "Bear statement",\n'
        '  "risk": "Risk manager statement"\n'
        "}\n"
    )
    
    prompt = f"Current Regime: {regime}\nPrices: {json.dumps(prices)}"
    
    try:
        response_text = provider.generate(prompt=prompt, system_message=system_prompt)
        data = json.loads(response_text)
        return {
            "messages": [
                {"agent": "BULL-BOT", "role": "bull", "message": data.get("bull", "Momentum is strong.")},
                {"agent": "BEAR-BOT", "role": "bear", "message": data.get("bear", "This is a trap.")},
                {"agent": "RISK-MANAGER", "role": "risk", "message": data.get("risk", "Deleverage immediately.")}
            ]
        }
    except Exception as e:
        logger.error(f"Failed to generate debate: {e}")
        raise HTTPException(500, f"Failed to generate debate: {str(e)}")
