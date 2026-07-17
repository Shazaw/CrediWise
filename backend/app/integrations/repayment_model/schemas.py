"""Strict artifact and prediction contracts for local linear inference."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PreprocessingArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_order: list[str]
    clip_lower: list[Decimal]
    clip_upper: list[Decimal]
    centers: list[Decimal]
    scales: list[Decimal]

    @model_validator(mode="after")
    def aligned(self) -> PreprocessingArtifact:
        width = len(self.feature_order)
        if width == 0 or any(
            len(values) != width
            for values in (self.clip_lower, self.clip_upper, self.centers, self.scales)
        ):
            raise ValueError("Artifact preprocessing arrays are not aligned")
        if any(scale <= 0 for scale in self.scales):
            raise ValueError("Artifact scales must be positive")
        return self


class LinearArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intercept: Decimal
    coefficients: list[Decimal]
    l2_penalty: Decimal = Field(ge=0)


class CalibrationArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: str
    intercept: Decimal
    slope: Decimal


class SupportArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum_months: int = Field(ge=1)
    training_rows: int = Field(gt=0)
    calibration_rows: int = Field(gt=0)
    test_rows: int = Field(gt=0)
    earliest_index_date: str
    latest_index_date: str
    geographic_scope: str


class RepaymentArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_format: str
    model_name: str
    model_version: str
    target_version: str
    feature_schema_version: str
    feature_schema_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    training_dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    training_source: str
    deployment_mode: str
    preprocessing: PreprocessingArtifact
    linear_model: LinearArtifact
    calibration: CalibrationArtifact
    support: SupportArtifact
    metrics: dict[str, dict[str, Decimal | int]]

    @model_validator(mode="after")
    def validate_contract(self) -> RepaymentArtifact:
        if self.artifact_format != "crediwise.linear_probability.v1":
            raise ValueError("Unsupported repayment artifact format")
        if self.calibration.method != "PLATT":
            raise ValueError("Unsupported calibration method")
        if len(self.linear_model.coefficients) != len(self.preprocessing.feature_order):
            raise ValueError("Artifact coefficient count does not match feature order")
        return self


class ModelContribution(BaseModel):
    feature: str
    contribution: Decimal
    reason_code: str


class RepaymentModelOutput(BaseModel):
    raw_probability: Decimal = Field(ge=0, le=1)
    calibrated_probability: Decimal = Field(ge=0, le=1)
    contributions: list[ModelContribution]
    out_of_domain_features: list[str]
