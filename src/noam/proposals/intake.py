"""Top-level A5.1 intake: request in, proposal-or-unresolved out.

This is the side-effect-free operation the contract is about. It:

* canonicalises and hashes the request;
* asks the recorded backend to resolve it;
* on success, wraps the recorded package in a :class:`ProposalResponse` with
  the request / source / output digests;
* on any structured failure, returns a typed :class:`UnresolvedState`.

It writes nothing: no study record, no index, no file. It logs only
non-content identifiers, versions, digests, reason codes, and counts -- never
a prompt, a source excerpt, a claim statement, or a full package.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from noam.proposals.backend import RecordedFixtureBackend
from noam.proposals.canonical import canonical_bytes, sha256_hex
from noam.proposals.contracts import ProposalPackage, ProposalRequest, ProposalResponse
from noam.proposals.errors import ProposalError
from noam.proposals.unresolved import (
    REASON_HUMAN_ACTION,
    UnresolvedItem,
    UnresolvedState,
)
from noam.proposals.version import BACKEND_ID, BACKEND_VERSION, CONTRACT_VERSION

_log = logging.getLogger("noam.proposals")


@dataclass(frozen=True)
class ProposalOutcome:
    """Result of :func:`run_proposal_intake`.

    Exactly one of ``response`` / ``unresolved`` is set. ``package_bytes`` is
    the canonical output whose SHA-256 is ``response.output_sha256``.
    """

    ok: bool
    response: ProposalResponse | None = None
    package_bytes: bytes | None = None
    unresolved: UnresolvedState | None = None


def run_proposal_intake(
    request: ProposalRequest, backend: RecordedFixtureBackend
) -> ProposalOutcome:
    """Run one recorded-fixture proposal intake. Never raises for a
    structured backend failure; returns an unresolved outcome instead."""

    request_bytes = canonical_bytes(request)
    request_sha = sha256_hex(request_bytes)

    try:
        resolved = backend.resolve(request)
    except ProposalError as exc:
        state = _unresolved_from_error(exc)
        _log.info(
            "proposal intake unresolved: fixture=%s request_sha=%s reason=%s affected=%s",
            request.fixture_id,
            request_sha,
            exc.reason_code.value,
            exc.affected,
        )
        return ProposalOutcome(ok=False, unresolved=state)

    if isinstance(resolved, UnresolvedState):
        _log.info(
            "proposal intake unresolved (recorded): fixture=%s request_sha=%s reasons=%s",
            request.fixture_id,
            request_sha,
            ",".join(item.reason_code.value for item in resolved.items),
        )
        return ProposalOutcome(ok=False, unresolved=resolved)

    package: ProposalPackage = resolved
    package_bytes = canonical_bytes(package)
    output_sha = sha256_hex(package_bytes)
    response = ProposalResponse(
        contract_version=CONTRACT_VERSION,
        backend_id=BACKEND_ID,
        backend_version=BACKEND_VERSION,
        request_sha256=request_sha,
        source_sha256=request.expected_source_sha256,
        output_sha256=output_sha,
        package=package,
    )
    _log.info(
        "proposal intake ok: fixture=%s request_sha=%s output_sha=%s "
        "sources=%d sourced_facts=%d inferred_facts=%d missing_information=%d "
        "proposed_study_fields=%d proposed_requirements=%d model_hypothesis_present=%s",
        request.fixture_id,
        request_sha,
        output_sha,
        len(package.provenance.sources),
        len(package.sourced_facts),
        len(package.inferred_facts),
        len(package.missing_information),
        len(package.proposed_study_fields),
        len(package.proposed_requirements),
        package.proposed_model_hypothesis.present,
    )
    return ProposalOutcome(ok=True, response=response, package_bytes=package_bytes)


def _unresolved_from_error(exc: ProposalError) -> UnresolvedState:
    return UnresolvedState(
        contract_version=CONTRACT_VERSION,
        backend_id=BACKEND_ID,
        items=(
            UnresolvedItem(
                reason_code=exc.reason_code,
                affected=exc.affected,
                human_action=REASON_HUMAN_ACTION[exc.reason_code],
            ),
        ),
    )
