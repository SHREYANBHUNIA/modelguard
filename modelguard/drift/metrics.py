"""Distribution-shift measurements for tabular model inputs."""

from __future__ import annotations

import numpy as np


def population_stability_index(reference: np.ndarray, candidate: np.ndarray, bins: int = 10) -> float:
    reference, candidate = np.asarray(reference, dtype=float).reshape(-1), np.asarray(candidate, dtype=float).reshape(-1)
    if len(reference) == 0 or len(candidate) == 0:
        raise ValueError("PSI requires non-empty reference and candidate samples.")
    edges = np.unique(np.quantile(reference, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        return 0.0
    expected, _ = np.histogram(reference, bins=edges)
    actual, _ = np.histogram(candidate, bins=edges)
    expected_ratio, actual_ratio = np.clip(expected / expected.sum(), 1e-6, None), np.clip(actual / actual.sum(), 1e-6, None)
    return float(np.sum((actual_ratio - expected_ratio) * np.log(actual_ratio / expected_ratio)))
