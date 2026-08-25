"""Execution engine for ModelGuard behavior tests."""

from __future__ import annotations

from typing import Sequence

import numpy as np

from ..adapters.base import PredictionAdapter
from ..core.contracts import Dataset, RunReport, TestDefinition, TestKind, TestResult
from ..drift.metrics import population_stability_index
from ..metrics.prediction import agreement, mean_absolute_delta, prediction_variance
from ..perturbation.tabular import add_delta, replace_feature


class BehaviorTestEngine:
    """Runs deterministic behavioral checks against a normalized model adapter."""

    def __init__(self, adapter: PredictionAdapter) -> None:
        self.adapter = adapter

    def run_suite(self, definitions: Sequence[TestDefinition], dataset: Dataset, *, reference_dataset: Dataset | None = None, comparison_adapter: PredictionAdapter | None = None) -> RunReport:
        return RunReport(
            model_name=self.adapter.model_name,
            results=[self.run_test(test, dataset, reference_dataset=reference_dataset, comparison_adapter=comparison_adapter) for test in definitions],
        )

    def run_test(self, definition: TestDefinition, dataset: Dataset, *, reference_dataset: Dataset | None = None, comparison_adapter: PredictionAdapter | None = None) -> TestResult:
        handlers = {
            TestKind.INPUT_PERTURBATION: self._input_perturbation,
            TestKind.BOUNDARY: self._boundary,
            TestKind.DISTRIBUTION_SHIFT: self._distribution_shift,
            TestKind.FEATURE_SENSITIVITY: self._feature_sensitivity,
            TestKind.PREDICTION_CONSISTENCY: self._prediction_consistency,
            TestKind.OUTLIER: self._outlier,
            TestKind.DATA_LEAKAGE: self._data_leakage,
            TestKind.MODEL_REGRESSION: self._model_regression,
            TestKind.MODEL_COMPARISON: self._model_comparison,
        }
        try:
            return handlers[definition.kind](definition, dataset, reference_dataset, comparison_adapter)
        except (KeyError, ValueError, TypeError) as error:
            return self._result(definition, "failed", "execution_error", float("nan"), "n/a", {"error": str(error)}, f"Test could not run: {error}")

    @staticmethod
    def _result(definition: TestDefinition, status: str, metric_name: str, metric_value: float, comparison: str, evidence: dict[str, object], message: str) -> TestResult:
        return TestResult(definition.id, definition.name, definition.kind, status, metric_name, float(metric_value), definition.threshold, comparison, evidence, message)

    @staticmethod
    def _feature_index(definition: TestDefinition, dataset: Dataset) -> int:
        return int(definition.parameters["feature_index"]) if "feature_index" in definition.parameters else dataset.feature_index(str(definition.parameters["feature"]))

    def _input_perturbation(self, definition: TestDefinition, dataset: Dataset, *_: object) -> TestResult:
        index, delta = self._feature_index(definition, dataset), float(definition.parameters.get("delta", 1.0))
        original, perturbed = self.adapter.predict_scores(dataset.values), self.adapter.predict_scores(add_delta(dataset.values, index, delta))
        shift = mean_absolute_delta(original, perturbed)
        passed = shift <= definition.threshold
        return self._result(definition, "passed" if passed else "failed", "mean_prediction_delta", shift, "<=", {"feature": dataset.feature_names[index], "perturbation_delta": delta, "sample_size": len(original)}, "Prediction remained stable after perturbation." if passed else "Prediction changed more than the allowed perturbation threshold.")

    def _boundary(self, definition: TestDefinition, dataset: Dataset, *_: object) -> TestResult:
        index, values = self._feature_index(definition, dataset), definition.parameters.get("values", [])
        if not isinstance(values, list) or not values:
            raise ValueError("Boundary tests require a non-empty 'values' list.")
        baseline, deltas, all_finite = self.adapter.predict_scores(dataset.values), [], True
        for value in values:
            prediction = self.adapter.predict_scores(replace_feature(dataset.values, index, float(value)))
            all_finite, deltas = all_finite and bool(np.all(np.isfinite(prediction))), [*deltas, mean_absolute_delta(baseline, prediction)]
        maximum, passed = max(deltas), all_finite and max(deltas) <= definition.threshold
        return self._result(definition, "passed" if passed else "failed", "max_boundary_prediction_delta", maximum, "<=", {"feature": dataset.feature_names[index], "boundary_values": values, "finite_predictions": all_finite}, "Boundary predictions are finite and within tolerance." if passed else "A boundary case produced an unstable or non-finite prediction.")

    def _distribution_shift(self, definition: TestDefinition, dataset: Dataset, reference_dataset: Dataset | None, *_: object) -> TestResult:
        if reference_dataset is None:
            raise ValueError("Distribution-shift tests require a reference_dataset.")
        if reference_dataset.values.shape[1] != dataset.values.shape[1]:
            raise ValueError("Reference and candidate datasets must have matching feature columns.")
        per_feature = [population_stability_index(reference_dataset.values[:, column], dataset.values[:, column]) for column in range(dataset.values.shape[1])]
        score, passed = float(np.mean(per_feature)), float(np.mean(per_feature)) <= definition.threshold
        return self._result(definition, "passed" if passed else "failed", "mean_population_stability_index", score, "<=", {"per_feature_psi": dict(zip(dataset.feature_names, per_feature)), "reference_dataset": reference_dataset.name}, "Observed feature distributions remain within the shift threshold." if passed else "Input distribution drift exceeds the allowed threshold.")

    def _feature_sensitivity(self, definition: TestDefinition, dataset: Dataset, *_: object) -> TestResult:
        index, delta = self._feature_index(definition, dataset), float(definition.parameters.get("delta", 1.0))
        baseline, changed = self.adapter.predict_scores(dataset.values), self.adapter.predict_scores(add_delta(dataset.values, index, delta))
        score = mean_absolute_delta(baseline, changed) / max(abs(delta), 1e-9)
        passed = score <= definition.threshold
        return self._result(definition, "passed" if passed else "failed", "prediction_sensitivity_per_unit", score, "<=", {"feature": dataset.feature_names[index], "feature_delta": delta}, "Feature sensitivity is within the expected bound." if passed else "Feature sensitivity is higher than the expected bound.")

    def _prediction_consistency(self, definition: TestDefinition, dataset: Dataset, *_: object) -> TestResult:
        repeats = int(definition.parameters.get("repeats", 3))
        if repeats < 2:
            raise ValueError("Consistency tests require at least two repeats.")
        score = prediction_variance(np.vstack([self.adapter.predict_scores(dataset.values) for _ in range(repeats)]))
        passed = score <= definition.threshold
        return self._result(definition, "passed" if passed else "failed", "mean_repeat_prediction_variance", score, "<=", {"repeats": repeats, "sample_size": dataset.values.shape[0]}, "Repeated inference is consistent." if passed else "Repeated inference is not sufficiently consistent.")

    def _outlier(self, definition: TestDefinition, dataset: Dataset, *_: object) -> TestResult:
        z_limit = float(definition.parameters.get("z_limit", 3.0))
        means, stds = dataset.values.mean(axis=0), np.where(dataset.values.std(axis=0) == 0, 1.0, dataset.values.std(axis=0))
        mask = np.any(np.abs((dataset.values - means) / stds) >= z_limit, axis=1)
        outputs = self.adapter.predict_scores(dataset.values[mask]) if mask.any() else np.array([])
        score = 0.0 if len(outputs) == 0 else float(np.mean(~np.isfinite(outputs)))
        passed = score <= definition.threshold
        return self._result(definition, "passed" if passed else "failed", "invalid_prediction_rate_on_outliers", score, "<=", {"outlier_rows": int(mask.sum()), "z_limit": z_limit}, "Outlier predictions are numerically valid." if passed else "Outlier inputs produced invalid predictions.")

    def _data_leakage(self, definition: TestDefinition, dataset: Dataset, *_: object) -> TestResult:
        if dataset.labels is None:
            raise ValueError("Data-leakage tests require dataset labels.")
        labels = np.asarray(dataset.labels, dtype=float)
        correlations = [0.0 if np.std(dataset.values[:, column]) == 0 or np.std(labels) == 0 else float(abs(np.corrcoef(dataset.values[:, column], labels)[0, 1])) for column in range(dataset.values.shape[1])]
        score, feature = max(correlations), dataset.feature_names[int(np.argmax(correlations))]
        passed = score <= definition.threshold
        return self._result(definition, "passed" if passed else "failed", "max_feature_label_correlation", score, "<=", {"suspected_feature": feature, "feature_correlations": dict(zip(dataset.feature_names, correlations))}, "No feature exceeds the configured leakage-correlation threshold." if passed else "A feature has suspiciously high correlation with the label.")

    def _model_regression(self, definition: TestDefinition, dataset: Dataset, _reference: Dataset | None, comparison_adapter: PredictionAdapter | None) -> TestResult:
        if comparison_adapter is None:
            raise ValueError("Model-regression tests require a baseline comparison_adapter.")
        score = agreement(comparison_adapter.predict(dataset.values), self.adapter.predict(dataset.values))
        passed = score >= definition.threshold
        return self._result(definition, "passed" if passed else "failed", "baseline_prediction_agreement", score, ">=", {"baseline_model": comparison_adapter.model_name, "candidate_model": self.adapter.model_name}, "Candidate behavior matches the approved baseline." if passed else "Candidate behavior regressed against the approved baseline.")

    def _model_comparison(self, definition: TestDefinition, dataset: Dataset, _reference: Dataset | None, comparison_adapter: PredictionAdapter | None) -> TestResult:
        if comparison_adapter is None:
            raise ValueError("Model-comparison tests require a comparison_adapter.")
        score = agreement(comparison_adapter.predict(dataset.values), self.adapter.predict(dataset.values))
        passed = score >= definition.threshold
        return self._result(definition, "passed" if passed else "failed", "model_prediction_agreement", score, ">=", {"comparison_model": comparison_adapter.model_name, "candidate_model": self.adapter.model_name}, "Models meet the configured agreement threshold." if passed else "Models disagree more than the configured agreement threshold.")
