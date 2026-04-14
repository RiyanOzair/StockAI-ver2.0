import logging
from typing import Optional, Dict, Any
import backend.app.state as state
from fastapi import APIRouter, HTTPException, BackgroundTasks, Header
from pydantic import BaseModel, Field
from backend.app.models.types import SimulationConfig
from backend.app.core.analytics import compute_market_analytics

class ExtendRequest(BaseModel):
    additional_days: int = Field(..., gt=0, description="Must be at least 1")

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
