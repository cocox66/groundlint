# groundlint

groundlint checks whether an LLM's answer is supported by its sources. You give it the answer and the files it was based on, and it lists every claim the sources don't support, with the passage to look at.

```bash
groundlint answer.md --sources label.md notes/
```

It's a developer aid for debugging RAG and agent apps one answer at a time. **It is not a compliance or safety tool, and it can miss errors.** See [Limits](#limits).

## Install

You need Python 3.10 or newer.

```bash
pip install git+https://github.com/cocox66/groundlint
```

groundlint has no other dependencies.

## Set up a model

groundlint works with any OpenAI-compatible chat completions endpoint. By default it uses NVIDIA's endpoint (`https://integrate.api.nvidia.com/v1`) and the `nvidia/nemotron-3-ultra-550b-a55b` model. Keys are available at [build.nvidia.com](https://build.nvidia.com).

```bash
export NVIDIA_API_KEY=...        # or GROUNDLINT_API_KEY, which takes priority
```

To use another provider, set the base URL and model with flags or environment variables:

| Setting | Flag | Environment variable |
|---|---|---|
| API key | (none, so the key stays out of shell history) | `GROUNDLINT_API_KEY`, then `NVIDIA_API_KEY` |
| Base URL | `--base-url` | `GROUNDLINT_BASE_URL` |
| Model | `--model` | `GROUNDLINT_MODEL` |

For example, any provider with an OpenAI-compatible API:

```bash
export GROUNDLINT_API_KEY=...
groundlint answer.md --sources label.md --base-url https://api.openai.com/v1 --model MODEL_NAME
```

> **Don't send confidential data.** groundlint sends the full answer and every source file to the API you configure. Don't use it on patient data, unpublished results or anything else you can't share with that provider.

## Try it on a sample

The repo includes three sample cases built from FDA drug label excerpts, each with deliberately planted errors. See [samples/README.md](samples/README.md).

```bash
git clone https://github.com/cocox66/groundlint && cd groundlint
groundlint samples/apixaban-dosing/answer.md --sources samples/apixaban-dosing/source.md
```

Part of the output:

```
== CONTRADICTED: the sources conflict with these claims (3) ==

[4] After hip replacement surgery, Eliquis is continued for 30 days to prevent DVT.
    why:        The source states the recommended duration of treatment after hip replacement surgery is 35 days, not 30 days.
    source:     samples/apixaban-dosing/source.md
    quote:      "In patients undergoing hip replacement surgery, the recommended duration of treatment is 35 days."
...
8 claims: 3 contradicted, 1 unsupported, 4 supported  (model: nvidia/nemotron-3-ultra-550b-a55b)
```

A sample takes about 35 seconds.

## Usage

```
groundlint ANSWER --sources PATH [PATH ...] [--json] [--model M] [--base-url URL]
```

- `ANSWER` is a `.txt` or `.md` file, or `-` to read the answer from stdin.
- `--sources` takes files and folders. Folders are searched recursively for `.txt` and `.md` files, skipping the answer file itself. At least one source is required.
- `--json` prints the same results as JSON instead of the report.

Only `.txt` and `.md` files are accepted. To use a PDF, convert it to text first, for example with `pdftotext label.pdf label.txt` (from Poppler: `brew install poppler` or `apt install poppler-utils`).

Sources can total up to 200,000 characters, and the answer can be up to 20,000. Over the limit, groundlint stops and reports the actual size and the limit. It never cuts text silently.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Nothing flagged |
| `1` | At least one claim flagged (`unsupported` or `contradicted`) |
| `2` | groundlint failed (bad input, missing key, API error) |

## How it works

1. An LLM splits the answer into separate claims and skips text that isn't a factual claim. Every extracted claim appears in the report, so you can see if one was dropped.
2. An LLM judge checks each claim against all the sources and returns a verdict, an explanation and a quote from the source.
3. Code rules check every `supported` verdict. If the quote isn't in the cited source, or a number, unit, comparison ("up to", "at least") or dose frequency in the claim doesn't match the quote, the verdict becomes `unsupported`. The report names the rule (`CODE RULE: ...`), so you can tell it apart from the LLM's judgment. The rules can only downgrade a verdict, never upgrade one.

| Verdict | Meaning |
|---|---|
| `supported` | The sources state the claim or directly entail it. |
| `unsupported` | The sources don't establish the claim. This doesn't mean it's false, only that these sources don't back it. |
| `contradicted` | The sources conflict with the claim. |

## Limits

- **It can miss errors.** Both the claim splitting and the judging are done by an LLM, which can be wrong. A `supported` verdict isn't proof. Spot-check it, especially for doses.
- It only checks claims against the sources you give it, not against the web or general knowledge.
- The code rules don't yet understand rates (mg/kg), IU, percentage points, or dosing abbreviations such as BID. See [docs/decisions.md](docs/decisions.md).
- So far it has only been tested on the three planted samples (21 of 22 claims as expected, see [docs/evals.md](docs/evals.md)). That shows it works on those cases, not how accurate it is in general.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

The tests don't need an API key. Design notes are in [docs/](docs/).

## License

MIT.
