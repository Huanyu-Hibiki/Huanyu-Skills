# Adapters 开发指南（HOWTO）

oracle-bone 的数据源适配层。四类 adapter，每份文档必须写清五件事：**依赖 / fetch 接口 / 输出 schema / 失败模式 / 稳定性星级**。

## 四类 adapter

| 类型 | 目录 | 被谁调用 | 输出 |
|---|---|---|---|
| trend-sources | `trend-sources/` | /oracle-trends | 符合 [candidate-schema](../../shared-references/candidate-schema.md) 的 items |
| perf-data | `perf-data/` | /oracle-retro (Path B) | report.md（数字 + top 评论） |
| candidate-pool | `candidate-pool/` | /oracle-recommend | 候选 items |
| script-extraction | `script-extraction/` | /oracle-learn-from (Way b) / /oracle-apprentice | transcript.md |

## 通用契约

1. **fetch() → items**：实际是 markdown 文档描述的协议（AI 按文档执行），或附带脚本
2. **输出符合对应 schema**：adapter 不输出"光秃秃的 url"——自己负责把 url/摘要拓展成可读 snapshot_text
3. **优雅降级**：配置缺失（API key / cookie）→ 返回空列表 + stderr 写明原因，**不抛异常**
4. **凭据不入库**：cookie / key 放 `.env` 或 `.oracle-secrets.json`（已 gitignore），不写进 adapter 文档或 state
5. **去重责任在调用方**（oracle-trends/recommend 按 id 去重），但 adapter 要保证同源输出稳定 id

## 新增一个 trend-source（示例结构）

```markdown
# <name>

- 依赖：<无 key / API key / cookie>
- 稳定性：★★★☆☆
- fetch：curl <endpoint> → jq 提取 title/url/snippet
- 输出：逐条 normalize 到 candidate-schema（id = sha256(trend|normalized_title|url_path)[:12]）
- 失败模式：<429 限流 → 退避重试 1 次 → skip；cookie 失效 → skip + 提示>
```

启用：临时跑 `/oracle-trends — sources: <name>`；永久启用改 `.oracle-state.json` 的 `enabled_trend_sources`。

## 已内置 / 推荐清单

见各子目录 README。社区贡献的 adapter 按同样结构放进来即可。
