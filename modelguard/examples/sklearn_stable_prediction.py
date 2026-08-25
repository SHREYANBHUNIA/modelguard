"""Run a stable-prediction test: changing an irrelevant feature should not matter."""

from __future__ import annotations

import json

import numpy as np
from sklearn.linear_model import LogisticRegression

from modelguard import BehaviorTestEngine, Dataset, TestDefinition, TestKind
from modelguard.adapters import SklearnAdapter


def build_example_report() -> dict[str, object]:
    rng = np.random.default_rng(24)
    age, income, irrelevant_color_code = rng.integers(18, 75, size=250), rng.normal(72_000, 16_000, size=250), rng.normal(0, 1, size=250)
    label = ((age * 0.05) + (income * 0.00002) > 3.4).astype(int)
    inputs = np.column_stack([age, income, irrelevant_color_code])
    model = LogisticRegression(C=0.15, max_iter=500).fit(inputs, label)
    dataset = Dataset(inputs, ["age", "income", "irrelevant_color_code"], label, "loan-eligibility-sample")
    test = TestDefinition("Irrelevant color-code stability", TestKind.INPUT_PERTURBATION, 0.03, {"feature": "irrelevant_color_code", "delta": 4.0}, "Predictions should remain stable when an irrelevant feature changes.")
    return BehaviorTestEngine(SklearnAdapter(model, "eligibility-logistic-regression")).run_suite([test], dataset).to_dict()


if __name__ == "__main__":
    print(json.dumps(build_example_report(), indent=2, default=str))
