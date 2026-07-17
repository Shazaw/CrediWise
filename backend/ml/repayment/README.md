# CrediWise Repayment Model Research

This lane trains `crediwise-cashflow-risk:v1-research`, an internally designed
and versioned cash-flow model using an attributed historical public benchmark.
It is deliberately separate from the deterministic engines that calculate Data
Confidence, the Indicative Risk Band, Safe Borrowing Capacity, shocks, and Safe
Offer scores.

## Reproduce

```bash
python -m pip install -e 'backend[ml]'
BERKA_DB_PASSWORD='<public password from the attributed CTU source>' \
  PYTHONPATH=backend python -m ml.repayment.acquire
PYTHONPATH=backend python -m ml.repayment.train
PYTHONPATH=backend python -m ml.repayment.benchmarks
```

Raw data is written under `backend/ml/data/`, which is ignored by Git. The
acquisition manifest records source URLs and SHA-256 hashes. The committed JSON
artifact contains no source rows or PII and can be evaluated by a
standard-library runtime without loading executable pickle files.

## Intended Use

- Shadow-mode research evidence.
- Demonstrating leakage-safe transaction feature engineering.
- Comparing model evidence with the deterministic assessment.
- Collecting calibration evidence before an Indonesian lender pilot.

## Prohibited Use

- Automatic approval or rejection.
- Official credit scoring.
- Safe-instalment, offer, pricing, or fraud decisions.
- Claims of Indonesian calibration or regulatory recognition.
- Training on synthetic CrediWise fixtures.
