import math
from collections import defaultdict
from typing import Dict, List, Tuple


def _safe_mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _safe_std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean_v = _safe_mean(values)
    variance = sum((v - mean_v) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def _pct_change(current: float, base: float) -> float:
    if not base:
        return 0.0
    return (current - base) / base


def compute_index_level(price_map: Dict[str, float], base_prices: Dict[str, float]) -> float:
    returns = [_pct_change(price_map[sym], base_prices[sym]) for sym in price_map if sym in base_prices]
    return round(100.0 * (1.0 + _safe_mean(returns)), 2) if returns else 100.0


def compute_sector_indices(price_map: Dict[str, float], stock_meta: Dict, base_prices: Dict[str, float]) -> Dict[str, float]:
    grouped: Dict[str, List[float]] = defaultdict(list)
    for sym, price in price_map.items():
        if sym not in stock_meta or sym not in base_prices:
            continue
        grouped[stock_meta[sym].sector].append(_pct_change(price, base_prices[sym]))
    return {
        sector: round(100.0 * (1.0 + _safe_mean(changes)), 2)
        for sector, changes in grouped.items()
    }


def compute_market_breadth(price_map: Dict[str, float], base_prices: Dict[str, float]) -> Dict[str, float]:
    changes = [_pct_change(price_map[sym], base_prices[sym]) for sym in price_map if sym in base_prices]
    if not changes:
        return {"advancers": 0, "decliners": 0, "breadth_ratio": 0.0, "dispersion": 0.0}
    advancers = sum(1 for ch in changes if ch > 0)
    decliners = sum(1 for ch in changes if ch < 0)
    breadth_ratio = advancers / max(1, advancers + decliners)
    dispersion = _safe_std(changes)
    return {
        "advancers": advancers,
        "decliners": decliners,
        "breadth_ratio": round(breadth_ratio, 4),
        "dispersion": round(dispersion, 4),
    }


def compute_drawdown(series: List[float]) -> float:
    if not series:
        return 0.0
    peak = series[0]
    max_dd = 0.0
    for value in series:
        peak = max(peak, value)
        if peak > 0:
            max_dd = max(max_dd, (peak - value) / peak)
    return max_dd


def compute_returns(series: List[float]) -> List[float]:
    returns = []
    for prev, curr in zip(series, series[1:]):
        if prev:
            returns.append((curr - prev) / prev)
    return returns


def compute_agent_metrics(agent, simulation, current_prices: Dict[str, float], stock_meta: Dict) -> Dict:
    snapshot = agent.get_snapshot(current_prices)
    portfolio_history = getattr(agent, "_portfolio_history", [])
    bench_history = [p["value"] for p in simulation.benchmark_history[: len(portfolio_history)]]
    returns = compute_returns(portfolio_history)
    benchmark_returns = compute_returns(bench_history)
    downside = [r for r in returns if r < 0]

    # FIX H8: 1008 = 252 trading days × 4 sessions per day — matches per-session return frequency
    volatility = _safe_std(returns) * math.sqrt(1008) if returns else 0.0
    sortino = 0.0
    if downside:
        sortino = (_safe_mean(returns) / _safe_std(downside)) * math.sqrt(1008) if _safe_std(downside) > 0 else 0.0

    beta = 0.0
    if len(returns) > 1 and len(benchmark_returns) == len(returns):
        mean_r = _safe_mean(returns)
        mean_b = _safe_mean(benchmark_returns)
        covariance = _safe_mean([(r - mean_r) * (b - mean_b) for r, b in zip(returns, benchmark_returns)])
        variance_b = _safe_mean([(b - mean_b) ** 2 for b in benchmark_returns])
        beta = covariance / variance_b if variance_b > 0 else 0.0

    holdings = snapshot["holdings"]
    total_value = max(snapshot["total_value"], 1.0)
    concentration_weights = []
    sector_pnl = defaultdict(float)
    best_contrib: Tuple[str, float] | None = None
    worst_contrib: Tuple[str, float] | None = None
    mtm_contrib_total = 0.0
    for sym, qty in holdings.items():
        price = current_prices.get(sym, 0.0)
        initial = agent.initial_prices.get(sym, price)
        position_value = qty * price
        if position_value > 0:
            weight = position_value / total_value
            concentration_weights.append(weight)
        contribution = qty * (price - initial)
        mtm_contrib_total += contribution
        sector = stock_meta[sym].sector if sym in stock_meta else "Other"
        sector_pnl[sector] += contribution
        if best_contrib is None or contribution > best_contrib[1]:
            best_contrib = (sym, contribution)
        if worst_contrib is None or contribution < worst_contrib[1]:
            worst_contrib = (sym, contribution)

    trade_pnl_proxy = snapshot["pnl"] - mtm_contrib_total
    concentration = sum(weight ** 2 for weight in concentration_weights)
    cash_ratio = snapshot["cash"] / total_value
    debt_ratio = snapshot["debt"] / total_value if total_value > 0 else 0.0
    regime_values = [point["portfolio_value"] for point in agent._regime_performance.values()] or [total_value]
    regime_relative = total_value - _safe_mean(regime_values)
    consistency = getattr(agent, "_consistency_score", 100.0)

    return {
        "agent_id": str(agent.id),
        "sharpe_ratio": round(agent.get_analytics()["sharpe_ratio"], 3),
        "sortino_ratio": round(sortino, 3),
        "beta": round(beta, 3),
        "volatility": round(volatility * 100, 2),
        "max_drawdown": round(agent._max_drawdown * 100, 2),
        "win_rate": round(agent.get_analytics()["win_rate"], 1),
        "hit_rate": round(agent.get_analytics()["win_rate"], 1),
        "avg_trade_size": round(agent.get_analytics()["avg_trade_size"], 1),
        "total_trades": snapshot["trades"],
        "concentration_hhi": round(concentration, 3),
        "cash_ratio": round(cash_ratio * 100, 2),
        "debt_ratio": round(debt_ratio * 100, 2),
        "consistency_score": round(consistency, 1),
        "attribution": {
            "sector_pnl": {k: round(v, 2) for k, v in sorted(sector_pnl.items())},
            "trading_pnl": round(trade_pnl_proxy, 2),
            "mark_to_market_pnl": round(mtm_contrib_total, 2),
            "best_contributor": {
                "symbol": best_contrib[0] if best_contrib else None,
                "pnl": round(best_contrib[1], 2) if best_contrib else 0.0,
            },
            "worst_contributor": {
                "symbol": worst_contrib[0] if worst_contrib else None,
                "pnl": round(worst_contrib[1], 2) if worst_contrib else 0.0,
            },
            "regime_relative_performance": round(regime_relative, 2),
        },
    }


def compute_market_analytics(simulation, current_prices: Dict[str, float], stock_meta: Dict) -> Dict:
    base_prices = simulation.base_prices
    benchmark_series = [point["value"] for point in simulation.benchmark_history]
    latest_index = benchmark_series[-1] if benchmark_series else 100.0
    realized_vol = _safe_std(compute_returns(benchmark_series[-20:])) * math.sqrt(252) if len(benchmark_series) > 2 else 0.0
    breadth = compute_market_breadth(current_prices, base_prices)
    sector_indices = compute_sector_indices(current_prices, stock_meta, base_prices)
    return {
        "regime": simulation.current_regime,
        "benchmark": {
            "level": round(latest_index, 2),
            "return_pct": round(latest_index - 100.0, 2),
            "drawdown_pct": round(compute_drawdown(benchmark_series) * 100, 2),
        },
        "sectors": sector_indices,
        "breadth": breadth,
        "realized_vol_pct": round(realized_vol * 100, 2),
        "turnover": round(simulation.turnover, 2),
        "market_sentiment": simulation.market_sentiment,
        "session_risk": simulation.session_risk,
        "scenario": simulation.current_regime_profile.get("headline", simulation.current_regime.replace("_", " ").title()),
    }
