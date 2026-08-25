"""Shared contracts for defining and reporting model behavior tests."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence
from uuid import uuid4

import numpy as np


class TestKind(str, Enum):
    __test__ = False
    INPUT_PERTURBATION = "input_perturbation"
    BOUNDARY = "boundary"
    DISTRIBUTION_SHIFT = "distribution_shift"
    FEATURE_SENSITIVITY = "feature_sensitivity"
    PREDICTION_CONSISTENCY = "prediction_consistency"
    OUTLIER = "outlier"
    DATA_LEAKAGE = "data_leakage"
    MODEL_REGRESSION = "model_regression"
    MODEL_COMPARISON = "model_comparison"


@dataclass(frozen=True)
class Dataset:
    """Tabular model input with a stable feature-name to column-index mapping."""

    values: np.ndarray
    feature_names: Sequence[str]
    labels: np.ndarray | None = None
    name: str = "dataset"

    def __post_init__(self) -> None:
        values = np.asarray(self.values, dtype=float)
        if values.ndim != 2:
            raise ValueError("Dataset values must be a two-dimensional array.")
        if values.shape[1] != len(self.feature_names):
            raise ValueError("The number of feature names must match the input columns.")
        if self.labels is not None and len(self.labels) != len(values):
            raise ValueError("Labels must contain one value for every input row.")
        object.__setattr__(self, "values", values)
        if self.labels is not None:
            object.__setattr__(self, "labels", np.asarray(self.labels))

    def feature_index(self, name: str) -> int:
        try:
            return list(self.feature_names).index(name)
        except ValueError as error:
            raise KeyError(f"Unknown feature '{name}'.") from error


@dataclass(frozen=True)
class TestDefinition:
    __test__ = False
    """A serializable behavior-test definition."""

    name: str
    kind: TestKind
    threshold: float
    parameters: Mapping[str, Any] = field(default_factory=dict)
    description: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TestDefinition":
        return cls(
            id=str(payload.get("id") or uuid4()),
            name=str(payload["name"]),
            kind=TestKind(payload["kind"]),
            threshold=float(payload["threshold"]),
            parameters=dict(payload.get("parameters", {})),
            description=str(payload.get("description", "")),
        )


@dataclass(frozen=True)
class TestResult:
    test_id: str
    test_name: str
    kind: TestKind
    status: str
    metric_name: str
    metric_value: float
    threshold: float
    comparison: str
    evidence: Mapping[str, Any]
    message: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["kind"] = self.kind.value
        return payload


@dataclass(frozen=True)
class RunReport:
    model_name: str
    results: Sequence[TestResult]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    report_id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def status(self) -> str:
        return "passed" if all(result.status == "passed" for result in self.results) else "failed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "model_name": self.model_name,
            "created_at": self.created_at,
            "status": self.status,
            "summary": {"total": len(self.results), "passed": sum(result.status == "passed" for result in self.results), "failed": sum(result.status == "failed" for result in self.results)},
            "results": [result.to_dict() for result in self.results],
        }
