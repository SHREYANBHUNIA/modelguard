"""Deterministic tabular input transformations used to probe model behavior."""

from __future__ import annotations

import numpy as np


def add_delta(values: np.ndarray, feature_index: int, delta: float) -> np.ndarray:
    perturbed = np.asarray(values, dtype=float).copy()
    perturbed[:, feature_index] += float(delta)
    return perturbed


def replace_feature(values: np.ndarray, feature_index: int, value: float) -> np.ndarray:
    perturbed = np.asarray(values, dtype=float).copy()
    perturbed[:, feature_index] = float(value)
    return perturbed
