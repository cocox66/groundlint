"""Loader, JSON parsing, report and CLI exit codes, with a fake LLM (no API key needed)."""

import io
import json

import pytest

from groundlint import cli, llm, sources
from groundlint.models import Downgrade, Judgment, Verdict
from groundlint.report import to_json, to_text
from groundlint.sources import LoadError, load_answer, load_sources

# --- Loader ------------------------------------------------------------------


def test_no_sources_is_a_clear_error():
    with pytest.raises(LoadError, match="no sources given"):
        load_sources([])
    with pytest.raises(LoadError, match="no sources given"):
        load_sources(None)


def test_rejects_other_extensions_and_missing_paths(tmp_path):
    pdf = tmp_path / "label.pdf"
    pdf.write_text("x")
    with pytest.raises(LoadError, match=r"\.txt or \.md"):
        load_sources([str(pdf)])
    with pytest.raises(LoadError, match="source not found"):
        load_sources([str(tmp_path / "nope.md")])


def test_folder_loads_only_text_files_sorted(tmp_path):
    (tmp_path / "b.md").write_text("bee")
    (tmp_path / "a.txt").write_text("ay")
    (tmp_path / "c.pdf").write_text("skip")
    loaded = load_sources([str(tmp_path)])
    assert [s.text for s in loaded] == ["ay", "bee"]


def test_answer_file_is_never_its_own_source(tmp_path):
    (tmp_path / "answer.md").write_text("claim")
    (tmp_path / "label.md").write_text("source")
    loaded = load_sources([str(tmp_path)], answer_path=str(tmp_path / "answer.md"))
    assert [s.text for s in loaded] == ["source"]
    with pytest.raises(LoadError, match="answer file itself"):
        load_sources([str(tmp_path / "answer.md")], answer_path=str(tmp_path / "answer.md"))


def test_empty_folder_is_an_error(tmp_path):
    with pytest.raises(LoadError, match="no .txt or .md files"):
        load_sources([str(tmp_path)])


def test_size_limit_reports_actual_size_and_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(sources, "SOURCE_LIMIT_CHARS", 10)
    (tmp_path / "a.md").write_text("x" * 11)
    with pytest.raises(LoadError, match="11 characters in total; the limit is 10"):
        load_sources([str(tmp_path / "a.md")])


def test_answer_from_stdin_and_empty_answer():
    assert load_answer("-", stdin=io.StringIO("Hello.")) == "Hello."
    with pytest.raises(LoadError, match="empty"):
        load_answer("-", stdin=io.StringIO("  \n"))


# --- JSON parsing ------------------------------------------------------------


@pytest.mark.parametrize(
    "reply",
    ['{"a": 1}', '```json\n{"a": 1}\n```', 'Sure! {"a": 1} Hope that helps.', '<think>hmm {}</think>{"a": 1}'],
)
def test_parse_json_tolerates_wrapping(reply):
    assert llm.parse_json(reply) == {"a": 1}


def test_ask_json_retries_once_then_fails():
    replies = iter(["not json", '{"a": 1}'])
    assert llm.ask_json(lambda m: next(replies), [], lambda d: d["a"]) == 1
    with pytest.raises(llm.LLMError, match="unusable"):
        llm.ask_json(lambda m: "nope", [], lambda d: d)


def test_settings_need_a_key_and_hide_it(monkeypatch):
    for name in llm.KEY_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(llm.LLMError, match="no API key"):
        llm.settings()
    monkeypatch.setenv("NVIDIA_API_KEY", "secret-value")
    config = llm.settings(model="m")
    assert config.model == "m" and config.base_url == llm.DEFAULT_BASE_URL
    assert "secret-value" not in repr(config)


# --- Report ------------------------------------------------------------------


def judgment(verdict, downgrades=()):
    return Judgment("Claim.", "Claim.", verdict, "Because.", "a quote", "s.md", downgrades)


def test_report_names_the_code_rule_and_counts():
    down = judgment(Verdict.UNSUPPORTED, (Downgrade("number", "number missing: claim 30 days not in quote"),))
    text = to_text([judgment(Verdict.SUPPORTED), down], "m")
    assert "CODE RULE:" in text and "number rule" in text
    assert "2 claims: 0 contradicted, 1 unsupported, 1 supported" in text


def test_json_is_a_dump_of_the_judgments():
    data = json.loads(to_json([judgment(Verdict.CONTRADICTED)], "m"))
    assert data["flagged"] is True
    assert data["counts"] == {"contradicted": 1, "unsupported": 0, "supported": 0}
    assert data["claims"][0]["verdict"] == "contradicted"


# --- CLI end to end with a fake LLM -------------------------------------------

SOURCE = "The recommended dose is 5 mg taken orally twice daily."


def fake_chat(verdict, source_path, quote=SOURCE):
    def chat(messages):
        if "atomic factual claims" in messages[0]["content"]:
            return json.dumps({"claims": [{"claim": "The dose is 5 mg twice daily.", "sentence": "The dose is 5 mg twice daily."}]})
        return json.dumps({"verdict": verdict, "explanation": "x", "quote": quote, "source": source_path})

    return chat


@pytest.fixture
def files(tmp_path):
    source, answer = tmp_path / "label.md", tmp_path / "answer.md"
    source.write_text(SOURCE)
    answer.write_text("The dose is 5 mg twice daily.")
    return str(answer), str(source)


def test_exit_0_when_supported(files, capsys):
    answer, source = files
    assert cli.run([answer, "--sources", source], chat=fake_chat("supported", source)) == 0
    assert "1 supported" in capsys.readouterr().out


def test_exit_1_when_flagged(files):
    answer, source = files
    assert cli.run([answer, "--sources", source], chat=fake_chat("contradicted", source)) == 1


def test_code_rule_downgrade_flags_a_bad_quote(files, capsys):
    answer, source = files
    code = cli.run([answer, "--sources", source, "--json"], chat=fake_chat("supported", source, quote="5 mg once daily"))
    data = json.loads(capsys.readouterr().out)
    assert code == 1
    assert data["claims"][0]["downgrades"][0]["rule"] == "quote"


def test_exit_2_without_sources(files, capsys):
    answer, source = files
    assert cli.run([answer], chat=fake_chat("supported", source)) == 2
    assert "no sources given" in capsys.readouterr().err


def test_exit_2_on_unusable_model_reply(files, capsys):
    answer, source = files
    assert cli.run([answer, "--sources", source], chat=lambda m: "garbage") == 2
    assert "unusable model reply" in capsys.readouterr().err
