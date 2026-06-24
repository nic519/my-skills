#!/usr/bin/env python3
"""node.1024.hair 配置地址和写回 payload 逻辑。"""

from __future__ import annotations

import urllib.parse
from copy import deepcopy
from typing import Any


def build_node1024_put_payload(response: dict[str, Any], rule_overwrite: str) -> dict[str, Any]:
    """构造 node.1024.hair PUT payload，只替换 ruleOverwrite 并保留其它配置字段。"""

    data = response.get("data")
    if not isinstance(data, dict):
        raise ValueError("GET response does not contain a data object")
    if not isinstance(data.get("accessToken"), str) or not data["accessToken"]:
        raise ValueError("GET response data.accessToken is required for PUT")

    config = deepcopy(data)
    config["ruleOverwrite"] = rule_overwrite
    return {"config": config}


def node1024_user_url(base_url: str, uid: str, token: str) -> str:
    """根据 uid/token 构造 node.1024.hair 用户配置 API 地址。"""

    query = urllib.parse.urlencode({"uid": uid, "token": token})
    return f"{base_url.rstrip('/')}/api/user?{query}"


def node1024_subscription_url(base_url: str, uid: str, token: str) -> str:
    """根据 uid/token 构造 node.1024.hair 生成订阅地址。"""

    query = urllib.parse.urlencode({"uid": uid, "token": token})
    return f"{base_url.rstrip('/')}/api/x?{query}"
