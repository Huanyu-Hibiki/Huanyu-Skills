---
name: oracle-trends
description: 从配置的热点源抓取热门话题——归一化去重 + 旧闻回流剔除 + 信源分层粗打分 + 分轨写入 candidates.md，输出覆盖账本让"今天没料"可审计。**绝大部分人没有候选池——这是让"我没素材"问题在初始化后就消失的钥匙**。触发词："抓热点"/"fetch trends"/"今天有什么可做的"/"trending now"/"找选题素材"。
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

### Phase 0: 读启用的 adapters + 运行前预检

`args.sources or state.enabled_trend_sources（默认 ["manual-paste"]）`。为空 → 输出引导（临时跑用 `— sources:`；永久改 state 数组）。

**预检（Phase 0 就做，别等运行时炸）**：逐 enabled adapter 按其文档「依赖」列自检（API key 在不在 / cookie 能否取到 / 网络依赖），输出三态健康表——✅ 可跑 / ⚠️ 能跑但降级（如无 key 用免 key 版）/ ❌ 跳过（skipped-unconfigured，附缺什么 + 一句修法）。❌ 的不进本轮 fetch，汇总里如实声明「本轮没查这些源」，**不许事后把没跑说成"查了没货"**。

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

**信封四态（每 adapter 的结果必须归入其一——借鉴 union-search / last30days 的健康语义）**：

| 状态 | 语义 | 汇总里怎么说 |
|---|---|---|
| ✅ has_results | 查到货 | "拉到 N 条" |
| ⚠️ no-results | **查了但确实没货**（唯一允许说"该源今天没热点"的状态） | "该源无新内容（结论有效）" |
| ❌ failed | 限流 / 掉认证 / 超时 / 解析失败——**覆盖不完全**，不得说"没热点" | "该源故障（<原因>），本轮未覆盖" |
| ⏭️ skipped-unconfigured | Phase 0 预检就缺依赖 | "未配置，<缺什么>" |

单 adapter 失败 skip **不抛异常**；全失败走下方降级协议。

### Phase 3: 去重（归一化键 + 旧闻回流检测）

**先归一化再比对**（两道键）：
- **链接键**：剥掉 `utm_*` / `gclid` / `fbclid` 等跟踪参数 → scheme/host 小写 → 去尾斜杠 → 再比对；短链先解跳转再归一
- **标题键**：空白归一 + casefold（"XX发布新模型"和"xx 发布 新模型"算同一条）

然后按 candidate-schema 去重协议：算 id → 查 candidates.md / 各作品 predictions / `.oracle-cache/trends-history.jsonl`（rejected 且 6 个月内）→ 命中跳过。

**旧闻回流检测（第五态 recirculation）**：跨平台二次爆发的旧热点是高发误报源——不同站点不同标题讲**同一底层事件**（实体 + 变化类型相同，如"同一融资/同一发布/同一政策"）不算新信号。检测：归一化键未命中、但与 history / 池内已有条目**同实体同事件类型** → 记入 trends-history（台账），**不进本轮新候选数**；若原候选仍在池内，给原条目附注"二次发酵中"（REVISION 式信号，对持续热度有用）。判定拿不准 → 当新候选入池但在 note 标"疑似旧闻回流"。

统计写汇总（多源重叠率一般 20-30%，属正常）。

### Phase 4: 粗打分（按轨道）

解析与打分纪律按 [shared-references/scoring-procedure.md](../../shared-references/scoring-procedure.md) §1-§3（粗打分定位差异见 §4）。对每条新 item：
1. **初步分轨**：按 item 主题与各轨 content-plan 定义匹配 → 用**该轨 rubric** 打分（转化轨候选用 conversion rubric，破圈轨用 opinion rubric）
2. 分不出来的 → 用默认轨 rubric + `track: null`（后续 seed 分流时补）
3. 算 composite + 一句 rationale；composite 标注 `rough, snapshot-based`

**粗打分 ≠ 正式预测**：基于 snapshot 的"值不值得展开写"粗筛，预测必须基于最终稿重新打。

**热度修正（与 composite 正交，展示 + 排序平手裁决用，不合并进 composite）**：

- **计龄口径**：优先用 `event_at`（事件发生时间）——旧事件新发稿按发布时间算会虚高；无 event_at 用发布时间并在时效列标注"按发布口径"；两者都无法确立 → 新鲜度 unknown，热度标 N/A 不猜、入池候选降档展示
- `热度 = 互动量 × 1/√(事件距现在小时数 + 1)`；事件 <24h 再 ×1.2（首日加成）
- 同一事件多源命中（去重前）→ 佐证乘数 ×(1 + 0.15 × (源数 − 1))，汇总标注"多源佐证"
- 互动量取 adapter 返回的点赞/评论等归一数值（无互动数据的源 → 热度标 N/A，不猜）
- 用途：composite 相近（±0.3）的热点间按热度 tiebreak；输出附**时效列**——最早事件 <24h 标「刚起」、<7d 标「上升期」、更早标「常温」。rubric composite 管"内容质量预测"，热度管"话题时效"，两把尺分开亮，防热度绑架质量分

**信源层级门（source_tier A-E，见 candidate-schema）**：

- **E 层（聚合号/SEO 摘要）单源候选不入池**——只能做线索：顺手查有没有 A-D 层源讲同一事件，有 → 合并进那条并标佐证；没有 → 弃（记 history 防重推）
- D 层（社区讨论）单源可入池但推荐时降档（见 recommend 稳分位证据门）
- adapter 文档标注各自默认 source_tier（见 `adapters/trend-sources/README.md` 层级表）

### Phase 5: 排序 + 🔴 入池确认（CHECKPOINT——写入 candidates.md 前用户拍板）

**覆盖账本**（先于候选表展示——"今天没料"要可审计，不注水凑条数）：

```
📋 覆盖账本
| 源 | 状态 | 最新验证到的变化 / none | 缺口 |
|---|---|---|---|
| hackernews | ✅ 有货 | <主题>：<一句话> | — |
| bilibili-popular | ⚠️ 无新内容 | none（结论有效） | — |
| douyin-hot | ❌ 故障 | 未覆盖 | cookie 失效，--auth-only 重登 |
| xhs-explore | ⏭️ 未配置 | 未覆盖 | 缺 cookie |
```

然后输出候选表：

```
🔥 抓热点完成。
- hackernews: 18 条 / bilibili-popular: 15 条 / ⚠️ douyin-hot 跳过（缺 cookie）
去重后 27 条新（剔除旧闻回流 3 条）。粗打分后 12 条 ≥6.0：

| # | 标题 | source | 轨道 | composite | 热度/时效 | rationale |
|---|---|---|---|---|---|---|
| 1 | ... | hackernews | 破圈轨 | 8.4 | 87·刚起 | ER+QL 双 5，普适 |
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
7. **四态信封**——只有 no-results 才能说"该源没货"；failed/skipped 必须声明"本轮未覆盖该源"（Phase 0 预检 + Phase 1-2 信封）
8. **热度与质量分正交**——velocity 只做展示与平手裁决，不合并进 composite
9. **旧闻回流不是新信号**——同底层事件（实体+事件类型）的跨站新稿计台账不进新候选数
10. **E 层单源不入池**——聚合号/SEO 摘要只做线索；计龄优先 event_at，无则标注发布口径，都不立就 unknown 不猜

## Refusals

- 「跳过去重全写进去」 → 拒绝。污染候选池，recommend 排序失效
- 「跳过粗打分直接写 raw 标题」 → 允许（AUTO_SCORE=false）但提示后续需打分才能进 recommend 池

## Integration

- 上游：state.enabled_trend_sources 配置
- 下游：oracle-recommend 直接读 candidates.md；audience-feedback adapter 依赖 oracle-retro 沉淀的实绩数据
- oracle-status 显示"上次抓热点 X 天前"
