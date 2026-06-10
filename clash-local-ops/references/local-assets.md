# Clash/Mihomo 本地资产

## 查找顺序

1. 先检查用户当前使用的客户端：Clash Verge / ClashX / mihomo-party / Clash for Windows / 其它封装。
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

## 慢 IDE 场景

1. 记录用户说的 IDE 名称和进程名。不要只靠产品名猜域名。
2. 按 mtime 取最近日志：

```bash
ls -lt ~/.config/clash-verge/logs/*.log 2>/dev/null | head
tail -n 300 ~/.config/clash-verge/logs/<latest>.log
```

3. 搜索关键词：`timeout`、`error`、`connect`、`rule`、`match`、`openai`、`anthropic`、`github`、`cursor`、`tree`、`trae`、`ide`。
4. 有外部控制器时，优先用 `/connections` 看活跃连接，必要时用 `/logs?level=debug` 临时观测。
5. 只把可解释的域名写成规则；不要把 IP、临时 CDN 子域或带签名参数的 URL 直接写入规则。
