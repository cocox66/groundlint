---
title: Code Checks and Sample Cases - Plan
type: feat
date: 2026-11-08
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-plan-bootstrap
execution: code
---

# Code Checks and Sample Cases - Plan

## Goal Capsule

- **Objective:** The test suite shows groundlint catching a fabricated quote and a wrong number in a `supported` verdict on the 3 sample cases, with no API key.
- **Means:** Build `checks.py` and the shared data types first, then hand-written samples and expected labels (KTD1, KTD5).
- **Authority:** `docs/product.md` wins on behavior. `docs/architecture.md` wins on module layout. This plan wins on the details below.
- **Stop conditions:** Stop and ask if no sample source has a license that clearly allows committing it, or if a check rule turns out to need meaning (not just text) to work.
- **Execution profile:** Pure Python, standard library only at runtime. No network or LLM calls in code or tests.
- **Who finishes:** The implementer builds and tests all four units. The user reviews the samples' planted errors before they're used for evals.

## Product Contract

### Summary

Build the code rules that downgrade a `supported` verdict, along with the data types they act on. The rules are quote, number with units, comparison qualifier and dose frequency. Then write 3 biopharma sample cases, each with a source, an answer with planted errors and the expected verdict for each claim. The LLM steps, CLI and report come in later slices.

### Problem Frame

The code checks are the part of groundlint that doesn't depend on an LLM, so they can be built and proven today. The samples are needed anyway for the README demo and the eval set. Building both now means the later LLM steps have working checks and real test material from day one.

### Requirements

**Quote check**

- R1. A `supported` verdict is downgraded to `unsupported` when its quote does not appear in the cited source's text.
- R2. A `supported` verdict is downgraded when its quote is empty or its cited source isn't among the loaded sources.

**Number check**

- R3. A `supported` verdict is downgraded to `unsupported` when any number in the claim does not appear in the quote.
- R10. When a number in the claim has a mass, volume or time unit, it must match a quantity in the quote after converting within the same unit family, so 0.5 g matches 500 mg and 2 weeks matches 14 days. If the quote has the same number with a different unit or no unit, the downgrade reason says "unit mismatch".
- R11. A bare number in the quote counts for a claim quantity with a unit only when it's part of a list or range that ends in a unit of the same family ("5 or 10 mg", "5-10 mg"). "5 mg" does not pass against "5 patients ... 10 mg".

**Comparison check**

- R12. A `supported` verdict is downgraded when a claim number and its matching quote number carry different comparison qualifiers ("up to", "at least", "less than", "more than", `<`, `>`, `≤`, `≥`), including when only one side has a qualifier.

**Frequency check**

- R13. A `supported` verdict is downgraded when the claim states a daily dose frequency (once, twice or three times daily) and the quote doesn't state the same one.

**Both rules**

- R4. The checks never change `unsupported` or `contradicted` verdicts and never upgrade a verdict.
- R5. Each downgrade records which rule fired, so the report can tell it apart from the LLM's judgment.

**Samples**

- R6. 3 sample cases, each with a public biopharma source whose license allows committing it.
- R7. Each sample answer plants all four error types (a changed number, a reversed finding, an overextended population and a claim with no source) alongside some correct claims.
- R8. Each sample has a hand-written expected verdict for every claim. Together the samples give about 20 labeled claims.
- R9. A person can read through one sample in under 5 minutes.

### Scope Boundaries

- No LLM calls, prompts, API keys or `llm.py`.
- No `cli.py`, `report.py` or console entry point.
- No `sources.py` file loading or size limit. Tests build `Source` objects directly from file text.
- Not built: matching spelled-out numbers ("twice", "five"). Digits only in v0. Revisit if a sample shows the LLM writing numbers as words.
- Not built in this slice: rates (mg/kg), percent vs percentage points, other number formats (1.000), and units like IU or mmol/L. These are recorded under "Later" in `docs/decisions.md`. A number with one of them is compared by value alone, as in KTD3.
- Not built: spelled-out mass and volume names ("milligrams", "liters"). Time units do take full words, since text usually spells them out ("12 weeks").

#### Deferred to Follow-Up Work

- Running the samples through DeepEval for comparison (needs an LLM).
- Recording eval results in `docs/evals.md` (needs the full pipeline).

## Planning Contract

### Key Technical Decisions

- KTD1. **Plain dataclasses in `models.py`.** `Source` (path, text), `Judgment` (claim, original sentence, verdict, explanation, quote, source path) and a `Downgrade` record (rule name, short reason). `Judgment` carries a list of downgrades. Dataclasses can be dumped to JSON directly, which `--json` will need later.
- KTD2. **The quote check matches after light normalization.** Collapse runs of whitespace, map curly quotes and Unicode dashes to ASCII, and compare case-insensitively. LLMs often re-wrap lines or change capitals when quoting. Anything more lenient (fuzzy matching) would let a slightly edited quote pass, which defeats the rule.
- KTD3. **The number check compares values, not strings.** Pull digit runs from the claim and the quote, including decimals, thousands commas and a trailing `%`. Compare them as decimal values, so `1,000` matches `1000` and `2.50` matches `2.5`. A hyphen between digits is a range separator, not a minus sign, so "10-20 mg" gives 10 and 20. Skip a digit run that directly follows a letter, or a letter and a hyphen, because it's part of a name (CYP3A4, HER2, HbA1c, IL-6, COVID-19). Digits followed by letters, as in "10mg", still count. A claim with no numbers passes. Start from Soundscape's number and value matching ([cocox66/soundscape](https://github.com/cocox66/soundscape), MIT, with attribution in the file header), as `docs/product.md` plans. Adapt it to these rules and note where its behavior differs.
- KTD7. **A number followed by a unit is one quantity, converted within its family before comparing.** (session-settled: user-directed — chosen over leaving units to the LLM judge and over letting any bare quote number count: a 1000x dose error like 5 mg vs 5 g is exactly the wrong sentence groundlint exists to catch.)
  - Mass: mcg, µg, μg, mg, g, kg. Volume: mL, L. These are abbreviations only and ignore case.
  - Short time: hour(s), hr(s), h, day(s), week(s), wk(s), with base unit hours. 1 day is 24 h and 1 week is 168 h.
  - Long time: month(s), mo, year(s), yr(s), with base unit months. 1 year is 12 months.
  - Days and months aren't converted to each other because the ratio isn't exact. "4 weeks" vs "1 month" is a missing number, not a match.
  - A unit may follow the number after a space, no space or a hyphen ("5 g", "5g", "12-week"). A word boundary must follow the unit, so "5 grade" has no unit.
  - Each quantity becomes (family, value in the base unit) using exact decimal math, so 0.5 g, 500 mg and 500000 mcg are equal.
  - **Lists and ranges share their last unit (R11).** Numbers joined by `,`, "or", "and", "to", `-` or `–` form one group, and a unit after the last number applies to every number in it. "5, 10 or 20 mg" gives 5 mg, 10 mg and 20 mg. A number outside such a group with no unit stays bare.
  - A claim quantity passes only if the quote has an equal quantity in the same family. A bare quote number never satisfies a claim quantity that has a unit.
  - A claim quantity fails with reason "unit mismatch: claim <x>, quote <y>" when the quote has the same number with a different unit or no unit, and nothing matches. Otherwise it fails with the ordinary missing-number reason.
  - A unit followed by `/` (mg/kg) is a rate. It isn't unit-checked and falls back to comparing by value (Later).
  - Unit handling stays inside the number rule, so "unit mismatch" is reason text and not a separate rule.
- KTD8. **The comparison rule checks that qualifiers match for each matched number.** (session-settled: user-directed — chosen over leaving qualifiers to the LLM judge: "up to 20 mg" and "20 mg" are different claims with the same digits.)
  - A qualifier attaches to the number right after it.
  - Synonym groups, matched longest-first so "no more than" is never read as "more than":
    - at most: "up to", "no more than", "not more than", `≤`, `<=`
    - at least: "at least", "no less than", "not less than", `≥`, `>=`
    - below: "less than", "fewer than", `<`
    - above: "more than", "greater than", `>`
  - For each claim number that the number rule matched in the quote, the two qualifier groups must be equal, where "none" is a group. "20 mg" vs "up to 20 mg" fails, and so does the reverse.
  - It's a separate rule named `comparison`, with reason "comparison mismatch: claim <x>, quote <y>". A claim number with no match in the quote is left to the number rule, so the two never double-report one number.
- KTD9. **The frequency rule checks daily dose frequency.** (session-settled: user-directed — chosen over leaving frequency to the LLM judge: once vs twice daily doubles the dose with no digits involved.)
  - Phrases: "once", "twice" or "three times" (or the digits 1, 2 and 3 followed by "times"), then "daily", "a day" or "per day". These normalize to 1, 2 or 3 times a day.
  - If the claim states a frequency, the quote must state the same one. A claim with no frequency isn't checked.
  - Digits inside a frequency phrase ("3 times daily") are left out of the number rule, so "3 times daily" vs "three times daily" isn't flagged twice.
  - It's a separate rule named `frequency`, with reason "frequency mismatch: claim <x>, quote <y or none>".
- KTD4. **Run every rule and record every failure.** A single judgment can carry several downgrades, so the report can show all of them. The check returns a new `Judgment` rather than changing the input.
- KTD5. **Samples are data in `samples/`, with expected labels in one JSON file per sample.** Each label gives the claim text, the expected verdict, the planted error type (or `none`) and a quote. For `supported` claims, that's the quote that supports the claim. For "changed number" claims, it's the source passage with the correct number. The test suite checks that every labeled quote passes the code checks against its source. That keeps the labels honest and gives the checks a real-text test.
- KTD6. **Prefer FDA drug label excerpts for sources.** FDA labeling is widely reused and likely public domain, but the implementer confirms each source's license before committing it and records it in `samples/README.md`. If an FDA label's status is unclear, the fallback is a CC-BY open-access trial abstract with attribution.

### Assumptions

- Python 3.10 or later (the machine has 3.13). pytest is the only dev dependency.
- `src/` layout installed with `pip install -e ".[dev]"` into a virtual environment, matching `docs/architecture.md`.

## Output Structure

```text
pyproject.toml
src/groundlint/__init__.py
src/groundlint/models.py
src/groundlint/checks.py
samples/README.md
samples/<case-name>/source.md
samples/<case-name>/answer.md
samples/<case-name>/expected.json
tests/test_checks.py
tests/test_samples.py
```

## Implementation Units

### U1. Package scaffold and data types

- **Goal:** An installable, empty `groundlint` package with the shared data types.
- **Requirements:** R5 (the `Downgrade` record), KTD1
- **Dependencies:** none
- **Files:** `pyproject.toml`, `src/groundlint/__init__.py`, `src/groundlint/models.py`, `.gitignore`
- **Approach:**
  1. `pyproject.toml` with a `src/` layout, Python 3.10 or later, no runtime dependencies, and a `dev` extra for pytest.
  2. Add `models.py` with the types from KTD1. Verdict is a string enum: `supported`, `unsupported`, `contradicted`.
  3. Add `.venv/`, `__pycache__/` and `*.egg-info/` to `.gitignore`.
- **Test expectation:** none, since this is scaffolding. U2's tests exercise the types.
- **Verification:** `pip install -e ".[dev]"` succeeds and `import groundlint.models` works.

### U2. Quote and number checks

- **Goal:** `checks.py` downgrades bad `supported` verdicts and records why. It has four rules: quote, number (with units), comparison and frequency.
- **Requirements:** R1, R2, R3, R4, R5, R10, R11, R12, R13, KTD2, KTD3, KTD4, KTD7, KTD8, KTD9
- **Dependencies:** U1
- **Files:** `src/groundlint/checks.py`, `tests/test_checks.py`
- **Approach:**
  1. One public function takes a `Judgment` and the loaded `Source`s and returns a checked `Judgment`.
  2. If the verdict isn't `supported`, return it unchanged.
  3. Run the quote, number, comparison and frequency rules in that order, and collect every failure. If any rule fails, set the verdict to `unsupported` and attach a `Downgrade` per failure.
  4. Keep the normalization and number extraction as small private helpers so each can be tested directly.
- **Execution note:** Write tests first. The rules are small and easy to get subtly wrong.
- **Test scenarios:**
  - A supported judgment whose quote appears word for word in the source stays `supported`, with no downgrades.
  - A quote that matches only after collapsing a line break and changing case still passes.
  - A quote with curly quotes or an en dash matches source text that uses ASCII.
  - A quote with one word changed ("reduced" instead of "did not reduce") is downgraded by the quote rule.
  - An empty quote is downgraded by the quote rule.
  - A quote citing a source path that isn't loaded is downgraded by the quote rule.
  - The claim says "15 mg", the quote says "10 mg" and the quote is in the source: downgraded by the number rule only.
  - The claim says "1,000 patients" and the quote says "1000 patients": passes.
  - The claim says "2.5%" and the quote says "2.50%": passes.
  - The claim says "10-20 mg" and the quote contains only 10: downgraded by the number rule.
  - The claim says "6 mg" and the quote says "CYP2D6 ... 2 mg": downgraded by the number rule with the missing-number reason, not "unit mismatch", because the 6 in CYP2D6 is part of a name.
  - The claim says "0.5 g" and the quote says "500 mg": passes.
  - The claim says "250 mcg" and the quote says "0.25 mg": passes. The same with "µg" and with "μg".
  - The claim says "1 L" and the quote says "1000 mL": passes.
  - The claim says "5 mg" and the quote says "5 g": downgraded, with "unit mismatch" in the reason.
  - The claim says "5 mL" and the quote says "5 mg": downgraded, with "unit mismatch" in the reason.
  - The claim says "5 mg" and the quote says "5 or 10 mg": passes. The same with "5-10 mg", "5 to 10 mg" and "5, 10 or 20 mg".
  - The claim says "5 mg" and the quote says "5 patients received 10 mg": downgraded with "unit mismatch".
  - The claim says "5 mg" and the quote says "5 or 10 mL": downgraded with "unit mismatch", because the list's unit is a different family.
  - The claim says "2 weeks" and the quote says "14 days": passes. The same for "48 hours" vs "2 days", "1 year" vs "12 months" and "12-week" vs "12 weeks".
  - The claim says "4 weeks" and the quote says "1 month": downgraded with the missing-number reason.
  - The claim says "6 months" and the quote says "6 weeks": downgraded with "unit mismatch".
  - The claim says "up to 20 mg" and the quote says "≤ 20 mg": passes. The same with "no more than 20 mg".
  - The claim says "20 mg" and the quote says "up to 20 mg": downgraded by the comparison rule, and the reverse too.
  - The claim says "more than 50%" and the quote says "no more than 50%": downgraded by the comparison rule.
  - The claim says "at least 18 years" and the quote says "less than 18 years": downgraded by the comparison rule.
  - The claim says "up to 30 mg" and the quote says "20 mg": downgraded by the number rule only, not the comparison rule.
  - The claim says "twice daily" and the quote says "twice a day": passes.
  - The claim says "twice daily" and the quote says "once daily": downgraded by the frequency rule.
  - The claim says "three times daily" and the quote has no frequency: downgraded by the frequency rule.
  - The claim says "3 times daily" and the quote says "three times daily": passes all rules.
  - The claim has no frequency and the quote says "once daily": passes the frequency rule.
  - The claim says "10-20 mg" and the quote says "10-20 g": downgraded with "unit mismatch", because the range's unit applies to both ends.
  - The claim says "5 mg/kg" and the quote says "5 mg": passes on value alone, because rates aren't unit-checked in v0.
  - The claim says "avoid strong CYP3A4 inhibitors" and the quote has no numbers: passes.
  - A claim with no numbers passes the number rule.
  - The quote is missing from the source and the numbers don't match: two downgrades recorded.
  - `unsupported` and `contradicted` judgments with fake quotes come back unchanged.
  - The input `Judgment` isn't mutated.
- **Verification:** All scenarios pass, and no test imports anything outside the standard library and `groundlint`.

### U3. Sample cases and expected labels

- **Goal:** 3 small biopharma cases a friend can run through, with labels the checks can verify.
- **Requirements:** R6, R7, R8, R9, KTD5, KTD6
- **Dependencies:** none (can run in parallel with U2)
- **Files:** `samples/README.md`, plus `source.md`, `answer.md` and `expected.json` for each of 3 case folders under `samples/`
- **Approach:**
  1. Pick 3 sources on different drugs and topics, such as dosing, a trial outcome and contraindications. Trim each to a short excerpt, a few hundred words at most, and keep the original wording.
  2. Confirm and record each source's URL, retrieval date and license in `samples/README.md` (KTD6).
  3. Write each answer as a short paragraph of 6–8 claims: the four planted error types (R7), 2–3 correct claims, and at least one sentence that packs two facts together, to test whether claim extraction drops one.
  4. Write `expected.json` per KTD5, so the 3 samples give about 20 labeled claims in total.
- **Test expectation:** covered by U4.
- **Verification:** A second reader can find each planted error from the label file alone, and each source's license is recorded.

### U4. Tie samples to checks

- **Goal:** A test that keeps the samples and the checks consistent.
- **Requirements:** R6, R8, KTD5
- **Dependencies:** U2, U3
- **Files:** `tests/test_samples.py`
- **Approach:** Load each sample's source and `expected.json`. Build a `supported` `Judgment` for every claim labeled `supported` and run it through the checks.
- **Test scenarios:**
  - Every `supported` label's quote passes both rules against its sample source.
  - Every sample has all four planted error types and at least 2 `supported` claims.
  - Across all samples there are at least 18 labeled claims.
  - For each "changed number" claim, the labeled quote passes the quote rule. A fake `supported` judgment that pairs the claim with that quote is downgraded by the number rule.
  - For each "reversed finding" claim, a fake `supported` judgment that uses the claim's own wording as its quote is downgraded by the quote rule.
- **Verification:** `pytest` passes with the samples in place.

## Verification Contract

| Gate | Command | Proves |
|---|---|---|
| Install | `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"` | U1 packaging works |
| Tests | `.venv/bin/pytest` | U2 and U4 behavior |
| License check | Manual read of `samples/README.md` | R6, KTD6 |

## Definition of Done

- All four units' verification passes, and `pytest` is green.
- No LLM, network or API key is used anywhere in code or tests.
- `samples/README.md` lists the source, URL and license for each sample.
- No leftover experimental code or unused helpers in the diff.
