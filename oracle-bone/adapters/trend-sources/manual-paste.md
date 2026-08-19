# manual-paste — 手动粘贴源（默认，永远可用）

- **依赖**：无
- **稳定性**：★★★★★（唯一保证永远能用的兜底）
- **fetch 接口**：

```
/oracle-trends — sources: manual-paste

流程：
1. AI 问用户："粘贴你今天的候选 URL/标题列表（每行一条）"
2. 对每个 URL 做 WebFetch 拓展 snippet（标题行无 URL 则跳过拓展）
3. 逐条 normalize
```

- **输出**：`source = "paste:manual"` 的 items，其余字段按 candidate-schema
- **失败模式**：URL 拓展失败（403/超时）→ 保留标题行 + `snapshot_text = "(无法拓展，仅标题)"`，不丢弃
- **何时用**：所有自动源都失败时；用户自己刷到素材想入库时
