"""LLM step: split an answer into atomic claims, each linked to its original sentence."""

from __future__ import annotations

from typing import Any

from groundlint.llm import Chat, ask_json
from groundlint.models import Claim

SYSTEM = """You split an answer into atomic factual claims so each can be checked against sources.

Rules:
- One claim per checkable fact. Split sentences that join several facts ("X and Y", "A, then B").
- Make each claim stand alone: replace pronouns and vague references with the names they refer to.
- Keep every number, unit, dose, frequency, qualifier ("at least", "up to", "all", "only") and population exactly as written. Never round, generalize or correct.
- Skip text that states no fact: greetings, hedges about yourself, questions, advice to consult a doctor, headings.
- "sentence" is the exact sentence from the answer that the claim comes from, copied verbatim.
- Don't drop any factual claim, even one you think is wrong.

Reply with only JSON in this shape:
{"claims": [{"claim": "...", "sentence": "..."}]}"""


def _validate(data: Any) -> list[Claim]:
    items = data["claims"]
    if not isinstance(items, list):
        raise ValueError("'claims' is not a list")
    claims = []
    for item in items:
        claim = str(item["claim"]).strip()
        if claim:
            claims.append(Claim(claim=claim, sentence=str(item.get("sentence") or claim).strip()))
    return claims


def extract(answer: str, chat: Chat) -> list[Claim]:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Answer:\n<answer>\n{answer}\n</answer>"},
    ]
    return ask_json(chat, messages, _validate)
