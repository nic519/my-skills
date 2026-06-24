#!/usr/bin/env python3
"""HTTP 读写和敏感 URL 展示辅助函数。"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


SENSITIVE_QUERY_KEYS = {"token", "access_token", "key", "owO", "owo"}


def read_json_url(url: str, timeout: int = 30) -> dict[str, Any]:
    """读取 JSON URL，并在 HTTP 错误里使用脱敏后的地址。"""

    request = urllib.request.Request(url, headers={"User-Agent": "clash-local-ops/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GET {mask_url(url)} failed: HTTP {error.code}: {body}") from error


def read_text_url(url: str, timeout: int = 30) -> str:
    """读取文本 URL，主要用于获取生成后的 Clash 订阅配置。"""

    request = urllib.request.Request(url, headers={"User-Agent": "clash-local-ops/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def put_json_url(url: str, payload: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
    """向 JSON URL 发起 PUT，并在失败信息中隐藏敏感查询参数。"""

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="PUT",
        headers={"Content-Type": "application/json", "User-Agent": "clash-local-ops/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"PUT {mask_url(url)} failed: HTTP {error.code}: {body}") from error


def mask_url(url: str) -> str:
    """遮蔽 URL 查询参数里的 token/key 等敏感字段，保留排查所需上下文。"""

    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    masked = []
    for key, value in query:
        if key.lower() in SENSITIVE_QUERY_KEYS:
            masked.append((key, mask_secret(value)))
        else:
            masked.append((key, value))
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(masked, safe="*"), parsed.fragment)
    )


def mask_secret(value: str) -> str:
    """用短占位符隐藏密钥内容，只在较长密钥上保留首尾少量字符。"""

    if len(value) <= 4:
        return "***"
    return f"{value[:3]}***{value[-2:]}"
