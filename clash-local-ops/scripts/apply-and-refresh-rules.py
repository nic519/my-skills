#!/usr/bin/env python3
"""写入 node.1024.hair ruleOverwrite，并按需刷新 Clash Party 本地状态。"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

from clash_local_ops_common import (
    build_node1024_put_payload,
    contains_all_keywords,
    fetch_controller_json,
    find_latest_unix_controller,
    find_node1024_profile,
    mask_url,
    merge_rule_overwrite,
    node1024_subscription_url,
    node1024_user_url,
    patch_controller_config,
    put_json_url,
    read_json_url,
    read_rule_file,
    read_text_url,
    run_text,
    summarize_verification_state,
)


def main() -> None:
    """串联远端写入、订阅验证、本地刷新、重启和运行时规则校验。"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("NODE1024_BASE_URL", "https://node.1024.hair"))
    parser.add_argument("--app-root", type=Path, default=Path.home() / "Library/Application Support/mihomo-party")
    parser.add_argument("--uid", default=os.environ.get("NODE1024_UID"))
    parser.add_argument("--token", default=os.environ.get("NODE1024_TOKEN"))
    parser.add_argument("--controller", help="Controller base URL or unix:/path/to.sock; auto-detected when omitted")
    parser.add_argument("--rule", action="append", default=[], help="Rule without leading '- ', repeatable")
    parser.add_argument("--rule-file", type=Path, help="File containing a +rules block or one rule per line")
    parser.add_argument("--apply", action="store_true", help="Actually PUT the merged config; default is dry-run")
    parser.add_argument("--refresh-local", action="store_true", help="Refresh Clash Party profile/work config from generated subscription")
    parser.add_argument("--restart-app", action="store_true", help="Restart Clash Party after refreshing local config")
    parser.add_argument("--app-name", default="Clash Party")
    args = parser.parse_args()

    profile_path = args.app_root / "profile.yaml"
    profile = find_node1024_profile(profile_path.read_text(encoding="utf-8", errors="replace"))
    uid = args.uid or profile["uid"]
    token = args.token or profile["token"]
    rules = collect_rules(args.rule, args.rule_file)
    if not rules:
        raise SystemExit("Provide at least one --rule or --rule-file")

    user_url = node1024_user_url(args.base_url, uid, token)
    response = read_json_url(user_url)
    merged = merge_rule_overwrite(response.get("data", {}).get("ruleOverwrite", ""), rules)
    payload = build_node1024_put_payload(response, merged)

    result: dict[str, object] = {
        "user_url": mask_url(user_url),
        "mode": "apply" if args.apply else "dry-run",
        "profile_id": profile.get("id"),
        "ruleOverwrite": merged,
    }

    current_rule_overwrite = response.get("data", {}).get("ruleOverwrite", "")
    if args.apply:
        put_response = put_json_url(user_url, payload)
        result["response"] = {
            "code": put_response.get("code"),
            "msg": put_response.get("msg"),
        }
        current_rule_overwrite = merged

    subscription_url = node1024_subscription_url(args.base_url, uid, token)
    subscription_text = read_text_url(subscription_url)
    keywords = rule_payload_keywords(rules)
    remote_ok = contains_all_keywords(current_rule_overwrite, keywords)
    subscription_ok = contains_all_keywords(subscription_text, keywords)
    local_ok = False
    runtime_ok = False
    controller = args.controller or current_controller()

    result["subscription_url"] = mask_url(subscription_url)
    result["remote_rule_overwrite_matches"] = remote_ok
    result["subscription_matches"] = subscription_ok

    config_path = args.app_root / "work" / "config.yaml"
    if args.refresh_local:
        if not subscription_ok:
            raise SystemExit("Generated subscription does not contain all requested rules; refusing local refresh")
        result["local_refresh"] = refresh_local_configs(args.app_root, profile, subscription_text)
        local_ok = contains_all_keywords(config_path.read_text(encoding="utf-8", errors="replace"), keywords)
        result["local_config_path"] = str(config_path)
        result["local_config_matches"] = local_ok
        if controller:
            result["reload_status"] = patch_controller_config(controller, config_path, force=True)

    if args.restart_app:
        restart_app(args.app_name)
        controller = wait_for_controller(previous=controller)
        result["controller_after_restart"] = controller

    if controller:
        runtime_rules, runtime_ok = runtime_rule_matches(controller, keywords)
        result["controller"] = controller
        result["runtime_rules"] = runtime_rules
        result["runtime_rules_match"] = runtime_ok

    result["state"] = summarize_verification_state(
        remote_ok=remote_ok,
        subscription_ok=subscription_ok,
        local_ok=local_ok,
        runtime_ok=runtime_ok,
        has_local_check=args.refresh_local,
        has_runtime_check=bool(controller),
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


def collect_rules(raw_rules: list[str], rule_file: Path | None) -> list[str]:
    """汇总命令行传入的规则和规则文件中的规则。"""

    rules = list(raw_rules)
    if rule_file:
        rules.extend(read_rule_file(rule_file))
    return rules


def rule_payload_keywords(rules: list[str]) -> list[str]:
    """提取规则 payload 作为跨远端、订阅、本地和运行时校验的关键词。"""

    keywords = []
    for rule in rules:
        parts = [part.strip() for part in rule.split(",")]
        keywords.append(parts[1].lower() if len(parts) >= 2 else rule.lower())
    return keywords


def refresh_local_configs(app_root: Path, profile: dict[str, str], subscription_text: str) -> dict[str, object]:
    """用生成订阅覆盖 Clash Party profile 和 work 配置，并先备份旧文件。"""

    if "rules:" not in subscription_text:
        raise ValueError("Generated subscription does not look like a Clash config")
    profile_id = profile.get("id")
    if not profile_id:
        raise ValueError("Current profile id is required for local refresh")
    targets = [
        app_root / "profiles" / f"{profile_id}.yaml",
        app_root / "work" / "config.yaml",
    ]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backups = []
    updated = []
    for target in targets:
        if target.exists():
            backup = target.with_name(f"{target.name}.bak-{stamp}")
            shutil.copy2(target, backup)
            backups.append(str(backup))
        tmp = target.with_name(f"{target.name}.tmp-{stamp}")
        tmp.write_text(subscription_text, encoding="utf-8")
        os.replace(tmp, target)
        updated.append(str(target))
    return {"updated": updated, "backups": backups}


def current_controller() -> str | None:
    """从当前进程列表自动探测 Mihomo unix controller。"""

    return find_latest_unix_controller(run_text(["ps", "aux"]))


def wait_for_controller(previous: str | None, timeout: int = 20) -> str | None:
    """重启应用后等待新的 Mihomo controller 出现，超时则返回最后候选。"""

    deadline = time.time() + timeout
    latest = current_controller()
    while time.time() < deadline:
        latest = current_controller()
        if latest and latest != previous:
            return latest
        time.sleep(1)
    return latest


def runtime_rule_matches(controller: str, keywords: list[str]) -> tuple[list[dict[str, object]], bool]:
    """在当前 Mihomo /rules 中查找目标 payload，并判断关键词是否全部命中。"""

    rules = fetch_controller_json(controller, "/rules")
    matched_rules = []
    matched_payloads = []
    for rule in rules.get("rules", []):
        payload = str(rule.get("payload") or "")
        if any(keyword in payload.lower() for keyword in keywords):
            matched_payloads.append(payload)
            matched_rules.append(
                {
                    "type": rule.get("type"),
                    "payload": rule.get("payload"),
                    "proxy": rule.get("proxy"),
                }
            )
    return matched_rules, contains_all_keywords("\n".join(matched_payloads), keywords)


def restart_app(app_name: str) -> None:
    """通过 AppleScript 退出并重新打开 Clash Party 等 macOS 应用。"""

    subprocess.run(["osascript", "-e", f'tell application "{app_name}" to quit'], check=False)
    time.sleep(3)
    subprocess.run(["open", "-a", app_name], check=True)
    time.sleep(3)


if __name__ == "__main__":
    main()
