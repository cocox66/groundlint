# Evals

How we measure whether groundlint correctly flags unsupported claims.

## Run 1: 2026-11-09, the 3 samples

Model `nvidia/nemotron-3-ultra-550b-a55b` on NVIDIA's endpoint. Each groundlint claim was lined up with the nearest labeled claim by text similarity, and the alignments were checked by hand.

| Sample | Labeled claims | Extracted claims | Verdict matches |
|---|---|---|---|
| apixaban-dosing | 8 | 8 | 7 |
| simvastatin-contraindications-interactions | 7 | 9 | 7 |
| empagliflozin-cv-outcomes | 7 | 7 | 7 |
| **Total** | **22** | **24** | **21** |

- Every planted error was flagged, and every labeled `supported` claim passed, so there were no false alarms on labeled claims.
- The one mismatch is apixaban c7, an overextended population ("all patients aged 80 years or older should take 2.5 mg"). The label is `unsupported`, and groundlint said `contradicted` because the source requires 2 of 3 criteria. It's still flagged, and the exit code is the same.
- The simvastatin answer lists five contraindicated drugs in one sentence. groundlint split it into four claims and the answer key into two. The two extra claims (danazol, gemfibrozil) are correctly `supported`.
- No code rule fired: every `supported` quote was found verbatim in the source, with matching numbers.
- Mistral Large 4 timed out on all three samples and gave no verdicts.

These are planted cases written and labeled by the same person, so this shows the tool works on them, not how accurate it is in general.
