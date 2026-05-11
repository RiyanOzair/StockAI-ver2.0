"""Live-market endpoints for real-world data snapshots."""
from fastapi import APIRouter, Query

from backend.app.core.live_market import live_market_service
from backend.app.core.india_market import india_market_service
from backend.app.core.global_market import global_market_service

router = APIRouter(prefix="/api/live-market", tags=["live-market"])


@router.get("/snapshot")
async def get_live_market_snapshot(refresh: bool = Query(False, description="Force a provider refresh")):
    return await live_market_service.get_snapshot(force_refresh=refresh)


@router.get("/india/summary")
async def get_india_market_summary():
    """Return Indian market indices and top stocks via Twelve Data."""
    return await india_market_service.get_summary()


@router.get("/global/summary")
async def get_global_market_summary():
    """Return key global indices via Yahoo Finance."""
    return await global_market_service.get_summary()


@router.get("/india/comparison")
async def get_india_market_comparison():
    """Return India market data formatted for comparison with US equities."""
    return await india_market_service.get_comparison()
