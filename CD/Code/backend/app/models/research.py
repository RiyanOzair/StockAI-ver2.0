from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CalibrationProfile(BaseModel):
    version: str = "calibration-us-cash-v1"
    reference_mode: str = "embedded_priors"
    volatility_bands: Dict[str, float] = Field(default_factory=dict)
    spread_bps: Dict[str, float] = Field(default_factory=dict)
    average_daily_volume_millions: Dict[str, float] = Field(default_factory=dict)
    sector_correlation: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    event_frequency: float = 1.0
    regime_transition_bias: Dict[str, float] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)


class DatasetVersionRecord(BaseModel):
    id: str
    name: str
    version: str
    universe_id: str
    description: str
    calibration: CalibrationProfile
    metadata: Dict[str, Any] = Field(default_factory=dict)
    status: str = "ready"
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ScenarioRecord(BaseModel):
    id: str
    name: str
    version: str
    description: str
    regime_overrides: Dict[str, Any] = Field(default_factory=dict)
    shock_profile: Dict[str, Any] = Field(default_factory=dict)
    config_overrides: Dict[str, Any] = Field(default_factory=dict)
    status: str = "ready"
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ExperimentRecord(BaseModel):
    id: str
    name: str
    description: str
    scenario_id: str
    dataset_id: str
    agent_population_id: Optional[str] = None
    status: str = "draft"
    config_snapshot: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class BotDefinitionRecord(BaseModel):
    id: str
    name: str
    bot_type: str
    strategy_id: Optional[str] = None
    module_path: Optional[str] = None
    class_name: Optional[str] = None
    description: str = ""
    config: Dict[str, Any] = Field(default_factory=dict)
    status: str = "ready"
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class AgentPopulationRecord(BaseModel):
    id: str
    name: str
    description: str = ""
    composition: Dict[str, Any] = Field(default_factory=dict)
    status: str = "ready"
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class RunRecord(BaseModel):
    id: str
    name: str
    experiment_id: Optional[str] = None
    scenario_id: Optional[str] = None
    dataset_id: Optional[str] = None
    agent_population_id: Optional[str] = None
    seed: Optional[int] = None
    status: str = "configured"
    config_snapshot: Dict[str, Any] = Field(default_factory=dict)
    summary: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class RunEventRecord(BaseModel):
    run_id: str
    sequence: int
    event_type: str
    phase: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)


class EvaluationReportRecord(BaseModel):
    id: str
    name: str
    bot_id: str
    experiment_id: Optional[str] = None
    scenario_id: Optional[str] = None
    dataset_id: Optional[str] = None
    status: str = "queued"
    metrics: Dict[str, Any] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class BackgroundJobRecord(BaseModel):
    id: str
    job_type: str
    status: str = "queued"
    payload: Dict[str, Any] = Field(default_factory=dict)
    result: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
