#!/usr/bin/env python3
"""Collect Clash/Mihomo connection evidence for app or domain keywords."""

from __future__ import annotations

import argparse
import json

from clash_local_ops_common import collect_matching_connections, fetch_controller_json


def main() -> None:
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
