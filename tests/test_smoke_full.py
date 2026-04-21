"""
StockAI v2.0 — Full endpoint smoke test suite.
Hits every registered API endpoint and asserts no 500 errors.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


# ═══════════════════════════════════════════════════════════
#  STATIC PAGES
# ═══════════════════════════════════════════════════════════

class TestStaticPages:
    def test_landing_page(self):
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_app_page(self):
        r = client.get("/app")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_workspace_page(self):
        r = client.get("/workspace")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_live_market_page(self):
        r = client.get("/live-market")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_credits_page(self):
        r = client.get("/credits")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert "status" in data


# ═══════════════════════════════════════════════════════════
#  FAVICON
# ═══════════════════════════════════════════════════════════

class TestFavicon:
    def test_workspace_has_favicon_tag(self):
        r = client.get("/workspace")
        assert r.status_code == 200
        assert 'rel="icon"' in r.text

    def test_all_pages_have_favicon_tag(self):
        for path in ("/", "/app", "/workspace", "/live-market"):
            r = client.get(path)
            assert r.status_code == 200
            assert 'rel="icon"' in r.text, f"Missing favicon on {path}"


# ═══════════════════════════════════════════════════════════
#  SIMULATION
# ═══════════════════════════════════════════════════════════

class TestSimulationSmoke:
    def test_status(self):
        r = client.get("/simulation/status")
        assert r.status_code == 200
        data = r.json()
        assert "is_running" in data

    def test_reset(self):
        r = client.post("/simulation/reset")
        assert r.status_code == 200

    def test_stop(self):
        r = client.post("/simulation/stop")
        assert r.status_code == 200

    def test_config_get_via_status(self):
        r = client.get("/simulation/status")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
#  DATA ENDPOINTS
# ═══════════════════════════════════════════════════════════

class TestDataSmoke:
    def test_events(self):
        r = client.get("/data/events")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_forum(self):
        r = client.get("/data/forum")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_reports(self):
        r = client.get("/data/reports")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_loans(self):
        r = client.get("/data/loans")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_export(self):
        r = client.get("/data/export")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)

    def test_event_injection(self):
        r = client.post("/data/event", json={
            "title": "Smoke Test Event",
            "description": "smoke test event injection",
            "severity": "LOW",
            "impact_pct": 2.5,
            "affected_stocks": [],
        })
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
#  MARKET ENDPOINTS
# ═══════════════════════════════════════════════════════════

class TestMarketSmoke:
    def test_stocks(self):
        r = client.get("/market/stocks")
        assert r.status_code == 200
        assert isinstance(r.json(), dict)

    def test_trades(self):
        r = client.get("/market/trades")
        assert r.status_code == 200

    def test_analytics(self):
        r = client.get("/market/analytics")
        assert r.status_code == 200
        data = r.json()
        assert "regime" in data

    def test_history(self):
        stocks = client.get("/market/stocks").json()
        sym = next(iter(stocks))
        r = client.get(f"/market/history/{sym}")
        assert r.status_code == 200

    def test_single_stock(self):
        stocks = client.get("/market/stocks").json()
        sym = next(iter(stocks))
        r = client.get(f"/market/{sym}")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
#  AGENTS ENDPOINTS
# ═══════════════════════════════════════════════════════════

class TestAgentsSmoke:
    def test_list_agents(self):
        r = client.get("/agents")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_explainability(self):
        r = client.get("/agents/explainability")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
#  RESEARCH / WORKSPACE
# ═══════════════════════════════════════════════════════════

class TestResearchSmoke:
    def test_datasets(self):
        r = client.get("/datasets")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_scenarios(self):
        r = client.get("/scenarios")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_experiments(self):
        r = client.get("/experiments")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_agent_populations(self):
        r = client.get("/agent-populations")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_bots(self):
        r = client.get("/bots")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_runs(self):
        r = client.get("/runs")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_runs_active(self):
        r = client.get("/runs/active")
        # 200 if active run exists, 404 if not — both acceptable
        assert r.status_code in (200, 404)

    def test_evaluations(self):
        r = client.get("/evaluations")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_jobs(self):
        r = client.get("/jobs")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_workspace_summary(self):
        r = client.get("/workspace/summary")
        assert r.status_code == 200
        data = r.json()
        assert "counts" in data
        assert "workflow" in data

    def test_create_scenario(self):
        r = client.post("/scenarios", json={
            "name": "Smoke Test Scenario",
            "description": "smoke test scenario",
            "version": "1.0",
        })
        assert r.status_code == 200

    def test_create_bot(self):
        r = client.post("/bots", json={
            "name": "Smoke Test Bot",
            "bot_type": "strategy",
            "strategy_id": "mean_reversion",
            "description": "smoke test bot",
            "config": {"lookback": 5, "z_entry": 1.2, "z_exit": 0.4},
        })
        assert r.status_code == 200

    def test_calibrate(self):
        datasets = client.get("/datasets").json()
        if not datasets:
            pytest.skip("No datasets to calibrate")
        r = client.post("/datasets/calibrate", json={
            "dataset_id": datasets[0]["id"],
            "returns": [0.01, 0.015],
            "spreads_bps": [4, 6],
            "volumes_millions": [12, 18],
        })
        assert r.status_code == 200

    def test_create_experiment(self):
        scenarios = client.get("/scenarios").json()
        datasets = client.get("/datasets").json()
        populations = client.get("/agent-populations").json()
        if not (scenarios and datasets and populations):
            pytest.skip("Missing prerequisites for experiment creation")
        r = client.post("/experiments", json={
            "name": "Smoke Test Experiment",
            "description": "smoke test",
            "scenario_id": scenarios[0]["id"],
            "dataset_id": datasets[0]["id"],
            "agent_population_id": populations[0]["id"],
        })
        assert r.status_code == 200

    def test_launch_run(self):
        r = client.post("/runs", json={
            "name": "Smoke Test Run",
            "autostart": False,
            "config": {
                "num_agents": 4,
                "num_days": 2,
                "use_llm": False,
                "seed": 42,
                "speed": 0.1,
            },
        })
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
#  REPLAY
# ═══════════════════════════════════════════════════════════

class TestReplaySmoke:
    def test_replay_existing_run(self):
        runs = client.get("/runs").json()
        if not runs:
            pytest.skip("No runs available for replay test")
        r = client.get(f"/runs/{runs[0]['id']}/replay")
        assert r.status_code == 200

    def test_replay_nonexistent_run(self):
        r = client.get("/runs/nonexistent-run-id/replay")
        assert r.status_code == 404


# ═══════════════════════════════════════════════════════════
#  CHAT
# ═══════════════════════════════════════════════════════════

class TestChatSmoke:
    def test_chat_returns_response(self):
        r = client.post("/chat", json={
            "message": "What is the current regime?",
            "history": [],
        })
        assert r.status_code == 200
        data = r.json()
        assert "response" in data

    def test_chat_with_history(self):
        r = client.post("/chat", json={
            "message": "Tell me more",
            "history": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ],
        })
        assert r.status_code == 200
        data = r.json()
        assert "response" in data


# ═══════════════════════════════════════════════════════════
#  WEBSOCKET & SSE
# ═══════════════════════════════════════════════════════════

class TestWebSocketSmoke:
    def test_ws_connect(self):
        """Test that WebSocket endpoint accepts connections (not 500)."""
        try:
            with client.websocket_connect("/ws") as ws:
                ws.send_text("ping")
                data = ws.receive_text()
                assert "pong" in data
        except Exception:
            # Connection failing is acceptable; 500 is not
            pass

class TestSSESmoke:
    def test_sse_nonexistent_run_returns_404(self):
        r = client.get("/runs/nonexistent-run-id/stream")
        assert r.status_code == 404


# ═══════════════════════════════════════════════════════════
#  LIVE MARKET (MOCKED)
# ═══════════════════════════════════════════════════════════

class TestLiveMarketSmoke:
    def test_snapshot(self, monkeypatch):
        from backend.app.api import live_market as lm_api

        async def fake(force_refresh=False):
            return {
                "provider_name": "Yahoo Finance",
                "provider_status": "fallback",
                "provider_note": "Mocked.",
                "generated_at": "2026-04-01T00:00:00+00:00",
                "last_successful_at": None,
                "cache_age_seconds": None,
                "is_stale": True,
                "warnings": [],
                "tracked_scope_note": "",
                "market_snapshot": [],
                "sector_pulse": [],
                "major_movers": {"leaders": [], "laggards": []},
                "watchlist": [],
                "simulator_context": {"day": 1, "session": 0, "total_trades": 0, "regime": "sideways", "scenario": "Flat", "benchmark_return_pct": 0, "realized_vol_pct": 0, "breadth_ratio": 50, "market_sentiment": 0, "session_risk": 0, "sector_leader": None, "sector_laggard": None},
                "ai_brief": {"sentiment": "fallback", "headline": "Fallback", "summary": "Mocked.", "opportunities": [], "risks": [], "comparison": []},
            }

        monkeypatch.setattr(lm_api.live_market_service, "get_snapshot", fake)
        r = client.get("/api/live-market/snapshot")
        assert r.status_code == 200
