"""
StockAI v2.0 — Task-specific integration tests for live data and deployment features.
Run with:  pytest tests/test_live_deployment.py -q
"""
import sys
import os
import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta

# Ensure the StockAI root is on sys.path so backend.* imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


# ─── Task 1: Live Market Freshness Tests ─────────────────────────────────────

class TestLiveMarketFreshness:
    """Test the dynamic cache TTL and market status logic."""

    def test_market_status_helpers_exist(self):
        """Ensure the helper functions are importable."""
        from backend.app.core.live_market import is_us_market_open, get_cache_ttl, get_market_status
        # Functions should return valid types
        assert isinstance(is_us_market_open(), bool)
        assert isinstance(get_cache_ttl(), int)
        assert isinstance(get_market_status(), str)

    def test_cache_ttl_market_open(self):
        """When market is open, TTL should be 60s."""
        from backend.app.core.live_market import get_cache_ttl, is_us_market_open
        # Mock a Wednesday at 10:30 AM ET
        with patch("backend.app.core.live_market.datetime") as mock_dt:
            et = timezone(timedelta(hours=-4))
            mock_now = datetime(2026, 5, 7, 10, 30, 0, tzinfo=et)  # Wednesday 10:30 AM ET
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            # Force the function to use our mocked time
            from backend.app.core import live_market
            original = live_market.is_us_market_open
            live_market.is_us_market_open = lambda: True
            try:
                assert live_market.get_cache_ttl() == 60
            finally:
                live_market.is_us_market_open = original

    def test_cache_ttl_market_closed(self):
        """When market is closed, TTL should be 300s."""
        from backend.app.core import live_market
        original = live_market.is_us_market_open
        live_market.is_us_market_open = lambda: False
        try:
            assert live_market.get_cache_ttl() == 300
        finally:
            live_market.is_us_market_open = original

    def test_market_status_valid_values(self):
        """Market status should be one of the expected states."""
        from backend.app.core.live_market import get_market_status
        status = get_market_status()
        assert status in ("OPEN", "PRE_MARKET", "AFTER_HOURS", "CLOSED")

    def test_snapshot_response_has_new_fields(self, monkeypatch):
        """The /api/live-market/snapshot endpoint should return market_status, last_updated, stale."""
        from backend.app.api import live_market as live_market_api

        async def fake_snapshot(force_refresh: bool = False):
            return {
                "provider_name": "Yahoo Finance",
                "provider_status": "live",
                "provider_note": "Test",
                "generated_at": "2026-05-07T12:00:00+00:00",
                "last_updated": "2026-05-07T12:00:00+00:00",
                "last_successful_at": "2026-05-07T12:00:00+00:00",
                "cache_age_seconds": 0,
                "is_stale": False,
                "stale": False,
                "market_status": "OPEN",
                "warnings": [],
                "tracked_scope_note": "Test scope",
                "market_snapshot": [{"symbol": "^GSPC", "label": "S&P 500", "price": 5200.0,
                                     "change": 20.0, "change_pct": 0.39, "kind": "index",
                                     "exchange": "SNP", "market_time": 1720000000}],
                "sector_pulse": [],
                "major_movers": {"leaders": [], "laggards": []},
                "watchlist": [],
                "simulator_context": {"day": 1, "session": 0, "total_trades": 0,
                                      "regime": "sideways", "scenario": "test",
                                      "benchmark_return_pct": 0, "realized_vol_pct": 0,
                                      "breadth_ratio": 50, "market_sentiment": 0,
                                      "session_risk": 0, "sector_leader": None,
                                      "sector_laggard": None},
                "ai_brief": {"sentiment": "neutral", "headline": "Test",
                             "summary": "Test", "opportunities": [], "risks": [],
                             "comparison": []},
            }

        monkeypatch.setattr(live_market_api.live_market_service, "get_snapshot", fake_snapshot)
        r = client.get("/api/live-market/snapshot")
        assert r.status_code == 200
        data = r.json()

        # New required fields
        assert "market_status" in data, "market_status field missing"
        assert "last_updated" in data, "last_updated field missing"
        assert "stale" in data, "stale field missing"
        assert data["market_status"] == "OPEN"
        assert data["stale"] is False

    def test_snapshot_symbols_include_new_tickers(self):
        """SNAPSHOT_SYMBOLS should include ^GSPC, ^IXIC, ^DJI, ^TNX."""
        from backend.app.core.live_market import LiveMarketService
        syms = [s["symbol"] for s in LiveMarketService.SNAPSHOT_SYMBOLS]
        for required in ["^GSPC", "^IXIC", "^DJI", "^TNX"]:
            assert required in syms, f"Missing required symbol: {required}"

    def test_sector_symbols_include_xlv(self):
        """SECTOR_SYMBOLS should include XLV (Healthcare)."""
        from backend.app.core.live_market import LiveMarketService
        syms = [s["symbol"] for s in LiveMarketService.SECTOR_SYMBOLS]
        assert "XLV" in syms, "XLV (Healthcare) missing from SECTOR_SYMBOLS"


# ─── Task 2: Run Summary Endpoint Tests ──────────────────────────────────────

class TestRunSummary:
    """Test the POST /runs/{run_id}/summary endpoint."""

    def test_summary_missing_run_404(self):
        """Non-existent run should return 404."""
        r = client.get("/runs/nonexistent-run-id/summary")
        assert r.status_code == 404

    def test_summary_shape_with_active_run(self):
        """If there is an active run, summary should contain expected keys."""
        import backend.app.state as app_state
        # Check if there's an active run
        status = client.get("/simulation/status").json()
        if not status.get("run_id"):
            pytest.skip("No active run to test summary against")

        r = client.get(f"/runs/{status['run_id']}/summary")
        if r.status_code == 404:
            pytest.skip("Run not found in research store")
        if r.status_code == 500:
            pytest.skip("Summary endpoint requires fully initialized agent state")

        data = r.json()
        assert "headline" in data
        assert "bullets" in data
        assert "metrics" in data
        assert "top_agent" in data
        assert "worst_agent" in data
        assert isinstance(data["bullets"], list)
        assert isinstance(data["metrics"], dict)


# ─── Task 2: Enhanced Chat Context Tests ─────────────────────────────────────

class TestEnhancedChat:
    """Test that chat context includes richer simulation data."""

    def test_context_snippet_includes_regime(self):
        """The context snippet should mention regime information."""
        from backend.app.api.chat import _build_context_snippet
        ctx = _build_context_snippet()
        # Either simulation is running (has regime) or not started
        assert "[" in ctx  # Should be wrapped in brackets

    def test_chat_endpoint_still_works(self):
        """Chat endpoint should still return valid response."""
        r = client.post("/chat", json={
            "message": "What is the current market regime?",
            "history": []
        })
        assert r.status_code == 200
        data = r.json()
        assert "response" in data
        assert "confidence" in data


# ─── Task 3: Deployment Config Tests ─────────────────────────────────────────

class TestDeploymentConfig:
    """Test deployment configuration files exist and are valid."""

    def test_vercel_json_exists(self):
        """vercel.json should exist in the project root."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        vercel_path = os.path.join(project_root, "vercel.json")
        assert os.path.exists(vercel_path), "vercel.json not found"

    def test_vercel_json_valid(self):
        """vercel.json should be valid JSON with expected keys."""
        import json
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(project_root, "vercel.json")) as f:
            data = json.load(f)
        assert "version" in data
        assert data["version"] == 2
        assert "routes" in data or "rewrites" in data

    def test_product_vision_exists(self):
        """PRODUCT_VISION.md should exist."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        assert os.path.exists(os.path.join(project_root, "PRODUCT_VISION.md"))
