"""
Logistics Coordinator Agent

Responsibilities:
  - Picks up new Purchase Orders and schedules delivery.
  - Estimates delivery day and shipping cost using LLM reasoning.
  - Simulates delivery completion (marks POs as "in_transit" → "delivered").
  - Reacts to transport disruptions by rescheduling.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta

import httpx

from agents.base_agent import BaseAgent
from utils.openai_client import ask_gpt

STATE_URL = "http://localhost:8000/state"


class LogisticsCoordinator(BaseAgent):
    NAME = "LogisticsCoordinator"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._scheduled: set[str] = set()  # PO IDs we've already scheduled

    async def process(self) -> None:
        """Schedule deliveries for open POs and check in-transit ones."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(STATE_URL)
            state = resp.json()

        pos = state.get("purchase_orders", [])
        disruption = state.get("active_disruption")

        await self.send("🚚 Reviewing logistics & deliveries…")

        for po in pos:
            po_id = po["id"]

            # Schedule new POs
            if po["status"] == "open" and po_id not in self._scheduled:
                delivery = await self._schedule_delivery(po, disruption)
                self._scheduled.add(po_id)
                await self.send(
                    f"📅 Scheduled {po_id}: deliver by {delivery['delivery_date']}, "
                    f"cost ${delivery['shipping_cost']:.0f}",
                    extra={"type": "delivery_scheduled", "po_id": po_id, "delivery": delivery},
                )

            # Simulate in-transit → delivered (simplified: deliver after 1 cycle)
            if po["status"] == "in_transit":
                await self.send(
                    f"✅ {po_id} ({po['product']}) delivered – "
                    f"{po['quantity']} units added to inventory.",
                    extra={"type": "delivery_complete", "po_id": po_id},
                )

        if not pos:
            await self.send("📭 No purchase orders to coordinate.")

        # If disruption active and is transport-related, flag it
        if disruption and disruption.get("type") == "transport_strike":
            await self.send(
                f"⚠️ Transport strike active (severity {disruption['severity']}) – "
                "re-routing shipments via alternate carriers."
            )
            # End disruption after handling
            async with httpx.AsyncClient() as client:
                pass  # recovery handled by simulator

    async def _schedule_delivery(self, po: dict, disruption: dict | None) -> dict:
        """Use LLM to estimate delivery date and cost."""
        lead = po.get("lead_time_days", 3)
        qty = po.get("quantity", 100)

        prompt = (
            f"Purchase Order: {po['id']}\n"
            f"Product: {po['product']}, Quantity: {qty}\n"
            f"Supplier: {po['supplier']}, Lead time: {lead} days\n"
        )
        if disruption:
            prompt += f"Active disruption: {disruption['description']}\n"
        prompt += (
            "\nEstimate the delivery date (YYYY-MM-DD) and total shipping cost in USD. "
            "Return ONLY a JSON object with keys 'delivery_date' and 'shipping_cost'."
        )

        reply = await ask_gpt(
            system_prompt="You are a logistics AI agent scheduling deliveries.",
            user_prompt=prompt,
        )

        await self.send(f"🤖 Delivery reasoning:\n{reply}")

        # Parse LLM response
        try:
            start = reply.index("{")
            end = reply.rindex("}") + 1
            result = json.loads(reply[start:end])
            return {
                "delivery_date": result.get(
                    "delivery_date",
                    (datetime.now() + timedelta(days=lead)).strftime("%Y-%m-%d"),
                ),
                "shipping_cost": float(result.get("shipping_cost", qty * 0.5)),
            }
        except (ValueError, json.JSONDecodeError):
            pass

        # Fallback calculation
        extra_days = 0
        if disruption and disruption.get("type") == "transport_strike":
            extra_days = int(disruption.get("severity", 0.5) * 3)
        delivery_date = (datetime.now() + timedelta(days=lead + extra_days)).strftime("%Y-%m-%d")
        return {
            "delivery_date": delivery_date,
            "shipping_cost": round(qty * 0.5 * (1 + random.uniform(0, 0.3)), 2),
        }

    async def on_message(self, data: dict) -> None:
        if data.get("type") == "disruption":
            await self.send("⚡ Disruption – rescheduling active deliveries!")
            await self.process()


if __name__ == "__main__":
    import asyncio, logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(LogisticsCoordinator().start())
