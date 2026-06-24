#!/usr/bin/env python3
"""校验 node.1024.hair ruleOverwrite、生成订阅和本地 Mihomo 规则是否一致。"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from http_helpers import mask_url, read_json_url, read_text_url
from mihomo_runtime import fetch_controller_json, patch_controller_config
from node1024_config import node1024_subscription_url, node1024_user_url
from verification_state import contains_all_keywords, summarize_verification_state


def main() -> None:
    """解析参数、执行校验并打印 JSON 结果。"""

    args = parse_args()
    print(json.dumps(run_verification(args), ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    """解析 verify-rules 的命令行参数。"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("NODE1024_BASE_URL", "https://node.1024.hair"))
    parser.add_argument("--uid", default=os.environ.get("NODE1024_UID"))
    parser.add_argument("--token", default=os.environ.get("NODE1024_TOKEN"))
    parser.add_argument("--controller", help="Controller base URL or unix:/path/to.sock")
    parser.add_argument("--config-path", type=Path, help="Local config path for optional reload and file checks")
    parser.add_argument("--keyword", action="append", default=[], help="Expected payload keyword, repeatable")
    parser.add_argument("--reload", action="store_true", help="PATCH /configs with --config-path before checking /rules")
    return parser.parse_args()


def run_verification(args: argparse.Namespace) -> dict[str, object]:
    """执行远端、订阅、本地文件和运行时规则的分层校验。"""

    if not args.uid or not args.token:
        raise SystemExit("Provide --uid/--token or NODE1024_UID/NODE1024_TOKEN")
    keywords = [item.lower() for item in args.keyword]

    user_url = node1024_user_url(args.base_url, args.uid, args.token)
    subscription_url = node1024_subscription_url(args.base_url, args.uid, args.token)
    user_response = read_json_url(user_url)
    rule_overwrite = user_response.get("data", {}).get("ruleOverwrite", "")
    subscription_text = read_text_url(subscription_url)

    local_text = None
    if args.config_path:
        local_text = args.config_path.read_text(encoding="utf-8", errors="replace") if args.config_path.exists() else ""

    runtime_rules_payload = None
    reload_status = None
    if args.controller:
        if args.reload:
            if not args.config_path:
                raise SystemExit("--reload requires --config-path")
            reload_status = patch_controller_config(args.controller, args.config_path)
        runtime_rules_payload = fetch_controller_json(args.controller, "/rules")

    result = build_verification_result(
        user_url=user_url,
        subscription_url=subscription_url,
        rule_overwrite=rule_overwrite,
        subscription_text=subscription_text,
        keywords=keywords,
        local_text=local_text,
        local_config_path=args.config_path,
        runtime_rules_payload=runtime_rules_payload,
        reload_status=reload_status,
    )
    return result


def build_verification_result(
    *,
    user_url: str,
    subscription_url: str,
    rule_overwrite: str,
    subscription_text: str,
    keywords: list[str],
    local_text: str | None = None,
    local_config_path: Path | None = None,
    runtime_rules_payload: dict[str, object] | None = None,
    reload_status: int | None = None,
) -> dict[str, object]:
    """组装 verify-rules 输出结果，不执行网络、文件或 controller 操作。"""

    remote_ok = contains_all_keywords(rule_overwrite, keywords)
    subscription_ok = contains_all_keywords(subscription_text, keywords)
    local_ok = contains_all_keywords(local_text or "", keywords) if local_text is not None else False
    matched_rules, runtime_ok = summarize_runtime_rules(runtime_rules_payload, keywords)

    result: dict[str, object] = {
        "user_url": mask_url(user_url),
        "subscription_url": mask_url(subscription_url),
        "remote_rule_overwrite_matches": remote_ok,
        "subscription_matches": subscription_ok,
    }
    if local_config_path is not None:
        result["local_config_path"] = str(local_config_path)
        result["local_config_matches"] = local_ok
    if reload_status is not None:
        result["reload_status"] = reload_status
    if runtime_rules_payload is not None:
        result["runtime_rules"] = matched_rules
        result["runtime_rules_match"] = runtime_ok
    result["state"] = summarize_verification_state(
        remote_ok=remote_ok,
        subscription_ok=subscription_ok,
        local_ok=local_ok,
        runtime_ok=runtime_ok,
        has_local_check=local_text is not None,
        has_runtime_check=runtime_rules_payload is not None,
    )
    return result


def summarize_runtime_rules(
    runtime_rules_payload: dict[str, object] | None,
    keywords: list[str],
) -> tuple[list[dict[str, object]], bool]:
    """从 /rules 响应里筛选目标规则，并返回匹配摘要和全关键词命中状态。"""

    if runtime_rules_payload is None:
        return [], False
    matched_rules = []
    matched_payload_text = []
    for rule in runtime_rules_payload.get("rules", []):
        if not isinstance(rule, dict):
            continue
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
    return matched_rules, contains_all_keywords("\n".join(matched_payload_text), keywords)


if __name__ == "__main__":
    main()
