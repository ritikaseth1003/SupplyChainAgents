"""
Centralised state manager for the supply-chain simulation.

Holds ALL shared mutable state so every agent and the dashboard can
read / write a single source of truth via simple method calls.
Thread-safe via asyncio locks (single event-loop model).
"""

from __future__ import annotations

import asyncio
import time
from copy import deepcopy
from datetime import datetime
from typing import Any

from data.synthetic_data import (
    PRODUCT_NAMES,
    get_initial_inventory,
    get_safety_stock,
    generate_supplier_info,
)


class StateManager:
    """In-memory state for the entire simulation."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()

        # Inventory
        self.inventory: dict[str, int] = get_initial_inventory()
        self.safety_stock: dict[str, int] = get_safety_stock()

        # Demand forecasts  {product: [next 7 days]}
        self.forecasts: dict[str, list[int]] = {p: [] for p in PRODUCT_NAMES}

        # Purchase orders  list of dicts
        self.purchase_orders: list[dict[str, Any]] = []

        # Supplier info
        self.suppliers = generate_supplier_info()

        # Agent states
        self.agent_states: dict[str, str] = {
            "DemandForecaster": "Online 🟢",
            "InventoryManager": "Online 🟢",
            "ReplenishmentPlanner": "Online 🟢",
            "LogisticsCoordinator": "Online 🟢",
        }

        # Chat log  [(timestamp, agent, message)]
        self.chat_log: list[tuple[str, str, str]] = []

        # Metrics
        self.metrics = {
            "stockout_count": 0,
            "total_demand": 0,
            "total_cost": 0.0,
            "disruption_recovery_time": 0.0,
            "days_simulated": 0,
        }

        # Current disruption (None when calm)
        self.active_disruption: dict | None = None
        self._disruption_start: float | None = None

        # Simulation day counter
        self.sim_day: int = 0

    # ------------------------------------------------------------------ helpers
    async def set_agent_state(self, agent: str, state: str) -> None:
        async with self._lock:
            self.agent_states[agent] = state

    async def log_chat(self, agent: str, message: str) -> None:
        async with self._lock:
            ts = datetime.now().strftime("%H:%M:%S")
            self.chat_log.append((ts, agent, message))
            # Keep the last 200 messages
            if len(self.chat_log) > 200:
                self.chat_log = self.chat_log[-200:]

    async def update_inventory(self, product: str, delta: int) -> int:
        """Add *delta* to inventory (negative = consumption). Returns new level."""
        async with self._lock:
            self.inventory[product] = max(0, self.inventory[product] + delta)
            return self.inventory[product]

    async def set_forecasts(self, product: str, values: list[int]) -> None:
        async with self._lock:
            self.forecasts[product] = values

    async def add_purchase_order(self, po: dict) -> None:
        async with self._lock:
            self.purchase_orders.append(po)

    async def close_purchase_order(self, po_id: str) -> None:
        async with self._lock:
            for po in self.purchase_orders:
                if po["id"] == po_id:
                    po["status"] = "delivered"
                    break

    async def start_disruption(self, disruption: dict) -> None:
        async with self._lock:
            self.active_disruption = disruption
            self._disruption_start = time.time()

    async def end_disruption(self) -> float:
        """End the current disruption, return recovery duration in seconds."""
        async with self._lock:
            elapsed = 0.0
            if self._disruption_start is not None:
                elapsed = round(time.time() - self._disruption_start, 2)
            self.active_disruption = None
            self._disruption_start = None
            self.metrics["disruption_recovery_time"] = elapsed
            return elapsed

    async def snapshot(self) -> dict[str, Any]:
        """Return a JSON-serialisable copy of the full state."""
        async with self._lock:
            return {
                "sim_day": self.sim_day,
                "inventory": deepcopy(self.inventory),
                "safety_stock": deepcopy(self.safety_stock),
                "forecasts": deepcopy(self.forecasts),
                "purchase_orders": deepcopy(self.purchase_orders),
                "agent_states": deepcopy(self.agent_states),
                "chat_log": list(self.chat_log),
                "metrics": deepcopy(self.metrics),
                "active_disruption": deepcopy(self.active_disruption),
                "suppliers": deepcopy(self.suppliers),
            }
