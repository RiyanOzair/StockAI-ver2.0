"""Market data endpoints."""
from fastapi import APIRouter, HTTPException
import backend.app.state as state
from backend.app.state import STOCKS

router = APIRouter(prefix="/market", tags=["market"])


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
        "bids": depth["bids"],
        "asks": depth["asks"],
        "last_price": book.last_price,
    }
