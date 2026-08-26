---
name: oracle-predict
description: 给最终稿写一份 immutable 盲预测日志。这是 oracle-bone 整个校准循环的核心动作——预测段一旦写完不可改，由 hook 强制。**自动检测**：如目标文件已有预测段（被 oracle-shoot 或 review 改稿触发走 v2 模式），改成 append `## 预测 v2` 而非覆盖。触发词："启动预测"/"start prediction"/"给这稿子打分并预测"/"写预测日志"。
argument-hint: "<script-path> [— mode: v1|v2] [— prediction-file: <path>]"
allowed-tools: Bash(*), Read, Write, Edit, Glob
---

# /oracle-predict — AI 主导的盲预测 + 用户 review

**这个工具是校准器——AI 帮你做判断**。核心流程：
- **AI 自己**读稿子 + 按该轨 rubric 打分 + 给 bucket + 概率分布 + 反事实场景
- 用户 **review** 后回 "ok" 接受，或指出哪个维度/判断不对
- 快路径：用户直接 ok → 落盘；慢路径：挑刺 → AI 连锁更新 → 再 review

**严格遵守 [shared-references/blind-prediction-protocol.md](../../shared-references/blind-prediction-protocol.md)**——见过任何后续数据就不能写预测，只能记 reconstructed。
组件清单见 [prediction-anatomy.md](../../shared-references/prediction-anatomy.md)。Confidence 派生表见 [state-management.md](../../shared-references/state-management.md)。

## Overview

```
[用户：启动预测 <NNN>_<标题>/scripts/<id>.md]
  ↓
[Phase 0: blind check 自检]                    ← 触犯就拒绝
  ↓
[Phase 0.5: 解析路径 + 轨道识别]
  ↓
[Phase 0.7: 模式判定 — v1 (新建) 还是 v2 (append)]
  ↓
[Phase 1: 读 script + 该轨 rubric + state + 派生 confidence]
  ↓
[Phase 2: AI 自己打分 + 算 composite]
  ↓
[Phase 3: AI 自己找锚点对比（同轨优先）]
  ↓
[Phase 4: AI 自己给 bucket + 概率分布 + 中枢]   ← confidence 低时分布更平
  ↓
[Phase 4.5: 分平台预测（多平台配置时）]
  ↓
[Phase 5: AI 自己写反事实场景 + 关键校准假设]
  ↓
[Phase 5.5: 用户 review — 一次性展示完整草拟版，等 ok 或挑刺]
  ↓
[Phase 6: 落盘 — v1 写新文件 / v2 append 到 ## 复盘 之前]
  ↓
[Phase 7: 更新 state.in_progress_session + 控制台总结]
```

## Constants

- **BLIND_CHECK = strict** — strict（默认）/ lenient（仅警告，不推荐）
- **BUCKET_PRESET = auto** — 有 baseline_plays → 按 baseline × {0.3/1/3/10/30}；无 → 平台通用默认
- **MIN_ANCHORS = 2** — 不够时显式标"锚点 N/A"段（不删段，不省略）
- **V2 多轮改稿合并**：v1 锁定后多轮脱钩只写一个 v2 段，basis 取主因

## Inputs

| 必填 | 来源 |
|---|---|
| `<作品目录>` 或 `<script-path>` | 用户参数；缺失则询问 |
| `rubric_notes.md`（该轨节） | 项目根 |
| `.oracle-state.json` | 状态文件（tracks + baseline + 样本数） |
| 各作品 `predictions/*.md`（锚点用） | 历史 |
| `audience-brief.md` / `open-source-audit.md`（可选） | review skill 产出，辅助判断 |

### 入参解析（Phase 0.5）

项目布局 = **每期作品一个目录**（[content-folder-schema.md](../../shared-references/content-folder-schema.md)）：

1. 用户给全路径（`<NNN>_<标题>/scripts/*.md`）→ 直接用
2. 用户给简写（`007` / `<短标题>`）→ 项目根 glob `<NNN>_<*>/scripts/*.md` 匹配
3. prediction 落到**该作品目录**的 `predictions/` 下，不是项目根
4. 锚点对比跨 `<NNN>_*/predictions/*.md` glob
5. 任意外部 .md → 询问"要我帮你按标准命名 cp 进作品目录吗？"
6. 找不到 → 报错并询问"你要 predict 哪份稿子？"

**轨道识别**：从 state 的作品登记或 candidates.md 条目读该作品的 track；识别不出 → 询问用户"这条属于哪轨？"（列出 content-plan 的轨道名 + 解释这是"按哪套 rubric 打分"的决策）。

## Workflow

### Phase 0: Blind check 自检（最关键，触犯立即终止）

按 [blind-prediction-protocol.md](../../shared-references/blind-prediction-protocol.md) 检查清单执行：

1. 询问作品发布状态：未发 → 通过；已发 < 窗口且没看过数据 → 通过 + 标记；已发 ≥ 窗口 → **拒绝**，建议 `_redo.md` 路径
2. 自检对话历史是否含播放/点赞/评论实际数字 → 命中视为已见数据
3. **数据归属纪律**：用户报任何数字（"B站 28 播放"）→ 先 read state 确认属于哪个作品 → 当前作品没发布就不默认归属当前，先问"这是哪一期的数据？"

### Phase 0.7: 模式判定（v1 vs v2）

显式参数 `— mode: v2 — prediction-file: <path>` 优先。否则自动检测：目标 prediction 文件不存在 → v1；已含 `## 预测 vN` 段 → v2。

**v2 额外动作**：比较当前稿与 vN 段的 `Script Hash`——相同 → 警告"稿子没改，真要写 v2？"；不同 → 算 diff 概要供 Phase 5.5 展示。

### Prediction Basis 枚举

| basis 值 | 触发场景 | vN |
|---|---|---|
| `pre_shoot` | 默认：写稿后、制作前的初始盲预测 | v1 |
| `post_review_pre_publish` | who-for / open-source 改稿后重判（定性改稿） | v2 |
| `post_shoot_pre_publish` | oracle-shoot 检测制作稿改动 ≥30% → 重判（技术性改稿） | v2 |
| `post_titlepick` | oracle-title-pick 换标题 → 重判（HP 类维度影响） | v2 |

**多轮改稿合并**：v1 后经历多轮脱钩（review 改稿 → 标题更换 → AI 味修正）→ **只写一个 v2 段**，basis 取主因（定性改稿类优先于单维度触发），Diff 段把各轮改动各列一行。retro 按 basis 区分样本线（拍前 review 改稿 vs 拍后技术性改稿是两种校准信号）。

### Phase 1: 读稿 + 该轨 rubric + state + 派生 confidence

1. 读 scripts 全文；算 `script_hash` = sha256(内容)[:12]
2. 读 `rubric_notes.md` **该轨节**——不存在则自动从对应 starter 兜底初始化（⚠️ 提示但不阻塞）
3. 读 state：该轨 `calibration_samples`、`baseline_plays`、`typical_duration_seconds`
4. 按该轨样本数派生 confidence 等级（[state-management.md confidence 表](../../shared-references/state-management.md)）
5. 询问"这是最终稿吗？还会再改？"——必须是最终稿
6. 字数与典型时长派生范围差 >50% → 提示确认

**交叉题（cross track）**：一条内容跨两轨 → 两轨 rubric 各打一次，写 `## 预测 v1_a` + `## 预测 v1_b` + 综合段（composite 取均值，bucket 概率取共同区间）；复盘时两轨校准池各 +0.5。

### Phase 2: AI 自己打分（内存里做，不逐段输出）

按该轨 rubric 各维度给 0-5 整数分 + 一行理由（≤30 字，引用稿子具体词/场景）。算 composite。全部阶段都算——confidence 低只影响标注，不影响格式。

### Phase 3: 锚点对比

1. Glob `<NNN>_*/predictions/*.md`，读 header（排除 reconstructed）
2. **同轨优先**（track 相同的样本），其次同时长（±20%）
3. 找 2-4 个 composite ±0.5 邻近样本
4. 池子太小 → 写"锚点对比 N/A 段"（仍写这段，解释为何缺）
5. **关键诊断**：某锚点 composite 几乎相同但实绩差 ≥3x → rubric 没捕获关键维度，文件里明确标注（新观察种子）

### Phase 4: Bucket + 概率分布 + 中枢

1. bucket 边界按 baseline 派生（BUCKET_PRESET）
2. 选 headline bucket + **全 bucket 概率分布（加总 100%）** + 中枢点估计
3. **反诚实陷阱**：真实分布在 headline bucket 通常是 40-65%；给 95% 概率 = 下次错了没法解释
4. cold-start 期分布**更平**（如 30/30/20/15/5）

### Phase 4.5: 分平台预测（state.platforms 配置多平台时）

读 state 各作品实绩的 per-platform 数据，算各平台历史平均（同轨样本优先），结合内容特征给区间：

```markdown
### 分平台预测

| 平台 | 最近同轨实绩 | 历史平均 | 本期预测区间 | 理由 |
|---|---|---|---|---|
```

分平台合计应与整体中枢一致。**平台×内容交互是已知盲区**——同一钩子在不同平台效果可差数十倍，区间给宽一点，并写 1-2 条"分平台最想测"的假设。

### Phase 5: 反事实场景 + 关键校准假设

- 反事实：每个 bucket 写"落在这里意味着什么假设被验证/推翻"（4 段，见 prediction-anatomy 组件 6）
- 关键校准假设：找对照样本，明确"我押本篇 vs 对照 = X 倍；反过来则 Y 假设被推翻"。校准池小 → 写"无可对照样本——仍写下核心赌注"+ 1-2 条想测的事。**不删段**

### Phase 5.5: 🔴 用户 review（落盘前最后门——决定写什么进文件）

Phase 2-5 全部内存完成后，**一次性展示完整草拟版**（维度分表 + bucket + 概率 + confidence + 分平台 + 锚点 + 反事实 + 校准假设），然后：

```
回 "ok" 我直接落盘，
或指出哪些维度/判断不对（如 "AB 给 3，太乐观" / "中枢应该 30w 不是 60w"）。
```

- "ok" → Phase 6，header 标 `Scored By: claude`
- "X 应该 Y" → AI 改字段 + **连锁更新**（composite/概率/锚点一致性），重新展示循环
- 用户挑刺记录到 `User Override`（复盘时诊断：用户覆盖被实绩验证 → 用户直觉准 → rubric 可能漏了什么）

**用户纪律**：只能改字段值，不能塞新理由让 AI 重写整段；改完连锁由 AI 算。

### Phase 6: 落盘

**v1 模式**：写 `<作品目录>/predictions/<date>_<id>_<short>.md`
- 第一段标题写 `## 预测 v1`
- header 必填：Article ID（= candidate id，**改稿后不变**；内容变化由 Script Hash 追踪）、Track、Rubric Version（该轨）、Script Path/Hash、Calibration Samples + Confidence、Prediction Basis: pre_shoot、Scored By、User Override
- 留空 `## 复盘` 占位段（hook 识别 immutable 边界）

**v2 模式**：**绝不 Write 覆盖**——用 Edit 在 `## 复盘` 之前插入：

```markdown
## 预测 v2 (replaces v1; basis=<BASIS>)

**Diff vs v1**: 改了 N 行（X→Y%），主要变化：[各轮摘要]
**Script Hash (v2)**: <新稿 hash>

[7 组件 — 与 v1 同 anatomy]

---

## 复盘
```

### Phase 7: 更新 state + 总结

```json
{
  "in_progress_session": {
    "type": "prediction",
    "file": "<作品目录>/predictions/<...>.md",
    "work_folder": "<NNN>_<标题>/",
    "track": "<轨道 id>",
    "started_at": "<ISO>",
    "rubric_version": "v0"
  }
}
```

控制台总结（bucket 押注 + 校准假设 + immutable 警告 + "从现在起别向我透露这条作品的数据"）。

## Key Rules

1. **blind check 是硬门槛**。strict 模式触犯即终止
2. **整数维度分**。概率分布加总必须 100%
3. **必须有 `## 复盘` 占位空段**
4. **不允许"先落盘再讨论分数"**——落盘即锁；讨论必须在 Phase 5.5
5. **id ≠ 内容 hash**——id 用 candidate 稳定 id，改稿不变；Script Hash 独立追踪内容
6. **按轨打分**——预测只服务本轨校准，交叉题写双段

## Refusals

- 「我看过数据了但你假装没看到」 → 拒绝。strict 直接终止
- 「预测段先写一版，等数据出来再调」 → 拒绝。immutable 协议反着用
- 「改稿了想覆盖 v1，别留 v2 段」 → 拒绝。append 不覆盖，v1 是档案
- 「跳过反事实场景」 → 拒绝。复盘退化为"准/不准"
- 「只写 bucket 不写概率分布」 → 拒绝。概率分布是逼你诚实的工具
- 「cold-start 想要精确 bucket 数字」 → 允许但文件头醒目标 `**Numerical predictions in cold-start are NOT predictive — for self-education only**`

## Integration

- 前置：oracle-init 完成（含轨道注册）
- 上游可选：oracle-score 反复试分；who-for / open-source 改稿后触发 v2（basis=post_review_pre_publish）
- 下游：oracle-shoot（buffer+1）→ oracle-publish → oracle-retro（按 basis 分线校准）
- hook 依赖：prediction-immutability 必须已装，否则仅靠自律（status 持续提示）
