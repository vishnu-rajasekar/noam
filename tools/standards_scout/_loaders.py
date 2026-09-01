"""Structured-file loading with no hard dependency on PyYAML.

This workstation's interpreters do not have PyYAML and the sandbox forbids
installing it, so the committed synthetic corpus is JSON. ``.yaml`` / ``.yml``
inputs (the restricted Airport library, when an engineer runs with PyYAML
available) are still supported: they load only if PyYAML can be imported, and
raise a clear, actionable error otherwise instead of a bare ImportError.
"""

from __future__ import annotations

import json
from pathlib import Path


def load_structured(path: str | Path) -> object:
    p = Path(path)
    suffix = p.suffix.lower()
    text = p.read_text(encoding="utf-8")
    if suffix == ".json":
        return json.loads(text)
    if suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ImportError as exc:  # pragma: no cover - env dependent
            raise RuntimeError(
                f"{p} is YAML but PyYAML is not installed in this interpreter. "
                f"Install PyYAML in the environment you run the harness from, or "
                f"provide the same data as .json."
            ) from exc
        return yaml.safe_load(text)
    raise ValueError(f"{p}: unsupported structured format {suffix!r} (use .json or .yaml)")


def resolve_one(base: Path, *candidates: str) -> Path:
    """Return the first existing path among ``base/<candidate>``."""

    for name in candidates:
        cand = base / name
        if cand.exists():
            return cand
    return base / candidates[0]
