"""Adapter for torch.nn.Module models without coupling the core engine to PyTorch."""

from __future__ import annotations

from typing import Any

import numpy as np

from .base import PredictionAdapter


class PyTorchAdapter(PredictionAdapter):
    def __init__(self, model: Any, model_name: str | None = None, device: str = "cpu") -> None:
        try:
            import torch  # type: ignore
        except ImportError as error:
            raise ImportError("PyTorchAdapter requires the optional 'torch' dependency.") from error
        super().__init__(model_name or model.__class__.__name__)
        self.model, self.device, self.torch = model, device, torch
        self.model.eval()

    def _forward(self, values: np.ndarray) -> np.ndarray:
        tensor = self.torch.as_tensor(values, dtype=self.torch.float32, device=self.device)
        with self.torch.no_grad():
            output = self.model(tensor)
        if isinstance(output, (tuple, list)):
            output = output[0]
        return output.detach().cpu().numpy()

    def predict(self, values: np.ndarray) -> np.ndarray:
        output = self._forward(np.asarray(values, dtype=np.float32))
        if output.ndim == 1 or output.shape[-1] == 1:
            return (output.reshape(-1) >= 0).astype(int)
        return np.argmax(output, axis=1)

    def predict_scores(self, values: np.ndarray) -> np.ndarray:
        output = self._forward(np.asarray(values, dtype=np.float32))
        if output.ndim == 1 or output.shape[-1] == 1:
            return self.torch.sigmoid(self.torch.as_tensor(output)).cpu().numpy().reshape(-1)
        return self.torch.softmax(self.torch.as_tensor(output), dim=1).cpu().numpy().max(axis=1)
