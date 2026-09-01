"""Frozen version identifiers for the A5.1 contract and recorded backend.

A request and every recorded fixture must name these exact strings. A
mismatch is a structured unresolved state, never a silent upgrade or a
fallback to some other backend.
"""

from __future__ import annotations

# Bump only through a new human-approved task: the request/response DTO shape,
# canonical serialisation rule, or digest semantics changing all require it.
CONTRACT_VERSION = "a5.1.0"

# The only backend A5.1 authorises. There is deliberately no registry of
# alternative backend ids -- a live model is out of scope.
BACKEND_ID = "recorded-fixture"
BACKEND_VERSION = "a5.1.0"
