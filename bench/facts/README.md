# FACTS Grounding sample

20 medical examples from [FACTS Grounding](https://huggingface.co/datasets/google/FACTS-grounding-public) (Google DeepMind and Google Research), used to try groundlint on material we didn't write.

## Rebuild

```bash
python3 bench/facts/make_sample.py
```

Standard library only, with no LLM calls. It downloads `examples.csv` at revision `11b6961`, so every run writes the same `sample.jsonl`.

## How the 20 were picked

FACTS has no domain label, so the script picks rows by keyword:

1. Count the distinct medical terms (patient, diagnosis, dose, side effect…) in the request and the document. 110 of the 860 rows have at least 8.
2. Shuffle those 110 with seed 0 and keep the first 20.
3. Rows that are on topic but not clinical go in `EXCLUDE` in the script, with a reason. Only row 460 is excluded so far, a legal question about drug scheduling. The next row in the shuffle takes its place.

This is a judgment call, not a label from the dataset.

## Format

`sample.jsonl` has one JSON object per line:

| Field | Meaning |
|---|---|
| `id`, `row` | `facts-<row>`, and the row's 0-based index in `examples.csv` |
| `system_instruction` | Rules for the model, e.g. "answer only from the document" |
| `user_request` | The question or task |
| `context_document` | The source text the answer must be grounded in |
| `full_prompt` | The three fields above combined, exactly as a model receives them |
| `medical_terms` | Which keywords matched |
| `source` | Dataset and revision |

FACTS includes no reference answers or labels. To benchmark groundlint, you first need to generate answers to these prompts.

## License

The FACTS Grounding public examples are © Google LLC, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The rows here are unchanged except for the added `id`, `row`, `medical_terms` and `source` fields.
