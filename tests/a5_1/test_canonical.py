"""Canonical serialisation rules (Gate 2 criterion 7)."""

from __future__ import annotations

import json

from _support import A51TestCase

from noam.proposals import Claim, canonical_bytes, canonical_json
from noam.proposals.canonical import quantise_confidence


class CanonicalJsonTest(A51TestCase):
    def _claim(self, confidence: float) -> Claim:
        return Claim(
            claim_id="SF-001",
            category="sourced",
            statement="unicode: naïve façade — €",
            citations=[{"source_id": "s1", "locator": "line:3"}],
            confidence=confidence,
        )

    def test_keys_are_sorted_and_separators_are_compact(self) -> None:
        raw = canonical_bytes(self._claim(0.5)).decode("utf-8")
        self.assertTrue(raw.endswith("}\n"))
        payload = json.loads(raw)
        self.assertEqual(list(payload), sorted(payload))
        # exact compact + sorted form, recomputed independently
        reference = (
            json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            + "\n"
        )
        self.assertEqual(raw, reference)

    def test_exactly_one_trailing_newline(self) -> None:
        raw = canonical_bytes(self._claim(0.5))
        self.assertTrue(raw.endswith(b"}\n"))
        self.assertFalse(raw.endswith(b"\n\n"))

    def test_unicode_is_preserved_not_escaped(self) -> None:
        raw = canonical_bytes(self._claim(0.5)).decode("utf-8")
        self.assertIn("naïve façade — €", raw)
        self.assertNotIn("\\u", raw)

    def test_confidence_is_quantised_to_three_decimals(self) -> None:
        self.assertEqual(quantise_confidence(0.333333), 0.333)
        self.assertEqual(quantise_confidence(0.0), 0.0)
        self.assertEqual(quantise_confidence(-0.0), 0.0)
        raw = canonical_bytes(self._claim(0.1 + 0.2)).decode("utf-8")
        self.assertIn('"confidence":0.3', raw)
        self.assertNotIn("0.30000000", raw)

    def test_nan_and_infinity_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            canonical_json({"x": float("nan")})
        with self.assertRaises(ValueError):
            canonical_json({"x": float("inf")})

    def test_array_order_is_preserved_not_sorted(self) -> None:
        raw = canonical_json(["b", "a", "c"])
        self.assertEqual(raw, '["b","a","c"]\n')
