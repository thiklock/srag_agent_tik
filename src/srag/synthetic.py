"""Fake srag-looking csv (with fake PII columns too) for tests and demos. Not real data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def make_synthetic_csv(path: Path, n: int = 5000, seed: int = 7, end: str = "2024-12-31") -> Path:
    rng = np.random.default_rng(seed)
    end_ts = pd.Timestamp(end)
    offsets = rng.integers(0, 540, n)
    onset = end_ts - pd.to_timedelta(offsets, unit="D")
    df = pd.DataFrame(
        {
            "DT_NOTIFIC": (onset + pd.Timedelta(days=2)).strftime("%d/%m/%Y"),
            "DT_SIN_PRI": onset.strftime("%d/%m/%Y"),
            "SG_UF": rng.choice(["SP", "RJ", "MG", "BA", "RS"], n),
            "CS_SEXO": rng.choice(["M", "F", "I"], n),
            "NU_IDADE_N": rng.integers(0, 95, n).astype(str),
            "TP_IDADE": "3",
            "UTI": rng.choice(["1", "2", "9", ""], n, p=[0.25, 0.6, 0.1, 0.05]),
            "EVOLUCAO": rng.choice(["1", "2", "3", "9", ""], n, p=[0.6, 0.18, 0.02, 0.1, 0.1]),
            "CLASSI_FIN": rng.choice(["1", "4", "5"], n),
            "VACINA_COV": rng.choice(["1", "2", "9", ""], n, p=[0.35, 0.4, 0.15, 0.1]),
            "VACINA": rng.choice(["1", "2", "9"], n),
            # fake identifiers, these must never make it into the db
            "NM_PACIENT": [f"PATIENT {i}" for i in range(n)],
            "NU_CPF": [f"{i:011d}" for i in range(n)],
            "DT_NASC": "01/01/1980",
            "NM_MAE_PAC": "MOTHER NAME",
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep=";", index=False, encoding="utf-8")
    return path
