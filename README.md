# StockAI v2.0

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

StockAI v2.0 is a local-first research platform for high-fidelity market simulation. It combines a FastAPI backend with static HTML frontends for the landing page, research workspace, simulator console, and live performance monitor. Researchers and bot builders can configure persistent runs, inspect agent behavior, evaluate strategy bots, compare experiments, and export research data.

Live deployment: https://stockai-ver2-0.onrender.com/

## What Is Deployed

- A landing page at `/`
- A research workspace at `/workspace`
- A simulator dashboard at `/app`
- A live performance monitor at `/live-market`
- A FastAPI backend serving market, simulation, agents, chat, data, and websocket routes
- Research APIs for runs, scenarios, experiments, datasets, bots, evaluations, jobs, and run-scoped event streams
- Live simulation state including stocks, agents, trades, events, forum activity, loans, financial reports, and persistent run events
- Optional LLM-backed features through provider keys configured in `.env`

## Features

- Multi-agent market simulation with LLM, deterministic, and Python strategy-SDK agents
- Multi-Market Support: Native support for Indian (NSE/BSE), US, and Crypto markets
- Cognitive HUD & Immersive UI: 
  - Mood Engine: Sentiment-driven UI atmosphere and data visualization
  - 3D Topology: Real-time market density and sector topology visualization
  - AI Voice Briefings: Context-aware narrated market summaries
  - Onboarding Tour: Guided walkthrough for new researchers
- Research Toolkit & Persistence:
  - Agent Notebooks: Research entries, thesis notes, and observations attached to active runs
  - Persistent Records: Runs, scenarios, datasets, experiments, bots, and evaluations backed by SQLite
- Session-phase aware market kernel with latency, slippage, market orders, partial fills, and queue-priority matching
- Live stock prices, recent trades, market depth, price history, and run-scoped event tape
- Research workspace for dataset/scenario/bot discovery and experiment comparison
- Simulation lifecycle controls for start, pause, stop, reset, config updates, extension, and run launch
- Agent analytics, explainability summaries, decision logs, custom agent creation, and strategy-bot evaluation
- Exportable structured data for downstream analysis and research bundles
- Static frontend served directly from the FastAPI app for simpler deployment

## Tech Stack

- Backend: FastAPI, Pydantic, Uvicorn
- Frontend: HTML, CSS, Vanilla JavaScript, Chart.js
- Testing: Pytest, httpx TestClient
- Optional AI providers: Groq, OpenAI, Google Gemini
- Deployment: Render

## Project Structure

```text
StockAI/
|-- backend/
|   |-- app/
|   |   |-- api/              # FastAPI route modules
|   |   |-- agents/           # Agent logic and behaviors
|   |   |-- models/           # Pydantic and domain models
|   |   `-- main.py           # FastAPI app and frontend routes
|   `-- run.py                # Local Uvicorn entry point
|-- frontend/
|   |-- landing.html          # Landing page served at /
|   |-- workspace.html        # Research workspace served at /workspace
|   |-- live-market.html      # Live performance monitor
|   `-- index.html            # Simulator UI served at /app
|-- docs/                     # Architecture and workflow diagrams
|-- tests/                    # Critical path API tests
|-- requirements.txt
`-- README.md
```

## Run Locally

```bash
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python backend/run.py
```

Open:

- `http://127.0.0.1:8000/` for the landing page
- `http://127.0.0.1:8000/workspace` for the research workspace
- `http://127.0.0.1:8000/app` for the simulation console
- `http://127.0.0.1:8000/live-market` for the live performance monitor

## Environment Variables

StockAI can run without LLM keys, but richer chat and model-backed behavior depend on provider configuration.

```env
GROQ_API_KEY=your_groq_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
DEFAULT_MODEL_PROVIDER=groq
HOST=127.0.0.1
PORT=8000
```

See `.env.example` for the project template.

## API Overview

Current important routes:

- `GET /` serves `frontend/landing.html`
- `GET /workspace` serves `frontend/workspace.html`
- `GET /app` serves `frontend/index.html`
- `GET /live-market` serves `frontend/live-market.html`
- `GET /health` returns status JSON
- `GET /market/*` returns stock metadata, history, trades, and symbol detail
- `GET` and `POST /simulation/*` control simulation state and snapshots
- `GET` and `POST /agents/*` expose agent lists, analytics, decisions, explainability, and custom agent creation
- `GET` and `POST /data/*` expose exports, events, forum items, reports, loans, and event injection
- `GET` and `POST /data/notebooks` manage research entries and agent observations
- `GET` and `POST /runs`, `/experiments`, `/scenarios`, `/bots`, `/evaluations`, `/datasets` expose the research platform resources
- `GET /runs/{run_id}/events` and `GET /runs/{run_id}/stream` expose run-scoped event feeds

## Testing

Run the critical path suite with:

```bash
.\.venv\Scripts\python.exe -m pytest tests -q
```

The suite covers the current FastAPI behavior, including the landing, workspace, simulator, and live performance monitor HTML responses, the JSON health endpoint, the main market/simulation/agents/data routes, the research resource routes, calibration, evaluation, and execution-kernel behaviors.

## Deployment

The current deployed app is hosted on Render at:

https://stockai-ver2-0.onrender.com/

### Environment Variables on Render

Since the `.env` file is gitignored for security, you must manually set your API keys in the **Render Dashboard** to enable AI and Indian market features:

1. Go to your **Render Dashboard**
2. Select your **StockAI** service
3. Go to the **Environment** tab
4. Add the following keys:
   - `INDIA_MARKET_API_KEY` (from twelvedata.com)
   - `GROQ_API_KEY` (from console.groq.com)
   - `GEMINI_API_KEY` (from aistudio.google.com)
   - `DEFAULT_MODEL_PROVIDER` (set to `groq`)
   - `DEFAULT_MODEL_NAME` (set to `llama-3.3-70b-versatile`)

5. Save Changes and Render will automatically redeploy.

For Docker-based deployment:

```bash
docker build -t stockai .
docker run -p 8000:8000 --env-file .env stockai
```

For Docker Compose:

```bash
docker compose up --build -d
```

Useful Docker Compose commands:

```bash
docker compose ps
docker compose logs -f
docker compose down
```

## Documentation

- [Step-by-Step User Guide](docs/USER_GUIDE_STEP_BY_STEP.md) — How to use the research workplace.
- [Project Q&A](docs/PROJECT_Q_AND_A.md) — Answers to common questions.
- [Architecture Docs](docs/architecture.mmd) — Mermaid diagrams.

## License

This project is licensed under the MIT License.
