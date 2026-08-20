---
name: oracle-bump
description: 提议并执行 rubric 或 bucket 升级，按轨道独立执行。两种模式：**完整 rubric bump**（最高风险动作，5 步强制 + 跨模型审核）和 **--bucket-only 轻量重校**（只换 bucket 边界，不动公式）。触发词："升级 rubric"/"bump rubric"/"更新公式"/"我想加一个维度"/"调整权重"/"重校桶"/"recalibrate bucket"。
argument-hint: --propose "<...>" --track <id> | --bucket-only [--scheme ratio|absolute|percentile]
allowed-tools: Bash(*), Read, Write, Edit, Glob, Grep, Skill
---

# /oracle-bump — Rubric / Bucket 升级（按轨道）

两种模式：

| 模式 | 触发 | 做什么 | 验证强度 |
|---|---|---|---|
| **完整 rubric bump** | `--propose "<新公式>"` | 改公式/维度/权重 | 5 步 + 跨模型审核（强制） |
| **bucket-only 重校** | `--bucket-only` | 只重新派生 bucket 边界 | 数据自动派生，无审核 |

完整 bump 严格遵守 [bump-validation-protocol.md](../../shared-references/bump-validation-protocol.md)。**按轨道独立**：一次操作只 bump 一个轨道。

## Overview

```
入口：/oracle-bump
  ↓
[Phase A0: 模式分流]
  ├─ --bucket-only → [Phase B: 轻量重校]
  └─ --propose     → [Phase 0~8: 完整 bump]
```

## Constants

- **READINESS_HEURISTIC** — 默认：该轨校准池 ≥5 样本 + ≥1 个跨样本观察有 ≥3 样本支持；Claude 可基于强信号（≥3x 偏差反例 / 单点极强模因）提前，可因证据弱推迟。**提议必标注 default-aligned / judgment-driven**
- **THRESHOLD = 0.8** — 排序一致性阈值（4/5）。**写死**，统计刚性
- **CROSS_MODEL_AUDIT = true** — 跨模型独立审核默认开
- **REQUIRE_CONFIRM = true** — 落地前用户明确 "yes, bump"

## 完整 rubric bump 流程

### Phase 0: 前置门槛检查（按轨道）

| 检查 | 失败处理 |
|---|---|
| `in_progress_session == null` | 拒绝："有 in-progress 预测未完成，先走完或清掉" |
| `--track <id>` 指定（必填） | 漏了 → 询问"升级哪轨？"（列出 content-plan 轨道） |
| 该轨校准池 ≥5（默认）+ 上次 bump 后 ≥1 新样本 | 硬约束：无新样本拒绝；样本少软约束：显式标注后仍走全流程 |
| **诊断前置**：「本公式能否解决 retro 暴露的偏差？」 | 答案 no 或混合且核心偏差在 no 侧（如平台分发问题 rubric 修不了）→ **在 Phase 0 直接拒绝进 Phase 1**，省掉后面工作量 |

诊断证据先跑收敛工具（确定性重算，不靠记忆）：`python tools/score-curve.py <项目根> --track <id> --json` → 该轨偏差方向序列（连续高估/低估？）+ 平均绝对偏差 + bucket 命中率。「retro 暴露的偏差」以此数据交叉核对 state 的 consecutive_directional_errors——**公式修不了方向性系统偏差以外的命中问题**（bucket 命中低但方向随机 → 该跑 --bucket-only 而不是 rubric bump）。

校准池 = `state.calibration_samples_by_track[<track>]` 登记的该轨样本；cross 样本两轨各计 0.5。**一次只 bump 一轨**——`--propose` 跨轨公式 → 拒绝，按轨各算一次。

### Phase 1: 写出新公式完整方程

不能只接受简短描述，展开为完整方程（标轨道 + 版本号）：

```
[track: reach] 当前 v2  composite = (ER×1.5 + SR×1.5 + HP×1.5 + QL + NA + AB + SAT) / 8.5 × 2.0
[track: reach] 提议 v2.1 composite = (ER×2.0 + HP×1.5 + MS×1.5 + QL + SR + TS + SAT) / 9.0 × 2.0

变化总结：
- ER ×1.5 → ×2.0（升）/ SR ×1.5 → ×1.0（降）
- 新增 MS ×1.5、TS ×1.0 / 删除 NA、AB
- 归一化常数 8.5 → 9.0
```

含糊（"ER 权重提一点"）→ 询问具体数值，**禁止自己猜**。

### Phase 2: 该轨校准池全量重打分

Glob `<NNN>_*/predictions/*.md`，筛该轨（header Track 匹配）+ 有完整复盘段的文件。每篇：读各维度分 → 新公式重算 composite → 新增维度**回追打分**（读稿子/复盘证据打 0-5）。

**回追诚实要求**：看过实绩再回追会被污染（不可避免）→ 重打表明确标 `score_post_hoc: true`。

**解析兼容**：维度表格行可能带 markdown 加粗（`**ER**` vs `ER`）——解析正则允许 `**` 包夹。漏一个样本 = 排序一致性失真。

### Phase 3: 计算排序一致性

```
| 样本 | composite (v2) | composite (v2.1) | rank(new) | 实绩 | rank(actual) | delta |
```

- 一致性 < 0.8 或 pairwise 回归 → **本地拒绝，走 FAIL 终止协议**
- 实绩排序用该轨 success_metrics 的主指标

### Phase 3 FAIL 终止协议

**FAIL → 直接终止，不进 Phase 4**（跨模型审核是兜底 PASS 的，FAIL 拉外部审核浪费 token；阈值本身是元规则不归模型判定）。

**终止 ≠ 死胡同**，给用户 3 条替代路径：

| 路径 | 何时推荐 |
|---|---|
| 1. 改跑 `--bucket-only` | 校准池 ≥4 篇，bucket 边界本身过期（5 分钟，无门槛） |
| 2. 推迟 bump 等样本 | 提升 <20pp 或样本 <5（N<5 时 THRESHOLD 极难达标是统计噪声不是公式错） |
| 3. 记 v2 候选但 v1 保留 | 提升明显（>20pp）但绝对值仍 <0.8 → 候选标 disabled 留作下次起点 |

**诊断报告必含**：新旧一致率对比 + pairwise 回归数（FAIL 也显式报）+ 失败样本偏差成因（维度没捕获 vs 权重错配——用 `score-curve.py --track <id>` 的分样本偏差序列定位：偏差集中在特定 bucket / 特定维度缺失时）+「能否解决 retro 暴露的偏差」明确 yes/no。

**断点续跑**：写 `bump_in_progress` 状态（phase_completed / termination_reason / 双方公式 / 诊断），下次 session 读它跳过已完成 phase。

### Phase 4: 跨模型独立审核（强制，除非 escape hatch）

调用跨模型审核通道（用户配置的第二模型 / MCP 工具），打包：轨道 + 新旧公式 + 重打表 JSON + 排序对照 JSON。要求输出 **PASS/REJECT + ≥100 字理由 + 关键风险**。

- 本地 PASS + 外部 PASS → Phase 5
- 本地 PASS + 外部 REJECT → **视为 REJECT**（冲突 = 至少一方解读不稳定）
- 审核通道不可用 → 优雅降级 `CROSS_MODEL_AUDIT=false`，state 标 `last_bump_self_audited: true`（status 持续提示）。**该降级只在 Phase 3 PASS 后有效**

### Phase 5: 落地 + cleanup pass

REQUIRE_CONFIRM → 用户 "yes, bump" 后一次性完成：
1. rubric_notes.md 该轨节：更新版本号 + 版本速查表 + 完整升级 Memo（触发观察/证据/诊断/新公式/审核结论/已知局限）
2. 更新该轨"当前评分维度"段
3. **cleanup pass**（[observation-lifecycle.md](../../shared-references/observation-lifecycle.md)）：被吸收的观察删 / 被推翻的删 / 未解决的迁"待验证假设" / 已验证规律迁"规律沉淀区"
4. 重读全文，60 秒内能理解当下规则

### Phase 6: 校准样本批量追加

每个该轨校准样本的 prediction 文件**底部追加**（不动预测/复盘段）：

```markdown
---
**Re-scored under v2.1 on 2026-05-04**: composite=8.24 → 9.11
```

### Phase 7: 更新 state

```json
{
  "tracks.definitions[<track>].rubric_version": "v2.1",
  "last_bump_at": { "<track>": "<ISO>" },
  "last_bump_self_audited": false,
  "consecutive_directional_errors": { "<track>": [] },
  "calibration_samples_at_last_bump": { "<track>": <N> }
}
```

清空该轨偏差队列——新 rubric 重新计数。

### Phase 8: 控制台报告

版本变化 + 校准池重打结果 + 审核结论 + cleanup 摘要 + "下一篇预测起按新公式打分"。

---

## Phase B：bucket-only 重校（轻量分支）

bucket 边界是**数据派生量**不是规则——重新派生不需要审核（确定性算法无判断成分）。

### B1: 选算法（按样本数自动派生，不持久化 scheme）

| 算法 | 默认适用 | 派生方式 |
|---|---|---|
| `ratio` | N=1-4 | 最近 3 篇实绩中位数 × {0.3/1/3/10/30} |
| `absolute` | N=5-9 | 校准池中位数 × 同上 |
| `percentile` | N≥10 | 实绩 percentile {30/60/85/95/100} |

`--scheme` 显式覆盖（percentile 要求 N≥3）。

### B2: 派生新边界

读该轨（或全池，流量轨主指标）所有实绩样本。**数据抽取必须确定性**：字段名可能漂移（actual_plays / totals.views / actual_total）——写明确的抽取函数兼容多 schema，或先跑校验列出每篇的实绩值让用户确认。**启发式 grep 单一字段会把 7 篇样本误判成 1 篇**。

### B3: 报告变化 + 用户确认

```
当前 scheme: ratio → proposed: absolute
baseline: 4.2w 中位数（基于 5 篇样本）
新边界：底部 <1.3w / 基础盘 1.3-4.2w / 命中 4.2-12.6w / 爆款 12.6-42w / 现象级 >42w
确认应用？(yes / no)
```

### B4: 落地

1. rubric_notes.md bucket 段替换新表 + 顶部追加变更记录行
2. state 更新 `baseline_plays` + 追加 `bucket_recalibration_history[]`（date/scheme/baseline/sample_count/trigger/old_baseline——status 可显示"上次重校 N 天前"）
3. **不动任何 prediction 文件**——历史 bucket 标签是预测时语义，事后改写破坏盲度

## Key Rules

1. **5 步不可跳**（完整 bump）；"先简化跑一下" → 拒绝
2. **THRESHOLD 写死**；降阈值通过 = 诚实的 self-deception → 拒绝
3. **跨模型审核默认开**；关闭需 state 显式标记
4. **cleanup 是 bump 的一部分**；"下次再清" → 拒绝
5. **REQUIRE_CONFIRM 两种模式都要**
6. **bucket 重校不动历史预测**
7. **Phase 3 FAIL = 终止**，走终止协议 3 条路径

## Refusals

- 「跳过校准池重打，直接换公式」 → 拒绝。原则 #2
- 「跳过外部审核」 → 仅当显式设置
- 「THRESHOLD 调到 3/5 让它过」 → 拒绝。改阈值是元层级 bump
- 「保留所有旧观察作为历史」 → 违反原则 #3
- 「一次 bump 两轨」 → 拒绝。按轨独立，各算一次

## Integration

- 上游：oracle-retro 检测该轨 ≥3 同向偏差（或强单点信号）→ 提议
- 修改：rubric_notes.md（该轨节，结构性）+ 该轨所有 prediction 文件（追加 Re-scored 行）+ state
- 下游：下一篇 oracle-predict 自动按该轨新版本打分
