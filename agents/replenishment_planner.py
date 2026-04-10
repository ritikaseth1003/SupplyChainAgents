"""
Replenishment Planner Agent

Responsibilities:
  - Listens for low-stock alerts from the Inventory Manager.
  - Creates Purchase Orders (POs) to best-fit suppliers.
  - Uses GPT-4 to reason about optimal order quantity and supplier.
  - Broadcasts new POs via the message bus.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

import httpx

from agents.base_agent import BaseAgent
from data.synthetic_data import PRODUCT_NAMES
from utils.openai_client import ask_gpt

STATE_URL = "http://localhost:8000/state"


class ReplenishmentPlanner(BaseAgent):
    NAME = "ReplenishmentPlanner"

    async def process(self) -> None:
        """Evaluate whether new POs are needed."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(STATE_URL)
            state = resp.json()

        inventory = state["inventory"]
        safety = state["safety_stock"]
        forecasts = state.get("forecasts", {})
        suppliers = state.get("suppliers", [])
        existing_pos = [
            po for po in state.get("purchase_orders", [])
            if po.get("status") in ("open", "in_transit")
        ]

        await self.send("📝 Evaluating replenishment needs…")

        new_orders: list[dict] = []
        for product in PRODUCT_NAMES:
            level = inventory.get(product, 0)
            threshold = safety.get(product, 150)

            # Forecast total demand over next 7 days
            fc = forecasts.get(product, [])
            demand_7d = sum(fc) if fc else 120 * 7

            # Check if product already has an open PO
            open_for_product = [
                po for po in existing_pos if po.get("product") == product
            ]
            if open_for_product:
                continue  # already ordered

            # Need to order?
            projected = level - demand_7d
            if projected < threshold:
                order_qty = max(demand_7d, threshold * 2) - level + threshold
                order_qty = max(order_qty, 100)  # minimum order

                # Pick best supplier via LLM
                supplier = await self._pick_supplier(product, order_qty, suppliers)

                po = {
                    "id": f"PO-{uuid.uuid4().hex[:8]}",
                    "product": product,
                    "quantity": int(order_qty),
                    "supplier": supplier["supplier"],
                    "lead_time_days": supplier["lead_time_days"],
                    "status": "open",
                    "created_at": datetime.now().isoformat(),
                    "estimated_cost": round(order_qty * 4.5, 2),
                }
                new_orders.append(po)

        if new_orders:
            order_lines = []
            for po in new_orders:
                order_lines.append(
                    f"  🛒 {po['id']}: {po['quantity']} × {po['product']} "
                    f"from {po['supplier']} (lead {po['lead_time_days']}d, "
                    f"${po['estimated_cost']:.0f})"
                )
            summary = "📦 New Purchase Orders:\n" + "\n".join(order_lines)
            await self.send(summary, extra={
                "type": "new_purchase_orders",
                "orders": new_orders,
            })
        else:
            await self.send("✅ No replenishment needed this cycle.")

    async def _pick_supplier(
        self, product: str, qty: int, suppliers: list[dict]
    ) -> dict:
        """Use GPT-4 to pick the optimal supplier."""
        prompt = (
            f"Product: {product}, Quantity needed: {qty}\n"
            f"Available suppliers:\n{json.dumps(suppliers, indent=2)}\n\n"
            "Pick the best supplier considering lead time, capacity, and reliability. "
            "Return ONLY a JSON object with the key 'supplier' set to the supplier name."
        )

        reply = await ask_gpt(
            system_prompt="You are a procurement AI agent in a supply-chain simulation.",
            user_prompt=prompt,
        )

        await self.send(f"🤖 Supplier selection reasoning:\n{reply}")

        # Extract supplier name
        try:
            start = reply.index("{")
            end = reply.rindex("}") + 1
            result = json.loads(reply[start:end])
            picked_name = result.get("supplier", suppliers[0]["supplier"])
            for s in suppliers:
                if s["supplier"] == picked_name:
                    return s
        except (ValueError, json.JSONDecodeError):
            pass

        # Fallback: pick lowest lead-time supplier with enough capacity
        best = min(suppliers, key=lambda s: s["lead_time_days"])
        return best

    async def on_message(self, data: dict) -> None:
        if data.get("type") == "disruption":
            await self.send("⚡ Disruption – rechecking replenishment urgently!")
            await self.process()


if __name__ == "__main__":
    import asyncio, logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(ReplenishmentPlanner().start())
