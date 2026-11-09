# Decisions

A record of key project decisions and the reasoning behind them.

## 2026-11-08: Small pipeline package, not a single script

**Decision:** Build groundlint as a Python package with one module per step (load, extract, judge, check, report), described in [architecture.md](architecture.md).

**Why:** The code checks are the part we trust most and want to build first. Keeping them in their own module means they can be written and tested today, before any LLM or API key exists. Each later step drops in without touching the checks.

**Rejected: a single `groundlint.py` file.** It's the simplest start and fine for a few hundred lines. But the LLM calls, file loading and checks would be mixed together, so testing the checks without an API key gets harder as the file grows. Splitting it later means a refactor in the middle of the v0 week.

## 2026-11-08: Build the code checks before the LLM steps

**Decision:** The first slice is the quote check, the number check and the 3 sample files, with no LLM.

**Why:** They are deterministic, need no API key and give the samples a use straight away. The LLM steps can then be tested against checks that already work.

**Rejected: building end to end with the LLM first.** It shows something sooner, but we'd be debugging prompts and the checks at the same time.

## 2026-11-08: The number check understands units

**Decision:** The number check reads a number and its unit together and converts within the same unit family before comparing. 0.5 g matches 500 mg and 2 weeks matches 14 days, but 5 mg vs 5 g is downgraded with "unit mismatch" in the reason. The families are mass (mcg/µg, mg, g, kg), volume (mL, L), short time (hours, days, weeks) and long time (months, years).

**Why:** In biopharma the riskiest wrong sentence is often the dose. A 1000x unit error with the right digits would pass a check that only compares numbers. Unit conversion is still a text comparison, so it fits the rule that code checks compare text and can only downgrade.

**Bare numbers:** A quote number with no unit counts only when it's in a list or range that ends in a unit of the same family ("5 or 10 mg", "5-10 mg"). "5 mg" doesn't pass against "5 patients ... 10 mg".

**Rejected: leaving units to the LLM judge.** That's simpler, but the judge can miss a unit swap, and this is the error the code checks are best placed to catch for sure.

**Rejected: letting any bare quote number count.** That avoided false alarms on "5 or 10 mg" but let unrelated numbers ("5 patients") support a dose. Sharing the unit across a list or range fixes the false alarm without that hole.

**Rejected: converting days to months.** The ratio isn't exact, so "4 weeks" vs "1 month" is reported as a missing number rather than guessed.

## 2026-11-08: Comparison qualifiers and dose frequency must match

**Decision:** Two more code rules. The comparison rule requires "up to", "at least", "less than", "more than" and `<` `>` `≤` `≥` to match between a claim number and its quote number, including when only one side has one. The frequency rule requires a claim's "once/twice/three times daily" to appear in the quote.

**Why:** "up to 20 mg" vs "20 mg", and once vs twice daily, are dose errors with the same or no digits, so the number rule can't see them.

**Rejected: leaving them to the LLM judge.** The judge can miss them for the same reason it can miss unit swaps, and both are simple enough for exact text rules.

## Later

Not built in v0. Each currently falls back to comparing values only, or isn't checked.

- **Rates and compound units** (mg/kg, mg/day, mg/mL): need a unit per numerator and denominator.
- **Percent vs percentage points:** "rose 5%" and "rose 5 percentage points" mean different things, and both have the digit 5.
- **Other number formats:** "1.000" as one thousand (European) currently reads as 1.0.
- **Other units:** IU, mmol/L, mEq and similar.
- **Other frequencies:** abbreviations (QD, BID, TID), "every 12 hours" and weekly or monthly dosing.
