"""Dependency-free binary probability metrics."""

from __future__ import annotations

import math


def roc_auc(targets: list[int], probabilities: list[float]) -> float:
    positives = sum(targets)
    negatives = len(targets) - positives
    if not positives or not negatives:
        raise ValueError("ROC-AUC requires both target classes")
    ordered = sorted(zip(probabilities, targets, strict=True), key=lambda pair: pair[0])
    rank_sum = 0.0
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][0] == ordered[index][0]:
            end += 1
        average_rank = ((index + 1) + end) / 2.0
        rank_sum += average_rank * sum(target for _, target in ordered[index:end])
        index = end
    return (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def average_precision(targets: list[int], probabilities: list[float]) -> float:
    positives = sum(targets)
    if not positives:
        raise ValueError("Average precision requires positive targets")
    ordered = sorted(zip(probabilities, targets, strict=True), reverse=True)
    true_positives = 0
    precision_sum = 0.0
    for rank, (_, target) in enumerate(ordered, start=1):
        if target:
            true_positives += 1
            precision_sum += true_positives / rank
    return precision_sum / positives


def evaluate(targets: list[int], probabilities: list[float]) -> dict[str, float | int]:
    clipped = [min(max(value, 1e-12), 1.0 - 1e-12) for value in probabilities]
    return {
        "rows": len(targets),
        "adverse_events": sum(targets),
        "prevalence": sum(targets) / len(targets),
        "roc_auc": roc_auc(targets, clipped),
        "average_precision": average_precision(targets, clipped),
        "brier_score": sum(
            (target - value) ** 2 for target, value in zip(targets, clipped, strict=True)
        )
        / len(targets),
        "log_loss": -sum(
            target * math.log(value) + (1 - target) * math.log(1 - value)
            for target, value in zip(targets, clipped, strict=True)
        )
        / len(targets),
    }
