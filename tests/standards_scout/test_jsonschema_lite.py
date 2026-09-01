"""Direct tests for the dependency-free JSON Schema subset validator that
validate.py's _check_schema is built on."""

from __future__ import annotations

import unittest

from tools.standards_scout import _jsonschema_lite as js


class TestJsonSchemaLite(unittest.TestCase):
    def test_type_mismatch(self) -> None:
        self.assertTrue(js.validate(5, {"type": "string"}))
        self.assertFalse(js.validate("x", {"type": "string"}))

    def test_integer_excludes_bool(self) -> None:
        self.assertTrue(js.validate(True, {"type": "integer"}))
        self.assertFalse(js.validate(3, {"type": "integer"}))

    def test_enum(self) -> None:
        schema = {"type": "string", "enum": ["A", "B"]}
        self.assertFalse(js.validate("A", schema))
        self.assertTrue(js.validate("C", schema))

    def test_min_max_length(self) -> None:
        schema = {"type": "string", "minLength": 1, "maxLength": 3}
        self.assertTrue(js.validate("", schema))
        self.assertFalse(js.validate("ab", schema))
        self.assertTrue(js.validate("abcd", schema))

    def test_minimum_maximum(self) -> None:
        schema = {"type": "integer", "minimum": 1, "maximum": 5}
        self.assertTrue(js.validate(0, schema))
        self.assertFalse(js.validate(3, schema))
        self.assertTrue(js.validate(6, schema))

    def test_required_property_missing(self) -> None:
        schema = {"type": "object", "required": ["a", "b"], "properties": {}}
        errs = js.validate({"a": 1}, schema)
        self.assertEqual(len(errs), 1)
        self.assertIn("b", errs[0][1])

    def test_additional_properties_false_rejects_unknown_key(self) -> None:
        schema = {"type": "object", "additionalProperties": False, "properties": {"a": {"type": "integer"}}}
        self.assertFalse(js.validate({"a": 1}, schema))
        self.assertTrue(js.validate({"a": 1, "b": 2}, schema))

    def test_additional_properties_unset_allows_unknown_key(self) -> None:
        schema = {"type": "object", "properties": {"a": {"type": "integer"}}}
        self.assertFalse(js.validate({"a": 1, "b": 2}, schema))

    def test_nested_items_validated_with_path(self) -> None:
        schema = {"type": "array", "items": {"type": "integer", "minimum": 0}}
        errs = js.validate([1, -1, 2], schema)
        self.assertEqual(len(errs), 1)
        self.assertEqual(errs[0][0], "$[1]")

    def test_min_items(self) -> None:
        schema = {"type": "array", "minItems": 2}
        self.assertTrue(js.validate([1], schema))
        self.assertFalse(js.validate([1, 2], schema))

    def test_valid_nested_object_has_no_errors(self) -> None:
        schema = {
            "type": "object",
            "required": ["items"],
            "properties": {"items": {"type": "array", "items": {"type": "string", "minLength": 1}}},
        }
        self.assertEqual(js.validate({"items": ["a", "b"]}, schema), [])

    def test_unsupported_keyword_raises(self) -> None:
        with self.assertRaises(NotImplementedError):
            js.validate("x", {"type": "string", "pattern": "^x$"})

    def test_never_raises_on_malformed_instance(self) -> None:
        schema = {"type": "object", "required": ["a"], "properties": {"a": {"type": "string"}}}
        for bad_instance in (None, "str", 5, ["list"], {"a": 5}):
            js.validate(bad_instance, schema)  # must not raise

    def test_validates_the_committed_response_schema_loads(self) -> None:
        from tools.standards_scout.validate import _RESPONSE_SCHEMA

        # The schema itself must be usable by this validator with no
        # NotImplementedError - proves the "committed schema" and the
        # validator stay in the supported subset together.
        errs = js.validate({"not": "a valid response"}, _RESPONSE_SCHEMA)
        self.assertTrue(errs)


if __name__ == "__main__":
    unittest.main()
