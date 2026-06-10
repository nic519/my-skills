import json
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from clash_local_ops_common import (  # noqa: E402
    build_node1024_put_payload,
    collect_matching_connections,
    find_latest_unix_controller,
    find_node1024_profile,
    is_runtime_process_line,
    mask_url,
    merge_rule_overwrite,
    summarize_verification_state,
)


class RuleOverwriteTests(unittest.TestCase):
    def test_merge_prepends_new_rules_and_deduplicates_existing_rules(self):
        current = "\n".join(
            [
                "+rules:",
                "  - DOMAIN-SUFFIX,trae.ai,[类]-海外AI🤖",
                "  - DOMAIN,sub2.kalin.asia,DIRECT",
            ]
        )
        new_rules = [
            "DOMAIN-SUFFIX,trae.ai,[类]-海外AI🤖",
            "DOMAIN-SUFFIX,traeapi.us,[类]-海外AI🤖",
            "DOMAIN-SUFFIX,mchost.guru,[类]-海外AI🤖",
        ]

        result = merge_rule_overwrite(current, new_rules)

        self.assertEqual(
            result,
            "\n".join(
                [
                    "+rules:",
                    "  - DOMAIN-SUFFIX,trae.ai,[类]-海外AI🤖",
                    "  - DOMAIN-SUFFIX,traeapi.us,[类]-海外AI🤖",
                    "  - DOMAIN-SUFFIX,mchost.guru,[类]-海外AI🤖",
                    "  - DOMAIN,sub2.kalin.asia,DIRECT",
                ]
            ),
        )

    def test_merge_creates_rules_block_when_current_is_empty(self):
        result = merge_rule_overwrite("", ["DOMAIN,example.com,DIRECT"])

        self.assertEqual(result, "+rules:\n  - DOMAIN,example.com,DIRECT")


class Node1024PayloadTests(unittest.TestCase):
    def test_build_payload_preserves_full_data_config_shape(self):
        response = {
            "code": 0,
            "msg": "操作成功",
            "data": {
                "accessToken": "secret-token",
                "appendSubList": [{"subscribe": "https://example.invalid/sub"}],
                "fileName": "BIGME1",
                "requiredFilters": "[类]-海外AI🤖",
                "ruleOverwrite": "+rules:\n  - DOMAIN,old.example,DIRECT",
                "ruleUrl": "https://node.1024.hair/api/subscription/template/id",
                "updatedAt": "2026-06-10T16:03:44.404Z",
            },
        }

        payload = build_node1024_put_payload(response, "+rules:\n  - DOMAIN,new.example,DIRECT")

        self.assertEqual(payload["config"]["accessToken"], "secret-token")
        self.assertEqual(payload["config"]["appendSubList"], [{"subscribe": "https://example.invalid/sub"}])
        self.assertEqual(payload["config"]["ruleOverwrite"], "+rules:\n  - DOMAIN,new.example,DIRECT")

    def test_build_payload_rejects_missing_access_token(self):
        with self.assertRaises(ValueError):
            build_node1024_put_payload({"code": 0, "data": {"ruleOverwrite": ""}}, "+rules:")


class EvidenceTests(unittest.TestCase):
    def test_collect_matching_connections_summarizes_hosts_and_chains(self):
        payload = {
            "connections": [
                {
                    "start": "2026-06-11T00:59:00+08:00",
                    "metadata": {
                        "host": "api22-normal-alisg.mchost.guru",
                        "type": "HTTPS",
                        "inboundPort": "7890",
                    },
                    "rule": "RuleSet",
                    "rulePayload": "cn_domain",
                    "chains": ["DIRECT"],
                    "upload": 10,
                    "download": 20,
                },
                {
                    "start": "2026-06-11T01:02:13+08:00",
                    "metadata": {
                        "host": "core22-normal-sg.trae.ai",
                        "type": "HTTPS",
                        "inboundPort": "7890",
                    },
                    "rule": "RuleSet",
                    "rulePayload": "ai",
                    "chains": ["node", "[自动]-新加坡🇸🇬", "[类]-海外AI🤖"],
                    "upload": 30,
                    "download": 40,
                },
            ]
        }

        rows = collect_matching_connections(payload, ["trae", "mchost"])

        self.assertEqual([row["host"] for row in rows], ["api22-normal-alisg.mchost.guru", "core22-normal-sg.trae.ai"])
        self.assertEqual(rows[0]["chain"], "DIRECT")
        self.assertEqual(rows[1]["chain"], "node > [自动]-新加坡🇸🇬 > [类]-海外AI🤖")


class RedactionTests(unittest.TestCase):
    def test_mask_url_redacts_token_without_encoding_mask(self):
        result = mask_url("https://node.1024.hair/api/x?uid=519&token=d2f1441a2f96")

        self.assertEqual(result, "https://node.1024.hair/api/x?uid=519&token=d2f***96")


class RuntimeProcessTests(unittest.TestCase):
    def test_runtime_process_filter_skips_this_skill_scripts(self):
        self.assertFalse(is_runtime_process_line("/bin/zsh -c python3 clash-local-ops/scripts/inspect-runtime.py"))
        self.assertTrue(is_runtime_process_line("/Applications/Clash Party.app/Contents/Resources/sidecar/mihomo -ext-ctl-unix /tmp/mihomo.sock"))

    def test_find_latest_unix_controller_uses_active_mihomo_socket(self):
        process_text = "\n".join(
            [
                "root 932 0.0 /Applications/Clash Party.app/Contents/Resources/sidecar/mihomo -d /Users/me/Library/Application Support/mihomo-party/work -ext-ctl-unix /tmp/mihomo-party-501-667.sock",
                "root 47343 0.0 /Applications/Clash Party.app/Contents/Resources/sidecar/mihomo -d /Users/me/Library/Application Support/mihomo-party/work -ext-ctl-unix /tmp/mihomo-party-501-47330.sock",
            ]
        )

        self.assertEqual(find_latest_unix_controller(process_text), "unix:/tmp/mihomo-party-501-47330.sock")


class MihomoPartyProfileTests(unittest.TestCase):
    def test_find_node1024_profile_returns_current_profile_credentials(self):
        text = "\n".join(
            [
                "current: abc123",
                "items:",
                "  - id: old",
                "    name: OLD.yaml",
                "    type: remote",
                "    url: https://node.1024.hair/api/x?uid=1&token=old-token",
                "  - id: abc123",
                "    name: BIGME.yaml",
                "    type: remote",
                "    url: https://node.1024.hair/api/x?uid=519&token=d2f1441a2f96",
            ]
        )

        profile = find_node1024_profile(text)

        self.assertEqual(profile["id"], "abc123")
        self.assertEqual(profile["uid"], "519")
        self.assertEqual(profile["token"], "d2f1441a2f96")
        self.assertEqual(profile["subscription_url"], "https://node.1024.hair/api/x?uid=519&token=d2f1441a2f96")


class VerificationSummaryTests(unittest.TestCase):
    def test_runtime_stale_recommends_restart_after_remote_and_local_are_ok(self):
        summary = summarize_verification_state(
            remote_ok=True,
            subscription_ok=True,
            local_ok=True,
            runtime_ok=False,
            has_local_check=True,
            has_runtime_check=True,
        )

        self.assertEqual(summary["status"], "runtime_stale")
        self.assertEqual(summary["recommended_next_action"], "restart_clash_party")

    def test_remote_ready_recommends_refreshing_local_config_when_no_local_check(self):
        summary = summarize_verification_state(
            remote_ok=True,
            subscription_ok=True,
            local_ok=False,
            runtime_ok=False,
            has_local_check=False,
            has_runtime_check=False,
        )

        self.assertEqual(summary["status"], "remote_ready")
        self.assertEqual(summary["recommended_next_action"], "refresh_local_config")


if __name__ == "__main__":
    unittest.main()
