"""Privacy and logging boundary (Gate 2 criterion 11).

With logging captured at all levels and every scenario exercised, no raw
prompt, raw corpus text, planted sentinel, or complete proposal content may
appear in a log line or an exception string. Operational logs may contain
only non-content identifiers, versions, digests, reason codes, and counts.
"""

from __future__ import annotations

from _support import CORPUS, FIXTURE_ROOT, A51TestCase, make_request

from noam.proposals import RecordedFixtureBackend, run_proposal_intake
from noam.proposals.errors import ProposalError

SCENARIOS = (
    ("cw-basics", {}),
    ("injection", {}),
    ("sparse-notes", {}),
    ("insufficient-source", {}),
    ("incompatible-units", {}),
    ("malformed-record", {}),
    ("digest-drift", {}),
    ("cw-basics", {"source_sha256": "b" * 64}),  # digest mismatch
    ("cw-basics", {"contract_version": "a5.0.0"}),  # version mismatch
    ("does-not-exist", {"source_sha256": "a" * 64}),  # unknown fixture
)


class PrivacyLoggingTest(A51TestCase):
    def test_no_raw_content_in_logs_or_exceptions_across_all_scenarios(self) -> None:
        backend = RecordedFixtureBackend(FIXTURE_ROOT)
        error_strings: list[str] = []
        for fixture_id, overrides in SCENARIOS:
            request = make_request(fixture_id, **overrides)
            outcome = run_proposal_intake(request, backend)
            if not outcome.ok:
                for item in outcome.unresolved.items:
                    error_strings.append(item.affected)
                    error_strings.append(item.human_action)
            try:
                backend.resolve(request)
            except ProposalError as exc:
                error_strings.append(str(exc))
                error_strings.append(repr(exc))

        self.assert_no_raw_content(*error_strings)

        # a whole raw corpus file must not appear verbatim either
        haystack = "\n".join([self.captured_log_text(), *error_strings])
        for path in CORPUS.glob("*.txt"):
            body = path.read_text().strip()
            self.assertNotIn(body, haystack)

    def test_full_proposal_content_is_not_logged(self) -> None:
        outcome = run_proposal_intake(make_request("cw-basics"), RecordedFixtureBackend(FIXTURE_ROOT))
        log_text = self.captured_log_text()
        # the canonical package as a whole, and individual claim statements
        self.assertNotIn(outcome.package_bytes.decode("utf-8"), log_text)
        self.assertNotIn("The stated nominal panel size is 1.5 m wide", log_text)
        self.assertNotIn("Bound the preliminary mullion size", log_text)

    def test_operational_log_keeps_only_identifiers_digests_and_counts(self) -> None:
        with self.assertLogs("noam.proposals", level="INFO") as captured:
            run_proposal_intake(make_request("cw-basics"), RecordedFixtureBackend(FIXTURE_ROOT))
            run_proposal_intake(
                make_request("cw-basics", contract_version="a5.0.0"),
                RecordedFixtureBackend(FIXTURE_ROOT),
            )
        joined = "\n".join(captured.output)
        self.assertIn("fixture=cw-basics", joined)
        self.assertIn("output_sha=", joined)
        self.assertIn("reason=contract_version_mismatch", joined)
        self.assert_no_raw_content(joined)
