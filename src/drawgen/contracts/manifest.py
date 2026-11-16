"""RunManifest (HANDOFF.md section 8.12)."""

from typing import Literal

from pydantic import Field

from drawgen.contracts.common import Contract, Tolerances


class RunInputs(Contract):
    target: str
    reference_model: str
    reference_drawing: str


class RunConfig(Contract):
    backend: str
    pack: str
    rules_only: bool
    tolerances: Tolerances = Field(default_factory=Tolerances)


class Artifact(Contract):
    path: str
    sha256: str


class RunStep(Contract):
    node: str
    started: str  # ISO 8601
    ended: str | None = None
    status: str


class LlmCall(Contract):
    node: str
    model: str
    prompt_hash: str
    response_hash: str


class RunManifest(Contract):
    schema_: Literal["run_manifest/0"] = Field("run_manifest/0", alias="schema")
    run_id: str
    created_at: str  # ISO 8601
    inputs: RunInputs
    config: RunConfig
    artifacts: dict[str, Artifact] = Field(default_factory=dict)
    steps: list[RunStep] = Field(default_factory=list)
    llm_calls: list[LlmCall] = Field(default_factory=list)
