# 🏭 SupplyChainAgents

**Multi-Agent AI System for Retail Operations Automation**

A fully functional multi-agent system where four specialized AI agents collaborate in real time to manage a retail supply chain. Each agent uses GPT-4 with chain-of-thought reasoning and communicates via WebSockets.

---

## 🤖 Agent Architecture

| Agent | Role |
|-------|------|
| **🔮 Demand Forecaster** | Predicts next 7 days of demand using SMA + LLM reasoning |
| **📦 Inventory Manager** | Monitors stock vs safety stock, flags shortages |
| **📝 Replenishment Planner** | Creates Purchase Orders when stock is low |
| **🚚 Logistics Coordinator** | Schedules delivery day & cost for POs |

## 🏗️ Project Structure

```
Supply-Sim/
├── app.py                          # Streamlit dashboard
├── agents/
│   ├── base_agent.py               # Abstract base agent (WebSocket lifecycle)
│   ├── demand_forecaster.py        # SMA + GPT-4 forecasting
│   ├── inventory_manager.py        # Stock monitoring
│   ├── replenishment_planner.py    # PO creation + supplier selection
│   └── logistics_coordinator.py    # Delivery scheduling
├── core/
│   ├── message_bus.py              # FastAPI WebSocket server + REST API
│   ├── state_manager.py            # Centralised simulation state
│   └── simulator.py                # Orchestrator: runs bus + agents + sim loop
├── data/
│   ├── synthetic_data.py           # Generates demand, suppliers, disruptions
│   └── historical_demand.csv       # Auto-generated 90-day history
├── utils/
│   └── openai_client.py            # Async GPT-4 wrapper with CoT
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

### 1. Install dependencies

```bash
cd Supply-Sim
pip install -r requirements.txt
```

### 2. Set your OpenAI API key

```bash
# Windows PowerShell
$env:OPENAI_API_KEY = "sk-..."

# Linux / macOS
export OPENAI_API_KEY="sk-..."
```

> **Note:** The system works without an API key too — agents will fall back to heuristic reasoning instead of GPT-4.

### 3. Start the simulator (Terminal 1)

```bash
python -m core.simulator
```

This starts:
- FastAPI WebSocket message bus on `ws://localhost:8000/ws`
- All four AI agents
- Simulation loop (advances 1 day every 3 seconds)

### 4. Start the dashboard (Terminal 2)

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

## 🎮 Features

### Live Dashboard
- **Agent status cards** — see each agent's current state
- **Inventory chart** — bar chart with safety-stock threshold line
- **7-day forecast chart** — line chart per product
- **Purchase orders table** — all POs with status tracking
- **Chat log** — real-time stream of agent reasoning
- **Key metrics** — stockout rate, turnover, total cost, recovery time

### Trigger Disruption
Click the **🚨 Trigger Disruption** button to randomly inject one of:
- **Demand spike** — demand multiplied by up to 2×
- **Supplier delay** — lead times increase
- **Transport strike** — deliveries halted

Watch agents detect, reason about, and recover from the disruption in under 10 seconds.

## 📊 Metrics

| Metric | Description |
|--------|-------------|
| Stockout Rate | % of demand events that hit zero inventory |
| Inventory Turnover | How many times inventory is cycled |
| Total Cost | Sum of PO costs + shipping |
| Recovery Time | Seconds from disruption trigger to resolution |

## ⚙️ Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | Your OpenAI API key (optional) |
| Sim tick interval | 3s | How often the simulation advances one day |
| Agent tick interval | 2s | How often each agent runs its process loop |
| History days | 90 | Days of synthetic demand history |

## 🛠️ Tech Stack

- **Python 3.10+**
- **FastAPI + WebSockets** — agent message bus
- **Streamlit** — interactive dashboard
- **OpenAI GPT-4** — chain-of-thought reasoning
- **Plotly** — interactive charts
- **Pandas + NumPy** — data handling
- **asyncio** — concurrency

---

*Built with ❤️ by SupplyChainAgents*
