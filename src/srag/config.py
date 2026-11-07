"""Settings, read from env vars."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    db_path: Path
    log_dir: Path
    report_dir: Path
    model: str
    hash_salt: str

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            db_path=Path(os.getenv("SRAG_DB_PATH", "data/srag.duckdb")),
            log_dir=Path(os.getenv("SRAG_LOG_DIR", "logs")),
            report_dir=Path(os.getenv("SRAG_REPORT_DIR", "reports")),
            model=os.getenv("SRAG_MODEL", "claude-haiku-5-5"),
            hash_salt=os.getenv("SRAG_HASH_SALT", "change-me"),
        )
