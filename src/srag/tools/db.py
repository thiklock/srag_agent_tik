"""DB access: read-only connection and a guarded query helper."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from srag.guardrails import check_sql

MAX_ROWS = 50


def connect_readonly(db_path: Path) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(db_path), read_only=True)


def run_query(con: duckdb.DuckDBPyConnection, sql: str) -> list[dict[str, Any]]:
    """Run a checked select, never returns more than MAX_ROWS rows."""
    verdict = check_sql(sql)
    if not verdict.allowed:
        raise PermissionError(verdict.reason)
    cur = con.execute(f"SELECT * FROM ({sql.strip().rstrip(';')}) LIMIT {MAX_ROWS}")
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]
