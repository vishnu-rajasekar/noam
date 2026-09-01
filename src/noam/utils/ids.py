"""Sequential id allocation, e.g. REQ-001, REQ-002, ... or S001, S002, ...

Ids are derived from filenames already on disk, never from a counter file,
so two studies created independently (e.g. on different machines before a
sync) cannot collide silently -- a collision surfaces as a duplicate
filename instead.
"""

from __future__ import annotations

import re
from pathlib import Path


def next_id(
    prefix: str,
    existing_ids: list[str],
    width: int = 3,
    dashed: bool = True,
) -> str:
    sep = "-" if dashed else ""
    pattern = re.compile(rf"^{re.escape(prefix)}{re.escape(sep)}(\d{{{width}}})$")
    numbers = [int(m.group(1)) for eid in existing_ids if (m := pattern.match(eid))]
    return f"{prefix}{sep}{max(numbers, default=0) + 1:0{width}d}"


def existing_ids_in(directory: Path) -> list[str]:
    if not directory.is_dir():
        return []
    return [p.stem for p in directory.glob("*.yaml")]
