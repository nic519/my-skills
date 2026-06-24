#!/usr/bin/env python3
"""Clash ruleOverwrite 规则解析、规范化和合并逻辑。"""

from __future__ import annotations

import re
from pathlib import Path


def merge_rule_overwrite(current: str | None, new_rules: list[str]) -> str:
    """合并 ruleOverwrite 规则块，把本次新增规则前置并去掉完全重复项。"""

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
    """从 +rules/rules 文本块或裸规则行中提取标准规则字符串。"""

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
    """规范化单条规则的逗号间距和可选 YAML 列表前缀。"""

    line = value.strip()
    if line.startswith("- "):
        line = line[2:].strip()
    return re.sub(r"\s*,\s*", ",", line)


def read_rule_file(path: Path) -> list[str]:
    """读取规则文件，兼容 +rules YAML 块和一行一条的裸规则格式。"""

    return parse_rule_overwrite(path.read_text(encoding="utf-8"))
