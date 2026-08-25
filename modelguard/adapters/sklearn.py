"""Adapter for estimators following scikit-learn's prediction conventions."""

from __future__ import annotations

from typing import Any

import numpy as np

from .base import PredictionAdapter


class SklearnAdapter(PredictionAdapter):
    def __init__(self, model: Any, model_name: str | None = None) -> None:
        super().__init__(model_name or model.__class__.__name__)
        self.model = model

    def predict(self, values: np.ndarray) -> np.ndarray:
        return self.ensure_vector(np.asarray(self.model.predict(np.asarray(values))))

    def predict_scores(self, values: np.ndarray) -> np.ndarray:
        batch = np.asarray(values)
        if hasattr(self.model, "predict_proba"):
            probabilities = np.asarray(self.model.predict_proba(batch))
            return probabilities[:, 1] if probabilities.ndim == 2 and probabilities.shape[1] > 1 else probabilities.reshape(-1)
        if hasattr(self.model, "decision_function"):
            return self.ensure_vector(np.asarray(self.model.decision_function(batch))).astype(float)
        return super().predict_scores(batch)
