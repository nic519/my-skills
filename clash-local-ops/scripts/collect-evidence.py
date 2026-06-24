#!/usr/bin/env python3
"""按应用、域名或链路关键词收集 Clash/Mihomo 连接证据。"""

from __future__ import annotations

import argparse
import json

from mihomo_runtime import collect_matching_connections, fetch_controller_json


def main() -> None:
    """解析命令行参数，读取 /connections 并输出匹配连接摘要。"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--controller", required=True, help="Controller base URL or unix:/path/to.sock")
    parser.add_argument("--keywords", required=True, help="Comma-separated host/process/chain keywords")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of TSV")
    args = parser.parse_args()

    keywords = [item.strip() for item in args.keywords.split(",") if item.strip()]
    payload = fetch_controller_json(args.controller, "/connections")
    rows = collect_matching_connections(payload, keywords)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return

    print("start\thost\ttype\tinboundPort\trule\trulePayload\tchain\tupload\tdownload")
    for row in rows:
        print(
            "\t".join(
                str(row.get(key) or "")
                for key in ["start", "host", "type", "inboundPort", "rule", "rulePayload", "chain", "upload", "download"]
            )
        )


if __name__ == "__main__":
    main()
