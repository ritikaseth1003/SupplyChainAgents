"""
Base class for all supply-chain agents.

Handles:
  - WebSocket connection to the message bus
  - Sending / receiving messages
  - Abstract method `process` that subclasses implement
"""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import websockets
from websockets.asyncio.client import connect as ws_connect

logger = logging.getLogger("agent")


class BaseAgent(ABC):
    """Abstract base for every supply-chain agent."""

    NAME: str = "BaseAgent"  # Override in subclass

    def __init__(self, bus_url: str = "ws://localhost:8000/ws") -> None:
        self.bus_url = bus_url
        self._ws: Any = None
        self._running = False

    # ----- communication -----
    async def _connect(self) -> None:
        """Connect to the message bus with retry."""
        for attempt in range(10):
            try:
                self._ws = await ws_connect(self.bus_url)
                logger.info("%s connected to bus", self.NAME)
                return
            except Exception:
                await asyncio.sleep(1)
        raise ConnectionError(f"{self.NAME} could not connect to {self.bus_url}")

    async def send(self, message: str, extra: dict | None = None) -> None:
        """Send a message to the bus."""
        payload: dict[str, Any] = {
            "type": "agent_message",
            "agent": self.NAME,
            "message": message,
        }
        if extra:
            payload.update(extra)
        if self._ws:
            await self._ws.send(json.dumps(payload))

    async def _listen(self) -> None:
        """Listen for incoming messages and dispatch to handler."""
        try:
            async for raw in self._ws:
                data = json.loads(raw)
                await self.on_message(data)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("%s lost connection", self.NAME)

    # ----- lifecycle -----
    async def start(self) -> None:
        """Connect and begin listening + processing."""
        await self._connect()
        self._running = True
        await self.send(f"{self.NAME} online ✅")
        # Run listener and processor concurrently
        await asyncio.gather(self._listen(), self._run_loop())

    async def _run_loop(self) -> None:
        """Periodically call `process` (the agent's main work)."""
        while self._running:
            try:
                await self.process()
            except Exception as exc:
                logger.error("%s process error: %s", self.NAME, exc)
            await asyncio.sleep(2)  # tick every 2 seconds

    # ----- abstract -----
    @abstractmethod
    async def process(self) -> None:
        """Subclass implements its core logic here."""
        ...

    async def on_message(self, data: dict) -> None:
        """Override to react to bus messages (e.g., disruptions)."""
        pass
