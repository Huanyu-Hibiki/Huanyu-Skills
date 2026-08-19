# trend-sources — 热点抓取源

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
