#!/usr/bin/env python3
"""Clash/Mihomo controller、连接证据和运行时进程辅助函数。"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from http_helpers import read_json_url


def collect_matching_connections(payload: dict[str, Any], keywords: list[str]) -> list[dict[str, Any]]:
    """按关键词筛选 Mihomo connections，并输出域名、规则和链路摘要。"""

    patterns = [keyword.lower() for keyword in keywords if keyword.strip()]
    rows: list[dict[str, Any]] = []
    for item in payload.get("connections", []):
        metadata = item.get("metadata") or {}
        host = str(metadata.get("host") or metadata.get("sniffHost") or "")
        haystack = " ".join(
            [
                host,
                str(metadata.get("process") or ""),
                str(metadata.get("processPath") or ""),
                " ".join(str(part) for part in item.get("chains", [])),
                str(item.get("rule") or ""),
                str(item.get("rulePayload") or ""),
            ]
        ).lower()
        if patterns and not any(pattern in haystack for pattern in patterns):
            continue
        chains = [str(part) for part in item.get("chains", [])]
        rows.append(
            {
                "start": item.get("start"),
                "host": host,
                "type": metadata.get("type"),
                "inboundPort": metadata.get("inboundPort"),
                "rule": item.get("rule"),
                "rulePayload": item.get("rulePayload"),
                "chain": " > ".join(chains),
                "upload": item.get("upload"),
                "download": item.get("download"),
            }
        )
    return rows


def fetch_controller_json(controller: str, endpoint: str, timeout: int = 15) -> dict[str, Any]:
    """从 HTTP 或 unix socket 形式的 Clash/Mihomo controller 读取 JSON。"""

    if controller.startswith("unix:"):
        socket_path = controller.removeprefix("unix:")
        output = subprocess.check_output(
            [
                "curl",
                "--silent",
                "--show-error",
                "--max-time",
                str(timeout),
                "--unix-socket",
                socket_path,
                f"http://127.0.0.1/{endpoint.lstrip('/')}",
            ],
            text=True,
        )
        return json.loads(output)

    base = controller.rstrip("/")
    return read_json_url(f"{base}/{endpoint.lstrip('/')}", timeout=timeout)


def patch_controller_config(controller: str, config_path: Path, timeout: int = 15, force: bool = False) -> int:
    """通过 Mihomo controller 重新加载本地配置文件，并返回 HTTP 状态码。"""

    payload = json.dumps({"path": str(config_path)}, ensure_ascii=False)
    if controller.startswith("unix:"):
        socket_path = controller.removeprefix("unix:")
        url = "http://127.0.0.1/configs?force=true" if force else "http://127.0.0.1/configs"
        result = subprocess.run(
            [
                "curl",
                "--silent",
                "--show-error",
                "--max-time",
                str(timeout),
                "--unix-socket",
                socket_path,
                "-X",
                "PATCH",
                url,
                "-H",
                "Content-Type: application/json",
                "--data",
                payload,
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
            ],
            check=False,
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
        return int(result.stdout.strip() or "0")
    raise ValueError("HTTP controller reload is not implemented by this helper")


def find_latest_unix_controller(process_text: str) -> str | None:
    """从 ps 输出中返回最后一个活动 Mihomo unix controller。"""

    controller: str | None = None
    for line in process_text.splitlines():
        if not is_runtime_process_line(line):
            continue
        socket_match = re.search(r"-ext-ctl-unix\s+(\S+)", line)
        if socket_match:
            controller = f"unix:{socket_match.group(1)}"
    return controller


def is_runtime_process_line(line: str) -> bool:
    """判断 ps 行是否像真实 Clash/Mihomo 运行时进程，并排除本工具自身。"""

    lowered = line.lower()
    if "clash-local-ops/scripts/" in lowered:
        return False
    if " rg " in lowered or lowered.endswith(" rg"):
        return False
    return any(
        marker in lowered
        for marker in [
            "/mihomo",
            "sidecar/mihomo",
            "clash party.app",
            "clash-core-service",
            "clashverge.helper",
            "party.mihomo.helper",
        ]
    )
