"""HTTP API for defining, running, comparing, and sharing ModelGuard reports."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from modelguard import BehaviorTestEngine, Dataset, TestDefinition, TestKind
from modelguard.adapters.base import PredictionAdapter

from .database import ReportSummary, TestConfiguration, TestRun, create_schema, session_scope


class DatasetRequest(BaseModel):
    values: list[list[float]]
    feature_names: list[str]
    labels: list[float] | None = None
    name: str = "run-dataset"

    def to_dataset(self) -> Dataset:
        return Dataset(np.asarray(self.values, dtype=float), self.feature_names, None if self.labels is None else np.asarray(self.labels), self.name)


class TestDefinitionRequest(BaseModel):
    name: str
    kind: TestKind
    threshold: float
    parameters: dict[str, Any] = Field(default_factory=dict)
    description: str = ""


class ConfigurationRequest(BaseModel):
    name: str
    model_name: str
    model_spec: dict[str, Any] = Field(default_factory=dict)
    adapter_type: str = "linear_score"
    artifact_ref: str | None = None
    baseline_model_spec: dict[str, Any] | None = None
    tests: list[TestDefinitionRequest]


class RunRequest(BaseModel):
    dataset: DatasetRequest | None = None
    reference_dataset: DatasetRequest | None = None
    baseline_model_spec: dict[str, Any] | None = None


class LinearScoreAdapter(PredictionAdapter):
    """Small deterministic tabular adapter useful for quick API smoke tests."""

    def __init__(self, model_name: str, model_spec: dict[str, Any]) -> None:
        super().__init__(model_name)
        self.weights = np.asarray(model_spec.get("weights", [0.06, 0.00002, 0.0]), dtype=float)
        self.bias = float(model_spec.get("bias", -4.0))

    def predict_scores(self, values: np.ndarray) -> np.ndarray:
        logits = np.asarray(values, dtype=float) @ self.weights + self.bias
        return 1 / (1 + np.exp(-np.clip(logits, -500, 500)))

    def predict(self, values: np.ndarray) -> np.ndarray:
        return (self.predict_scores(values) >= 0.5).astype(int)


def default_dataset() -> Dataset:
    return Dataset(
        values=np.asarray([[25.0, 58_000.0, 0.0], [42.0, 95_000.0, 1.0], [30.0, 72_000.0, -1.0], [55.0, 120_000.0, 0.5]]),
        feature_names=["age", "income", "irrelevant_color_code"],
        labels=np.asarray([0, 1, 0, 1]),
        name="modelguard-reference-sample",
    )


def trusted_artifact_path(artifact_ref: str) -> Path:
    """Resolve server-provisioned model artifacts without accepting arbitrary filesystem paths."""
    root = Path(__import__("os").environ.get("MODEL_GUARD_MODEL_DIR", "./models")).resolve()
    candidate = (root / artifact_ref).resolve()
    if root not in candidate.parents or not candidate.is_file():
        raise ValueError("Model artifact must be an approved file within MODEL_GUARD_MODEL_DIR.")
    return candidate


def adapter_from_spec(model_name: str, adapter_type: str, artifact_ref: str | None, model_spec: dict[str, Any]) -> PredictionAdapter:
    """Create a framework adapter from persisted, operator-approved configuration metadata."""
    if adapter_type == "linear_score":
        return LinearScoreAdapter(model_name, model_spec)
    if not artifact_ref:
        raise ValueError(f"The '{adapter_type}' adapter requires an approved artifact_ref.")
    artifact = trusted_artifact_path(artifact_ref)
    if adapter_type == "sklearn":
        if artifact.suffix != ".joblib":
            raise ValueError("Scikit-learn artifacts must use the .joblib extension.")
        import joblib

        from modelguard.adapters import SklearnAdapter

        return SklearnAdapter(joblib.load(artifact), model_name)
    if adapter_type == "pytorch":
        if artifact.suffix not in {".pt", ".torchscript"}:
            raise ValueError("PyTorch artifacts must be trusted TorchScript .pt or .torchscript files.")
        import torch

        from modelguard.adapters import PyTorchAdapter

        return PyTorchAdapter(torch.jit.load(str(artifact), map_location="cpu"), model_name)
    raise ValueError("adapter_type must be one of: linear_score, sklearn, pytorch.")


@asynccontextmanager
async def lifecycle(_: FastAPI):
    create_schema()
    yield


app = FastAPI(title="ModelGuard API", version="0.1.0", lifespan=lifecycle)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/test-kinds")
def list_test_kinds() -> list[str]:
    return [kind.value for kind in TestKind]


@app.post("/configurations", status_code=201)
def create_configuration(payload: ConfigurationRequest, db: Session = Depends(session_scope)) -> dict[str, Any]:
    configuration = TestConfiguration(
        name=payload.name,
        model_name=payload.model_name,
        adapter_type=payload.adapter_type,
        artifact_ref=payload.artifact_ref,
        model_spec=payload.model_spec,
        baseline_model_spec=payload.baseline_model_spec,
        test_definitions=[test.model_dump(mode="json") for test in payload.tests],
    )
    db.add(configuration)
    db.commit()
    db.refresh(configuration)
    return serialize_configuration(configuration)


@app.get("/configurations")
def list_configurations(db: Session = Depends(session_scope)) -> list[dict[str, Any]]:
    return [serialize_configuration(item) for item in db.query(TestConfiguration).order_by(TestConfiguration.created_at.desc()).all()]


@app.get("/configurations/{configuration_id}")
def get_configuration(configuration_id: str, db: Session = Depends(session_scope)) -> dict[str, Any]:
    return serialize_configuration(require_configuration(db, configuration_id))


@app.post("/configurations/{configuration_id}/runs", status_code=201)
def run_configuration(configuration_id: str, payload: RunRequest, db: Session = Depends(session_scope)) -> dict[str, Any]:
    configuration = require_configuration(db, configuration_id)
    dataset = payload.dataset.to_dataset() if payload.dataset else default_dataset()
    reference = payload.reference_dataset.to_dataset() if payload.reference_dataset else None
    baseline_spec = payload.baseline_model_spec or configuration.baseline_model_spec
    definitions = [TestDefinition.from_dict(test) for test in configuration.test_definitions]
    try:
        adapter = adapter_from_spec(configuration.model_name, configuration.adapter_type, configuration.artifact_ref, configuration.model_spec)
        baseline = None if baseline_spec is None else adapter_from_spec(
            f"{configuration.model_name}-baseline",
            str(baseline_spec.get("adapter_type", configuration.adapter_type)),
            baseline_spec.get("artifact_ref"),
            baseline_spec,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    report = BehaviorTestEngine(adapter).run_suite(definitions, dataset, reference_dataset=reference, comparison_adapter=baseline).to_dict()
    baseline_snapshot = None if baseline is None else {"model_name": baseline.model_name, "adapter_type": baseline_spec.get("adapter_type", configuration.adapter_type), "artifact_ref": baseline_spec.get("artifact_ref"), "model_spec": baseline_spec}
    report["baseline"] = baseline_snapshot
    run = TestRun(configuration_id=configuration.id, adapter_type=configuration.adapter_type, artifact_ref=configuration.artifact_ref, baseline_snapshot=baseline_snapshot, status=report["status"], report=report)
    db.add(run)
    db.flush()
    summary = ReportSummary(run_id=run.id, aggregate_status=report["status"], totals=report["summary"], baseline_snapshot=baseline_snapshot)
    db.add(summary)
    db.commit()
    db.refresh(run)
    db.refresh(summary)
    return {**serialize_run(run), "report_id": summary.id, "share_token": summary.share_token}


@app.get("/runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(session_scope)) -> dict[str, Any]:
    run = db.get(TestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Test run not found.")
    return serialize_run(run)


@app.get("/reports/{report_id}")
def get_report(report_id: str, db: Session = Depends(session_scope)) -> dict[str, Any]:
    report = db.get(ReportSummary, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    return serialize_report(report)


@app.get("/reports")
def list_reports(db: Session = Depends(session_scope)) -> list[dict[str, Any]]:
    reports = db.query(ReportSummary).order_by(ReportSummary.created_at.desc()).all()
    return [serialize_report(report) for report in reports]


@app.get("/reports/share/{share_token}")
def get_shared_report(share_token: str, db: Session = Depends(session_scope)) -> dict[str, Any]:
    report = db.query(ReportSummary).filter(ReportSummary.share_token == share_token).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Shared report not found.")
    return serialize_report(report)


@app.get("/reports/compare/{left_report_id}/{right_report_id}")
def compare_reports(left_report_id: str, right_report_id: str, db: Session = Depends(session_scope)) -> dict[str, Any]:
    left, right = db.get(ReportSummary, left_report_id), db.get(ReportSummary, right_report_id)
    if left is None or right is None:
        raise HTTPException(status_code=404, detail="One or both reports were not found.")
    left_results, right_results = left.run.report["results"], right.run.report["results"]
    counterpart = {item["test_id"]: item for item in right_results}
    comparisons = [{"test_id": item["test_id"], "test_name": item["test_name"], "left_status": item["status"], "right_status": counterpart.get(item["test_id"], {}).get("status", "missing"), "metric_delta": item["metric_value"] - counterpart.get(item["test_id"], {}).get("metric_value", 0)} for item in left_results]
    return {"left": serialize_report(left), "right": serialize_report(right), "comparisons": comparisons}


def require_configuration(db: Session, configuration_id: str) -> TestConfiguration:
    configuration = db.get(TestConfiguration, configuration_id)
    if configuration is None:
        raise HTTPException(status_code=404, detail="Test configuration not found.")
    return configuration


def serialize_configuration(configuration: TestConfiguration) -> dict[str, Any]:
    return {"id": configuration.id, "name": configuration.name, "model_name": configuration.model_name, "adapter_type": configuration.adapter_type, "artifact_ref": configuration.artifact_ref, "model_spec": configuration.model_spec, "baseline_model_spec": configuration.baseline_model_spec, "tests": configuration.test_definitions, "created_at": configuration.created_at.isoformat(), "updated_at": configuration.updated_at.isoformat()}


def serialize_run(run: TestRun) -> dict[str, Any]:
    return {"id": run.id, "configuration_id": run.configuration_id, "adapter_type": run.adapter_type, "artifact_ref": run.artifact_ref, "baseline": run.baseline_snapshot, "status": run.status, "created_at": run.created_at.isoformat(), "report": run.report}


def serialize_report(report: ReportSummary) -> dict[str, Any]:
    return {"id": report.id, "run_id": report.run_id, "share_token": report.share_token, "status": report.aggregate_status, "summary": report.totals, "baseline": report.baseline_snapshot, "created_at": report.created_at.isoformat(), "report": report.run.report}
