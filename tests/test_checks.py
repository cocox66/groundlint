from dataclasses import replace

import pytest

from groundlint.checks import check
from groundlint.models import Judgment, Source, Verdict

SOURCE_PATH = "label.md"


def judge(claim, quote, *, source_text=None, verdict=Verdict.SUPPORTED, source_path=SOURCE_PATH):
    """Run the checks on one judgment. By default the source is exactly the quote."""
    text = quote if source_text is None else source_text
    judgment = Judgment(
        claim=claim,
        sentence=claim,
        verdict=verdict,
        explanation="",
        quote=quote,
        source_path=source_path,
    )
    return check(judgment, [Source(path=SOURCE_PATH, text=text)])


def rules(result):
    return [d.rule for d in result.downgrades]


def reasons(result):
    return " | ".join(d.reason for d in result.downgrades)


def assert_passes(result):
    assert result.verdict is Verdict.SUPPORTED, reasons(result)
    assert result.downgrades == ()


def assert_downgraded(result, *expected_rules):
    assert result.verdict is Verdict.UNSUPPORTED
    assert rules(result) == list(expected_rules), reasons(result)


# --- Quote rule -------------------------------------------------------------


def test_verbatim_quote_passes():
    source = "In clinical trials, the drug reduced the risk of stroke. Other text follows."
    assert_passes(judge("The drug reduced the risk of stroke.", "the drug reduced the risk of stroke", source_text=source))


def test_quote_matches_across_line_break_and_case():
    source = "The recommended dose is\n  taken with food."
    assert_passes(judge("Take it with food.", "THE RECOMMENDED DOSE IS TAKEN WITH FOOD", source_text=source))


def test_curly_quotes_and_en_dash_match_ascii_source():
    source = 'Patients said it was "well tolerated" - see section 6.'
    assert_passes(judge("It was well tolerated.", "said it was “well tolerated” – see section", source_text=source))


def test_one_word_changed_fails_quote_rule():
    source = "Treatment did not reduce mortality."
    result = judge("Treatment reduced mortality.", "Treatment reduced mortality.", source_text=source)
    assert_downgraded(result, "quote")


def test_empty_quote_fails_quote_rule():
    assert_downgraded(judge("It works.", "", source_text="It works."), "quote")


def test_unloaded_source_fails_quote_rule():
    result = judge("It works.", "It works.", source_path="other.md")
    assert_downgraded(result, "quote")
    assert "other.md" in reasons(result)


# --- Number rule: values ----------------------------------------------------


def test_changed_number_fails_number_rule_only():
    assert_downgraded(judge("The dose is 15 mg.", "The dose is 10 mg."), "number")


def test_thousands_comma_matches_plain_number():
    assert_passes(judge("1,000 patients enrolled.", "1000 patients enrolled"))


def test_trailing_zero_decimal_matches():
    assert_passes(judge("Incidence was 2.5%.", "incidence was 2.50%"))


def test_range_needs_both_ends():
    assert_downgraded(judge("Give 10-20 mg.", "give 10 mg"), "number")


def test_claim_without_numbers_passes():
    assert_passes(judge("The drug is well tolerated.", "well tolerated"))


def test_quote_missing_and_numbers_wrong_records_two_downgrades():
    result = judge("The dose is 15 mg.", "The dose is 10 mg.", source_text="Unrelated text.")
    assert_downgraded(result, "quote", "number")


def test_integer_not_found_inside_longer_integer():
    # Digit-boundary rule from Soundscape: 8 is not "found" inside 18.
    assert_downgraded(judge("8 patients withdrew.", "18 patients withdrew"), "number")


def test_integer_not_found_inside_decimal():
    # Digit-boundary rule from Soundscape: 1 is not "found" inside 1.04.
    assert_downgraded(judge("The ratio was 1.", "the ratio was 1.04"), "number")


def test_digits_inside_names_are_not_numbers():
    result = judge("Use 6 mg.", "Avoid with CYP2D6 inhibitors; use 2 mg.")
    assert_downgraded(result, "number")
    assert "unit mismatch" not in reasons(result)


def test_name_with_digits_and_no_quantities_passes():
    assert_passes(judge("Avoid strong CYP3A4 inhibitors.", "avoid strong cyp3a4 inhibitors"))


# --- Number rule: units -----------------------------------------------------


@pytest.mark.parametrize(
    "claim, quote",
    [
        ("Take 0.5 g.", "take 500 mg"),
        ("Take 250 mcg.", "take 0.25 mg"),
        ("Take 250 µg.", "take 0.25 mg"),
        ("Take 250 μg.", "take 0.25 mg"),
        ("Infuse 1 L.", "infuse 1000 mL"),
        ("Give 5mg.", "give 5 mg"),
        ("Give 5 mg.", "give 5 or 10 mg"),
        ("Give 5 mg.", "give 5-10 mg"),
        ("Give 5 mg.", "give 5 to 10 mg"),
        ("Give 5 mg.", "give 5, 10, or 20 mg"),
        ("Treat for 2 weeks.", "treat for 14 days"),
        ("Wait 48 hours.", "wait 2 days"),
        ("Follow for 1 year.", "follow for 12 months"),
        ("A 12-week trial.", "a trial of 12 weeks"),
        ("Give 5 mg/kg.", "give 5 mg"),
        ("Give 10 mg.", "give 10 mg/day"),
    ],
)
def test_matching_quantities_pass(claim, quote):
    assert_passes(judge(claim, quote))


@pytest.mark.parametrize(
    "claim, quote",
    [
        ("Take 5 mg.", "take 5 g"),
        ("Take 5 mL.", "take 5 mg"),
        ("Give 5 mg.", "5 patients received 10 mg"),
        ("Give 5 mg.", "give 5 or 10 mL"),
        ("Give 10-20 mg.", "give 10-20 g"),
        ("Treat for 6 months.", "treat for 6 weeks"),
    ],
)
def test_same_number_with_other_unit_is_unit_mismatch(claim, quote):
    result = judge(claim, quote)
    assert_downgraded(result, "number")
    assert "unit mismatch" in reasons(result)


def test_weeks_and_months_are_not_converted():
    result = judge("Treat for 4 weeks.", "treat for 1 month")
    assert_downgraded(result, "number")
    assert "unit mismatch" not in reasons(result)


# --- Comparison rule --------------------------------------------------------


@pytest.mark.parametrize(
    "claim, quote",
    [
        ("Take up to 20 mg.", "take ≤ 20 mg"),
        ("Take up to 20 mg.", "take no more than 20 mg"),
        ("Take at least 5 mg.", "take >= 5 mg"),
        ("Fewer than 10 patients.", "less than 10 patients"),
    ],
)
def test_equivalent_qualifiers_pass(claim, quote):
    assert_passes(judge(claim, quote))


@pytest.mark.parametrize(
    "claim, quote",
    [
        ("Take 20 mg.", "take up to 20 mg"),
        ("Take up to 20 mg.", "take 20 mg"),
        ("Response in more than 50%.", "response in no more than 50%"),
        ("Patients at least 18 years old.", "patients less than 18 years old"),
    ],
)
def test_qualifier_mismatch_fails_comparison_rule(claim, quote):
    result = judge(claim, quote)
    assert_downgraded(result, "comparison")
    assert "comparison mismatch" in reasons(result)


def test_unmatched_number_is_reported_by_number_rule_only():
    assert_downgraded(judge("Take up to 30 mg.", "take 20 mg"), "number")


# --- Frequency rule ---------------------------------------------------------


def test_same_frequency_different_wording_passes():
    assert_passes(judge("Take it twice daily.", "take it twice a day"))


def test_different_frequency_fails_frequency_rule():
    result = judge("Take it twice daily.", "take it once daily")
    assert_downgraded(result, "frequency")
    assert "frequency mismatch" in reasons(result)


def test_frequency_missing_from_quote_fails():
    result = judge("Take it three times daily.", "take it with food")
    assert_downgraded(result, "frequency")
    assert "none" in reasons(result)


def test_digit_frequency_matches_word_frequency():
    assert_passes(judge("Take it 3 times daily.", "take it three times daily"))


def test_claim_without_frequency_is_not_checked():
    assert_passes(judge("Take it with food.", "take it once daily with food"))


# --- Verdict handling -------------------------------------------------------


@pytest.mark.parametrize("verdict", [Verdict.UNSUPPORTED, Verdict.CONTRADICTED])
def test_non_supported_verdicts_are_unchanged(verdict):
    result = judge("The dose is 15 mg.", "made-up quote 99 g", source_text="Nothing here.", verdict=verdict)
    assert result.verdict is verdict
    assert result.downgrades == ()


def test_input_judgment_is_not_mutated():
    original = Judgment(
        claim="The dose is 15 mg.",
        sentence="The dose is 15 mg.",
        verdict=Verdict.SUPPORTED,
        explanation="",
        quote="The dose is 10 mg.",
        source_path=SOURCE_PATH,
    )
    snapshot = replace(original)
    result = check(original, [Source(path=SOURCE_PATH, text="The dose is 10 mg.")])
    assert original == snapshot
    assert result is not original
    assert result.verdict is Verdict.UNSUPPORTED
