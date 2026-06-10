#!/usr/bin/env python3
"""列出本机 Clash/Mihomo 相关候选资产，不读取敏感内容。"""

from __future__ import annotations

import json
import os
from pathlib import Path


MAX_DEPTH = 4
MAX_FILES_PER_ROOT = 200


def main() -> None:
    home = Path.home()
    roots = [
        home / ".config" / "clash-verge",
        home / ".config" / "clash",
        home / ".config" / "mihomo",
        home / "Library" / "Application Support" / "mihomo-party",
        home / "Library" / "Application Support" / "com.west2online.ClashX",
        home / "Library" / "Application Support" / "Clashy",
    ]

    payload = []
    for root in roots:
        if not root.exists():
            continue
        files = []
        for path in walk_limited(root):
            try:
                stat = path.stat()
            except OSError:
                continue
            files.append(
                {
                    "path": str(path).replace(str(home), "~", 1),
                    "kind": classify(path),
                    "size": stat.st_size,
                    "mtime": int(stat.st_mtime),
                }
            )
            if len(files) >= MAX_FILES_PER_ROOT:
                break
        payload.append({"root": str(root).replace(str(home), "~", 1), "files": files})

    print(json.dumps(payload, ensure_ascii=False, indent=2))


def walk_limited(root: Path):
    root_depth = len(root.parts)
    for current, dirs, names in os.walk(root):
        current_path = Path(current)
        depth = len(current_path.parts) - root_depth
        if depth >= MAX_DEPTH:
            dirs[:] = []
        dirs[:] = sorted(skip_noisy_dirs(dirs))
        for name in sorted(names):
            yield current_path / name


def skip_noisy_dirs(dirs: list[str]):
    noisy = {
        "Cache",
        "Code Cache",
        "GPUCache",
        "DawnGraphiteCache",
        "DawnWebGPUCache",
        "Service Worker",
        "Session Storage",
    }
    return [item for item in dirs if item not in noisy]


def classify(path: Path) -> str:
    suffix = path.suffix.lower()
    name = path.name.lower()
    if suffix in {".yaml", ".yml"}:
        if "profile" in str(path).lower():
            return "profile-yaml"
        return "config-yaml"
    if suffix == ".log":
        return "log"
    if suffix in {".db", ".sqlite"}:
        return "database"
    if name in {"country.mmdb", "geoip.dat", "geosite.dat"}:
        return "geo-data"
    if suffix == ".json":
        return "json"
    return "other"


if __name__ == "__main__":
    main()
