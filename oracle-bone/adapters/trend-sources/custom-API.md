# custom-API — 第三方数据服务接入模板

新榜 / 飞瓜 / 蝉妈妈等付费数据服务，或任何带 API 的热点源。**复制本模板为 `<name>.md` 填写**：

---

# <adapter 名>

- **依赖**：`<API key / token，放 .oracle-secrets.json 的哪个字段>`
- **稳定性**：`<★ 1-5>`
- **计费提示**：`<免费额度 / 按次计费——标注每次调用的成本，防用户无意烧钱>`
- **fetch 接口**：

```bash
curl -s "<endpoint>" -H "Authorization: Bearer ${KEY}"
# 响应结构：<贴一段示例 JSON>
# 提取字段：<哪个字段是标题/热度/链接>
```

- **输出**：`source = "trend:<name>"`；snapshot_text = <服务给的热度值 + 标题 + 摘要>
- **失败模式**：
  - 401/403 → key 失效，skip + 提示重新配置
  - 429 → <退避策略>
  - 余额不足 → skip + 明确提示（不静默）

---

## 已知注意事项

- **凭据纪律**：key 只放 `.oracle-secrets.json`（gitignore 已含）或环境变量；adapter 文档里只写字段名不写值
- **输出契约**：必须符合 [candidate-schema](../../shared-references/candidate-schema.md)——id 归一化规则同其他源（source_type 都是 `trend`，跨源同题自动去重）
- **付费源建议**：粗打分前的 `MIN_COMPOSITE_TO_SUGGEST` 过滤尤其重要——付费源拉得多，别把候选池灌爆
