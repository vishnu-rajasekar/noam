"""Fixture provenance, redistribution, and no-leaked-real-content checks
(Gate 2 criterion 8)."""

from __future__ import annotations

import importlib.util
import json

from _support import ALL_FIXTURE_IDS, CORPUS, FIXTURE_ROOT, RECORDED, A51TestCase

from noam.proposals import sha256_hex

PROV_KEYS = {
    "fixture_id",
    "source_id",
    "origin",
    "locator",
    "author_or_publisher",
    "licence",
    "created_or_retrieved",
    "byte_length",
    "sha256",
    "redistribution_rationale",
}

# things that would indicate real / licensed / confidential material leaked in
DISALLOWED_IN_CORPUS = (
    "S001",
    "airport_cw",
    "EN 1993",
    "EN 1999",
    "EN 1991",
    "confidential",
    "restricted",
    "knowledge/restricted",
)


class FixtureProvenanceTest(A51TestCase):
    def test_every_corpus_file_has_matching_provenance_metadata(self) -> None:
        for fixture_id in ALL_FIXTURE_IDS:
            src = CORPUS / f"{fixture_id}.txt"
            meta_path = CORPUS / f"{fixture_id}.source.json"
            self.assertTrue(src.is_file(), fixture_id)
            self.assertTrue(meta_path.is_file(), fixture_id)
            meta = json.loads(meta_path.read_text())
            self.assertEqual(set(meta), PROV_KEYS, fixture_id)
            body = src.read_bytes()
            self.assertEqual(meta["byte_length"], len(body), fixture_id)
            self.assertEqual(meta["sha256"], sha256_hex(body), fixture_id)
            self.assertTrue(meta["licence"].strip(), fixture_id)
            self.assertTrue(meta["redistribution_rationale"].strip(), fixture_id)
            self.assertRegex(meta["created_or_retrieved"], r"^\d{4}-\d{2}-\d{2}$")

    def test_recorded_artifacts_declare_their_own_digest_and_versions(self) -> None:
        for fixture_id in ALL_FIXTURE_IDS:
            meta = json.loads((RECORDED / f"{fixture_id}.meta.json").read_text())
            self.assertEqual(meta["contract_version"], "a5.1.0")
            self.assertEqual(meta["backend_id"], "recorded-fixture")
            self.assertEqual(meta["backend_version"], "a5.1.0")
            request_bytes = (RECORDED / f"{fixture_id}.request.json").read_bytes()
            self.assertEqual(meta["request_sha256"], sha256_hex(request_bytes))
            suffix = "unresolved.json" if meta["kind"] == "unresolved" else "package.json"
            output_bytes = (RECORDED / f"{fixture_id}.{suffix}").read_bytes()
            if fixture_id == "digest-drift":
                self.assertNotEqual(meta["output_sha256"], sha256_hex(output_bytes))
            else:
                self.assertEqual(meta["output_sha256"], sha256_hex(output_bytes))

    def test_corpus_contains_no_real_licensed_or_confidential_markers(self) -> None:
        for path in sorted(CORPUS.glob("*.txt")):
            text = path.read_text()
            for token in DISALLOWED_IN_CORPUS:
                self.assertNotIn(token, text, f"{path.name} :: {token}")
            self.assertIn("synthetic", text.lower(), path.name)

    def test_manifest_lists_every_fixture_and_matches_disk(self) -> None:
        manifest = json.loads((FIXTURE_ROOT / "manifest.json").read_text())
        listed = {entry["fixture_id"] for entry in manifest["fixtures"]}
        self.assertEqual(listed, set(ALL_FIXTURE_IDS))
        for entry in manifest["fixtures"]:
            src = FIXTURE_ROOT / entry["source_file"]
            self.assertEqual(entry["source_sha256"], sha256_hex(src.read_bytes()))
            out = FIXTURE_ROOT / entry["recorded_output_file"]
            self.assertTrue(out.is_file())

    def test_corpus_is_tiny(self) -> None:
        total = sum(p.stat().st_size for p in CORPUS.glob("*.txt"))
        self.assertLess(total, 8_000)


class FixtureRegenerationIsStableTest(A51TestCase):
    def test_build_fixtures_check_reports_no_drift(self) -> None:
        script = FIXTURE_ROOT / "build_fixtures.py"
        spec = importlib.util.spec_from_file_location("_a5_1_build_fixtures", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.build(check=True), 0)
