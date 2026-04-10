"""
Synthetic data generator for the supply-chain simulation.

Generates:
  - 90 days of historical daily demand
  - Lead times per supplier
  - Supplier capacity
  - Random disruptions (demand spike, supplier delay, transport strike)
"""

import csv
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
NUM_PRODUCTS = 5
PRODUCT_NAMES = [
    "Widget-A", "Widget-B", "Gadget-X", "Gadget-Y", "Component-Z"
]
HISTORY_DAYS = 90
SUPPLIERS = ["SupplierAlpha", "SupplierBeta", "SupplierGamma"]

DISRUPTION_TYPES = [
    "demand_spike",
    "supplier_delay",
    "transport_strike",
]


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------
def generate_historical_demand(
    days: int = HISTORY_DAYS,
    seed: int = 42,
) -> pd.DataFrame:
    """Return a DataFrame with columns: date, product, demand."""
    rng = np.random.default_rng(seed)
    rows = []
    start = datetime.now() - timedelta(days=days)

    for day_offset in range(days):
        date = (start + timedelta(days=day_offset)).strftime("%Y-%m-%d")
        for product in PRODUCT_NAMES:
            base = rng.integers(80, 200)
            # Add weekly seasonality
            seasonal = int(15 * np.sin(2 * np.pi * day_offset / 7))
            noise = rng.integers(-10, 10)
            demand = max(0, base + seasonal + noise)
            rows.append({"date": date, "product": product, "demand": demand})

    return pd.DataFrame(rows)


def save_demand_csv(df: pd.DataFrame, path: str | None = None) -> str:
    """Persist historical demand to CSV; returns the file path."""
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "historical_demand.csv")
    df.to_csv(path, index=False)
    return path


def generate_supplier_info() -> list[dict]:
    """Return lead-time and capacity info for each supplier."""
    rng = random.Random(123)
    info = []
    for supplier in SUPPLIERS:
        info.append({
            "supplier": supplier,
            "lead_time_days": rng.randint(2, 7),
            "capacity_units_per_day": rng.randint(200, 600),
            "reliability_pct": round(rng.uniform(0.80, 0.99), 2),
        })
    return info


def generate_random_disruption() -> dict:
    """Pick a random disruption event with severity."""
    dtype = random.choice(DISRUPTION_TYPES)
    severity = round(random.uniform(0.3, 1.0), 2)

    descriptions = {
        "demand_spike": f"Unexpected demand surge – demand multiplied by {1 + severity:.1f}x",
        "supplier_delay": f"Supplier delay – lead time increased by {int(severity * 5)} days",
        "transport_strike": f"Transport strike – deliveries halted for {int(severity * 3)} days",
    }

    return {
        "type": dtype,
        "severity": severity,
        "description": descriptions[dtype],
        "timestamp": datetime.now().isoformat(),
    }


def get_initial_inventory() -> dict[str, int]:
    """Starting inventory for every product."""
    rng = random.Random(99)
    return {p: rng.randint(300, 800) for p in PRODUCT_NAMES}


def get_safety_stock() -> dict[str, int]:
    """Safety-stock thresholds per product."""
    return {p: 150 for p in PRODUCT_NAMES}


# ---------------------------------------------------------------------------
# Bootstrap: generate and save CSV on import if missing
# ---------------------------------------------------------------------------
_csv_path = os.path.join(os.path.dirname(__file__), "historical_demand.csv")
if not os.path.exists(_csv_path):
    _df = generate_historical_demand()
    save_demand_csv(_df, _csv_path)
