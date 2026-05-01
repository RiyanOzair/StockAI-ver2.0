"""
Research platform tests for StockAI's productization layer.
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from backend.app.engine.order_book import OrderBook
from backend.app.main import app
from backend.app.models.types import Order, OrderSide, OrderType

client = TestClient(app)


class TestResearchWorkspace:
    def test_workspace_page_served(self):
        response = client.get("/workspace")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        html = response.text
        for token in ("launchRunBtn", "createBotBtn", "runEvalBtn", "calibrateBtn", "exportRunBtn"):
            assert token in html

    def test_app_shell_exposes_workspace_and_run_context(self):
        response = client.get("/app")
        assert response.status_code == 200
        text = response.text
        assert "/workspace" in text
        assert "run-context-panel" in text

    def test_research_registry_routes(self):
        for path in ("/datasets", "/scenarios", "/experiments", "/bots", "/agent-populations", "/runs", "/jobs"):
            response = client.get(path)
            assert response.status_code == 200, path
            assert isinstance(response.json(), list)

    def test_workspace_summary_route(self):
        response = client.get("/workspace/summary")
        assert response.status_code == 200
        payload = response.json()
        for key in ("status", "counts", "workflow", "next_actions", "leaderboard"):
            assert key in payload
        assert payload["counts"]["datasets"] >= 1
        assert "run_configured" in payload["workflow"]

    def test_active_run_and_run_events(self):
        run = client.get("/runs/active")
        assert run.status_code == 200
        payload = run.json()
        assert payload["id"]
        events = client.get(f"/runs/{payload['id']}/events")
        assert events.status_code == 200
        event_list = events.json()
        assert event_list
        assert any(evt["event_type"] == "run_configured" for evt in event_list)

    def test_run_export_bundle(self):
        run = client.get("/runs/active").json()
        response = client.get(f"/runs/{run['id']}/export")
        assert response.status_code == 200
        payload = response.json()
        assert payload["run"]["id"] == run["id"]
        assert "events" in payload

    def test_status_exposes_research_fields(self):
        response = client.get("/simulation/status")
        data = response.json()
        for key in ("run_id", "session_phase", "dataset_version", "scenario_id", "training_mode", "latency_ms", "slippage_bps"):
            assert key in data


class TestCalibrationAndEvaluation:
    def test_dataset_calibration_bounded_output(self):
        response = client.post(
            "/datasets/calibrate",
            json={
                "dataset_id": "dataset-us-equities-core-v1",
                "returns": [0.01, 0.015, 0.02, 0.03],
                "spreads_bps": [3.5, 5.0, 9.0, 12.0],
                "volumes_millions": [12, 15, 22, 28],
                "event_frequency": 1.1,
            },
        )
        assert response.status_code == 200
        calibration = response.json()["calibration"]
        assert 0.004 <= calibration["volatility_bands"]["low"] <= calibration["volatility_bands"]["high"] <= 0.09
        assert 2.0 <= calibration["spread_bps"]["deep"] <= calibration["spread_bps"]["thin"] <= 80.0

    def test_run_launch_creates_new_research_run(self):
        before = client.get("/runs").json()
        response = client.post(
            "/runs",
            json={
                "name": "Deterministic Smoke Run",
                "autostart": False,
                "config": {"num_agents": 6, "num_days": 2, "use_llm": False, "seed": 42, "speed": 0.1},
            },
        )
        assert response.status_code == 200
        run = response.json()["run"]
        assert run["name"] == "Deterministic Smoke Run"
        after = client.get("/runs").json()
        assert len(after) >= len(before)
        active = client.get("/runs/active").json()
        assert active["id"] == run["id"]

    def test_run_launch_validates_dataset_reference(self):
        response = client.post(
            "/runs",
            json={
                "name": "Broken Run",
                "autostart": False,
                "config": {
                    "num_agents": 6,
                    "num_days": 2,
                    "use_llm": False,
                    "seed": 42,
                    "speed": 0.1,
                    "dataset_version": "dataset-does-not-exist",
                },
            },
        )
        assert response.status_code == 404

    def test_sync_evaluation_creates_completed_report(self):
        bot = client.post(
            "/bots",
            json={"name": "PySDK Mean Reversion", "bot_type": "strategy", "strategy_id": "mean_reversion", "config": {"lookback": 4}},
        )
        assert bot.status_code == 200
        evaluation = client.post(
            "/evaluations",
            json={
                "name": "Mean Reversion Eval",
                "bot_id": bot.json()["id"],
                "seeds": [5, 7],
                "num_days": 1,
                "run_async": False,
            },
        )
        assert evaluation.status_code == 200
        payload = evaluation.json()
        assert payload["status"] == "completed"
        assert "avg_pnl" in payload["metrics"]

    def test_experiment_creation_validates_references(self):
        response = client.post(
            "/experiments",
            json={
                "name": "Invalid Experiment",
                "scenario_id": "scenario-missing",
                "dataset_id": "dataset-us-equities-core-v1",
                "agent_population_id": "population-core-mixed-v1",
            },
        )
        assert response.status_code == 404


class TestExecutionKernel:
    def test_market_order_matches_and_does_not_rest(self):
        book = OrderBook("AAPL")
        first_sell = Order(
            id="sell-1",
            agent_id="seller-a",
            stock_symbol="AAPL",
            side=OrderSide.SELL,
            type=OrderType.LIMIT,
            price=100.0,
            quantity=5,
            timestamp=datetime.now(),
        )
        second_sell = Order(
            id="sell-2",
            agent_id="seller-b",
            stock_symbol="AAPL",
            side=OrderSide.SELL,
            type=OrderType.LIMIT,
            price=100.0,
            quantity=5,
            timestamp=datetime.now() + timedelta(milliseconds=1),
        )
        book.add_order(first_sell)
        book.add_order(second_sell)
        market_buy = Order(
            id="buy-1",
            agent_id="buyer-a",
            stock_symbol="AAPL",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            price=0.0,
            quantity=3,
            timestamp=datetime.now() + timedelta(milliseconds=2),
        )
        trades = book.add_order(market_buy)
        assert len(trades) == 1
        assert trades[0].sell_order_id == "sell-1"
        assert market_buy.filled_quantity == 3
        assert len(book.bids) == 0

    def test_price_priority_then_time_priority(self):
        book = OrderBook("MSFT")
        low_bid = Order(id="bid-low", agent_id="a", stock_symbol="MSFT", side=OrderSide.BUY, type=OrderType.LIMIT, price=99.0, quantity=5, timestamp=datetime.now())
        high_bid_early = Order(id="bid-high-early", agent_id="b", stock_symbol="MSFT", side=OrderSide.BUY, type=OrderType.LIMIT, price=101.0, quantity=5, timestamp=datetime.now() + timedelta(milliseconds=1))
        high_bid_late = Order(id="bid-high-late", agent_id="c", stock_symbol="MSFT", side=OrderSide.BUY, type=OrderType.LIMIT, price=101.0, quantity=5, timestamp=datetime.now() + timedelta(milliseconds=2))
        book.add_order(low_bid)
        book.add_order(high_bid_early)
        book.add_order(high_bid_late)
        sell = Order(id="sell-hit", agent_id="seller", stock_symbol="MSFT", side=OrderSide.SELL, type=OrderType.MARKET, price=0.0, quantity=6, timestamp=datetime.now() + timedelta(milliseconds=3))
        trades = book.add_order(sell)
        assert len(trades) == 2
        assert trades[0].buy_order_id == "bid-high-early"
        assert trades[1].buy_order_id == "bid-high-late"
