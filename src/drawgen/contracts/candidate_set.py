"""CandidateSet (HANDOFF.md section 8.8).

``expected_value`` is the only place a dimension value is stored before
execution. Deterministic code computes it; an LLM never does (NFR-02).
"""

from typing import Literal

from pydantic import Field

from drawgen.contracts.common import (
    Contract,
    DimDirection,
    DimKind,
    FeatureRef,
    FrameDirection,
    ViewKind,
)


class ViewCandidate(Contract):
    id: str
    kind: ViewKind
    direction_in_frame: FrameDirection | None
    parent_id: str | None = None
    scale_options: list[float]
    rule_id: str


class DimensionCandidate(Contract):
    id: str
    role_signature: str
    dim_kind: DimKind
    direction: DimDirection | None
    feature_refs: list[FeatureRef]
    view_ids: list[str]  # view candidates in which it is visible and true length
    expected_value: float
    required: bool
    rule_id: str
    source: Literal["measured"] = "measured"


class CandidateSet(Contract):
    schema_: Literal["candidate_set/0"] = Field("candidate_set/0", alias="schema")
    target_hash: str
    views: list[ViewCandidate]
    dimensions: list[DimensionCandidate]
