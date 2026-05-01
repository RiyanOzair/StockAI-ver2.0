from __future__ import annotations

import uuid
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional

import backend.app.state as state
from backend.app.agents.strategy_agent import StrategyAgent, build_strategy
from backend.app.models.research import CalibrationProfile
from backend.app.models.types import SimulationConfig


def build_calibration_profile(reference: Optional[Dict[str, Any]] = None) -> CalibrationProfile:
    reference = reference or {}
    returns = [abs(float(v)) for v in reference.get("returns", []) if v is not None]
    spreads = [abs(float(v)) for v in reference.get("spreads_bps", []) if v is not None]
    volumes = [abs(float(v)) for v in reference.get("volumes_millions", []) if v is not None]
    low = max(0.004, min(0.03, mean(returns[: max(1, len(returns) // 3)]) if returns else 0.008))
    medium = max(low + 0.002, min(0.04, mean(returns) if returns else 0.015))
    high = max(medium + 0.003, min(0.06, max(returns) if returns else 0.027))
    shock = max(high + 0.003, min(0.09, high * 1.65))
    deep = max(2.0, min(15.0, mean(spreads[: max(1, len(spreads) // 3)]) if spreads else 4.0))
    core = max(deep + 0.5, min(25.0, mean(spreads) if spreads else 8.0))
    satellite = max(core + 1.5, min(40.0, max(spreads) if spreads else 15.0))
    thin = max(satellite + 2.0, min(80.0, satellite * 1.8))
    avg_vol = mean(volumes) if volumes else 18.0
    return CalibrationProfile(
        version=f"calibration-{uuid.uuid4().hex[:8]}",
        reference_mode="user_reference" if reference else "embedded_priors",
        volatility_bands={"low": round(low, 4), "medium": round(medium, 4), "high": round(high, 4), "shock": round(shock, 4)},
        spread_bps={"deep": round(deep, 2), "core": round(core, 2), "satellite": round(satellite, 2), "thin": round(thin, 2)},
        average_daily_volume_millions={"deep": round(avg_vol * 2.4, 1), "core": round(avg_vol, 1), "satellite": round(max(2.0, avg_vol * 0.45), 1), "thin": round(max(1.0, avg_vol * 0.2), 1)},
        sector_correlation=reference.get("sector_correlation", {}),
        event_frequency=float(reference.get("event_frequency", 1.0)),
        regime_transition_bias=reference.get("regime_transition_bias", {}),
        notes=["Bounded calibration profile generated for StockAI's hybrid synthetic market kernel."],
    )


async def evaluate_bot_suite(
    *,
    bot_name: str,
    strategy_id: str,
    strategy_config: Optional[Dict[str, Any]] = None,
    scenario_id: str = state.DEFAULT_SCENARIO_ID,
    dataset_version: str = state.DEFAULT_DATASET_ID,
    seeds: Optional[Iterable[int]] = None,
    num_days: int = 4,
) -> Dict[str, Any]:
    seeds = list(seeds or [11, 19, 23])
    run_results: List[Dict[str, Any]] = []
    for seed in seeds:
        cfg = SimulationConfig(
            num_agents=6,
            num_days=num_days,
            use_llm=False,
            speed=0.1,
            seed=seed,
            scenario_id=scenario_id,
            dataset_version=dataset_version,
            training_mode="deterministic",
            agent_mix={"llm": 0.0, "rule": 1.0, "strategy": 0.0},
            latency_ms=80,
            slippage_bps=4.0,
        ).model_dump()
        initial_prices = {sym: meta.initial_price for sym, meta in state.STOCKS.items()}
        evaluator = StrategyAgent(
            agent_id=f"eval-{seed}",
            name=f"{bot_name} Seed {seed}",
            strategy=build_strategy(strategy_id, strategy_config or {}),
            strategy_id=strategy_id,
            initial_cash=120_000.0,
            initial_holdings={},
            initial_prices=initial_prices,
            dataset_version=dataset_version,
            scenario_id=scenario_id,
            universe_id=cfg["universe_id"],
            seed=seed,
            training_mode="deterministic",
        )
        evaluator.set_run_id(f"eval-run-{seed}")
        # FIX C1: Seed RNG before world build so evaluation runs are deterministic per seed
        import random
        random.seed(seed)
        bundle = state.build_world_bundle(config=cfg, extra_agents=[evaluator])
        sim = bundle["simulation"]
        sim.activate_run({"id": f"eval-run-{seed}", "config_snapshot": cfg})
        await sim.run_simulation(steps=num_days * sim.sessions_per_day)
        prices = {sym: book.last_price or state.STOCKS[sym].initial_price for sym, book in bundle["market_books"].items()}
        snapshot = evaluator.get_snapshot(prices)
        analytics = evaluator.get_analytics()
        run_results.append(
            {
                "seed": seed,
                "pnl": round(snapshot["pnl"], 2),
                "pnl_pct": round(snapshot["pnl_pct"], 2),
                "total_value": round(snapshot["total_value"], 2),
                "sharpe_ratio": float(analytics.get("sharpe_ratio", 0.0)),
                "win_rate": float(analytics.get("win_rate", 0.0)),
                "max_drawdown": round(evaluator._max_drawdown * 100, 2),
                "trades": int(snapshot["trades"]),
            }
        )
    pnl_values = [row["pnl"] for row in run_results]
    sharpe_values = [row["sharpe_ratio"] for row in run_results]
    drawdowns = [row["max_drawdown"] for row in run_results]
    return {
        "bot_name": bot_name,
        "strategy_id": strategy_id,
        "scenario_id": scenario_id,
        "dataset_version": dataset_version,
        "runs": run_results,
        "aggregate": {
            "avg_pnl": round(mean(pnl_values), 2) if pnl_values else 0.0,
            "avg_sharpe_ratio": round(mean(sharpe_values), 3) if sharpe_values else 0.0,
            "avg_max_drawdown": round(mean(drawdowns), 2) if drawdowns else 0.0,
            "best_seed": max(run_results, key=lambda row: row["pnl"])["seed"] if run_results else None,
            "worst_seed": min(run_results, key=lambda row: row["pnl"])["seed"] if run_results else None,
        },
    }
