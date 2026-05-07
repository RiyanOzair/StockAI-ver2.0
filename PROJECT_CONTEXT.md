# PROJECT_CONTEXT.md

## 1. Project Overview

StockAI v2.0 is a local-first research platform for simulating a synthetic US equities cash market and comparing that simulated market against a lightweight real-market intelligence layer. It combines a FastAPI backend, static HTML/JavaScript frontends, an in-memory multi-agent market engine, and a persistent SQLite-backed research workspace for runs, datasets, scenarios, experiments, bots, and evaluations.

The project solves two related problems:
- It provides a controllable sandbox for studying market microstructure, agent behavior, and strategy performance without needing a live brokerage connection.
- It gives researchers and bot builders a lightweight experiment-management layer so runs, calibration data, scenarios, and evaluations are persistent and exportable.

Target users:
- Quant/research-minded developers exploring synthetic market behavior
- Bot/strategy builders using a Python strategy SDK
- Users who want an interactive AI-driven trading simulator with explainability and analytics

Current stage:
- Functional MVP / advanced prototype
- The app is deployable and tested, but still heavily local-first, monolithic, and operationally simple rather than production-hardened

## 2. Tech Stack

Languages:
- Python 3.11 in Docker (`python:3.11-slim`)
- Local virtualenv currently uses Python 3.13.1
- HTML, CSS, vanilla JavaScript

Backend frameworks and libraries:
- FastAPI
- Uvicorn
- Pydantic v2
- pydantic-settings
- httpx
- sqlite3 from the Python standard library

Frontend libraries:
- Static HTML pages with inline CSS/JS
- Chart.js 4.4.4 loaded from CDN on the simulator page
- Google Fonts (`JetBrains Mono`, `Space Grotesk`)

AI / model integrations:
- Groq
- OpenAI
- Google Gemini via `google-genai`
- Mock provider fallback for simulation agents when API keys are missing

Database and storage:
- SQLite database for research/workspace persistence
- Default DB path: `backend/runtime/stockai_research.db`
- In-memory runtime state for active simulation world
- JSON export bundles via API

Infra / DevOps:
- Dockerfile for single-container deployment
- `docker-compose.yml` for local container orchestration
- Render deployment is referenced in README
- No CI/CD config found in-repo

Testing/tooling:
- Pytest
- FastAPI `TestClient`

Other code in workspace:
- `legacy/` contains the older Streamlit/chatbot codebase and reference assets
- `PromptCoder/` exists as a sibling package in the workspace but is not part of the StockAI v2 runtime path

## 3. Architecture & Structure

High-level architecture:
- Monolithic FastAPI application
- Static frontend pages served directly by FastAPI
- Single in-process simulation kernel with global module state
- SQLite-backed research registry for persistent metadata and event logs

Major directory structure:
- `backend/app/main.py`: FastAPI app factory, router registration, static page routes
- `backend/app/api/`: HTTP and WebSocket route modules
- `backend/app/state.py`: global runtime state, seeded stock universe, world-building, active simulation singleton
- `backend/app/engine/`: order-matching engine and simulation loop
- `backend/app/agents/`: LLM, rule-based, and SDK strategy agent implementations
- `backend/app/core/`: analytics, config, live-market service, research store, prompt creation, job manager, evaluation helpers
- `backend/app/models/`: Pydantic domain models for simulation and research records
- `backend/app/sdk/`: strategy SDK abstractions and built-in strategies
- `backend/run.py`: local Uvicorn launcher
- `frontend/landing.html`: marketing/overview page
- `frontend/index.html`: main simulator console
- `frontend/workspace.html`: research workspace UI
- `frontend/live-market.html`: real-market intelligence UI
- `tests/`: API and execution-kernel tests
- `docs/`: Mermaid diagrams, mostly reflecting older/legacy architecture
- `legacy/`: previous-generation implementation (Streamlit UI, chatbot modules, older engine)

Key runtime modules and responsibilities:
- `state.py`: owns the active world bundle, seeded stock metadata, current agents, active simulation, chat engine init, research store, and job manager
- `simulation_loop.py`: drives phased sessions, event generation, price evolution, order latency/slippage, fills, forum posts, reports, snapshots, and run-event logging
- `order_book.py`: limit/market order matching with price-time priority and self-trade skipping
- `research_store.py`: initializes SQLite schema, seeds default workspace records, persists runs/events/jobs/evaluations/notebooks
- `research.py`: exposes research registry APIs, run launch/export, calibration, bot creation, evaluation workflows, SSE event streaming
- `live_market.py`: fetches free Yahoo Finance chart data with caching/stale fallback and compares it to simulator analytics

Data flow:
1. Browser loads one of the static pages from FastAPI (`/`, `/app`, `/workspace`, `/live-market`)
2. Frontend JS polls REST endpoints and, for simulator live ticks, optionally connects to `/ws`
3. Backend uses global `state.simulation`, `state.agents`, and `state.market_books` for active runtime data
4. Simulation loop mutates in-memory market state and appends run events to SQLite
5. Research/workspace APIs read and write persistent records in SQLite
6. Live-market page fetches external Yahoo Finance data through backend `httpx` calls, then merges it with simulator analytics before returning JSON

## 4. Core Features

- Multi-agent synthetic market simulation: mixes LLM behavioral agents, deterministic rule-based agents, and Python SDK strategy agents in one market.
- Price formation and matching engine: supports limit and market orders, price-time priority, partial fills, self-trade avoidance, and resting-book depth.
- Session-phase market model: each day runs `pre_open`, `open_auction`, `continuous`, and `close_auction` phases.
- Execution realism knobs: latency and slippage are configurable and materially affect when/where orders execute.
- Regime-based market generation: market regimes rotate periodically and influence volatility, liquidity regime, sector drift, and event bias.
- Market events and shocks: random and scheduled macro/earnings/corporate-style events move sectors and individual names.
- Circuit breakers: symbols are halted if intraday move exceeds 10% from session open.
- Loans and bankruptcy: agents can take loans, repay on due days, default, and be liquidated into bankruptcy.
- Forum and explainability: agents post daily sentiment messages and retain per-decision logs with reasoning, memo fields, biases, conviction, and consistency metrics.
- Financial report generation: quarterly-style synthetic financial reports are generated on specific report days.
- Day snapshots / rewind support: end-of-day snapshots capture prices, agent summaries, trades, and event counts.
- Research registry: datasets, scenarios, experiments, populations, bots, runs, evaluations, jobs, and notebook entries persist in SQLite.
- Dataset calibration: users can overwrite embedded priors with bounded reference inputs for returns, spreads, liquidity, and regime bias.
- Strategy bot SDK: custom strategy bots use a typed observation/microstructure/event interface and can be evaluated across seeds.
- Evaluation harness: deterministic multi-seed evaluation produces aggregate PnL/Sharpe/drawdown summaries and can run sync or async.
- Run-scoped event feeds: run events are available via normal REST retrieval and SSE streaming.
- Live market intelligence layer: free Yahoo Finance data is cached server-side, summarized, and compared with the simulator’s current regime.
- Chat endpoint: advisor chat uses Groq first, Gemini second, and returns low-confidence fallback messaging when no provider is configured.
- Project Singularity (Autonomous Engine): Includes 'The Architect' narrative generator, 'Neural Overdrive' visual shocks, 'Market Prophecy' HUD, 'Oracle Pulse' procedural audio, and the 'Inner Monologue' real-time logic stream.

Partially built / in-progress / rough edges:
- `legacy/` code is still present and partially reused for chat initialization, but it is not the primary UI/runtime anymore.
- Docs in `docs/` describe older Streamlit-oriented architecture, not the current FastAPI/static-frontend structure.
- Some UI behavior appears aspirational or partially aligned with backend contracts because the HTML files are very large and hand-written.

## 5. Key Files & Entry Points

Primary entry points:
- `backend/run.py`: local app launcher
- `backend/app/main.py`: FastAPI app object used by Uvicorn
- `frontend/index.html`: main simulator UI served at `/app`
- `frontend/workspace.html`: research workspace served at `/workspace`
- `frontend/live-market.html`: real-market layer served at `/live-market`
- `frontend/landing.html`: landing page served at `/`

Important configuration files:
- `requirements.txt`: Python dependencies
- `backend/app/core/config.py`: current runtime settings model loaded from `.env`
- `config.py`: older broader configuration module; mostly legacy/not used by the v2 FastAPI runtime
- `pytest.ini`: test discovery
- `Dockerfile`: container build/runtime definition
- `docker-compose.yml`: local container run config

Most important files for understanding the system:
- `backend/app/state.py`
- `backend/app/engine/simulation_loop.py`
- `backend/app/engine/order_book.py`
- `backend/app/api/research.py`
- `backend/app/core/research_store.py`
- `backend/app/agents/behavioral_agent.py`
- `backend/app/agents/strategy_agent.py`
- `backend/app/sdk/strategy.py`
- `backend/app/core/live_market.py`
- `tests/test_critical_paths.py`
- `tests/test_research_platform.py`

## 6. Data Models / Schema

Simulation/domain models in `backend/app/models/types.py`:
- `Order`: agent order with side, type, price, quantity, filled quantity, status, timestamp
- `Trade`: execution record linking buyer/seller orders and agents
- `MarketDepth`, `MarketState`: order-book views
- `StockMeta`: seeded per-symbol metadata
- `MarketEvent`: synthetic event/shock record
- `ForumMessage`: daily forum post
- `Loan`: loan state with due day and repayment status
- `FinancialReport`: synthetic quarterly-style report
- `DaySnapshot`: end-of-day rewind snapshot
- `SimulationConfig`: validated run configuration
- `EventInjection`, `ChatRequest`, `CustomAgentRequest`: API payload models

Research/persistence models in `backend/app/models/research.py`:
- `DatasetVersionRecord`
- `ScenarioRecord`
- `ExperimentRecord`
- `BotDefinitionRecord`
- `AgentPopulationRecord`
- `RunRecord`
- `RunEventRecord`
- `EvaluationReportRecord`
- `BackgroundJobRecord`
- `CalibrationProfile`

SQLite schema in `research_store.py`:
- `datasets`
- `scenarios`
- `experiments`
- `agent_populations`
- `bots`
- `runs`
- `run_events`
- `evaluations`
- `jobs`
- `agent_notebooks`

Relationships:
- An `ExperimentRecord` references one `ScenarioRecord`, one `DatasetVersionRecord`, and optionally one `AgentPopulationRecord`
- A `RunRecord` references one experiment/scenario/dataset/population combination
- `RunEventRecord` is one-to-many from `RunRecord`
- `EvaluationReportRecord` references one bot and may reference scenario/dataset/experiment context
- `BackgroundJobRecord` is independent but often linked by payload to evaluations

Validation rules and constraints:
- `SimulationConfig.num_agents`: 2 to 100
- `SimulationConfig.num_days`: 1 to 264
- `speed`: 0.1 to 30.0
- `event_intensity`: 1 to 10
- `latency_ms`: 0 to 5000
- `slippage_bps`: 0.0 to 200.0
- `CustomAgentRequest.initial_cash`: 10,000 to 500,000
- `OrderIntent.quantity`: must be > 0
- `EvaluationCreateRequest.num_days`: 1 to 20

Important seeded defaults:
- Dataset: `dataset-us-equities-core-v1`
- Scenario: `scenario-hybrid-baseline-v1`
- Experiment: `experiment-default-research-v1`
- Population: `population-core-mixed-v1`
- Universe: `us-equities-core-v1`

## 7. API & Interfaces

Static page routes:
- `GET /`: landing page
- `GET /app`: simulator UI
- `GET /workspace`: research workspace
- `GET /live-market`: live-market UI
- `GET /health`: health/status JSON

Market API:
- `GET /market/stocks`: all stock metadata plus current price
- `GET /market/trades`: last 50 trades
- `GET /market/history/{symbol}`: price history for a symbol
- `GET /market/analytics`: market analytics summary
- `GET /market/{symbol}`: single-symbol order book and metadata

Simulation API:
- `GET /simulation/status`
- `POST /simulation/start`
- `POST /simulation/pause`
- `POST /simulation/stop`
- `POST /simulation/reset`
- `POST /simulation/config`
- `POST /simulation/extend`
- `GET /simulation/snapshots`
- `GET /simulation/snapshots/{day}`

Agents API:
- `GET /agents`
- `GET /agents/{agent_id}/decisions`
- `GET /agents/{agent_id}/analytics`
- `POST /agents/custom`
- `GET /agents/explainability`

Data/export API:
- `GET /data/export`
- `GET /data/loans`
- `GET /data/events`
- `GET /data/forum`
- `GET /data/reports`
- `POST /data/event`

Chat API:
- `POST /chat`

Live-market API:
- `GET /api/live-market/snapshot`

Research/workspace API:
- `GET /datasets`
- `GET /workspace/summary`
- `GET /datasets/{dataset_id}`
- `POST /datasets/calibrate`
- `GET /scenarios`
- `POST /scenarios`
- `GET /experiments`
- `POST /experiments`
- `GET /agent-populations`
- `GET /bots`
- `POST /bots`
- `GET /runs`
- `GET /runs/active`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/events`
- `GET /runs/{run_id}/export`
- `GET /runs/{run_id}/stream` (SSE)
- `POST /runs`
- `GET /evaluations`
- `POST /evaluations`
- `GET /jobs`

Realtime interfaces:
- WebSocket: `/ws` for live simulation tick/complete events
- SSE: `/runs/{run_id}/stream` for run-event streaming

Authentication:
- None found
- CORS is fully open (`allow_origins=["*"]`)
- No JWT, sessions, OAuth, or access control

## 8. Business Logic & Rules

Important non-obvious rules:
- The active app is built around global singleton state. Importing `backend.app.state` builds the initial world immediately.
- Launching a new run while the simulation is running is rejected.
- Updating config while running is rejected.
- Resetting the simulation rebuilds the world and creates a new configured run record.
- Each new world build automatically creates and activates a run in the research store.
- Strategy-agent counts are forced to at least one when `num_agents >= 4` and the initial mix would otherwise produce zero.
- If `use_llm` is false, LLM agent allocation is folded into rule-based agents.
- Order latency is modeled as delayed execution steps based on `latency_ms`, not literal wall-clock milliseconds.
- Slippage is applied after trade matching and depends on liquidity profile, session phase, and aggressing side.
- Market orders do not rest on the book.
- Matching skips self-trades by temporarily removing same-agent resting orders and reinserting them afterward.
- Circuit breakers halt trading in a symbol for the session once the move from session open reaches 10%.
- Financial reports only generate on report days `[12, 78, 144, 210]`.
- Event generation includes both deterministic milestone events and random event-intensity-driven events.
- Regime rolls occur on day 1 and every 6 days thereafter.
- Evaluation runs are deterministic by design: `use_llm=False`, low latency, low slippage, fixed seeds, and strategy-only injection on top of a rule-based population.
- Chat history is stored in-memory only and capped to the last 20 message objects.
- Live-market data is intentionally limited to a tracked universe and uses cache/stale/fallback behavior rather than failing hard.

Domain-specific assumptions:
- The simulator models a synthetic US cash equities market, not options, crypto, or 24/7 trading.
- Benchmark levels are synthetic index levels derived from average relative returns against seeded base prices.
- Liquidity profile (`deep`, `core`, `satellite`, `thin`) drives spreads and slippage assumptions.
- Research datasets are not raw historical datasets; they are calibration profiles and metadata describing market priors.

Edge cases explicitly handled:
- Missing market data provider: returns stale cache or fallback payload instead of a 500
- Missing LLM keys: simulation agents can fall back to mock/demo behavior
- Missing chat providers: chat returns low-confidence explanatory response
- Unknown symbols and agents: return 404s
- Running simulation during config changes: blocked
- Invalid dataset/scenario/experiment/population references: blocked with 404
- Market orders: execute against book if possible and do not rest

## 9. Environment & Configuration

Environment variables used by current runtime:
- `HOST`: bind host for `backend/run.py`
- `PORT`: bind port for `backend/run.py`
- `OPENAI_API_KEY`: OpenAI provider key
- `GROQ_API_KEY`: Groq provider key
- `GEMINI_API_KEY`: Gemini key used by `backend/app/core/config.py`
- `GOOGLE_API_KEY`: also referenced in README and legacy code; current chat route actually expects `GEMINI_API_KEY`
- `DEFAULT_MODEL_PROVIDER`: provider selector for simulation LLM agents (`groq`, `openai`, `mock`)
- `DEFAULT_MODEL_NAME`: primary model name
- `STOCKAI_DB_PATH`: override SQLite DB path
- `OLLAMA_HOST`: legacy config only; not part of the primary v2 runtime

How to run locally:
1. Create and activate a virtualenv
2. Install `requirements.txt`
3. Provide `.env` keys if you want real LLM/chat behavior
4. Run `python backend/run.py`
5. Open `/`, `/app`, `/workspace`, or `/live-market`

Recommended local path actually validated in this repo:
- `.\.venv\Scripts\python.exe backend/run.py`

How to run tests:
- `.\.venv\Scripts\python.exe -m pytest tests -q`

Observed test/runtime note:
- Running tests with the system Python failed because `groq` was not installed there
- Running the suite with the project virtualenv succeeded: `43 passed`

## 10. Known Issues, TODOs & Limitations

Known issues / rough edges:
- `backend/app/core/llm_provider.py` imports `groq` at module import time, so tests and app startup fail immediately if that package is missing from the active interpreter, even when mock mode would otherwise be acceptable.
- Environment variable naming is inconsistent: README mentions `GOOGLE_API_KEY`, while current main settings model uses `GEMINI_API_KEY`.
- `docs/architecture.mmd` and `docs/workflow.mmd` describe the legacy Streamlit architecture, not the current FastAPI/static frontend.
- The runtime uses module-level global state, which makes concurrency, multi-user isolation, and horizontal scaling difficult.
- No authentication or authorization exists; the app is effectively open-admin.
- CORS is fully open.
- SQLite persistence is simple and local-first; no migrations framework or explicit schema versioning exists.
- Frontend pages are very large, hand-authored HTML/JS files, which increases coupling and makes targeted UI changes harder.
- The simulator is not backed by real brokerage/exchange data; all market mechanics are synthetic except the live-market page.

TODO/FIXME search summary:
- No explicit `TODO`, `FIXME`, `XXX`, or `HACK` comments were found by repository search in the main project tree.

Functional limitations:
- Single-process memory state means only one active world is really supported at a time.
- Run events persist, but the core market world itself is not restored from DB on restart.
- Strategy SDK includes only two built-in strategies (`mean_reversion`, `benchmark_vwap`).
- Live-market page depends on Yahoo Finance chart endpoints and may degrade to stale/fallback mode during upstream issues.
- Research notebook storage exists in SQLite, but no primary API/UI workflow for notebooks was found in the current frontend.
- Legacy code is still present and partially referenced, which increases cognitive overhead.

## 11. Glossary

- `Run`: one configured or executing simulation instance tied to experiment/scenario/dataset/population metadata.
- `Dataset`: a calibration profile plus metadata describing synthetic market priors.
- `Scenario`: a reusable package of regime/shock/config overrides.
- `Experiment`: a named research program that binds scenario, dataset, and population context.
- `Population`: the composition template for agent types.
- `Bot`: a strategy definition, usually backed by the Python SDK.
- `Evaluation`: a deterministic benchmark sweep for a bot across multiple seeds.
- `Regime`: the current synthetic market state such as `risk_on`, `risk_off`, `inflation_shock`, or `earnings_repricing`.
- `Liquidity profile`: stock-level liquidity tier used to derive spread/slippage assumptions.
- `Session phase`: sub-day phase in the market clock (`pre_open`, `open_auction`, `continuous`, `close_auction`).
- `Live market layer`: the `/live-market` page that compares real-market snapshots with the synthetic simulator state.
- `Workspace`: the `/workspace` page used for calibration, scenario creation, run launch, bot creation, and evaluation tracking.

## 12. Fix Log

The following critical system and heuristic bugs were surgically fixed to stabilize the research engine and UI components:
* **C1**: Implemented `random.seed()` at simulation entry sequence to reinstate deterministic/reproducible runs required for valid evaluation comparison.
* **C2**: Guarded `groq` dependencies using a lazy import checking pattern, preventing backend starvation when providers are unconfigured.
* **C3**: Recalculated Agent Sharpe Ratio based strictly on internal temporal PnL curves instead of raw asset delta metrics.
* **C4**: Rewired stochastic regime transitions to pull their weighted distribution probabilities directly from runtime database inputs.
* **C5**: Enforced scenario calibration overrides onto sector impact walk mechanics, completing the domain bridge for research tuning.
* **H1**: Bound frontend component workflows to a `showToast` JavaScript interceptor handling success/error notification events globally.
* **H2**: Decoupled LLM chat session state context from the Python server namespace into local browser storage instances for concurrency scaling.
* **H3**: Integrated API payload event streams into internal turn buffers, resolving pipeline gaps that shielded trading agents from injected shocks.
* **H5**: Configured early break termination heuristics tracking collective agency capital depletion, suppressing endless flatlined compute epochs.
* **H6**: Bootstrapped synthetic regression fallbacks per asset if upstream live market Yahoo Finance APIs timeout or exclude ticker listings.
* **H7**: Aligned internal agent metric computation for "win rate" against universally standard per-period period financial returns models.
* **H8**: Calibrated tracking scalar values up from baseline typical day boundaries (252) into the true granular tick boundaries (1008). 
* **H9 / H10**: Audited CSS stylesheets deploying WCAG contrast standard color palettes (--muted) and globally enforced element focus bounds.
* **S1 (Singularity)**: Integrated the 'Architect' autonomous narrative engine to inject dynamic market shocks via `/data/event`.
* **S2 (Singularity)**: Resolved agent identity mapping bug in 'Inner Monologue' stream by attaching agent state to the global window scope.
* **S3 (Singularity)**: Synchronized 'Neural Overdrive' glitch effects and 'Oracle Pulse' audio with the market volatility event bus for immersive feedback.
