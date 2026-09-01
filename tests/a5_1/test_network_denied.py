"""Network / subprocess denial and static client-freedom (criterion 10)."""

from __future__ import annotations

import socket
from pathlib import Path

from _support import (
    ALL_FIXTURE_IDS,
    FIXTURE_ROOT,
    A51TestCase,
    make_request,
    network_denied,
)

from noam.proposals import RecordedFixtureBackend, run_proposal_intake

PROPOSALS_SRC = Path(__file__).resolve().parents[2] / "src" / "noam" / "proposals"

FORBIDDEN_IMPORT_TOKENS = (
    "import socket",
    "import ssl",
    "import http",
    "import urllib",
    "import requests",
    "import httpx",
    "import aiohttp",
    "import asyncio",
    "import subprocess",
    "import ollama",
    "from http",
    "from urllib",
    "socket.",
    "urlopen",
    "subprocess.",
)


class NetworkDenialTest(A51TestCase):
    def test_guard_is_active_during_every_a5_1_test(self) -> None:
        with self.assertRaises(RuntimeError):
            socket.create_connection(("example.invalid", 80))
        self.assertIn("socket.create_connection", self.network_attempts)

    def test_full_intake_matrix_runs_with_network_denied(self) -> None:
        # setUp already installs the guard; assert every fixture path still
        # completes without ever touching a connection primitive.
        for fixture_id in ALL_FIXTURE_IDS:
            outcome = run_proposal_intake(
                make_request(fixture_id), RecordedFixtureBackend(FIXTURE_ROOT)
            )
            self.assertIsNotNone(outcome)
        self.assertEqual(self.network_attempts, [])

    def test_nested_explicit_guard_also_blocks_dns_and_subprocess(self) -> None:
        with network_denied() as guard:
            with self.assertRaises(RuntimeError):
                socket.getaddrinfo("example.invalid", 80)
            import subprocess

            with self.assertRaises(RuntimeError):
                subprocess.Popen(["true"])
        self.assertIn("socket.getaddrinfo", guard.attempts)
        self.assertIn("subprocess.Popen", guard.attempts)


class StaticClientFreedomTest(A51TestCase):
    def test_no_network_or_model_client_in_proposals_source(self) -> None:
        offenders: list[str] = []
        for path in sorted(PROPOSALS_SRC.glob("*.py")):
            text = path.read_text()
            for token in FORBIDDEN_IMPORT_TOKENS:
                if token in text:
                    offenders.append(f"{path.name}: {token}")
        self.assertEqual(offenders, [])

    def test_proposals_package_declares_no_third_party_backend_dependency(self) -> None:
        # only pydantic + stdlib may be imported by the runtime package
        for path in sorted(PROPOSALS_SRC.glob("*.py")):
            text = path.read_text()
            self.assertNotIn("ollama", text)
            self.assertNotIn("openai", text)
            self.assertNotIn("anthropic", text)
