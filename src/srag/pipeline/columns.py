"""Columns we keep from the DATASUS SRAG csv.

We read with an allowlist so names, cpf, address etc never even get loaded (LGPD).
"""

from __future__ import annotations

KEEP_COLUMNS: tuple[str, ...] = (
    "DT_NOTIFIC",  # notification date
    "DT_SIN_PRI",  # symptom onset, main date we use
    "SG_UF",  # state, nothing finer than this
    "CS_SEXO",
    "NU_IDADE_N",  # age, turned into a band later then dropped
    "TP_IDADE",  # 1 days, 2 months, 3 years
    "UTI",  # 1 yes, 2 no, 9 unknown
    "EVOLUCAO",  # 1 cure, 2 death srag, 3 death other, 9 unknown
    "CLASSI_FIN",  # 5 = covid, 1 = influenza
    "VACINA_COV",  # covid vaccine 1/2/9
    "VACINA",  # flu vaccine 1/2/9
)

# just for docs, these exist in older files and are never read
EXCLUDED_IDENTIFIER_EXAMPLES: tuple[str, ...] = (
    "NM_PACIENT",
    "NU_CPF",
    "NU_CNS",
    "DT_NASC",
    "NM_MAE_PAC",
    "NU_CEP",
    "NM_LOGRADO",
    "NM_BAIRRO",
    "NU_TELEFON",
    "ID_MUNICIP",
)

# 9 means "ignorado", we turn it into null
IGNORED_CODE_COLUMNS: tuple[str, ...] = ("UTI", "EVOLUCAO", "VACINA_COV", "VACINA")
