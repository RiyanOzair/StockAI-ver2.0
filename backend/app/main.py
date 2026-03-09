"""StockAI v2.0 — FastAPI application factory."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from datetime import datetime
import logging

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-22s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)

# ── Import state (triggers _build_world on first import) ──
import backend.app.state  # noqa: F401

# ── Import routers ──
from backend.app.api import market, simulation, agents, chat, data, ws

app = FastAPI(title="StockAI v2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount routers ──
app.include_router(market.router)
app.include_router(simulation.router)
app.include_router(agents.router)
app.include_router(chat.router)
app.include_router(data.router)
app.include_router(ws.router)


# ── Root health check ──
@app.get("/")
async def root():
    return {"status": "StockAI v2.0 Online", "time": str(datetime.now())}


# ── Serve Frontend ──
_FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


@app.get("/app", response_class=FileResponse)
async def serve_frontend():
    return FileResponse(_FRONTEND_DIR / "index.html", media_type="text/html")
