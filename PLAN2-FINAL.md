# PLAN2.md — Krediwise Two-Hour Hackathon Build Plan

> **Purpose:** This is the implementation source of truth for the final two hours of the hackathon.
>
> Do not build the full production roadmap now. Build the smallest real, end-to-end Krediwise product that demonstrates the core innovation:
>
> 1. Can we trust the uploaded financial data?
> 2. What does the user’s cash flow say about repayment capacity?
> 3. Is a proposed loan safe for the user?
> 4. Can we explain the result clearly?
> 5. Can we keep users engaged with responsible-borrowing reminders?

- **Version:** `2.2.0-hackathon-final`
- **Status:** Final implementation scope
- **Primary client:** Native iOS, SwiftUI
- **Backend:** FastAPI
- **Async jobs:** Celery + Redis only where already available
- **Database:** PostgreSQL
- **Storage:** Existing S3-compatible storage or local development storage
- **Local AI:** Ollama with `qwen3:8b`
- **Time budget:** Approximately two hours

---

## 1. Final MVP Scope

### Must work end to end

1. User uploads one supported bank-statement PDF or screenshot.
2. Backend extracts statement text, metadata, and transactions.
3. Deterministic checks inspect:
   - balance consistency;
   - transaction chronology;
   - duplicate rows;
   - missing balances;
   - suspicious metadata;
   - OCR quality.
4. Local Qwen reviews the document and deterministic evidence for visual or structural anomalies.
5. Backend calculates a Data Confidence Score.
6. Backend computes:
   - income;
   - expenses;
   - free cash flow;
   - income stability;
   - existing debt burden;
   - maximum safe instalment;
   - indicative repayment-risk band;
   - shock resilience.
7. User enters a proposed loan amount, instalment, tenor, fees, and due date.
8. Krediwise calculates a Safe Offer Score and explains why the offer is safe, tight, or unsafe.
9. iOS dashboard displays the main results.
10. iOS schedules one daily responsible-borrowing notification at a semi-random local time.

### Do not build during the final two hours

- production Open Finance integration;
- production KYC;
- real lender integration;
- lender dashboard;
- full PKA workflow;
- complex model registry UI;
- multi-bank universal parsers;
- large-scale public-dataset retraining;
- full APNs backend campaign infrastructure;
- advanced admin portal;
- complete appeal and human-review workflow.

Scaffold existing code only if it does not delay the golden path.

---

## 2. Golden Demo Flow

```text
Open Krediwise
    ↓
Upload statement PDF
    ↓
Extract transactions
    ↓
Run deterministic verification
    ↓
Run local Qwen anomaly review
    ↓
Generate Data Confidence Score
    ↓
Build cash-flow summary
    ↓
Enter proposed loan terms
    ↓
Calculate Safe Instalment + Shock Resilience
    ↓
Generate Safe Offer Score
    ↓
Show dashboard and explanation
    ↓
Schedule daily responsible-borrowing notification
```

The entire demo should work with one known test statement fixture.

---

## 3. Feature Priority

### P0 — Required for demo

- document upload;
- PDF/image extraction;
- transaction parser for one known format;
- metadata checks;
- balance reconstruction;
- local Qwen anomaly analysis;
- Data Confidence Score;
- financial summary;
- safe instalment algorithm;
- shock simulation;
- Safe Offer Score;
- iOS dashboard;
- local daily notification;
- clear disclaimers.

### P1 — Build only if P0 is green

- second statement format;
- transaction-category charts;
- multiple shock scenarios;
- user-entered provider name;
- simple provider-warning message;
- notification preferences;
- assessment history.

### P2 — Skip unless already implemented

- Celery retry dashboard;
- full push-notification backend;
- public dataset model training;
- model registry administration;
- provider-directory scraper;
- user correction workflow;
- full multi-source aggregation.

---

## 4. Backend Architecture

Use the existing repository architecture. Do not restructure the project during the final two hours.

```text
backend/app/
├── api/
│   ├── documents.py
│   ├── assessments.py
│   └── offers.py
├── services/
│   ├── document_service.py
│   ├── assessment_service.py
│   └── offer_service.py
├── engines/
│   ├── trust_engine.py
│   ├── cashflow_engine.py
│   ├── risk_engine.py
│   ├── shock_engine.py
│   └── offer_engine.py
├── integrations/
│   └── ollama_qwen.py
├── schemas/
│   ├── document.py
│   ├── assessment.py
│   └── offer.py
└── models/
```

### Hard rule

- Deterministic engines calculate every number.
- Qwen returns structured anomaly evidence and natural-language explanations.
- Qwen must never directly decide the final score.

---

## 5. Supported Input

### Primary supported input

One known digitally generated bank statement PDF.

Recommended fixture requirements:

- transaction date;
- description;
- debit or credit;
- balance;
- statement owner name;
- statement period.

### Fallback input

Screenshot or image of a statement.

For image input:

- OCR confidence is lower;
- provenance score is lower;
- missing metadata is expected;
- Data Confidence cannot be marked “strongly verified.”

### File constraints

- PDF, PNG, JPG;
- maximum 15 MB;
- reject corrupt files;
- calculate SHA-256 hash;
- never commit real financial records;
- use synthetic or redacted fixtures for demo.

---

## 6. Transaction Extraction

Canonical transaction object:

```json
{
  "date": "2026-06-01",
  "description": "TRANSFER MASUK",
  "amount": 2500000,
  "direction": "CREDIT",
  "balance_after": 3200000,
  "extraction_confidence": 0.97
}
```

Required extraction outputs:

- account holder;
- statement start and end date;
- opening balance;
- closing balance;
- transaction list;
- OCR confidence;
- parser name;
- parser version.

### Parser rule

Support one format well. Do not create a universal parser during the last two hours.

If the format is unsupported:

```json
{
  "status": "UNSUPPORTED_FORMAT",
  "message": "This statement format is not supported in the current MVP."
}
```

---

## 7. Deterministic Document Verification

### 7.1 Metadata checks

Check:

- creation date;
- modification date;
- PDF producer;
- PDF creator;
- page count;
- whether text is embedded or image-only;
- suspicious modification after creation;
- inconsistent metadata fields.

Output:

```json
{
  "metadata_score": 82,
  "flags": [
    "MODIFIED_AFTER_CREATION"
  ]
}
```

### 7.2 Balance reconstruction

For each transaction:

```text
Expected Balance =
Previous Balance + Credits - Debits
```

Calculate:

```text
balance_consistency_ratio =
consistent_rows / rows_with_balance
```

Flags:

- `BALANCE_MISMATCH`;
- `IMPOSSIBLE_BALANCE_JUMP`;
- `MISSING_BALANCE`;
- `OPENING_CLOSING_MISMATCH`.

### 7.3 Chronology

Check:

- dates are ordered;
- statement period contains all rows;
- no impossible future dates;
- no repeated row sequence.

### 7.4 Duplicate detection

Row hash:

```text
SHA256(date + amount + direction + normalized_description + balance_after)
```

Flags:

- exact duplicate;
- near-duplicate with different balance;
- repeated transaction reference.

### 7.5 Extraction quality

Calculate:

- mean OCR confidence;
- low-confidence field count;
- missing required values;
- parse-failure ratio.

---

## 8. Local Qwen Fraud and Anomaly Detection

### 8.1 Model

Use:

```text
Ollama
Model: qwen3:8b
```

If a vision-capable Qwen model is already installed, use it for rendered-page analysis. Otherwise provide Qwen with:

- extracted text;
- PDF metadata;
- font statistics;
- bounding-box anomalies;
- deterministic flags;
- transaction consistency evidence.

Do not spend the remaining time downloading a massive model if Qwen is not already available.

### 8.2 Qwen responsibility

Qwen may identify:

- inconsistent formatting;
- suspicious spacing;
- unusual font changes;
- duplicated text sections;
- missing statement fields;
- unnatural transaction descriptions;
- suspicious metadata combinations;
- anomalies that deserve manual review.

Qwen must return JSON:

```json
{
  "anomalies": [
    {
      "type": "FONT_INCONSISTENCY",
      "severity": "MEDIUM",
      "confidence": 0.78,
      "evidence": "Transaction row 14 appears to use a different font weight."
    }
  ],
  "summary": "Two structural anomalies were detected."
}
```

### 8.3 Prompt

```text
You are a financial-document anomaly assistant.

You do not decide whether a document is fake.
You do not calculate the final Data Confidence Score.
You only identify structural, textual, and consistency anomalies.

Review the supplied:
- metadata;
- extracted transaction rows;
- OCR confidence;
- deterministic verification flags;
- layout statistics.

Return strict JSON matching the required schema.
Do not invent missing data.
```

### 8.4 Qwen failure handling

If Ollama is unavailable:

- continue using deterministic checks;
- set `ai_analysis_status = UNAVAILABLE`;
- do not fail the assessment;
- explain that AI anomaly assistance was skipped.

---

## 9. Data Confidence Score

The score must be deterministic.

### 9.1 Components

| Component | Weight |
|---|---:|
| Source provenance | 15% |
| Balance consistency | 25% |
| Metadata integrity | 15% |
| Extraction quality | 15% |
| Completeness | 10% |
| Ownership evidence | 10% |
| Structural anomaly evidence | 10% |

### 9.2 Source provenance score

| Source | Score |
|---|---:|
| Original digital PDF | 85 |
| Exported PDF without strong metadata | 70 |
| Screenshot | 50 |
| Photograph of screen | 35 |

### 9.3 Structural anomaly score

Start at 100.

Subtract:

- low anomaly: 5;
- medium anomaly: 12;
- high anomaly: 25.

Maximum total deduction: 60.

Qwen contributes evidence severity. The backend applies the deduction.

### 9.4 Formula

```text
DataConfidence =
0.15 × provenance
+ 0.25 × balance_consistency
+ 0.15 × metadata
+ 0.15 × extraction_quality
+ 0.10 × completeness
+ 0.10 × ownership
+ 0.10 × structural_consistency
```

Clamp to 0–100.

### 9.5 Bands

```text
HIGH: 80–100
MEDIUM: 55–79
LOW: 0–54
```

### 9.6 Required wording

Do not say:

- fake;
- fraudulent;
- dishonest user.

Say:

- high confidence;
- medium confidence;
- low confidence;
- anomalies detected;
- additional verification recommended.

---

## 10. Cash-Flow Analysis

Use only confirmed extracted transactions.

### 10.1 Income

For the final MVP:

```text
monthly_income =
sum of CREDIT transactions
excluding internal transfers
```

For a multi-month statement:

```text
median_monthly_income
average_monthly_income
income_volatility = standard_deviation / mean
```

### 10.2 Expenses

```text
monthly_expenses =
sum of DEBIT transactions
excluding internal transfers
```

Use simple categories:

- essential;
- discretionary;
- debt;
- internal transfer;
- unknown.

A keyword-based classifier is sufficient for the final two hours.

### 10.3 Existing debt

Identify likely debt payments through keywords:

- cicilan;
- kredit;
- pinjaman;
- paylater;
- kredivo;
- akulaku;
- bank finance;
- multifinance.

### 10.4 Free cash flow

```text
FreeCashFlow =
MedianMonthlyIncome
- EssentialExpenses
- ExistingDebtPayments
```

### 10.5 Required buffer

```text
RequiredBuffer =
max(
  250000,
  0.10 × MedianMonthlyIncome,
  0.15 × EssentialExpenses
)
```

The fixed Rp250,000 value is an MVP assumption and must be configurable.

---

## 11. Actual Repayment-Risk Algorithm

For the final two hours, use a deterministic risk algorithm unless a trained model artifact is already integrated and tested.

### 11.1 Inputs

- Data Confidence;
- income stability;
- positive cash-flow ratio;
- debt-service ratio;
- low-balance frequency;
- free-cash-flow margin;
- months of data.

### 11.2 Sub-scores

#### Income stability

```text
volatility <= 0.10 → 100
0.10–0.20 → 80
0.20–0.35 → 60
0.35–0.50 → 40
> 0.50 → 20
```

#### Positive cash-flow ratio

```text
>= 0.80 → 100
0.60–0.79 → 75
0.40–0.59 → 50
< 0.40 → 25
```

#### Debt-service ratio

```text
DebtServiceRatio =
ExistingDebtPayments / MedianMonthlyIncome
```

```text
<= 0.20 → 100
0.20–0.35 → 75
0.35–0.45 → 50
> 0.45 → 20
```

#### Free-cash-flow margin

```text
FreeCashFlowMargin =
FreeCashFlow / MedianMonthlyIncome
```

```text
>= 0.30 → 100
0.20–0.29 → 80
0.10–0.19 → 60
0–0.09 → 40
< 0 → 10
```

#### Data coverage

```text
>= 6 months → 100
3–5 months → 70
2 months → 50
1 month → 30
```

### 11.3 Composite risk score

```text
RepaymentReliability =
0.25 × income_stability
+ 0.20 × positive_cashflow
+ 0.25 × debt_service
+ 0.20 × free_cashflow_margin
+ 0.10 × coverage
```

Apply confidence gate:

```text
if DataConfidence < 55:
    result = INSUFFICIENT_DATA
```

### 11.4 Risk bands

```text
A: 80–100
B: 65–79
C: 50–64
D: 0–49
```

Required label:

> Indicative Repayment-Risk Band

Do not label it as an official credit score.

### 11.5 Optional trained model

Only use a trained Berka model if all of the following already exist:

- model artifact;
- preprocessing pipeline;
- feature-schema match;
- tests;
- model card;
- serving endpoint.

Do not spend the final two hours training and integrating a model from scratch unless the rest of the demo is already complete.

---

## 12. Maximum Safe Instalment

### 12.1 Base capacity

```text
BaseCapacity =
MedianMonthlyIncome
- EssentialExpenses
- ExistingDebtPayments
- RequiredBuffer
```

### 12.2 Ratio cap

```text
RatioCap =
0.25 × MedianMonthlyIncome
```

### 12.3 Final maximum

```text
MaximumSafeInstalment =
max(
  0,
  min(BaseCapacity, RatioCap)
)
```

### 12.4 Weak-month adjustment

If more than one month is available:

```text
WeakMonthCapacity =
WeakestMonthIncome
- WeakestMonthEssentialExpenses
- ExistingDebtPayments
- RequiredBuffer
```

Then:

```text
MaximumSafeInstalment =
max(
  0,
  min(
    MaximumSafeInstalment,
    WeakMonthCapacity
  )
)
```

---

## 13. Shock Simulation

Run three scenarios.

### Scenario A — Income drops 10%

```text
AdjustedIncome = MedianIncome × 0.90
```

### Scenario B — Income drops 20%

```text
AdjustedIncome = MedianIncome × 0.80
```

### Scenario C — Emergency expense

```text
EmergencyExpense = Rp1,000,000
```

For each:

```text
ProjectedRemainingCash =
AdjustedIncome
- EssentialExpenses
- ExistingDebt
- ProposedInstalment
- EmergencyExpense
```

Outcome:

```text
SAFE:
ProjectedRemainingCash >= RequiredBuffer

TIGHT:
0 <= ProjectedRemainingCash < RequiredBuffer

DEFICIT:
ProjectedRemainingCash < 0
```

### Shock Resilience Score

```text
10% income drop safe → 30 points
20% income drop safe → 40 points
Emergency expense safe → 30 points
```

Partial/TIGHT earns half points.

Bands:

```text
STRONG: 75–100
MODERATE: 50–74
FRAGILE: 0–49
```

---

## 14. Safe Offer Score

### 14.1 User-entered terms

Required:

- loan amount;
- amount actually received;
- monthly instalment;
- tenor;
- admin fee;
- other fees;
- due date;
- total repayment, if known.

### 14.2 True cost

```text
TotalCost =
TotalRepayment - NetAmountReceived
```

If total repayment is missing:

```text
TotalRepayment =
Instalment × NumberOfInstalments
```

### 14.3 Scoring

| Factor | Weight |
|---|---:|
| Instalment within safe limit | 30% |
| Shock resilience | 25% |
| Remaining cash buffer | 20% |
| Total cost | 15% |
| Fee transparency | 5% |
| Due-date fit | 5% |

### 14.4 Safe instalment factor

```text
ProposedInstalment <= MaximumSafeInstalment → 100
<= 1.20 × MaximumSafeInstalment → 50
> 1.20 × MaximumSafeInstalment → 10
```

### 14.5 Bands

```text
SAFE: 75–100
CAUTION: 50–74
UNSAFE: 0–49
```

### 14.6 Required explanation

Examples:

- “The instalment is below your estimated safe monthly limit.”
- “The offer becomes unaffordable after a 20% income reduction.”
- “Upfront fees reduce the amount you actually receive.”
- “The due date may occur before your normal income arrives.”

---

## 15. Daily Responsible-Borrowing Notification

For the final two hours, use **local iOS notifications**, not full APNs infrastructure.

### 15.1 Behavior

- user opts in;
- one notification per day;
- time is semi-random within 09:30–19:30;
- do not send during quiet hours;
- schedule the next seven days locally;
- tapping opens Krediwise.

### 15.2 Deterministic semi-random timing

Use:

```text
seed = hash(user_id + local_date)
offset_minutes = seed % 600
scheduled_time = 09:30 + offset_minutes
```

### 15.3 Notification pool

Indonesian examples:

**Pinjol belum tentu jadi jalan keluar**
Cek legalitas, biaya, dan kemampuan bayarmu sebelum mengambil pinjaman.

**Cicilan kecil belum tentu murah**
Lihat total biaya dan uang yang benar-benar kamu terima.

**Ada tawaran pinjaman baru?**
Masukkan detailnya dan cek apakah cicilannya aman untuk arus kasmu.

**Jangan buru-buru ambil pinjaman**
Simulasikan dulu bagaimana kondisi keuanganmu jika pendapatan turun.

**Pinjam sesuai kemampuan, bukan batas maksimum**
Cari tahu cicilan yang tetap aman saat ada pengeluaran mendadak.

### 15.4 iOS implementation

```text
NotificationService.swift
NotificationPermissionView.swift
NotificationSettingsView.swift
```

Use `UNUserNotificationCenter`.

No backend required for this final build.

---

## 16. iOS Screens

### Screen 1 — Upload

- choose PDF/image;
- show selected filename;
- upload;
- processing state.

### Screen 2 — Data Confidence

Show:

- score;
- band;
- balance consistency;
- metadata status;
- extraction quality;
- anomaly summary.

### Screen 3 — Financial Summary

Show:

- monthly income;
- expenses;
- existing debt;
- free cash flow;
- risk band;
- safe instalment.

### Screen 4 — Loan Offer Input

Fields:

- loan amount;
- amount received;
- instalment;
- tenor;
- fees;
- due date.

### Screen 5 — Offer Result

Show:

- Safe Offer Score;
- SAFE / CAUTION / UNSAFE;
- shock outcomes;
- explanation;
- total cost.

### Screen 6 — Notification Settings

- enable daily tips;
- show next notification time;
- disable notifications.

---

## 17. Minimal API

### Upload

```text
POST /api/v1/documents
```

Response:

```json
{
  "document_id": "uuid",
  "status": "PROCESSING"
}
```

### Status

```text
GET /api/v1/documents/{id}
```

### Assessment

```text
POST /api/v1/assessments
```

Request:

```json
{
  "document_id": "uuid"
}
```

### Dashboard

```text
GET /api/v1/assessments/{id}/dashboard
```

### Offer analysis

```text
POST /api/v1/assessments/{id}/offers/analyze
```

Request:

```json
{
  "loan_amount": 5000000,
  "net_amount_received": 4700000,
  "monthly_instalment": 620000,
  "tenor_months": 10,
  "fees": 300000,
  "due_day": 5
}
```

---

## 18. Minimal Database Tables

### `source_documents`

- id;
- user_id;
- file_path;
- file_hash;
- mime_type;
- status;
- metadata_json;
- created_at.

### `transactions`

- id;
- document_id;
- date;
- description;
- amount;
- direction;
- balance_after;
- category;
- extraction_confidence.

### `document_verification_results`

- document_id;
- metadata_score;
- balance_score;
- extraction_score;
- structural_score;
- data_confidence_score;
- confidence_band;
- qwen_anomalies_json.

### `assessments`

- id;
- user_id;
- document_id;
- risk_score;
- risk_band;
- shock_score;
- max_safe_instalment;
- financial_summary_json.

### `offers`

- id;
- assessment_id;
- terms_json;
- safe_offer_score;
- status;
- explanation_json.

Use JSON columns where it saves implementation time.

---

## 19. Testing Priorities

### Required tests

1. Balance reconstruction produces expected score.
2. Data Confidence formula is deterministic.
3. Low-confidence document returns `INSUFFICIENT_DATA`.
4. Safe instalment never becomes negative.
5. Shock simulation correctly identifies deficits.
6. Safe Offer Score penalizes an instalment over the safe limit.
7. Qwen invalid JSON does not crash the pipeline.
8. Local notification scheduler produces one time per day within the allowed window.

### Skip during final two hours

- exhaustive integration suite;
- load testing;
- complete security penetration testing;
- full model fairness evaluation;
- nightly AI evals.

Run the required tests before final demo.

---

## 20. Two-Hour Execution Plan

### Minute 0–20

Backend:

- confirm existing upload endpoint;
- confirm one supported fixture;
- implement or fix parser;
- verify extracted transactions.

Frontend:

- confirm upload screen;
- connect upload API;
- display processing state.

### Minute 20–45

Backend:

- implement metadata checks;
- balance reconstruction;
- duplicate and chronology checks;
- Data Confidence formula.

Frontend:

- build Data Confidence card.

### Minute 45–65

Backend:

- integrate Ollama Qwen JSON call;
- add fallback;
- store anomaly evidence.

Frontend:

- display anomaly summary.

### Minute 65–90

Backend:

- implement cash-flow metrics;
- risk band;
- safe instalment;
- three shock scenarios.

Frontend:

- financial summary and shock results.

### Minute 90–110

Backend:

- implement offer analysis;
- Safe Offer Score;
- explanations.

Frontend:

- loan-offer form;
- result screen.

### Minute 110–120

Frontend:

- local daily notification;
- schedule next seven days.

Everyone:

- run tests;
- run full demo twice;
- fix only demo-blocking issues;
- commit and push.

---

## 21. Demo Data

Use one synthetic statement that intentionally contains:

- stable income;
- several expenses;
- one existing debt payment;
- one balance inconsistency or formatting anomaly;
- enough history to show calculations.

Use one loan offer:

```text
Loan amount: Rp5,000,000
Cash received: Rp4,700,000
Monthly instalment: Rp620,000
Tenor: 10 months
Fees: Rp300,000
Due date: 5th
```

The expected result should be `CAUTION` or `UNSAFE`, so the product’s warning value is visible.

---

## 22. Required Disclaimers

Display:

> Krediwise provides an indicative financial-risk and affordability assessment based on the data supplied. It is not an official credit score, loan approval, or financial institution.

For fraud analysis:

> Detected anomalies reduce confidence but do not prove that a document is fraudulent.

For loan offers:

> Krediwise independently analyses terms entered by the user. It does not issue, endorse, or guarantee the offer.

---

## 23. Definition of Done

The final hackathon build is done when:

- one statement uploads successfully;
- transactions are extracted;
- deterministic verification runs;
- Qwen anomaly analysis runs or safely falls back;
- Data Confidence Score appears;
- income, expenses, free cash flow, risk band, and safe instalment appear;
- a loan offer can be entered;
- shock simulation and Safe Offer Score appear;
- one daily local notification is scheduled;
- the entire demo works twice without restarting;
- code is committed and pushed.

Anything else is optional.

---

## 24. Final Positioning

> Krediwise verifies uploaded financial records, analyses a user’s real cash flow, calculates an indicative repayment-risk profile, stress-tests proposed loan terms, and warns users when a loan may become unsafe.
>
> The MVP uses deterministic financial algorithms and local Qwen-assisted anomaly detection. It does not claim to be a licensed PKA or an official lender decision system.

*End of PLAN2.md v2.2.0-hackathon-final.*
