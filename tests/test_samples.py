"""Keep the sample cases and the code checks consistent."""

import json
from pathlib import Path

import pytest

from groundlint.checks import check
from groundlint.models import Judgment, Source, Verdict

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
ERROR_TYPES = {"changed_number", "reversed_finding", "overextended_population", "no_source"}
CASES = sorted(p for p in SAMPLES.iterdir() if (p / "expected.json").is_file()) if SAMPLES.is_dir() else []


def load(case):
    labels = json.loads((case / "expected.json").read_text(encoding="utf-8"))
    source = Source(path=labels["source"], text=(case / labels["source"]).read_text(encoding="utf-8"))
    return labels, source


def supported(claim, source):
    return Judgment(
        claim=claim["claim"],
        sentence=claim["sentence"],
        verdict=Verdict.SUPPORTED,
        explanation="",
        quote=claim["quote"],
        source_path=source.path,
    )


def claims_of(error_type):
    for case in CASES:
        labels, source = load(case)
        for claim in labels["claims"]:
            if claim["error_type"] == error_type:
                yield pytest.param(claim, source, id=f"{case.name}:{claim['id']}")


def test_there_are_three_samples_with_enough_claims():
    assert len(CASES) == 3
    assert sum(len(load(case)[0]["claims"]) for case in CASES) >= 18


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_each_sample_plants_every_error_type(case):
    labels, _ = load(case)
    error_types = {c["error_type"] for c in labels["claims"]}
    assert ERROR_TYPES <= error_types
    assert sum(c["expected"] == "supported" for c in labels["claims"]) >= 2


@pytest.mark.parametrize("claim, source", list(claims_of("none")))
def test_supported_labels_pass_every_rule(claim, source):
    assert claim["expected"] == "supported"
    result = check(supported(claim, source), [source])
    assert result.verdict is Verdict.SUPPORTED, [d.reason for d in result.downgrades]


@pytest.mark.parametrize("claim, source", list(claims_of("changed_number")))
def test_changed_number_is_caught_by_the_number_rule(claim, source):
    result = check(supported(claim, source), [source])
    assert result.verdict is Verdict.UNSUPPORTED
    assert [d.rule for d in result.downgrades] == ["number"], [d.reason for d in result.downgrades]


@pytest.mark.parametrize("claim, source", list(claims_of("reversed_finding")))
def test_reversed_finding_quoted_as_itself_is_caught_by_the_quote_rule(claim, source):
    # The claim's own wording, offered as if it were a quote from the source.
    result = check(supported({**claim, "quote": claim["claim"]}, source), [source])
    assert result.verdict is Verdict.UNSUPPORTED
    assert "quote" in [d.rule for d in result.downgrades]
