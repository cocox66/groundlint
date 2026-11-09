"""Shared data types passed between pipeline steps."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Verdict(str, Enum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"


@dataclass(frozen=True)
class Source:
    path: str
    text: str


@dataclass(frozen=True)
class Downgrade:
    """A code rule that turned a `supported` verdict into `unsupported`."""

    rule: str
    reason: str


@dataclass(frozen=True)
class Judgment:
    claim: str
    sentence: str
    verdict: Verdict
    explanation: str
    quote: str
    source_path: str
    downgrades: tuple[Downgrade, ...] = field(default_factory=tuple)
