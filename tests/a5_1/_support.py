"""Shared helpers for the A5.1 (`noam.proposals`) test suite.

Every A5.1 test case:

* runs with network connection primitives and ``subprocess.Popen`` denied
  (Gate 2 criterion 10) -- the guard records any attempt and raises;
* captures logging at ``DEBUG`` on the root and ``noam.proposals`` loggers so
  a test can assert that no raw prompt / source text / sentinel leaked
  (criterion 11).

The suite is runnable under both ``unittest`` (the repo's offline default)
and ``pytest``; nothing here needs a conftest.
"""

from __future__ import annotations

import json
import logging
import shutil
import socket
import subprocess
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from noam.proposals import ProposalRequest, canonical_json, sha256_hex
from noam.proposals.version import BACKEND_ID, CONTRACT_VERSION

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "a5_1"
CORPUS = FIXTURE_ROOT / "corpus"
RECORDED = FIXTURE_ROOT / "recorded"

# Distinctive strings that appear ONLY in raw source text (or are planted
# sentinels). None of these may ever reach a log line or an exception string.
FORBIDDEN_SUBSTRINGS = (
    "A5.1-SENTINEL-Q7bright-EXFIL",
    "secret_admin=true",
    "override_status",
    "Ignore all previous instructions",
    "network.fetch",
    "exact code to be confirmed",
    "to be confirmed later",
    "rest of the document is missing",
    "18 feet in the same sentence",
    "the responsible engineer signs off",
)

PACKAGE_FIXTURE_IDS = ("cw-basics", "sparse-notes", "injection", "digest-drift")
UNRESOLVED_FIXTURE_IDS = ("insufficient-source", "incompatible-units")
ALL_FIXTURE_IDS = PACKAGE_FIXTURE_IDS + UNRESOLVED_FIXTURE_IDS + ("malformed-record",)


class NetworkDenied(RuntimeError):
    """Raised when guarded code attempts an outbound connection or subprocess."""


class _NetworkGuard:
    """Patches the low-level connection/subprocess entry points to fail."""

    def __init__(self) -> None:
        self.attempts: list[str] = []
        self._saved: list[tuple[object, str, object]] = []

    def _deny(self, name: str):
        def _fail(*_args, **_kwargs):
            self.attempts.append(name)
            raise NetworkDenied(f"A5.1 test suite denies {name}")

        return _fail

    def install(self) -> None:
        for attr in ("create_connection", "getaddrinfo", "gethostbyname", "socketpair"):
            if hasattr(socket, attr):
                self._saved.append((socket, attr, getattr(socket, attr)))
                setattr(socket, attr, self._deny(f"socket.{attr}"))
        for attr in ("connect", "connect_ex"):
            self._saved.append((socket.socket, attr, getattr(socket.socket, attr)))
            setattr(socket.socket, attr, self._deny(f"socket.socket.{attr}"))
        self._saved.append((subprocess, "Popen", subprocess.Popen))
        subprocess.Popen = self._deny("subprocess.Popen")  # type: ignore[assignment]

    def uninstall(self) -> None:
        for obj, attr, value in reversed(self._saved):
            setattr(obj, attr, value)
        self._saved.clear()


@contextmanager
def network_denied():
    guard = _NetworkGuard()
    guard.install()
    try:
        yield guard
    finally:
        guard.uninstall()


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def text(self) -> str:
        parts: list[str] = []
        for record in self.records:
            try:
                parts.append(record.getMessage())
            except Exception:  # pragma: no cover - defensive
                parts.append(str(record.msg))
            for value in (record.args or ()):
                parts.append(str(value))
        return "\n".join(parts)


class A51TestCase(unittest.TestCase):
    """Base case: network denied + full log capture for every A5.1 test."""

    def setUp(self) -> None:
        self._guard = _NetworkGuard()
        self._guard.install()
        self.addCleanup(self._guard.uninstall)

        self._log_handler = _ListHandler()
        for name in ("", "noam.proposals"):
            logger = logging.getLogger(name)
            logger.addHandler(self._log_handler)
            self.addCleanup(logger.removeHandler, self._log_handler)
        self._root_logger = logging.getLogger()
        self._saved_level = self._root_logger.level
        self._root_logger.setLevel(logging.DEBUG)
        self.addCleanup(self._root_logger.setLevel, self._saved_level)

    # -- helpers ----------------------------------------------------------

    @property
    def network_attempts(self) -> list[str]:
        return self._guard.attempts

    def captured_log_text(self) -> str:
        return self._log_handler.text()

    def assert_no_raw_content(self, *extra: str) -> None:
        haystack = "\n".join([self.captured_log_text(), *extra])
        for needle in FORBIDDEN_SUBSTRINGS:
            self.assertNotIn(needle, haystack)


def copy_fixture_root(into: Path, *, name: str = "a5_1") -> Path:
    """Copy the whole fixture tree so a test can safely mutate a fixture
    without touching the checked-in corpus. ``name`` sets the copied root's
    own directory name (used by the fixture-root confinement tests)."""

    dest = into / name
    shutil.copytree(FIXTURE_ROOT, dest)
    return dest


@contextmanager
def mutable_fixture_root(*, relative_name: str = "a5_1"):
    """Yield a writable copy of the fixture tree. ``relative_name`` may be a
    multi-segment path (e.g. ``studies/S001_airport_cw``) so a test can place
    the root under a forbidden-looking directory."""

    with tempfile.TemporaryDirectory() as tmp:
        parts = Path(relative_name)
        yield copy_fixture_root(Path(tmp) / parts.parent, name=parts.name)


def read_recorded_meta(root: Path, fixture_id: str) -> dict:
    return json.loads((root / "recorded" / f"{fixture_id}.meta.json").read_text())


def write_recorded_meta(root: Path, fixture_id: str, meta: dict) -> None:
    (root / "recorded" / f"{fixture_id}.meta.json").write_bytes(
        canonical_json(meta).encode("utf-8")
    )


def rewrite_recorded_output(
    root: Path, fixture_id: str, suffix: str, new_bytes: bytes
) -> None:
    """Overwrite a recorded output file and keep ``meta.output_sha256`` in
    step, so a test can exercise a *content* defect rather than tripping the
    output-digest check first."""

    (root / "recorded" / f"{fixture_id}.{suffix}").write_bytes(new_bytes)
    meta = read_recorded_meta(root, fixture_id)
    meta["output_sha256"] = sha256_hex(new_bytes)
    write_recorded_meta(root, fixture_id, meta)


def source_bytes(fixture_id: str) -> bytes:
    return (CORPUS / f"{fixture_id}.txt").read_bytes()


def source_sha(fixture_id: str) -> str:
    return sha256_hex(source_bytes(fixture_id))


def make_request(fixture_id: str, *, source_sha256: str | None = None, **overrides) -> ProposalRequest:
    data = {
        "contract_version": CONTRACT_VERSION,
        "backend_id": BACKEND_ID,
        "fixture_id": fixture_id,
        "expected_source_sha256": source_sha256 or source_sha(fixture_id),
    }
    data.update(overrides)
    return ProposalRequest(**data)
