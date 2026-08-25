from pathlib import Path

import joblib
import numpy as np
from fastapi.testclient import TestClient
from sklearn.dummy import DummyClassifier

from modelguard.api.database import Base, engine
from modelguard.api.main import app


def test_api_runs_and_shares_structured_report() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as client:
        configuration = client.post(
            "/configurations",
            json={
                "name": "Eligibility behavior suite",
                "model_name": "eligibility-linear",
                "adapter_type": "linear_score",
                "model_spec": {"weights": [0.06, 0.00002, 0.0], "bias": -4.0},
                "baseline_model_spec": {"adapter_type": "linear_score", "weights": [0.06, 0.00002, 0.0], "bias": -4.0},
                "tests": [
                    {
                        "name": "Irrelevant color-code stability",
                        "kind": "input_perturbation",
                        "threshold": 0.001,
                        "parameters": {"feature": "irrelevant_color_code", "delta": 8.0},
                    },
                    {
                        "name": "Repeatable inference",
                        "kind": "prediction_consistency",
                        "threshold": 0.0,
                        "parameters": {"repeats": 3},
                    },
                    {
                        "name": "Baseline agreement",
                        "kind": "model_regression",
                        "threshold": 1.0,
                    },
                ],
            },
        )
        assert configuration.status_code == 201
        configuration_id = configuration.json()["id"]

        run = client.post(f"/configurations/{configuration_id}/runs", json={})
        assert run.status_code == 201
        payload = run.json()
        assert payload["status"] == "passed"
        assert payload["report"]["summary"] == {"total": 3, "passed": 3, "failed": 0}
        assert payload["report"]["baseline"]["adapter_type"] == "linear_score"
        assert payload["baseline"]["model_spec"]["bias"] == -4.0

        report = client.get(f"/reports/{payload['report_id']}")
        shared = client.get(f"/reports/share/{payload['share_token']}")
        compared = client.get(f"/reports/compare/{payload['report_id']}/{payload['report_id']}")
        listed = client.get("/reports")
        assert report.status_code == shared.status_code == compared.status_code == 200
        assert listed.status_code == 200
        assert listed.json()[0]["id"] == payload["report_id"]
        assert shared.json()["report"]["results"][0]["evidence"]["feature"] == "irrelevant_color_code"
        assert len(compared.json()["comparisons"]) == 3


def test_api_executes_trusted_sklearn_artifact_and_rejects_bad_baseline() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    artifact_dir = Path("models")
    artifact_dir.mkdir(exist_ok=True)
    artifact_path = artifact_dir / "api-test-model.joblib"
    model = DummyClassifier(strategy="constant", constant=1).fit(np.asarray([[1.0, 1.0, 1.0], [2.0, 2.0, 2.0]]), np.asarray([1, 1]))
    joblib.dump(model, artifact_path)

    try:
        with TestClient(app) as client:
            configuration = client.post(
                "/configurations",
                json={
                    "name": "Trusted sklearn suite",
                    "model_name": "constant-sklearn",
                    "adapter_type": "sklearn",
                    "artifact_ref": artifact_path.name,
                    "tests": [{"name": "Stable irrelevant feature", "kind": "input_perturbation", "threshold": 0.0, "parameters": {"feature": "irrelevant_color_code", "delta": 5.0}}],
                },
            )
            assert configuration.status_code == 201
            run = client.post(f"/configurations/{configuration.json()['id']}/runs", json={})
            assert run.status_code == 201
            assert run.json()["adapter_type"] == "sklearn"
            assert run.json()["artifact_ref"] == artifact_path.name

            bad_baseline = client.post(f"/configurations/{configuration.json()['id']}/runs", json={"baseline_model_spec": {"adapter_type": "sklearn", "artifact_ref": "not-approved.joblib"}})
            assert bad_baseline.status_code == 422
    finally:
        artifact_path.unlink(missing_ok=True)
