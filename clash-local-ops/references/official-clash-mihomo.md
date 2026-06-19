# 官方 Clash/Mihomo 接口与规则

## 来源

- Clash 文档：`https://en.clash.wiki/configuration/configuration-reference.html`
- Clash 外部控制器：`https://en.clash.wiki/runtime/external-controller.html`
- Mihomo API：`https://wiki.metacubex.one/en/api/`
- Mihomo Route Rules：`https://wiki.metacubex.one/en/config/rules/`

## 外部控制器

配置文件通常包含：

```yaml
external-controller: 127.0.0.1:9090
secret: ""
log-level: info
```

Mihomo API 请求使用：

```http
Authorization: Bearer ${secret}
```

有些客户端不会在配置文件里写 HTTP 控制器。例如 Clash Party / mihomo-party 可能通过进程参数暴露 Unix socket：

```bash
ps aux | rg mihomo
# ... mihomo ... -ext-ctl-unix /tmp/mihomo-party-501-667.sock

curl --unix-socket /tmp/mihomo-party-501-667.sock http://127.0.0.1/connections
```

此时把控制器记为 `unix:/tmp/mihomo-party-501-667.sock`，可直接传给本 Skill 的脚本。

常用端点：

| 端点 | 用途 |
| --- | --- |
| `GET /logs?level=info` 或 WebSocket | 实时日志；level 可用 `info`、`warning`、`error`、`debug` |
| `GET /connections` 或 WebSocket | 实时连接；可用来确认 IDE 请求连到哪个域名和策略 |
| `DELETE /connections` | 关闭全部连接；规则修改后可清旧连接 |
| `GET /rules` | 查看运行中规则 |
| `GET /proxies` | 查看代理和策略组 |
| `PUT /proxies/{group}` | 为 selector 组选择节点，body 如 `{"name":"Japan"}` |
| `GET /proxies/{name}/delay?url=...&timeout=5000` | 测指定代理延迟 |
| `GET /providers/proxies` | 查看代理 provider |
| `PUT /providers/proxies/{name}` | 更新代理 provider |
| `GET /configs` | 查看基础运行配置 |
| `PATCH /configs` | 更新部分基础配置 |
| `PUT /configs?force=true` | 重载基础配置 |

## 规则语法

规则自上而下匹配，越靠前优先级越高。

常用规则：

```yaml
rules:
  - DOMAIN,api.example.com,PROXY
  - DOMAIN-SUFFIX,example.com,PROXY
  - DOMAIN-KEYWORD,example,PROXY
  - PROCESS-NAME,Cursor,PROXY
  - PROCESS-NAME,Trae,PROXY
  - GEOIP,CN,DIRECT
  - MATCH,PROXY
```

选择规则类型：

- `DOMAIN`：只匹配完整域名，最适合从日志中确认出的 API 域名。
- `DOMAIN-SUFFIX`：匹配域名及子域，适合同一服务的稳定域名族。
- `DOMAIN-KEYWORD`：范围较大，只有用户明确接受时使用。
- `PROCESS-NAME` / `PROCESS-PATH`：Mihomo 支持；适合按本机进程分流，但可移植性较差。
- `RULE-SET`：已有远程或本地规则集时使用，不要为一两个域名新建。
- `MATCH`：兜底规则，不能放在自定义覆盖规则前面。

## 安全约束

- 不要输出 `secret`、订阅 URL token、节点密码或完整代理配置。
- 需要打开 `debug` 日志时，提醒用户完成后恢复，避免日志过大或泄漏。
- 修改规则后，建议关闭旧连接或重启内核，否则已有连接可能继续沿用旧策略。

## 已命中规则但仍慢

当 `/connections` 显示目标域名已经命中正确策略组，且 `verify-rules.py` 或 dry-run 已确认 `ruleOverwrite` 在远端、订阅、本地运行规则中都存在时，不要继续重复添加同一条规则。下一步应检查 selector 当前选择：

```bash
curl --unix-socket /tmp/mihomo-party-501-667.sock \
  http://127.0.0.1/proxies/%5B%E7%B1%BB%5D-%E6%B5%B7%E5%A4%96AI%F0%9F%A4%96
```

关注响应中的：

- `now`：当前 selector 选择的自动组或节点。
- `all`：可切换的已有组和节点。
- `/connections` 的 `chain`：实际链路，例如 `某节点 > [自动]-新加坡 > [类]-海外AI`。

如果应用日志是 `stream timeout`、`context deadline exceeded`、`network request failed`，而普通短请求或配置请求又能成功，优先怀疑当前出口对长连接、SSE、流式响应或目标 CDN 不稳。用户可先在客户端 UI 中把该策略组切到另一个已有出口；只有用户明确要求自动切换，才考虑调用 `PUT /proxies/{group}`。

## 本 Skill 脚本

```bash
python3 scripts/inspect-runtime.py
python3 scripts/collect-evidence.py --controller unix:/tmp/mihomo.sock --keywords trae,mchost
python3 scripts/verify-rules.py --controller unix:/tmp/mihomo.sock --config-path "$HOME/Library/Application Support/mihomo-party/work/config.yaml" --reload --keyword trae.ai
```
