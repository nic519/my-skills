#!/usr/bin/env python3
"""校验 node.1024.hair ruleOverwrite、生成订阅和本地 Mihomo 规则是否一致。"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from clash_local_ops_common import (
    contains_all_keywords,
    fetch_controller_json,
    mask_url,
    node1024_subscription_url,
    node1024_user_url,
    patch_controller_config,
    read_json_url,
    read_text_url,
    summarize_verification_state,
)


def main() -> None:
    """执行远端、订阅、本地文件和运行时规则的分层校验并输出 JSON。"""

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

    remote_ok = contains_all_keywords(rule_overwrite, keywords)
    subscription_ok = contains_all_keywords(subscription_text, keywords)
    local_ok = False
    runtime_ok = False

    result: dict[str, object] = {
        "user_url": mask_url(user_url),
        "subscription_url": mask_url(subscription_url),
        "remote_rule_overwrite_matches": remote_ok,
        "subscription_matches": subscription_ok,
    }

    if args.config_path:
        local_text = args.config_path.read_text(encoding="utf-8", errors="replace") if args.config_path.exists() else ""
        local_ok = contains_all_keywords(local_text, keywords)
        result["local_config_path"] = str(args.config_path)
        result["local_config_matches"] = local_ok

    if args.controller:
        if args.reload:
            if not args.config_path:
                raise SystemExit("--reload requires --config-path")
            result["reload_status"] = patch_controller_config(args.controller, args.config_path)
        rules = fetch_controller_json(args.controller, "/rules")
        matched_rules = []
        matched_payload_text = []
        for rule in rules.get("rules", []):
            payload = str(rule.get("payload") or "")
            if not keywords or any(keyword in payload.lower() for keyword in keywords):
                matched_payload_text.append(payload)
                matched_rules.append(
                    {
                        "type": rule.get("type"),
                        "payload": rule.get("payload"),
                        "proxy": rule.get("proxy"),
                    }
                )
        result["runtime_rules"] = matched_rules
        runtime_ok = contains_all_keywords("\n".join(matched_payload_text), keywords)
        result["runtime_rules_match"] = runtime_ok

    result["state"] = summarize_verification_state(
        remote_ok=remote_ok,
        subscription_ok=subscription_ok,
        local_ok=local_ok,
        runtime_ok=runtime_ok,
        has_local_check=bool(args.config_path),
        has_runtime_check=bool(args.controller),
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
