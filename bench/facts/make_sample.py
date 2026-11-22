"""Build bench/facts/sample.jsonl: 20 medical examples from FACTS Grounding.

Downloads the public examples from Hugging Face at a pinned revision, scores
each row by how many distinct medical terms it uses, shuffles the qualifying
rows with a fixed seed and keeps the first N that aren't excluded by hand.

Standard library only. No LLM calls.

    python3 bench/facts/make_sample.py
"""

from __future__ import annotations

import csv
import http.client
import io
import json
import random
import re
import sys
import urllib.request
from pathlib import Path

DATASET = "google/FACTS-grounding-public"
REVISION = "11b6961370aa0ac73c91d58e35317e724b2ac765"
URL = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/examples.csv"

SEED = 0
N = 20
MIN_TERMS = 8  # distinct medical terms a row needs to count as medical

# (name, regex) pairs, matched case-insensitively on word boundaries.
MEDICAL_TERMS = [
    ("patient", r"patients?"),
    ("clinical", r"clinical"),
    ("diagnosis", r"diagnos(?:is|es|ed|e)"),
    ("symptom", r"symptoms?"),
    ("treatment", r"treatments?"),
    ("medication", r"medications?"),
    ("dose", r"doses?|dosage"),
    ("therapy", r"therap(?:y|ies)"),
    ("physician", r"physicians?|doctors?"),
    ("disease", r"diseases?"),
    ("cancer", r"cancers?|tumou?rs?"),
    ("vaccine", r"vaccines?|vaccinations?"),
    ("FDA", r"FDA"),
    ("side effect", r"side effects?"),
    ("contraindicated", r"contraindicat\w*"),
    ("infection", r"infections?"),
    ("chronic", r"chronic"),
    ("surgery", r"surgery|surgical"),
    ("hospital", r"hospitals?"),
    ("prescription", r"prescri(?:be|bed|ption)s?"),
    ("hypertension", r"blood pressure|hypertension"),
    ("diabetes", r"diabetes"),
    ("mg", r"mg"),
    ("trial", r"trials?"),
    ("adverse", r"adverse"),
]
_PATTERNS = [(name, re.compile(rf"\b(?:{rx})\b", re.I)) for name, rx in MEDICAL_TERMS]

# Rows the keyword rule picked that aren't clinical, with the reason.
EXCLUDE: dict[int, str] = {
    460: "legal question about rescheduling marijuana under the Controlled Substances Act",
}

OUT = Path(__file__).resolve().parent / "sample.jsonl"
COLUMNS = ["system_instruction", "user_request", "context_document", "full_prompt"]


def download() -> list[dict[str, str]]:
    for attempt in range(3):
        try:
            with urllib.request.urlopen(URL, timeout=120) as resp:
                text = resp.read().decode("utf-8")
            break
        except (OSError, http.client.IncompleteRead) as e:
            if attempt == 2:
                raise SystemExit(f"download failed: {e}")
            print(f"download failed ({e!r:.80}), retrying", file=sys.stderr)
    csv.field_size_limit(sys.maxsize)
    rows = list(csv.DictReader(io.StringIO(text)))
    missing = set(COLUMNS) - set(rows[0])
    if missing:
        raise SystemExit(f"examples.csv is missing columns: {sorted(missing)}")
    return rows


def medical_terms(row: dict[str, str]) -> list[str]:
    text = row["user_request"] + "\n" + row["context_document"]
    return [name for name, pat in _PATTERNS if pat.search(text)]


def pick(rows: list[dict[str, str]]) -> list[tuple[int, list[str]]]:
    candidates = []
    for i, row in enumerate(rows):
        terms = medical_terms(row)
        if len(terms) >= MIN_TERMS:
            candidates.append((i, terms))
    random.Random(SEED).shuffle(candidates)
    # Walk the shuffled order so excluding a row only replaces that row.
    picked = [c for c in candidates if c[0] not in EXCLUDE][:N]
    if len(picked) < N:
        raise SystemExit(f"only {len(picked)} medical rows found, need {N}")
    print(f"{len(rows)} rows, {len(candidates)} medical candidates, {len(EXCLUDE)} excluded", file=sys.stderr)
    return sorted(picked)


def main() -> None:
    rows = download()
    picked = pick(rows)
    source = f"{DATASET}@{REVISION[:7]}"
    with OUT.open("w", encoding="utf-8") as f:
        for i, terms in picked:
            record = {"id": f"facts-{i}", "row": i}
            record.update({c: rows[i][c] for c in COLUMNS})
            record["medical_terms"] = terms
            record["source"] = source
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    for i, terms in picked:
        request = " ".join(rows[i]["user_request"].split())
        print(f"{i:>4}  {len(terms):>2} terms  {len(rows[i]['context_document']):>6} chars  {request[:90]}")
    print(f"wrote {len(picked)} examples to {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
