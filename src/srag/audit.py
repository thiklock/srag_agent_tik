"""Audit log: one jsonl file per run, one event per line."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class AuditLog:
    """Writes every decision, tool call and guard result for a single run."""

    def __init__(self, log_dir: Path, run_id: str | None = None) -> None:
        self.run_id = run_id or uuid.uuid4().hex[:12]
        log_dir.mkdir(parents=True, exist_ok=True)
        self.path = log_dir / f"run_{self.run_id}.jsonl"

    def event(self, kind: str, **payload: Any) -> None:
        record = {
            "run_id": self.run_id,
            "ts": datetime.now(UTC).isoformat(),
            "event": kind,
            **payload,
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    def events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()]
