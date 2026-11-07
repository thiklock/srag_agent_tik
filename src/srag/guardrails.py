"""Guardrails: input check, sql guard, news cleanup and the output number check."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

DISCLAIMER = (
    "This report is generated automatically from public DATASUS data for informational "
    "purposes only. It is not medical advice and must not be used for diagnosis or "
    "treatment. ICU and vaccination figures are proxies (see definitions)."
)

# input

_INJECTION = re.compile(
    r"ignore (all |any |the )?(previous|prior|above) (instructions|rules)|"
    r"disregard (the )?(system|previous)|reveal (your )?(system )?prompt|"
    r"you are now|jailbreak|developer mode|"
    r"ignore (as )?instru[cç][õo]es|desconsidere (as )?instru[cç][õo]es",
    re.IGNORECASE,
)
_MEDICAL_ADVICE = re.compile(
    r"\b(should i (take|use)|what (medication|drug|dose)|diagnos[ei]|prescri|"
    r"treat(ment)? (for )?my|devo tomar|qual (rem[eé]dio|dose)|me diagnostique|"
    r"tratamento para mim)\b",
    re.IGNORECASE,
)
_SCOPE = re.compile(
    r"\b(srag|sars|covid|influenza|flu|respirat|report|relat[oó]rio|metric|m[eé]trica|"
    r"mortality|mortalidade|icu|uti|vaccin|vacina|cases|casos|growth|crescimento|news|"
    r"not[ií]cias|chart|gr[aá]fico|datasus|hospital)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    reason: str = ""


def check_input(request: str) -> GuardResult:
    """Refuse injection attempts, medical advice and anything off topic."""
    if len(request) > 2000:
        return GuardResult(False, "Request too long.")
    if _INJECTION.search(request):
        return GuardResult(False, "Possible prompt-injection attempt detected.")
    if _MEDICAL_ADVICE.search(request):
        return GuardResult(False, "I cannot give medical advice, diagnosis or treatment.")
    if not _SCOPE.search(request):
        return GuardResult(False, "Out of scope: I only produce SRAG surveillance reports.")
    return GuardResult(True)


# sql

ALLOWED_TABLES = {"srag_cases"}
_FORBIDDEN_SQL = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|copy|export|import|pragma|call|"
    r"install|load|set|truncate|replace|read_csv|read_parquet|read_json|glob)\b",
    re.IGNORECASE,
)
_TABLE_REF = re.compile(r"\b(?:from|join)\s+([a-zA-Z_][\w.]*)", re.IGNORECASE)


def check_sql(sql: str) -> GuardResult:
    """Only one plain select on the allowed table, nothing else."""
    stripped = sql.strip().rstrip(";").strip()
    if ";" in stripped:
        return GuardResult(False, "Multiple statements are not allowed.")
    if "--" in stripped or "/*" in stripped:
        return GuardResult(False, "SQL comments are not allowed.")
    if not re.match(r"^(select|with)\b", stripped, re.IGNORECASE):
        return GuardResult(False, "Only SELECT queries are allowed.")
    if _FORBIDDEN_SQL.search(stripped):
        return GuardResult(False, "Query contains a forbidden keyword.")
    tables = {t.lower() for t in _TABLE_REF.findall(stripped)}
    if not tables or not tables <= ALLOWED_TABLES:
        return GuardResult(False, f"Only these tables are allowed: {sorted(ALLOWED_TABLES)}.")
    return GuardResult(True)


# news

NEWS_DOMAIN_ALLOWLIST = (
    "who.int",
    "paho.org",
    "gov.br",
    "fiocruz.br",
    "agenciabrasil.ebc.com.br",
    "g1.globo.com",
    "folha.uol.com.br",
    "estadao.com.br",
    "cnnbrasil.com.br",
    "reuters.com",
    "bbc.com",
    "bvsms.saude.gov.br",
)
_NEWS_INJECTION = re.compile(
    r"ignore .{0,30}instructions|system prompt|you must|assistant:|<\s*/?\s*(system|script)",
    re.IGNORECASE,
)


def domain_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in NEWS_DOMAIN_ALLOWLIST)


def sanitize_news_text(text: str, max_len: int = 300) -> str | None:
    """Strip html, squash whitespace, drop anything that looks like an injected instruction."""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()[:max_len]
    if not clean or _NEWS_INJECTION.search(clean):
        return None
    return clean


# output

_DATE_RE = re.compile(r"\b\d{4}-\d{2}(-\d{2})?\b|\b\d{1,2}/\d{1,2}/\d{4}\b")
_NAME_RE = re.compile(r"\b(?:[A-Za-z]+-)+\d+\b|\b[A-Za-z]+\d+[A-Za-z0-9]*\b")
_NUM_RE = re.compile(r"(?<![\w.])-?\d+(?:[.,]\d+)*(?![\w])")


def _to_float(token: str) -> float | None:
    t = token.replace(",", "") if re.search(r"\d,\d{3}\b", token) else token.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def numbers_in(text: str) -> list[float]:
    """Pull numbers out of text, skipping dates and names like COVID-19 or H1N1."""
    without_dates = _DATE_RE.sub(" ", text)
    without_dates = _NAME_RE.sub(" ", without_dates)
    values = (_to_float(m.group()) for m in _NUM_RE.finditer(without_dates))
    return [v for v in values if v is not None]


@dataclass
class NumberCheck:
    ok: bool
    unsupported: list[float] = field(default_factory=list)


def validate_numbers(narrative: str, allowed: list[float], *, tol: float = 0.051) -> NumberCheck:
    """Every number in the text has to match a computed one (small rounding slack).

    Sign is ignored so "fell 12.5%" matches -12.5.
    """
    pool = [abs(a) for a in allowed]
    bad: list[float] = []
    for n in numbers_in(narrative):
        if not any(abs(abs(n) - a) <= tol or abs(abs(n) - round(a)) <= 1e-9 for a in pool):
            bad.append(n)
    return NumberCheck(ok=not bad, unsupported=bad)
