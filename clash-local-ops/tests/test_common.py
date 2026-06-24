import json
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
SKILL_PATH = Path(__file__).resolve().parents[1] / "SKILL.md"
sys.path.insert(0, str(SCRIPT_DIR))

from clash_rules import merge_rule_overwrite, read_rule_file  # noqa: E402
from http_helpers import mask_url, read_text_url  # noqa: E402
from local_commands import run_text  # noqa: E402
from mihomo_runtime import collect_matching_connections, find_latest_unix_controller, is_runtime_process_line  # noqa: E402
from node1024_config import build_node1024_put_payload  # noqa: E402
from profile_config import find_node1024_profile, find_profile_item_by_id, find_yaml_scalar  # noqa: E402
from verification_state import summarize_verification_state  # noqa: E402


def load_script_module(filename: str, module_name: str):
    """按文件名加载带连字符的 CLI 脚本，便于测试其中的纯函数。"""

    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_DIR / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RuleOverwriteTests(unittest.TestCase):
    """验证 ruleOverwrite 解析、合并和规则文件读取的公共行为。"""

    def test_merge_prepends_new_rules_and_deduplicates_existing_rules(self):
        """新规则应前置，和已有规则完全重复时只保留一份。"""

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
        """空复写内容应生成合法的 +rules 块。"""

        result = merge_rule_overwrite("", ["DOMAIN,example.com,DIRECT"])

        self.assertEqual(result, "+rules:\n  - DOMAIN,example.com,DIRECT")

    def test_read_rule_file_accepts_rules_block_or_plain_rules(self):
        """规则文件既可以是 +rules YAML 块，也可以是一行一条裸规则。"""

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "rules.yaml"
            path.write_text(
                "\n".join(
                    [
                        "+rules:",
                        "  - DOMAIN,api.example.com,DIRECT",
                        "DOMAIN-SUFFIX,example.com,Proxy",
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                read_rule_file(path),
                ["DOMAIN,api.example.com,DIRECT", "DOMAIN-SUFFIX,example.com,Proxy"],
            )


class SkillPositioningTests(unittest.TestCase):
    """锁定 skill 文案的定位，避免未来又默认写回远端配置。"""

    def test_skill_is_clash_diagnosis_first_not_node1024_writeback_first(self):
        """技能触发描述应以 Clash/Mihomo 排查为主。"""

        text = SKILL_PATH.read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]

        self.assertIn("Use when diagnosing local Clash/Mihomo issues", frontmatter)
        self.assertNotIn("turned into node.1024.hair personal rule overrides", frontmatter)
        self.assertIn("以排查 Clash/Mihomo 问题为主", text)
        self.assertIn("不要把写回 `node.1024.hair` 当成默认解决路径", text)

    def test_node1024_writeback_requires_yaml_subscription_management_url(self):
        """写回 node.1024.hair 必须以用户配置里的管理地址为条件。"""

        text = SKILL_PATH.read_text(encoding="utf-8")

        self.assertIn("只有看到用户的 YAML/配置中包含", text)
        self.assertIn("`node.1024.hair/config?uid=...&token=...`", text)
        self.assertIn("才询问是否把 `ruleOverwrite` 写回 `node.1024.hair`", text)


class Node1024PayloadTests(unittest.TestCase):
    """验证 node.1024.hair 写回 payload 的保形逻辑。"""

    def test_build_payload_preserves_full_data_config_shape(self):
        """写回时只替换 ruleOverwrite，其他配置字段必须原样保留。"""

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
        """缺少 accessToken 时拒绝构造 PUT payload，避免写入不完整配置。"""

        with self.assertRaises(ValueError):
            build_node1024_put_payload({"code": 0, "data": {"ruleOverwrite": ""}}, "+rules:")


class EvidenceTests(unittest.TestCase):
    """验证从 Mihomo connections 响应里提取排查证据的逻辑。"""

    def test_collect_matching_connections_summarizes_hosts_and_chains(self):
        """按关键词匹配 host、规则和链路，并输出便于阅读的连接摘要。"""

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
    """验证敏感 URL 展示前的脱敏策略。"""

    def test_mask_url_redacts_token_without_encoding_mask(self):
        """token 查询参数必须被遮蔽，避免在输出或异常中泄漏。"""

        result = mask_url("https://node.1024.hair/api/x?uid=33&token=test")

        self.assertEqual(result, "https://node.1024.hair/api/x?uid=33&token=***")

    def test_read_text_url_reads_utf8_text(self):
        """文本 URL 读取 helper 应保留 UTF-8 内容，供订阅配置校验复用。"""

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "config.yaml"
            path.write_text("rules:\n  - DOMAIN,例子.test,DIRECT\n", encoding="utf-8")

            self.assertIn("例子.test", read_text_url(path.as_uri()))


class RuntimeProcessTests(unittest.TestCase):
    """验证本机运行进程识别，避免把排查脚本自身当成 Mihomo。"""

    def test_run_text_returns_stdout_for_successful_command(self):
        """本机命令 helper 应返回 stdout，供进程和系统代理探测复用。"""

        self.assertEqual(run_text([sys.executable, "-c", "print('ok')"]), "ok\n")

    def test_run_text_can_tolerate_expected_failure(self):
        """允许失败时，命令退出非零不应中断可选证据采集。"""

        self.assertEqual(run_text([sys.executable, "-c", "raise SystemExit(7)"], allow_failure=True), "")

    def test_runtime_process_filter_skips_this_skill_scripts(self):
        """运行时筛选应排除本 skill 的脚本命令行。"""

        self.assertFalse(is_runtime_process_line("/bin/zsh -c python3 clash-local-ops/scripts/inspect-runtime.py"))
        self.assertTrue(is_runtime_process_line("/Applications/Clash Party.app/Contents/Resources/sidecar/mihomo -ext-ctl-unix /tmp/mihomo.sock"))

    def test_find_latest_unix_controller_uses_active_mihomo_socket(self):
        """多个 Mihomo 进程存在时，取最后出现的 unix controller 作为当前候选。"""

        process_text = "\n".join(
            [
                "root 932 0.0 /Applications/Clash Party.app/Contents/Resources/sidecar/mihomo -d /Users/me/Library/Application Support/mihomo-party/work -ext-ctl-unix /tmp/mihomo-party-501-667.sock",
                "root 47343 0.0 /Applications/Clash Party.app/Contents/Resources/sidecar/mihomo -d /Users/me/Library/Application Support/mihomo-party/work -ext-ctl-unix /tmp/mihomo-party-501-47330.sock",
            ]
        )

        self.assertEqual(find_latest_unix_controller(process_text), "unix:/tmp/mihomo-party-501-47330.sock")


class MihomoPartyProfileTests(unittest.TestCase):
    """验证 Clash Party profile.yaml 中 node.1024.hair 配置的解析。"""

    def test_profile_helpers_use_yaml_specific_names(self):
        """profile 解析 helper 的名称应清楚表达 YAML 标量和按 id 查找条目。"""

        text = "\n".join(
            [
                "current: abc123",
                "items:",
                "  - id: abc123",
                "    name: BIGME.yaml",
                "    type: remote",
            ]
        )

        self.assertEqual(find_yaml_scalar(text, "current"), "abc123")
        profile_item = find_profile_item_by_id(text, "abc123")
        assert profile_item is not None
        self.assertEqual(profile_item["name"], "BIGME.yaml")

    def test_find_node1024_profile_returns_current_profile_credentials(self):
        """优先返回 current 指向的 node.1024.hair profile 和凭据。"""

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
                "    url: https://node.1024.hair/api/x?uid=33&token=test",
            ]
        )

        profile = find_node1024_profile(text)

        self.assertEqual(profile["id"], "abc123")
        self.assertEqual(profile["uid"], "33")
        self.assertEqual(profile["token"], "test")
        self.assertEqual(profile["subscription_url"], "https://node.1024.hair/api/x?uid=33&token=test")


class VerificationSummaryTests(unittest.TestCase):
    """验证远端、订阅、本地和运行时四层状态的归纳结果。"""

    def test_runtime_stale_recommends_restart_after_remote_and_local_are_ok(self):
        """远端和本地都正确但运行时未加载时，应建议重启 Clash Party。"""

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
        """只确认远端与订阅成功时，应提示继续刷新本地配置。"""

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


class CliResultBuilderTests(unittest.TestCase):
    """验证 CLI 脚本里的结果组装逻辑可以脱离网络和本机运行时独立测试。"""

    def test_verify_rules_builds_layered_result_without_io(self):
        """verify-rules 的 main 之外应有纯函数负责四层校验结果。"""

        module = load_script_module("verify-rules.py", "verify_rules_script")
        result = module.build_verification_result(
            user_url="https://node.1024.hair/api/user?uid=33&token=test",
            subscription_url="https://node.1024.hair/api/x?uid=33&token=test",
            rule_overwrite="+rules:\n  - DOMAIN,api.example.com,DIRECT",
            subscription_text="rules:\n  - DOMAIN,api.example.com,DIRECT",
            keywords=["api.example.com"],
            local_text="rules:\n  - DOMAIN,api.example.com,DIRECT",
            local_config_path=Path("/tmp/config.yaml"),
            runtime_rules_payload={"rules": [{"type": "Domain", "payload": "api.example.com", "proxy": "DIRECT"}]},
        )

        self.assertEqual(result["user_url"], "https://node.1024.hair/api/user?uid=33&token=***")
        self.assertTrue(result["remote_rule_overwrite_matches"])
        self.assertTrue(result["runtime_rules_match"])
        self.assertEqual(result["state"]["status"], "ready")

    def test_apply_and_refresh_builds_result_without_io(self):
        """apply-and-refresh 的状态输出应由可测试函数组装。"""

        module = load_script_module("apply-and-refresh-rules.py", "apply_and_refresh_script")
        result = module.build_apply_result(
            user_url="https://node.1024.hair/api/user?uid=33&token=test",
            subscription_url="https://node.1024.hair/api/x?uid=33&token=test",
            mode="dry-run",
            profile_id="abc123",
            rule_overwrite="+rules:\n  - DOMAIN,api.example.com,DIRECT",
            remote_ok=True,
            subscription_ok=True,
            local_ok=False,
            runtime_ok=False,
            has_local_check=False,
            has_runtime_check=False,
        )

        self.assertEqual(result["profile_id"], "abc123")
        self.assertEqual(result["subscription_url"], "https://node.1024.hair/api/x?uid=33&token=***")
        self.assertEqual(result["state"]["status"], "remote_ready")


if __name__ == "__main__":
    unittest.main()
