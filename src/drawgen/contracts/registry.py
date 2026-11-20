"""The list of contracts that are exported to schemas/ and round-trip tested."""

from drawgen.contracts.candidate_set import CandidateSet
from drawgen.contracts.common import Contract
from drawgen.contracts.convention_profile import ConventionProfile
from drawgen.contracts.correspondence import Correspondence
from drawgen.contracts.drawing_graph import DrawingGraph
from drawgen.contracts.drawing_plan import DrawingPlan, PlanSelection
from drawgen.contracts.execution import ExecutionJob, ExecutionReport
from drawgen.contracts.feature_graph import FeatureGraph
from drawgen.contracts.findings import Findings
from drawgen.contracts.live import Selection, SessionContext
from drawgen.contracts.manifest import RunManifest
from drawgen.contracts.operation_plan import OperationPlan, PipelineResult
from drawgen.contracts.raw_drawing import RawDrawing
from drawgen.contracts.raw_model import RawModel
from drawgen.contracts.worker import (
    ExportResult,
    MeasureResults,
    PingResult,
    WorkerJob,
    WorkerStatus,
)

# Contracts that carry a `schema` string, keyed by its name part.
VERSIONED: dict[str, type[Contract]] = {
    "raw_model": RawModel,
    "raw_drawing": RawDrawing,
    "feature_graph": FeatureGraph,
    "drawing_graph": DrawingGraph,
    "convention_profile": ConventionProfile,
    "correspondence": Correspondence,
    "candidate_set": CandidateSet,
    "drawing_plan": DrawingPlan,
    "plan_selection": PlanSelection,
    "execution_job": ExecutionJob,
    "execution_report": ExecutionReport,
    "findings": Findings,
    "run_manifest": RunManifest,
    "session_context": SessionContext,
    "selection": Selection,
    "operation_plan": OperationPlan,
    "pipeline_result": PipelineResult,
}

# Worker protocol messages, versioned by the `protocol` field of job.json.
PROTOCOL: dict[str, type[Contract]] = {
    "worker_job": WorkerJob,
    "worker_status": WorkerStatus,
    "ping_result": PingResult,
    "measure_results": MeasureResults,
    "export_result": ExportResult,
}

ALL: dict[str, type[Contract]] = {**VERSIONED, **PROTOCOL}
