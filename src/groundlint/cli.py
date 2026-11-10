"""The groundlint command: parse arguments, run the pipeline, pick the exit code."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from groundlint import llm, report
from groundlint.checks import check
from groundlint.extract import extract
from groundlint.judge import judge_all
from groundlint.sources import LoadError, load_answer, load_sources

EXIT_CLEAN, EXIT_FLAGGED, EXIT_FAILED = 0, 1, 2


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="groundlint",
        description="Flag claims in an LLM answer that its sources don't support.",
        epilog=(
            "Exit codes: 0 nothing flagged, 1 at least one claim flagged, 2 groundlint failed. "
            f"API key: {' or '.join(llm.KEY_VARIABLES)}. "
            "Answers and sources are sent to the configured API; don't send confidential data."
        ),
    )
    p.add_argument("answer", help="answer file (.txt or .md), or - to read from stdin")
    p.add_argument("--sources", nargs="+", metavar="PATH", help="source files or folders (.txt or .md)")
    p.add_argument("--json", action="store_true", help="print machine-readable JSON instead of the report")
    p.add_argument("--model", help=f"model name (env GROUNDLINT_MODEL, default {llm.DEFAULT_MODEL})")
    p.add_argument(
        "--base-url", help=f"OpenAI-compatible base URL (env GROUNDLINT_BASE_URL, default {llm.DEFAULT_BASE_URL})"
    )
    return p


def run(argv: Sequence[str] | None = None, chat: llm.Chat | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        answer = load_answer(args.answer)
        sources = load_sources(args.sources)
        if chat is None:
            config = llm.settings(base_url=args.base_url, model=args.model)
            chat, model = llm.client(config), config.model
        else:
            model = args.model or "test"
        claims = extract(answer, chat)
        judgments = [check(j, sources) for j in judge_all(claims, sources, chat)]
    except (LoadError, llm.LLMError) as error:
        print(f"groundlint: error: {error}", file=sys.stderr)
        return EXIT_FAILED
    except KeyboardInterrupt:
        print("groundlint: interrupted", file=sys.stderr)
        return EXIT_FAILED

    print(report.to_json(judgments, model) if args.json else report.to_text(judgments, model))
    return EXIT_FLAGGED if report.flagged(judgments) else EXIT_CLEAN


def main() -> None:
    try:
        code = run()  # argparse usage errors exit with 2 on their own
    except Exception as error:  # any other failure is still exit 2, not a traceback with exit 1
        print(f"groundlint: unexpected error: {type(error).__name__}: {error}", file=sys.stderr)
        code = EXIT_FAILED
    sys.exit(code)
