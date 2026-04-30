# StockAI Workspace — Complete Guide

## Table of Contents

1. [What Is the Workspace?](#1-what-is-the-workspace)
2. [Why Should You Use It?](#2-why-should-you-use-it)
3. [How It Works — Architecture Overview](#3-how-it-works--architecture-overview)
4. [Workspace Tools & Features](#4-workspace-tools--features)
5. [Step-by-Step Usage Guide](#5-step-by-step-usage-guide)
6. [Keyboard Shortcuts](#6-keyboard-shortcuts)
7. [API Endpoints Used by the Workspace](#7-api-endpoints-used-by-the-workspace)
8. [What Outcomes You Get](#8-what-outcomes-you-get)
9. [FAQ](#9-faq)

---

## 1. What Is the Workspace?

The **Workspace** is the **Research & Orchestration Layer** of StockAI v2.0. It is a dedicated frontend page served at `/workspace` that sits on top of the platform's simulation engine and research APIs, giving researchers a single surface to:

- **Configure** high-fidelity market simulation environments
- **Shape** agent populations (LLM agents, rule-based baselines, and strategy bots)
- **Inject** custom market scenarios and shock events
- **Inspect** agent reasoning and explainability logs
- **Compare** experiments across different market regimes
- **Benchmark** strategy bots with multi-seed evaluation sweeps
- **Identify** which strategies are ready to graduate from research into live performance monitoring

Think of it as a **research control room**: while the Simulation Console (`/app`) runs the simulation and the Live Monitor (`/live-market`) tracks real-time performance, the Workspace is where you **design, calibrate, launch, and evaluate** all of your research programs.

### Where Does It Live?

| Component | Location |
|---|---|
| Frontend page | `frontend/workspace.html` |
| Backend API routes | `backend/app/api/research.py` |
| Route registration | `backend/app/main.py` → `/workspace` |
| Persistent store | SQLite via `ResearchStore` in `backend/app/state.py` |

---

## 2. Why Should You Use It?

### Problem Without the Workspace

Without the Workspace, a researcher would need to:

1. Manually call raw API endpoints with `curl` or Postman to create datasets, scenarios, bots, and runs.
2. Write scripts to compare evaluation results.
3. Have no visual overview of what is currently running, what has been tested, and what is ready for deployment.
4. Context-switch between multiple tools to set up a single experiment.

### What the Workspace Solves

| Benefit | Description |
|---|---|
| **Single-pane orchestration** | Everything you need — from dataset calibration to evaluation benchmarking — is on one page. |
| **Reproducible research** | Scenarios, experiments, and evaluations are versioned records stored in SQLite, so every configuration is traceable. |
| **Visual feedback** | Real-time hero stats, run overview cards, registry snapshots, and explainability feeds give you instant awareness of the system state. |
| **Guided workflow** | The stepped Run Launcher (4 stages) walks you through core settings → context → population → rules, reducing misconfiguration. |
| **Agent transparency** | The Explainability Feed shows agent-level decision reasoning, so you can validate *why* agents acted, not just *what* they did. |
| **Deployment readiness** | When evaluations pass, the Workspace signals `RESEARCH + DEPLOYMENT READY`, telling you a strategy is safe to promote to the Live Monitor. |
| **Data hygiene** | The Research Store Purge tool lets you clean up old runs and events so the database stays lean. |

---

## 3. How It Works — Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                    WORKSPACE (workspace.html)             │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌──────────────┐  │
│  │Run       │ │Agent     │ │Bot     │ │Calibration   │  │
│  │Launcher  │ │Config    │ │Forge   │ │Pulse         │  │
│  └────┬─────┘ └────┬─────┘ └───┬────┘ └──────┬───────┘  │
│       │             │           │              │          │
│  ┌────┴─────┐ ┌─────┴────┐ ┌───┴─────┐ ┌─────┴───────┐ │
│  │Scenario  │ │Experiment│ │Eval     │ │Event        │ │
│  │Builder   │ │Packager  │ │Bench    │ │Injection    │ │
│  └────┬─────┘ └────┬─────┘ └───┬─────┘ └─────┬───────┘ │
│       └─────────────┴───────────┴─────────────┘          │
│                         │ HTTP / Fetch                    │
└─────────────────────────┼────────────────────────────────┘
                          │
              ┌───────────▼───────────┐
              │   FastAPI Backend      │
              │  research.py router    │
              │  ┌─────────────────┐   │
              │  │ ResearchStore   │   │
              │  │ (SQLite)        │   │
              │  └─────────────────┘   │
              │  ┌─────────────────┐   │
              │  │ SimulationState │   │
              │  │ (In-memory)     │   │
              │  └─────────────────┘   │
              └────────────────────────┘
```

**Data flow:**

1. The Workspace frontend loads and immediately calls `GET /workspace/summary` to fetch the full state.
2. Every **8 seconds**, it auto-refreshes to keep the display current.
3. User actions (launch run, create bot, calibrate, etc.) send `POST` requests to the research API.
4. The backend persists all records in a SQLite-backed `ResearchStore`.
5. When a run is active and the Event Tape panel is open, an **SSE (Server-Sent Events)** stream pushes real-time events to the browser.

---

## 4. Workspace Tools & Features

The Workspace contains **10 distinct tool panels**, plus supporting features:

### 4.1 Run Launcher
> *Launch the next simulation run using the current dataset, scenario, experiment, and population context.*

A **4-stage stepped wizard** that walks you through:
- **Stage 1 — Core Settings**: Run name, number of simulation days, random seed.
- **Stage 2 — Context**: Select dataset and scenario.
- **Stage 3 — Population**: Choose experiment and agent population.
- **Stage 4 — Rules**: Training mode (Hybrid / Deterministic) and LLM agent toggle.

You can **LAUNCH RUN** (configure only) or **LAUNCH + START** (configure and immediately begin the simulation).

### 4.2 Agent Configuration
> *Control the total agent count and the mix between LLM agents, rule-based baselines, and strategy bots.*

- Set total agent count (2–100).
- Adjust the LLM / Rule-based / Strategy percentage split via sliders.
- A **visual mix preview bar** shows the normalized distribution in real time.

### 4.3 Bot Forge
> *Register a strategy bot definition and optionally attach it to the active simulation.*

- Name, strategy type (Mean Reversion, VWAP Benchmark), and custom JSON config.
- Optionally **attach the bot to the live simulation** to watch it trade in real time.

### 4.4 Calibration Pulse
> *Update the active dataset calibration profile using bounded returns, spreads, and liquidity references.*

- Feed in reference return distributions, spread ranges (BPS), and volume benchmarks.
- The system builds a calibration profile that shapes how the synthetic market behaves.

### 4.5 Scenario Builder
> *Package reusable regime and shock assumptions so experiments can be replayed consistently.*

- Choose from preset regimes: **Stress**, **Momentum**, or **Balanced**.
- Each preset automatically configures regime overrides, shock profiles, and config overrides (volatility spike, spillover bias, slippage, etc.).
- Scenarios are versioned and reusable across multiple experiments.

### 4.6 Experiment Packager
> *Bind datasets, scenarios, and populations into a research program.*

- Links a scenario, dataset, and agent population together.
- Creates a formal experiment record that runs and evaluations can roll up into.

### 4.7 Evaluation Bench
> *Benchmark registered bots across multiple seeds and collect aggregate PNL, Sharpe, and drawdown outputs.*

- Select a bot, set the number of simulation days, and specify seeds (e.g., `11, 19, 23`).
- Run synchronously (wait for result) or asynchronously (queue as a background job).
- Produces aggregate performance metrics.

### 4.8 Event Injection
> *Define a custom shock and send it through the event injection endpoint.*

- Event types: Earnings Shock, Liquidity Crisis, Macro Announcement, Sector Rotation, Regulatory Action.
- Set target day, magnitude (Mild / Moderate / Severe), and affected sector.
- A **20-tick timeline preview** shows exactly when the event will land.

### 4.9 Research Store Purge
> *Clear all events, notebooks, and inactive runs from the SQLite database.*

- Preview before deleting — shows how many events, notebooks, and old runs will be removed.
- The **active run is always excluded** from purge.
- Requires confirmation before execution.

### 4.10 Agent Notebooks
> *Review qualitative research entries and agent observations from the current simulation run.*

- Displays per-agent, per-day, per-session notebook entries.
- Shows entry type, content, and context.
- Requires LLM agents and an active run to generate entries.

### Supporting Features

| Feature | Description |
|---|---|
| **Run Overview** | 10-card grid showing Run ID, Regime, Benchmark Return, Total Trades, Latency/Slippage, Dataset, Scenario, Experiment, Sentiment, Session Risk. |
| **Explainability Feed** | Shows the most recent agent decisions with action, stock, reasoning, conviction %, and a confidence bar. |
| **Local Research Inventory** | Registry snapshot of all datasets, scenarios, experiments, bots, populations, and jobs. |
| **Run Event Tape** | Expandable panel with SSE-powered real-time event stream from the active run. |
| **Market Research Chat** | Floating chat assistant for asking about the current regime, run stats, agent decisions, or bot readiness. Session-scoped with history persistence. |
| **Run Export** | Download the full active run bundle as a JSON file for offline analysis. |
| **Mock Mode Banner** | Warns when running without LLM API keys (hardcoded demo logic). |
| **Collapsible Tool Panels** | Click any tool's sidebar to collapse/expand it; state is saved in `localStorage`. |
| **Custom Cursor** | Neo-brutalist animated cursor with hover/click effects. |

---

## 5. Step-by-Step Usage Guide

### Prerequisites

1. **Start the StockAI server**:
   ```bash
   python backend/run.py
   ```
2. **Open the Workspace** in your browser:
   ```
   http://127.0.0.1:8000/workspace
   ```
   Or navigate from the Landing Page → click **OPEN RESEARCH WORKSPACE**.

---

### Step 1: Calibrate Your Dataset

Before doing anything meaningful, calibrate the default dataset so the synthetic market reflects realistic conditions.

1. Scroll to the **Calibration Pulse** panel.
2. Select the dataset from the dropdown.
3. Enter reference values:
   - **Returns**: e.g., `0.01, 0.015, 0.02, 0.03`
   - **Spreads (BPS)**: e.g., `4, 6, 9, 12`
   - **Volumes (Millions)**: e.g., `12, 18, 24, 31`
4. Click **CALIBRATE DATASET**.
5. The status pill updates to show the last calibration timestamp.

### Step 2: Define a Scenario

Package the market conditions you want to test under.

1. Go to the **Scenario Builder** panel.
2. Enter a name (e.g., `LIQUIDITY STRESS DRILL`).
3. Select a regime preset: **Stress**, **Momentum**, or **Balanced**.
4. Add a description.
5. Click **CREATE SCENARIO**.

### Step 3: Create a Strategy Bot

Register a bot that the platform can benchmark.

1. Go to the **Bot Forge** panel.
2. Name your bot (e.g., `RESEARCH MEAN REVERSION`).
3. Select a strategy: **Mean Reversion** or **VWAP Benchmark**.
4. Customize the config JSON if needed:
   ```json
   {"lookback": 5, "z_entry": 1.2, "z_exit": 0.4}
   ```
5. Choose whether to attach it to the current active simulation.
6. Click **CREATE BOT**.

### Step 4: Package an Experiment

Bind your dataset, scenario, and population into a formal experiment.

1. Go to the **Experiment Packager** panel.
2. Name the experiment (e.g., `LIQUIDITY STRESS PROGRAM`).
3. Select the scenario, dataset, and population from the dropdowns.
4. Click **CREATE EXPERIMENT**.

### Step 5: Launch a Simulation Run

1. Go to the **Run Launcher** panel at the top.
2. Walk through the 4 stages:
   - **Stage 1**: Set the run name, days (e.g., 4), and seed (e.g., 42).
   - **Stage 2**: Select your dataset and scenario.
   - **Stage 3**: Select your experiment and population.
   - **Stage 4**: Set training mode and enable/disable LLM agents.
3. Click **LAUNCH RUN** (configure only) or **LAUNCH + START** (begin immediately).
4. The Hero section updates to show `ACTIVE RUN LIVE`.

### Step 6: Configure Your Agent Mix

1. Go to the **Agent Configuration** panel.
2. Set the total number of agents.
3. Adjust the LLM / Rule-based / Strategy sliders.
4. Watch the mix preview bar update in real time.
5. This configuration is automatically applied when you launch a new run.

### Step 7: Observe the Simulation

While the run is active:

- **Hero Stats** update every 8 seconds with the current run ID, session phase, training mode, and completed evaluations.
- **Run Overview** cards show regime, benchmark return, total trades, and more.
- **Explainability Feed** populates with agent decision reasoning.
- **Agent Notebooks** show qualitative observations.
- Expand the **Run Event Tape** to see the live SSE event stream.

### Step 8: Inject an Event (Optional)

Stress-test your agents mid-run:

1. Go to the **Event Injection** panel.
2. Select event type, sector, target day, and magnitude.
3. Review the timeline preview.
4. Click **INJECT EVENT**.
5. Watch how agents respond in the Explainability Feed.

### Step 9: Run an Evaluation

Benchmark your bot with statistical rigour:

1. Go to the **Evaluation Bench** panel.
2. Select the bot to evaluate.
3. Set the number of days and seeds (e.g., `11, 19, 23`).
4. Choose to wait for the result or queue the job.
5. Click **RUN EVALUATION**.
6. When completed, the evaluation metrics (PNL, Sharpe, drawdown) are stored in the research store.

### Step 10: Export & Promote

1. Click **EXPORT ACTIVE RUN** in the sticky toolbar to download the full run bundle as JSON.
2. When the Workspace status shows **RESEARCH + DEPLOYMENT READY**, your strategies have passed evaluation — they are ready to be monitored on the **Live Market** surface.

---

## 6. Keyboard Shortcuts

The Workspace supports global keyboard shortcuts (when not focused on an input field):

| Shortcut | Action |
|---|---|
| `G` then `S` | Navigate to Simulation Console (`/app`) |
| `G` then `W` | Navigate to Workspace (`/workspace`) |
| `G` then `L` | Navigate to Live Market (`/live-market`) |
| `G` then `H` | Navigate to Landing Page (`/`) |
| `/` | Open the Chat drawer and focus chat input |
| `Esc` | Close the Chat drawer |
| `?` (hold) | Show the keyboard shortcuts overlay |

---

## 7. API Endpoints Used by the Workspace

The Workspace frontend calls these backend routes:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/workspace/summary` | Full workspace state (status, active run, all records, counts, workflow flags, leaderboard, next actions) |
| `GET` | `/market/stocks` | Stock universe for event injection sector dropdowns |
| `GET` | `/agents` | Agent list for explainability |
| `GET` | `/agents/{id}/decisions` | Agent decision logs |
| `POST` | `/runs` | Launch a new simulation run |
| `GET` | `/runs/{id}/events` | Fetch run events (polling) |
| `GET` | `/runs/{id}/stream` | SSE stream of real-time run events |
| `GET` | `/runs/{id}/export` | Export full run bundle |
| `POST` | `/bots` | Register a new strategy bot |
| `POST` | `/datasets/calibrate` | Calibrate a dataset |
| `POST` | `/scenarios` | Create a scenario |
| `POST` | `/experiments` | Create an experiment |
| `POST` | `/evaluations` | Run a bot evaluation |
| `POST` | `/data/event` | Inject a market event |
| `GET` | `/data/purge/preview` | Preview purge impact |
| `POST` | `/data/purge/execute` | Execute research store purge |
| `GET` | `/data/notebooks` | Fetch agent notebook entries |
| `POST` | `/chat` | Send a message to the research assistant |

---

## 8. What Outcomes You Get

By using the Workspace, you produce the following tangible outcomes:

### Research Artifacts

| Artifact | What It Contains |
|---|---|
| **Calibrated Dataset** | A dataset with realistic return, spread, and volume distributions baked in. |
| **Scenario Records** | Versioned, reusable market regime and shock configurations. |
| **Experiment Records** | Formal research programs binding datasets + scenarios + populations. |
| **Bot Definitions** | Named, configurable strategy bot records with JSON config. |
| **Evaluation Reports** | Multi-seed benchmark results with aggregate PNL, Sharpe ratio, and max drawdown. |
| **Run Bundles (JSON)** | Exportable snapshots of the entire run: config, events, dataset, scenario, and evaluations. |
| **Agent Notebooks** | Qualitative agent observations and reasoning logs. |
| **Explainability Logs** | Per-decision reasoning with action, stock, conviction, and timestamp. |

### Decision Outcomes

| Outcome | How the Workspace Helps |
|---|---|
| **"Is this strategy ready?"** | The Evaluation Bench benchmarks bots across multiple seeds. If aggregate Sharpe is positive and drawdown is acceptable, the Workspace signals `RESEARCH + DEPLOYMENT READY`. |
| **"How does this strategy behave under stress?"** | Create a Stress scenario, inject Liquidity Crisis events, and watch agent decisions in the Explainability Feed. |
| **"Which agent type performs best?"** | Vary the Agent Mix between LLM, rule-based, and strategy bots across runs and compare evaluation results. |
| **"Is the data clean enough for a new experiment?"** | The Calibration Pulse lets you shape the dataset to match real-world distributions before running experiments. |

---

## 9. FAQ

**Q: Can the Workspace run without LLM API keys?**
A: Yes. StockAI runs in **mock mode** when no API keys are configured. A red banner appears at the top of the Workspace warning that research results reflect hardcoded demo logic. To get full LLM-backed agent behavior, configure `GROQ_API_KEY`, `OPENAI_API_KEY`, or `GOOGLE_API_KEY` in your `.env` file.

**Q: What happens if I close the browser while a run is active?**
A: The simulation continues running on the backend. When you reopen the Workspace, it will reconnect to the active run and resume displaying the current state.

**Q: Can multiple people use the Workspace at the same time?**
A: The Workspace uses a session lock. The session that launches a run is the only one that can modify it. Other sessions will receive a `409 Conflict` error if they try to modify the active simulation.

**Q: How do I reset everything?**
A: Use the **Research Store Purge** tool to delete all inactive runs, events, and notebooks. The active run is always protected.

**Q: Where is the data stored?**
A: All research records (runs, scenarios, experiments, bots, evaluations, datasets, jobs, events, notebooks) are stored in a local **SQLite database** managed by the `ResearchStore` class.

**Q: How do I access the workspace?**
A: Navigate to `http://127.0.0.1:8000/workspace` when running locally, or `https://stockai-ver2-0.onrender.com/workspace` on the deployed version. You can also reach it from the Landing Page, Simulation Console, or Live Monitor navigation links, or press `G` then `W` from any page.

---

*Last updated: April 2026*
