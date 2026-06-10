#!/usr/bin/env python3
"""Merge ruleOverwrite rules into node.1024.hair user config."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from clash_local_ops_common import (
    build_node1024_put_payload,
    mask_url,
    merge_rule_overwrite,
    node1024_user_url,
    put_json_url,
    read_json_url,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("NODE1024_BASE_URL", "https://node.1024.hair"))
    parser.add_argument("--uid", default=os.environ.get("NODE1024_UID"))
    parser.add_argument("--token", default=os.environ.get("NODE1024_TOKEN"))
    parser.add_argument("--rule", action="append", default=[], help="Rule without leading '- ', repeatable")
    parser.add_argument("--rule-file", type=Path, help="File containing a +rules block or one rule per line")
    parser.add_argument("--apply", action="store_true", help="Actually PUT the merged config; default is dry-run")
    args = parser.parse_args()

    if not args.uid or not args.token:
        raise SystemExit("Provide --uid/--token or NODE1024_UID/NODE1024_TOKEN")

    new_rules = list(args.rule)
    if args.rule_file:
        new_rules.extend(read_rules(args.rule_file))
    if not new_rules:
        raise SystemExit("Provide at least one --rule or --rule-file")

    url = node1024_user_url(args.base_url, args.uid, args.token)
    response = read_json_url(url)
    current = response.get("data", {}).get("ruleOverwrite", "")
    merged = merge_rule_overwrite(current, new_rules)
    payload = build_node1024_put_payload(response, merged)

    summary = {
        "url": mask_url(url),
        "mode": "apply" if args.apply else "dry-run",
        "ruleOverwrite": merged,
    }

    if args.apply:
        put_response = put_json_url(url, payload)
        summary["response"] = {
            "code": put_response.get("code"),
            "msg": put_response.get("msg"),
            "ruleOverwrite": put_response.get("data", {}).get("ruleOverwrite"),
        }

    print(json.dumps(summary, ensure_ascii=False, indent=2))


def read_rules(path: Path) -> list[str]:
    rules: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line in {"+rules:", "rules:"}:
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        rules.append(line)
    return rules


if __name__ == "__main__":
    main()
