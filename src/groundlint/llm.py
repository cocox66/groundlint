"""The one place that talks to an OpenAI-compatible chat completions endpoint.

Uses only the standard library, so groundlint has no runtime dependencies.
The API key is read from the environment and never printed or logged.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"
KEY_VARIABLES = ("GROUNDLINT_API_KEY", "NVIDIA_API_KEY")
TIMEOUT_SECONDS = 120
RETRY_STATUS = {429, 500, 502, 503, 504}

# A chat function takes a list of messages and returns the reply text.
Chat = Callable[[list[dict[str, str]]], str]


class LLMError(Exception):
    """The endpoint failed, or its reply couldn't be used."""


@dataclass(frozen=True)
class Settings:
    base_url: str
    model: str
    api_key: str

    def __repr__(self) -> str:  # never show the key
        return f"Settings(base_url={self.base_url!r}, model={self.model!r}, api_key=<hidden>)"


def settings(base_url: str | None = None, model: str | None = None) -> Settings:
    """Flags win over environment variables, which win over the defaults."""
    key = next((os.environ[v] for v in KEY_VARIABLES if os.environ.get(v)), None)
    if not key:
        raise LLMError(f"no API key: set {' or '.join(KEY_VARIABLES)}")
    return Settings(
        base_url=(base_url or os.environ.get("GROUNDLINT_BASE_URL") or DEFAULT_BASE_URL).rstrip("/"),
        model=model or os.environ.get("GROUNDLINT_MODEL") or DEFAULT_MODEL,
        api_key=key,
    )


def client(config: Settings, retries: int = 2) -> Chat:
    """Return a chat function bound to these settings."""

    def chat(messages: list[dict[str, str]]) -> str:
        body = json.dumps({"model": config.model, "messages": messages, "temperature": 0}).encode()
        request = urllib.request.Request(
            f"{config.base_url}/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
        )
        for attempt in range(retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                    payload = json.load(response)
                break
            except urllib.error.HTTPError as error:
                if error.code in RETRY_STATUS and attempt < retries:
                    time.sleep(2 * (attempt + 1))
                    continue
                detail = error.read(300).decode("utf-8", "replace").strip()
                raise LLMError(f"{config.model} at {config.base_url}: HTTP {error.code} {detail}") from None
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                if attempt < retries:
                    time.sleep(2 * (attempt + 1))
                    continue
                reason = getattr(error, "reason", error)
                raise LLMError(f"could not reach {config.base_url}: {reason}") from None
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise LLMError(f"{config.model} returned no message content") from None
        if not content:
            raise LLMError(f"{config.model} returned an empty message")
        return content

    return chat


def parse_json(text: str) -> Any:
    """Parse a JSON object from a model reply, tolerating code fences and surrounding prose."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    raise LLMError(f"model reply is not JSON: {text[:200]!r}")


def ask_json(chat: Chat, messages: list[dict[str, str]], validate: Callable[[Any], Any], attempts: int = 2) -> Any:
    """Call the model and return validate(parsed reply), asking again once if the reply is unusable."""
    error: Exception | None = None
    for _ in range(attempts):
        reply = chat(messages)
        try:
            return validate(parse_json(reply))
        except (LLMError, ValueError, KeyError, TypeError) as exc:
            error = exc
            messages = messages + [
                {"role": "assistant", "content": reply},
                {"role": "user", "content": f"That reply was not usable ({exc}). Reply with only the JSON object."},
            ]
    raise LLMError(f"unusable model reply after {attempts} attempts: {error}")
