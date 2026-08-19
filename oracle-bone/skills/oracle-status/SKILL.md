---
name: oracle-status
description: oracle-bone 的状态看板。分轨显示校准进度 / confidence / 待复盘 / buffer / 轨道占比执行情况 / 该不该 bump / 该不该清算。**任何时候都可调，无副作用（只读）**。触发词："状态"/"看板"/"status"/"我现在该做什么"/"进度怎么样"。
allowed-tools: Bash(*), Read, Glob, Grep
---

# /oracle-status — 状态看板

读 state + 扫项目 → 汇总进度 → 输出"今天该做什么"清单。**读多写零**。

## Overview

```
[用户：状态]
  ↓
[Phase 1: 读 state + 扫文件系统]
  ↓
[Phase 2: 计算派生指标（分轨）]
  ↓
[Phase 3: 检测建议触发器（按优先级）]
  ↓
[Phase 4: 输出看板]
```

## Constants

- **SQLITE_UPGRADE_THRESHOLD = 30** — 总校准样本 ≥N 建议升 SQLite
- **CLEANUP_LINE_THRESHOLD = 600** — rubric_notes.md 行数超 N 建议清算
- **STALE_PREDICTION_DAYS = 30** — in-progress 超 N 天未发布提示清理
- **COMPASS_RETRO_EVERY = 2** — 每 N 期已复盘作品提示罗盘复盘

## Inputs

| 来源 | 用途 |
|---|---|
| `.oracle-state.json` | 主状态（tracks / buffer / pending_retros） |
| `<NNN>_*/predictions/*.md` | 校准样本数核验 |
| `candidates.md` | 候选池规模 |
| `rubric_notes.md` | 行数 / 各轨版本 |
| `.oracle-cache/usage.jsonl`（如有） | 使用频率 |

## Workflow

### Phase 1: 读状态

```python
state = read_json('.oracle-state.json')
if not state:
    return "你还没初始化。请先跑 /oracle-init。"
```

### Phase 2: 派生指标（分轨）

| 指标 | 算法 |
|---|---|
| **Buffer 数 / 颜色** | `len(state.shoots)`；颜色按 [cadence-protocol.md](../../shared-references/cadence-protocol.md)（cadence=null → 颜色禁用） |
| **各轨样本数 + confidence** | `calibration_samples_by_track` → 按轨派生 emoji 等级（[state-management.md](../../shared-references/state-management.md) confidence 表） |
| **总样本数可信度** | 扫 shoots 中 `calibration_status == "not_for_calibration"` / `retroactive == true` 的数量 → 有效数 = 总数 - retroactive 数，显示时附注 |
| **最早一拍至今天数** | `now - shoots[0].shot_at` → "拍了 N 天没发"警告 |
| **待复盘（分轨分窗口）** | pending_retros 展开 due_windows：已过 due_at 且未 done 的 |
| **轨道占比执行情况** | 最近 N 期（默认 5）已发布作品的 track 分布 vs mix_ratio → "破圈轨 40% 计划 / 最近 5 期实际 20%——该补稀轨" |
| 池大小 | candidates.md 中 tier != skip 的条数（分轨统计） |
| 同向偏差队列 | consecutive_directional_errors（分轨） |
| in_progress 陈旧度 | now - in_progress_session.started_at |

### Phase 3: 检测建议触发器（按优先级）

1. **Buffer 🔴 红** → 第一行警戒："buffer 0/1 篇，断更风险——今天必须拍/发。说'推荐选题'只推 top 1 稳分"
2. **Buffer 🔵 蓝** → "积压 N 篇，暂停制作，先发存货 + 复盘"
3. **shoots 最早一项 > 14 天** → "有作品拍了 N 天没发——时效流失风险"
4. **in_progress 陈旧 ≥ 30 天** → "清理或 publish（是忘登记还是弃稿？）"
5. **待复盘 ≥1（按 due_at 最近排序）** → "今天该复盘 X 篇"（转化轨显示是哪个窗口 T+3d/T+7d/T+30d）
6. **轨道占比偏离**（某轨连续 3 期低于 mix_ratio 的一半）→ "该轨按计划该发了——下次'推荐选题'我会优先补稀轨"
7. **bump 信号（分轨，Claude 判断）**：默认 ≥3 同向；可提前（1 次极端偏差 / 2 次+评论反向证据）；可推迟（幅度都 <25%）→ 提议时标注 default-aligned / judgment-driven
8. **confidence 升级跨档**（0→1 / 2→3 / 5→6 / 10→11 / 20→21）→ "🎉 <轨> confidence 升级"（仅通知）
9. **某轨样本跨 5** → "该轨 rubric 可第一次正式 bump 了"
10. **总样本跨 10** → "可跑 /oracle-bump --bucket-only --scheme percentile"
11. **总样本 ≥30 且 data_layer=markdown** → 建议升 SQLite
12. **rubric_notes 行数 > 600** → 建议清算观察段
13. **已复盘作品数达 COMPASS_RETRO_EVERY 倍数** → "罗盘复盘到期：/oracle-compass-retro（账号级诊断 + 规划修订候选）"
14. **hooks_installed=false** → "immutability 是君子协定，建议补装"
15. **last_bump_self_audited=true** → "上次 bump 是自审，建议配置跨模型审核通道"
16. **rubric_form_mismatch=true** → "形态与 starter 不完全匹配，下次 bump 建议调权重"
17. **benchmark_status=pending** → "答应找的对标账号还没找——跑 /oracle-learn-from"
18. **benchmark 影响淡出判断**（该轨样本 ≥10 且与 benchmark pattern 出现 ≥3 条不一致）→ "你的真实数据已成主信号"（通知不 gate，benchmark 保留作 sanity check）
19. **retroactive 残留 ≥20%** → "总样本中 N 条 retroactive 不计校准，bump 触发只看有效数"
20. **mix_ratio 之和 ≠ 1.0 / tracks 定义异常** → 报警等用户拍板修正

### Phase 4: 输出看板

```
🎛️ oracle-bone 状态（更新于 2026-08-19 15:00）

内容形态：opinion-video / 时长 3-5min / cadence: 隔日更
规划：双轨 — 破圈 40% + 转化 60%

📊 分轨校准
  破圈轨   rubric v2 · 样本 12 · 🟢 中（中枢 ±25%）
  转化轨   rubric v1 · 样本 6  · 🟡 偏低（±40%）
  （总样本 18，其中 1 条 retroactive 不计）

📦 Buffer：3 篇（🟢 绿）· 按你的 cadence = 6 天，节奏稳定

🎬 待办（按紧急度）
  🚨 复盘 1 篇（转化轨 T+7d 窗口到期）→ "复盘 006_获客案例"
  ⚠️  破圈轨同向偏差 3 次（high）→ 建议 /oracle-bump --track 破圈轨
  💤 in-progress 陈旧 35 天 → 已发忘登记？还是弃稿？

⚖️ 占比执行：最近 5 期 破圈 20% / 转化 80%（计划 40/60）→ 该补破圈轨

🔥 候选池：27 条（tier1: 12 / tier2: 9 / tier3: 6）· 距上次抓热点 4 天

📈 健康度
  rubric_notes.md: 412 行（健康）· hooks ✅ · 跨模型审核 ❌（未配置）

下一步建议（按优先级）：
1. /oracle-retro（006 获客案例 T+7d）
2. /oracle-bump --propose "..." --track 破圈轨
3. "推荐选题"（会优先补破圈轨）
```

输出风格：**直白、具体、可复制执行**——每个建议附确切命令。

## Key Rules

1. **无副作用**。读多写零；状态修改是其他 skill 的事
2. **不假装数据可用**。字段缺失 → 显式标"未知"，不猜
3. **建议带优先级**。按紧急度排，不同时堆 10 条
4. **每个建议附命令**。不能只说"该 bump 了"
5. **分轨呈现**。混池显示会掩盖单轨问题

## Refusals

- 「顺便帮我自动跑一下 retro」 → 拒绝。status 只读，一次操作只做一件事
- 「不想看行数/健康度，太琐碎」 → 折叠到底部"健康度"区，不移除——出问题前可见

## Integration

- 上游：所有 skill 完成时更新 state，status 是这些更新的可视化
- 下游：每个建议路由到具体子 skill
- SessionStart hook 调本 skill 渲染 4-6 行开场报告
