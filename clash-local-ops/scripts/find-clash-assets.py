#!/usr/bin/env python3
"""列出本机 Clash/Mihomo 相关候选资产，不读取敏感内容。"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path


MAX_DEPTH = 4
MAX_FILES_PER_ROOT = 200


def main() -> None:
    """扫描常见 Clash/Mihomo 配置目录，输出有限数量的候选文件摘要。"""

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


def walk_limited(root: Path) -> Iterator[Path]:
    """按固定深度遍历目录，避免误扫缓存和大型历史文件。"""

    root_depth = len(root.parts)
    for current, dirs, names in os.walk(root):
        current_path = Path(current)
        depth = len(current_path.parts) - root_depth
        if depth >= MAX_DEPTH:
            dirs[:] = []
        dirs[:] = sorted(skip_noisy_dirs(dirs))
        for name in sorted(names):
            yield current_path / name


def skip_noisy_dirs(dirs: list[str]) -> list[str]:
    """过滤浏览器或桌面应用缓存目录，让资产扫描聚焦配置和日志。"""

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
    """按文件名和扩展名给候选资产打粗粒度类型标签。"""

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
