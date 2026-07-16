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
    }
}


def config_hash() -> str:
    canonical = json.dumps(CONFIG, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()
