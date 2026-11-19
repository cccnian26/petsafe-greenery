#!/usr/bin/env python3
"""
End-to-end test of the DeepSeek (OpenAI-compatible) code path.

    python scripts/test_deepseek_path.py

A local HTTP server speaks the DeepSeek / OpenAI chat-completions protocol,
so the real client, the real tool dispatch and the real agent loop are
exercised -- without an API key and without spending anything.

What it checks:
  1. the pre-flight probe works;
  2. the tool declaration is converted to the OpenAI format;
  3. the tool result comes back as a role="tool" message with a tool_call_id;
  4. thinking is switched off (DeepSeek rejects tool calls in thinking mode
     unless the reasoning content is echoed back);
  5. the design that comes out has zones, care instructions and cautions;
  6. the evaluator can score that design.
"""
from __future__ import annotations

import json
import os
import uuid
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

STATE: dict = {"calls": 0, "requests": [], "reject_thinking": True,
               "rejected_tools": False}


def _make_design():
    from src.db import get_database
    from src.offline import _design
    from src.tools import query_pet_safe_plants
    res = query_pet_safe_plants(pets=["cat"], light="partial_shade",
                                moisture="moderate", limit=8)
    return _design(res["candidates"], "partial_shade/moderate/cat")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):        # keep the test output clean
        pass

    def do_POST(self):                   # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        STATE["calls"] += 1
        STATE["requests"].append(body)

        # Scenario: a relay that does not know the DeepSeek-specific
        # 'thinking' field rejects the first request with a 400.  The client
        # must retry without it instead of killing the whole run.
        _first_seeing_thinking = body.get("thinking")
        if (STATE.get("reject_thinking") and _first_seeing_thinking
                and (not body.get("tools") or not STATE.get("rejected_tools"))):
            err = {"error": {"message": "Unsupported parameter: 'thinking'",
                             "type": "invalid_request_error"}}
            raw = json.dumps(err).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            if body.get("tools"):
                STATE["rejected_tools"] = True
            return

        has_tool_result = any(m.get("role") == "tool" for m in body["messages"])
        if body.get("tools") and not has_tool_result:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "query_pet_safe_plants",
                        "arguments": json.dumps({
                            "pets": ["cat"], "light": "partial_shade",
                            "moisture": "moderate", "limit": 6}),
                    },
                }],
            }
        else:
            message = {"role": "assistant",
                       "content": json.dumps(_make_design(), ensure_ascii=False)}

        out = {"id": "x", "object": "chat.completion", "created": 0,
               "model": body.get("model", "deepseek-flash"),
               "choices": [{"index": 0, "finish_reason": "stop",
                            "message": message}],
               "usage": {"prompt_tokens": 500, "completion_tokens": 900,
                         "total_tokens": 1400}}
        data = json.dumps(out).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> int:
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    os.environ["DEEPSEEK_API_KEY"] = "sk-test-0123456789"
    os.environ["DEEPSEEK_BASE_URL"] = f"http://127.0.0.1:{port}"
    os.environ["PETSAFE_BACKEND"] = "deepseek"

    from src.llm import LLM
    from src.tools import ALL_TOOLS, TOOL_DISPATCH
    from src.evaluate import evaluate_design
    from src.db import get_database

    llm = LLM(backend="deepseek")
    checks = [
        ("the provider is DeepSeek", llm.provider == "deepseek"),
        # The model may be overridden with DEEPSEEK_MODEL (a relay service
        # may serve its own names), so the test checks the model that is
        # actually in use, not a hard-coded one.
        ("the configured model is the one in use",
         llm.model == (os.environ.get("DEEPSEEK_MODEL")
                       or os.environ.get("PETSAFE_MODEL")
                       or "deepseek-flash")),
    ]

    ok, reason = llm.ping()
    checks.append(("the pre-flight probe answers", ok and reason == "ok"))

    turn = llm.tool_loop(
        # A unique prompt per run: otherwise the disk cache answers the
        # request and the test never inspects a real request body.
        prompt=f"Design a cat-safe balcony for a half-shaded site. "
               f"(test run {uuid.uuid4().hex[:10]})",
        system_instruction="You are a planting designer.",
        tools=ALL_TOOLS, dispatch=TOOL_DISPATCH, max_rounds=3, tag="ds_test")
    checks.append(("the model called the tool", turn["n_calls"] == 1))
    checks.append(("the transcript names the tool",
                   turn["transcript"][0]["tool"] == "query_pet_safe_plants"))
    checks.append(("the tool returned candidates",
                   len(turn["transcript"][0]["result"].get("candidates", [])) > 0))

    tool_req = next((r for r in STATE["requests"] if r.get("tools")), {})
    checks.append(("the run survived a provider that rejects 'thinking'",
                   any("thinking" not in r for r in STATE["requests"])))
    checks.append(("the tool was declared in the OpenAI format",
                   bool(tool_req) and tool_req["tools"][0]["type"] == "function"
                   and tool_req["tools"][0]["function"]["name"]
                   == "query_pet_safe_plants"))
    checks.append(("thinking was switched off",
                   bool(tool_req) and tool_req.get("thinking") == {"type": "disabled"}))
    last = STATE["requests"][-1]
    tool_msgs = [m for m in last["messages"] if m.get("role") == "tool"]
    checks.append(("the tool result came back as a tool message",
                   len(tool_msgs) == 1 and bool(tool_msgs[0].get("tool_call_id"))))

    design = json.loads(turn["text"])
    checks.append(("the design has zones", len(design.get("zones", [])) >= 2))
    checks.append(("the design has combination logic",
                   bool(design.get("layout_strategy")) and bool(design.get("combination_logic"))))
    checks.append(("the design has care instructions",
                   bool(design.get("care_instructions"))))
    checks.append(("the design has care cautions",
                   bool(design.get("care_cautions"))))

    metrics = evaluate_design(design, {"id": "t", "pets": ["cat"],
                                       "light": "partial_shade",
                                       "moisture": "moderate"},
                               get_database())
    checks.append(("the evaluator scored the design",
                   metrics["n_recommended"] > 0))

    print("=" * 70)
    print("DEEPSEEK PATH TEST -- real client, mocked HTTP server, no key needed")
    print("=" * 70)
    for name, ok_ in checks:
        print(f"  [{'PASS' if ok_ else 'FAIL'}] {name}")
    print(f"\n  HTTP requests: {STATE['calls']}")
    failed = [n for n, ok_ in checks if not ok_]
    print()
    if failed:
        print("FAILED:", failed)
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
