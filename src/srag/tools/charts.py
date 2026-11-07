"""The two charts. They only get aggregated counts, no patient rows."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def daily_chart(counts: dict[date, int], out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(list(counts), list(counts.values()), marker="o", ms=3, color="#1f6f8b")
    ax.set_title("SRAG cases per day: last 30 days of data")
    ax.set_ylabel("Cases (by symptom onset)")
    ax.grid(alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out


def monthly_chart(counts: dict[str, int], out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.bar(list(counts), list(counts.values()), color="#1f6f8b")
    ax.set_title("SRAG cases per month: last 12 months of data")
    ax.set_ylabel("Cases (by symptom onset)")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out
