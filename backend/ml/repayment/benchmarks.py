"""Run separate, non-deployed public credit benchmarks without row pooling."""

from __future__ import annotations

import argparse
import json
import random
import statistics
import zipfile
from dataclasses import dataclass
from pathlib import Path

from ml.repayment.linear import fit_logistic, sigmoid
from ml.repayment.metrics import evaluate


@dataclass(frozen=True)
class _Sample:
    features: tuple[float, ...]
    target: int


def _stratified_split(
    samples: list[_Sample], seed: int = 20260717
) -> tuple[list[_Sample], list[_Sample], list[_Sample]]:
    randomizer = random.Random(seed)
    classes = {
        target: [sample for sample in samples if sample.target == target] for target in (0, 1)
    }
    for rows in classes.values():
        randomizer.shuffle(rows)
    splits: list[list[_Sample]] = [[], [], []]
    for rows in classes.values():
        train_end = int(len(rows) * 0.7)
        calibration_end = train_end + int(len(rows) * 0.15)
        for destination, source in zip(
            splits,
            (rows[:train_end], rows[train_end:calibration_end], rows[calibration_end:]),
            strict=True,
        ):
            destination.extend(source)
    for rows in splits:
        randomizer.shuffle(rows)
    return splits[0], splits[1], splits[2]


def _preprocessing(samples: list[_Sample]) -> tuple[list[float], list[float]]:
    columns = list(zip(*(sample.features for sample in samples), strict=True))
    centers = [statistics.fmean(column) for column in columns]
    scales = [statistics.pstdev(column) or 1.0 for column in columns]
    return centers, scales


def _transform(
    features: tuple[float, ...], centers: list[float], scales: list[float]
) -> tuple[float, ...]:
    return tuple(
        (value - center) / scale
        for value, center, scale in zip(features, centers, scales, strict=True)
    )


def _fit(samples: list[_Sample]) -> dict[str, object]:
    train, calibration, test = _stratified_split(samples)
    centers, scales = _preprocessing(train)
    train_targets = [sample.target for sample in train]
    adverse = sum(train_targets)
    model = fit_logistic(
        [_transform(sample.features, centers, scales) for sample in train],
        train_targets,
        l2_penalty=1.0,
        max_iterations=50,
        tolerance=1e-8,
        positive_weight=(len(train) - adverse) / adverse,
    )
    calibration_logits = [
        (model.logit(_transform(sample.features, centers, scales)),) for sample in calibration
    ]
    calibrator = fit_logistic(
        calibration_logits,
        [sample.target for sample in calibration],
        l2_penalty=0.01,
        max_iterations=50,
        tolerance=1e-8,
    )

    def probabilities(rows: list[_Sample]) -> list[float]:
        return [
            sigmoid(
                calibrator.intercept
                + calibrator.coefficients[0]
                * model.logit(_transform(sample.features, centers, scales))
            )
            for sample in rows
        ]

    return {
        "split": "deterministic stratified 70/15/15; source has no usable entity/time split",
        "training": evaluate(train_targets, probabilities(train)),
        "calibration": evaluate(
            [sample.target for sample in calibration], probabilities(calibration)
        ),
        "test": evaluate([sample.target for sample in test], probabilities(test)),
    }


def _south_german(path: Path) -> list[_Sample]:
    with zipfile.ZipFile(path) as archive:
        lines = archive.read("SouthGermanCredit.asc").decode("utf-8").splitlines()
    header = lines[0].split()
    samples = []
    selected = (
        "laufkont",
        "laufzeit",
        "moral",
        "hoehe",
        "sparkont",
        "beszeit",
        "rate",
        "bishkred",
    )
    for line in lines[1:]:
        values = dict(zip(header, line.split(), strict=True))
        samples.append(
            _Sample(
                features=tuple(float(values[name]) for name in selected),
                target=1 if values["kredit"] == "0" else 0,
            )
        )
    return samples


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator > 0 else 0.0


def _taiwan(path: Path) -> list[_Sample]:
    try:
        import xlrd
    except ImportError as exc:  # pragma: no cover - command-line dependency message
        raise RuntimeError("Install the backend 'ml' optional dependencies") from exc
    with zipfile.ZipFile(path) as archive:
        workbook_bytes = archive.read("default of credit card clients.xls")
    sheet = xlrd.open_workbook(file_contents=workbook_bytes).sheet_by_index(0)
    headers = [str(sheet.cell_value(1, column)).strip() for column in range(sheet.ncols)]
    samples = []
    for row_index in range(2, sheet.nrows):
        values = {
            name: float(sheet.cell_value(row_index, column)) for column, name in enumerate(headers)
        }
        limit = values["LIMIT_BAL"]
        payment_statuses = [values[f"PAY_{suffix}"] for suffix in ("0", "2", "3", "4", "5", "6")]
        bills = [values[f"BILL_AMT{month}"] for month in range(1, 7)]
        payments = [values[f"PAY_AMT{month}"] for month in range(1, 7)]
        payment_ratios = [
            _safe_ratio(payment, max(0.0, bill))
            for payment, bill in zip(payments, bills, strict=True)
        ]
        samples.append(
            _Sample(
                features=(
                    max(payment_statuses),
                    statistics.fmean(payment_statuses),
                    sum(status > 0 for status in payment_statuses) / 6.0,
                    _safe_ratio(statistics.fmean(bills), limit),
                    _safe_ratio(bills[0], limit),
                    statistics.fmean(payment_ratios),
                    payment_ratios[0],
                    _safe_ratio(statistics.fmean(payments), limit),
                ),
                target=int(values["default payment next month"]),
            )
        )
    return samples


def run(raw_directory: Path, output: Path) -> dict[str, object]:
    results = {
        "warning": (
            "Separate native-feature benchmarks only; not pooled, not external validation, "
            "and not used by production inference."
        ),
        "uci_default_credit_card_clients": _fit(
            _taiwan(raw_directory / "uci_default_credit_card_clients.zip")
        ),
        "uci_south_german_credit": _fit(
            _south_german(raw_directory / "uci_south_german_credit.zip")
        ),
    }
    output.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-directory", type=Path, default=Path("backend/ml/data/raw"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("backend/ml/repayment/evals/public_benchmarks_v1.json"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.raw_directory, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
