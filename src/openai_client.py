#!/usr/bin/env python3
"""
A tiny OpenAI-compatible chat client, written with the standard library only.

Why not the `openai` package?  Two reasons:

  1. no new dependency has to be installed on the student's machine (the
     whole project runs on four packages, and one more is one more thing that
     can fail to install behind a firewall);
  2. the request format is completely visible in one screen, which matters
     when a provider rejects one parameter.

It talks to any endpoint that implements `POST {base_url}/chat/completions`
with the OpenAI request/response shape -- DeepSeek is the one this project
uses, but the base URL is configurable.

DeepSeek specifics that this client handles:

  * `thinking` is ON by default there, and a request that uses tools while
    thinking is on must echo the `reasoning_content` back, or the API
    answers 400.  We therefore send `{"thinking": {"type": "disabled"}}`
    unless the caller asks otherwise, and echo `reasoning_content` whenever
    it comes back.
  * `response_format={"type": "json_object"}` is only accepted when the
    prompt itself mentions JSON; the caller is responsible for that.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


class ApiError(RuntimeError):
    """A non-2xx answer from the API.

    `status` is the HTTP status code, so the caller can tell a transient
    failure (429, 500, 503) from a permanent one (400, 401, 402, 422).
    """

    def __init__(self, status: int, message: str, body: str = ""):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.message = message
        self.body = body


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ChatResult:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    reasoning_content: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw: dict = field(default_factory=dict)


def to_openai_tools(declarations: list[Any]) -> list[dict]:
    """Convert Gemini function declarations into OpenAI tool definitions.

    The Gemini SDK objects expose their JSON schema in `parameters`, which is
    exactly what the OpenAI format wants, so the conversion is mechanical.
    """
    out = []
    for decl in declarations:
        if hasattr(decl, "model_dump"):
            decl = decl.model_dump(exclude_none=True)
        name = decl.get("name")
        params = decl.get("parameters") or {"type": "object", "properties": {}}
        out.append({
            "type": "function",
            "function": {
                "name": name,
                "description": decl.get("description", ""),
                "parameters": params,
            },
        })
    return out


class OpenAICompatibleClient:
    """Minimal client for `POST {base_url}/chat/completions`."""

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com",
                 timeout: int = 180):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------------ --
    def chat(
        self,
        model: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        response_format: dict | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        thinking: bool = False,
        json_mode_hint: str | None = None,
        send_thinking: bool = True,
    ) -> ChatResult:
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        if response_format:
            body["response_format"] = response_format
            if json_mode_hint:
                # DeepSeek only accepts json_object when the prompt mentions
                # JSON; making sure of it here avoids a 400.
                body["messages"] = list(messages)
                body["messages"][-1] = {
                    "role": body["messages"][-1].get("role", "user"),
                    "content": (body["messages"][-1].get("content") or "")
                               + "\n\n" + json_mode_hint,
                }
        if max_tokens:
            body["max_tokens"] = max_tokens
        if temperature is not None:
            body["temperature"] = temperature
        # DeepSeek-specific field; thinking is on by default there.  A relay
        # service in front of a provider that does not know the field may
        # reject the request with a 400, so it can be left out entirely.
        if send_thinking:
            body["thinking"] = {"type": "enabled" if thinking else "disabled"}

        payload = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "petsafe-greenery/1.0",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body_text = ""
            try:
                body_text = exc.read().decode("utf-8", errors="replace")
            except Exception:                            # pragma: no cover
                pass
            raise ApiError(exc.code, _extract_message(body_text) or exc.reason,
                           body_text) from exc
        except urllib.error.URLError as exc:
            raise ApiError(0, f"network error: {exc.reason}") from exc

        data = json.loads(raw)
        choices = data.get("choices") or [{}]
        message = choices[0].get("message") or {}
        usage = data.get("usage") or {}

        calls: list[ToolCall] = []
        for tc in message.get("tool_calls") or []:
            fn = tc.get("function") or {}
            raw_args = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
            except (TypeError, ValueError):
                args = {}
            calls.append(ToolCall(id=tc.get("id", ""), name=fn.get("name", ""),
                                  arguments=args))

        return ChatResult(
            text=message.get("content") or "",
            tool_calls=calls,
            reasoning_content=message.get("reasoning_content") or "",
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            raw=data,
        )


def _extract_message(body_text: str) -> str:
    """Pull the API's own error message out of the response body."""
    if not body_text:
        return ""
    try:
        data = json.loads(body_text)
    except ValueError:
        return body_text[:300]
    err = data.get("error") if isinstance(data, dict) else None
    if isinstance(err, dict):
        return str(err.get("message") or err)[:300]
    if err:
        return str(err)[:300]
    return body_text[:300]
