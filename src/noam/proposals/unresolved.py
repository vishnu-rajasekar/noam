"""Structured unresolved states for A5.1.

The backend never invents a default, a dimension, a jurisdiction, a standard,
a unit, an assumption, or a confidence value. When a request cannot be
honoured, or a recorded fixture itself declares the source insufficient or
incompatible, the intake returns a typed :class:`UnresolvedState` carrying
stable reason codes, the affected non-content reference, and fixed
human-action text.

Nothing in this module contains prompt or source content: ``affected`` is a
field / source identifier and ``human_action`` is a fixed template string.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReasonCode(str, Enum):
    """Why an intake did not produce a proposal package."""

    # --- request / backend resolution ------------------------------------
    UNKNOWN_FIXTURE = "unknown_fixture"
    SOURCE_DIGEST_MISMATCH = "source_digest_mismatch"
    OUTPUT_DIGEST_MISMATCH = "output_digest_mismatch"
    CONTRACT_VERSION_MISMATCH = "contract_version_mismatch"
    BACKEND_VERSION_MISMATCH = "backend_version_mismatch"
    INCOMPATIBLE_INPUT = "incompatible_input"
    MALFORMED_FIXTURE_RECORD = "malformed_fixture_record"
    UNAUTHORISED_FIXTURE_ROOT = "unauthorised_fixture_root"
    # --- recorded source-level unresolved states ------------------------
    MISSING_REQUIRED_SOURCE_INFO = "missing_required_source_info"


# Fixed, content-free guidance. Keyed by reason code so logs can stay
# code-only while a caller can still render an actionable message.
REASON_HUMAN_ACTION: dict[ReasonCode, str] = {
    ReasonCode.UNKNOWN_FIXTURE: (
        "Register the fixture id and its recorded output in the corpus before retrying."
    ),
    ReasonCode.SOURCE_DIGEST_MISMATCH: (
        "Recompute the source SHA-256 and send a request whose expected digest matches."
    ),
    ReasonCode.OUTPUT_DIGEST_MISMATCH: (
        "The recorded output no longer matches its declared digest; re-record the fixture."
    ),
    ReasonCode.CONTRACT_VERSION_MISMATCH: (
        "Use a request that names the contract version this build implements."
    ),
    ReasonCode.BACKEND_VERSION_MISMATCH: (
        "The recorded fixture was produced by a different backend version; re-record it."
    ),
    ReasonCode.INCOMPATIBLE_INPUT: (
        "The request targets a backend or mode this build does not provide; adjust the request."
    ),
    ReasonCode.MALFORMED_FIXTURE_RECORD: (
        "The recorded fixture does not parse against the current contract; re-record it."
    ),
    ReasonCode.UNAUTHORISED_FIXTURE_ROOT: (
        "Point the backend at the authorised A5.1 recorded-fixture root; "
        "study and restricted trees are refused."
    ),
    ReasonCode.MISSING_REQUIRED_SOURCE_INFO: (
        "A human must supply the missing source information; the backend will not infer it."
    ),
}


class UnresolvedItem(BaseModel):
    """One reason an intake is unresolved."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    reason_code: ReasonCode
    affected: str = Field(min_length=1, description="non-content field/source reference")
    human_action: str = Field(min_length=1, description="fixed template guidance, no content")


class UnresolvedState(BaseModel):
    """Typed 'no package' result. ``ok`` is always ``False``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: Literal[False] = False
    contract_version: str = Field(min_length=1)
    backend_id: str = Field(min_length=1)
    items: tuple[UnresolvedItem, ...] = Field(min_length=1)
