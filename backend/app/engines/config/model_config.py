"""Versioned deterministic-engine weights/thresholds (PLAN §19.2, T1.7).

`CONFIG` is the hashable source of truth stamped on `model_versions.config_hash`
(§19.2: "changing any number here = a new model version"). Sprint 1-2 left
this empty as a bootstrap placeholder ("Real deterministic-engine weights
land starting Sprint 3+ as each engine in PLAN §15 ships" — this file's
prior docstring); Sprint 3 is the first engine (`TrustLayerEngine`) to
populate it, so this remains `MODEL_VERSION = "v1"` rather than a bump — an
empty placeholder becoming real for the first time is not "mutating a
released version's meaning." Any future change to a number already defined
here requires a new `MODEL_VERSION`.

Numeric values not explicitly given by PLAN §5.2/§15.3 (e.g. the exact
metadata/visual-forensics penalty sizes) are Sprint 3 gap-fills (§24.11),
called out inline — PLAN documents *which signals* feed each sub-score, not
their exact point values.

Sprint 4 adds `normalization`/`cash_flow_twin`/`risk`/`safe_borrowing` keys
under the *same* `MODEL_VERSION = "v1"` — net-new keys, not a change to any
number `trust_layer` already shipped under v1, so this is the same
"empty/undefined becoming real for the first time" case the paragraph above
already covers, not a version bump. PLAN §5.3/§5.6/§5.7 name the required
signals and several concrete thresholds (DSTI bands, cash-flow-ratio bands,
weight splits, tenor candidate set, 24%/year reference rate); numbers PLAN
leaves unspecified (volatility scaling, behaviour-score signal, buffer
ratios, due-date offsets) are Sprint 4 gap-fills, called out inline below.
"""

import hashlib
import json
from decimal import Decimal

MODEL_NAME = "crediwise-core"
MODEL_VERSION = "v1"

# PLAN §5.2 weighted model (must sum to 1.00).
TRUST_LAYER_WEIGHTS: dict[str, Decimal] = {
    "provenance": Decimal("0.20"),
    "consistency": Decimal("0.20"),
    "metadata": Decimal("0.15"),
    "ocr": Decimal("0.15"),
    "visual": Decimal("0.10"),
    "completeness": Decimal("0.10"),
    "ownership": Decimal("0.10"),
}

# PLAN §5.2 provenance tiers, keyed by `source_type_enum` value.
TRUST_LAYER_PROVENANCE_TIERS: dict[str, int] = {
    "BANK_API": 100,
    "SIGNED_STATEMENT": 90,
    "ORIGINAL_PDF": 78,
    "EXPORTED_CSV": 65,
    "SCREENSHOT": 45,
    "PHOTO": 30,
}

# PLAN §5.2: HIGH >= 80, MEDIUM 50-79, LOW < 50.
TRUST_LAYER_BAND_THRESHOLDS: dict[str, int] = {"high": 80, "medium": 50}

# PLAN §5.2 completeness component: "months covered vs required (target 6)".
TRUST_LAYER_COMPLETENESS_TARGET_MONTHS = 6

# Sprint 3 gap-fill (§24.11): PLAN §15.3 item 3 names the signals (creation/
# mod date, producer/creator, digital signature, incremental edits) but not
# point values.
TRUST_LAYER_METADATA: dict[str, int] = {
    "base": 100,
    "missing_creation_date_penalty": 20,
    "missing_producer_penalty": 10,
    "no_forensics_base": 60,
    "incremental_update_penalty_per_update": 10,
    "incremental_update_penalty_cap": 40,
    "signature_bonus": 5,
}

# Sprint 3 gap-fill (§24.11): PLAN §15.3 item 6 names font/alignment/overlay
# heuristics but not point values.
TRUST_LAYER_VISUAL: dict[str, int] = {
    "base": 100,
    "excess_font_threshold": 3,
    "excess_font_penalty": 15,
    "duplicate_row_penalty": 20,
    "no_forensics_base": 70,
}

# Sprint 3 gap-fill (§24.11): the neutral default when no balance-carrying
# rows exist to reconstruct (PLAN §5.2 EC: "single-month upload may have
# high authenticity but low coverage" — a missing signal is not a penalty).
TRUST_LAYER_CONSISTENCY: dict[str, int] = {"no_balance_data_default": 50}

# Sprint 3 gap-fill (§24.11): PLAN §15.3 item 9 requires ownership matching
# "tolerant of initials/titles/spacing" but not point values.
TRUST_LAYER_OWNERSHIP: dict[str, int] = {
    "no_name_default": 50,
    "exact_match": 100,
    "partial_match_floor": 40,
    "mismatch": 10,
}

# PLAN §15.6: disabled by default; only affects scoring when explicitly
# enabled in an ACTIVE model version with a documented weight.
TRUST_LAYER_KIMI: dict[str, object] = {
    "anomaly_scoring_enabled": False,
    "weight_within_visual": Decimal("0.30"),
}

# --- Sprint 4: NormalizationEngine (PLAN §15.1, FR-6) -----------------------
#
# Ordered, first-match-wins keyword rules against `raw_description`
# (case-insensitive substring match). `direction` narrows a rule to
# CREDIT/DEBIT rows only; `None` matches either. Sprint 4 gap-fill (§24.11):
# PLAN §7.5/FR-6 names the categories/contexts to enrich but not the exact
# Indonesian bank/e-wallet vocabulary — this is a starting fixture-driven set,
# extended as new statement formats are supported (same spirit as
# `TRUST_LAYER_PROVENANCE_TIERS`). Unmatched rows stay `CategoryEnum.UNKNOWN`
# / `TransactionContextEnum.UNKNOWN` (FR-6 EC: never guessed as income).
NORMALIZATION_CATEGORY_RULES: list[dict[str, object]] = [
    {
        "keywords": ("GAJI", "PAYROLL", "SALARY"),
        "direction": "CREDIT",
        "category": "INCOME",
        "context": "PERSONAL",
        "subcategory": "SALARY",
    },
    {
        "keywords": ("QRIS",),
        "direction": "CREDIT",
        "category": "INCOME",
        "context": "BUSINESS",
        "subcategory": "QRIS_SETTLEMENT",
    },
    {
        "keywords": ("QRIS",),
        "direction": "DEBIT",
        "category": "DISCRETIONARY",
        "context": "PERSONAL",
        "subcategory": "QRIS_PAYMENT",
    },
    {
        "keywords": ("MARKETPLACE", "SHOPEE", "TOKOPEDIA", "SETTLEMENT"),
        "direction": "CREDIT",
        "category": "INCOME",
        "context": "BUSINESS",
        "subcategory": "MARKETPLACE_SETTLEMENT",
    },
    {
        "keywords": ("BIAYA ADM", "ADMIN FEE", "BIAYA ADMIN"),
        "direction": "DEBIT",
        "category": "ESSENTIAL_EXPENSE",
        "context": "PERSONAL",
        "subcategory": "BANK_FEE",
    },
    {
        "keywords": ("BPJS",),
        "direction": "DEBIT",
        "category": "ESSENTIAL_EXPENSE",
        "context": "PERSONAL",
        "subcategory": "INSURANCE",
    },
    {
        "keywords": ("LISTRIK", "PLN", "PDAM", "INTERNET", "WIFI", "TELKOM"),
        "direction": "DEBIT",
        "category": "ESSENTIAL_EXPENSE",
        "context": "PERSONAL",
        "subcategory": "UTILITIES",
    },
    {
        "keywords": ("CICILAN", "ANGSURAN", "KREDIT", "PINJAMAN"),
        "direction": "DEBIT",
        "category": "FINANCIAL_OBLIGATION",
        "context": "PERSONAL",
        "subcategory": "LOAN_INSTALMENT",
    },
    {
        "keywords": ("SUPPLIER", "GROSIR", "STOK", "BELANJA BARANG"),
        "direction": "DEBIT",
        "category": "ESSENTIAL_EXPENSE",
        "context": "BUSINESS",
        "subcategory": "INVENTORY_SUPPLIER",
    },
    {
        "keywords": ("TARIK TUNAI", "ATM WITHDRAWAL", "CASH WITHDRAWAL"),
        "direction": "DEBIT",
        "category": "DISCRETIONARY",
        "context": "PERSONAL",
        "subcategory": "CASH_WITHDRAWAL",
    },
    {
        "keywords": ("SAVING", "TABUNGAN", "DEPOSITO"),
        "direction": "DEBIT",
        "category": "SAVINGS_TRANSFER",
        "context": "PERSONAL",
        "subcategory": "SAVINGS",
    },
]

# Sprint 4 gap-fill (§24.11): FR-6 AC5's internal-transfer detection window
# and AC3's recurring-detection thresholds — PLAN names the signals
# (amount+interval+counterparty similarity) but not the exact bounds.
NORMALIZATION_INTERNAL_TRANSFER: dict[str, int] = {"date_window_days": 1}
NORMALIZATION_RECURRING: dict[str, Decimal | int] = {
    "min_occurrences": 3,
    "amount_variance_ratio": Decimal("0.15"),
    "interval_stddev_days_max": 5,
}

# --- Sprint 4: CashFlowTwinEngine (PLAN §15.1, FR-7) ------------------------
#
# FR-7 EC: "<2 months of data -> Twin flagged LOW_COVERAGE".
CASH_FLOW_TWIN: dict[str, int] = {"low_coverage_min_months": 2}

# --- Sprint 4: RiskEngine (PLAN §5.3, §5.5, FR-8) ---------------------------
#
# Weight split, DSTI thresholds, and cash-flow-ratio thresholds are PLAN
# §5.3's documented numbers. `volatility_scale`/`behaviour_discretionary_scale`
# (how income volatility / discretionary-spending ratio map onto a 0-100
# sub-score) and the model-confidence month thresholds are Sprint 4 gap-fills
# (§24.11) — PLAN names the signals but not the scaling constants.
RISK_WEIGHTS: dict[str, Decimal] = {
    "income_stability": Decimal("0.30"),
    "cash_flow_health": Decimal("0.30"),
    "obligation_load": Decimal("0.25"),
    "behaviour": Decimal("0.15"),
}
# PLAN §5.3: "<=20% excellent, <=35% good, <=45% caution, >45% high".
RISK_DSTI_THRESHOLDS: dict[str, Decimal] = {
    "excellent": Decimal("0.20"),
    "good": Decimal("0.35"),
    "caution": Decimal("0.45"),
}
RISK_DSTI_SCORES: dict[str, int] = {"excellent": 100, "good": 80, "caution": 50, "high": 20}
# PLAN §5.3: ">=0.8 strong, 0.6-0.79 ok, <0.6 weak".
RISK_CASH_FLOW_RATIO_THRESHOLDS: dict[str, Decimal] = {
    "strong": Decimal("0.8"),
    "ok": Decimal("0.6"),
}
# PLAN §5.3: "single-source dependency > 80% -> risk flag (but not
# auto-penalised for predictable seasonality)" -- informational reason code
# only, never a score penalty (§19.4 fairness).
RISK_INCOME_CONCENTRATION_FLAG_THRESHOLD = Decimal("0.8")
RISK_VOLATILITY_SCALE = Decimal("200")
RISK_BEHAVIOUR_DISCRETIONARY_SCALE = Decimal("150")
# PLAN §5.3: "A>=80, B65-79, C50-64, D<50".
RISK_BAND_THRESHOLDS: dict[str, int] = {"a": 80, "b": 65, "c": 50}
# PLAN §5.5/FR-8: "a low-risk result derived from thin data must be shown
# with reduced model confidence -- never high confidence".
RISK_MODEL_CONFIDENCE_MONTHS: dict[str, int] = {
    "min_months_for_high": 6,
    "min_months_for_medium": 2,
}

# --- Sprint 4: SafeBorrowingEngine (PLAN §5.6, §5.7, FR-9) ------------------
#
# `tenor_candidates` and `reference_annual_flat_rate` are PLAN §5.6/§5.7's
# documented numbers (`{6,9,12}`, "24%/year flat" reference). Buffer ratios,
# the DSTI capacity limit, and due-date offsets are Sprint 4 gap-fills
# (§24.11) -- PLAN §5.6 names each buffer/capacity term's *shape*
# (`RequiredLiquidityBuffer`, `DSTICapacity`, ...) but not its constants.
# `dsti_limit` reuses §5.3's "good" DSTI threshold (0.35) as the safe-
# borrowing ceiling, consistent with the same risk vocabulary. `ShockCapacity`
# is intentionally absent -- deferred to Sprint 5 once `ShockEngine` exists
# (see `app/engines/safe_borrowing.py` module docstring).
SAFE_BORROWING: dict[str, object] = {
    "min_absolute_buffer_idr": 500_000,
    "income_buffer_ratio": Decimal("0.5"),
    "essential_buffer_ratio": Decimal("1.0"),
    "volatility_buffer_multiplier": Decimal("1.0"),
    "dsti_limit": Decimal("0.35"),
    "tenor_candidates": (6, 9, 12),
    "reference_annual_flat_rate": Decimal("0.24"),
    "due_date_offset_min_days": 3,
    "due_date_offset_max_days": 7,
    "default_due_date_window": (20, 25),
}

CONFIG: dict[str, object] = {
    "trust_layer": {
        "weights": TRUST_LAYER_WEIGHTS,
        "provenance_tiers": TRUST_LAYER_PROVENANCE_TIERS,
        "band_thresholds": TRUST_LAYER_BAND_THRESHOLDS,
        "completeness_target_months": TRUST_LAYER_COMPLETENESS_TARGET_MONTHS,
        "metadata": TRUST_LAYER_METADATA,
        "visual": TRUST_LAYER_VISUAL,
        "consistency": TRUST_LAYER_CONSISTENCY,
        "ownership": TRUST_LAYER_OWNERSHIP,
        "kimi": TRUST_LAYER_KIMI,
    },
    "normalization": {
        "category_rules": NORMALIZATION_CATEGORY_RULES,
        "internal_transfer": NORMALIZATION_INTERNAL_TRANSFER,
        "recurring": NORMALIZATION_RECURRING,
    },
    "cash_flow_twin": CASH_FLOW_TWIN,
    "risk": {
        "weights": RISK_WEIGHTS,
        "dsti_thresholds": RISK_DSTI_THRESHOLDS,
        "dsti_scores": RISK_DSTI_SCORES,
        "cash_flow_ratio_thresholds": RISK_CASH_FLOW_RATIO_THRESHOLDS,
        "income_concentration_flag_threshold": RISK_INCOME_CONCENTRATION_FLAG_THRESHOLD,
        "volatility_scale": RISK_VOLATILITY_SCALE,
        "behaviour_discretionary_scale": RISK_BEHAVIOUR_DISCRETIONARY_SCALE,
        "band_thresholds": RISK_BAND_THRESHOLDS,
        "model_confidence_months": RISK_MODEL_CONFIDENCE_MONTHS,
    },
    "safe_borrowing": SAFE_BORROWING,
}


def config_hash() -> str:
    canonical = json.dumps(CONFIG, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()
