from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from backend.app.models.research import (
    AgentPopulationRecord,
    BackgroundJobRecord,
    BotDefinitionRecord,
    CalibrationProfile,
    DatasetVersionRecord,
    EvaluationReportRecord,
    ExperimentRecord,
    RunEventRecord,
    RunRecord,
    ScenarioRecord,
)


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_db_path() -> Path:
    env_path = os.getenv("STOCKAI_DB_PATH")
    if env_path:
        return Path(env_path)
    runtime_dir = _repo_root() / "backend" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir / "stockai_research.db"


class ResearchStore:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path or default_db_path())
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_schema()
        self.seed_defaults()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS datasets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS scenarios (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS experiments (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS agent_populations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS bots (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    scenario_id TEXT,
                    dataset_id TEXT,
                    experiment_id TEXT,
                    agent_population_id TEXT,
                    seed INTEGER,
                    payload_json TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS run_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_run_events_run_id_sequence
                    ON run_events(run_id, sequence);
                CREATE TABLE IF NOT EXISTS evaluations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    bot_id TEXT NOT NULL,
                    experiment_id TEXT,
                    scenario_id TEXT,
                    dataset_id TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS agent_notebooks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    day INTEGER NOT NULL,
                    session INTEGER NOT NULL,
                    entry_type TEXT NOT NULL, -- thesis, review, research
                    content TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_agent_notebooks_run_agent
                    ON agent_notebooks(run_id, agent_id);
                """
            )

    def save_notebook_entry(self, run_id: str, agent_id: str, day: int, session: int, entry_type: str, content: str, payload_json: Dict[str, Any] = None) -> Dict[str, Any]:
        now = utcnow_iso()
        payload = payload_json or {}
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_notebooks (run_id, agent_id, day, session, entry_type, content, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, agent_id, day, session, entry_type, content, self._serialize(payload), now),
            )
        return {"run_id": run_id, "agent_id": agent_id, "day": day, "session": session, "entry_type": entry_type, "content": content, "created_at": now}

    def list_notebook_entries(self, run_id: str, agent_id: Optional[str] = None, limit: int = 50) -> list[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            if agent_id:
                rows = conn.execute(
                    "SELECT * FROM agent_notebooks WHERE run_id = ? AND agent_id = ? ORDER BY id DESC LIMIT ?",
                    (run_id, agent_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM agent_notebooks WHERE run_id = ? ORDER BY id DESC LIMIT ?",
                    (run_id, limit),
                ).fetchall()
        return [dict(row) for row in rows]


    def _serialize(self, data: Dict[str, Any]) -> str:
        return json.dumps(data, default=str)

    def _deserialize(self, value: str) -> Dict[str, Any]:
        return json.loads(value) if value else {}

    def _upsert_payload_record(
        self,
        table: str,
        *,
        record_id: str,
        name: str,
        status: str,
        payload: Dict[str, Any],
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = utcnow_iso()
        with self._lock, self._connect() as conn:
            existing = conn.execute(f"SELECT created_at FROM {table} WHERE id = ?", (record_id,)).fetchone()
            created_at = existing["created_at"] if existing else now
            columns = ["id", "name", "status", "payload_json", "created_at", "updated_at"]
            values = [record_id, name, status, self._serialize(payload), created_at, now]
            if version is not None:
                columns.insert(2, "version")
                values.insert(2, version)
            placeholders = ", ".join("?" for _ in columns)
            update_clause = ", ".join(f"{column} = excluded.{column}" for column in columns[1:])
            conn.execute(
                f"""
                INSERT INTO {table} ({", ".join(columns)})
                VALUES ({placeholders})
                ON CONFLICT(id) DO UPDATE SET {update_clause}
                """,
                values,
            )
        return self.get_record(table, record_id) or {}

    def get_record(self, table: str, record_id: str) -> Optional[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (record_id,)).fetchone()
        return self._row_to_record(table, row) if row else None

    def list_records(self, table: str) -> list[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(f"SELECT * FROM {table} ORDER BY updated_at DESC, created_at DESC").fetchall()
        return [self._row_to_record(table, row) for row in rows]

    def _row_to_record(self, table: str, row: sqlite3.Row) -> Dict[str, Any]:
        if table == "runs":
            payload = self._deserialize(row["payload_json"])
            payload.update(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "status": row["status"],
                    "scenario_id": row["scenario_id"],
                    "dataset_id": row["dataset_id"],
                    "experiment_id": row["experiment_id"],
                    "agent_population_id": row["agent_population_id"],
                    "seed": row["seed"],
                    "summary": self._deserialize(row["summary_json"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )
            return payload
        if table == "run_events":
            return {
                "sequence": row["sequence"],
                "run_id": row["run_id"],
                "event_type": row["event_type"],
                "phase": row["phase"],
                "payload": self._deserialize(row["payload_json"]),
                "created_at": row["created_at"],
            }
        if table == "jobs":
            payload = self._deserialize(row["payload_json"])
            payload.update(
                {
                    "id": row["id"],
                    "job_type": row["job_type"],
                    "status": row["status"],
                    "result": self._deserialize(row["result_json"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )
            return payload
        payload = self._deserialize(row["payload_json"])
        payload.update(
            {
                "id": row["id"],
                "name": row["name"],
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
        if "version" in row.keys():
            payload["version"] = row["version"]
        return payload

    def seed_defaults(self):
        if self.list_records("datasets"):
            return
        sector_correlation = {
            "Technology": {"Technology": 1.0, "Energy": 0.18, "Financials": 0.31, "Consumer": 0.27},
            "Energy": {"Technology": 0.18, "Energy": 1.0, "Financials": 0.29, "Consumer": 0.16},
            "Financials": {"Technology": 0.31, "Energy": 0.29, "Financials": 1.0, "Consumer": 0.34},
            "Consumer": {"Technology": 0.27, "Energy": 0.16, "Financials": 0.34, "Consumer": 1.0},
        }
        calibration = CalibrationProfile(
            version="us-cash-calibration-2026.04",
            reference_mode="embedded_priors",
            volatility_bands={"low": 0.008, "medium": 0.015, "high": 0.027, "shock": 0.045},
            spread_bps={"deep": 4.0, "core": 8.0, "satellite": 15.0, "thin": 28.0},
            average_daily_volume_millions={"deep": 65.0, "core": 28.0, "satellite": 11.0, "thin": 4.0},
            sector_correlation=sector_correlation,
            event_frequency=1.0,
            regime_transition_bias={"risk_on": 0.24, "risk_off": 0.16, "earnings_repricing": 0.22, "policy_tightening": 0.18, "inflation_shock": 0.10, "sector_rotation": 0.10},
            notes=[
                "Embedded US cash-market priors for a local-first research workflow.",
                "Calibration pipeline can overwrite these priors with user-supplied historical reference series.",
            ],
        )
        dataset = DatasetVersionRecord(
            id="dataset-us-equities-core-v1",
            name="US Equities Core",
            version="2026.04",
            universe_id="us-equities-core-v1",
            description="Core US equities cash-market calibration baseline for StockAI.",
            calibration=calibration,
            metadata={"market_scope": "US equities cash", "reference_window": "embedded default priors"},
        )
        scenario = ScenarioRecord(
            id="scenario-hybrid-baseline-v1",
            name="Hybrid Baseline",
            version="1.0",
            description="Balanced synthetic market with realistic dispersion, event flow, and liquidity shifts.",
            regime_overrides={"risk_on_weight": 1.0, "risk_off_weight": 1.0},
            shock_profile={"volatility_shock_prob": 0.08, "halt_prob": 0.03},
            config_overrides={"liquidity_model": "adaptive", "latency_ms": 120, "slippage_bps": 6.0},
        )
        population = AgentPopulationRecord(
            id="population-core-mixed-v1",
            name="Core Mixed Population",
            description="LLM behavioral agents blended with deterministic baselines and strategy slots.",
            composition={"llm_ratio": 0.35, "rule_ratio": 0.45, "strategy_ratio": 0.20, "deterministic_only_mode": False},
        )
        experiment = ExperimentRecord(
            id="experiment-default-research-v1",
            name="Default Research Workspace",
            description="Baseline experiment scaffold for local researchers and bot builders.",
            scenario_id=scenario.id,
            dataset_id=dataset.id,
            agent_population_id=population.id,
            status="ready",
            config_snapshot={"training_mode": "hybrid", "evaluation_mode": "rolling"},
        )
        bots: Iterable[BotDefinitionRecord] = (
            BotDefinitionRecord(
                id="bot-benchmark-vwap-v1",
                name="VWAP Benchmark",
                bot_type="deterministic",
                strategy_id="benchmark_vwap",
                class_name="VWAPBenchmarkStrategy",
                description="Deterministic execution-style benchmark for reproducible comparisons.",
                config={"participation_rate": 0.12},
            ),
            BotDefinitionRecord(
                id="bot-mean-reversion-v1",
                name="Mean Reversion Template",
                bot_type="strategy",
                strategy_id="mean_reversion",
                class_name="MeanReversionStrategy",
                description="Python SDK template strategy for research experiments and bot training.",
                config={"lookback": 5, "z_entry": 1.2, "z_exit": 0.3},
            ),
        )
        self.save_dataset(dataset)
        self.save_scenario(scenario)
        self.save_agent_population(population)
        self.save_experiment(experiment)
        for bot in bots:
            self.save_bot(bot)

    def save_dataset(self, dataset: DatasetVersionRecord) -> Dict[str, Any]:
        return self._upsert_payload_record(
            "datasets",
            record_id=dataset.id,
            name=dataset.name,
            status=dataset.status,
            version=dataset.version,
            payload=dataset.model_dump(mode="json"),
        )

    def save_scenario(self, scenario: ScenarioRecord) -> Dict[str, Any]:
        return self._upsert_payload_record(
            "scenarios",
            record_id=scenario.id,
            name=scenario.name,
            status=scenario.status,
            version=scenario.version,
            payload=scenario.model_dump(mode="json"),
        )

    def save_experiment(self, experiment: ExperimentRecord) -> Dict[str, Any]:
        return self._upsert_payload_record(
            "experiments",
            record_id=experiment.id,
            name=experiment.name,
            status=experiment.status,
            payload=experiment.model_dump(mode="json"),
        )

    def save_agent_population(self, population: AgentPopulationRecord) -> Dict[str, Any]:
        return self._upsert_payload_record(
            "agent_populations",
            record_id=population.id,
            name=population.name,
            status=population.status,
            payload=population.model_dump(mode="json"),
        )

    def save_bot(self, bot: BotDefinitionRecord) -> Dict[str, Any]:
        return self._upsert_payload_record(
            "bots",
            record_id=bot.id,
            name=bot.name,
            status=bot.status,
            payload=bot.model_dump(mode="json"),
        )

    def save_run(self, run: RunRecord) -> Dict[str, Any]:
        now = utcnow_iso()
        payload = run.model_dump(mode="json")
        summary = payload.pop("summary", {})
        with self._lock, self._connect() as conn:
            existing = conn.execute("SELECT created_at FROM runs WHERE id = ?", (run.id,)).fetchone()
            created_at = existing["created_at"] if existing else now
            conn.execute(
                """
                INSERT INTO runs (
                    id, name, status, scenario_id, dataset_id, experiment_id, agent_population_id,
                    seed, payload_json, summary_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    status = excluded.status,
                    scenario_id = excluded.scenario_id,
                    dataset_id = excluded.dataset_id,
                    experiment_id = excluded.experiment_id,
                    agent_population_id = excluded.agent_population_id,
                    seed = excluded.seed,
                    payload_json = excluded.payload_json,
                    summary_json = excluded.summary_json,
                    updated_at = excluded.updated_at
                """,
                (
                    run.id,
                    run.name,
                    run.status,
                    run.scenario_id,
                    run.dataset_id,
                    run.experiment_id,
                    run.agent_population_id,
                    run.seed,
                    self._serialize(payload),
                    self._serialize(summary),
                    created_at,
                    now,
                ),
            )
        return self.get_record("runs", run.id) or {}

    def update_run(self, run_id: str, *, status: Optional[str] = None, summary: Optional[Dict[str, Any]] = None, config_snapshot: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        record = self.get_record("runs", run_id)
        if not record:
            return None
        if status is not None:
            record["status"] = status
        if summary is not None:
            record["summary"] = summary
        if config_snapshot is not None:
            record["config_snapshot"] = config_snapshot
        run = RunRecord(**record)
        return self.save_run(run)

    def create_run(self, **kwargs: Any) -> Dict[str, Any]:
        run = RunRecord(**kwargs)
        return self.save_run(run)

    def append_run_event(self, event: RunEventRecord) -> Dict[str, Any]:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO run_events (run_id, sequence, event_type, phase, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.run_id,
                    event.sequence,
                    event.event_type,
                    event.phase,
                    self._serialize(event.payload),
                    event.created_at.isoformat(),
                ),
            )
        return event.model_dump(mode="json")

    def next_event_sequence(self, run_id: str) -> int:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(sequence), 0) AS max_sequence FROM run_events WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return int(row["max_sequence"]) + 1

    def list_run_events(self, run_id: str, after_sequence: int = 0) -> list[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT run_id, sequence, event_type, phase, payload_json, created_at
                FROM run_events
                WHERE run_id = ? AND sequence > ?
                ORDER BY sequence ASC
                """,
                (run_id, after_sequence),
            ).fetchall()
        return [self._row_to_record("run_events", row) for row in rows]

    def save_evaluation(self, evaluation: EvaluationReportRecord) -> Dict[str, Any]:
        now = utcnow_iso()
        payload = evaluation.model_dump(mode="json")
        with self._lock, self._connect() as conn:
            existing = conn.execute("SELECT created_at FROM evaluations WHERE id = ?", (evaluation.id,)).fetchone()
            created_at = existing["created_at"] if existing else now
            conn.execute(
                """
                INSERT INTO evaluations (
                    id, name, status, bot_id, experiment_id, scenario_id, dataset_id, payload_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    status = excluded.status,
                    bot_id = excluded.bot_id,
                    experiment_id = excluded.experiment_id,
                    scenario_id = excluded.scenario_id,
                    dataset_id = excluded.dataset_id,
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (
                    evaluation.id,
                    evaluation.name,
                    evaluation.status,
                    evaluation.bot_id,
                    evaluation.experiment_id,
                    evaluation.scenario_id,
                    evaluation.dataset_id,
                    self._serialize(payload),
                    created_at,
                    now,
                ),
            )
        return self.get_record("evaluations", evaluation.id) or {}

    def save_job(self, job: BackgroundJobRecord) -> Dict[str, Any]:
        now = utcnow_iso()
        payload = job.model_dump(mode="json")
        result = payload.pop("result", {})
        with self._lock, self._connect() as conn:
            existing = conn.execute("SELECT created_at FROM jobs WHERE id = ?", (job.id,)).fetchone()
            created_at = existing["created_at"] if existing else now
            conn.execute(
                """
                INSERT INTO jobs (id, job_type, status, payload_json, result_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    job_type = excluded.job_type,
                    status = excluded.status,
                    payload_json = excluded.payload_json,
                    result_json = excluded.result_json,
                    updated_at = excluded.updated_at
                """,
                (job.id, job.job_type, job.status, self._serialize(payload), self._serialize(result), created_at, now),
            )
        return self.get_record("jobs", job.id) or {}

    def get_purge_preview(self, active_run_id: Optional[str]) -> Dict[str, Any]:
        with self._lock, self._connect() as conn:
            # We want to identify runs that are NOT the active run
            # And count how many run_events and agent_notebooks belong to them
            if active_run_id:
                events_count = conn.execute("SELECT COUNT(*) FROM run_events WHERE run_id != ?", (active_run_id,)).fetchone()[0]
                notebooks_count = conn.execute("SELECT COUNT(*) FROM agent_notebooks WHERE run_id != ?", (active_run_id,)).fetchone()[0]
                runs_affected = [row[0] for row in conn.execute("SELECT DISTINCT id FROM runs WHERE id != ?", (active_run_id,)).fetchall()]
            else:
                events_count = conn.execute("SELECT COUNT(*) FROM run_events").fetchone()[0]
                notebooks_count = conn.execute("SELECT COUNT(*) FROM agent_notebooks").fetchone()[0]
                runs_affected = [row[0] for row in conn.execute("SELECT id FROM runs").fetchall()]
                
        return {
            "events_count": events_count,
            "notebooks_count": notebooks_count,
            "runs_affected_count": len(runs_affected),
            "runs_affected": runs_affected
        }

    def execute_purge(self, active_run_id: Optional[str]) -> Dict[str, Any]:
        preview = self.get_purge_preview(active_run_id)
        if not preview["runs_affected"]:
            return {"status": "ok", "purged_events": 0, "purged_notebooks": 0, "purged_runs": 0}
            
        with self._lock, self._connect() as conn:
            if active_run_id:
                conn.execute("DELETE FROM run_events WHERE run_id != ?", (active_run_id,))
                conn.execute("DELETE FROM agent_notebooks WHERE run_id != ?", (active_run_id,))
                conn.execute("DELETE FROM runs WHERE id != ?", (active_run_id,))
            else:
                conn.execute("DELETE FROM run_events")
                conn.execute("DELETE FROM agent_notebooks")
                conn.execute("DELETE FROM runs")
                
        return {
            "status": "ok", 
            "purged_events": preview["events_count"], 
            "purged_notebooks": preview["notebooks_count"], 
            "purged_runs": preview["runs_affected_count"]
        }

    def update_job(self, job_id: str, *, status: Optional[str] = None, result: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        record = self.get_record("jobs", job_id)
        if not record:
            return None
        record["status"] = status or record["status"]
        record["result"] = result or record.get("result", {})
        job = BackgroundJobRecord(**record)
        return self.save_job(job)

    def create_job(self, job_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        job = BackgroundJobRecord(id=str(uuid.uuid4()), job_type=job_type, payload=payload)
        return self.save_job(job)
