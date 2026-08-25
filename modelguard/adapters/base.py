"""Model adapter interfaces used by the test engine."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class PredictionAdapter(ABC):
    """Normalizes framework-specific models behind a compact prediction contract."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    @abstractmethod
    def predict(self, values: np.ndarray) -> np.ndarray:
        """Return a one-dimensional array of labels or regression predictions."""

    def predict_scores(self, values: np.ndarray) -> np.ndarray:
        """Return numeric scores suitable for measuring prediction deltas."""
        return np.asarray(self.predict(values), dtype=float).reshape(-1)

    @staticmethod
    def ensure_vector(predictions: np.ndarray) -> np.ndarray:
        output = np.asarray(predictions)
        if output.ndim == 0:
            output = output.reshape(1)
        if output.ndim > 1:
            output = output.reshape(output.shape[0], -1)
            output = output[:, 0] if output.shape[1] == 1 else np.argmax(output, axis=1)
        return output.reshape(-1)
