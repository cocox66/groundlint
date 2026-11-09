"""Code rules that can downgrade a `supported` verdict.

The rules compare text only. They never upgrade a verdict and never touch
`unsupported` or `contradicted` ones. Each failure is recorded as a Downgrade
naming its rule, so the report can tell it apart from the LLM's judgment.

Rules, in order: quote, number (with units), comparison, frequency.

The digit-boundary behavior of the number rule (8 is not found inside 18, and
1 is not found inside 1.04) follows the value matching in Soundscape's grounding
gate, https://github.com/cocox66/soundscape (MIT License). Soundscape matches
known values in text. This module instead extracts every quantity from both
sides, which gives the same boundaries by construction.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Iterable, NamedTuple

from groundlint.models import Downgrade, Judgment, Source, Verdict

# --- Text normalization ------------------------------------------------------

_CHAR_MAP = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "‐": "-",
        "‑": "-",
        "‒": "-",
        "–": "-",
        "—": "-",
        "−": "-",
    }
)


def _normalize(text: str) -> str:
    """NFKC (so µ and μ agree), ASCII quotes and dashes, collapsed whitespace, casefolded."""
    text = unicodedata.normalize("NFKC", text).translate(_CHAR_MAP)
    return " ".join(text.split()).casefold()


# --- Quantities --------------------------------------------------------------

class _Unit(NamedTuple):
    family: str
    to_base: Decimal  # multiply by this to get the family's base unit


_UNITS: dict[str, _Unit] = {
    "mcg": _Unit("mass", Decimal("0.000001")),
    "μg": _Unit("mass", Decimal("0.000001")),
    "mg": _Unit("mass", Decimal("0.001")),
    "g": _Unit("mass", Decimal("1")),
    "kg": _Unit("mass", Decimal("1000")),
    "ml": _Unit("volume", Decimal("0.001")),
    "l": _Unit("volume", Decimal("1")),
    "h": _Unit("short time", Decimal("1")),
    "hr": _Unit("short time", Decimal("1")),
    "hrs": _Unit("short time", Decimal("1")),
    "hour": _Unit("short time", Decimal("1")),
    "hours": _Unit("short time", Decimal("1")),
    "day": _Unit("short time", Decimal("24")),
    "days": _Unit("short time", Decimal("24")),
    "wk": _Unit("short time", Decimal("168")),
    "wks": _Unit("short time", Decimal("168")),
    "week": _Unit("short time", Decimal("168")),
    "weeks": _Unit("short time", Decimal("168")),
    "mo": _Unit("long time", Decimal("1")),
    "month": _Unit("long time", Decimal("1")),
    "months": _Unit("long time", Decimal("1")),
    "yr": _Unit("long time", Decimal("12")),
    "yrs": _Unit("long time", Decimal("12")),
    "year": _Unit("long time", Decimal("12")),
    "years": _Unit("long time", Decimal("12")),
}

# A digit run that directly follows a letter, or a letter and a hyphen, is part
# of a name (cyp3a4, her2, il-6, covid-19), not a quantity.
_NUMBER = re.compile(r"(?<![a-z0-9.])(?<![a-z]-)(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(%?)")
_UNIT = re.compile(
    r"(?:\s?|-)(" + "|".join(sorted(map(re.escape, _UNITS), key=len, reverse=True)) + r")(?![a-z0-9μ])"
)
_CONNECTOR = re.compile(r"\s*(?:,\s*(?:or|and)?|or|and|to|-)\s*")

# Longest phrases first, so "no more than" is never read as "more than".
_QUALIFIERS: list[tuple[str, str]] = [
    ("no more than", "at most"),
    ("not more than", "at most"),
    ("no less than", "at least"),
    ("not less than", "at least"),
    ("greater than", "above"),
    ("fewer than", "below"),
    ("less than", "below"),
    ("more than", "above"),
    ("at least", "at least"),
    ("up to", "at most"),
    ("<=", "at most"),
    (">=", "at least"),
    ("≤", "at most"),
    ("≥", "at least"),
    ("<", "below"),
    (">", "above"),
]

_FREQUENCY = re.compile(r"\b(once|twice|three times|[123] times)[\s-]+(daily|a day|per day)\b")
_FREQUENCY_COUNT = {"once": 1, "twice": 2, "three times": 3, "1 times": 1, "2 times": 2, "3 times": 3}
_FREQUENCY_NAME = {1: "once daily", 2: "twice daily", 3: "three times daily"}


@dataclass(frozen=True)
class _Quantity:
    number: Decimal  # as written, before unit conversion
    unit: str | None
    qualifier: str  # a group from _QUALIFIERS, or "none"
    start: int
    end: int
    rate: bool = False  # mg/kg and the like: unit not checked, compared by value only

    @property
    def family(self) -> str | None:
        return _UNITS[self.unit].family if self.unit else None

    @property
    def bare(self) -> _Quantity:
        """The same quantity without its comparison qualifier, for messages."""
        return replace(self, qualifier="none")

    @property
    def base_value(self) -> Decimal:
        return self.number * _UNITS[self.unit].to_base if self.unit else self.number

    def __str__(self) -> str:
        number = format(self.number.normalize(), "f")
        text = f"{number} {self.unit}" if self.unit else number
        return text if self.qualifier == "none" else f"{self.qualifier} {text}"


def _qualifier_before(text: str, start: int) -> str:
    prefix = text[:start].rstrip()
    for phrase, group in _QUALIFIERS:
        if prefix.endswith(phrase):
            before = prefix[: -len(phrase)]
            if not phrase[0].isalpha() or not before or not before[-1].isalnum():
                return group
    return "none"


def _frequency_spans(text: str) -> list[tuple[int, int, int]]:
    return [(m.start(), m.end(), _FREQUENCY_COUNT[m.group(1)]) for m in _FREQUENCY.finditer(text)]


def _quantities(text: str) -> list[_Quantity]:
    """Every quantity in normalized text, with list and range members sharing their last unit."""
    frequency = _frequency_spans(text)
    found: list[_Quantity] = []
    for match in _NUMBER.finditer(text):
        if any(start <= match.start() < end for start, end, _ in frequency):
            continue
        number = Decimal(match.group(1).replace(",", "") + (match.group(2) or ""))
        unit, end, rate = None, match.end(), False
        if not match.group(3):
            unit_match = _UNIT.match(text, match.end())
            if unit_match and not text.startswith("/", unit_match.end()):
                unit, end = unit_match.group(1), unit_match.end()
            elif unit_match:  # a rate such as mg/kg: compared by value only
                end, rate = unit_match.end(), True
        found.append(_Quantity(number, unit, _qualifier_before(text, match.start()), match.start(), end, rate))

    # Group numbers joined by connectors ("5, 10 or 20 mg", "10-20 mg") and give
    # the group's last unit to the members that have none.
    result: list[_Quantity] = []
    group: list[_Quantity] = []
    for quantity in found + [None]:
        if quantity is not None and group and _CONNECTOR.fullmatch(text, group[-1].end, quantity.start):
            group.append(quantity)
            continue
        if group:
            last_unit = group[-1].unit
            result.extend(replace(q, unit=q.unit or last_unit) for q in group)
        group = [quantity] if quantity is not None else []
    return result


# --- Rules -------------------------------------------------------------------


def _quote_rule(quote: str, judgment: Judgment, sources: Iterable[Source]) -> str | None:
    if not quote:
        return "quote is empty"
    source = next((s for s in sources if s.path == judgment.source_path), None)
    if source is None:
        return f"cited source not loaded: {judgment.source_path}"
    if not _quote_pattern(quote).search(_normalize(source.text)):
        return f"quote not found in {judgment.source_path}"
    return None


def _quote_pattern(quote: str) -> re.Pattern[str]:
    """Match the quote only where it isn't cut from inside a longer word or number.

    Without this, the quote "5 mg" would be found inside "2.5 mg" and "10 mg" inside "110 mg".
    """
    before = r"(?<!\w)(?<!\d\.)" if quote[0].isalnum() else ""
    after = r"(?!\w)(?!\.\d)" if quote[-1].isalnum() else ""
    return re.compile(before + re.escape(quote) + after)


def _match(claimed: _Quantity, quoted: list[_Quantity]) -> _Quantity | None:
    """The quote quantity matching a claim quantity, preferring one with the same qualifier."""
    if claimed.unit:
        candidates = [
            q
            for q in quoted
            if (q.family == claimed.family and q.base_value == claimed.base_value)
            or (q.rate and q.number == claimed.number)
        ]
    else:
        candidates = [q for q in quoted if q.number == claimed.number]
    same_qualifier = [q for q in candidates if q.qualifier == claimed.qualifier]
    pool = same_qualifier or candidates
    return pool[0] if pool else None


def _number_and_comparison_rules(claim: list[_Quantity], quote: list[_Quantity]) -> tuple[str | None, str | None]:
    number_failures, comparison_failures = [], []
    for claimed in claim:
        matched = _match(claimed, quote)
        if matched is None:
            same_number = next((q for q in quote if q.number == claimed.number), None)
            if claimed.unit and same_number is not None:
                quoted_text = str(same_number.bare)
                if not same_number.unit:
                    quoted_text += " (no unit)"
                number_failures.append(
                    f"unit mismatch: claim {claimed.bare}, quote {quoted_text}"
                )
            else:
                number_failures.append(f"number missing: claim {claimed.bare} not in quote")
        elif matched.qualifier != claimed.qualifier:
            comparison_failures.append(f"comparison mismatch: claim {claimed}, quote {matched}")
    return ("; ".join(number_failures) or None, "; ".join(comparison_failures) or None)


def _frequency_rule(claim_text: str, quote_text: str) -> str | None:
    quoted = {count for _, _, count in _frequency_spans(quote_text)}
    found = ", ".join(_FREQUENCY_NAME[c] for c in sorted(quoted)) or "none"
    failures = []
    for _, _, count in _frequency_spans(claim_text):
        if count not in quoted:
            failures.append(f"frequency mismatch: claim {_FREQUENCY_NAME[count]}, quote {found}")
    return "; ".join(failures) or None


def check(judgment: Judgment, sources: Iterable[Source]) -> Judgment:
    """Return the judgment, downgraded to `unsupported` if any code rule fails."""
    if judgment.verdict is not Verdict.SUPPORTED:
        return judgment

    claim_text, quote_text = _normalize(judgment.claim), _normalize(judgment.quote)
    number, comparison = _number_and_comparison_rules(_quantities(claim_text), _quantities(quote_text))
    results = [
        ("quote", _quote_rule(quote_text, judgment, sources)),
        ("number", number),
        ("comparison", comparison),
        ("frequency", _frequency_rule(claim_text, quote_text)),
    ]
    downgrades = tuple(Downgrade(rule, reason) for rule, reason in results if reason)
    if not downgrades:
        return judgment
    return replace(
        judgment,
        verdict=Verdict.UNSUPPORTED,
        downgrades=judgment.downgrades + downgrades,
    )
