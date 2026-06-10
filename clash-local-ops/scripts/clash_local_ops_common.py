#!/usr/bin/env python3
"""Shared helpers for clash-local-ops scripts."""

from __future__ import annotations

import json
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from copy import deepcopy
from pathlib import Path
from typing import Any


SENSITIVE_QUERY_KEYS = {"token", "access_token", "key", "owO", "owo"}


def merge_rule_overwrite(current: str | None, new_rules: list[str]) -> str:
    """Return a +rules block with new rules first and exact duplicates removed."""

    ordered_rules: list[str] = []
    seen: set[str] = set()
    for rule in [*new_rules, *parse_rule_overwrite(current or "")]:
        normalized = normalize_rule(rule)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered_rules.append(normalized)

    if not ordered_rules:
        return "+rules:"
    return "\n".join(["+rules:", *[f"  - {rule}" for rule in ordered_rules]])


def parse_rule_overwrite(value: str) -> list[str]:
    rules: list[str] = []
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line or line == "+rules:" or line == "rules:":
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        if line:
            rules.append(line)
    return rules


def normalize_rule(value: str) -> str:
    line = value.strip()
    if line.startswith("- "):
        line = line[2:].strip()
    return re.sub(r"\s*,\s*", ",", line)


def build_node1024_put_payload(response: dict[str, Any], rule_overwrite: str) -> dict[str, Any]:
    """Build the observed node.1024.hair PUT payload while preserving all config fields."""

    data = response.get("data")
    if not isinstance(data, dict):
        raise ValueError("GET response does not contain a data object")
    if not isinstance(data.get("accessToken"), str) or not data["accessToken"]:
        raise ValueError("GET response data.accessToken is required for PUT")

    config = deepcopy(data)
    config["ruleOverwrite"] = rule_overwrite
    return {"config": config}


def collect_matching_connections(payload: dict[str, Any], keywords: list[str]) -> list[dict[str, Any]]:
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


def read_json_url(url: str, timeout: int = 30) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "clash-local-ops/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GET {mask_url(url)} failed: HTTP {error.code}: {body}") from error


def put_json_url(url: str, payload: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
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


def fetch_controller_json(controller: str, endpoint: str, timeout: int = 15) -> dict[str, Any]:
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


def patch_controller_config(controller: str, config_path: Path, timeout: int = 15) -> int:
    payload = json.dumps({"path": str(config_path)}, ensure_ascii=False)
    if controller.startswith("unix:"):
        socket_path = controller.removeprefix("unix:")
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
                "http://127.0.0.1/configs",
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


def mask_url(url: str) -> str:
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
    if len(value) <= 4:
        return "***"
    return f"{value[:3]}***{value[-2:]}"


def node1024_user_url(base_url: str, uid: str, token: str) -> str:
    query = urllib.parse.urlencode({"uid": uid, "token": token})
    return f"{base_url.rstrip('/')}/api/user?{query}"


def node1024_subscription_url(base_url: str, uid: str, token: str) -> str:
    query = urllib.parse.urlencode({"uid": uid, "token": token})
    return f"{base_url.rstrip('/')}/api/x?{query}"


def is_runtime_process_line(line: str) -> bool:
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
