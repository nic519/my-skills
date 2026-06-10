# node.1024.hair 用户配置 API

## 目标

把从本机行为证据中提炼出的 Clash/Mihomo 规则写入用户的 `node.1024.hair` 个人配置，重点字段是：

```json
{
  "config": {
    "ruleOverwrite": "+rules:\n  - DOMAIN,example.com,DIRECT"
  }
}
```

## 默认接口模板

不要把真实 token 写进 Skill。使用环境变量或用户当次提供并确认的值。历史对话中的示例 `node.1024.hair/config?uid=...&token=...` 只能说明格式，不能作为本次凭据。

```bash
export NODE1024_BASE_URL="https://node.1024.hair"
export NODE1024_UID="..."
export NODE1024_TOKEN="..."

curl "$NODE1024_BASE_URL/api/user?uid=$NODE1024_UID&token=$NODE1024_TOKEN" \
  -X PUT \
  -H "Content-Type: application/json" \
  --data-raw @payload.json
```

使用已知 API 契约，不要从配置订阅地址推导接口路径。

## PUT 风险

用户提供的契约是 `PUT /api/user?uid=...&token=...`，body 中包含完整 `config`。因此默认认为 PUT 可能替换整个配置。

安全做法：

1. 先查是否有 GET 接口能取回当前用户配置。
2. 如果能取回，保留原有 `config` 的所有字段，只替换 `config.ruleOverwrite`。
3. 如果不能取回，让用户提供当前完整 config，或明确确认可以用当前 payload 覆盖。
4. 不要发送只含 `ruleOverwrite` 的极简 body，除非服务端文档明确它会 merge。

## 写入前确认

写入前必须让用户确认：

1. 本机行为证据：时间窗口、应用或进程、目标域名、命中规则或错误。
2. 目标策略组：必须来自当前配置，不能自造。
3. 规则匹配策略：`DOMAIN`、`DOMAIN-SUFFIX`、`PROCESS-NAME` 或用户确认的 `DOMAIN-KEYWORD`。
4. 本次配置订阅地址：用户本次提供或明确确认，展示时脱敏 token。
5. 修改字段：默认只改 `config.ruleOverwrite`，保留其它配置字段。

## ruleOverwrite 格式

用户当前规则覆盖形态：

```yaml
+rules:
  - DOMAIN,sub2.kalin.asia,DIRECT
  - DOMAIN,sub2.kalin.asia1,DIRECT
```

约定：

- 顶层使用 `+rules:` 表示追加规则。
- 每条规则保持 Clash/Mihomo 格式：`类型,匹配值,策略或策略组[,参数]`。
- 新规则放在更宽泛规则之前。
- 策略组名称必须来自当前 node.1024.hair 配置的 `proxy-groups` 或用户明确指定的现有组，不能自造。
- 域名来自日志或连接证据；不能从错误信息里凭空猜。

## 规则生成模板

```yaml
+rules:
  - DOMAIN,api.service.example,[类]-海外AI🤖
  - DOMAIN-SUFFIX,service-cdn.example,[类]-海外AI🤖
```

常见目标：

- IDE/AI 服务慢：优先 `[类]-海外AI🤖`、`[单]-Cursor🐶`、`✈️ 手动选择` 或用户指定代理组。
- 订阅、规则模板、本地服务：优先 `DIRECT`。
- YouTube/TikTok/Apple 等：优先用户已有的专门策略组，不要混入 AI 组。

## 输出给用户前的检查

- YAML 缩进为两个空格。
- 没有完整 token、完整配置订阅地址、Clash 订阅 URL、节点密码。
- 域名不包含协议、路径、查询参数。
- 规则策略组在当前配置中存在，或明确标注需要用户替换。
