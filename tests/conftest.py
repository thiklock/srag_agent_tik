from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from srag.pipeline.ingest import ingest
from srag.synthetic import make_synthetic_csv


@pytest.fixture(scope="session")
def db_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    base = tmp_path_factory.mktemp("srag")
    csv = make_synthetic_csv(base / "raw.csv")
    path = base / "srag.duckdb"
    ingest(csv, path, salt="test-salt")
    return path


@pytest.fixture()
def con(db_path: Path) -> duckdb.DuckDBPyConnection:
    c = duckdb.connect(str(db_path), read_only=True)
    yield c  # type: ignore[misc]
    c.close()
