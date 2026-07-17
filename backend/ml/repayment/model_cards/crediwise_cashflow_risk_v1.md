# Model Card: CrediWise Cash-Flow Risk v1 Research

## Identity

- Model name: `crediwise-cashflow-risk`
- Version: `v1-research`
- Artifact: `crediwise.linear_probability.v1`
- Feature schema: `crediwise-cashflow-v1`
- Deployment mode: `SHADOW_RESEARCH`
- Artifact SHA-256: `57c4230f02f7f261da1eb1bdcea22ccfe9ea4688b705b5c2c41b9aba0977a267`

## Intended Use

This model demonstrates a CrediWise-owned, leakage-safe, explainable cash-flow
modeling pipeline. It provides supplementary research evidence after the
deterministic assessment completes. It does not modify Data Confidence, the
Indicative Risk Band, Safe Borrowing Capacity, shocks, Safe Offer scores, or
any approval decision.

## Training Data

The primary benchmark is the public Berka/PKDD'99 Financial dataset served by
the CTU Relational Dataset Repository. Only completed A/B loans are included.
Only transactions strictly before each loan's start date are eligible.

- Eligible rows after the two-month coverage gate: 234
- Adverse completed outcomes: 31
- Training: 163 rows / 25 adverse events
- Calibration: 35 rows / 3 adverse events
- Test: 36 rows / 3 adverse events
- Split: chronological 70/15/15 by loan start date

Raw and transformed source records are not committed because an explicit
redistribution license was not found. See `../ATTRIBUTION.md`.

## Features

The model uses twelve scale-free cash-flow and balance features: data coverage,
income volatility, positive-month ratio, debt-service ratio, free-cash-flow
margin, weakest-month margin, minimum and average balance ratios, buffer ratio,
negative-balance-month ratio, net-flow volatility, and balance trend.

Names, identifiers, demographics, precise geography, free-text descriptions,
Data Confidence, deterministic scores, and post-index transactions are excluded.

## Method

- Winsorization bounds fitted on the training partition only
- Standardization fitted on the training partition only
- L2-regularized logistic regression
- Positive-class weighting fitted on the training partition
- Platt calibration fitted only on the chronological calibration partition
- Dependency-free, deterministic training and JSON inference implementation

## Evaluation

| Split | ROC-AUC | Average precision | Brier score | Log loss |
|---|---:|---:|---:|---:|
| Training | 0.883 | 0.735 | 0.089 | 0.297 |
| Calibration | 0.635 | 0.428 | 0.075 | 0.277 |
| Temporal test | 0.687 | 0.696 | 0.041 | 0.205 |

The test set contains only three adverse events. These point estimates have
high uncertainty and are not sufficient for promotion beyond LOW model
confidence. No performance claim should omit the event count.

## Separate Public Benchmarks

The same dependency-free training and Platt-calibration implementation was
also tested independently on demographic-free native features from two CC BY
4.0 UCI datasets. These rows are never pooled with Berka and these results are
not external validation of the CrediWise cash-flow model.

| Dataset | Test rows / adverse | ROC-AUC | Average precision | Brier score |
|---|---:|---:|---:|---:|
| UCI Default of Credit Card Clients | 4,502 / 996 | 0.726 | 0.461 | 0.149 |
| UCI South German Credit | 151 / 45 | 0.735 | 0.563 | 0.180 |

Exact metrics and split warnings are recorded in
`../evals/public_benchmarks_v1.json`.

## Limitations

- Historical Czech banking data is not representative of Indonesian thin-file,
  gig-worker, informal-income, or UMKM users.
- The target is observed trouble on completed historical loans, not a fixed
  Indonesian delinquency horizon.
- Income is conservatively inferred from account inflows; own-account transfers
  cannot always be identified.
- The sample and adverse-event count are small.
- Public benchmarks contain approval and survivorship selection bias.
- No user-facing or lender-facing decision may depend on this model.

## Promotion Requirements

Promotion requires prospectively governed Indonesian repayment outcomes,
immutable pre-decision snapshots, a fixed outcome horizon, out-of-time
calibration, subgroup evaluation, confidence intervals, and explicit product,
fairness, privacy, and regulatory approval. Until then the deterministic
CrediWise assessment remains authoritative.
