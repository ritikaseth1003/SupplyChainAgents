"""
Simulator – runs the full multi-agent loop.

Starts the FastAPI message bus in a background thread, then launches
all four agents as concurrent async tasks. The Streamlit dashboard
(app.py) runs separately and polls state via HTTP.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time

import uvicorn

from core.message_bus import app as fastapi_app, state, manager
from data.synthetic_data import (
    PRODUCT_NAMES,
    generate_historical_demand,
    generate_random_disruption,
)

logger = logging.getLogger("simulator")

# ---------------------------------------------------------------------------
# Agent imports (deferred to avoid circular imports at module level)
# ---------------------------------------------------------------------------

def _make_agents():
    from agents.demand_forecaster import DemandForecaster
    from agents.inventory_manager import InventoryManager
    from agents.replenishment_planner import ReplenishmentPlanner
    from agents.logistics_coordinator import LogisticsCoordinator
    return [
        DemandForecaster(),
        InventoryManager(),
        ReplenishmentPlanner(),
        LogisticsCoordinator(),
    ]


# ---------------------------------------------------------------------------
# State simulation tick – runs every cycle on the server side
# ---------------------------------------------------------------------------
async def simulation_tick() -> None:
    """
    Advance the simulation by one day:
      - Consume inventory based on forecasts
      - Process deliveries
      - Update metrics
      - Check if disruption should end
    """
    state.sim_day += 1

    # --- consume inventory (simulate actual daily demand) ---
    import numpy as np
    rng = np.random.default_rng()

    total_demand_today = 0
    for product in PRODUCT_NAMES:
        fc = state.forecasts.get(product, [])
        demand = fc[0] if fc else int(rng.integers(80, 160))
        total_demand_today += demand

        old_level = state.inventory.get(product, 0)
        new_level = max(0, old_level - demand)
        state.inventory[product] = new_level

        if new_level == 0:
            state.metrics["stockout_count"] += 1

        # Shift forecast forward
        if fc:
            state.forecasts[product] = fc[1:] + [fc[-1]]

    state.metrics["total_demand"] += total_demand_today
    state.metrics["days_simulated"] = state.sim_day

    # --- process deliveries (open → in_transit → delivered) ---
    for po in state.purchase_orders:
        if po["status"] == "open":
            po["status"] = "in_transit"
        elif po["status"] == "in_transit":
            # Deliver goods
            product = po["product"]
            state.inventory[product] = state.inventory.get(product, 0) + po["quantity"]
            po["status"] = "delivered"
            state.metrics["total_cost"] += po.get("estimated_cost", 0)

    # --- end disruption after 2 ticks (≈4 seconds) ---
    if state.active_disruption and state._disruption_start:
        elapsed = time.time() - state._disruption_start
        if elapsed > 6:
            recovery = await state.end_disruption()
            await state.log_chat("System", f"✅ Disruption resolved in {recovery:.1f}s")
            await manager.broadcast({
                "type": "disruption_resolved",
                "agent": "System",
                "message": f"Disruption resolved in {recovery:.1f}s",
            })

    # Broadcast state update
    snapshot = await state.snapshot()
    await manager.broadcast({"type": "state_update", "state": snapshot})


# ---------------------------------------------------------------------------
# Background simulation runner
# ---------------------------------------------------------------------------
async def run_simulation_loop() -> None:
    """Tick the simulation every 3 seconds."""
    await asyncio.sleep(5)  # let agents connect first
    while True:
        try:
            await simulation_tick()
        except Exception as exc:
            logger.error("Sim tick error: %s", exc)
        await asyncio.sleep(6)


# ---------------------------------------------------------------------------
# Entry-point: start the bus server + agents + simulation
# ---------------------------------------------------------------------------
def start_server() -> None:
    """Run the FastAPI message bus on a background thread."""
    config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    logger.info("Message bus started on ws://localhost:8000/ws")
    time.sleep(2)  # wait for server to be ready


async def run_agents() -> None:
    """Start all agents + simulation loop concurrently."""
    agents = _make_agents()
    tasks = [asyncio.create_task(a.start()) for a in agents]
    tasks.append(asyncio.create_task(run_simulation_loop()))
    await asyncio.gather(*tasks)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
    )
    logger.info("Starting SupplyChainAgents simulator…")
    start_server()
    asyncio.run(run_agents())


if __name__ == "__main__":
    main()
