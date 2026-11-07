"""Load the srag csv into a local duckdb file, cleaned and anonymised."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from srag.pipeline.clean import clean
from srag.pipeline.columns import KEEP_COLUMNS

TABLE = "srag_cases"


def read_raw(csv_path: Path) -> pd.DataFrame:
    """Read only the allowlisted columns, the rest never gets into memory."""
    keep = set(KEEP_COLUMNS)
    last_error: Exception | None = None
    for encoding in ("utf-8", "latin-1"):
        try:
            return pd.read_csv(
                csv_path,
                sep=";",
                dtype=str,
                encoding=encoding,
                usecols=lambda c: c.upper() in keep,
                low_memory=False,
            )
        except UnicodeDecodeError as exc:
            last_error = exc
    raise RuntimeError(f"Could not decode {csv_path}") from last_error


def ingest(csv_path: Path, db_path: Path, *, salt: str) -> int:
    """read -> clean -> load. Returns how many rows ended up in the table."""
    cleaned = clean(read_raw(csv_path), salt=salt)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        con.register("cleaned_df", cleaned)
        con.execute(f"CREATE OR REPLACE TABLE {TABLE} AS SELECT * FROM cleaned_df")
        count = con.execute(f"SELECT count(*) FROM {TABLE}").fetchone()
    finally:
        con.close()
    return int(count[0]) if count else 0
