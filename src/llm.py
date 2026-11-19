"""
Thin, well-behaved wrapper around the Gemini API.

Two things matter for this project:

1. **Disk cache.**  The free tier of the Gemini API allows only a limited
   number of requests per day.  Every call is therefore cached on disk keyed
   by a hash of (model, prompt, schema).  Re-running an experiment costs zero
   extra quota and the run is resumable after an interruption.

2. **Graceful degradation.**  If no API key is present (or the backend is
   switched to "offline"), a deterministic local planner is used instead so
   that the whole pipeline can still be debugged end-to-end.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .config import (API_KEY_ENV, BACKEND, CACHE_DIR, DEFAULT_MODEL,
                    DEEPSEEK_API_KEY_ENV, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
                    MAX_CAPACITY_ATTEMPTS, MAX_OUTPUT_TOKENS,
                    MAX_QUOTA_RETRIES, MODEL_FALLBACKS, QUOTA_BACKOFF_SECONDS,
                    THINKING_MODE, sanitize_api_key, write_json)
from .openai_client import (ApiError, OpenAICompatibleClient,
                            to_openai_tools)


# --------------------------------------------------------------------------
# encoding safety net
# --------------------------------------------------------------------------
def _ascii_safe(obj: Any) -> Any:
    """Return a copy of *obj* in which every string is pure ASCII.

    HTTP headers, some SDK internals and a few Windows consoles cannot carry
    non-ASCII characters.  When one of them refuses a request, the remedy is
    to strip the offending characters and try again; the project is written in
    English, so nothing of substance is lost.
    """
    if isinstance(obj, str):
        return obj.encode("ascii", "replace").decode("ascii")
    if isinstance(obj, dict):
        return {(k if isinstance(k, str) else k): _ascii_safe(v)
                for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_ascii_safe(v) for v in obj]
    return obj


def _is_invalid_argument(msg: str) -> bool:
    """True when the API rejected the request itself (a bad parameter)."""
    m = msg.lower()
    return "400" in m or "invalid_argument" in m or "invalid argument" in m


def _api_detail(msg: str, limit: int = 220) -> str:
    """Pull the API's own message out of an SDK error string."""
    m = re.search(r"'message':\s*'([^']{4,400})'", msg)
    if m:
        return m.group(1)[:limit]
    m = re.search(r'"message":\s*"([^"]{4,400})"', msg)
    if m:
        return m.group(1)[:limit]
    return msg[:limit]


def _quota_info(msg: str) -> dict:
    """Extract what the API itself says about the quota from a 429 message.

    The Gemini API is helpful here: it states the daily limit of the model
    that was hit, the quota metric, and how long until the reset.  Showing
    those numbers to the user is far more useful than a generic "quota
    exceeded".
    """
    info: dict = {}
    _m = re.search(r"limit:\s*(\d+),\s*model:\s*([\w.\-]+)", msg)
    if _m:
        info["limit"] = int(_m.group(1))
        info["model"] = _m.group(2)
    _m = re.search(r"retry in ([\d.]+h)?(?:(\d+)m)?(?:([\d.]+)s)?", msg)
    if _m:
        h = float(_m.group(1)[:-1]) if _m.group(1) else 0.0
        mnt = float(_m.group(2)) if _m.group(2) else 0.0
        s = float(_m.group(3)) if _m.group(3) else 0.0
        total = h * 3600 + mnt * 60 + s
        if total:
            info["reset_in_seconds"] = total
            hh, rem = divmod(int(total), 3600)
            mm, ss = divmod(rem, 60)
            info["reset_in"] = f"{hh}h {mm}m"
    return info


def _is_capacity_error(msg: str) -> bool:
    """True when Google is telling us the model is overloaded / unavailable."""
    m = msg.lower()
    return ("503" in m or "unavailable" in m or "high demand" in m
            or "overloaded" in m or "internal error" in m)


def _backoff(attempt: int, base: int = 6, cap: int = 60) -> float:
    """Exponential backoff with jitter (a fixed wait makes retry storms)."""
    wait = min(cap, base * (2 ** attempt))
    jittered = wait * (0.75 + 0.5 * ((attempt * 7919) % 13) / 13.0)
    return min(float(cap), jittered)


# Maps our PETSAFE_THINKING setting onto the SDK's thinking_level values.
#
# IMPORTANT: `thinking_budget` must NOT be used with Gemini 3.5 or newer.
# The SDK states it in its own documentation: "Starting from Gemini 3.5
# models, the old thinking_budget will no longer be supported and will
# result in a user error if set."  Sending it to gemini-3.5-flash-lite
# produces
#     400 INVALID_ARGUMENT -- Request contains an invalid argument
# which is exactly the kind of failure that silently ruins a long run.
_THINKING_LEVELS = {"off": "MINIMAL", "low": "LOW", "on": "HIGH"}


def _thinking_config():
    """Return the SDK thinking configuration, or None when not applicable.

    Thinking is the single biggest latency factor: a Gemini 3.x flash model
    that thinks before answering spends most of its wall-clock time in the
    thinking phase, and this project gains nothing from it because every
    checkable property is verified in Python.

    Gemini 3.5+ models only accept ``thinking_level``; ``thinking_budget``
    is rejected with a 400.  We therefore use the level vocabulary.
    """
    level = _THINKING_LEVELS.get(THINKING_MODE)
    if level is None:
        return None
    try:
        from google.genai import types
        return types.ThinkingConfig(thinking_level=level)
    except Exception:                                    # pragma: no cover
        return None


def _log_call(label: str, elapsed: float, p_tok: int, o_tok: int,
              attempt: int) -> None:
    """Print one line per model call so the user can see where time goes."""
    extra = f" attempt {attempt}" if attempt > 1 else ""
    print(f"      [call] {label:<22} {elapsed:6.1f}s  "
          f"in {p_tok:>5} / out {o_tok:>5} tok{extra}", flush=True)


def _save_last_traceback(tb: str) -> str:
    """Write the inner traceback of a failed call to disk for diagnosis."""
    if not tb:
        return ""
    try:
        from .config import RESULTS_DIR
        path = Path(RESULTS_DIR) / "last_error_traceback.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(tb, encoding="utf-8")
        return str(path)
    except Exception:                                    # pragma: no cover
        return ""


# --------------------------------------------------------------------------
# caching
# --------------------------------------------------------------------------
def _cache_key(*parts: Any) -> str:
    blob = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:32]


def cache_get(key: str) -> dict | None:
    path = Path(CACHE_DIR) / f"{key}.json"
    if not path.exists():
        return None
    try:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:      # a cache file written as ASCII escapes
            return json.loads(path.read_text(encoding="ascii"))
    except json.JSONDecodeError:
        return None


def cache_put(key: str, payload: dict) -> None:
    path = Path(CACHE_DIR) / f"{key}.json"
    # NB: never write with the platform default encoding.  On a Windows
    # machine whose locale is ASCII, that cannot represent the non-ASCII
    # characters a model sometimes returns and the write raises
    # UnicodeEncodeError, which used to abort the whole experiment.
    write_json(path, payload)


# --------------------------------------------------------------------------
# usage accounting
# --------------------------------------------------------------------------
@dataclass
class Usage:
    """Token / latency accounting, printed in the final results table."""

    calls: int = 0
    cache_hits: int = 0
    prompt_tokens: int = 0
    output_tokens: int = 0
    total_seconds: float = 0.0
    per_model: dict = field(default_factory=dict)

    def record(self, model: str, prompt_tokens: int, output_tokens: int, seconds: float) -> None:
        self.calls += 1
        self.prompt_tokens += prompt_tokens
        self.output_tokens += output_tokens
        self.total_seconds += seconds
        m = self.per_model.setdefault(model, {"calls": 0, "prompt_tokens": 0, "output_tokens": 0, "seconds": 0.0})
        m["calls"] += 1
        m["prompt_tokens"] += prompt_tokens
        m["output_tokens"] += output_tokens
        m["seconds"] += seconds

    def as_dict(self) -> dict:
        return {
            "calls": self.calls,
            "cache_hits": self.cache_hits,
            "prompt_tokens": self.prompt_tokens,
            "output_tokens": self.output_tokens,
            "total_seconds": round(self.total_seconds, 2),
            "per_model": self.per_model,
        }


USAGE = Usage()


def _schema_hint(schema: dict) -> str:
    """A textual description of a JSON schema, used when the API rejects it."""
    def walk(node: dict, indent: int = 0) -> list[str]:
        pad = "  " * indent
        lines = []
        t = node.get("type")
        if t == "object":
            for key, sub in (node.get("properties") or {}).items():
                if sub.get("type") == "array":
                    lines.append(f"{pad}{key}: array of objects with fields "
                                 + ", ".join((sub.get("items", {}).get("properties") or {}).keys()))
                    lines.extend(walk(sub.get("items", {}), indent + 1))
                elif sub.get("type") == "object":
                    lines.append(f"{pad}{key}: object with fields "
                                 + ", ".join((sub.get("properties") or {}).keys()))
                    lines.extend(walk(sub, indent + 1))
                else:
                    lines.append(f"{pad}{key}: {sub.get('type', 'string')}")
        elif t == "array":
            lines.extend(walk(node.get("items", {}), indent))
        return lines

    body = "\n".join(walk(schema))
    return ("IMPORTANT: answer with a single JSON object and nothing else. "
            "It must have exactly these fields:\n" + body)



# --------------------------------------------------------------------------
# the LLM client
# --------------------------------------------------------------------------
class LLM:
    """A small facade over google-genai with caching, retries and telemetry."""

    def __init__(self, model: str | None = None, backend: str | None = None):
        self.backend = (backend or BACKEND).lower()
        # "gemini" speaks the Gemini protocol, "deepseek" speaks the
        # OpenAI-compatible protocol.  The two differ only in how a request
        # is written and how an answer is read; everything else -- the
        # cache, the retries, the telemetry, the rubric -- is shared.
        self.provider = "deepseek" if self.backend.startswith("deepseek") else "gemini"
        if self.provider == "deepseek":
            self.model = model or DEEPSEEK_MODEL
        else:
            self.model = model or DEFAULT_MODEL
        self._client = None
        self._offline_handler: Callable[..., str] | None = None
        # Models to try when this one is overloaded (503).  The list is
        # consumed in order, so the experiment keeps going.
        self.fallbacks: list[str] = [m for m in MODEL_FALLBACKS if m != self.model]
        # Every model that was actually used, for the record.
        self.models_used: list[str] = [self.model]

    # --------------------------------------------------------------- ping --
    def ping(self) -> tuple[bool, str]:
        """One tiny request.  Returns (answered, reason).

        Used as a pre-flight check: the free tier is shared and a model can
        be unavailable at peak times, so we find out BEFORE the experiment
        starts.  The reason matters, because the three situations need three
        different responses:

        * capacity (503)  -- temporary; the run should proceed and let the
          retry/backoff logic deal with it;
        * quota (429)     -- today's allowance is gone; there is nothing to
          wait for, so stop with a clear message;
        * bad key (401/403) -- stop, the key has to be fixed.
        """
        try:
            if self.provider != "gemini":
                # A provider (or relay) that does not know the
                # DeepSeek-specific 'thinking' field answers 400.  The
                # probe must survive that, otherwise the run refuses to
                # start on a configuration that would work fine.
                for send_thinking in (True, False):
                    try:
                        _res = self._openai_client().chat(
                            model=self.model,
                            messages=[{"role": "user",
                                       "content": "Reply with the single "
                                                  "word: ok"}],
                            temperature=0.0, max_tokens=16, thinking=False,
                            send_thinking=send_thinking)
                        return (bool(_res.text), "ok")
                    except ApiError as exc:
                        if exc.status == 400 and send_thinking:
                            continue
                        raise
                return (False, "error")
            from google.genai import types
            cfg = types.GenerateContentConfig(temperature=0.0)
            _tc = _thinking_config()
            if _tc is not None:
                cfg.thinking_config = _tc
            cfg.max_output_tokens = 16
            response = self.client.models.generate_content(
                model=self.model, contents="Reply with the single word: ok",
                config=cfg)
            return (bool(response.text), "ok")
        except Exception as exc:                          # noqa: BLE001
            msg = str(exc)
            if isinstance(exc, ApiError):
                if exc.status == 402:
                    reason = "balance"
                elif exc.status == 429:
                    reason = "quota"
                elif exc.status in (401, 403):
                    reason = "auth"
                elif exc.status >= 500:
                    reason = "capacity"
                else:
                    reason = "error"
                msg = exc.message
            elif "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                reason = "quota"
            elif "401" in msg or "403" in msg or "API key" in msg:
                reason = "auth"
            elif _is_capacity_error(msg):
                reason = "capacity"
            else:
                reason = "error"
            print(f"      [probe] {self.model}: {reason} "
                  f"({_api_detail(msg, 120)})", flush=True)
            return (False, reason)

    # ------------------------------------------------------------ client --
    @property
    def client(self):
        if self._client is None:
            from google import genai

            api_key = os.environ.get(API_KEY_ENV)
            if not api_key:
                raise RuntimeError(
                    f"{API_KEY_ENV} is not set. Get a free key at "
                    "https://aistudio.google.com/apikey  (AI Studio -> Create API key), "
                    "then run:  export GEMINI_API_KEY=your_key"
                )
            # An HTTP header must be ASCII.  The SDK puts the key in the
            # x-goog-api-key header, so a key copied from a web page that
            # picked up a stray Chinese / full-width character would fail
            # with "'ascii' codec can't encode characters in position ..."
            # before the request is even sent.  Clean it and say so.
            api_key, problems = sanitize_api_key(api_key)
            for problem in problems:
                print(f"WARNING: {API_KEY_ENV} -> {problem}.")
                print("         The key was cleaned automatically, but please "
                      "re-copy it from https://aistudio.google.com/apikey .")
            self._client = genai.Client(api_key=api_key)
        return self._client

    def register_offline(self, handler: Callable[..., str]) -> None:
        """Install the deterministic stand-in used when there is no API key."""
        self._offline_handler = handler

    # ================================================== OpenAI-compatible ==
    # The methods below speak the OpenAI chat-completions protocol, which is
    # what DeepSeek (and every other compatible service) uses.  The Gemini
    # implementation further down is untouched.
    def _openai_client(self) -> OpenAICompatibleClient:
        if self._client is None:
            key = os.environ.get(DEEPSEEK_API_KEY_ENV) or os.environ.get(API_KEY_ENV)
            if not key:
                raise RuntimeError(
                    f"{DEEPSEEK_API_KEY_ENV} is not set. Create a key at "
                    "https://platform.deepseek.com/api_keys , then put it in "
                    f"your .env file as {DEEPSEEK_API_KEY_ENV}=sk-...")
            key, problems = sanitize_api_key(key)
            for problem in problems:
                print(f"WARNING: {DEEPSEEK_API_KEY_ENV} -> {problem}.")
            self._client = OpenAICompatibleClient(key, DEEPSEEK_BASE_URL)
        return self._client

    def _openai_messages(self, prompt: str,
                         system_instruction: str | None) -> list[dict]:
        messages: list[dict] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _generate_openai(
        self,
        prompt: str,
        system_instruction: str | None = None,
        json_schema: dict | None = None,
        temperature: float = 0.4,
        tag: str = "default",
    ) -> str:
        key = _cache_key(self.model, prompt, system_instruction, json_schema,
                        f"backend={self.backend}",
                        f"think={THINKING_MODE}", f"maxtok={MAX_OUTPUT_TOKENS}")
        cached = cache_get(key)
        if cached is not None:
            USAGE.cache_hits += 1
            return cached["text"]

        client = self._openai_client()
        messages = self._openai_messages(prompt, system_instruction)
        response_format = {"type": "json_object"} if json_schema else None
        hint = ("Return the answer as a single JSON object and nothing else."
                if json_schema else None)

        last_error: Exception | None = None
        minimal_retried = False
        for attempt in range(MAX_CAPACITY_ATTEMPTS):
            try:
                start = time.time()
                result = client.chat(
                    model=self.model,
                    messages=messages,
                    response_format=response_format,
                    temperature=temperature,
                    max_tokens=MAX_OUTPUT_TOKENS or None,
                    thinking=False,
                    json_mode_hint=hint,
                    send_thinking=not minimal_retried,
                )
                elapsed = time.time() - start
                text = result.text
                USAGE.record(self.model, result.prompt_tokens,
                             result.completion_tokens, elapsed)
                _log_call(tag, elapsed, result.prompt_tokens,
                          result.completion_tokens, attempt + 1)
                cache_put(key, {"text": text, "model": self.model,
                                "backend": self.provider,
                                "prompt_tokens": result.prompt_tokens,
                                "output_tokens": result.completion_tokens})
                return text
            except ApiError as exc:
                last_error = exc
                if exc.status == 400 and not minimal_retried:
                    # The provider -- or a relay in front of it -- rejected
                    # the request.  The most likely cause is a field it does
                    # not know (`thinking` is DeepSeek-specific), so retry
                    # once without it before giving up.
                    minimal_retried = True
                    print(f"      [400] the provider rejected the request "
                          f"({exc.message}); retrying without the "
                          f"provider-specific 'thinking' field.", flush=True)
                    continue
                if (exc.status in (429, 500, 502, 503)
                        and attempt < MAX_CAPACITY_ATTEMPTS - 1):
                    wait = _backoff(attempt)
                    print(f"      [{exc.status}] the provider is busy, "
                          f"retrying in {wait:.0f}s "
                          f"(attempt {attempt + 1}/{MAX_CAPACITY_ATTEMPTS})",
                          flush=True)
                    time.sleep(wait)
                    continue
                if exc.status == 402:
                    raise RuntimeError(
                        "The DeepSeek account has no balance left (HTTP 402). "
                        "Top it up at https://platform.deepseek.com . Nothing "
                        "is lost: every successful call is cached, so re-running "
                        "resumes where it stopped.") from exc
                if exc.status in (401, 403):
                    raise RuntimeError(
                        f"The API key was rejected (HTTP {exc.status}). Check "
                        f"the {DEEPSEEK_API_KEY_ENV} line in your .env file "
                        f"({exc.message}).") from exc
                break
            except Exception as exc:                    # noqa: BLE001
                last_error = exc
                break

        where = _save_last_traceback(traceback.format_exc())
        raise RuntimeError(
            f"The OpenAI-compatible provider failed: "
            f"[{type(last_error).__name__}] {last_error}"
            + (f"\n       the inner traceback was saved to {where}" if where else "")
        )

    def _tool_loop_openai(
        self,
        prompt: str,
        system_instruction: str | None = None,
        tools: list | None = None,
        dispatch: dict[str, Callable] | None = None,
        max_rounds: int = 3,
        tag: str = "agent",
    ) -> dict:
        """The manual tool-calling loop, OpenAI-compatible protocol."""
        declarations: list[Any] = []
        for tool in (tools or []):
            decls = getattr(tool, "function_declarations", None)
            if decls is None:
                decls = getattr(tool, "function_declarations", []) or []
            declarations.extend(decls)
        openai_tools = to_openai_tools(declarations)

        key = _cache_key(self.model, prompt, system_instruction,
                         [d.model_dump_json() for d in declarations],
                         sorted((dispatch or {}).keys()), max_rounds, tag,
                         f"backend={self.backend}",
                         f"think={THINKING_MODE}", f"maxtok={MAX_OUTPUT_TOKENS}")
        cached = cache_get(key)
        if cached is not None:
            USAGE.cache_hits += 1
            return cached

        client = self._openai_client()
        messages = self._openai_messages(prompt, system_instruction)
        transcript: list[dict] = []
        last_error: Exception | None = None
        minimal_retried = False

        for attempt in range(MAX_CAPACITY_ATTEMPTS):
            try:
                start = time.time()
                rounds = 0
                while rounds < max_rounds:
                    result = client.chat(
                        model=self.model,
                        messages=messages,
                        tools=openai_tools or None,
                        temperature=0.2,
                        max_tokens=MAX_OUTPUT_TOKENS or None,
                        thinking=False,
                        send_thinking=not minimal_retried,
                    )
                    if not result.tool_calls:
                        elapsed = time.time() - start
                        USAGE.record(self.model, result.prompt_tokens,
                                     result.completion_tokens, elapsed)
                        _log_call(f"{tag}:tool", elapsed, result.prompt_tokens,
                                  result.completion_tokens, attempt + 1)
                        payload = {
                            "text": result.text,
                            "transcript": transcript,
                            "n_calls": len(transcript),
                            "n_rounds": rounds,
                            "backend": self.provider,
                            "model": self.model,
                        }
                        cache_put(key, payload)
                        return payload

                    assistant_msg: dict[str, Any] = {
                        "role": "assistant",
                        "content": result.text or None,
                    }
                    if result.reasoning_content:
                        assistant_msg["reasoning_content"] = result.reasoning_content
                    assistant_msg["tool_calls"] = [
                        {"id": c.id, "type": "function",
                         "function": {"name": c.name,
                                      "arguments": json.dumps(c.arguments)}}
                        for c in result.tool_calls
                    ]
                    messages.append(assistant_msg)

                    for call in result.tool_calls:
                        fn = (dispatch or {}).get(call.name)
                        try:
                            out = (fn(**{k: v for k, v in call.arguments.items()
                                          if v is not None})
                                   if fn else {"error": f"unknown tool {call.name}"})
                        except Exception as exc:        # noqa: BLE001
                            out = {"error": str(exc)}
                        transcript.append({"tool": call.name,
                                           "args": call.arguments,
                                           "result": out})
                        messages.append({
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": json.dumps(out, ensure_ascii=False, default=str),
                        })
                    rounds += 1

                # ran out of rounds: ask for the final answer without tools
                result = client.chat(
                    model=self.model, messages=messages, temperature=0.2,
                    max_tokens=MAX_OUTPUT_TOKENS or None, thinking=False,
                    send_thinking=not minimal_retried)
                elapsed = time.time() - start
                USAGE.record(self.model, result.prompt_tokens,
                             result.completion_tokens, elapsed)
                _log_call(f"{tag}:tool", elapsed, result.prompt_tokens,
                          result.completion_tokens, attempt + 1)
                payload = {
                    "text": result.text,
                    "transcript": transcript,
                    "n_calls": len(transcript),
                    "n_rounds": rounds,
                    "backend": self.provider,
                    "model": self.model,
                }
                cache_put(key, payload)
                return payload
            except ApiError as exc:
                last_error = exc
                if exc.status == 400 and not minimal_retried:
                    # The provider -- or a relay in front of it -- rejected
                    # the request.  The most likely cause is a field it does
                    # not know (`thinking` is DeepSeek-specific), so retry
                    # once without it before giving up.
                    minimal_retried = True
                    print(f"      [400] the provider rejected the request "
                          f"({exc.message}); retrying without the "
                          f"provider-specific 'thinking' field.", flush=True)
                    continue
                if (exc.status in (429, 500, 502, 503)
                        and attempt < MAX_CAPACITY_ATTEMPTS - 1):
                    wait = _backoff(attempt)
                    print(f"      [{exc.status}] the provider is busy, "
                          f"retrying in {wait:.0f}s "
                          f"(attempt {attempt + 1}/{MAX_CAPACITY_ATTEMPTS})",
                          flush=True)
                    time.sleep(wait)
                    continue
                break
            except Exception as exc:                    # noqa: BLE001
                last_error = exc
                break

        where = _save_last_traceback(traceback.format_exc())
        raise RuntimeError(
            f"The tool loop failed: [{type(last_error).__name__}] {last_error}"
            + (f"\n       the inner traceback was saved to {where}" if where else "")
        )

    # -------------------------------------------------------------- text --
    def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        tools: list | None = None,
        json_schema: dict | None = None,
        temperature: float = 0.4,
        tag: str = "default",
    ) -> str:
        """
        One model call.  Returns the text answer.

        If `tools` is given, automatic function calling is used and the SDK
        executes the Python functions for us; the resulting transcript (tool
        calls + tool outputs) is written into the cache so the agent loop is
        fully reproducible.
        """
        if self.provider != "gemini":
            return self._generate_openai(
                prompt=prompt, system_instruction=system_instruction,
                json_schema=json_schema, temperature=temperature, tag=tag)
        # The backend belongs in the cache key: the same prompt answered by a
        # different provider is a different answer, and the offline simulator
        # must never be served a cached real API answer (or the other way
        # round).
        key = _cache_key(self.model, prompt, system_instruction, json_schema, tools,
                        f"backend={self.backend}",
                        f"think={THINKING_MODE}", f"maxtok={MAX_OUTPUT_TOKENS}")
        cached = cache_get(key)
        if cached is not None:
            USAGE.cache_hits += 1
            return cached["text"]

        if self.backend == "offline" or self._offline_handler is not None:
            if self._offline_handler is None:
                raise RuntimeError("offline backend requested but no handler registered")
            text = self._offline_handler(prompt=prompt, system_instruction=system_instruction,
                                         tools=tools, json_schema=json_schema, tag=tag)
            cache_put(key, {"text": text, "model": self.model, "backend": "offline"})
            return text

        from google.genai import types

        cfg = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
            tools=tools,
        )
        _tc = _thinking_config()
        if _tc is not None:
            cfg.thinking_config = _tc
        if MAX_OUTPUT_TOKENS:
            cfg.max_output_tokens = MAX_OUTPUT_TOKENS
        if json_schema:
            cfg.response_mime_type = "application/json"
            cfg.response_json_schema = json_schema

        last_error: Exception | None = None
        last_tb = ""
        schema_rejected = False
        ascii_retried = False
        quota_hits = 0
        capacity_hits = 0
        other_errors = 0
        minimal_retried = False
        for attempt in range(MAX_CAPACITY_ATTEMPTS):
            try:
                start = time.time()
                response = self.client.models.generate_content(
                    model=self.model, contents=prompt, config=cfg
                )
                elapsed = time.time() - start
                text = response.text or ""
                usage = getattr(response, "usage_metadata", None)
                p_tok = getattr(usage, "prompt_token_count", 0) or 0
                o_tok = getattr(usage, "candidates_token_count", 0) or 0
                USAGE.record(self.model, p_tok, o_tok, elapsed)
                _log_call(tag, elapsed, p_tok, o_tok, attempt + 1)
                cache_put(key, {"text": text, "model": self.model, "backend": "gemini",
                                "prompt_tokens": p_tok, "output_tokens": o_tok})
                return text
            except Exception as exc:  # noqa: BLE001 - we want a generic retry
                last_error = exc
                last_tb = traceback.format_exc()
                msg = str(exc)
                if isinstance(exc, UnicodeEncodeError) and not ascii_retried:
                    # Something in the request could not be encoded (a stray
                    # non-ASCII character in the prompt, or in the API key).
                    # Strip them and try once more instead of failing the run.
                    ascii_retried = True
                    prompt = _ascii_safe(prompt)
                    system_instruction = _ascii_safe(system_instruction)
                    cfg = types.GenerateContentConfig(
                        temperature=temperature,
                        system_instruction=system_instruction,
                        tools=_ascii_safe(tools),
                    )
                    _tc = _thinking_config()
                    if _tc is not None:
                        cfg.thinking_config = _tc
                    if MAX_OUTPUT_TOKENS:
                        cfg.max_output_tokens = MAX_OUTPUT_TOKENS
                    if json_schema:
                        cfg.response_mime_type = "application/json"
                        cfg.response_json_schema = json_schema
                    continue
                if json_schema and not schema_rejected and (
                    "schema" in msg.lower() or "json_schema" in msg.lower()
                    or "response_json" in msg.lower()
                ):
                    # The API refused our structured-output schema.  Fall back
                    # to plain JSON mode and describe the schema in the prompt
                    # instead, so the run continues with the same contract.
                    schema_rejected = True
                    cfg.response_json_schema = None
                    prompt = prompt + "\n\n" + _schema_hint(json_schema)
                    continue
                if _is_invalid_argument(msg) and not minimal_retried:
                    # The model rejected something in the request (a parameter
                    # it does not support, most often).  Retry once with the
                    # smallest possible configuration, so one unsupported
                    # knob cannot ruin the whole experiment.
                    minimal_retried = True
                    print(f"      [400] the model rejected the request "
                          f"({_api_detail(msg)}); retrying with a minimal "
                          f"configuration (no thinking level, no token cap).",
                          flush=True)
                    cfg = types.GenerateContentConfig(
                        temperature=temperature,
                        system_instruction=system_instruction,
                        tools=tools,
                    )
                    if json_schema:
                        cfg.response_mime_type = "application/json"
                        cfg.response_json_schema = json_schema
                    continue
                if _is_capacity_error(msg):
                    # The free tier is shared; peaks are transient.  Wait
                    # longer each time (with jitter) and, if the model stays
                    # unavailable, switch to a fallback model.
                    capacity_hits += 1
                    if capacity_hits >= 3 and self.fallbacks:
                        nxt = self.fallbacks.pop(0)
                        print(f"      [model] {self.model} is overloaded "
                              f"(503). Switching to {nxt} for the rest of "
                              f"this run.", flush=True)
                        self.models_used.append(nxt)
                        self.model = nxt
                        capacity_hits = 0
                        continue
                    if capacity_hits > 12:
                        raise RuntimeError(
                            f"Model '{self.model}' stayed overloaded (503) for "
                            f"{capacity_hits} attempts. This is Google-side "
                            f"capacity, not a bug. Wait a few minutes and "
                            f"re-run: every finished call is cached, so the "
                            f"re-run resumes where it stopped.\n"
                            f"       If it stays overloaded, try another model "
                            f"with the same quota class:  set PETSAFE_MODEL="
                            f"gemini-3.5-flash-lite\n"
                            f"       (never switch to gemini-3.6/3.8-flash "
                            f"here -- they allow only ~20 calls/day, which "
                            f"cannot finish the benchmark).")
                    wait = _backoff(attempt)
                    print(f"      [503] model overloaded, retrying in "
                          f"{wait:.0f}s (attempt {attempt + 1}/{MAX_CAPACITY_ATTEMPTS})",
                          flush=True)
                    time.sleep(wait)
                    continue
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    quota_hits += 1
                    if quota_hits > MAX_QUOTA_RETRIES:
                        _q = _quota_info(msg)
                        _limit = _q.get("limit")
                        _hit = _q.get("model", self.model)
                        _reset = _q.get("reset_in", "at midnight Pacific Time")
                        raise RuntimeError(
                            f"The daily free-tier quota is exhausted for "
                            f"model '{_hit}'"
                            + (f" ({_limit} requests/day)" if _limit else "")
                            + f". It resets in {_reset}.\n"
                            f"       Nothing is lost: every successful call is "
                            f"cached, so re-running resumes where it stopped.\n"
                            f"       To run sooner, use a model with a larger "
                            f"daily limit -- gemini-3.5-flash-lite allows "
                            f"about 500 requests/day, while gemini-3.6-flash "
                            f"and gemini-3.8-flash allow only about 20.\n"
                            f"       Run it with:  set PETSAFE_MODEL="
                            f"gemini-3.5-flash-lite")
                    wait = QUOTA_BACKOFF_SECONDS
                elif "500" in msg or "503" in msg:
                    wait = 5 * (attempt + 1)
                else:
                    wait = 2
                    other_errors += 1
                    if other_errors >= 3:
                        break        # not a capacity problem: fail fast
                time.sleep(wait)
        where = _save_last_traceback(last_tb)
        raise RuntimeError(
            f"Gemini call failed after {capacity_hits} capacity retries "
            f"[{type(last_error).__name__}]: {_api_detail(str(last_error))}"
            + (f"\n       the inner traceback was saved to {where}" if where else "")
        )

    # ------------------------------------------------------- tool-calling --
    def tool_loop(
        self,
        prompt: str,
        system_instruction: str | None = None,
        tools: list | None = None,
        dispatch: dict[str, Callable] | None = None,
        max_rounds: int = 3,
        tag: str = "agent",
    ) -> dict:
        """
        Run one *manual* tool-calling turn and return everything we need:

            {"text": <final assistant text>,
             "transcript": [{"tool":..., "args":..., "result":...}, ...],
             "n_calls": <int>, "n_rounds": <int>}

        The loop is manual (not the SDK's automatic mode) on purpose: the
        agent's tool invocations are the core object of study in this project,
        so they must be logged, counted and reproducible.  The whole turn is
        cached as a unit, so re-running the experiment costs no API quota.
        """
        key = _cache_key(
            self.model, prompt, system_instruction,
            [t.model_dump_json() for t in (tools or [])],
            sorted((dispatch or {}).keys()), max_rounds, tag,
            f"backend={self.backend}",
            f"think={THINKING_MODE}", f"maxtok={MAX_OUTPUT_TOKENS}",
        )
        if self.provider != "gemini":
            return self._tool_loop_openai(
                prompt=prompt, system_instruction=system_instruction,
                tools=tools, dispatch=dispatch, max_rounds=max_rounds, tag=tag)

        cached = cache_get(key)
        if cached is not None:
            USAGE.cache_hits += 1
            return cached

        if self.backend == "offline" or self._offline_handler is not None:
            # The offline planner bypasses tool-calling entirely.
            text = self.generate(prompt, system_instruction, tools=None, tag=tag)
            payload = {"text": text, "transcript": [], "n_calls": 0, "n_rounds": 0,
                       "backend": "offline"}
            cache_put(key, payload)
            return payload

        from google.genai import types

        cfg = types.GenerateContentConfig(
            temperature=0.2,
            system_instruction=system_instruction,
            tools=tools,
        )
        _tc = _thinking_config()
        if _tc is not None:
            cfg.thinking_config = _tc
        if MAX_OUTPUT_TOKENS:
            cfg.max_output_tokens = MAX_OUTPUT_TOKENS
        transcript: list[dict] = []
        last_error: Exception | None = None
        last_tb = ""
        ascii_retried = False
        minimal_retried = False
        capacity_hits = 0
        other_errors = 0
        for attempt in range(MAX_CAPACITY_ATTEMPTS):
            try:
                start = time.time()
                chat = self.client.chats.create(model=self.model, config=cfg)
                response = chat.send_message(prompt)
                rounds = 0
                while response.function_calls and rounds < max_rounds:
                    for call in response.function_calls:
                        args = dict(call.args or {})
                        fn = (dispatch or {}).get(call.name)
                        if fn is None:
                            result = {"error": f"unknown tool {call.name}"}
                        else:
                            try:
                                result = fn(**{k: v for k, v in args.items() if v is not None})
                            except Exception as exc:  # noqa: BLE001
                                result = {"error": str(exc)}
                        transcript.append({"tool": call.name, "args": args, "result": result})
                    response = chat.send_message(
                        types.Part.from_function_response(
                            name=response.function_calls[0].name,
                            response={"result": transcript[-1]["result"]},
                        )
                    )
                    # re-send any further function responses for the same turn
                    for extra in (response.function_calls or [])[1:]:
                        args = dict(extra.args or {})
                        fn = (dispatch or {}).get(extra.name)
                        try:
                            result = fn(**{k: v for k, v in args.items() if v is not None}) if fn else {"error": "unknown tool"}
                        except Exception as exc:  # noqa: BLE001
                            result = {"error": str(exc)}
                        transcript.append({"tool": extra.name, "args": args, "result": result})
                        response = chat.send_message(
                            types.Part.from_function_response(name=extra.name, response={"result": result})
                        )
                    rounds += 1
                elapsed = time.time() - start
                usage = getattr(response, "usage_metadata", None)
                p_tok = getattr(usage, "prompt_token_count", 0) or 0
                o_tok = getattr(usage, "candidates_token_count", 0) or 0
                USAGE.record(self.model, p_tok, o_tok, elapsed)
                _log_call(f"{tag}:tool", elapsed, p_tok, o_tok, attempt + 1)
                payload = {
                    "text": response.text or "",
                    "transcript": transcript,
                    "n_calls": len(transcript),
                    "n_rounds": rounds,
                    "backend": "gemini",
                    "model": self.model,
                }
                cache_put(key, payload)
                return payload
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                last_tb = traceback.format_exc()
                _msg = str(exc)
                if _is_invalid_argument(_msg) and not minimal_retried:
                    minimal_retried = True
                    print(f"      [400] the model rejected the request "
                          f"({_api_detail(_msg)}); retrying with a minimal "
                          f"configuration (no thinking level, no token cap).",
                          flush=True)
                    cfg = types.GenerateContentConfig(
                        temperature=0.2,
                        system_instruction=system_instruction,
                        tools=tools,
                    )
                    continue
                if _is_capacity_error(_msg):
                    capacity_hits += 1
                    if capacity_hits >= 3 and self.fallbacks:
                        nxt = self.fallbacks.pop(0)
                        print(f"      [model] {self.model} is overloaded "
                              f"(503). Switching to {nxt}.", flush=True)
                        self.models_used.append(nxt)
                        self.model = nxt
                        capacity_hits = 0
                        continue
                    if capacity_hits > 12:
                        raise RuntimeError(
                            f"Model '{self.model}' stayed overloaded (503) for "
                            f"{capacity_hits} attempts. This is Google-side "
                            f"capacity, not a bug -- wait a few minutes and "
                            f"re-run: every finished call is cached, so the "
                            f"re-run resumes where it stopped.")
                    wait = _backoff(attempt)
                    print(f"      [503] model overloaded, retrying in "
                          f"{wait:.0f}s (attempt {attempt + 1}/{MAX_CAPACITY_ATTEMPTS})",
                          flush=True)
                    time.sleep(wait)
                    continue
                if isinstance(exc, UnicodeEncodeError) and not ascii_retried:
                    # A non-ASCII character somewhere in the request could not
                    # be encoded.  Strip every non-ASCII character from the
                    # prompt, the system instruction and the tool schema and
                    # try once more; the design content is English, so
                    # nothing meaningful is lost.
                    ascii_retried = True
                    prompt = _ascii_safe(prompt)
                    system_instruction = _ascii_safe(system_instruction)
                    tools = _ascii_safe(tools)
                    transcript = _ascii_safe(transcript)
                    cfg = types.GenerateContentConfig(
                        temperature=0.2,
                        system_instruction=system_instruction,
                        tools=tools,
                    )
                    _tc = _thinking_config()
                    if _tc is not None:
                        cfg.thinking_config = _tc
                    if MAX_OUTPUT_TOKENS:
                        cfg.max_output_tokens = MAX_OUTPUT_TOKENS
                    continue
                other_errors += 1
                if other_errors >= 3:
                    break            # not a capacity problem: fail fast
                time.sleep(2 * (attempt + 1))
        where = _save_last_traceback(last_tb)
        raise RuntimeError(
            f"Gemini tool loop failed after {capacity_hits} capacity retries "
            f"[{type(last_error).__name__}]: {_api_detail(str(last_error))}"
            + (f"\n       the inner traceback was saved to {where}" if where else "")
        )

    # ------------------------------------------------- tool-call transcript --
    def generate_with_transcript(
        self,
        prompt: str,
        system_instruction: str | None = None,
        tools: list | None = None,
        temperature: float = 0.4,
        tag: str = "default",
    ) -> tuple[str, list[dict]]:
        """
        A model call that is allowed to use tools, returning both the final
        text and a transcript of every tool call that was made.  The
        transcript is what the report uses to show the agent's reasoning trace.
        """
        from google.genai import types

        transcript: list[dict] = []
        if self.backend == "offline" or self._offline_handler is not None:
            text = self.generate(prompt, system_instruction, tools=tools, tag=tag)
            return text, transcript

        cfg = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
            tools=tools,
        )
        last_error: Exception | None = None
        minimal_retried = False
        for attempt in range(MAX_CAPACITY_ATTEMPTS):
            try:
                start = time.time()
                response = self.client.models.generate_content(
                    model=self.model, contents=prompt, config=cfg
                )
                elapsed = time.time() - start
                for part in (response.function_calls or []):
                    transcript.append({"tool": part.name, "args": dict(part.args or {})})
                text = response.text or ""
                usage = getattr(response, "usage_metadata", None)
                p_tok = getattr(usage, "prompt_token_count", 0) or 0
                o_tok = getattr(usage, "candidates_token_count", 0) or 0
                USAGE.record(self.model, p_tok, o_tok, elapsed)
                return text, transcript
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"Gemini tool call failed after 5 attempts: {last_error}")
