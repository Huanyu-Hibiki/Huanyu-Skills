---
name: oracle-retro
description: 按轨道 retro 窗口回收数据 + 复盘 + 把新观察写入 rubric_notes.md。校准循环的反馈环节——不复盘的预测等于占星。转化轨按 T+3/7/30 三窗口分阶段回收（评论/私信/付费加权）。触发词："复盘 [path]"/"retro this"/"T+3d 数据来了"/"抓数据 [path]"/"把这篇复盘了"。
argument-hint: "<prediction-file> [— window: 3|7|30] [— source: manual|adapter]"
allowed-tools: Bash(*), Read, Edit, Write, Glob, Grep, Skill
---

# /oracle-retro — 数据回收与复盘

按该轨 retro 窗口抓实际表现 → 对比预测 → 提炼新观察 → 写入 rubric_notes.md。**只追加 `## 复盘` 段，绝不改预测段**。

## Overview

```
[用户：复盘 <NNN>_<标题>]
  ↓
[Phase 0: 校验（immutability + 窗口 + 有效预测段 + published_at）]
  ↓
[Phase 1: 抓数据（manual / adapter；转化轨按窗口加权追问私信/付费）]
  ↓
[Phase 1.5: 限流排查 — 某平台实绩 < 中枢 50% 时先扫合规，再下 rubric 结论]
  ↓
[Phase 2: 实绩段 + 派生比率 + 互动率追踪 + top 评论聚类]
  ↓
[Phase 3: 验证/推翻预测各假设]
  ↓
[Phase 4: 提炼新观察（4a rubric / 4b pattern diff / 4c 双角度档案验证）]
  ↓
[Phase 5: 落盘（追加 ## 复盘 段 + brief/audit 验证段）]
  ↓
[Phase 6: 写入 rubric_notes.md + script_patterns.md]
  ↓
[Phase 7: 更新 state 分桶计数 + 检测 bump 候选 → 提议]
  ↓
[Phase 8: 内容资产提取（可选）]
```

## Constants

- **窗口按轨道**：从 state 的 `tracks.definitions[].retro_windows_days` 读（流量轨 [3]；转化轨 [3,7,30]）。`— window: N` 可显式指定补跑某窗口
- **DATA_SOURCE = manual** 默认（state.data_collection 可改 adapter）
- **TOP_COMMENTS_N = 20**
- **LIMIT_CHECK_THRESHOLD = 0.50** — 任一平台实绩 < 预测中枢 × 此值 → Phase 1.5 自动触发
- **转化轨加权**（窗口权重，只用于该轨 bump 分桶重打）：

| 维度 | T+3d | T+7d | T+30d |
|---|---|---|---|
| 评论关键词命中 | 1.0 | 1.5 | 2.0 |
| 私信触发 | N/A | 2.0（首次出现） | 3.0 |
| 付费转化 | N/A | N/A | 5.0（**转化轨成功的唯一真信号**） |

## Workflow

### Phase 0: 校验

1. 读 prediction 文件，确认存在
2. **识别有效预测段**：扫所有 `## 预测...` 段，取**最后一个 vN** 作校准依据（交叉题 v1_a/v1_b 都读，各算各的）；state.shoots 对应项的 `v2_prediction_written` 与文件实际不一致 → 警告（state 与文件脱节）
3. **immutability 缓存**：用**段位置 offset**（不是段内容 hash）缓存所有预测段——写完后按 offset 切片核对"原段内容字面一致"
   > 坑（实战）：非贪婪 regex 重新匹配会把新追加段切进旧段边界 → hash 必然不一致的假警报。offset 切片或关键指纹校验（grep 几个核心字符串仍在）才是对的
4. 校验 `Published at` → 缺失 → 优先走 oracle-publish 补登记；不可用 → 询问用户手动给（"不知道" → 用文件 mtime 近似 + 标 `published_at_unverified: true`）
5. **窗口校验**：按 per-platform 时间独立判定 `今天 - published_at >= 窗口`：
   - 转化轨按 due_windows 勾掉本次完成的窗口；还有未到期窗口 → 保留在 pending_retros
   - 不到 → 提示"还差 X 天"，用户坚持 → 标 `early_retro: true`（bump 时权重降级）
6. 已有复盘段 → 询问"补充还是修正？"——修正预测段 → **拒绝**

### Phase 1: 抓数据

#### Path A：manual（候补）

- 询问"粘贴这条作品的当前数据：播放/点赞/评论/转发/收藏"
- **top 评论分级制**：≥20 条 → 完整 retro；5-19 条 → 部分 retro；<5 条 → 标 `comments_unavailable` 降级 retro；0 条+平台状态变化（限流/申诉/封禁）→ 写"平台状态变化"段，不强行套模板
- 用户给不出评论 → **必须问原因**（adapter 失败/没到时间/评论区关闭/没空），记入复盘段
- 转化轨按窗口追问：T+7d 加"私信触发数 + 咨询意图词（'怎么用'/'多少钱'）"；T+30d 加"试用/付费转化数 + 私信样本（脱敏）"

#### Path B：adapter（自动）

**优先级顺序**：

1. **auto-collect（一键采集，推荐）**——`adapters/perf-data/auto-collect/`：
   ```bash
   cd <skill包>/adapters/perf-data/auto-collect
   python collect.py all --days 30        # 四平台连采（首次使用每平台先跑 --auth-only 本人扫码授权）
   ```
   产物 `.oracle-cache/collections/<ts>/unified.json`（统一 schema）→ 直接进本 Phase 的实绩段提取。采集后顺手存快照供 compass-retro 用：
   ```bash
   python tools/snapshot_store.py archive --db <项目根>/content-analytics.db --input <unified.json>
   ```
   按 prediction header 的 Platform 字段过滤该作品的数据行（`平台作品键` 前缀匹配）。
   **失败不阻塞**：授权过期 → 提示用户 `--auth-only` 重授权后重试一次；仍失败 → 降级下一条路径。
2. **平台手动导出文件**——用户从后台点"导出"拿到的 Excel 拖进来 → `python tools/data_normalizer.py --input <文件> --platform <平台>` 归一后同上消费。
3. **manual paste（兜底）**——问用户要数字。

任何 adapter 失败 → 优雅降级到 manual，标"adapter 因 X 不可用"，不阻塞。

#### 共同输出

- 定稿快照旁写 `report.md`（原始数据真相：数字 + top 评论全文；auto-collect 场景附 unified.json 路径引用）
- prediction 复盘段含**摘要**（关键比率 + 评论聚类 + 验证/推翻判定）——数据真相在 report，判断真相在 prediction
- **actual_data 字段统一写归一后的 schema**（`平台作品键` + 中文统一字段）——只有一种口径，根除 schema 漂移（bump 取数不再需要兼容多格式）

### Phase 1.5: 限流排查（归因前必跑）

任一平台实绩 < 中枢 × 50% → **先扫合规再下 rubric 结论**：
1. 扫定稿口播段（[oracle-compliance](../oracle-compliance/SKILL.md) 清单）：竞品平台名 / 站外导流 / 敏感词 / 绝对化用语
2. 发现 ≥1 高危 → 实绩段标 `platform_compliance: flagged`，该平台 rubric 结论降权（"可能是限流导致，非 composite 问题"）
3. 无论结果，rubric_notes 观察注明是否排查过限流

**为什么在 Phase 3 之前**：低播放先归因于内容 → 后来发现是限流 → 错误观察污染 rubric_notes。归因顺序错了，校准白做。

### Phase 2: 实绩段 + 评论分析

- 实绩数据 + **派生比率必算**（赞播比/评播比/藏播比/转播比——播放数永远暴露不了的信号）
- 互动率追踪表：本期 vs 历史（同轨全量派生基线）vs 目标，逐项 ✅/⚠️/❌
- 互动设计复盘（draft 有 `## 互动设计` 段时）：逐项验证触发器是否生效
- top 评论关键词聚类：分 3-5 类（高赞模因 / 概念引用 / 离题 / @朋友传播等），每类代表评论（带赞数）+ 比例
- 转化轨：按窗口权重表额外回收评论关键词/私信/付费三维度

### Phase 3: 验证/推翻

对预测文件的推理因素表、关键校准假设、反事实场景逐项判定（✅/❌）。**每条必须引用具体数据**（"分播比 2.53%"），不许写"基本符合"。实际落在的 bucket → 明确写出它测试了哪个 rubric 假设。

### Phase 4: 提炼新观察

#### 4a. Rubric 观察（→ rubric_notes.md 该轨节）

打分维度/公式/bucket 相关。每条**可追溯到具体数据点**。按题材/内容类型分分支记录（同轨不同题材可能是两条独立预测路径——单中枢强行平均会两头错）。

#### 4b. 写作 Pattern 观察（→ script_patterns.md，用户确认后才写）

Diff `scripts/<id>.md`（草稿）vs 定稿快照 → 找"改动且对流量有明显影响"的部分：
- 砍了某段 + 实绩≥中枢 → 验证冗余 → "用户改稿模式"表
- 加了钩子 + 超中枢 → 候选 Pattern N（标 ≥1 样本待验证）
- 定稿缺失（script_lost）→ 跳过 4b + 标"因未登记定稿跳过"

> rubric 进化 ≠ 写作进化——两个文件解耦：rubric 改了影响所有未来打分；pattern 改了影响所有未来 draft。

#### 4c. 双角度档案验证（brief/audit 存在时）

- audience-brief.md 存在 → 对照实绩验证：受众画像匹配？搜索流量占比？钩子判断？红旗真的拖累流量？
- open-source-audit.md 存在 → 验证：评论引用推理还是结论？"被推销感"还是真诚信号？
- 判定写进 brief/audit 末尾 **Retro 验证段**（诊断段 immutable，只追加验证段）
- 发现 rubric 盲区 → 候选观察（攒 ≥3 篇同类验证触发 bump）

### Phase 5: 落盘

Edit 追加三处：prediction 复盘段 + brief 验证段 + audit 验证段。

**Retro 段命名规则**（防同名段解析错乱）：

| 文件已有 | 新段名 |
|---|---|
| （无） | `## 复盘` |
| 已有 `## 复盘` (T+3d) | `## 复盘（补充 T+Nd）` |
| 已有多个 | `## 复盘（YYYY-MM-DD T+Nd retroactive）` |
| header 标 NOT FOR CALIBRATION | 段头强制 `**calibration_skipped**: true` |

**写完按 Phase 0 的 offset 缓存核对**——任一预测段字面变了 → 报错回滚。

### Phase 6: 写入 rubric_notes + script_patterns

- 6a：按 [observation-lifecycle.md](../../shared-references/observation-lifecycle.md) 观察记录模板追加到该轨 `## 观察记录`；检测跨样本 pattern（≥2 样本支持 → 升"重大跨样本观察"段）
- 6b：Phase 4b 用户确认的 pattern → script_patterns.md（"用户改稿模式"表 / "新发现的 Pattern"段）

### Phase 7: 更新 state + 检测 bump

```json
{
  "calibration_samples_by_track": { "<track>": +1 },
  "calibration_samples_total": <+1（cross 各 +0.5）>,
  "pending_retros": [<勾掉完成窗口；全窗口完成则移除>],
  "consecutive_directional_errors": { "<track>": [push "high"/"low"（偏差 >±25% 才 push）] },
  "last_retro_at": "<ISO>"
}
```

retroactive 路径（header 标 NOT FOR CALIBRATION）：计数不变 + `shoots[].calibration_status = "not_for_calibration"` + retroactive = true。

**bump 提议判断**（Claude 判断，非死门槛）：
- 默认参考：连续 ≥3 次同向偏差 → 提议 /oracle-bump
- 更早：1 次极端偏差（≥10x）或 2 次同向 + 评论区反向证据
- 更晚：3 次同向但幅度都 <25%（可能只是噪声）
- 提议时标注 default-aligned / judgment-driven

### Phase 8: 内容资产提取（可选）

从本期 draft 提取 1-3 个**可独立成立的观点**（离开原作品也看得懂、可继续展开）写入 `content-assets.md`：优先复盘数据支持的 + 评论被引用复述的。下游：oracle-seed 没想法时读它当选题素材。

## Key Rules

1. **预测段 immutable**。offset 缓存 + 写后核对是双保险
2. **数据来源必标注**（manual / adapter:<name>）
3. **观察可追溯**——每条引用具体数据点
4. **不在复盘里 bump**——Phase 7 只提议，升级走 /oracle-bump
5. **早复盘降级**——early_retro 样本在 bump 时权重降级

## Refusals

- 「把预测段的概率分布改一下，让复盘看起来更准」 → 拒绝。原则 #1
- 「跳过观察提炼，直接结束」 → 拒绝。观察是 rubric 进化的唯一燃料
- 「直接 bump，不要单独走 oracle-bump」 → 拒绝。retro 是触发器不是执行器

## 已知坑（压缩版）

| 坑 | 正解 |
|---|---|
| adapter 不可用就阻塞 | 降级 manual，标注原因，判断维度降级 |
| state 滞后（没跑 publish）→ 校验失败 | retro 内走 publish 补登记逻辑 |
| 多平台分日发 → 窗口算错 | per-platform 独立判窗口 |
| 同一钩子不同平台效果差数十倍 | 平台×内容交互是已知盲区——分平台记录，观察按平台分支 |
| 限流 confounding（低播放误归因内容） | Phase 1.5 在归因前必跑 |

## Integration

- 前置：oracle-publish 已登记 + 窗口到达
- 下游：consecutive_directional_errors 累积 → /oracle-bump 提议；每 2 期已复盘 → /oracle-compass-retro
- 与 [observation-lifecycle.md](../../shared-references/observation-lifecycle.md) 紧耦合：每次复盘是观察新增入口
