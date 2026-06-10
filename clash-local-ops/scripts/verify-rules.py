#!/usr/bin/env python3
"""Verify node.1024.hair ruleOverwrite propagation and local Mihomo rules."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from clash_local_ops_common import (
    fetch_controller_json,
    mask_url,
    node1024_subscription_url,
    node1024_user_url,
    patch_controller_config,
    read_json_url,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("NODE1024_BASE_URL", "https://node.1024.hair"))
    parser.add_argument("--uid", default=os.environ.get("NODE1024_UID"))
    parser.add_argument("--token", default=os.environ.get("NODE1024_TOKEN"))
    parser.add_argument("--controller", help="Controller base URL or unix:/path/to.sock")
    parser.add_argument("--config-path", type=Path, help="Local config path for optional reload and file checks")
    parser.add_argument("--keyword", action="append", default=[], help="Expected payload keyword, repeatable")
    parser.add_argument("--reload", action="store_true", help="PATCH /configs with --config-path before checking /rules")
    args = parser.parse_args()

    if not args.uid or not args.token:
        raise SystemExit("Provide --uid/--token or NODE1024_UID/NODE1024_TOKEN")
    keywords = [item.lower() for item in args.keyword]

    user_url = node1024_user_url(args.base_url, args.uid, args.token)
    subscription_url = node1024_subscription_url(args.base_url, args.uid, args.token)
    user_response = read_json_url(user_url)
    rule_overwrite = user_response.get("data", {}).get("ruleOverwrite", "")
    subscription_text = read_text_url(subscription_url)

    result: dict[str, object] = {
        "user_url": mask_url(user_url),
        "subscription_url": mask_url(subscription_url),
        "remote_rule_overwrite_matches": contains_all(rule_overwrite, keywords),
        "subscription_matches": contains_all(subscription_text, keywords),
    }

    if args.config_path:
        local_text = args.config_path.read_text(encoding="utf-8", errors="replace") if args.config_path.exists() else ""
        result["local_config_path"] = str(args.config_path)
        result["local_config_matches"] = contains_all(local_text, keywords)

    if args.controller:
        if args.reload:
            if not args.config_path:
                raise SystemExit("--reload requires --config-path")
            result["reload_status"] = patch_controller_config(args.controller, args.config_path)
        rules = fetch_controller_json(args.controller, "/rules")
        matched_rules = []
        for rule in rules.get("rules", []):
            payload = str(rule.get("payload") or "")
            if not keywords or any(keyword in payload.lower() for keyword in keywords):
                matched_rules.append(
                    {
                        "type": rule.get("type"),
                        "payload": rule.get("payload"),
                        "proxy": rule.get("proxy"),
                    }
                )
        result["runtime_rules"] = matched_rules
        result["runtime_rules_match"] = bool(matched_rules) if keywords else True

    print(json.dumps(result, ensure_ascii=False, indent=2))


def contains_all(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return all(keyword in lowered for keyword in keywords)


def read_text_url(url: str, timeout: int = 30) -> str:
    import urllib.request

    request = urllib.request.Request(url, headers={"User-Agent": "clash-local-ops/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


if __name__ == "__main__":
    main()
