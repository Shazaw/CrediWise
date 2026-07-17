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

Sprint 5 adds `shock`/`offer` keys under the same `MODEL_VERSION = "v1"` (same
"net-new, not a mutation" reasoning) plus `safe_borrowing.moderate_shock_income_drop_pct`
(ADR-016). PLAN §5.8/§5.9 name the required scenario battery, scenario
weights, and Safe Offer Score factor weights exactly; numbers PLAN leaves
unspecified (scenario point values, band-adjacent scaling constants, offer
templates) are Sprint 5 gap-fills, called out inline below.
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
# (Sprint 5, ADR-016) reuses the same 20% figure PLAN §5.8 assigns the
# "20% income drop" scenario as its own "moderate shock" -- one constant,
# shared by both `SAFE_BORROWING` below and `SHOCK_INCOME_DROP_SCENARIOS`.
_MODERATE_SHOCK_INCOME_DROP_PCT = Decimal("0.20")

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
    # ADR-016: ShockCapacity, PLAN §5.6's fifth `min(...)` term, is computed
    # here in closed form rather than by calling `ShockEngine` (PLAN §10.1:
    # engines depend on nothing but their own inputs and `model_config`, not
    # on each other). `savings_buffer + average_free_cash_flow - median_income
    # * moderate_shock_income_drop_pct` is the exact instalment ceiling that
    # keeps the "moderate" (20%) income-drop scenario at or above a zero
    # projected balance -- see `app/engines/safe_borrowing.py` module
    # docstring for the derivation. Must equal `shock.MODERATE_SHOCK_KEY`'s
    # weight in `SHOCK_INCOME_DROP_SCENARIOS` below (both reference the same
    # `_MODERATE_SHOCK_INCOME_DROP_PCT` constant, not two independent numbers).
    "moderate_shock_income_drop_pct": _MODERATE_SHOCK_INCOME_DROP_PCT,
}

# --- Sprint 5: ShockEngine (PLAN §5.8, §15.1, FR-10) ------------------------
#
# The three income-drop tiers and their weights, the delayed-income/emergency-
# expense/income-source-loss/weakest-month-replay scenarios and their
# weights, and the STRONG/MODERATE/FRAGILE band thresholds are PLAN §5.8's
# documented numbers (weights sum to 1.00). The emergency-expense amount
# (Rp1,000,000) is PLAN §5.8's own example value, used as the literal default.
# Per-scenario point values (100/50/0 for SURVIVABLE/STRAINED/DEFICIT) are a
# Sprint 5 gap-fill (§24.11) -- PLAN §5.8 says "full points/half points/zero
# points" but not the point scale itself; 100/50/0 is the natural choice given
# the 0-100 resilience score.
SHOCK_INCOME_DROP_SCENARIOS: dict[str, Decimal] = {
    "10": Decimal("0.10"),
    "20": _MODERATE_SHOCK_INCOME_DROP_PCT,
    "30": Decimal("0.30"),
}
SHOCK_MODERATE_KEY = "20"
SHOCK_EMERGENCY_EXPENSE_AMOUNT_IDR = 1_000_000
SHOCK_SCENARIO_WEIGHTS: dict[str, Decimal] = {
    "INCOME_DROP_10": Decimal("0.10"),
    "INCOME_DROP_20": Decimal("0.20"),
    "INCOME_DROP_30": Decimal("0.10"),
    "DELAYED_INCOME": Decimal("0.15"),
    "EMERGENCY_EXPENSE": Decimal("0.15"),
    "INCOME_SOURCE_LOSS": Decimal("0.10"),
    "WEAKEST_MONTH_REPLAY": Decimal("0.20"),
}
SHOCK_RESILIENCE_BAND_THRESHOLDS: dict[str, int] = {"strong": 75, "moderate": 50}
SHOCK_SCENARIO_POINTS: dict[str, int] = {"survivable": 100, "strained": 50, "deficit": 0}

# --- Sprint 5: OfferEngine (PLAN §5.9, §15.1, FR-11) ------------------------
#
# Factor weights and SAFE/CAUTION/UNSAFE band thresholds are PLAN §5.9's
# documented numbers (weights sum to 1.00). Provider-verification sub-scores,
# the refinancing-dependency buffer ratio, timing-fit tolerance, and cost/
# affordability scaling constants are Sprint 5 gap-fills (§24.11) -- PLAN
# §5.9 names each factor's *signal* but not its point scale. `templates` are
# the three deterministic simulated-offer shapes `POST /assessments/{id}/offers`
# seeds against the seeded `lenders` catalog (PLAN §7.10/FR-11) -- not PLAN
# numbers, an MVP demo fixture analogous to `NORMALIZATION_CATEGORY_RULES`.
OFFER_WEIGHTS: dict[str, Decimal] = {
    "instalment_affordability": Decimal("0.20"),
    "within_safe_principal": Decimal("0.15"),
    "shock_survivability": Decimal("0.20"),
    "total_cost": Decimal("0.15"),
    "fee_transparency": Decimal("0.10"),
    "timing_fit": Decimal("0.05"),
    "refinancing_dependency": Decimal("0.10"),
    "provider_verification": Decimal("0.05"),
}
OFFER_BAND_THRESHOLDS: dict[str, int] = {"safe": 75, "caution": 50}
OFFER_PROVIDER_VERIFICATION_SCORES: dict[str, int] = {
    "REGULATED": 100,
    "SIMULATED_REGULATED_PROVIDER": 70,
    "UNLISTED": 40,
}
OFFER_REFINANCING_DEPENDENCY_BUFFER_RATIO = Decimal("0.5")
OFFER_TIMING_FIT_TOLERANCE_DAYS = 3
OFFER_COST_PENALTY_SCALE = Decimal("150")
OFFER_AFFORDABILITY_PENALTY_SCALE = Decimal("100")
OFFER_TEMPLATES: list[dict[str, object]] = [
    {
        "key": "SAFE_ALIGNED",
        "principal_ratio": Decimal("1.0"),
        "tenor_months": None,
        "nominal_rate": Decimal("0.24"),
        "upfront_fee_ratio": Decimal("0.0"),
        "admin_fee": 0,
        "amortization_method": "FLAT",
        "due_date_offset_days": 0,
        "late_penalty_terms": {
            "rate_pct": 2,
            "description": "2% of the overdue instalment per month late",
        },
    },
    {
        "key": "FAST_CASH",
        "principal_ratio": Decimal("1.0"),
        "tenor_months": 6,
        "nominal_rate": Decimal("0.36"),
        "upfront_fee_ratio": Decimal("0.02"),
        "admin_fee": 50_000,
        "amortization_method": "REDUCING_BALANCE",
        "due_date_offset_days": 10,
        "late_penalty_terms": {
            "rate_pct": 5,
            "description": "5% of the overdue instalment per month late",
        },
    },
    {
        "key": "EXTENDED_TENOR",
        "principal_ratio": Decimal("1.2"),
        "tenor_months": 12,
        "nominal_rate": Decimal("0.30"),
        "upfront_fee_ratio": Decimal("0.03"),
        "admin_fee": 0,
        "amortization_method": "FLAT",
        "due_date_offset_days": -5,
        # Intentionally omitted -- FR-11 EC: "offer missing fee disclosure ->
        # transparency penalty + warning" (this template exercises that path).
        "late_penalty_terms": None,
    },
]

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
    "shock": {
        "income_drop_scenarios": SHOCK_INCOME_DROP_SCENARIOS,
        "moderate_shock_key": SHOCK_MODERATE_KEY,
        "emergency_expense_amount": SHOCK_EMERGENCY_EXPENSE_AMOUNT_IDR,
        "scenario_weights": SHOCK_SCENARIO_WEIGHTS,
        "resilience_band_thresholds": SHOCK_RESILIENCE_BAND_THRESHOLDS,
        "scenario_points": SHOCK_SCENARIO_POINTS,
    },
    "offer": {
        "weights": OFFER_WEIGHTS,
        "band_thresholds": OFFER_BAND_THRESHOLDS,
        "provider_verification_scores": OFFER_PROVIDER_VERIFICATION_SCORES,
        "refinancing_dependency_buffer_ratio": OFFER_REFINANCING_DEPENDENCY_BUFFER_RATIO,
        "timing_fit_tolerance_days": OFFER_TIMING_FIT_TOLERANCE_DAYS,
        "cost_penalty_scale": OFFER_COST_PENALTY_SCALE,
        "affordability_penalty_scale": OFFER_AFFORDABILITY_PENALTY_SCALE,
        "reference_annual_flat_rate": SAFE_BORROWING["reference_annual_flat_rate"],
        "templates": OFFER_TEMPLATES,
    },
}


def config_hash() -> str:
    canonical = json.dumps(CONFIG, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()
