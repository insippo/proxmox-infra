#!/usr/bin/env python3
"""Query a Dify app (chat or workflow) from the command line.

Uses only the Python standard library so it runs on any host that can reach the
Dify instance -- a workstation, a Proxmox VM, or a cron job.

Environment variables:
  DIFY_API_BASE   Base URL of the Dify API, e.g. https://dify.example.ee/v1
  DIFY_API_KEY    App API key (starts with "app-")
  DIFY_USER       Optional end-user identifier reported to Dify (default: cli)

Examples:
  ./dify-query.py "Leia Erik Salumi kiri ja tema aadress indeksiga"
  ./dify-query.py --mode workflow --input question="300l puhver" --input mailbox=arved
  ./dify-query.py --json "viimased arved" > vastus.json
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def parse_args():
    parser = argparse.ArgumentParser(
        description="Send a query to a Dify app and print the answer.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("query", nargs="?", help="Question to send (chat mode)")
    parser.add_argument(
        "--mode",
        choices=("chat", "workflow"),
        default="chat",
        help="chat -> /chat-messages, workflow -> /workflows/run (default: chat)",
    )
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Workflow input variable; repeat for several",
    )
    parser.add_argument("--base", default=os.environ.get("DIFY_API_BASE"))
    parser.add_argument("--key", default=os.environ.get("DIFY_API_KEY"))
    parser.add_argument("--user", default=os.environ.get("DIFY_USER", "cli"))
    parser.add_argument("--conversation-id", default="")
    parser.add_argument("--timeout", type=int, default=120, help="Seconds (default: 120)")
    parser.add_argument("--json", action="store_true", help="Print the raw response")
    return parser.parse_args()


def build_payload(args):
    inputs = {}
    for item in args.input:
        if "=" not in item:
            sys.exit(f"error: --input expects KEY=VALUE, got {item!r}")
        key, value = item.split("=", 1)
        inputs[key] = value

    if args.mode == "workflow":
        return "/workflows/run", {
            "inputs": inputs,
            "response_mode": "blocking",
            "user": args.user,
        }

    if not args.query:
        sys.exit("error: a query is required in chat mode")
    payload = {
        "inputs": inputs,
        "query": args.query,
        "response_mode": "blocking",
        "user": args.user,
    }
    if args.conversation_id:
        payload["conversation_id"] = args.conversation_id
    return "/chat-messages", payload


def call_dify(base, key, path, payload, timeout):
    request = urllib.request.Request(
        base.rstrip("/") + path,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def extract_answer(data):
    if "answer" in data:
        return data["answer"]
    outputs = data.get("data", {}).get("outputs")
    if isinstance(outputs, dict):
        if len(outputs) == 1:
            return next(iter(outputs.values()))
        return json.dumps(outputs, ensure_ascii=False, indent=2)
    return json.dumps(data, ensure_ascii=False, indent=2)


def main():
    args = parse_args()
    if not args.base or not args.key:
        sys.exit("error: set DIFY_API_BASE and DIFY_API_KEY (or pass --base/--key)")

    path, payload = build_payload(args)

    try:
        data = call_dify(args.base, args.key, path, payload, args.timeout)
    except urllib.error.HTTPError as err:
        body = err.read().decode(errors="replace").strip()
        hints = {
            401: "check DIFY_API_KEY -- it must be the app key, not a workspace token",
            404: "check DIFY_API_BASE (it usually ends with /v1) and the app mode",
            403: "the request was refused; from a sandboxed session this is often an "
            "egress policy denial rather than Dify itself",
        }
        hint = hints.get(err.code)
        sys.exit(f"HTTP {err.code}: {body}" + (f"\nhint: {hint}" if hint else ""))
    except urllib.error.URLError as err:
        sys.exit(f"error: cannot reach {args.base}: {err.reason}")

    print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else extract_answer(data))


if __name__ == "__main__":
    main()
