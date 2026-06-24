#!/usr/bin/env python3
"""本机只读命令执行辅助函数。"""

from __future__ import annotations

import subprocess


def run_text(command: list[str], allow_failure: bool = False) -> str:
    """运行本机命令并返回 stdout，可用于允许失败的只读探测。"""

    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0 and not allow_failure:
        raise RuntimeError(result.stderr.strip() or f"{command[0]} failed")
    return result.stdout
