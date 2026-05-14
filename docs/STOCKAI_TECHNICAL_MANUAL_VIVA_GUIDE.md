# StockAI v2.0: Technical Manual & VIVA Preparation Guide

## 1. Project Overview
**StockAI v2.0** is an immersive, high-fidelity market simulation and research platform. It leverages Large Language Models (LLMs) to power autonomous trading agents that react to market regimes, news shocks, and sector rotations. The platform provides a "Mind-Blowing Mode" for maximum visual and cognitive immersion.

### Core Philosophy
To study the behavioral patterns of AI agents in adversarial and stressed market environments, bridging the gap between theoretical research and live market deployment.

---

## 2. Feature Breakdown

### A. Simulation Console
*   **What it is**: The real-time "cockpit" of the simulator.
*   **How to use it**: Place manual orders (Market/Limit), watch the "Live Tape" (Order Book), and monitor agent PnL.
*   **Technology**: WebSockets for sub-second updates, Chart.js for real-time price action.

### B. Orchestration Workspace
*   **What it is**: The "Lab" where experiments are designed.
*   **Features**: 
    *   **Bot Forge**: Register custom strategy bots.
    *   **Evaluation Bench**: Backtest strategies across multiple random seeds.
    *   **Event Injection**: Force "Black Swan" events like liquidity crises or earnings shocks.
    *   **Research Store**: Persistent storage of every run, decision, and observation.
*   **Technology**: FastAPI endpoints, SQLite backend, SSE (Server-Sent Events) for event streams.

### C. Live Performance Monitor
*   **What it is**: A deployment-focused dashboard tracking US, Indian, and Global markets.
*   **How to use it**: Switch between regions to see real-time telemetry, AI-generated briefs, and sector heatmaps.
*   **Technology**: Integration with Yahoo Finance (US) and Twelve Data (India/Global) APIs.

### D. Immersive Systems (Mind-Blowing Mode)
*   **3D Topology**: A WebGL-powered canvas visualizing market connectivity and "pulse."
*   **Agent War Room**: A live debate panel where BULL and BEAR agents argue about the current market regime.
*   **Project Singularity**: An autonomous "Architect" that injects narrative shifts based on sentiment.
*   **Voice Briefing**: Text-to-Speech narration of critical market shocks.

---

## 3. The Math & Engine Logic

### A. Price Generation (Correlated Walk)
The simulation does **not** use static data. It uses a **Correlated Random Walk** model:
$$P_{t+1} = P_t \times (1 + \text{Drift} + \text{Volatility} \times \text{Noise})$$

*   **Drift**: Calculated as a combination of **Regime Bias** (e.g., +0.8 for Tech in Risk-On) and **Event Impact** (e.g., -0.05 for an earnings miss).
*   **Volatility**: Based on the selected profile (Low/Medium/High) multiplied by the **Regime Multiplier** and **Session Phase Multiplier** (volatility is higher at open/close).
*   **Sector Correlation**: Drifts are blended across sectors using a correlation matrix to simulate spillover effects (e.g., if Tech drops, Media often follows).

### B. Order Book Dynamics
*   **Matching Engine**: Implements a price-time priority queue.
*   **Slippage**: Modeled based on liquidity depth (Deep/Core/Thin). Larger orders in "Thin" liquidity experience higher slippage.
*   **Circuit Breakers**: Automatic trading halts if a stock moves >10% in a single session.

---

## 4. Datasets & Tech Stack

### Datasets
1.  **Yahoo Finance (US)**: Used for live-market tracking and seed prices for the US simulation.
2.  **Twelve Data (India/Global)**: Provides NSE/BSE and international index telemetry.
3.  **Internal Calibration Store**: A curated set of volatility, spread, and volume profiles used to "tune" the simulation engine.

### Technology Stack
*   **Backend**: Python 3.10+, FastAPI (Asynchronous Web Framework), SQLAlchemy/SQLite.
*   **AI/LLM**: OpenAI GPT-4 / Gemini 1.5 Pro (via API) for agent reasoning and war room debates.
*   **Frontend**: HTML5, Vanilla CSS (Neo-Brutalist design), JavaScript (ES6+).
*   **Graphics**: Three.js / WebGL for 3D Topology.
*   **DevOps**: Docker for containerization, Vercel/Render for deployment.

---

## 5. VIVA (Oral Exam) Preparation

### Q: Why use LLM agents instead of simple rule-based bots?
**A**: Rule-based bots are deterministic and fail in "unseen" scenarios. LLM agents can interpret **qualitative data** (news headlines, sentiment) and exhibit complex behaviors like panic selling or FOMO, which creates a more realistic and adversarial training environment.

### Q: What is the "Reality-to-Simulation" bridge?
**A**: It's our engine's ability to take real-world news (e.g., "Fed hikes rates") and automatically translate that into simulation parameters (Impact %, Affected Sectors) so we can see how our strategies would have handled today's news.

### Q: How do you handle market liquidity?
**A**: We model liquidity as a "Regime." In a "Deep" regime, spreads are tight and slippage is low. In a "Thin" or "Satellite" regime (common during crises), spreads widen significantly, making execution more expensive.

### Q: What is "Project Singularity"?
**A**: It is the project's autonomous narrative engine. It acts as an "AI Architect" that monitors market sentiment and automatically generates events (like "AI Renaissance") to drive the simulation forward without human input.

### Q: Is the data truly real-time?
**A**: In the **Live Monitor**, we use live API feeds with ~1s latency for US and India. In the **Simulation Console**, the data is synthetic but "calibrated" to real-market statistics.

---

## 6. How to Explain the Project to an Evaluator
1.  **The Problem**: Traditional backtesting is "dead" (historical data doesn't react to your trades).
2.  **The Solution**: StockAI is a **living market** where agents react to you and each other.
3.  **The Hook**: "We didn't just build a tracker; we built a high-fidelity research lab with AI agents that can argue, panic, and trade exactly like human participants, but at scale."
4.  **The Result**: A platform where you can stress-test strategies against AI-driven "Black Swans" before risking real capital.
