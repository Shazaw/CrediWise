"""Train and export CrediWise Cash-Flow Risk v1 from pre-index Berka data."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any

from ml.repayment.features import (
    FEATURE_NAMES,
    TrainingSample,
    dataset_hash,
    load_berka_samples,
)
from ml.repayment.linear import LogisticModel, fit_logistic, sigmoid
from ml.repayment.metrics import evaluate


def _quantile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def _split(
    samples: list[TrainingSample], train_fraction: float, calibration_fraction: float
) -> tuple[list[TrainingSample], list[TrainingSample], list[TrainingSample]]:
    train_end = int(len(samples) * train_fraction)
    calibration_end = train_end + int(len(samples) * calibration_fraction)
    splits = samples[:train_end], samples[train_end:calibration_end], samples[calibration_end:]
    if any({sample.target for sample in split} != {0, 1} for split in splits):
        raise ValueError("Every temporal split must contain both outcomes")
    return splits


def _fit_preprocessing(samples: list[TrainingSample]) -> dict[str, list[float]]:
    columns = list(zip(*(sample.features for sample in samples), strict=True))
    lower = [_quantile(list(column), 0.01) for column in columns]
    upper = [_quantile(list(column), 0.99) for column in columns]
    clipped_columns = [
        [min(max(value, lo), hi) for value in column]
        for column, lo, hi in zip(columns, lower, upper, strict=True)
    ]
    centers = [statistics.fmean(column) for column in clipped_columns]
    scales = [statistics.pstdev(column) or 1.0 for column in clipped_columns]
    return {"clip_lower": lower, "clip_upper": upper, "centers": centers, "scales": scales}


def _transform(
    features: tuple[float, ...], preprocessing: dict[str, list[float]]
) -> tuple[float, ...]:
    return tuple(
        (min(max(value, lower), upper) - center) / scale
        for value, lower, upper, center, scale in zip(
            features,
            preprocessing["clip_lower"],
            preprocessing["clip_upper"],
            preprocessing["centers"],
            preprocessing["scales"],
            strict=True,
        )
    )


def _predict(
    samples: list[TrainingSample],
    preprocessing: dict[str, list[float]],
    model: LogisticModel,
    calibration: LogisticModel,
) -> list[float]:
    return [
        sigmoid(
            calibration.intercept
            + calibration.coefficients[0] * model.logit(_transform(sample.features, preprocessing))
        )
        for sample in samples
    ]


def _strings(values: list[float] | tuple[float, ...]) -> list[str]:
    return [format(value, ".17g") for value in values]


def _schema_hash(schema_path: Path) -> str:
    return hashlib.sha256(schema_path.read_bytes()).hexdigest()


def train(
    *,
    raw_directory: Path,
    config_path: Path,
    schema_path: Path,
    artifact_path: Path,
    metrics_path: Path,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    samples = load_berka_samples(raw_directory, minimum_months=config["minimum_months"])
    train_rows, calibration_rows, test_rows = _split(
        samples, config["train_fraction"], config["calibration_fraction"]
    )
    preprocessing = _fit_preprocessing(train_rows)
    train_features = [_transform(sample.features, preprocessing) for sample in train_rows]
    train_targets = [sample.target for sample in train_rows]
    positive_count = sum(train_targets)
    positive_weight = (len(train_targets) - positive_count) / positive_count
    model = fit_logistic(
        train_features,
        train_targets,
        l2_penalty=config["l2_penalty"],
        max_iterations=config["max_iterations"],
        tolerance=config["convergence_tolerance"],
        positive_weight=positive_weight,
    )
    calibration_logits = [
        (model.logit(_transform(sample.features, preprocessing)),) for sample in calibration_rows
    ]
    calibration = fit_logistic(
        calibration_logits,
        [sample.target for sample in calibration_rows],
        l2_penalty=0.01,
        max_iterations=config["max_iterations"],
        tolerance=config["convergence_tolerance"],
    )

    metrics = {
        "training": evaluate(
            [sample.target for sample in train_rows],
            _predict(train_rows, preprocessing, model, calibration),
        ),
        "calibration": evaluate(
            [sample.target for sample in calibration_rows],
            _predict(calibration_rows, preprocessing, model, calibration),
        ),
        "test": evaluate(
            [sample.target for sample in test_rows],
            _predict(test_rows, preprocessing, model, calibration),
        ),
    }
    artifact = {
        "artifact_format": "crediwise.linear_probability.v1",
        "model_name": config["model_name"],
        "model_version": config["model_version"],
        "target_version": config["target_version"],
        "feature_schema_version": config["feature_schema_version"],
        "feature_schema_sha256": _schema_hash(schema_path),
        "training_dataset_sha256": dataset_hash(samples),
        "training_source": "Berka/PKDD'99 Financial via CTU Relational Repository",
        "deployment_mode": "SHADOW_RESEARCH",
        "preprocessing": {
            "feature_order": list(FEATURE_NAMES),
            "clip_lower": _strings(preprocessing["clip_lower"]),
            "clip_upper": _strings(preprocessing["clip_upper"]),
            "centers": _strings(preprocessing["centers"]),
            "scales": _strings(preprocessing["scales"]),
        },
        "linear_model": {
            "intercept": format(model.intercept, ".17g"),
            "coefficients": _strings(model.coefficients),
            "l2_penalty": format(config["l2_penalty"], ".17g"),
        },
        "calibration": {
            "method": "PLATT",
            "intercept": format(calibration.intercept, ".17g"),
            "slope": format(calibration.coefficients[0], ".17g"),
        },
        "support": {
            "minimum_months": config["minimum_months"],
            "training_rows": len(train_rows),
            "calibration_rows": len(calibration_rows),
            "test_rows": len(test_rows),
            "earliest_index_date": samples[0].index_date.isoformat(),
            "latest_index_date": samples[-1].index_date.isoformat(),
            "geographic_scope": "Historical Czech banking benchmark; not Indonesian-calibrated",
        },
        "metrics": metrics,
    }
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(artifact, indent=2, sort_keys=True) + "\n"
    artifact_path.write_text(payload, encoding="utf-8")
    artifact_hash = hashlib.sha256(payload.encode()).hexdigest()
    artifact_path.with_suffix(artifact_path.suffix + ".sha256").write_text(
        f"{artifact_hash}  {artifact_path.name}\n", encoding="utf-8"
    )
    metrics_payload = {
        "artifact_sha256": artifact_hash,
        "metrics": metrics,
        "split": {
            "method": "chronological 70/15/15",
            "train_latest": train_rows[-1].index_date.isoformat(),
            "calibration_latest": calibration_rows[-1].index_date.isoformat(),
            "test_latest": test_rows[-1].index_date.isoformat(),
        },
    }
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(
        json.dumps(metrics_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return metrics_payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-directory", type=Path, default=Path("backend/ml/data/raw"))
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("backend/ml/repayment/configs/crediwise_cashflow_risk_v1.json"),
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("backend/ml/repayment/schemas/crediwise_cashflow_v1.json"),
    )
    parser.add_argument(
        "--artifact",
        type=Path,
        default=Path(
            "backend/app/integrations/repayment_model/artifacts/crediwise_cashflow_risk_v1.json"
        ),
    )
    parser.add_argument(
        "--metrics",
        type=Path,
        default=Path("backend/ml/repayment/evals/crediwise_cashflow_risk_v1.json"),
    )
    args = parser.parse_args()
    result = train(
        raw_directory=args.raw_directory,
        config_path=args.config,
        schema_path=args.schema,
        artifact_path=args.artifact,
        metrics_path=args.metrics,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
