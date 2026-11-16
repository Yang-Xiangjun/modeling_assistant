"""FeatureGraph (HANDOFF.md section 8.4). Coordinates are in the part frame."""

from typing import Literal

from pydantic import Field

from drawgen.contracts.common import Contract, Fingerprint, ParamValue, Vec3

FeatureType = Literal[
    "plane",
    "hole",
    "hole_pattern",
    "boss",
    "pocket",
    "slot",
    "outline",
    "body",
    "component",
    "component_group",
    "envelope",
]
RelationType = Literal[
    "coaxial", "coplanar", "parallel", "pattern_member", "mounted_on", "adjacent"
]


class Frame(Contract):
    origin: Vec3
    x: Vec3
    y: Vec3
    z: Vec3
    basis: str  # how the frame was derived


class Feature(Contract):
    id: str
    type: FeatureType
    role: str | None = None  # namespaced by the pack that assigned it
    role_source: Literal["rule", "attribute", "llm", "human"] | None = None
    role_confidence: float | None = None
    params: dict[str, ParamValue] = Field(default_factory=dict)
    fingerprints: list[Fingerprint] = Field(default_factory=list)
    component_id: str | None = None
    members: list[str] = Field(default_factory=list)  # feature ids
    attributes: dict[str, str] = Field(default_factory=dict)


class Relation(Contract):
    type: RelationType
    a: str
    b: str
    params: dict[str, ParamValue] = Field(default_factory=dict)


class FeatureGraph(Contract):
    schema_: Literal["feature_graph/0"] = Field("feature_graph/0", alias="schema")
    model_hash: str
    pack: str
    part_class: str
    frame: Frame
    features: list[Feature]
    relations: list[Relation] = Field(default_factory=list)
