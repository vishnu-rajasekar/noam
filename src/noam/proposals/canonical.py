"""Canonical UTF-8 serialisation and hashing for A5.1.

Byte stability is a contract requirement (ROADMAP.md / Gate 2 criterion 7):
the same request must produce byte-identical output in a fresh process, and
those bytes must equal the checked-in recorded fixture and its declared
SHA-256.

Canonical form rules (documented so a reviewer can reproduce them by hand):

* the value is ``model.model_dump(mode="json")`` -- pydantic's JSON-mode dump,
  so enums become their ``str`` value and tuples become arrays;
* object keys are emitted in ascending Unicode code-point order
  (``json.dumps(sort_keys=True)``);
* array element order is significant and is taken verbatim from the model /
  recorded fixture -- it is never sorted;
* separators are ``","`` and ``":"`` with no insignificant whitespace;
* non-ASCII text is kept as UTF-8 (``ensure_ascii=False``), not ``\\uXXXX``;
* ``NaN`` / ``Infinity`` are rejected (``allow_nan=False``);
* every confidence value is quantised to 3 decimal places on ingest
  (:func:`quantise_confidence`); all other numbers in the schema are
  integers, so float formatting is the only representation risk and it is
  removed at the edge rather than here;
* exactly one trailing newline (``"\\n"``) terminates the document.

Digest semantics:

* a *source* digest hashes the exact on-disk bytes of the source fixture
  file, with no normalisation;
* a *request* digest hashes :func:`canonical_bytes` of the request DTO;
* an *output* digest hashes :func:`canonical_bytes` of the proposal package
  DTO (the package alone, not the response envelope that carries the digest).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel

CANONICAL_ENCODING = "utf-8"
CONFIDENCE_DECIMALS = 3


def quantise_confidence(value: float) -> float:
    """Round a confidence to the fixed decimal precision and kill ``-0.0``.

    Applied as an ``AfterValidator`` on every confidence field so the value
    stored in the DTO -- and therefore serialised -- is already canonical.
    """

    quantised = round(float(value), CONFIDENCE_DECIMALS)
    return 0.0 if quantised == 0 else quantised


def canonical_json(data: Any) -> str:
    """Serialise already-JSON-safe ``data`` to the canonical string form."""

    return (
        json.dumps(
            data,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    )


def canonical_bytes(model: BaseModel) -> bytes:
    """Canonical UTF-8 bytes for a pydantic model."""

    return canonical_json(model.model_dump(mode="json")).encode(CANONICAL_ENCODING)


def sha256_hex(data: bytes) -> str:
    """Lower-case hex SHA-256 of ``data``."""

    return hashlib.sha256(data).hexdigest()
