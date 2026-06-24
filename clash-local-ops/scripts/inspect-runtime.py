#!/usr/bin/env python3
"""检查本机 Clash/Mihomo 运行时状态，并避免输出敏感信息。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from clash_local_ops_common import find_profile_item, find_scalar, is_runtime_process_line, mask_url, run_text


def main() -> None:
    """收集系统代理、Mihomo 进程和 Clash Party profile 摘要并输出 JSON。"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-root", type=Path, default=Path.home() / "Library/Application Support/mihomo-party")
    args = parser.parse_args()

    process_text = run_text(["ps", "aux"])
    runtime = {
        "system_proxy": read_system_proxy(),
        "mihomo_processes": find_mihomo_processes(process_text),
        "mihomo_party": inspect_mihomo_party(args.app_root),
    }
    print(json.dumps(runtime, ensure_ascii=False, indent=2))


def read_system_proxy() -> dict[str, object]:
    """读取 macOS 系统代理设置，用于判断请求是否可能进入本机代理。"""

    text = run_text(["scutil", "--proxy"], allow_failure=True)
    if not text:
        return {"available": False}
    result: dict[str, object] = {"available": True}
    for key in ["HTTPEnable", "HTTPProxy", "HTTPPort", "HTTPSEnable", "HTTPSProxy", "HTTPSPort", "SOCKSEnable", "SOCKSProxy", "SOCKSPort"]:
        match = re.search(rf"\b{re.escape(key)}\s*:\s*(.+)", text)
        if match:
            value = match.group(1).strip()
            result[key] = int(value) if value.isdigit() else value
    return result


def find_mihomo_processes(process_text: str) -> list[dict[str, object]]:
    """从 ps 输出中筛选 Mihomo/Clash 运行时进程和 unix controller。"""

    rows = []
    for line in process_text.splitlines():
        if not is_runtime_process_line(line):
            continue
        socket_match = re.search(r"-ext-ctl-unix\s+(\S+)", line)
        rows.append(
            {
                "command": trim_process_line(line),
                "unix_controller": socket_match.group(1) if socket_match else None,
            }
        )
    return rows


def inspect_mihomo_party(root: Path) -> dict[str, object]:
    """读取 Clash Party 的 profile/work 配置路径，并脱敏展示当前 profile。"""

    profile_path = root / "profile.yaml"
    config_path = root / "work" / "config.yaml"
    result: dict[str, object] = {
        "root": str(root),
        "profile_yaml": str(profile_path) if profile_path.exists() else None,
        "work_config": str(config_path) if config_path.exists() else None,
    }
    if not profile_path.exists():
        return result

    text = profile_path.read_text(encoding="utf-8", errors="replace")
    current = find_scalar(text, "current")
    result["current_profile_id"] = current
    if current:
        item = find_profile_item(text, current)
        if item:
            url = item.get("url")
            result["current_profile"] = {
                "id": item.get("id"),
                "name": item.get("name"),
                "type": item.get("type"),
                "url": mask_url(url) if url else None,
                "node1024": "node.1024.hair" in (url or ""),
            }
    return result


def trim_process_line(line: str) -> str:
    """截短进程命令行并遮蔽 token，保留定位 controller 所需信息。"""

    return re.sub(r"(token=)[^\s&]+", r"\1***", line)[:300]


if __name__ == "__main__":
    main()
