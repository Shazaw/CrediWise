"""Governance-only model configuration bootstrap (PLAN §19.2, T1.7).

Real deterministic-engine weights/thresholds land starting Sprint 3+ as each
engine in PLAN §15 ships. This module exists now only so `model_versions`
has a genuine, hashable configuration source rather than a fabricated hash.
Extend `CONFIG` as engines land; never mutate a released version's meaning —
bump `MODEL_VERSION` instead (PLAN §19.2: "changing any number here = a new
model version").
"""

import hashlib
import json

MODEL_NAME = "crediwise-core"
MODEL_VERSION = "v1"

CONFIG: dict[str, object] = {}


def config_hash() -> str:
    canonical = json.dumps(CONFIG, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()
