"""LLM step: give one claim a verdict against the full sources."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Sequence

from groundlint.llm import Chat, ask_json
from groundlint.models import Claim, Judgment, Source, Verdict

MAX_PARALLEL = 6

SYSTEM = """You check one claim against the given sources, and only those sources. Ignore what you know from elsewhere.

Verdicts:
- "supported": the sources state the claim or directly entail it. Every part must be covered, including numbers, units, frequency, qualifiers ("at least", "up to") and population ("all", "most", a subgroup).
- "contradicted": the sources conflict with the claim (a different number for the same thing, the opposite finding, a stated restriction or "not needed" that the claim denies).
- "unsupported": the sources don't establish the claim. Partial support, overgeneralizing a population, or a topic the sources don't cover all land here.

When unsure between supported and another verdict, don't choose supported.

"quote": copy the single most relevant passage from the source verbatim, character for character, without adding, removing or changing words. For "supported" it must be the passage that supports the claim. For "contradicted" it must be the passage that conflicts. For "unsupported" use the closest relevant passage, or "" if nothing is relevant.
"source": the file name exactly as given in the <source path="..."> tag the quote comes from, or "" if the quote is "".
"explanation": one or two sentences saying why. For "unsupported", say which part is missing.

Reply with only JSON in this shape:
{"verdict": "supported|unsupported|contradicted", "explanation": "...", "quote": "...", "source": "..."}"""


def _sources_block(sources: Sequence[Source]) -> str:
    return "\n\n".join(f'<source path="{s.path}">\n{s.text}\n</source>' for s in sources)


def _validator(claim: Claim):
    def validate(data: Any) -> Judgment:
        verdict = Verdict(str(data["verdict"]).strip().lower())
        return Judgment(
            claim=claim.claim,
            sentence=claim.sentence,
            verdict=verdict,
            explanation=str(data.get("explanation") or "").strip(),
            quote=str(data.get("quote") or "").strip(),
            source_path=str(data.get("source") or "").strip(),
        )

    return validate


def judge(claim: Claim, sources: Sequence[Source], chat: Chat) -> Judgment:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Sources:\n{_sources_block(sources)}\n\nClaim: {claim.claim}"},
    ]
    return ask_json(chat, messages, _validator(claim))


def judge_all(claims: Sequence[Claim], sources: Sequence[Source], chat: Chat) -> list[Judgment]:
    """Judge every claim, several at a time, keeping the claims' order."""
    if not claims:
        return []
    with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL, len(claims))) as pool:
        return list(pool.map(lambda c: judge(c, sources, chat), claims))
