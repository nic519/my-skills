#!/usr/bin/env python3
"""Clash Party profile.yaml 的轻量解析逻辑。"""

from __future__ import annotations

import re
import urllib.parse


def find_node1024_profile(profile_yaml_text: str) -> dict[str, str]:
    """从 Clash Party profile.yaml 中找到当前或首个 node.1024.hair profile。"""

    current = find_yaml_scalar(profile_yaml_text, "current")
    item = find_profile_item_by_id(profile_yaml_text, current) if current else None
    if not item or "node.1024.hair" not in item.get("url", ""):
        item = find_first_node1024_profile_item(profile_yaml_text)
    if not item:
        raise ValueError("No node.1024.hair profile found")

    url = item.get("url", "")
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qs(parsed.query)
    uid = query.get("uid", [""])[0]
    token = query.get("token", [""])[0]
    if not uid or not token:
        raise ValueError("node.1024.hair profile URL is missing uid or token")

    return {
        "id": item.get("id", ""),
        "name": item.get("name", ""),
        "type": item.get("type", ""),
        "subscription_url": url,
        "uid": uid,
        "token": token,
    }


def find_yaml_scalar(text: str, key: str) -> str | None:
    """从简单 YAML 文本里提取顶层标量字段，供 profile.yaml 轻量解析使用。"""

    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def find_profile_item_by_id(text: str, profile_id: str | None) -> dict[str, str] | None:
    """按 profile id 从 Clash Party profile.yaml 的 items 列表里提取条目字段。"""

    if not profile_id:
        return None
    current_item: dict[str, str] | None = None
    for line in text.splitlines():
        id_match = re.match(r"\s*-\s+id:\s*(.+)", line)
        if id_match:
            if current_item and current_item.get("id") == profile_id:
                return current_item
            current_item = {"id": id_match.group(1).strip()}
            continue
        if current_item is None:
            continue
        field_match = re.match(r"\s{4}([A-Za-z][A-Za-z0-9_-]*):\s*(.*)", line)
        if field_match:
            current_item[field_match.group(1)] = field_match.group(2).strip()
    if current_item and current_item.get("id") == profile_id:
        return current_item
    return None


def find_first_node1024_profile_item(text: str) -> dict[str, str] | None:
    """找出第一个 URL 指向 node.1024.hair 的 profile 条目。"""

    current_item: dict[str, str] | None = None
    for line in text.splitlines():
        id_match = re.match(r"\s*-\s+id:\s*(.+)", line)
        if id_match:
            if current_item and "node.1024.hair" in current_item.get("url", ""):
                return current_item
            current_item = {"id": id_match.group(1).strip()}
            continue
        if current_item is None:
            continue
        field_match = re.match(r"\s{4}([A-Za-z][A-Za-z0-9_-]*):\s*(.*)", line)
        if field_match:
            current_item[field_match.group(1)] = field_match.group(2).strip()
    if current_item and "node.1024.hair" in current_item.get("url", ""):
        return current_item
    return None
