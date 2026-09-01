"""Thin YAML load/dump wrapper.

PyYAML is a small, common, pure-offline dependency (see pyproject.toml). If
it is not installed -- e.g. a fresh work-PC Python before `uv sync` has run
-- fail with an instruction instead of a bare ImportError traceback.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised only when missing
    raise ImportError(
        "PyYAML is required for the noam registry but is not installed. "
        "Run `uv sync` (see README.md) before using `noam`."
    ) from exc


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def dump_yaml(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
