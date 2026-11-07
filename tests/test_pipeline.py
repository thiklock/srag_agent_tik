from __future__ import annotations

import duckdb
import pandas as pd

from srag.pipeline.clean import age_in_years, clean, parse_dates


def test_parse_dates_handles_both_formats_and_junk() -> None:
    out = parse_dates(pd.Series(["15/03/2024", "2024-03-15", "99/99/9999", None]))
    assert out.iloc[0] == out.iloc[1] == pd.Timestamp("2024-03-15")
    assert out.iloc[2:].isna().all()


def test_parse_dates_handles_portal_iso_timestamps() -> None:
    out = parse_dates(pd.Series(["2024-08-28T00:00:00.000Z", "2024-01-02T10:30:00Z"]))
    assert list(out) == [pd.Timestamp("2024-08-28"), pd.Timestamp("2024-01-02")]


def test_age_in_years_units() -> None:
    out = age_in_years(pd.Series(["30", "6", "365", "200"]), pd.Series(["3", "2", "1", "3"]))
    assert out.iloc[0] == 30
    assert out.iloc[1] == 0.5
    assert out.iloc[2] == 1.0
    assert pd.isna(out.iloc[3])  # implausible age


def test_clean_recodes_ignored_codes_and_falls_back_to_notification_date() -> None:
    raw = pd.DataFrame(
        {
            "DT_NOTIFIC": ["10/05/2024", "10/05/2024", "10/05/1900"],
            "DT_SIN_PRI": [None, "08/05/2024", "10/05/1900"],
            "UTI": ["9", "1", "2"],
            "EVOLUCAO": ["9", "2", "1"],
            "VACINA_COV": ["", "1", "2"],
        }
    )
    out = clean(raw, salt="s", today=pd.Timestamp("2024-12-31"))
    assert len(out) == 2  # 1900 row dropped as implausible
    assert pd.isna(out.loc[0, "icu"]) and pd.isna(out.loc[0, "outcome"])
    assert bool(out.loc[0, "event_date_is_fallback"]) is True
    assert out.loc[1, "icu"]


def test_clean_rejects_non_allowlisted_columns() -> None:
    raw = pd.DataFrame({"DT_NOTIFIC": ["10/05/2024"], "NM_PACIENT": ["Jane Doe"]})
    try:
        clean(raw, salt="s")
    except ValueError as exc:
        assert "NM_PACIENT" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_pii_never_reaches_database(db_path) -> None:  # type: ignore[no-untyped-def]
    con = duckdb.connect(str(db_path), read_only=True)
    cols = {r[0].upper() for r in con.execute("DESCRIBE srag_cases").fetchall()}
    assert not cols & {"NM_PACIENT", "NU_CPF", "DT_NASC", "NM_MAE_PAC", "NU_IDADE_N"}
    ids = [r[0] for r in con.execute("SELECT record_id FROM srag_cases LIMIT 20").fetchall()]
    assert all(len(i) == 16 and "PATIENT" not in i for i in ids)
    assert con.execute("SELECT count(DISTINCT record_id) = count(*) FROM srag_cases").fetchone()[0]
    con.close()
