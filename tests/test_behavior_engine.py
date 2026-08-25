import numpy as np

from modelguard import BehaviorTestEngine, Dataset, TestDefinition, TestKind
from modelguard.adapters.base import PredictionAdapter


class IrrelevantFeatureAdapter(PredictionAdapter):
    def __init__(self) -> None:
        super().__init__("irrelevant-feature-model")

    def predict(self, values: np.ndarray) -> np.ndarray:
        return (values[:, 0] >= 30).astype(int)

    def predict_scores(self, values: np.ndarray) -> np.ndarray:
        return values[:, 0] / 100


def test_irrelevant_feature_perturbation_passes() -> None:
    dataset = Dataset(np.array([[25.0, 1.0], [45.0, 2.0], [35.0, -2.0]]), ["age", "irrelevant_feature"])
    test = TestDefinition("irrelevant feature stability", TestKind.INPUT_PERTURBATION, 0.0, {"feature": "irrelevant_feature", "delta": 10.0})
    result = BehaviorTestEngine(IrrelevantFeatureAdapter()).run_test(test, dataset)
    assert result.status == "passed"
    assert result.metric_value == 0.0


def test_leakage_check_flags_a_label_copy() -> None:
    labels = np.array([0.0, 1.0, 0.0, 1.0])
    dataset = Dataset(np.column_stack([np.array([10.0, 20.0, 15.0, 30.0]), labels]), ["age", "leaked_target"], labels)
    result = BehaviorTestEngine(IrrelevantFeatureAdapter()).run_test(TestDefinition("leakage", TestKind.DATA_LEAKAGE, 0.95), dataset)
    assert result.status == "failed"
    assert result.evidence["suspected_feature"] == "leaked_target"
