"""WebSocket endpoint for live simulation updates."""
import json
import logging
import asyncio
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import backend.app.state as state

router = APIRouter(tags=["websocket"])
logger = logging.getLogger("api.ws")

# Connected clients
_clients: Set[WebSocket] = set()


async def broadcast(data: dict):
    """Send JSON to all connected WebSocket clients."""
    if not _clients:
        return
    payload = json.dumps(data, default=str)
    disconnected = set()
    for ws in _clients:
        try:
            await ws.send_text(payload)
        except Exception as e:
            logger.warning(f"WS send failed, removing client: {e}")
            disconnected.add(ws)
    _clients -= disconnected


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _clients.add(ws)
    logger.info(f"WS client connected ({len(_clients)} total)")

    # Wire broadcast into the CURRENT simulation loop
    state.simulation.ws_broadcast = broadcast

    try:
        while True:
            # Keep alive — listen for client pings or close
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(ws)
        logger.info(f"WS client disconnected ({len(_clients)} total)")
