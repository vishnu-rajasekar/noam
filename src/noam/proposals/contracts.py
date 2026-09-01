"""Typed, strict runtime DTOs for the A5.1 proposal contract.

These are runtime transport objects under ``noam.proposals`` -- deliberately
*not* new ``Study`` / ``Requirement`` / ``ModelHypothesis`` authoring schemas.
They carry proposed content out of a recorded backend with complete
provenance so a human (and the deterministic registry) can decide what, if
anything, becomes an engineering record.

Every model forbids unknown fields and is frozen. Every proposed or factual
claim is fixed at ``status="proposed"`` where a status appears; an inferred
claim stays labelled inferred even when it carries a citation.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from noam.proposals.canonical import quantise_confidence
from noam.proposals.version import BACKEND_ID, BACKEND_VERSION, CONTRACT_VERSION

_HEX64 = r"^[0-9a-f]{64}$"
_LOCATOR = re.compile(r"^(line|lines|para|span|offset):[0-9]+(-[0-9]+)?$")
_PM_REF = re.compile(r"^PM-\d{3}$")

# Confidence is the only non-integer number in the schema. Bound it to the
# closed interval [0, 1] and quantise its representation at the edge so
# serialisation is byte-stable.
Confidence = Annotated[float, Field(ge=0.0, le=1.0), AfterValidator(quantise_confidence)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Citation(_Strict):
    """A machine-checkable pointer into a declared source."""

    source_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)

    @field_validator("locator")
    @classmethod
    def _locator_is_machine_checkable(cls, value: str) -> str:
        if not _LOCATOR.match(value):
            raise ValueError(
                "locator must be '<kind>:<n>[-<n>]' with kind in "
                "line|lines|para|span|offset"
            )
        return value


class Claim(_Strict):
    """A factual statement, categorised sourced vs inferred.

    ``claim_id`` prefix is tied to the category (``SF`` sourced, ``IF``
    inferred) so an inferred claim cannot be silently relabelled by moving
    it between package sections.
    """

    claim_id: str = Field(pattern=r"^(SF|IF)-\d{3}$")
    category: Literal["sourced", "inferred"]
    statement: str = Field(min_length=1)
    citations: tuple[Citation, ...] = Field(min_length=1)
    confidence: Confidence

    @model_validator(mode="after")
    def _prefix_matches_category(self) -> "Claim":
        want = "SF" if self.category == "sourced" else "IF"
        if not self.claim_id.startswith(want):
            raise ValueError(f"claim_id must start with {want!r} for category {self.category!r}")
        return self


class SourceProvenance(_Strict):
    """Provenance for one declared source fixture."""

    source_id: str = Field(min_length=1)
    origin: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    author_or_publisher: str = Field(min_length=1)
    licence: str = Field(min_length=1)
    created_or_retrieved: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    byte_length: int = Field(ge=0)
    sha256: str = Field(pattern=_HEX64)
    redistribution_rationale: str = Field(min_length=1)


class MissingInfoItem(_Strict):
    """Information the source does not provide that a study would need.

    This is a normal part of a *successful* proposal -- distinct from an
    :class:`~noam.proposals.unresolved.UnresolvedState`, which means no
    package could be produced at all. Fields are generic labels and fixed
    guidance, never source content.
    """

    ref: str = Field(pattern=r"^MI-\d{3}$")
    topic: str = Field(min_length=1)
    why_needed: str = Field(min_length=1)
    human_action: str = Field(min_length=1)


class ProposedStudyField(_Strict):
    """A proposed value for one ``Study`` authoring field."""

    ref: str = Field(pattern=r"^PS-\d{3}$")
    field: str = Field(min_length=1)
    value: str = Field(min_length=1)
    category: Literal["sourced", "inferred"]
    citations: tuple[Citation, ...] = Field(min_length=1)
    confidence: Confidence
    status: Literal["proposed"] = "proposed"


class ProposedRequirement(_Strict):
    """A proposed requirement -- never a confirmed one."""

    ref: str = Field(pattern=r"^PR-\d{3}$")
    title: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    category: Literal["sourced", "inferred"]
    citations: tuple[Citation, ...] = Field(min_length=1)
    confidence: Confidence
    status: Literal["proposed"] = "proposed"


class ProposedModelHypothesis(_Strict):
    """A proposed idealisation choice.

    Always present as a section (``present`` tells you whether the fixture
    actually proposed one) so the package shape is stable and an empty
    proposal is still schema-complete. When ``present`` is false every other
    field is empty; when true, purpose / analysis_question / idealisation,
    a stable ``ref`` (``PM-NNN``) and at least one citation are required.

    ``ref`` is the stable identifier for this proposed claim, matching the
    ``PS-`` / ``PR-`` / ``MI-`` / ``SF-`` / ``IF-`` identifiers the other
    sections carry; an absent hypothesis has an empty ``ref``.
    """

    present: bool
    ref: str = ""
    purpose: str = ""
    analysis_question: str = ""
    idealisation: str = ""
    category: Literal["sourced", "inferred", "none"] = "none"
    citations: tuple[Citation, ...] = ()
    confidence: float | None = None
    status: Literal["proposed"] = "proposed"

    @model_validator(mode="after")
    def _present_consistency(self) -> "ProposedModelHypothesis":
        if self.present:
            if not _PM_REF.match(self.ref):
                raise ValueError(
                    "a present proposed_model_hypothesis needs a stable ref 'PM-NNN'"
                )
            if not (self.purpose and self.analysis_question and self.idealisation):
                raise ValueError(
                    "a present proposed_model_hypothesis needs purpose, "
                    "analysis_question and idealisation"
                )
            if not self.citations:
                raise ValueError("a present proposed_model_hypothesis needs >=1 citation")
            if self.category not in ("sourced", "inferred"):
                raise ValueError(
                    "a present proposed_model_hypothesis needs category sourced|inferred"
                )
            if self.confidence is None:
                raise ValueError("a present proposed_model_hypothesis needs a confidence")
            object.__setattr__(self, "confidence", quantise_confidence(self.confidence))
            if not (0.0 <= self.confidence <= 1.0):
                raise ValueError("confidence must be in [0, 1]")
        else:
            if (
                self.ref
                or self.purpose
                or self.analysis_question
                or self.idealisation
                or self.citations
                or self.confidence is not None
                or self.category != "none"
            ):
                raise ValueError("an absent proposed_model_hypothesis must be entirely empty")
        return self


class PackageProvenance(_Strict):
    """Package-level provenance: versions, the fixture id, and every source."""

    contract_version: str = Field(min_length=1)
    backend_id: str = Field(min_length=1)
    backend_version: str = Field(min_length=1)
    fixture_id: str = Field(min_length=1)
    sources: tuple[SourceProvenance, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _source_ids_are_unique(self) -> "PackageProvenance":
        _reject_duplicates([s.source_id for s in self.sources], "provenance source_id")
        return self


class ProposalPackage(_Strict):
    """The structured proposal. All six sections are always present.

    Empty sections are empty collections, never omitted or merged. Every
    claim / proposed item resolves its citations to a declared source, and
    section membership matches each item's declared category.
    """

    status: Literal["proposed"] = "proposed"
    provenance: PackageProvenance
    sourced_facts: tuple[Claim, ...]
    inferred_facts: tuple[Claim, ...]
    missing_information: tuple[MissingInfoItem, ...]
    proposed_study_fields: tuple[ProposedStudyField, ...]
    proposed_requirements: tuple[ProposedRequirement, ...]
    proposed_model_hypothesis: ProposedModelHypothesis

    @model_validator(mode="after")
    def _cross_checks(self) -> "ProposalPackage":
        known_sources = {s.source_id for s in self.provenance.sources}

        for claim in self.sourced_facts:
            if claim.category != "sourced":
                raise ValueError(f"{claim.claim_id} is in sourced_facts but categorised inferred")
        for claim in self.inferred_facts:
            if claim.category != "inferred":
                raise ValueError(f"{claim.claim_id} is in inferred_facts but categorised sourced")

        cited_items: list[tuple[str, tuple[Citation, ...]]] = []
        cited_items += [(c.claim_id, c.citations) for c in self.sourced_facts]
        cited_items += [(c.claim_id, c.citations) for c in self.inferred_facts]
        cited_items += [(p.ref, p.citations) for p in self.proposed_study_fields]
        cited_items += [(p.ref, p.citations) for p in self.proposed_requirements]
        mh = self.proposed_model_hypothesis
        if mh.present:
            cited_items.append((mh.ref, mh.citations))
        for owner, citations in cited_items:
            for citation in citations:
                if citation.source_id not in known_sources:
                    raise ValueError(f"{owner} cites unknown source {citation.source_id!r}")

        _reject_duplicates(
            [c.claim_id for c in self.sourced_facts] + [c.claim_id for c in self.inferred_facts],
            "claim_id",
        )
        _reject_duplicates([p.ref for p in self.proposed_study_fields], "proposed_study_fields ref")
        _reject_duplicates([p.ref for p in self.proposed_requirements], "proposed_requirements ref")
        _reject_duplicates([m.ref for m in self.missing_information], "missing_information ref")

        if self.provenance.contract_version != CONTRACT_VERSION:
            raise ValueError("package provenance names a different contract version")
        if self.provenance.backend_id != BACKEND_ID:
            raise ValueError("package provenance names a different backend id")
        if self.provenance.backend_version != BACKEND_VERSION:
            raise ValueError("package provenance names a different backend version")
        return self


def _reject_duplicates(values: list[str], label: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"duplicate {label}: {value}")
        seen.add(value)


class ProposalRequest(_Strict):
    """A request to produce a proposal from one recorded source fixture.

    It names the contract, the backend, the fixture id, and the source
    digest the caller expects. Nothing here is free text that could steer a
    model -- there is no model.
    """

    contract_version: str = Field(min_length=1)
    backend_id: str = Field(min_length=1)
    fixture_id: str = Field(min_length=1)
    expected_source_sha256: str = Field(pattern=_HEX64)


class ProposalResponse(_Strict):
    """Envelope around a successful package.

    Carries the contract/backend versions, the request digest, the source
    digest, and the output digest (SHA-256 of the canonical package bytes,
    not of this envelope).
    """

    contract_version: str = Field(min_length=1)
    backend_id: str = Field(min_length=1)
    backend_version: str = Field(min_length=1)
    request_sha256: str = Field(pattern=_HEX64)
    source_sha256: str = Field(pattern=_HEX64)
    output_sha256: str = Field(pattern=_HEX64)
    package: ProposalPackage
