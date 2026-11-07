"""CLI: `srag ingest <csv>` and `srag report [--request ...] [--offline]`."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from srag.agent import LLM, AnthropicLLM, run_report
from srag.audit import AuditLog
from srag.config import Settings
from srag.pipeline.ingest import ingest
from srag.tools.db import connect_readonly


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="srag")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_ing = sub.add_parser("ingest", help="Clean, anonymise and load the DATASUS CSV")
    p_ing.add_argument("csv", type=Path)
    p_rep = sub.add_parser("report", help="Generate the SRAG report")
    p_rep.add_argument("--request", default="Generate the full SRAG report")
    p_rep.add_argument("--offline", action="store_true", help="No LLM, template narrative")
    args = parser.parse_args(argv)
    load_dotenv()  # reads .env if there is one, real env vars still win
    settings = Settings.from_env()

    if args.cmd == "ingest":
        n = ingest(args.csv, settings.db_path, salt=settings.hash_salt)
        print(f"Loaded {n} cleaned, pseudonymised rows into {settings.db_path}")
        return 0

    llm: LLM | None = None
    if not args.offline and os.getenv("ANTHROPIC_API_KEY"):
        llm = AnthropicLLM(settings.model)
    audit = AuditLog(settings.log_dir)
    con = connect_readonly(settings.db_path)
    out_dir = settings.report_dir / audit.run_id
    result = run_report(args.request, con, llm, audit, out_dir)
    if result.get("refusal"):
        print(f"Request refused: {result['refusal']}")
        return 2
    print(f"Report: {result['report_path']}  |  Audit log: {audit.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
