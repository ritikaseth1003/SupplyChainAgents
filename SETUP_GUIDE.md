# SUPPLYCHAINAGENTS - COMPLETE SETUP GUIDE

## Repository Link
https://github.com/ritikaseth1003/SupplyChainAgents


# STEP 1: GET THE CODE

Option A - Clone with Git (Recommended):
    git clone https://github.com/ritikaseth1003/SupplyChainAgents.git
    cd SupplyChainAgents

Option B - Download ZIP:
    1. Go to https://github.com/ritikaseth1003/SupplyChainAgents
    2. Click green "<> Code" button
    3. Click "Download ZIP"
    4. Extract the ZIP file
    5. Open terminal in that folder

# STEP 2: CREATE VIRTUAL ENVIRONMENT

Windows:
    python -m venv venv
    venv\Scripts\activate

Mac / Linux:
    python3 -m venv venv
    source venv/bin/activate

(You should see (venv) appear at the beginning of your terminal line)

# STEP 3: INSTALL DEPENDENCIES


pip install -r requirements.txt

This installs:
    - fastapi, uvicorn (WebSocket server)
    - streamlit (dashboard)
    - pandas, numpy, plotly (data & charts)
    - openai, python-dotenv (LLM & config)

# STEP 4: SET UP API KEY (OPTIONAL)


Get a free API key from: https://console.groq.com

Then create a file named .env (no extension) with this line:
    GROQ_API_KEY=your_groq_api_key_here

OR run without API key - system works using fallback logic!

# STEP 5: RUN THE SYSTEM


You need TWO terminal windows open side by side:

TERMINAL 1 - Backend Simulator:
    python -m core.simulator
    
    Expected output:
    - "Starting message bus..."
    - "Agent DemandForecaster started"
    - "Agent InventoryManager started"
    - "Agent ReplenishmentPlanner started"
    - "Agent LogisticsCoordinator started"

TERMINAL 2 - Dashboard:
    streamlit run app.py
    
    Expected output:
    - "You can now view your Streamlit app in your browser"
    - "Local URL: http://localhost:8501"

# STEP 6: OPEN DASHBOARD


Open your web browser (Chrome/Firefox/Edge) and go to:
    http://localhost:8501

# STEP 7: RUN THE DEMO


1. Let the simulation run for 30 seconds
2. Watch the Agent Chat Log at the bottom - see agents "thinking"
3. Look at Inventory Levels chart
4. Look at 7-Day Demand Forecast chart
5. Click the red "🚨 Trigger Disruption" button on the left sidebar
6. Watch the agents react immediately in the chat log
7. See Recovery Time metric show how fast they stabilized

# WHAT YOU SHOULD SEE


Working Dashboard:
    ✅ Simulation Day increasing (1, 2, 3...)
    ✅ Stockout Rate changing
    ✅ Inventory Turnover updating
    ✅ 4 Agent Status cards (active/idle)
    ✅ Chat log with agent messages
    ✅ Inventory chart with bars
    ✅ Forecast chart with lines

When you click Disruption:
    ✅ Red banner appears at top
    ✅ Agents show "⚡ Disruption detected" messages
    ✅ Demand Forecaster re-forecasts
    ✅ Logistics Coordinator re-routes shipments
    ✅ Recovery Time shows seconds to stabilize

# TROUBLESHOOTING


Problem: "ModuleNotFoundError"
Solution: pip install -r requirements.txt

Problem: Port 8000 already in use
Solution: Close other programs using port 8000, or restart computer

Problem: Dashboard shows "Day: 0" and never changes
Solution: Terminal 1 (simulator) is not running - check that terminal

Problem: Chat log is empty
Solution: Wait 10-15 seconds - agents need time to start

Problem: "No module named 'core'"
Solution: Make sure you're in the SupplyChainAgents folder (cd SupplyChainAgents)

Problem: Dashboard shows errors
Solution: Press F5 to refresh, or restart both terminals

# QUICK TEST CHECKLIST

Before showing demo, verify:
    ☐ Simulation Day shows number > 0
    ☐ Chat log has messages appearing
    ☐ Inventory chart has bars
    ☐ Trigger Disruption button is red and clickable
    ☐ Both terminals are still running

# TEAMMATES - AFTER SETUP

Once running, explore:
    - Click "Reset Simulation" to start over
    - Click "Trigger Disruption" multiple times for different events
    - Scroll through Agent Chat Log to see Chain-of-Thought reasoning
    - Watch how fast the system recovers (3-7 seconds)

# SUPPORT
GitHub: https://github.com/ritikaseth1003/SupplyChainAgents
README: Contains full documentation


# ✅ SETUP COMPLETE! YOU'RE READY TO RUN THE DEMO!

