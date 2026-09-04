---
name: oracle-trends
description: 从配置的热点源抓取热门话题，去重 + 粗打分 + 分轨写入 candidates.md。**绝大部分人没有候选池——这是让"我没素材"问题在初始化后就消失的钥匙**。触发词："抓热点"/"fetch trends"/"今天有什么可做的"/"trending now"/"找选题素材"。
argument-hint: "[— sources: <comma-separated>] [— max-per: 20]"
allowed-tools: Bash(*), Read, Write, Edit, Glob, WebFetch, Skill
---

# /oracle-trends — 热点抓取

多 adapter 模式：读各 trend-sources adapter 输出 → 去重 → 粗打分 → 分轨写入 `candidates.md`。

## Overview

```
[Phase 0: 读 state 拿 enabled adapters]
  ↓
[Phase 1-2: 逐 adapter fetch + normalize 到 candidate-schema]
  ↓
[Phase 3: 去重（vs candidates / predictions / trends-history）]
  ↓
[Phase 4: 粗打分（inline 复用 score 逻辑，按轨道）]
  ↓
[Phase 5: 排序 + 询问用户哪些入池]
  ↓
[Phase 6: 落盘 + 更新 trends-history.jsonl]
```

## Constants

- **LOOKBACK_HOURS = 24** / **MAX_PER_SOURCE = 20**
- **AUTO_SCORE = true** — 抓回后自动粗打分
- **MIN_COMPOSITE_TO_SUGGEST = 6.0** — 低于不推荐入池（仍写 history 防重复推）

## Workflow

### Phase 0: 读启用的 adapters

`args.sources or state.enabled_trend_sources（默认 ["manual-paste"]）`。为空 → 输出引导（临时跑用 `— sources:`；永久改 state 数组）。

**adapter 一览**（文档在 `adapters/trend-sources/`——文档化：依赖/fetch 接口/输出 schema/失败模式/稳定性星级；**未文档化的 adapter 跑前需现场确认端点可用性，失败按优雅降级 skip**）：

| Adapter | 机制 | 依赖 | 文档 |
|---|---|---|---|
| `manual-paste` | 用户粘贴 URL/标题列表 → WebFetch 拓展 snippet | 无（永远能用，兜底） | ✅ |
| `hackernews` | HN Algolia API | 无 key | ✅ |
| `reddit-rising` | 公开 .json 端点 | 无 key | ❌ 待文档化——现场验证 |
| `youtube-trending` | YouTube Data API | API key | ❌ 待文档化——现场验证 |
| `bilibili-popular` | B 站 popular 接口 | 无（部分端点需登录态） | ✅ |
| `xhs-explore` / `douyin-hot` | 平台接口 | cookie（缺则 skip） | ❌ 待文档化——现场验证；反爬严，参考 `adapters/script-extraction/README.md` 五平台策略 |
| `thirdparty-paid` | 新榜/飞瓜等 | 用户自接 | ✅（`custom-API.md` 模板） |
| `audience-feedback` | **从自己受众反馈找选题**：已发作品评论区高赞/追问 + 私信咨询 + 粉丝群高频问题 → 提取"用户追问/抱怨/困惑"生成候选 | 无 | ✅ |

### Phase 1-2: fetch + normalize

对每个 adapter 按其文档调 fetch → 输出符合 [candidate-schema.md](../../shared-references/candidate-schema.md) 的 items。

**优雅降级**：单 adapter 失败（key 缺失 / 端点 503 / cookie 失效）→ skip 该 adapter **不抛异常**，汇总里说明（✅ 拉到 N 条 / ⚠️ 跳过+原因 / ❌ 失败+原因）。

### Phase 3: 去重

按 candidate-schema 去重协议：算 id → 查 candidates.md / 各作品 predictions / `.oracle-cache/trends-history.jsonl`（rejected 且 6 个月内）→ 命中跳过。统计写汇总。

### Phase 4: 粗打分（按轨道）

对每条新 item：
1. **初步分轨**：按 item 主题与各轨 content-plan 定义匹配 → 用**该轨 rubric** 打分（转化轨候选用 conversion rubric，破圈轨用 opinion rubric）
2. 分不出来的 → 用默认轨 rubric + `track: null`（后续 seed 分流时补）
3. 算 composite + 一句 rationale

**粗打分 ≠ 正式预测**：基于 snapshot 的"值不值得展开写"粗筛，预测必须基于最终稿重新打。

### Phase 5: 排序 + 🔴 入池确认（CHECKPOINT——写入 candidates.md 前用户拍板）

```
🔥 抓热点完成。
- hackernews: 18 条 / bilibili-popular: 15 条 / ⚠️ douyin-hot 跳过（缺 cookie）
去重后 27 条新。粗打分后 12 条 ≥6.0：

| # | 标题 | source | 轨道 | composite | rationale |
|---|---|---|---|---|---|
| 1 | ... | hackernews | 破圈轨 | 8.4 | ER+QL 双 5，普适 |
...

哪些入池？全部 "all" / 选几个 "1,3,5" / 都不要 "none"（记 history 防重推）
```

### Phase 6: 落盘

1. 选中 items → candidate-schema Markdown 格式追加 candidates.md（composite 标 `rough, snapshot-based`）
2. 所有抓回 items（含未选中）→ append `.oracle-cache/trends-history.jsonl`
3. state 更新 `last_trends_run_at` / `last_trends_added_count`

### 全部 adapter 失败的降级协议

所有启用源都拉不到（断网 / 全部 503 / cookie 全失效）→ **明示不可用，不拿缓存旧热点冒充新热点**，并转入常青路径：

1. 报告："⚠️ 当前所有热点源不可用（原因列表）。热点是时效资产，不降级用旧数据。"
2. 常青替代：读 `candidates.md` 已有未消化候选（read_status=shallow 的升 deep）+ `audience-feedback` 历史沉淀的未答追问 → 提议常青选题
3. 提示排查指引（key / cookie / 网络），下次再试热点

**禁止**：把 `trends-history.jsonl` 里 6 个月内的旧条目当"今天的热点"重新推荐——时效性是热点候选的核心属性，过期即失效。

## Key Rules

1. **不抛异常**。单 adapter 失败 skip + 报告；全失败走降级协议（上节）
2. **manual-paste 永远在**——兜底
3. **去重是硬约束**
4. **粗打分诚实标注**，防与 prediction 精打分混淆
5. **不进 predictions/**——trends 只产 candidates
6. **不冒充时效**——旧热点不翻新，全失败转常青

## Refusals

- 「跳过去重全写进去」 → 拒绝。污染候选池，recommend 排序失效
- 「跳过粗打分直接写 raw 标题」 → 允许（AUTO_SCORE=false）但提示后续需打分才能进 recommend 池

## Integration

- 上游：state.enabled_trend_sources 配置
- 下游：oracle-recommend 直接读 candidates.md；audience-feedback adapter 依赖 oracle-retro 沉淀的实绩数据
- oracle-status 显示"上次抓热点 X 天前"
