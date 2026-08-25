"""Small, dependency-light metrics for comparing model behavior."""

from __future__ import annotations

import numpy as np


def mean_absolute_delta(reference: np.ndarray, candidate: np.ndarray) -> float:
    return float(np.mean(np.abs(np.asarray(reference, dtype=float) - np.asarray(candidate, dtype=float))))


def agreement(reference: np.ndarray, candidate: np.ndarray) -> float:
    ref, value = np.asarray(reference).reshape(-1), np.asarray(candidate).reshape(-1)
    if ref.shape != value.shape:
        raise ValueError("Prediction arrays must have the same shape for agreement.")
    return float(np.mean(ref == value))


def prediction_variance(predictions: np.ndarray) -> float:
    return float(np.mean(np.var(np.asarray(predictions, dtype=float), axis=0)))
