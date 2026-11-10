"""Terminal report and --json output. Works on data only; never calls the LLM."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Sequence

from groundlint.models import Judgment, Verdict

ORDER = (Verdict.CONTRADICTED, Verdict.UNSUPPORTED, Verdict.SUPPORTED)
HEADINGS = {
    Verdict.CONTRADICTED: "CONTRADICTED: the sources conflict with these claims",
    Verdict.UNSUPPORTED: "UNSUPPORTED: the sources don't establish these claims",
    Verdict.SUPPORTED: "SUPPORTED",
}


def counts(judgments: Sequence[Judgment]) -> dict[str, int]:
    return {v.value: sum(j.verdict is v for j in judgments) for v in ORDER}


def flagged(judgments: Sequence[Judgment]) -> bool:
    return any(j.verdict is not Verdict.SUPPORTED for j in judgments)


def to_json(judgments: Sequence[Judgment], model: str) -> str:
    data = {
        "model": model,
        "flagged": flagged(judgments),
        "counts": counts(judgments),
        "claims": [asdict(j) for j in judgments],
    }
    return json.dumps(data, indent=2, ensure_ascii=False, default=lambda v: v.value)


def _indent(label: str, text: str) -> str:
    return f"    {label:<12}{text}"


def to_text(judgments: Sequence[Judgment], model: str) -> str:
    lines: list[str] = []
    number = {id(j): i for i, j in enumerate(judgments, 1)}
    for verdict in ORDER:
        group = [j for j in judgments if j.verdict is verdict]
        if not group:
            continue
        lines += [f"== {HEADINGS[verdict]} ({len(group)}) ==", ""]
        for j in group:
            lines.append(f"[{number[id(j)]}] {j.claim}")
            if j.sentence and j.sentence != j.claim:
                lines.append(_indent("sentence:", j.sentence))
            for d in j.downgrades:
                lines.append(_indent("CODE RULE:", f"{d.rule} rule downgraded the LLM's 'supported': {d.reason}"))
            if j.explanation:
                lines.append(_indent("why:", j.explanation))
            if j.quote:
                lines.append(_indent("source:", j.source_path or "(none named)"))
                lines.append(_indent("quote:", f'"{j.quote}"'))
            lines.append("")
    if not judgments:
        lines += ["No factual claims were found in the answer.", ""]
    total = counts(judgments)
    summary = ", ".join(f"{n} {v}" for v, n in total.items())
    lines.append(f"{len(judgments)} claims: {summary}  (model: {model})")
    lines.append("groundlint can miss errors. Check flagged claims, and spot-check supported ones.")
    return "\n".join(lines)
