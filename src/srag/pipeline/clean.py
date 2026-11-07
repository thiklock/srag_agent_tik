"""Cleaning + anonymising the srag dataframe. Plain functions so they're easy to test."""

from __future__ import annotations

import hashlib

import pandas as pd

from srag.pipeline.columns import IGNORED_CODE_COLUMNS, KEEP_COLUMNS

MIN_YEAR = 2009  # sivep-gripe starts here, anything before is a typo
AGE_BINS = [-1, 4, 17, 39, 59, 79, 200]
AGE_LABELS = ["0-4", "5-17", "18-39", "40-59", "60-79", "80+"]


def parse_dates(series: pd.Series) -> pd.Series:
    """Parse dates, bad ones become NaT.

    The portal files use things like 2024-08-28T00:00:00.000Z, older ones use dd/mm/yyyy.
    """
    s = series.astype("string").str.strip()
    # keep only the date part of iso timestamps
    s = s.where(~s.str.match(r"^\d{4}-\d{2}-\d{2}", na=False), s.str.slice(0, 10))
    iso = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    br = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
    return iso.fillna(br)


def age_in_years(value: pd.Series, unit: pd.Series) -> pd.Series:
    """NU_IDADE_N + TP_IDADE (1 days, 2 months, 3 years) -> years."""
    v = pd.to_numeric(value, errors="coerce")
    u = pd.to_numeric(unit, errors="coerce")
    years = v.where(u == 3)
    years = years.fillna((v / 12).where(u == 2)).fillna((v / 365).where(u == 1))
    return years.where((years >= 0) & (years <= 120))


def pseudonymise(index: pd.Index, salt: str) -> pd.Series:
    """Salted sha256 of the row position, cut to 16 chars. Can't be reversed."""
    return pd.Series(
        [hashlib.sha256(f"{salt}:{i}".encode()).hexdigest()[:16] for i in index],
        index=index,
        dtype="string",
    )


def clean(raw: pd.DataFrame, *, salt: str, today: pd.Timestamp | None = None) -> pd.DataFrame:
    """Clean a raw frame that only has the allowlisted columns.

    Parses dates, picks event_date (onset, else notification), turns the 9 codes into null,
    bands the age, drops impossible dates and swaps the row id for a hash.
    """
    today = today or pd.Timestamp.today().normalize()
    df = raw.copy()
    df.columns = [c.upper() for c in df.columns]
    unexpected = set(df.columns) - set(KEEP_COLUMNS)
    if unexpected:
        raise ValueError(f"Columns outside the allowlist reached clean(): {sorted(unexpected)}")
    for col in KEEP_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    df["DT_NOTIFIC"] = parse_dates(df["DT_NOTIFIC"])
    df["DT_SIN_PRI"] = parse_dates(df["DT_SIN_PRI"])
    df["event_date"] = df["DT_SIN_PRI"].fillna(df["DT_NOTIFIC"])
    df["event_date_is_fallback"] = df["DT_SIN_PRI"].isna() & df["DT_NOTIFIC"].notna()

    for col in IGNORED_CODE_COLUMNS:
        code = pd.to_numeric(df[col], errors="coerce")
        df[col] = code.where(code.isin([1, 2, 3]))  # 9, blanks and junk -> nan

    df["classi_fin"] = pd.to_numeric(df["CLASSI_FIN"], errors="coerce")
    df["age_years"] = age_in_years(df["NU_IDADE_N"], df["TP_IDADE"])
    df["age_band"] = pd.cut(df["age_years"], bins=AGE_BINS, labels=AGE_LABELS).astype("string")
    df["sex"] = df["CS_SEXO"].astype("string").str.upper().where(lambda s: s.isin(["M", "F"]))

    valid = df["event_date"].between(pd.Timestamp(f"{MIN_YEAR}-01-01"), today)
    df = df.loc[valid].copy()

    out = pd.DataFrame(
        {
            "record_id": pseudonymise(df.index, salt),
            "event_date": df["event_date"].dt.date,
            "event_date_is_fallback": df["event_date_is_fallback"],
            "state": df["SG_UF"].astype("string").str.upper(),
            "sex": df["sex"],
            "age_band": df["age_band"],
            "icu": df["UTI"].map({1: True, 2: False}).astype("boolean"),
            "outcome": df["EVOLUCAO"].astype("Int8"),
            "classi_fin": df["classi_fin"].astype("Int8"),
            "covid_vaccinated": df["VACINA_COV"].map({1: True, 2: False}).astype("boolean"),
            "flu_vaccinated": df["VACINA"].map({1: True, 2: False}).astype("boolean"),
        }
    )
    return out.reset_index(drop=True)
