#!/usr/bin/env python3
"""Inspect local Clash/Mihomo runtime without printing secrets."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from clash_local_ops_common import is_runtime_process_line, mask_url


def main() -> None:
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


def find_scalar(text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def find_profile_item(text: str, profile_id: str) -> dict[str, str] | None:
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


def trim_process_line(line: str) -> str:
    return re.sub(r"(token=)[^\s&]+", r"\1***", line)[:300]


def run_text(command: list[str], allow_failure: bool = False) -> str:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0 and not allow_failure:
        raise RuntimeError(result.stderr.strip() or f"{command[0]} failed")
    return result.stdout


if __name__ == "__main__":
    main()
