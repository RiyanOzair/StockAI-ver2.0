# StockAI v2.0: User Guide

## What is StockAI?
StockAI is a high-fidelity market research platform where you can build, test, and monitor AI-driven trading agents. Whether you're a quantitative researcher or an AI enthusiast, StockAI provides the tools to simulate complex market regimes and see how different LLM personalities respond to volatility, news shocks, and liquidity shifts.

---

## Getting Started

### 1. Installation
1.  **Clone the Repository**: Download the project to your local machine.
2.  **Set Up Environment**: Create a virtual environment and install dependencies:
    ```bash
    python -m venv .venv
    .\.venv\Scripts\activate
    pip install -r requirements.txt
    ```
3.  **Configure API Keys**: Create a `.env` file and add your keys (Groq, OpenAI, or Google):
    ```env
    GROQ_API_KEY=your_key_here
    ```
4.  **Run the App**:
    ```bash
    python backend/run.py
    ```

### 2. Accessing the Platform
Open your browser to `http://127.0.0.1:8000/`.

---

## Exploring the Interface

### 🏠 Landing Page
The gateway to the ecosystem. Review high-level platform stats and quickly jump into the Simulator, Workspace, or Live Monitor.

### 🧪 Research Workspace (`/workspace`)
Your technical laboratory.
- **Run Discovery**: Browse through past simulation runs and experiments.
- **Performance Deep-Dive**: Select an agent to see their PnL, Sharpe ratio, and sector attribution.
- **Comparison**: Select multiple agents to compare their performance in a unified dashboard.

### 🎮 Simulator Console (`/app`)
The "Live" matching engine interface.
- **Control**: Start, Pause, or Reset the simulation.
- **Watch**: See the order book update in real-time as agents trade.
- **Chat**: Interact with the StockAI assistant to get insights into the current market state.

### 📡 Live Performance Monitor (`/live-market`)
Benchmarks for the real world.
- **Real Data**: See how simulated candidates would perform against the actual US equity market (via Yahoo Finance).
- **Regime Alignment**: Compare current market conditions with simulated research regimes.

---

## Key Features

- **AI Personas**: Choose from diverse personalities like "Aggressive Alpha" or "Defensive Value."
- **Market Events**: Inject custom events like "Fed Interest Rate Hike" to see how agents pivot.
- **Smart Analytics**: Review institutional-grade metrics for every trade.
- **No-Code Config**: Set up complex simulations using simple dropdowns and sliders.

---

## Tips for Success
- **Start Small**: Run a 10-agent, 5-day simulation first to understand the flow.
- **Check the Logs**: If an agent stops trading, check the "Decision Logs" in the Research Workspace to see their reasoning.
- **Use the Assistant**: Click the pink "StockAI" button or use the `/` shortcut to ask the AI questions about the market.
