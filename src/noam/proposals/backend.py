"""The A5.1 recorded-fixture backend.

This is a *literal* recorded backend: given a request, it resolves a declared
fixture id to a recorded artefact on disk, verifies every digest and version,
and returns either the recorded :class:`ProposalPackage` or the recorded
:class:`UnresolvedState`. It has no heuristic, stochastic, generative,
network, or subprocess behaviour and imports no client library. If anything
fails to line up it raises a structured :class:`ProposalError`; it never
falls back to an invented result.

Fixture layout under ``root``::

    .a5_1-fixture-root              marker proving the tree is an authorised
                                   A5.1 recorded-fixture root
    corpus/<source_file>           raw source bytes (hashed verbatim)
    recorded/<id>.meta.json        versions, digests, kind, source pointer
    recorded/<id>.request.json     the canonical recorded request bytes
    recorded/<id>.package.json     canonical package bytes    (kind="package")
    recorded/<id>.unresolved.json  canonical unresolved bytes (kind="unresolved")

Trust boundary (Gate 2 criteria 5, 8, 11; Codex round-1 findings 1-4):

* the fixture root must resolve to an explicitly marked A5.1 fixture tree;
  ``studies/`` and ``knowledge/restricted`` trees are refused outright;
* every file read must stay beneath ``corpus/`` or ``recorded/`` after path
  resolution, and no path component may be a symlink;
* the recorded ``request.json`` bytes, their digest, their canonical form and
  their equality with the incoming request are all verified;
* fixture metadata is validated field-by-field against a strict typed model,
  so a malformed record is always a structured failure, never a traceback;
* the recorded package must declare exactly the one source the backend
  verified (id, digest and byte length), with no duplicate, extra or missing
  provenance entry.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from noam.proposals.canonical import canonical_bytes, canonical_json, sha256_hex
from noam.proposals.contracts import ProposalPackage, ProposalRequest
from noam.proposals.errors import ProposalError
from noam.proposals.unresolved import ReasonCode, UnresolvedState
from noam.proposals.version import BACKEND_ID, BACKEND_VERSION, CONTRACT_VERSION

_SAFE_ID_PATTERN = r"^[a-z0-9][a-z0-9-]*$"
_SAFE_FILENAME_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
_HEX64_PATTERN = r"^[0-9a-f]{64}$"

_SAFE_ID = re.compile(_SAFE_ID_PATTERN)

# Directory names that must never be used as a fixture root, even if they
# happen to contain a well-formed corpus. Matched against resolved path
# components so a nested ``studies/S001.../`` or ``knowledge/restricted/``
# tree is refused before any file is opened.
_FORBIDDEN_ROOT_COMPONENTS = frozenset({"studies", "restricted"})

# A tree is an authorised A5.1 fixture root only if it carries this marker
# file (a regular file, not a symlink) with exactly these bytes.
FIXTURE_ROOT_MARKER_NAME = ".a5_1-fixture-root"


def fixture_root_marker_bytes() -> bytes:
    """Canonical bytes the fixture-root marker file must contain."""

    return canonical_json(
        {"a5_1_recorded_fixture_root": True, "contract_version": CONTRACT_VERSION}
    ).encode("utf-8")


class _FixtureMeta(BaseModel):
    """Strict, typed contract for a ``recorded/<id>.meta.json`` record.

    Every field is validated in strict mode: a wrong type, a bad pattern, an
    unknown key or a missing key is a :class:`pydantic.ValidationError`, which
    the backend converts into ``MALFORMED_FIXTURE_RECORD``. No value ever
    reaches a bare dictionary lookup untyped.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    fixture_id: str = Field(pattern=_SAFE_ID_PATTERN)
    kind: Literal["package", "unresolved"]
    contract_version: str = Field(min_length=1)
    backend_id: str = Field(min_length=1)
    backend_version: str = Field(min_length=1)
    source_id: str = Field(pattern=_SAFE_ID_PATTERN)
    source_file: str = Field(pattern=_SAFE_FILENAME_PATTERN)
    source_sha256: str = Field(pattern=_HEX64_PATTERN)
    source_byte_length: int = Field(ge=0)
    request_sha256: str = Field(pattern=_HEX64_PATTERN)
    output_sha256: str = Field(pattern=_HEX64_PATTERN)


class RecordedFixtureBackend:
    """Resolves declared fixture inputs to recorded outputs. Nothing else."""

    def __init__(self, root: Path) -> None:
        # Stored unresolved; the authorised, canonical root is established on
        # every ``resolve`` call so a structured failure (not a constructor
        # exception) is returned for an unauthorised tree.
        self._root_arg = Path(root)
        self._root: Path | None = None

    # -- public ---------------------------------------------------------------

    def resolve(self, request: ProposalRequest) -> ProposalPackage | UnresolvedState:
        """Return the recorded package or unresolved state for ``request``.

        Raises :class:`ProposalError` (with a stable reason code) for an
        unauthorised fixture root, an unknown fixture, a digest mismatch, a
        version mismatch, a recorded-request mismatch, or a malformed fixture
        record.
        """

        self._root = self._authorised_root()

        self._check_request_versions(request)
        meta = self._load_meta(request.fixture_id)
        self._check_fixture_versions(meta)

        source_bytes = self._read_source(meta)
        actual_source_sha = sha256_hex(source_bytes)
        if actual_source_sha != meta.source_sha256:
            raise ProposalError(ReasonCode.MALFORMED_FIXTURE_RECORD, "fixture.source_sha256")
        if len(source_bytes) != meta.source_byte_length:
            raise ProposalError(
                ReasonCode.MALFORMED_FIXTURE_RECORD, "fixture.source_byte_length"
            )
        if request.expected_source_sha256 != actual_source_sha:
            raise ProposalError(
                ReasonCode.SOURCE_DIGEST_MISMATCH, "request.expected_source_sha256"
            )

        self._verify_recorded_request(request, meta)

        if meta.kind == "package":
            return self._load_package(meta, actual_source_sha)
        return self._load_unresolved(meta)

    # -- fixture-root authorisation ---------------------------------------

    def _authorised_root(self) -> Path:
        try:
            resolved = self._root_arg.resolve()
        except OSError:
            raise ProposalError(
                ReasonCode.UNAUTHORISED_FIXTURE_ROOT, "fixture.root"
            ) from None

        if _FORBIDDEN_ROOT_COMPONENTS.intersection(resolved.parts):
            raise ProposalError(ReasonCode.UNAUTHORISED_FIXTURE_ROOT, "fixture.root")

        marker = resolved / FIXTURE_ROOT_MARKER_NAME
        if marker.is_symlink() or not marker.is_file():
            raise ProposalError(ReasonCode.UNAUTHORISED_FIXTURE_ROOT, "fixture.root")
        try:
            content = marker.read_bytes()
        except OSError:
            raise ProposalError(
                ReasonCode.UNAUTHORISED_FIXTURE_ROOT, "fixture.root"
            ) from None
        if content != fixture_root_marker_bytes():
            raise ProposalError(ReasonCode.UNAUTHORISED_FIXTURE_ROOT, "fixture.root")

        for subdir in ("corpus", "recorded"):
            child = resolved / subdir
            if child.is_symlink():
                raise ProposalError(
                    ReasonCode.MALFORMED_FIXTURE_RECORD, f"fixture.{subdir}"
                )
            if not child.is_dir():
                raise ProposalError(
                    ReasonCode.UNAUTHORISED_FIXTURE_ROOT, "fixture.root"
                )
        return resolved

    def _safe_path(self, subdir: str, name: str) -> Path:
        """Join ``subdir/name`` under the authorised root, rejecting any
        symlink component or resolved-path escape."""

        assert self._root is not None  # set by resolve() before any use
        base = self._root / subdir
        path = base / name
        for candidate in (base, path):
            if candidate.is_symlink():
                raise ProposalError(
                    ReasonCode.MALFORMED_FIXTURE_RECORD, f"fixture.{subdir}.symlink"
                )
        resolved = path.resolve()
        if resolved != path or self._root not in resolved.parents:
            raise ProposalError(
                ReasonCode.MALFORMED_FIXTURE_RECORD, f"fixture.{subdir}.escape"
            )
        return path

    # -- steps --------------------------------------------------------------

    def _check_request_versions(self, request: ProposalRequest) -> None:
        if request.contract_version != CONTRACT_VERSION:
            raise ProposalError(
                ReasonCode.CONTRACT_VERSION_MISMATCH, "request.contract_version"
            )
        if request.backend_id != BACKEND_ID:
            # A request for any other backend (e.g. a live model) is refused
            # here -- there is no other backend to fall through to.
            raise ProposalError(ReasonCode.INCOMPATIBLE_INPUT, "request.backend_id")

    def _check_fixture_versions(self, meta: _FixtureMeta) -> None:
        if meta.contract_version != CONTRACT_VERSION:
            raise ProposalError(
                ReasonCode.CONTRACT_VERSION_MISMATCH, "fixture.contract_version"
            )
        if meta.backend_id != BACKEND_ID:
            raise ProposalError(ReasonCode.MALFORMED_FIXTURE_RECORD, "fixture.backend_id")
        if meta.backend_version != BACKEND_VERSION:
            raise ProposalError(
                ReasonCode.BACKEND_VERSION_MISMATCH, "fixture.backend_version"
            )

    def _load_meta(self, fixture_id: str) -> _FixtureMeta:
        if not _SAFE_ID.match(fixture_id):
            raise ProposalError(ReasonCode.UNKNOWN_FIXTURE, "request.fixture_id")
        meta_path = self._safe_path("recorded", f"{fixture_id}.meta.json")
        if not meta_path.is_file():
            raise ProposalError(ReasonCode.UNKNOWN_FIXTURE, "request.fixture_id")
        try:
            data = json.loads(meta_path.read_bytes())
        except (OSError, ValueError):
            raise ProposalError(
                ReasonCode.MALFORMED_FIXTURE_RECORD, "fixture.meta"
            ) from None
        try:
            meta = _FixtureMeta.model_validate(data)
        except ValidationError:
            raise ProposalError(
                ReasonCode.MALFORMED_FIXTURE_RECORD, "fixture.meta"
            ) from None
        if meta.fixture_id != fixture_id:
            raise ProposalError(ReasonCode.MALFORMED_FIXTURE_RECORD, "fixture.fixture_id")
        return meta

    def _read_source(self, meta: _FixtureMeta) -> bytes:
        path = self._safe_path("corpus", meta.source_file)
        try:
            return path.read_bytes()
        except OSError:
            raise ProposalError(
                ReasonCode.MALFORMED_FIXTURE_RECORD, "fixture.source_file"
            ) from None

    def _verify_recorded_request(
        self, request: ProposalRequest, meta: _FixtureMeta
    ) -> None:
        """Verify the adjacent recorded request: its digest, its canonical
        form, and its exact equality with the incoming (already validated)
        request. This is what makes ``meta.request_sha256`` load-bearing."""

        live_bytes = canonical_bytes(request)
        path = self._safe_path("recorded", f"{meta.fixture_id}.request.json")
        try:
            recorded = path.read_bytes()
        except OSError:
            raise ProposalError(
                ReasonCode.MALFORMED_FIXTURE_RECORD, "fixture.request"
            ) from None
        if sha256_hex(recorded) != meta.request_sha256:
            raise ProposalError(
                ReasonCode.MALFORMED_FIXTURE_RECORD, "fixture.request_sha256"
            )
        try:
            parsed = ProposalRequest.model_validate_json(recorded)
        except ValidationError:
            raise ProposalError(
                ReasonCode.MALFORMED_FIXTURE_RECORD, "fixture.request"
            ) from None
        if canonical_bytes(parsed) != recorded:
            raise ProposalError(
                ReasonCode.MALFORMED_FIXTURE_RECORD, "fixture.request.noncanonical"
            )
        if live_bytes != recorded:
            raise ProposalError(
                ReasonCode.MALFORMED_FIXTURE_RECORD, "fixture.request.mismatch"
            )

    def _load_recorded_bytes(self, meta: _FixtureMeta, suffix: str) -> bytes:
        path = self._safe_path("recorded", f"{meta.fixture_id}.{suffix}")
        try:
            raw = path.read_bytes()
        except OSError:
            raise ProposalError(
                ReasonCode.MALFORMED_FIXTURE_RECORD, f"fixture.{suffix}"
            ) from None
        if sha256_hex(raw) != meta.output_sha256:
            raise ProposalError(ReasonCode.OUTPUT_DIGEST_MISMATCH, f"fixture.{suffix}")
        return raw

    def _load_package(self, meta: _FixtureMeta, source_sha: str) -> ProposalPackage:
        raw = self._load_recorded_bytes(meta, "package.json")
        try:
            package = ProposalPackage.model_validate_json(raw)
        except ValidationError:
            raise ProposalError(
                ReasonCode.MALFORMED_FIXTURE_RECORD, "fixture.package"
            ) from None
        if canonical_bytes(package) != raw:
            raise ProposalError(
                ReasonCode.MALFORMED_FIXTURE_RECORD, "fixture.package.noncanonical"
            )
        if package.provenance.fixture_id != meta.fixture_id:
            raise ProposalError(
                ReasonCode.MALFORMED_FIXTURE_RECORD, "fixture.package.fixture_id"
            )
        # One-to-one: the package must declare exactly the single source the
        # backend actually read and verified -- no duplicate, extra, or
        # missing provenance entry.
        sources = package.provenance.sources
        if len(sources) != 1 or sources[0].source_id != meta.source_id:
            raise ProposalError(
                ReasonCode.MALFORMED_FIXTURE_RECORD, "fixture.package.sources"
            )
        if sources[0].sha256 != source_sha or sources[0].byte_length != meta.source_byte_length:
            raise ProposalError(
                ReasonCode.MALFORMED_FIXTURE_RECORD, "fixture.package.source_digest"
            )
        return package

    def _load_unresolved(self, meta: _FixtureMeta) -> UnresolvedState:
        raw = self._load_recorded_bytes(meta, "unresolved.json")
        try:
            state = UnresolvedState.model_validate_json(raw)
        except ValidationError:
            raise ProposalError(
                ReasonCode.MALFORMED_FIXTURE_RECORD, "fixture.unresolved"
            ) from None
        if canonical_bytes(state) != raw:
            raise ProposalError(
                ReasonCode.MALFORMED_FIXTURE_RECORD, "fixture.unresolved.noncanonical"
            )
        if state.contract_version != CONTRACT_VERSION or state.backend_id != BACKEND_ID:
            raise ProposalError(
                ReasonCode.MALFORMED_FIXTURE_RECORD, "fixture.unresolved.version"
            )
        return state
