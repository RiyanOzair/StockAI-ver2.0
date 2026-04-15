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
from backend.app.api import market, simulation, agents, chat, data, ws, live_market, research

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
app.include_router(live_market.router)
app.include_router(research.router)


# ── Serve Frontend ──
_FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


@app.get("/", response_class=FileResponse)
async def serve_landing():
    return FileResponse(
        _FRONTEND_DIR / "landing.html",
        media_type="text/html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/app", response_class=FileResponse)
async def serve_frontend():
    return FileResponse(
        _FRONTEND_DIR / "index.html",
        media_type="text/html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/workspace", response_class=FileResponse)
async def serve_workspace():
    return FileResponse(
        _FRONTEND_DIR / "workspace.html",
        media_type="text/html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/live-market", response_class=FileResponse)
async def serve_live_market():
    return FileResponse(
        _FRONTEND_DIR / "live-market.html",
        media_type="text/html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/credits", response_class=FileResponse)
async def serve_credits():
    return FileResponse(
        _FRONTEND_DIR / "credits.html",
        media_type="text/html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


# ── Health check ──
@app.get("/health")
async def health():
    return {"status": "StockAI v2.0 Online", "time": str(datetime.now())}
