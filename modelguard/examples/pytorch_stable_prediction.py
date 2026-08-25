"""Run the same irrelevant-feature stability test against a tiny PyTorch model."""

from __future__ import annotations

import json

import numpy as np
import torch

from modelguard import BehaviorTestEngine, Dataset, TestDefinition, TestKind
from modelguard.adapters import PyTorchAdapter


def build_example_report() -> dict[str, object]:
    model = torch.nn.Linear(3, 1)
    with torch.no_grad():
        model.weight[:] = torch.tensor([[0.06, 0.00002, 0.0]])
        model.bias[:] = torch.tensor([-4.0])
    dataset = Dataset(np.array([[25.0, 58_000.0, 0.0], [42.0, 95_000.0, 1.0], [30.0, 72_000.0, -1.0]]), ["age", "income", "irrelevant_color_code"], name="torch-sample")
    test = TestDefinition("Irrelevant color-code stability", TestKind.INPUT_PERTURBATION, 0.001, {"feature": "irrelevant_color_code", "delta": 8.0})
    return BehaviorTestEngine(PyTorchAdapter(model, "eligibility-torch-linear")).run_suite([test], dataset).to_dict()


if __name__ == "__main__":
    print(json.dumps(build_example_report(), indent=2, default=str))
