# Progress

Tracks which missions are complete and what comes next.

- [x] Mission 0: Build the workspace
- [x] Mission 1: Discover and scope
- [x] Mission 2: Design the system
- [ ] Mission 3: Ship the first slice

## Mission 3 status (2026-11-08)

- Code checks (quote, number with units, comparison, frequency) and 3 FDA-label sample cases are built and tested. Merged to `main` in PR #1.
- v0 deadline: Tuesday, November 10, 2026.

- 2026-11-09: the end-to-end `groundlint` command works on NVIDIA's endpoint with `nvidia/nemotron-3-ultra-550b-a55b`. On the 3 samples, 21 of 22 labeled claims got the expected verdict, and every planted error was flagged (results in [evals.md](evals.md)).

### Next steps, in order

1. [x] Get an API key for an OpenAI-compatible endpoint and choose the starting model.
2. [x] File loader: read the answer and sources, accept only `.txt` and `.md`, and enforce the size limit. If no sources are given, stop with a clear error.
3. [x] LLM claim extraction and LLM judge.
4. [x] CLI: the `groundlint` command, with exit codes 0, 1 and 2.
5. [x] Report: the terminal report and `--json`.
6. [x] README: install command, PDF conversion tip, confidential-data warning and the "can miss errors" note.
7. Friends try it, and their feedback is written down.
