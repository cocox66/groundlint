# Product

What groundlint is, who it's for, and what it needs to do.

groundlint is a small open source Python CLI. You give it an LLM's answer and the sources it used, and it tells you which claims the sources don't support.

```bash
groundlint answer.md --sources paper.md label.txt notes/
```

## Users

Developers building RAG or agent apps, especially in biopharma, where an unsupported claim is risky. In v0, a developer uses it by hand while debugging, to inspect one answer at a time.

groundlint is a developer aid, not a compliance or safety tool. It can miss errors, and the docs must say so.

## v0 goal

A working v0 by Monday, November 9, 2026, that 2 or 3 friends actually try.

v0 is done when:

- It installs from a public GitHub repo with one command.
- At least 2 friends have run it on their own material or the sample files. Real material is a bonus, not a requirement.
- Their feedback is written down, including any wrong verdicts and which material each friend used.

PyPI publishing, polish and accuracy targets are not required.

## Why not RAGAS, TruLens or DeepEval?

The core method isn't new: RAGAS and DeepEval also extract claims and judge them with an LLM. groundlint differs in workflow and output.

- **For a developer:** Those tools are good for scoring a RAG system across a dataset. groundlint answers a narrower question: which exact claims in this answer should I not trust? You point it at files and get each flagged claim, with the evidence checked by code rather than taken from the LLM.
- **For a PM:** A score of 0.8 doesn't tell a reviewer which sentence is wrong. In biopharma, the wrong sentence might be the dose, so groundlint shows which claim to check and where to look.

Don't claim that groundlint is more accurate or unique. Nothing has been measured, and a determined developer could get close with a short script over DeepEval. Before making a public comparison, run the sample files through DeepEval to see what it catches.

## What v0 does

### Input

- The answer comes from a file or stdin.
- `--sources` takes files or folders.
- Only `.txt` and `.md` are accepted. The README gives a one-line tip for converting PDFs.
- Sources over a size limit stop the run with an error that gives the actual size and the limit. Text is never silently cut. The limit is set once the default model is chosen.

### Checking

1. An LLM splits the answer into atomic claims, each linked to its original sentence, and skips non-factual text. All extracted claims appear in the report, so a dropped claim is visible.
2. An LLM judge gives each claim a verdict against the full sources, with an explanation and a supporting quote. Embeddings are not used, because similarity can't reliably separate "reduced risk" from "did not reduce risk".
3. Code checks each `supported` verdict and downgrades it to `unsupported` if either rule fails:
   - The quote must appear in the cited source.
   - Every number in the claim must appear in that quote.

These rules only compare text, so meaning remains the LLM's job. They can downgrade a verdict but never upgrade one.

### Verdicts

A claim is supported only if the sources state it or directly entail it.

| Verdict | Meaning |
|---|---|
| `supported` | The sources state or directly entail the claim. |
| `unsupported` | The sources don't establish the claim. Partial support lands here, and the explanation says which part is missing. |
| `contradicted` | The sources conflict with the claim. |

`unsupported` and `contradicted` claims are both flagged, with contradictions shown separately.

When the two errors trade off, prefer a false alarm over a miss, as long as false alarms don't get so frequent that users stop trusting the output.

### Output

- The default is a readable terminal report. Each claim shows its verdict, explanation, source file and exact quote, followed by a count for each verdict.
- If a code rule downgraded a verdict, the report names the rule, so it can't be mistaken for the LLM's judgment.
- `--json` gives the same content in machine-readable form.

| Exit code | Meaning |
|---|---|
| `0` | Nothing flagged |
| `1` | At least one claim flagged |
| `2` | The tool failed |

### Model access

- groundlint calls any OpenAI-compatible endpoint, with the base URL, model and key set by the user.
- The default model is chosen by running the test set and checking current model options.
- Answers and sources go to whichever third-party API the user configures. The README warns against sending confidential data.

### Samples and test set

- The repo ships about 3 sample cases. Each has a public biopharma source, such as an FDA drug label or an open-access trial abstract, and a hand-written answer with planted errors: a changed number, a reversed finding, an overextended population and a claim with no source.
- Check each source's license before committing it.
- A sample should work in under 5 minutes.
- The samples seed a hand-labeled test set of about 20 biopharma claims, including cases where claim extraction might drop a claim. Results go in `docs/evals.md`, with no pass mark set before the first run.
- Because the same person writes the errors and the labels, these results show the tool works on planted cases, not how accurate it is in general.

## Out of scope for v0

- Local model support
- PDFs and URLs as input
- JSON input
- Batch mode and CI thresholds
- Retrieval or chunking over large sources
- Checking facts against the web
- Biopharma-specific logic
- A web UI
- Publishing to PyPI

PDF support is the likely first follow-up. Biopharma users will eventually need a local model option.

## Relationship to Soundscape

groundlint is inspired by the grounding gate in [Soundscape](https://github.com/cocox66/soundscape), not extracted from it. The gate checks structured, cited claims with rules, so it can't take a free-text answer and prose sources or catch a reversed meaning.

- **Reuse:** the number and value matching, and the JSON parsing. Soundscape is MIT licensed.
- **New work:** claim extraction and the semantic judge.
- **Don't cite:** Soundscape's benchmark results. They ran in mock mode, and there's no human-labeled accuracy data.

## Name

The project was renamed from groundcheck because `groundcheck` on PyPI is an unrelated hallucination detection package. On November 7, 2026, `groundlint` returned no project on PyPI, but that doesn't reserve it, and PyPI could still reject it at first upload.
