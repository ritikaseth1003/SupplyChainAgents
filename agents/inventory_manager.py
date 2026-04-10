"""
Inventory Manager Agent

Responsibilities:
  - Monitors stock levels vs safety stock for every product.
  - Simulates daily consumption by subtracting forecasted demand.
  - Flags low-stock products and requests replenishment.
  - Updates metrics (stockout count, total demand served).
"""

from __future__ import annotations

import httpx

from agents.base_agent import BaseAgent
from data.synthetic_data import PRODUCT_NAMES

STATE_URL = "http://localhost:8000/state"


class InventoryManager(BaseAgent):
    NAME = "InventoryManager"

    async def process(self) -> None:
        """Check inventory against safety stock; simulate consumption."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(STATE_URL)
            state = resp.json()

        inventory = state["inventory"]
        safety = state["safety_stock"]
        forecasts = state.get("forecasts", {})

        await self.send("📦 Checking inventory levels…")

        alerts: list[str] = []
        for product in PRODUCT_NAMES:
            level = inventory.get(product, 0)
            threshold = safety.get(product, 150)

            # Simulate today's consumption (first element of forecast or default)
            today_demand = 0
            fc = forecasts.get(product, [])
            if fc:
                today_demand = fc[0]
            else:
                today_demand = 120  # fallback average

            new_level = max(0, level - today_demand)

            if new_level <= 0:
                alerts.append(f"🔴 STOCKOUT {product}! Level=0")
            elif new_level < threshold:
                deficit = threshold - new_level
                alerts.append(
                    f"🟡 LOW STOCK {product}: {new_level} units "
                    f"(safety={threshold}, need +{deficit})"
                )
            else:
                alerts.append(f"🟢 {product}: {new_level} units OK")

        report = "📋 Inventory status:\n" + "\n".join(f"  {a}" for a in alerts)
        await self.send(report, extra={
            "type": "inventory_update",
            "alerts": alerts,
        })

    async def on_message(self, data: dict) -> None:
        if data.get("type") == "disruption":
            await self.send("⚡ Disruption – urgent inventory check!")
            await self.process()


if __name__ == "__main__":
    import asyncio, logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(InventoryManager().start())
