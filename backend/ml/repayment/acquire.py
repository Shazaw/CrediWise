"""Acquire attributed public research datasets without committing raw data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any

UCI_DATASETS = {
    "uci_default_credit_card_clients.zip": (
        "https://archive.ics.uci.edu/static/public/350/" "default+of+credit+card+clients.zip"
    ),
    "uci_south_german_credit.zip": (
        "https://archive.ics.uci.edu/static/public/573/" "south+german+credit+update.zip"
    ),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _download(url: str, destination: Path) -> None:
    if destination.exists():
        return
    request = urllib.request.Request(url, headers={"User-Agent": "CrediWise-Research/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310 - fixed HTTPS URLs
        destination.write_bytes(response.read())


def _serialize(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, date | datetime):
        return value.isoformat()
    return str(value)


def _export_berka(destination: Path) -> dict[str, Any]:
    try:
        import pymysql
        from pymysql.cursors import SSCursor
    except ImportError as exc:  # pragma: no cover - command-line dependency message
        raise RuntimeError("Install the backend 'ml' optional dependencies") from exc

    password = os.environ.get("BERKA_DB_PASSWORD")
    if not password:
        raise RuntimeError(
            "Set BERKA_DB_PASSWORD to the public guest password published by the CTU source"
        )
    connection = pymysql.connect(
        host=os.environ.get("BERKA_DB_HOST", "relational.fel.cvut.cz"),
        port=3306,
        user=os.environ.get("BERKA_DB_USER", "guest"),
        password=password,
        database="financial",
        connect_timeout=30,
        read_timeout=300,
        cursorclass=SSCursor,
    )
    loan_path = destination / "berka_finished_loans.csv"
    transaction_path = destination / "berka_preloan_transactions.csv"
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT loan_id, account_id, date, amount, duration, payments, status "
                "FROM loan WHERE status IN ('A', 'B') ORDER BY date, loan_id"
            )
            with loan_path.open("w", newline="", encoding="utf-8") as output:
                writer = csv.writer(output)
                writer.writerow(
                    [
                        "loan_id",
                        "account_id",
                        "loan_date",
                        "amount",
                        "duration",
                        "payments",
                        "status",
                    ]
                )
                loan_count = 0
                for row in cursor:
                    writer.writerow([_serialize(value) for value in row])
                    loan_count += 1

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT l.loan_id, t.trans_id, t.account_id, t.date, t.type, "
                "t.amount, t.balance, t.k_symbol "
                "FROM loan l JOIN trans t ON t.account_id = l.account_id "
                "WHERE l.status IN ('A', 'B') AND t.date < l.date "
                "ORDER BY l.loan_id, t.date, t.trans_id"
            )
            with transaction_path.open("w", newline="", encoding="utf-8") as output:
                writer = csv.writer(output)
                writer.writerow(
                    [
                        "loan_id",
                        "transaction_id",
                        "account_id",
                        "transaction_date",
                        "type",
                        "amount",
                        "balance",
                        "k_symbol",
                    ]
                )
                transaction_count = 0
                for row in cursor:
                    writer.writerow([_serialize(value) for value in row])
                    transaction_count += 1
    finally:
        connection.close()

    return {
        "loan_rows": loan_count,
        "transaction_rows": transaction_count,
        "loan_sha256": _sha256(loan_path),
        "transaction_sha256": _sha256(transaction_path),
    }


def acquire(destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    files: dict[str, dict[str, Any]] = {}
    for filename, url in UCI_DATASETS.items():
        path = destination / filename
        _download(url, path)
        files[filename] = {"source": url, "sha256": _sha256(path)}

    berka = _export_berka(destination)
    manifest = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "raw_data_committed": False,
        "sources": files,
        "berka": {
            "source": "MariaDB financial database at relational.fel.cvut.cz",
            **berka,
        },
    }
    manifest_path = destination / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, default=Path("backend/ml/data/raw"))
    args = parser.parse_args()
    print(acquire(args.destination))


if __name__ == "__main__":
    main()
