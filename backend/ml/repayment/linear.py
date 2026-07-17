"""Small deterministic regularized logistic trainer used only offline."""

from __future__ import annotations

import math
from dataclasses import dataclass


def sigmoid(value: float) -> float:
    if value >= 0:
        exponent = math.exp(-min(value, 700.0))
        return 1.0 / (1.0 + exponent)
    exponent = math.exp(max(value, -700.0))
    return exponent / (1.0 + exponent)


def _solve(matrix: list[list[float]], values: list[float]) -> list[float]:
    size = len(values)
    augmented = [row[:] + [value] for row, value in zip(matrix, values, strict=True)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("Singular logistic-regression Hessian")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                current - factor * pivot_value
                for current, pivot_value in zip(augmented[row], augmented[column], strict=True)
            ]
    return [augmented[row][-1] for row in range(size)]


@dataclass(frozen=True)
class LogisticModel:
    intercept: float
    coefficients: tuple[float, ...]

    def logit(self, features: tuple[float, ...]) -> float:
        return self.intercept + sum(
            coefficient * feature
            for coefficient, feature in zip(self.coefficients, features, strict=True)
        )

    def predict(self, features: tuple[float, ...]) -> float:
        return sigmoid(self.logit(features))


def fit_logistic(
    rows: list[tuple[float, ...]],
    targets: list[int],
    *,
    l2_penalty: float,
    max_iterations: int,
    tolerance: float,
    positive_weight: float = 1.0,
) -> LogisticModel:
    if not rows or len(rows) != len(targets):
        raise ValueError("Training rows and targets must be non-empty and aligned")
    width = len(rows[0]) + 1
    beta = [0.0] * width
    design = [(1.0, *row) for row in rows]
    for _ in range(max_iterations):
        gradient = [0.0] * width
        hessian = [[0.0] * width for _ in range(width)]
        for features, target in zip(design, targets, strict=True):
            weight = positive_weight if target == 1 else 1.0
            probability = sigmoid(sum(b * x for b, x in zip(beta, features, strict=True)))
            residual = weight * (target - probability)
            curvature = weight * probability * (1.0 - probability)
            for left in range(width):
                gradient[left] += residual * features[left]
                for right in range(width):
                    hessian[left][right] += curvature * features[left] * features[right]
        for index in range(1, width):
            gradient[index] -= l2_penalty * beta[index]
            hessian[index][index] += l2_penalty
        hessian[0][0] += 1e-9
        delta = _solve(hessian, gradient)
        beta = [value + change for value, change in zip(beta, delta, strict=True)]
        if max(abs(change) for change in delta) < tolerance:
            break
    return LogisticModel(intercept=beta[0], coefficients=tuple(beta[1:]))
