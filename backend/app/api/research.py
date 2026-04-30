from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import backend.app.state as state
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.app.agents.strategy_agent import StrategyAgent, build_strategy
from backend.app.core.research_harness import build_calibration_profile, evaluate_bot_suite
from backend.app.core.analytics import compute_market_analytics
from backend.app.models.research import (
    BotDefinitionRecord,
    DatasetVersionRecord,
    EvaluationReportRecord,
    ExperimentRecord,
    ScenarioRecord,
)
from backend.app.models.types import SimulationConfig

router = APIRouter(tags=["research"])


def utcnow():
    return datetime.now(timezone.utc)


def _require_record(table: str, record_id: str, label: str) -> Dict[str, Any]:
    record = state.research_store.get_record(table, record_id)
    if not record:
        raise HTTPException(404, f"{label} not found")
    return record


def _get_active_run_record() -> Optional[Dict[str, Any]]:
    run_id = getattr(state.simulation, "active_run_id", None)
    if not run_id:
        return None
    return state.research_store.get_record("runs", run_id)


def _build_status_payload() -> Dict[str, Any]:
    from backend.app.core.config import settings
    provider_type = settings.DEFAULT_MODEL_PROVIDER.lower()
    llm_mode = "mock" if provider_type == "mock" or (not settings.GROQ_API_KEY and not settings.OPENAI_API_KEY) else "active"

    sim = state.simulation
    prices = {symbol: (state.market_books[symbol].last_price or state.STOCKS[symbol].initial_price) for symbol in state.STOCKS}
    analytics = compute_market_analytics(sim, prices, state.STOCKS)
    return {
        "is_running": sim.is_running,
        "is_paused": sim.is_paused,
        "llm_mode": llm_mode,
        "day": sim.day,
        "session": sim.session,
        "session_phase": getattr(sim, "session_phase", "pre_open"),
        "total_days": sim.total_days,
        "total_trades": sim.total_trade_count,
        "active_agents": sum(1 for agent in state.agents if agent.status == "active"),
        "run_id": getattr(sim, "active_run_id", None),
        "universe_id": getattr(sim, "universe_id", None),
        "dataset_version": getattr(sim, "dataset_version", None),
        "scenario_id": getattr(sim, "scenario_id", None),
        "experiment_id": getattr(sim, "experiment_id", None),
        "training_mode": getattr(sim, "training_mode", None),
        "liquidity_model": getattr(sim, "liquidity_model", None),
        "liquidity_regime": getattr(sim, "liquidity_regime", None),
        "latency_ms": getattr(sim, "latency_ms", None),
        "slippage_bps": getattr(sim, "slippage_bps", None),
        "regime": analytics["regime"],
        "benchmark": analytics["benchmark"],
        "breadth": analytics["breadth"],
        "realized_vol_pct": analytics["realized_vol_pct"],
        "turnover": analytics["turnover"],
        "market_sentiment": analytics["market_sentiment"],
        "session_risk": analytics["session_risk"],
    }


def _build_workspace_actions(
    *,
    status: Dict[str, Any],
    active_run: Optional[Dict[str, Any]],
    datasets: list[Dict[str, Any]],
    scenarios: list[Dict[str, Any]],
    experiments: list[Dict[str, Any]],
    bots: list[Dict[str, Any]],
    evaluations: list[Dict[str, Any]],
    jobs: list[Dict[str, Any]],
) -> list[Dict[str, str]]:
    actions: list[Dict[str, str]] = []
    if not datasets:
        actions.append(
            {
                "title": "Seed a dataset",
                "detail": "Workspace needs a dataset calibration before scenario testing becomes meaningful.",
                "intent": "calibrate",
            }
        )
    elif active_run and not status.get("is_running"):
        actions.append(
            {
                "title": "Start the active run",
                "detail": "A configured run is ready. Start it to generate event tape, fills, and regime changes.",
                "intent": "start_run",
            }
        )
    elif not active_run:
        actions.append(
            {
                "title": "Launch a baseline run",
                "detail": "Create a deterministic or hybrid run to anchor the rest of the research workflow.",
                "intent": "launch_run",
            }
        )

    strategy_bots = [bot for bot in bots if bot.get("bot_type") == "strategy"]
    if not strategy_bots:
        actions.append(
            {
                "title": "Forge a strategy bot",
                "detail": "Create a Python SDK strategy bot so the platform can benchmark repeatable agent behavior.",
                "intent": "create_bot",
            }
        )
    elif not any(item.get("status") == "completed" for item in evaluations):
        actions.append(
            {
                "title": "Run an evaluation sweep",
                "detail": "You have strategy bots available. Benchmark them across multiple seeds to establish a baseline.",
                "intent": "evaluate",
            }
        )

    if not scenarios:
        actions.append(
            {
                "title": "Define a scenario",
                "detail": "Package regime overrides and shock assumptions so experiments stay reproducible.",
                "intent": "create_scenario",
            }
        )
    elif not experiments:
        actions.append(
            {
                "title": "Package an experiment",
                "detail": "Bind a scenario, dataset, and population together so runs roll up into a research program.",
                "intent": "create_experiment",
            }
        )

    active_jobs = [job for job in jobs if job.get("status") not in {"completed", "failed"}]
    if active_jobs:
        actions.append(
            {
                "title": "Monitor background work",
                "detail": f"{len(active_jobs)} job(s) are still running. Keep the workspace open for refreshed outputs.",
                "intent": "jobs",
            }
        )

    return actions[:4]


def _build_workspace_summary() -> Dict[str, Any]:
    datasets = state.research_store.list_records("datasets")
    scenarios = state.research_store.list_records("scenarios")
    experiments = state.research_store.list_records("experiments")
    bots = state.research_store.list_records("bots")
    populations = state.research_store.list_records("agent_populations")
    evaluations = state.research_store.list_records("evaluations")
    jobs = state.research_store.list_records("jobs")
    status = _build_status_payload()
    active_run = _get_active_run_record()

    completed_evaluations = [item for item in evaluations if item.get("status") == "completed"]
    leaderboard = sorted(
        completed_evaluations,
        key=lambda item: (
            float(item.get("metrics", {}).get("avg_sharpe_ratio", -999)),
            float(item.get("metrics", {}).get("avg_pnl", -999999)),
        ),
        reverse=True,
    )[:5]

    return {
        "status": status,
        "active_run": active_run,
        "datasets": datasets,
        "scenarios": scenarios,
        "experiments": experiments,
        "bots": bots,
        "populations": populations,
        "evaluations": evaluations,
        "jobs": jobs,
        "counts": {
            "datasets": len(datasets),
            "scenarios": len(scenarios),
            "experiments": len(experiments),
            "bots": len(bots),
            "populations": len(populations),
            "evaluations": len(evaluations),
            "completed_evaluations": len(completed_evaluations),
            "jobs": len(jobs),
            "queued_jobs": sum(1 for job in jobs if job.get("status") not in {"completed", "failed"}),
        },
        "workflow": {
            "dataset_ready": bool(datasets),
            "scenario_ready": bool(scenarios),
            "experiment_ready": bool(experiments),
            "bot_ready": any(bot.get("bot_type") == "strategy" for bot in bots),
            "run_configured": active_run is not None,
            "evaluation_ready": bool(completed_evaluations),
            "export_ready": active_run is not None,
        },
        "leaderboard": leaderboard,
        "latest_completed_evaluation": completed_evaluations[0] if completed_evaluations else None,
        "latest_job": jobs[0] if jobs else None,
        "next_actions": _build_workspace_actions(
            status=status,
            active_run=active_run,
            datasets=datasets,
            scenarios=scenarios,
            experiments=experiments,
            bots=bots,
            evaluations=evaluations,
            jobs=jobs,
        ),
    }


class RunLaunchRequest(BaseModel):
    name: Optional[str] = None
    autostart: bool = False
    config: SimulationConfig = Field(default_factory=SimulationConfig)


class ScenarioCreateRequest(BaseModel):
    name: str
    description: str = ""
    version: str = "1.0"
    regime_overrides: Dict[str, Any] = Field(default_factory=dict)
    shock_profile: Dict[str, Any] = Field(default_factory=dict)
    config_overrides: Dict[str, Any] = Field(default_factory=dict)


class ExperimentCreateRequest(BaseModel):
    name: str
    description: str = ""
    scenario_id: str = state.DEFAULT_SCENARIO_ID
    dataset_id: str = state.DEFAULT_DATASET_ID
    agent_population_id: str = state.DEFAULT_POPULATION_ID
    config_snapshot: Dict[str, Any] = Field(default_factory=dict)


class BotCreateRequest(BaseModel):
    name: str
    bot_type: str = "strategy"
    strategy_id: str = "mean_reversion"
    description: str = ""
    config: Dict[str, Any] = Field(default_factory=dict)
    attach_to_active_simulation: bool = False


class CalibrationRequest(BaseModel):
    dataset_id: str = state.DEFAULT_DATASET_ID
    returns: list[float] = Field(default_factory=list)
    spreads_bps: list[float] = Field(default_factory=list)
    volumes_millions: list[float] = Field(default_factory=list)
    sector_correlation: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    event_frequency: float = 1.0
    regime_transition_bias: Dict[str, float] = Field(default_factory=dict)


class EvaluationCreateRequest(BaseModel):
    name: str
    bot_id: str
    scenario_id: str = state.DEFAULT_SCENARIO_ID
    dataset_id: str = state.DEFAULT_DATASET_ID
    seeds: list[int] = Field(default_factory=lambda: [11, 19, 23])
    num_days: int = Field(default=4, ge=1, le=20)
    run_async: bool = False


@router.get("/datasets")
async def list_datasets():
    return state.research_store.list_records("datasets")


@router.get("/workspace/summary")
async def workspace_summary():
    return _build_workspace_summary()


@router.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: str):
    record = state.research_store.get_record("datasets", dataset_id)
    if not record:
        raise HTTPException(404, "Dataset not found")
    return record


@router.post("/datasets/calibrate")
async def calibrate_dataset(req: CalibrationRequest):
    dataset = state.research_store.get_record("datasets", req.dataset_id)
    if not dataset:
        raise HTTPException(404, "Dataset not found")
    calibration = build_calibration_profile(req.model_dump(exclude={"dataset_id"}))
    updated = DatasetVersionRecord(**{**dataset, "calibration": calibration, "updated_at": utcnow(), "metadata": {**dataset.get("metadata", {}), "reference_window": "user supplied"}})
    return state.research_store.save_dataset(updated)


@router.get("/scenarios")
async def list_scenarios():
    return state.research_store.list_records("scenarios")


@router.post("/scenarios")
async def create_scenario(req: ScenarioCreateRequest):
    scenario = ScenarioRecord(id=f"scenario-{uuid.uuid4().hex[:8]}", name=req.name, version=req.version, description=req.description, regime_overrides=req.regime_overrides, shock_profile=req.shock_profile, config_overrides=req.config_overrides)
    return state.research_store.save_scenario(scenario)


@router.get("/experiments")
async def list_experiments():
    return state.research_store.list_records("experiments")


@router.post("/experiments")
async def create_experiment(req: ExperimentCreateRequest):
    _require_record("scenarios", req.scenario_id, "Scenario")
    _require_record("datasets", req.dataset_id, "Dataset")
    _require_record("agent_populations", req.agent_population_id, "Agent population")
    experiment = ExperimentRecord(id=f"experiment-{uuid.uuid4().hex[:8]}", name=req.name, description=req.description, scenario_id=req.scenario_id, dataset_id=req.dataset_id, agent_population_id=req.agent_population_id, status="ready", config_snapshot=req.config_snapshot)
    return state.research_store.save_experiment(experiment)


@router.get("/agent-populations")
async def list_agent_populations():
    return state.research_store.list_records("agent_populations")


@router.get("/bots")
async def list_bots():
    return state.research_store.list_records("bots")


@router.post("/bots")
async def create_bot(req: BotCreateRequest):
    bot = BotDefinitionRecord(id=f"bot-{uuid.uuid4().hex[:8]}", name=req.name, bot_type=req.bot_type, strategy_id=req.strategy_id, class_name=req.strategy_id, description=req.description, config=req.config)
    saved = state.research_store.save_bot(bot)
    if req.attach_to_active_simulation:
        initial_prices = {sym: (state.market_books[sym].last_price or state.STOCKS[sym].initial_price) for sym in state.STOCKS}
        agent = StrategyAgent(
            agent_id=str(uuid.uuid4()),
            name=req.name,
            strategy=build_strategy(req.strategy_id, req.config),
            strategy_id=req.strategy_id,
            initial_cash=120_000.0,
            initial_holdings={},
            initial_prices=initial_prices,
            dataset_version=state.simulation.dataset_version,
            scenario_id=state.simulation.scenario_id,
            universe_id=state.simulation.universe_id,
            seed=None,
            training_mode=state.simulation.training_mode,
        )
        agent.set_run_id(state.simulation.active_run_id or "ad-hoc")
        state.agents.append(agent)
        state.simulation.agents.append(agent)
        saved["attached_agent_id"] = str(agent.id)
    return saved


@router.get("/runs")
async def list_runs():
    return state.research_store.list_records("runs")


@router.get("/runs/active")
async def get_active_run():
    record = _get_active_run_record()
    if not record:
        raise HTTPException(404, "No active run")
    return record


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    record = state.research_store.get_record("runs", run_id)
    if not record:
        raise HTTPException(404, "Run not found")
    return record


@router.get("/runs/{run_id}/events")
async def get_run_events(run_id: str, after_sequence: int = 0):
    _require_record("runs", run_id, "Run")
    return state.research_store.list_run_events(run_id, after_sequence=after_sequence)


@router.get("/runs/{run_id}/export")
async def export_run_bundle(run_id: str):
    from backend.app.core.config import settings
    provider_type = settings.DEFAULT_MODEL_PROVIDER.lower()
    llm_mode = "mock" if provider_type == "mock" or (not settings.GROQ_API_KEY and not settings.OPENAI_API_KEY) else "active"

    run = state.research_store.get_record("runs", run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return {
        "run": run,
        "llm_mode": llm_mode,
        "events": state.research_store.list_run_events(run_id),
        "dataset": state.research_store.get_record("datasets", run.get("dataset_id", state.DEFAULT_DATASET_ID)),
        "scenario": state.research_store.get_record("scenarios", run.get("scenario_id", state.DEFAULT_SCENARIO_ID)),
        "evaluation_reports": [
            item
            for item in state.research_store.list_records("evaluations")
            if item.get("scenario_id") == run.get("scenario_id")
            and item.get("experiment_id", run.get("experiment_id")) == run.get("experiment_id")
        ],
    }


@router.get("/runs/{run_id}/replay")
async def get_run_replay(run_id: str):
    """Fetch structured event timeline for simulation playback."""
    _require_record("runs", run_id, "Run")
    events = state.research_store.list_run_events(run_id)
    # Return all events for the run; frontend will filter/handle empty state
    return events


@router.get("/runs/{run_id}/stream")
async def stream_run_events(run_id: str, after_sequence: int = 0):
    _require_record("runs", run_id, "Run")

    async def event_source():
        last_sequence = after_sequence
        idle_cycles = 0
        while idle_cycles < 20:
            events = state.research_store.list_run_events(run_id, after_sequence=last_sequence)
            if events:
                idle_cycles = 0
                for event in events:
                    last_sequence = max(last_sequence, int(event["sequence"]))
                    yield f"data: {json.dumps(event)}\n\n"
            else:
                idle_cycles += 1
                yield "event: ping\ndata: {}\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(event_source(), media_type="text/event-stream")

@router.get("/data/purge/preview")
async def preview_purge():
    active_run_id = getattr(state.simulation, "active_run_id", None)
    return state.research_store.get_purge_preview(active_run_id)

@router.post("/data/purge/execute")
async def execute_purge():
    active_run_id = getattr(state.simulation, "active_run_id", None)
    return state.research_store.execute_purge(active_run_id)

@router.get("/data/notebooks")
async def list_agent_notebooks(run_id: str):
    return state.research_store.list_notebook_entries(run_id, limit=200)


class NotebookEntryRequest(BaseModel):
    entry_type: str = "research"
    content: str
    agent_id: str = "researcher"
    day: int = 0
    session: int = 0
    payload: Dict[str, Any] = Field(default_factory=dict)


@router.post("/data/notebooks")
async def create_notebook_entry(req: NotebookEntryRequest):
    run_id = getattr(state.simulation, "active_run_id", None)
    if not run_id:
        raise HTTPException(400, "No active run — launch a run first to attach notebook entries")
    return state.research_store.save_notebook_entry(
        run_id=run_id,
        agent_id=req.agent_id,
        day=req.day or getattr(state.simulation, "day", 0),
        session=req.session or getattr(state.simulation, "session", 0),
        entry_type=req.entry_type,
        content=req.content,
        payload_json=req.payload,
    )

from fastapi import APIRouter, HTTPException, BackgroundTasks, Header

@router.post("/runs")
async def launch_run(req: RunLaunchRequest, background_tasks: BackgroundTasks, x_session_id: Optional[str] = Header(None)):
    if state.simulation.is_running:
        if state.active_session_id and x_session_id != state.active_session_id:
            raise HTTPException(409, f"Simulation session lock active (ID: {state.active_session_id[:8]}...). Only the session that started the run can modify it.")
        raise HTTPException(400, "Stop the active simulation before launching a new run")
    
    # Establish session lock on launch
    state.active_session_id = x_session_id
    _require_record("datasets", req.config.dataset_version, "Dataset")
    _require_record("scenarios", req.config.scenario_id, "Scenario")
    _require_record("experiments", req.config.experiment_id, "Experiment")
    _require_record("agent_populations", req.config.agent_population_id, "Agent population")
    payload = req.config.model_dump()
    if req.name:
        payload["config_snapshot_label"] = req.name
    state._build_world(config=payload)
    run = state.research_store.get_record("runs", state.simulation.active_run_id)
    if req.autostart:
        background_tasks.add_task(state.simulation.run_simulation)
    return {"run": run, "autostarted": req.autostart}


@router.get("/evaluations")
async def list_evaluations():
    return state.research_store.list_records("evaluations")


@router.post("/evaluations")
async def create_evaluation(req: EvaluationCreateRequest):
    bot = state.research_store.get_record("bots", req.bot_id)
    if not bot:
        raise HTTPException(404, "Bot not found")
    _require_record("scenarios", req.scenario_id, "Scenario")
    _require_record("datasets", req.dataset_id, "Dataset")
    evaluation_id = f"evaluation-{uuid.uuid4().hex[:8]}"
    evaluation = EvaluationReportRecord(id=evaluation_id, name=req.name, bot_id=req.bot_id, scenario_id=req.scenario_id, dataset_id=req.dataset_id, status="queued")
    state.research_store.save_evaluation(evaluation)

    async def _run(payload: Dict[str, Any]):
        try:
            results = await evaluate_bot_suite(bot_name=bot["name"], strategy_id=bot.get("strategy_id") or "mean_reversion", strategy_config=bot.get("config") or {}, scenario_id=req.scenario_id, dataset_version=req.dataset_id, seeds=req.seeds, num_days=req.num_days)
            report = EvaluationReportRecord(**{**evaluation.model_dump(mode="json"), "status": "completed", "metrics": results["aggregate"], "notes": [f"Seeds: {', '.join(str(seed) for seed in req.seeds)}"], "updated_at": utcnow()})
            state.research_store.save_evaluation(report)
            return {"evaluation_id": evaluation_id, "aggregate": results["aggregate"], "runs": results["runs"]}
        except Exception as exc:
            failed_report = EvaluationReportRecord(
                **{
                    **evaluation.model_dump(mode="json"),
                    "status": "failed",
                    "notes": [f"Evaluation failed: {exc}"],
                    "updated_at": utcnow(),
                }
            )
            state.research_store.save_evaluation(failed_report)
            raise

    job = await state.job_manager.submit(job_type="evaluation", payload={"evaluation_id": evaluation_id, "bot_id": req.bot_id}, handler=_run, run_async=req.run_async)
    if req.run_async:
        return {"evaluation_id": evaluation_id, "job": job}
    return state.research_store.get_record("evaluations", evaluation_id)


@router.get("/jobs")
async def list_jobs():
    return state.research_store.list_records("jobs")
