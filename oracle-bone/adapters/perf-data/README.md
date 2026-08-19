# perf-data — 复盘数据源

/oracle-retro Path B / oracle-compass-retro Phase 1 自动采集用。

## 通用契约

- 输入：作品 URL / 平台内容 ID（prediction header 的 Platform ID 字段）
- 输出：`report.md` 写到作品目录（完整原始数据 + top 评论全文）——**数据真相在 report，判断真相在 prediction 复盘段**
- 失败 → **优雅降级 manual**（"adapter 因 X 不可用，改用 manual 模式"），绝不阻塞 retro
- 凭据（cookie/token）放 `.auth/` 或 `.oracle-secrets.json`
- **统一归一**：所有来源的数据过 `tools/data_normalizer.py`（四平台字段别名映射 / "1.2万"多值解析 / 跳出率口径标注 / 零值过滤）——actual_data 只有一种 schema

## 内置方案

| 方案 | 位置 | 说明 |
|---|---|---|
| **auto-collect（推荐）** | `auto-collect/` | Playwright 一键采集四平台（监听后台 API + DOM 兜底，复用本机浏览器 Profile）。首次每平台 `--auth-only` 本人扫码；日常 `python collect.py all --days 30`。**设计参考 data-scientist-community（AGPL-3.0）思路，clean-room 重写**；平台改版后跑 `--debug` 校准选择器 |
| 手动导出导入 | `tools/data_normalizer.py` | 用户后台点"导出"拿 Excel → `python data_normalizer.py --input <文件>` 归一。零依赖零风险，auto-collect 的降级路径 |
| manual paste | —（内置） | 永远可用的兜底：问用户要数字 |

## 数据管线（auto-collect 全流程）

```
collect.py（Playwright 采集）
  → unified.json（data_normalizer 归一：别名/口径/零值）
  → snapshot_store.py archive（SQLite run 快照：content-analytics.db）
  → dashboard.py（diff + 五维提取 + quantile 规则建议）
  → oracle-retro Phase 1 / oracle-compass-retro Phase 1-2 消费
```

## 新平台接入

按 [../HOWTO.md](../HOWTO.md) 五要素写 `<platform>/README.md` + 脚本。注意各平台反爬政策差异大——**优先官方 API / 官方后台导出**，脚本化抓取要有频率节制。
