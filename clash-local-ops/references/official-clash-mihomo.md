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
