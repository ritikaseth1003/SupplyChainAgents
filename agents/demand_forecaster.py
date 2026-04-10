"""
Demand Forecaster Agent

Predicts the next 7 days of demand for every product using:
  1. Simple Moving Average (SMA) over the last 14 days of history
  2. GPT-4 chain-of-thought reasoning to adjust the forecast

Publishes forecasts to the message bus and updates shared state.
"""

from __future__ import annotations

import json
import os
import httpx
import numpy as np
import pandas as pd

from agents.base_agent import BaseAgent
from utils.openai_client import ask_gpt
from data.synthetic_data import PRODUCT_NAMES

HISTORY_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "historical_demand.csv")
STATE_URL = "http://localhost:8000/state"


class DemandForecaster(BaseAgent):
    NAME = "DemandForecaster"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._demand_df = pd.read_csv(HISTORY_CSV)
        self._last_disruption: dict | None = None

    # ----- core logic -----
    async def process(self) -> None:
        """Compute SMA forecast then enhance with LLM reasoning."""
        # Fetch current state to check for disruptions
        async with httpx.AsyncClient() as client:
            resp = await client.get(STATE_URL)
            state = resp.json()

        await self.send("📊 Running demand forecast cycle…")

        forecasts: dict[str, list[int]] = {}
        for product in PRODUCT_NAMES:
            sma_forecast = self._sma_forecast(product)

            # If there's a disruption, ask GPT to adjust
            disruption = state.get("active_disruption")
            if disruption:
                adjusted = await self._llm_adjust(product, sma_forecast, disruption)
                forecasts[product] = adjusted
            else:
                forecasts[product] = sma_forecast

        # Push forecasts to state
        async with httpx.AsyncClient() as client:
            current = await client.get(STATE_URL)
            # We update via the bus message so the server can pick it up
            pass

        summary_lines = []
        for p, vals in forecasts.items():
            summary_lines.append(f"  {p}: {vals}")
        summary = "🔮 7-day forecast:\n" + "\n".join(summary_lines)
        await self.send(summary, extra={"type": "forecast_update", "forecasts": forecasts})

    def _sma_forecast(self, product: str, window: int = 14) -> list[int]:
        """Simple Moving Average over the last *window* days."""
        pdf = self._demand_df[self._demand_df["product"] == product]
        recent = pdf["demand"].values[-window:]
        avg = int(np.mean(recent)) if len(recent) > 0 else 100
        # Add a bit of variance for realism
        rng = np.random.default_rng()
        return [max(0, avg + int(rng.integers(-8, 8))) for _ in range(7)]

    async def _llm_adjust(
        self, product: str, baseline: list[int], disruption: dict
    ) -> list[int]:
        """Ask GPT-4 to adjust the SMA forecast given a disruption."""
        prompt = (
            f"Product: {product}\n"
            f"Baseline 7-day demand forecast (units/day): {baseline}\n"
            f"Active disruption: {disruption['description']}\n"
            f"Disruption severity (0-1): {disruption['severity']}\n\n"
            "Adjust the 7-day forecast considering this disruption. "
            "Return ONLY a JSON list of 7 integers."
        )

        reply = await ask_gpt(
            system_prompt="You are a demand-forecasting AI agent in a supply-chain simulation.",
            user_prompt=prompt,
        )

        await self.send(f"🤖 LLM reasoning for {product}:\n{reply}")

        # Try to extract the JSON list from the reply
        try:
            # Find first '[' and last ']'
            start = reply.index("[")
            end = reply.rindex("]") + 1
            return json.loads(reply[start:end])
        except (ValueError, json.JSONDecodeError):
            # Fallback: scale baseline by disruption severity
            factor = 1 + disruption.get("severity", 0.5)
            if disruption["type"] == "demand_spike":
                return [int(v * factor) for v in baseline]
            return baseline

    # ----- disruption listener -----
    async def on_message(self, data: dict) -> None:
        if data.get("type") == "disruption":
            self._last_disruption = data.get("disruption")
            await self.send("⚡ Disruption detected – re-forecasting immediately!")
            await self.process()


# ---------------------------------------------------------------------------
# Entry-point when run standalone
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import asyncio
    logging_cfg = __import__("logging")
    logging_cfg.basicConfig(level=logging_cfg.INFO)
    asyncio.run(DemandForecaster().start())
