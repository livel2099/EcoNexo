"""Autoencoder de deteccion de anomalias (PyTorch, CPU).

Elegimos PyTorch sobre TensorFlow: red chica, entrenamiento en segundos sobre
las series del seeder, imagen CPU liviana y API imperativa clara para un MVP.

El modelo aprende el patron NORMAL de cada variable a partir de features
[z(value), sin(hora), cos(hora)]. En inferencia, un error de reconstruccion
alto => lectura anomala. El score se calibra contra la distribucion de errores
de entrenamiento y se expone como probabilidad [0..1].
"""
from __future__ import annotations

import math

import numpy as np
import torch
from torch import nn


class AutoEncoder(nn.Module):
    def __init__(self, dim: int = 3) -> None:
        super().__init__()
        self.enc = nn.Sequential(nn.Linear(dim, 8), nn.ReLU(), nn.Linear(8, 2))
        self.dec = nn.Sequential(nn.Linear(2, 8), nn.ReLU(), nn.Linear(8, dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dec(self.enc(x))


class AnomalyModel:
    """Un autoencoder global + estadisticas de normalizacion por variable."""

    def __init__(self) -> None:
        self.net = AutoEncoder()
        self.var_stats: dict[str, tuple[float, float]] = {}   # variable -> (mean, std)
        self.err_mean = 0.02
        self.err_std = 0.02
        self.trained = False

    @staticmethod
    def _hour_feats(hour: int) -> tuple[float, float]:
        a = 2 * math.pi * hour / 24
        return math.sin(a), math.cos(a)

    def _featurize(self, variable: str, value: float, hour: int) -> list[float]:
        mean, std = self.var_stats.get(variable, (value, 1.0))
        z = (value - mean) / (std if std > 1e-6 else 1.0)
        s, c = self._hour_feats(hour)
        return [z, s, c]

    def train(self, rows: list[tuple[str, float, int]], epochs: int = 40) -> int:
        """rows: (variable, value, hour). Devuelve # de muestras entrenadas."""
        if not rows:
            return 0
        # estadisticas por variable
        by_var: dict[str, list[float]] = {}
        for var, val, _ in rows:
            by_var.setdefault(var, []).append(val)
        self.var_stats = {
            v: (float(np.mean(a)), float(np.std(a) or 1.0)) for v, a in by_var.items()
        }
        X = np.array([self._featurize(v, val, h) for v, val, h in rows], dtype=np.float32)
        xt = torch.from_numpy(X)
        opt = torch.optim.Adam(self.net.parameters(), lr=1e-2)
        loss_fn = nn.MSELoss()
        self.net.train()
        for _ in range(epochs):
            opt.zero_grad()
            out = self.net(xt)
            loss = loss_fn(out, xt)
            loss.backward()
            opt.step()
        # distribucion de error de reconstruccion (para calibrar el score)
        self.net.eval()
        with torch.no_grad():
            err = ((self.net(xt) - xt) ** 2).mean(dim=1).numpy()
        self.err_mean = float(err.mean())
        self.err_std = float(err.std() or 1e-3)
        self.trained = True
        return len(rows)

    def score(self, variable: str, value: float, hour: int) -> float:
        """Probabilidad de anomalia [0..1]."""
        feat = np.array([self._featurize(variable, value, hour)], dtype=np.float32)
        with torch.no_grad():
            xt = torch.from_numpy(feat)
            err = float(((self.net(xt) - xt) ** 2).mean().item())
        # sigmoide sobre el z-score del error de reconstruccion
        z = (err - self.err_mean) / (self.err_std if self.err_std > 1e-6 else 1e-3)
        prob = 1.0 / (1.0 + math.exp(-1.2 * (z - 1.0)))
        return round(min(1.0, max(0.0, prob)), 3)
