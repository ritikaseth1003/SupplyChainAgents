"""
WebSocket-based message bus built on FastAPI.

Every agent connects as a WebSocket client. The bus broadcasts messages
to all connected clients and also exposes REST endpoints so the
Streamlit dashboard can push disruptions and poll state.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os

from agents.reporting_agent import generate_pdf_report

from core.state_manager import StateManager

logger = logging.getLogger("message_bus")

app = FastAPI(title="SupplyChainAgents – Message Bus")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Shared state  – created once when the server starts
# ---------------------------------------------------------------------------
state = StateManager()

# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)
        logger.info("Client connected – total %d", len(self.active))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)
        logger.info("Client disconnected – total %d", len(self.active))

    async def broadcast(self, message: dict) -> None:
        dead: list[WebSocket] = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()

# ---------------------------------------------------------------------------
# WebSocket endpoint – agents connect here
# ---------------------------------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_json()
            # Persist chat messages into state
            agent = data.get("agent", "Unknown")
            msg = data.get("message", "")
            if msg:
                await state.log_chat(agent, msg)
                
            msg_type = data.get("type")
            if msg_type == "forecast_update":
                forecasts = data.get("forecasts", {})
                for product, vals in forecasts.items():
                    await state.set_forecasts(product, vals)
            elif msg_type == "new_purchase_orders":
                orders = data.get("orders", [])
                for po in orders:
                    await state.add_purchase_order(po)

            # Broadcast to everyone
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception as exc:
        logger.error("WS error: %s", exc)
        manager.disconnect(ws)


# ---------------------------------------------------------------------------
# REST helpers for the Streamlit dashboard
# ---------------------------------------------------------------------------
@app.get("/state")
async def get_state() -> dict[str, Any]:
    """Return a full snapshot of the simulation state."""
    return await state.snapshot()


@app.post("/disruption")
async def trigger_disruption() -> dict:
    """Trigger a random disruption; agents will re-plan automatically."""
    from data.synthetic_data import generate_random_disruption

    disruption = generate_random_disruption()
    await state.start_disruption(disruption)
    await state.log_chat("System", f"🚨 DISRUPTION: {disruption['description']}")
    await manager.broadcast({
        "type": "disruption",
        "agent": "System",
        "message": disruption["description"],
        "disruption": disruption,
    })
    return disruption


@app.post("/reset")
async def reset_simulation() -> dict:
    """Reset the simulation to initial state."""
    global state
    state.__init__()
    await manager.broadcast({"type": "reset", "agent": "System", "message": "Simulation reset."})
    return {"status": "ok"}


@app.post("/generate-report")
async def trigger_report() -> dict:
    current_state = await state.snapshot()
    filename = await generate_pdf_report(current_state)
    return {"status": "ok", "filename": filename}

@app.get("/reports")
async def list_reports() -> dict:
    reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    if not os.path.exists(reports_dir):
        return {"reports": []}
    
    files = [f for f in os.listdir(reports_dir) if f.endswith('.pdf')]
    files.sort(reverse=True)
    return {"reports": files}

@app.get("/reports/{filename}")
async def get_report(filename: str):
    reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    filepath = os.path.join(reports_dir, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, filename=filename)
    return {"error": "Report not found"}

