# Architecture

How groundlint is structured and how its parts fit together.

## Shape

groundlint is a small Python package laid out as a pipeline. Each step is its own module and passes plain data to the next one. Only two modules talk to the LLM, so everything else can be tested without an API key.

```
src/groundlint/
  cli.py        parse arguments, run the pipeline, pick the exit code
  sources.py    load the answer and source files, enforce .txt/.md and the size limit
  llm.py        one function that calls an OpenAI-compatible endpoint
  extract.py    LLM step: answer -> list of claims, each with its original sentence
  judge.py      LLM step: claim + sources -> verdict, explanation, quote, source file
  checks.py     code rules: quote is in the source, numbers in the claim are in the quote
  report.py     terminal report and --json output
  models.py     the shared data types (Source, Claim, Verdict, CheckResult)
samples/        3 biopharma cases: source file, answer with planted errors, expected labels
tests/
```

## How a run flows

```
groundlint answer.md --sources label.txt
  -> cli.py        reads arguments
  -> sources.py    loads the answer and sources, or stops with an error (exit 2)
  -> extract.py    splits the answer into claims
  -> judge.py      gives each claim a verdict
  -> checks.py     downgrades a `supported` verdict if a rule fails, and records which rule
  -> report.py     prints the report or JSON
  -> cli.py        exits 0 (nothing flagged), 1 (something flagged) or 2 (tool failed)
```

## Rules for the code

- `checks.py` and `report.py` never import `llm.py`. They work on data only.
- `checks.py` can only downgrade a verdict, never upgrade one.
- The data types in `models.py` are plain dataclasses, so `--json` is a direct dump of them.
