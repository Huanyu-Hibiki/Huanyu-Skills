# hackernews — HN 前页热门

- **依赖**：无 key
- **稳定性**：★★★★☆（Algolia API 稳定）
- **fetch 接口**：

```bash
curl -s "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=20"
# 提取每条: title / url / points（热度参考）/ num_comments
```

- **输出**：`source = "trend:hackernews"`；snapshot_text = title + points + top comment 摘要（再请求一次 item API 可得，可选）
- **失败模式**：429 → 等 5s 重试 1 次 → skip；JSON 异常 → skip + stderr 报告
- **适配提示**：英文源——title 保留原文（id 归一化已做 lowercase）；中文创作者用它挖科技向选题时 AI 在粗打分阶段自行翻译理解
