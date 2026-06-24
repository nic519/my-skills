# Clash/Mihomo 本地资产

## 查找顺序

1. 先运行 `scripts/find-clash-assets.py` 和 `scripts/inspect-runtime.py`，确认用户当前使用的客户端：Clash Verge / ClashX / mihomo-party / Clash for Windows / 其它封装。
2. 再检查通用配置目录：`~/.config/clash`、`~/.config/mihomo`、`~/.config/clash-verge`。
3. 最后检查 macOS 应用支持目录：`~/Library/Application Support/...`。

## 常见 macOS 路径

这些路径来自 Clash/Mihomo 客户端常见约定和本机实测目录名；不同版本可能变化，读取前先 `ls` 或 `find` 验证。

| 客户端/用途 | 候选路径 |
| --- | --- |
| Clash Verge 配置 | `~/.config/clash-verge/config.yaml` |
| Clash Verge 应用设置 | `~/.config/clash-verge/verge.yaml`、`~/.config/clash-verge/clash-verge.yaml` |
| Clash Verge 订阅档案 | `~/.config/clash-verge/profiles.yaml`、`~/.config/clash-verge/profiles/*.yaml` |
| Clash Verge 日志 | `~/.config/clash-verge/logs/*.log` |
| Clash Verge 本地规则集 | `~/.config/clash-verge/ruleset/*.yaml` |
| Mihomo 通用目录 | `~/.config/mihomo` |
| mihomo-party 配置 | `~/Library/Application Support/mihomo-party/mihomo.yaml` |
| ClashX | `~/Library/Application Support/com.west2online.ClashX` |

## 应读文件

- `config.yaml` / `mihomo.yaml`：查 `external-controller`、`secret`、`log-level`、`rules`、`proxy-groups`、`proxy-providers`。
- `profiles.yaml`：查订阅列表和当前激活配置，但不要输出订阅 URL token。
- `profiles/*.yaml`：查展开后的 `proxies`、`proxy-groups`、`rules`。
- `logs/*.log`：查 DNS、rule match、connect error、timeout、目标域名、策略组。
- `cache.db`：只在用户要求且你知道 schema 时读取；否则先不用。

## 应用慢请求场景

1. 记录用户说的应用名称、进程名、操作时间和失败现象。不要只靠产品名猜域名。
2. 优先从控制器取连接证据：

```bash
python3 scripts/collect-evidence.py \
  --controller unix:/tmp/mihomo-party-501-667.sock \
  --keywords example,api
```

3. 若控制器不可用，再按 mtime 取最近日志：

```bash
ls -lt ~/.config/clash-verge/logs/*.log 2>/dev/null | head
tail -n 300 ~/.config/clash-verge/logs/<latest>.log
```

4. 搜索关键词应来自用户报告的应用、进程、域名或错误文本。通用关键词可包含：`timeout`、`error`、`connect`、`rule`、`match`、`failed`、`deadline`、`reset`、`closed`。
5. 结论必须区分两层：应用是否进入 Clash/Mihomo 入口；进入后最终 `chains` 是 `DIRECT` 还是代理组。
6. 只把可解释的域名写成规则；不要把 IP、临时 CDN 子域或带签名参数的 URL 直接写入规则。

## 应用日志补充证据

当 `/connections` 里没有足够证据，或用户报告的是应用内功能失败时，再查该应用自己的近期日志。应用日志用于补充时间窗口、目标域名、进程、错误类型和请求链路，不应替代 Clash/Mihomo 运行时证据。

常见查找方式：

```bash
find "$HOME/Library/Application Support" "$HOME/.config" -maxdepth 5 -type f \
  \( -name '*.log' -o -name '*.txt' \) -mtime -2 -print
```

优先提取这些证据：

- 与用户操作时间接近的错误行。
- 目标 host、URL 中的域名、进程名或功能模块名。
- `stream timeout`、`context deadline exceeded`、`network request failed`、`connection reset/closed` 等网络错误。
- 应用内请求成功但长连接、SSE 或流式响应失败的差异。

归纳时按通用判断收束：

1. 用 `collect-evidence.py --keywords ...` 看请求是否进入 Clash/Mihomo，以及命中的 `rule`、`rulePayload`、`chain`。
2. 如果规则已生效且连接已经命中目标策略组，问题通常不是缺规则，而是当前出口对该应用或请求类型不稳定。
3. 只有当域名仍然 `DIRECT`、命中错误策略组，或出现新的稳定域名族时，才进入规则补充或可选写回判断。
