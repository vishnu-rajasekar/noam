"""Local, disposable, rebuildable structured index over the authoring files.

The task brief that seeded this restructuring specified DuckDB. This
sandbox has neither network access nor DuckDB (or `uv`) available offline,
and this index must run with zero network access on a fresh work-PC Python
(see the migration report). SQLite is stdlib, gives the same "local
index/query layer over authoring files" role, and is trivially swappable
later: only this module and ``cli/main.py``'s ``search``/``registry``
commands would need to change, because callers never touch the database
directly.

No semantic/vector search. Structured filters only (see ROADMAP.md Phase A).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from noam.registry import paths, store

SCHEMA = """
CREATE TABLE IF NOT EXISTS studies (
    id TEXT PRIMARY KEY,
    title TEXT,
    domain TEXT,
    project_stage TEXT,
    status TEXT,
    confidentiality TEXT,
    jurisdiction TEXT,
    system_type TEXT
);
CREATE TABLE IF NOT EXISTS capabilities (
    id TEXT PRIMARY KEY,
    domain TEXT,
    name TEXT,
    status TEXT,
    version TEXT
);
CREATE TABLE IF NOT EXISTS precedents (
    id TEXT PRIMARY KEY,
    domain TEXT,
    title TEXT,
    validation_state TEXT
);
CREATE TABLE IF NOT EXISTS insights (
    id TEXT PRIMARY KEY,
    study_id TEXT,
    statement TEXT,
    reuse_status TEXT
);
"""

_SEARCHABLE_COLUMNS: dict[str, set[str]] = {
    "studies": {"id", "title", "domain", "project_stage", "status",
                "confidentiality", "jurisdiction", "system_type"},
    "capabilities": {"id", "domain", "name", "status", "version"},
    "precedents": {"id", "domain", "title", "validation_state"},
    "insights": {"id", "study_id", "statement", "reuse_status"},
}


@dataclass
class IndexResult:
    studies: int
    capabilities: int
    precedents: int
    insights: int


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    db_path = db_path or paths.index_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def build_index(db_path: Path | None = None) -> IndexResult:
    """Rebuild the index from scratch from the authoring files on disk.

    Idempotent: always drops and recreates its tables, so running it twice
    in a row produces the same result as running it once.
    """
    conn = _connect(db_path)
    try:
        conn.executescript(
            "DROP TABLE IF EXISTS studies;"
            "DROP TABLE IF EXISTS capabilities;"
            "DROP TABLE IF EXISTS precedents;"
            "DROP TABLE IF EXISTS insights;"
        )
        conn.executescript(SCHEMA)

        studies = store.list_studies()
        for s in studies:
            conn.execute(
                "INSERT INTO studies VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (s.id, s.title, s.domain.value, s.project_stage.value,
                 s.status.value, s.confidentiality.value, s.jurisdiction,
                 s.system_type),
            )

        capabilities = store.list_capabilities()
        for c in capabilities:
            conn.execute(
                "INSERT INTO capabilities VALUES (?, ?, ?, ?, ?)",
                (c.id, c.domain.value, c.name, c.status.value, c.version),
            )

        precedents = store.list_precedents()
        for p in precedents:
            conn.execute(
                "INSERT INTO precedents VALUES (?, ?, ?, ?)",
                (p.id, p.domain.value, p.title, p.validation_state.value),
            )

        insights = store.list_insights()
        for i in insights:
            conn.execute(
                "INSERT INTO insights VALUES (?, ?, ?, ?)",
                (i.id, i.study_id, i.statement, i.reuse_status.value),
            )

        conn.commit()
        return IndexResult(
            studies=len(studies),
            capabilities=len(capabilities),
            precedents=len(precedents),
            insights=len(insights),
        )
    finally:
        conn.close()


def search(table: str, db_path: Path | None = None, **filters: Any) -> list[dict]:
    if table not in _SEARCHABLE_COLUMNS:
        raise ValueError(
            f"unknown search table {table!r}; expected one of "
            f"{sorted(_SEARCHABLE_COLUMNS)}"
        )
    allowed = _SEARCHABLE_COLUMNS[table]
    unknown = set(filters) - allowed
    if unknown:
        raise ValueError(f"unknown filter(s) for {table}: {sorted(unknown)}")

    conn = _connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        clauses = " AND ".join(f"{col} = ?" for col in filters)
        query = f"SELECT * FROM {table}"  # noqa: S608 - table name is allow-listed above
        if clauses:
            query += f" WHERE {clauses}"
        rows = conn.execute(query, tuple(filters.values())).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
