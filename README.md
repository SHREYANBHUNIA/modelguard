# ModelGuard

ModelGuard is a full-stack behavior-testing platform for machine-learning models. It turns expectations such as “a prediction should remain stable when an irrelevant feature changes” into versioned test definitions, structured evidence, aggregate reports, comparisons, and shareable links.

## Framework package

The Python package is organized around `core`, `test_engine`, `perturbation`, `drift`, `metrics`, `adapters`, `api`, `dashboard`, and `examples`. The test engine provides input perturbation, boundary, distribution-shift, feature-sensitivity, prediction-consistency, outlier, data-leakage, model-regression, and model-comparison checks. `SklearnAdapter` and `PyTorchAdapter` expose the same prediction contract, while any custom model can implement `PredictionAdapter`.

The stable-prediction example below changes an irrelevant feature while requiring the mean prediction delta to remain below its tolerance.

```bash
pip install -e '.[dev]'
python -m modelguard.examples.sklearn_stable_prediction
pytest -q
```

To run the optional PyTorch example, install `pip install -e '.[pytorch]'` first.

## FastAPI service and PostgreSQL

The FastAPI service lets developers create configurations, start test runs, retrieve structured reports, compare two reports, and retrieve a report using its generated share token. It persists configurations in `model_test_configurations`, executions in `model_test_runs`, and concise shareable summaries in `model_test_report_summaries`.

```bash
docker compose up --build
```

The complete stack is then available at `http://localhost:3000`; the API remains available at `http://localhost:8000`, with interactive OpenAPI documentation at `/docs`. Compose starts PostgreSQL, FastAPI, and the React/tRPC web application, passing `MODEL_GUARD_API_URL=http://api:8000` to the web service. A configuration persists an `adapter_type`, optional `artifact_ref`, model specification, optional baseline specification, and test definitions. The API executes `linear_score`, `sklearn`, and `pytorch` adapter configurations. For scikit-learn, use an operator-approved `.joblib` artifact; for PyTorch, use a trusted TorchScript `.pt` or `.torchscript` artifact. Artifacts must be placed below `MODEL_GUARD_MODEL_DIR`; API clients cannot request arbitrary filesystem locations. Because deserializing a model artifact can execute code, only platform operators should provision trusted scikit-learn artifacts.

For local web development without containers, run `pnpm dev` in one terminal. Start the Python service in a second terminal with `uvicorn modelguard.api.main:app --reload --port 8000`, then launch the web app with `MODELGUARD_API_URL=http://127.0.0.1:8000 pnpm dev`. The default database is local SQLite; use `MODEL_GUARD_DATABASE_URL=postgresql+psycopg://modelguard:modelguard_dev_password@127.0.0.1:5432/modelguard` when PostgreSQL is running through Compose.

### Minimal API workflow

Create a suite, run it, then retrieve its report. The API accepts a `linear_score` configuration for a quick end-to-end smoke test; real deployments should use a persisted `sklearn` or `pytorch` artifact reference.

```bash
curl -X POST http://localhost:8000/configurations \
  -H 'content-type: application/json' \
  -d '{
    "name": "Eligibility stability",
    "model_name": "credit-risk-v3",
    "adapter_type": "linear_score",
    "model_spec": {"weights": [0.06, 0.00002, 0.0], "bias": -4.0},
    "tests": [{
      "name": "Irrelevant color stability",
      "kind": "input_perturbation",
      "threshold": 0.03,
      "parameters": {"feature": "irrelevant_color_code", "delta": 4.0}
    }]
  }'

curl -X POST http://localhost:8000/configurations/<configuration-id>/runs \
  -H 'content-type: application/json' -d '{}'

curl http://localhost:8000/reports
```

The resulting report contains aggregate status, per-test thresholds, observed metrics, evidence, optional baseline context, and a `share_token` available from `GET /reports/share/{share_token}`. To compare two saved reports, request `GET /reports/compare/{left_report_id}/{right_report_id}`.

## Deploying from GitHub

The repository contains three deployable concerns: the React/tRPC web application, the FastAPI behavior-testing service, and PostgreSQL. Deploy the web service from the project root with the build command `pnpm install && pnpm build` and start command `node dist/index.js`. Set `MODELGUARD_API_URL` on the web service to the publicly reachable FastAPI base URL, for example `https://api.example.com`.

Deploy the FastAPI service using `docker/api.Dockerfile` or the command `uvicorn modelguard.api.main:app --host 0.0.0.0 --port $PORT`. Set `MODEL_GUARD_DATABASE_URL` to a managed PostgreSQL connection string in SQLAlchemy format, such as `postgresql+psycopg://USER:PASSWORD@HOST:5432/modelguard`. The API service must be able to reach that database, and the web service must be able to reach the API service. Do not expose database credentials or model artifact paths in browser variables.

For model-backed test execution, provision trusted artifacts in the server-controlled `MODEL_GUARD_MODEL_DIR`. Scikit-learn adapters accept approved `.joblib` files; PyTorch adapters accept trusted TorchScript `.pt` or `.torchscript` files. The development `compose.yaml` runs all three services together and is the reference for GitHub-connected deployment environments.

## Dashboard

The React dashboard in `client/` provides the interactive control room for launching suites, inspecting evidence, comparing outcomes, and sharing reports. Its default preview uses the same structured report shape as the API so the UI remains usable in the managed development environment; Docker provides the portable FastAPI and PostgreSQL service configuration for full local-stack integration.
