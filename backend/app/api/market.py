"""Market data endpoints."""
from fastapi import APIRouter, HTTPException
import backend.app.state as state
from backend.app.state import STOCKS
from backend.app.core.analytics import compute_market_analytics

from backend.app.core.sentiment import mood_engine

router = APIRouter(prefix="/market", tags=["market"])
 
 
@router.get("/universes")
async def get_universes():
    """Return all possible stock universes for selection."""
    return {
        "us_equities": {sym: meta.name for sym, meta in state.US_STOCKS.items()},
        "india_nse_bse": {sym: meta.name for sym, meta in state.INDIA_STOCKS.items()},
        "global": {sym: meta.name for sym, meta in {**state.US_STOCKS, **state.INDIA_STOCKS}.items()},
    }


@router.get("/sentiment")
async def get_global_sentiment():
    """Return the global market sentiment score and regime."""
    return await mood_engine.get_global_sentiment()


@router.get("/briefing")
async def get_market_briefing():
    """Generate a high-impact AI market briefing."""
    return await mood_engine.get_market_briefing()


@router.get("/stocks")
async def get_all_stocks():
    """Return metadata + live price for every stock."""
    return {
        sym: {
            "name": meta.name,
            "sector": meta.sector,
            "emoji": meta.emoji,
            "initial_price": meta.initial_price,
            "volatility": meta.volatility_multiplier,
            "benchmark": meta.benchmark,
            "liquidity_profile": meta.liquidity_profile,
            "market_cap_bucket": meta.market_cap_bucket,
            "beta": meta.beta,
            "average_daily_volume_millions": meta.average_daily_volume_millions,
            "description": meta.description,
            "price": state.market_books[sym].last_price or meta.initial_price,
        }
        for sym, meta in STOCKS.items()
    }


@router.get("/trades")
async def get_recent_trades():
    recent = state.simulation.all_trades[-50:]
    return [
        {
            "trade_id": t.trade_id,
            "stock": t.stock_symbol,
            "price": t.price,
            "quantity": t.quantity,
            "buyer": t.buyer_agent_id,
            "seller": t.seller_agent_id,
            "time": t.timestamp.isoformat() if t.timestamp else "",
        }
        for t in reversed(recent)
    ]


@router.get("/history/{symbol}")
async def get_price_history(symbol: str):
    symbol = symbol.upper()
    history = state.simulation.price_history.get(symbol, [])
    return {"symbol": symbol, "history": history}


@router.get("/analytics")
async def get_market_analytics():
    prices = {s: (state.market_books[s].last_price or STOCKS[s].initial_price) for s in STOCKS}
    return compute_market_analytics(state.simulation, prices, STOCKS)


@router.get("/{symbol}")
async def get_market_state(symbol: str):
    symbol = symbol.upper()
    if symbol not in state.market_books:
        raise HTTPException(404, "Symbol not found")
    book = state.market_books[symbol]
    depth = book.get_depth()
    meta = STOCKS.get(symbol)
    return {
        "symbol": symbol,
        "name": meta.name if meta else symbol,
        "sector": meta.sector if meta else "",
        "emoji": meta.emoji if meta else "📈",
        "benchmark": meta.benchmark if meta else "SPY",
        "liquidity_profile": meta.liquidity_profile if meta else "core",
        "bids": depth["bids"],
        "asks": depth["asks"],
        "last_price": book.last_price,
    }
