"""A5.1 -- Recorded-Fixture Local Proposal Intake (see ROADMAP.md Phase A.5).

This package is a *contract proof*, not a model integration. It defines the
runtime request / response / provenance DTOs a future local-model backend
would have to satisfy, plus a literal recorded-fixture backend that only
resolves declared fixture inputs (by id and digest) to recorded outputs.

Deliberate non-goals (enforced by tests, not just prose):

* no live model, emulation, network, socket, or subprocess inference -- the
  backend is pure file lookup + digest verification;
* no engineering authority -- every produced record and claim is fixed at
  ``status="proposed"``; confidence is evidence metadata, never approval;
* no writes to the study registry or any ``src/noam/models`` authoring schema;
* no raw prompt or source/corpus text in logs, exceptions, or telemetry.

The recorded backend demonstrates only the interface and trust contract. It
says nothing about model quality, numerical/physics correctness, standards
applicability, or review status.
"""

from noam.proposals.backend import (
    FIXTURE_ROOT_MARKER_NAME,
    RecordedFixtureBackend,
    fixture_root_marker_bytes,
)
from noam.proposals.canonical import canonical_bytes, canonical_json, sha256_hex
from noam.proposals.contracts import (
    Citation,
    Claim,
    MissingInfoItem,
    PackageProvenance,
    ProposalPackage,
    ProposalRequest,
    ProposalResponse,
    ProposedModelHypothesis,
    ProposedRequirement,
    ProposedStudyField,
    SourceProvenance,
)
from noam.proposals.errors import ProposalError
from noam.proposals.intake import ProposalOutcome, run_proposal_intake
from noam.proposals.unresolved import (
    REASON_HUMAN_ACTION,
    ReasonCode,
    UnresolvedItem,
    UnresolvedState,
)
from noam.proposals.version import BACKEND_ID, BACKEND_VERSION, CONTRACT_VERSION

__all__ = [
    "BACKEND_ID",
    "BACKEND_VERSION",
    "CONTRACT_VERSION",
    "FIXTURE_ROOT_MARKER_NAME",
    "Citation",
    "Claim",
    "MissingInfoItem",
    "PackageProvenance",
    "ProposalError",
    "ProposalOutcome",
    "ProposalPackage",
    "ProposalRequest",
    "ProposalResponse",
    "ProposedModelHypothesis",
    "ProposedRequirement",
    "ProposedStudyField",
    "REASON_HUMAN_ACTION",
    "ReasonCode",
    "RecordedFixtureBackend",
    "SourceProvenance",
    "UnresolvedItem",
    "UnresolvedState",
    "canonical_bytes",
    "canonical_json",
    "fixture_root_marker_bytes",
    "run_proposal_intake",
    "sha256_hex",
]
