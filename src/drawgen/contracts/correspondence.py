"""Correspondence between target and reference features (HANDOFF.md section 8.7)."""

from typing import Literal

from pydantic import Field

from drawgen.contracts.common import Contract


class FeaturePair(Contract):
    target_id: str
    reference_id: str
    method: Literal["attribute", "geometry", "pattern", "llm", "human"]
    confidence: float


class Correspondence(Contract):
    schema_: Literal["correspondence/0"] = Field("correspondence/0", alias="schema")
    target_hash: str
    reference_hash: str
    pairs: list[FeaturePair]
    target_only: list[str] = Field(default_factory=list)
    reference_only: list[str] = Field(default_factory=list)
