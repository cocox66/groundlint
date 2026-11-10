"""Load the answer and the source files.

Only .txt and .md are accepted. Text over the size limit stops the run with
the actual size and the limit; nothing is ever silently cut.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, TextIO

from groundlint.models import Source

EXTENSIONS = {".txt", ".md"}
# About 50,000 tokens of English: fits the default model's context with room
# for the prompt and reply, and keeps a per-claim judge call affordable.
SOURCE_LIMIT_CHARS = 200_000
ANSWER_LIMIT_CHARS = 20_000


class LoadError(Exception):
    """An input couldn't be loaded. The message is shown to the user as is."""


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise LoadError(f"{path}: not UTF-8 text") from None
    except OSError as error:
        raise LoadError(f"{path}: {error.strerror or error}") from None


def load_answer(path: str, stdin: TextIO = sys.stdin) -> str:
    """Read the answer from a file, or from stdin when the path is '-'."""
    if path == "-":
        text = stdin.read()
        name = "stdin"
    else:
        file = Path(path)
        if not file.is_file():
            raise LoadError(f"answer file not found: {path}")
        if file.suffix.lower() not in EXTENSIONS:
            raise LoadError(f"answer must be a .txt or .md file: {path}")
        text = _read(file)
        name = path
    if not text.strip():
        raise LoadError(f"answer is empty: {name}")
    if len(text) > ANSWER_LIMIT_CHARS:
        raise LoadError(f"answer is {len(text):,} characters; the limit is {ANSWER_LIMIT_CHARS:,}")
    return text


def _files(paths: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            found = sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS)
            if not found:
                raise LoadError(f"no .txt or .md files in folder: {raw}")
            files.extend(found)
        elif path.is_file():
            if path.suffix.lower() not in EXTENSIONS:
                raise LoadError(f"sources must be .txt or .md files (convert PDFs to text first): {raw}")
            files.append(path)
        else:
            raise LoadError(f"source not found: {raw}")
    return list(dict.fromkeys(files))  # drop duplicates, keep order


def load_sources(paths: Iterable[str] | None, answer_path: str | None = None) -> list[Source]:
    """Load every source file, or stop if there are none or they're too large.

    The answer file is skipped if a source folder contains it, so the answer
    can never count as evidence for itself.
    """
    paths = list(paths or [])
    if not paths:
        raise LoadError("no sources given: pass at least one file or folder with --sources")
    files = _files(paths)
    if answer_path and answer_path != "-":
        answer = Path(answer_path).resolve()
        files = [f for f in files if f.resolve() != answer]
        if not files:
            raise LoadError("the only source given is the answer file itself")
    sources = [Source(path=str(f), text=_read(f)) for f in files]
    sources = [s for s in sources if s.text.strip()]
    if not sources:
        raise LoadError("every source file is empty")
    total = sum(len(s.text) for s in sources)
    if total > SOURCE_LIMIT_CHARS:
        raise LoadError(
            f"sources are {total:,} characters in total; the limit is {SOURCE_LIMIT_CHARS:,}. "
            "Pass fewer or shorter files (text is never cut)."
        )
    return sources
