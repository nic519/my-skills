# node.1024.hair Skill

This context defines the language for the skill that helps maintain personal proxy rule overrides through node.1024.hair.

## Language

**node.1024.hair 规则复写助手**:
A skill for turning local Clash/Mihomo behavior evidence into personal rule overrides maintained on node.1024.hair. The website is the primary product surface; Clash/Mihomo is the evidence source and rule runtime.
_Avoid_: 通用代理运维

**本机行为证据**:
Network request evidence produced by a local app or command within a clear time window. It may include the process, target domain, matched proxy group or rule, and the slow or failed behavior that motivated a rule override.
_Avoid_: 全量配置扫描, 泛代理排查

**node.1024.hair 配置订阅地址**:
The personal node.1024.hair config URL used to identify where rule overrides should be read or written. It is not a Clash provider subscription URL and must be treated as sensitive because it contains user identity and token parameters.
_Avoid_: Clash 订阅地址, 节点订阅, provider URL

**本次配置订阅地址确认**:
The required step where the user provides or explicitly confirms the node.1024.hair config URL for the current operation. Example URLs from earlier conversation are format examples only and must not be reused as credentials.
_Avoid_: 复用历史示例 URL, 默认使用旧 token

**写入前确认**:
The required confirmation step before changing node.1024.hair rule overrides. It names the evidence, target group, rule strategy, config subscription URL status, and exact field to be changed.
_Avoid_: 自动静默写入, 直接覆盖配置

**目标策略组**:
A proxy group that already exists in the current node.1024.hair configuration and will receive the matched traffic. The skill may recommend a group, but it must not invent group names.
_Avoid_: 临时组名, 猜测组名

**规则匹配策略**:
The Clash/Mihomo rule type used to match the confirmed evidence, such as `DOMAIN`, `DOMAIN-SUFFIX`, `PROCESS-NAME`, or `DOMAIN-KEYWORD`. The skill should choose the narrowest rule that explains the evidence.
_Avoid_: 代理组, 节点策略, 分流目的地

**node.1024.hair 用户配置 API**:
The already-known API surface used to read or update a user's node.1024.hair configuration. The skill should use the provided API contract and must not infer endpoints from the config subscription URL.
_Avoid_: API 推导, 接口猜测
