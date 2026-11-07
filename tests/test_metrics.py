from __future__ import annotations

from datetime import date

import duckdb

from srag.metrics import (
    all_metrics,
    anchor_date,
    case_growth_rate,
    daily_cases,
    monthly_cases,
    mortality_rate,
)


def _mem(rows: list[tuple]) -> duckdb.DuckDBPyConnection:  # type: ignore[type-arg]
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE srag_cases(event_date DATE, icu BOOLEAN, outcome TINYINT, "
        "covid_vaccinated BOOLEAN)"
    )
    con.executemany("INSERT INTO srag_cases VALUES (?, ?, ?, ?)", rows)
    return con


def test_growth_rate_exact() -> None:
    # anchor is 03-31 so current = 03-02..03-31 and previous = 01-31..03-01
    recent = (date(2024, 3, 31), None, None, None)
    earlier = (date(2024, 2, 10), None, None, None)
    rows = [recent] * 15 + [earlier] * 10
    con = _mem(rows)
    m = case_growth_rate(con, anchor_date(con))
    assert (m.numerator, m.denominator, m.value) == (15, 10, 50.0)


def test_growth_rate_none_when_previous_is_zero() -> None:
    con = _mem([(date(2024, 3, 31), None, None, None)])
    assert case_growth_rate(con, date(2024, 3, 31)).value is None


def test_mortality_excludes_unknown_outcomes() -> None:
    d = date(2024, 3, 1)
    con = _mem([(d, None, 1, None), (d, None, 2, None), (d, None, 3, None), (d, None, None, None)])
    m = mortality_rate(con, d)
    assert (m.numerator, m.denominator, m.unknown_excluded) == (2, 3, 1)
    assert m.value == 66.7


def test_daily_and_monthly_shapes(con: duckdb.DuckDBPyConnection) -> None:
    anchor = anchor_date(con)
    daily = daily_cases(con, anchor)
    monthly = monthly_cases(con, anchor)
    assert len(daily) == 30 and max(daily) == anchor
    assert len(monthly) == 12 and list(monthly) == sorted(monthly)


def test_all_metrics_in_range(con: duckdb.DuckDBPyConnection) -> None:
    for m in all_metrics(con):
        if m.name != "case_growth_rate":
            assert m.value is not None and 0 <= m.value <= 100
        assert m.caveat
