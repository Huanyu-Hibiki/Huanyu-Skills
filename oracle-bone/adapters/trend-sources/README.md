# trend-sources — 热点抓取源

## 信源层级（source_tier，候选可选字段，语义见 candidate-schema）

| 层级 | 定义 | 本目录 adapter 默认值 | 入池规则 |
|---|---|---|---|
| A | 官方一手（公告/文档/监管备案/仓库 release） | — | 可单独入池 |
| B | 权威半官方（当事人实名/大会演讲/官方路线图/应用商店） | — | 可单独入池 |
| C | 专业媒体与研究机构 | hackernews ★C、bilibili-popular ★C-D 混合 | 可单独入池 |
| D | 社区讨论/社媒热帖（线索或弱证据） | manual-paste ★用户自判或默认 D、audience-feedback ★D | 可入池，recommend 稳分位降档 |
| E | 聚合号/SEO 摘要（只可溯源） | — | **单源不入池**，只做线索找 A-D 佐证 |

新写 adapter 文档时标注自己默认落在哪层；用户粘贴内容层级不明 → 按 D 处理，trends 打分时按 snapshot 内容可上调。

| Adapter | 依赖 | 稳定性 | 说明 |
|---|---|---|---|
| [manual-paste.md](manual-paste.md) | 无 | ★★★★★ | 永远可用的兜底：用户粘 URL/标题列表 |
| [hackernews.md](hackernews.md) | 无 key | ★★★★☆ | HN Algolia API |
| [bilibili-popular.md](bilibili-popular.md) | 无（部分端点需 cookie） | ★★★☆☆ | B 站 popular/ranking 接口 |
| [audience-feedback.md](audience-feedback.md) | 无 | ★★★★☆ | 从自己受众反馈找选题（评论区/私信追问） |
| [custom-API.md](custom-API.md) | 按平台 | — | 第三方数据服务接入模板（新榜/飞瓜等） |

**通用契约**（详见 [HOWTO](../HOWTO.md)）：
- fetch → 符合 [candidate-schema](../../shared-references/candidate-schema.md) 的 items
- id = `sha256(trend|normalized_title|url_path)[:12]`——跨源同题去重靠这个
- 配置缺失 → 空列表 + stderr 说明，不抛异常
- cookie 类源：凭据放 `.oracle-secrets.json` / `.auth/`，绝不写进文档或 state

**新源接入**：按 custom-API.md 模板写一份 <name>.md 放本目录，`/oracle-trends — sources: <name>` 即可用。
