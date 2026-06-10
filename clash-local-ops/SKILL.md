---
name: clash-local-ops
description: Use when local app, IDE, Git, CLI, or web traffic needs Clash/Mihomo evidence turned into node.1024.hair personal rule overrides, especially for finding domains, strategy groups, and writing config.ruleOverwrite through the known user config API.
---

# node.1024.hair 规则复写助手

## 何时使用

当用户要为 `node.1024.hair` 上的个人配置添加或修正 `ruleOverwrite`，并且需要从本机 Clash/Mihomo 行为里找到域名、进程、策略组、错分流或慢请求证据时，使用本 Skill。

典型场景：某个 IDE、AI 工具、命令行或网页请求很慢，需要从 Clash/Mihomo 的日志、实时连接、DNS 查询或配置里确认目标域名，再把单独规则写入 `node.1024.hair` 的 `config.ruleOverwrite`。

默认解决路径是新增或修正 `node.1024.hair` 的 `ruleOverwrite`。不要把本 Skill 转向通用 Clash 运维、节点测速、系统代理、Git 代理、IDE 代理或 shell 环境变量配置；这些只能作为辅助证据，用来判断请求是否进入 Clash/Mihomo、命中了什么规则、应该补哪条域名或进程规则。除非用户明确要求，否则不要把 `git config http.proxy`、应用内代理设置、系统代理设置当成本 Skill 的主要解决方案。

Clash/Mihomo 是证据来源和运行时；`node.1024.hair` 才是主要写入表面。

## 工作流

1. **先定位客户端资产。** 优先运行 `scripts/inspect-runtime.py` 获取当前 Clash Party profile、work config 和最新 Mihomo unix controller。只有找不到活动客户端时才运行 `scripts/find-clash-assets.py`；不要一开始读取大量历史日志。
2. **识别运行时控制器。** 优先运行 `scripts/inspect-runtime.py`。在配置里查 `external-controller`、`external-controller-cors`、`secret`、`log-level`；如果为空，再从运行进程里查 Mihomo 的 `-ext-ctl-unix /tmp/...sock`。不要猜端口。
3. **确认本机行为证据。** 明确时间窗口、应用或进程、目标域名、命中规则或策略组、慢或失败现象。优先用 `scripts/collect-evidence.py` 查 `/connections`，必要时再看最近 5-15 分钟日志或 `/logs?level=warning`；只摘录域名、策略组、错误和时间，不复制 token、订阅 URL、完整节点。若问题来自 Trae、GitHub、Git、IDE 或 CLI，只把 Git/应用/环境代理检查当作判定请求路径的证据，下一步仍应回到可写入 `ruleOverwrite` 的域名、进程或策略组规则。
4. **确认本次配置订阅地址。** 让用户提供或明确确认本次要使用的 `node.1024.hair/config?uid=...&token=...`。历史对话里的示例 URL 只能说明格式，不能复用为凭据。展示时必须脱敏 token。
5. **读取当前用户配置。** 使用已知的 `node.1024.hair` 用户配置 API，不从配置订阅地址推导端点。优先用 `scripts/update-node1024-rules.py` 的 dry-run 模式确认将写入的 `ruleOverwrite`；需要确认当前 `proxy-groups`、已有 `ruleOverwrite` 和目标字段。
6. **选择目标策略组。** 目标组名必须来自当前 `node.1024.hair` 配置或用户明确指定的现有组；不要自造类似 AI、手动选择、DIRECT 之外的组名。若组不存在，要求用户选择实际组名。
7. **选择规则匹配策略。** 域名精确命中用 `DOMAIN`，确认域名族才用 `DOMAIN-SUFFIX`，本机应用维度可用 `PROCESS-NAME`，`DOMAIN-KEYWORD` 只有用户明确接受扩大范围时使用。
8. **写入前确认。** 展示证据、目标策略组、规则匹配策略、本次配置订阅地址状态、将修改的字段和 payload 摘要。只有用户确认后才调用 API。
9. **写入并验证。** 写入时保留现有配置其它字段，只修改 `ruleOverwrite`。优先用 `scripts/apply-and-refresh-rules.py` 完成 dry-run/apply/本地刷新/重启验证；只在需要拆分排查时使用 `scripts/update-node1024-rules.py` 和 `scripts/verify-rules.py`。

## 快速路径

常见 IDE、GitHub、Trae、CLI、网页慢请求场景，按这个顺序收束：

1. `inspect-runtime.py` 找当前 profile、work config、unix controller。
2. `collect-evidence.py --controller ... --keywords ...` 确认域名、进程、命中规则和策略组。
3. 选已有策略组并 dry-run：

```bash
python3 /path/to/clash-local-ops/scripts/apply-and-refresh-rules.py \
  --rule "DOMAIN-SUFFIX,example.com,🚀 国外流量"
```

4. 用户确认后写入、刷新本地配置、重启 Clash Party 并验证运行时：

```bash
python3 /path/to/clash-local-ops/scripts/apply-and-refresh-rules.py \
  --rule "DOMAIN-SUFFIX,example.com,🚀 国外流量" \
  --apply --refresh-local --restart-app
```

验证结果看 `state.status`：`ready` 才代表远端配置、生成订阅、本地缓存和当前 `/rules` 都已一致。`remote_ready` 表示远端已写入但本地未刷新；`local_stale` 表示本地缓存未更新；`runtime_stale` 表示本地文件已更新但 Mihomo 运行时还没加载，优先重启 Clash Party。不要只凭 `PATCH /configs` 返回 204 判定已生效。

## 本地查找

详细路径见 `references/local-assets.md`。

常用命令：

```bash
python3 /path/to/clash-local-ops/scripts/find-clash-assets.py
python3 /path/to/clash-local-ops/scripts/inspect-runtime.py
```

快速人工查找：

```bash
find "$HOME/.config" "$HOME/Library/Application Support" -maxdepth 3 \
  \( -iname '*clash*' -o -iname '*mihomo*' -o -iname '*verge*' \) -print 2>/dev/null
```

## 外部控制器

详细 API 见 `references/official-clash-mihomo.md`。

请求模板：

```bash
curl -H "Authorization: Bearer $CLASH_SECRET" "http://127.0.0.1:9090/connections"
curl -H "Authorization: Bearer $CLASH_SECRET" "http://127.0.0.1:9090/rules"
python3 /path/to/clash-local-ops/scripts/collect-evidence.py \
  --controller unix:/tmp/mihomo-party-501-667.sock \
  --keywords trae,mchost
```

实时日志和连接可以是 WebSocket，也可以先用普通 GET 看是否可用。不要把 `secret` 写进最终答案、提交、Skill 或 node.1024.hair 配置。

## node.1024.hair 用户配置 API

详细契约见 `references/rule-store-api.md`。

默认把接口视为用户私有服务，所有示例必须使用占位符。不要把真实 `uid`、`token`、配置订阅地址或订阅 URL 写进 Skill、提交或最终输出。

```bash
python3 /path/to/clash-local-ops/scripts/update-node1024-rules.py \
  --uid "$NODE1024_UID" \
  --token "$NODE1024_TOKEN" \
  --rule "DOMAIN,example.com,DIRECT"

python3 /path/to/clash-local-ops/scripts/update-node1024-rules.py \
  --uid "$NODE1024_UID" \
  --token "$NODE1024_TOKEN" \
  --rule "DOMAIN,example.com,DIRECT" \
  --apply
```

如果用户提供了真实 token，只用于当次请求；展示时只保留 `uid` 或 token 前几位，不能完整复述。

## 输出规范

给用户的结论按这个顺序：

1. 找到了哪些本机行为证据。
2. 慢或错分流最可能涉及哪些域名、进程、当前命中规则或策略组。
3. 推荐归并到哪个目标策略组，并说明该组来自当前配置。
4. 推荐的规则匹配策略和规则片段。
5. 本次配置订阅地址是否已确认，以及将修改的字段。
6. 写入状态和验证步骤。

规则片段必须是可复制的 YAML：

```yaml
+rules:
  - DOMAIN,api.example.com,[类]-海外AI🤖
  - DOMAIN-SUFFIX,example-cdn.com,[类]-海外AI🤖
```
