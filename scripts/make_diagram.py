"""Draws the architecture diagram -> docs/architecture.pdf and .png"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "docs"

fig, ax = plt.subplots(figsize=(15, 8.4))
ax.set_xlim(0, 15)
ax.set_ylim(0, 8.4)
ax.axis("off")


def box(x: float, y: float, w: float, h: float, text: str, color: str, size: int = 9) -> None:
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04", fc=color, ec="#333"))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size)


def arrow(x1: float, y1: float, x2: float, y2: float, label: str = "", dy: float = 0.12) -> None:
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops={"arrowstyle": "->", "color": "#333", "lw": 1.3})
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + dy, label, fontsize=8, ha="center", color="#555")


ax.text(7.5, 8.1, "SRAG Report Agent: conceptual architecture", ha="center", fontsize=15,
        weight="bold")

# headers
for x, t in ((2.45, "ORCHESTRATOR (LangGraph)"), (7.6, "TOOLS"), (13.0, "DATA & EXTERNAL")):
    ax.text(x, 7.6, t, ha="center", fontsize=10, weight="bold", color="#555")

# left: orchestrator steps
ax.add_patch(FancyBboxPatch((0.3, 1.5), 4.3, 5.9, boxstyle="round,pad=0.05", fc="#eef3fb",
                            ec="#333"))
box(0.6, 6.2, 3.7, 0.8, "1. Input guard\nscope, prompt-injection, no medical advice", "#ffffff", 8)
box(0.6, 5.0, 3.7, 0.8, "2. Plan\nLLM picks tools (allowlist)", "#ffe6a7", 8)
box(0.6, 3.8, 3.7, 0.8, "3. Run tools\ntyped and deterministic", "#ffffff", 8)
box(0.6, 2.6, 3.7, 0.8, "4. Narrate\nLLM, aggregated facts only", "#ffe6a7", 8)
box(0.6, 1.7, 3.7, 0.6, "5. Output guard: numbers must match", "#ffffff", 8)
for y in (6.2, 5.0, 3.8):
    arrow(2.45, y, 2.45, y - 0.4)
arrow(2.45, 2.6, 2.45, 2.3)
ax.text(2.45, 1.25, "retry once, then deterministic template", ha="center", fontsize=7.5,
        color="#555")

# middle: tools, all hang off step 3
ax.plot([5.5, 5.5], [3.3, 6.5], color="#333", lw=1.3)
arrow(4.6, 4.2, 5.5, 4.2)
tools = [
    (6.1, "Metrics tool\ngrowth, mortality, ICU proxy,\nvaccination proxy"),
    (5.0, "Charts tool\ndaily 30d, monthly 12m"),
    (3.9, "SQL tool (optional, not in default plan)\nSELECT-only, 1 table, row cap"),
    (2.8, "News tool\nRSS + domain allowlist + sanitiser"),
]
for y, text in tools:
    box(6.0, y, 3.2, 0.8, text, "#d5e8d4", 8)
    arrow(5.5, y + 0.4, 6.0, y + 0.4)

# LLM
box(6.0, 0.95, 3.2, 0.9, "LLM (Claude, langchain-anthropic)\nreceives aggregates only,\nnever raw rows", "#e1d5e7", 8)
arrow(4.6, 5.4, 6.0, 1.6, "plan", dy=0.0)
arrow(4.6, 3.0, 6.0, 1.3, "narrative", dy=0.1)

# right: data and outside stuff
box(10.9, 6.9, 4.0, 0.6, "Open DATASUS SRAG CSV (raw, contains PII)", "#f6d5d5", 8)
box(10.9, 5.6, 4.0, 0.8, "Ingestion pipeline (offline)\ncolumn allowlist, clean, age bands, hashed id", "#fde9c9", 8)
box(10.9, 4.2, 4.0, 0.9, "DuckDB: srag_cases\nno PII, opened read-only", "#d5e8d4")
box(10.9, 2.8, 4.0, 0.8, "Public news (Google News RSS)\nWHO, Fiocruz, Agencia Brasil, G1...", "#f5f5f5", 8)
box(10.9, 1.4, 4.0, 0.8, "Report: report.md + 2 PNG charts\n+ metric definitions + disclaimer", "#d5e8d4", 8)
arrow(12.9, 6.9, 12.9, 6.4, "usecols")
arrow(12.9, 5.6, 12.9, 5.1, "load")
for y in (6.5, 5.4, 4.3):  # Metrics, Charts, SQL -> DB
    arrow(9.2, y, 10.9, 4.65)
arrow(9.2, 3.2, 10.9, 3.2)
arrow(4.6, 1.95, 10.9, 1.8, "final report", dy=0.12)

# audit log bar at the bottom
box(0.3, 0.1, 14.6, 0.5,
    "Audit trail (logs/run_<id>.jsonl): run_id, timestamps, guard verdicts, plan, every tool "
    "call with inputs and outputs, retries, final report path",
    "#fff2cc", 8)

fig.savefig(OUT / "architecture.pdf", bbox_inches="tight")
fig.savefig(OUT / "architecture.png", dpi=120, bbox_inches="tight")
print("wrote", OUT / "architecture.pdf")
