#!/usr/bin/env python3
"""跨远端、订阅、本地文件和运行时规则的校验状态归纳。"""

from __future__ import annotations


def summarize_verification_state(
    *,
    remote_ok: bool,
    subscription_ok: bool,
    local_ok: bool,
    runtime_ok: bool,
    has_local_check: bool,
    has_runtime_check: bool,
) -> dict[str, str | None]:
    """把远端、订阅、本地文件和运行时规则四层校验归纳成下一步状态。"""

    if not remote_ok:
        return {"status": "remote_stale", "recommended_next_action": "apply_rule_overwrite"}
    if not subscription_ok:
        return {"status": "subscription_stale", "recommended_next_action": "check_node1024_subscription_generation"}
    if has_local_check and not local_ok:
        return {"status": "local_stale", "recommended_next_action": "refresh_local_config"}
    if has_runtime_check and not runtime_ok:
        return {"status": "runtime_stale", "recommended_next_action": "restart_clash_party"}
    if has_local_check and has_runtime_check:
        return {"status": "ready", "recommended_next_action": None}
    return {"status": "remote_ready", "recommended_next_action": "refresh_local_config"}


def contains_all_keywords(text: str, keywords: list[str]) -> bool:
    """判断文本是否包含所有关键词，关键词应由调用方按业务粒度准备。"""

    lowered = text.lower()
    return all(keyword in lowered for keyword in keywords)
