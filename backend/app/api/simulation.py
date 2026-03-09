"""Simulation control endpoints."""
import logging
import backend.app.state as state
from fastapi import APIRouter, HTTPException, BackgroundTasks
from backend.app.models.types import SimulationConfig

router = APIRouter(prefix="/simulation", tags=["simulation"])
logger = logging.getLogger("api.simulation")


@router.get("/status")
async def get_status():
    sim = state.simulation
    return {
        "is_running": sim.is_running,
        "is_paused": sim.is_paused,
        "day": sim.day,
        "session": sim.session,
        "total_days": sim.total_days,
        "total_trades": sim.total_trade_count,
        "active_agents": sum(1 for a in state.agents if a.status == "active"),
        "stocks": {
            s: {"name": state.STOCKS[s].name, "price": state.market_books[s].last_price or state.STOCKS[s].initial_price}
            for s in state.STOCKS
        },
    }


@router.post("/start")
async def start_simulation(background_tasks: BackgroundTasks):
    sim = state.simulation
    if sim.is_running and not sim.is_paused:
        return {"message": "Simulation already running"}
    if sim.is_paused:
        sim.is_paused = False
        return {"message": "Simulation resumed"}
    # Auto-reset if previous run completed
    if sim.day >= sim.total_days and not sim.is_running:
        state._build_world()
        logger.info("Auto-reset after completed simulation")
    background_tasks.add_task(state.simulation.run_simulation)
    return {"message": "Simulation started", "agents": len(state.agents), "days": state.simulation.total_days}


@router.post("/pause")
async def pause_simulation():
    sim = state.simulation
    if not sim.is_running:
        return {"message": "Simulation not running"}
    sim.is_paused = True
    return {"message": "Simulation paused"}


@router.post("/stop")
async def stop_simulation():
    state.simulation.is_running = False
    state.simulation.is_paused = False
    return {"message": "Simulation stopped"}


@router.post("/reset")
async def reset_simulation():
    state.simulation.is_running = False
    state.simulation.is_paused = False
    state._build_world()
    return {"message": "Simulation reset"}


@router.post("/config")
async def update_config(cfg: SimulationConfig):
    if state.simulation.is_running:
        raise HTTPException(400, "Stop simulation before changing config")
    state._build_world(config=cfg.model_dump())
    return {"message": "Configuration updated", "config": cfg.model_dump()}


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
