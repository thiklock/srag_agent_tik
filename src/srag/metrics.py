"""Metrics. Every number in the report comes from here, the LLM never computes any.

Windows are anchored to the last event date in the data, not today, so a report on an
old extract still makes sense and gives the same result every time.
"""

from __future__ import annotations

from datetime import date, timedelta

import duckdb
from pydantic import BaseModel

TABLE = "srag_cases"
RATE_WINDOW_DAYS = 365


class MetricResult(BaseModel):
    """One metric plus where it came from, so it can be checked later."""

    name: str
    value: float | None
    unit: str  # "%" or "cases"
    numerator: int | None
    denominator: int | None
    unknown_excluded: int
    window_start: date
    window_end: date
    definition: str
    caveat: str


def anchor_date(con: duckdb.DuckDBPyConnection) -> date:
    row = con.execute(f"SELECT max(event_date) FROM {TABLE}").fetchone()
    if not row or row[0] is None:
        raise ValueError("The cases table is empty; run `srag ingest` first.")
    return row[0]  # type: ignore[no-any-return]


def _count(con: duckdb.DuckDBPyConnection, start: date, end: date, where: str = "TRUE") -> int:
    row = con.execute(
        f"SELECT count(*) FROM {TABLE} WHERE event_date BETWEEN ? AND ? AND {where}",
        [start, end],
    ).fetchone()
    return int(row[0]) if row else 0


def case_growth_rate(con: duckdb.DuckDBPyConnection, anchor: date) -> MetricResult:
    cur_start = anchor - timedelta(days=29)
    prev_end = cur_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=29)
    current = _count(con, cur_start, anchor)
    previous = _count(con, prev_start, prev_end)
    value = None if previous == 0 else round((current - previous) / previous * 100, 1)
    return MetricResult(
        name="case_growth_rate",
        value=value,
        unit="%",
        numerator=current,
        denominator=previous,
        unknown_excluded=0,
        window_start=cur_start,
        window_end=anchor,
        definition="(cases in last 30 days - cases in the previous 30 days) / previous 30 days",
        caveat="Recent days are under-counted because of notification lag, which biases the "
        "growth rate downward. Cases are dated by symptom onset (notification date if absent).",
    )


def _rate(
    con: duckdb.DuckDBPyConnection,
    anchor: date,
    *,
    name: str,
    known: str,
    positive: str,
    definition: str,
    caveat: str,
) -> MetricResult:
    start = anchor - timedelta(days=RATE_WINDOW_DAYS - 1)
    total = _count(con, start, anchor)
    denominator = _count(con, start, anchor, known)
    numerator = _count(con, start, anchor, positive)
    value = None if denominator == 0 else round(numerator / denominator * 100, 1)
    return MetricResult(
        name=name,
        value=value,
        unit="%",
        numerator=numerator,
        denominator=denominator,
        unknown_excluded=total - denominator,
        window_start=start,
        window_end=anchor,
        definition=definition,
        caveat=caveat,
    )


def mortality_rate(con: duckdb.DuckDBPyConnection, anchor: date) -> MetricResult:
    return _rate(
        con,
        anchor,
        name="mortality_rate",
        known="outcome IN (1, 2, 3)",
        positive="outcome IN (2, 3)",
        definition="deaths (EVOLUCAO 2 or 3) / cases with known outcome, last 12 months",
        caveat="In-hospital case fatality among notified SRAG cases, not population mortality. "
        "Cases still open or with unknown outcome are excluded, which can bias the rate.",
    )


def icu_admission_rate(con: duckdb.DuckDBPyConnection, anchor: date) -> MetricResult:
    return _rate(
        con,
        anchor,
        name="icu_admission_rate",
        known="icu IS NOT NULL",
        positive="icu",
        definition="cases admitted to ICU (UTI=1) / cases with known ICU field, last 12 months",
        caveat="PROXY. True ICU occupancy needs bed capacity, which this dataset does not "
        "contain. This is the share of notified SRAG hospitalisations that required ICU.",
    )


def vaccination_rate(con: duckdb.DuckDBPyConnection, anchor: date) -> MetricResult:
    return _rate(
        con,
        anchor,
        name="vaccination_rate",
        known="covid_vaccinated IS NOT NULL",
        positive="covid_vaccinated",
        definition="cases that received a COVID-19 vaccine (VACINA_COV=1) / cases with known "
        "vaccination field, last 12 months",
        caveat="PROXY. True population coverage needs a population denominator, absent here. "
        "This is the vaccinated share among notified SRAG cases, not among the population.",
    )


def all_metrics(con: duckdb.DuckDBPyConnection) -> list[MetricResult]:
    anchor = anchor_date(con)
    return [
        case_growth_rate(con, anchor),
        mortality_rate(con, anchor),
        icu_admission_rate(con, anchor),
        vaccination_rate(con, anchor),
    ]


def daily_cases(con: duckdb.DuckDBPyConnection, anchor: date, days: int = 30) -> dict[date, int]:
    start = anchor - timedelta(days=days - 1)
    rows = con.execute(
        f"SELECT event_date, count(*) FROM {TABLE} WHERE event_date BETWEEN ? AND ? "
        "GROUP BY 1",
        [start, anchor],
    ).fetchall()
    found = {r[0]: int(r[1]) for r in rows}
    return {start + timedelta(days=i): found.get(start + timedelta(days=i), 0) for i in range(days)}


def monthly_cases(
    con: duckdb.DuckDBPyConnection, anchor: date, months: int = 12
) -> dict[str, int]:
    first = date(anchor.year, anchor.month, 1)
    month_starts: list[date] = []
    y, m = first.year, first.month
    for _ in range(months):
        month_starts.append(date(y, m, 1))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    month_starts.reverse()
    rows = con.execute(
        f"SELECT strftime(date_trunc('month', event_date), '%Y-%m'), count(*) FROM {TABLE} "
        "WHERE event_date BETWEEN ? AND ? GROUP BY 1",
        [month_starts[0], anchor],
    ).fetchall()
    found = {r[0]: int(r[1]) for r in rows}
    return {d.strftime("%Y-%m"): found.get(d.strftime("%Y-%m"), 0) for d in month_starts}
