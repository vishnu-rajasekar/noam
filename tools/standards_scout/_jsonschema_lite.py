"""Minimal, dependency-free JSON Schema validator.

No `jsonschema` package is installed and installing one is denied in the
sandbox, so this implements exactly the subset of draft-07 the committed
schemas under ``schemas/`` actually use: ``type``, ``enum``, ``required``,
``properties``, ``additionalProperties`` (boolean only), ``items``,
``minLength``, ``maxLength``, ``minItems``, ``minimum``, ``maximum``.

Validating against the schema file itself (rather than a hand-maintained copy
of its rules) is the point: a hand-written checker drifts from the schema as
the schema evolves and can silently under-validate. If a committed schema ever
needs a keyword outside this subset, `validate()` raises ``NotImplementedError``
at call time so that gap is loud, not silent.
"""

from __future__ import annotations

_SUPPORTED_KEYWORDS = {
    "type",
    "enum",
    "required",
    "properties",
    "additionalProperties",
    "items",
    "minLength",
    "maxLength",
    "minItems",
    "minimum",
    "maximum",
    # metadata keywords that carry no validation semantics here
    "$schema",
    "$id",
    "title",
    "version",
    "description",
}


def _is_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _type_ok(value: object, type_name: str) -> bool:
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "array":
        return isinstance(value, list)
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "integer":
        return _is_integer(value)
    if type_name == "number":
        return _is_number(value)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "null":
        return value is None
    raise NotImplementedError(f"unsupported schema type {type_name!r}")


def _check_unsupported(schema: dict) -> None:
    unknown = set(schema) - _SUPPORTED_KEYWORDS
    if unknown:
        raise NotImplementedError(f"schema uses unsupported keyword(s): {sorted(unknown)}")


def validate(instance: object, schema: dict, path: str = "$") -> list[tuple[str, str]]:
    """Return ``[(json_path, message), ...]``; empty means valid.

    Deliberately never raises on the *instance* (untrusted model output) -
    every mismatch becomes an entry in the returned list. It raises only on a
    *schema* that uses a keyword this lite validator does not implement, which
    is a bug in the committed schema/validator pairing, not in model output.
    """

    _check_unsupported(schema)
    errors: list[tuple[str, str]] = []

    types = schema.get("type")
    if types is not None:
        type_list = types if isinstance(types, list) else [types]
        if not any(_type_ok(instance, t) for t in type_list):
            errors.append((path, f"expected type {types!r}, got {type(instance).__name__}"))
            return errors  # further checks on this node would be noise

    if "enum" in schema and instance not in schema["enum"]:
        errors.append((path, f"{instance!r} is not one of {schema['enum']!r}"))

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append((path, f"length {len(instance)} < minLength {schema['minLength']}"))
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append((path, f"length {len(instance)} > maxLength {schema['maxLength']}"))

    if _is_number(instance):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append((path, f"{instance} < minimum {schema['minimum']}"))
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append((path, f"{instance} > maximum {schema['maximum']}"))

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append((path, f"missing required property {key!r}"))
        properties = schema.get("properties", {})
        for key, value in instance.items():
            if key in properties:
                errors.extend(validate(value, properties[key], f"{path}.{key}"))
            elif schema.get("additionalProperties") is False:
                errors.append((path, f"unexpected property {key!r}"))

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append((path, f"{len(instance)} items < minItems {schema['minItems']}"))
        item_schema = schema.get("items")
        if item_schema is not None:
            for i, item in enumerate(instance):
                errors.extend(validate(item, item_schema, f"{path}[{i}]"))

    return errors
