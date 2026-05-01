# StockAI v2.0: Technical Specification

## 1. Executive Summary
StockAI v2.0 is a professional-grade quantitative research platform designed to study the behavior of LLM-driven autonomous agents in simulated and real-world market conditions. The system provides a high-fidelity simulation engine ("Market Kernel"), a comprehensive research workspace, and a live performance monitor for candidate evaluation.

## 2. System Architecture
The platform follows a modern client-server architecture with a high-performance event-driven core.

### 2.1 Technical Stack
- **Backend API**: Python 3.9+ / FastAPI / Uvicorn
- **Simulation Engine**: Custom asynchronous event loop (SimulationLoop)
- **Data Storage**: SQLite (Research persistent store) / In-memory state (Live simulation)
- **Frontend**: HTML5 / CSS3 (Neo-Brutalist Aesthetic) / Vanilla JavaScript
- **Visualization**: Chart.js / D3.js
- **AI Integration**: OpenAI (GPT-4), Groq (Llama-3), Google Gemini

### 2.2 Core Components
- **Market Kernel**: Handles order matching (Limit/Market), liquidity modeling, and session phase management.
- **Agent Framework**: Multi-agent system supporting LLM personalities, deterministic rules, and Python SDK strategies.
- **Analytics Engine**: Computes professional-grade metrics (Sharpe, Sortino, Beta, HHI, Market Breadth).
- **Research Store**: Manages persistent records for Runs, Scenarios, Experiments, and Evaluations.

## 3. Market Kernel & Simulation Engine
The simulation operates on a multi-session day cycle, modeling institutional market behaviors.

### 3.1 Session Phases
Each trading day is divided into four critical phases:
1. **Pre-Open (08:45)**: Order buildup and price discovery.
2. **Open Auction (09:30)**: Liquidity injection and initial price formation.
3. **Continuous Trading (13:00)**: Active order matching and agent interaction.
4. **Close Auction (15:55)**: Final price fixing and MOC (Market-on-Close) balancing.

### 3.2 Order Matching Logic
The engine implements a price-time priority matching algorithm:
- **Market Orders**: Aggress against available liquidity with slippage modeling.
- **Limit Orders**: Queue in the book for passive execution.
- **Slippage & Latency**: Dynamically calculated based on the session phase and symbol liquidity profile (Deep, Core, Satellite, Thin).

## 4. AI Agent System
AI agents are the heart of the research platform. Each agent possesses a unique persona, risk tolerance, and decision-making framework.

### 4.1 Personality Fragments
Agents are calibrated using "Personality Fragments" such as:
- **Momentum Chaser**: High sensitivity to recent price trends.
- **Value Contrarian**: Focuses on mean reversion and fundamental metrics.
- **Risk-Averse Hedger**: High weight on Sortino ratio and drawdowns.

### 4.2 Decision Lifecycle
1. **Observation**: Agent receives a `MarketState` snapshot (Prices, Trends, Sentiment, News).
2. **Reasoning**: LLM processes the state, identifying opportunities and risks.
3. **Action**: Agent emits an `Order` (BUY/SELL/HOLD).
4. **Learning**: Decision logs and fill events are recorded for downstream attribution analysis.

## 5. Analytics & Performance Attribution
StockAI provides institutional-grade metrics to evaluate both market health and agent skill.

- **Market Metrics**: Breadth Ratio, Sector Dispersion, Realized Volatility, Turnover.
- **Agent Metrics**: Sharpe/Sortino Ratios, Alpha/Beta, Concentration HHI, Sector PnL Attribution.
- **Regime Performance**: Tracks how agents behave in specific macro-regimes (e.g., Inflation Shock vs. Risk-On Expansion).

## 6. API Infrastructure
The FastAPI backend exposes a comprehensive set of REST and WebSocket endpoints.

- `/simulation`: Lifecycle control (Start/Stop/Pause/Reset).
- `/agents`: Persona management and behavioral analytics.
- `/research`: Persistent storage for experimental metadata.
- `/data`: Exportable event streams and forum activity.
- `/ws`: Real-time state synchronization for the frontend.

## 7. Data Modeling (E-R)
The system uses a relational SQLite database to manage research complexity:
- **Run**: A unique simulation instance with a specific config snapshot.
- **Event**: A time-stamped market shock or agent decision.
- **Evaluation**: A benchmarked comparison of agent performance against a scenario.
- **Snapshot**: A full day-end capture of aggregate prices and agent wallets.

## 8. Frontend Interface
Designed for depth and efficiency, the UI provides three primary environments:
- **Simulator Console**: Real-time monitoring of the active matching engine.
- **Research Workspace**: Tools for experiment configuration and PnL deep-dives.
- **Live Performance Monitor**: Real-world data integration for deployment benchmarking.

## 9. Future Work
- Integration of multi-asset classes (Crypto, FX, Commodities).
- Advanced scenario GANs for synthetic event generation.
- Expanded SDK for C++ high-frequency strategy plugins.
