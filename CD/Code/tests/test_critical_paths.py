"""
StockAI v2.0 â€” Critical path tests (FastAPI / httpx TestClient)
Run with:  pytest tests/ -q
"""
import sys
import os
import pytest

# Ensure the StockAI root is on sys.path so backend.* imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


# â”€â”€â”€ Health â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestHealth:
    def test_root_health(self):
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_health_endpoint(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "StockAI v2.0 Online"

    def test_frontend_served(self):
        r = client.get("/app")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_live_market_page_served(self):
        r = client.get("/live-market")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]


# â”€â”€â”€ Market â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestMarket:
    def test_get_all_stocks(self):
        r = client.get("/market/stocks")
        assert r.status_code == 200
        data = r.json()
        assert len(data) > 0
        for sym, meta in data.items():
            assert "price" in meta
            assert "sector" in meta

    def test_get_stock_by_symbol(self):
        # Pick the first known symbol
        stocks = client.get("/market/stocks").json()
        sym = next(iter(stocks))
        r = client.get(f"/market/{sym}")
        assert r.status_code == 200
        assert r.json()["symbol"] == sym

    def test_get_unknown_symbol_404(self):
        r = client.get("/market/ZZZZ")
        assert r.status_code == 404

    def test_price_history(self):
        stocks = client.get("/market/stocks").json()
        sym = next(iter(stocks))
        r = client.get(f"/market/history/{sym}")
        assert r.status_code == 200
        assert "history" in r.json()

    def test_market_analytics_shape(self):
        r = client.get("/market/analytics")
        assert r.status_code == 200
        data = r.json()
        for key in ("regime", "benchmark", "breadth", "sectors", "realized_vol_pct", "turnover"):
            assert key in data, f"missing key: {key}"


# â”€â”€â”€ Simulation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestSimulation:
    def test_status_shape(self):
        r = client.get("/simulation/status")
        assert r.status_code == 200
        data = r.json()
        for key in ("is_running", "is_paused", "day", "total_days", "total_trades", "active_agents"):
            assert key in data, f"missing key: {key}"
        for key in ("market_analytics", "benchmark", "breadth", "regime", "realized_vol_pct", "turnover"):
            assert key in data, f"missing analytics key: {key}"

    def test_config_valid(self):
        r = client.post("/simulation/config", json={"num_agents": 6, "num_days": 5})
        assert r.status_code == 200
        assert r.json()["config"]["num_agents"] == 6

    def test_config_rejects_running_sim(self):
        # Directly set is_running; background tasks fire after response
        # so we can't rely on POST /start to flip the flag in time.
        from backend.app import state as app_state
        app_state.simulation.is_running = True
        try:
            r = client.post("/simulation/config", json={"num_days": 3})
            assert r.status_code == 400
        finally:
            app_state.simulation.is_running = False
            client.post("/simulation/reset")

    def test_config_validation_speed_bounds(self):
        # speed must be >= 0.1 and <= 30
        r = client.post("/simulation/config", json={"num_days": 1, "speed": 0.0})
        assert r.status_code == 422  # Pydantic validation error

    def test_config_validation_speed_negative(self):
        r = client.post("/simulation/config", json={"num_days": 1, "speed": -5.0})
        assert r.status_code == 422

    def test_snapshots_list(self):
        r = client.get("/simulation/snapshots")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_snapshot_missing_day_404(self):
        r = client.get("/simulation/snapshots/99999")
        assert r.status_code == 404


# â”€â”€â”€ Agents â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestAgents:
    def test_list_agents(self):
        r = client.get("/agents")
        assert r.status_code == 200
        agents = r.json()
        assert len(agents) > 0
        for a in agents:
            for key in ("id", "name", "cash", "pnl", "status", "trades"):
                assert key in a, f"missing key: {key}"

    def test_agent_analytics(self):
        agents = client.get("/agents").json()
        aid = agents[0]["id"]
        r = client.get(f"/agents/{aid}/analytics")
        assert r.status_code == 200
        data = r.json()
        for key in ("sharpe_ratio", "max_drawdown", "win_rate", "total_trades"):
            assert key in data
        for key in ("sortino_ratio", "beta", "volatility", "concentration_hhi", "cash_ratio", "debt_ratio", "attribution"):
            assert key in data
        for key in ("sector_pnl", "trading_pnl", "mark_to_market_pnl", "best_contributor", "worst_contributor"):
            assert key in data["attribution"]

    def test_agent_decisions(self):
        agents = client.get("/agents").json()
        aid = agents[0]["id"]
        r = client.get(f"/agents/{aid}/decisions")
        assert r.status_code == 200
        assert "decisions" in r.json()

    def test_missing_agent_404(self):
        r = client.get("/agents/nonexistent-id/analytics")
        assert r.status_code == 404

    def test_create_custom_agent(self):
        payload = {
            "name": "TestBot",
            "character_type": "Aggressive",
            "description": "A test agent",
            "risk_tolerance": "High",
        }
        r = client.post("/agents/custom", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert "id" in data
        # ID must be a valid UUID (not a sequential integer that could collide)
        import uuid
        uuid.UUID(data["id"])  # raises ValueError if not a valid UUID


# â”€â”€â”€ Data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestData:
    def test_events_list(self):
        r = client.get("/data/events")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_forum_list(self):
        r = client.get("/data/forum")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_reports_list(self):
        r = client.get("/data/reports")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_loans_list(self):
        r = client.get("/data/loans")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_export_shape(self):
        r = client.get("/data/export")
        assert r.status_code == 200
        data = r.json()
        for key in ("config", "stocks", "agents", "trades", "events", "price_history"):
            assert key in data, f"missing export key: {key}"
        for key in ("benchmark_history", "regime_history", "market_analytics", "agent_risk_snapshots"):
            assert key in data, f"missing enhanced export key: {key}"


class TestLiveMarket:
    def test_live_market_snapshot_shape(self, monkeypatch):
        from backend.app.api import live_market as live_market_api

        async def fake_snapshot(force_refresh: bool = False):
            return {
                "provider_name": "Yahoo Finance",
                "provider_status": "live",
                "provider_note": "Mocked live provider.",
                "generated_at": "2026-04-01T12:00:00+00:00",
                "last_successful_at": "2026-04-01T12:00:00+00:00",
                "cache_age_seconds": 0,
                "is_stale": False,
                "warnings": [],
                "tracked_scope_note": "Tracked movers only.",
                "market_snapshot": [{"symbol": "SPY", "label": "S&P 500", "price": 510.2, "change": 4.2, "change_pct": 0.83, "kind": "index", "exchange": "NYSE", "market_time": 1711972800}],
                "sector_pulse": [{"symbol": "XLK", "label": "Technology", "change_pct": 1.2, "price": 220.4, "momentum": "accelerating"}],
                "major_movers": {
                    "leaders": [{"symbol": "NVDA", "name": "NVIDIA", "price": 912.0, "change": 22.0, "change_pct": 2.47, "market_time": 1711972800}],
                    "laggards": [{"symbol": "TSLA", "name": "Tesla", "price": 171.0, "change": -4.5, "change_pct": -2.56, "market_time": 1711972800}],
                },
                "watchlist": [{"symbol": "AAPL", "name": "Apple", "price": 192.4, "change": 1.1, "change_pct": 0.58, "day_low": 189.1, "day_high": 193.0, "market_time": 1711972800, "exchange": "NasdaqGS", "sparkline": [189.1, 190.2, 191.7, 192.4]}],
                "simulator_context": {"day": 4, "session": 2, "total_trades": 88, "regime": "bull_market", "scenario": "Risk-on tape", "benchmark_return_pct": 6.4, "realized_vol_pct": 12.1, "breadth_ratio": 68.0, "market_sentiment": 0.74, "session_risk": 0.33, "sector_leader": {"label": "Tech", "index": 107.2}, "sector_laggard": {"label": "Retail", "index": 98.1}},
                "ai_brief": {"sentiment": "risk-on", "headline": "Risk appetite is pushing the tape higher", "summary": "Mocked brief.", "opportunities": [{"title": "NVDA is the velocity leader", "detail": "Still pressing higher."}], "risks": [{"title": "TSLA is dragging", "detail": "Relative weakness is visible."}], "comparison": ["Breadth is stronger than the simulator baseline."]},
            }

        monkeypatch.setattr(live_market_api.live_market_service, "get_snapshot", fake_snapshot)
        r = client.get("/api/live-market/snapshot")
        assert r.status_code == 200
        data = r.json()
        for key in ("provider_name", "provider_status", "market_snapshot", "sector_pulse", "major_movers", "watchlist", "simulator_context", "ai_brief"):
            assert key in data, f"missing live-market key: {key}"
        assert data["provider_status"] == "live"
        assert len(data["market_snapshot"]) == 1

    def test_live_market_snapshot_fallback_state(self, monkeypatch):
        from backend.app.api import live_market as live_market_api

        async def fake_fallback(force_refresh: bool = False):
            return {
                "provider_name": "Yahoo Finance",
                "provider_status": "fallback",
                "provider_note": "Provider unavailable.",
                "generated_at": "2026-04-01T12:00:00+00:00",
                "last_successful_at": None,
                "cache_age_seconds": None,
                "is_stale": True,
                "warnings": ["Live market quotes could not be loaded right now."],
                "tracked_scope_note": "Tracked real-market cards will repopulate automatically.",
                "market_snapshot": [],
                "sector_pulse": [],
                "major_movers": {"leaders": [], "laggards": []},
                "watchlist": [],
                "simulator_context": {"day": 1, "session": 0, "total_trades": 0, "regime": "sideways", "scenario": "Flat tape", "benchmark_return_pct": 0.0, "realized_vol_pct": 0.0, "breadth_ratio": 50.0, "market_sentiment": 0.0, "session_risk": 0.0, "sector_leader": None, "sector_laggard": None},
                "ai_brief": {"sentiment": "fallback", "headline": "Fallback active", "summary": "Waiting for the next successful refresh.", "opportunities": [], "risks": [], "comparison": ["Simulator remains available."]},
            }

        monkeypatch.setattr(live_market_api.live_market_service, "get_snapshot", fake_fallback)
        r = client.get("/api/live-market/snapshot?refresh=true")
        assert r.status_code == 200
        data = r.json()
        assert data["provider_status"] == "fallback"
        assert data["market_snapshot"] == []
        assert data["warnings"]


# â”€â”€â”€ Explainability â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestExplainability:
    def test_explainability_shape(self):
        r = client.get("/agents/explainability")
        assert r.status_code == 200
        data = r.json()
        for key in ("bias_counts", "action_distribution", "per_agent"):
            assert key in data, f"missing key in explainability: {key}"
        for key in ("avg_conviction", "thesis_drift_total", "decision_consistency_avg"):
            assert key in data, f"missing enhanced explainability key: {key}"

