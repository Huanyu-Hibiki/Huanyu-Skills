---
name: oracle-recommend
description: 从 candidates.md 按各轨 rubric 排序推荐 top N 选题，**按 content-plan 占比过滤 + 1 稳分 + 1 实验性策略**，每条带 composite + rationale + 锚点对比。candidates 不存在时给引导而非报错。触发词："推荐选题"/"next topic"/"下一篇做什么"/"挑一个选题"。
argument-hint: "[— top: N] [— track: <id>] [— filter: tier1|all|safe|risky]"
allowed-tools: Read, Glob, Grep
---

# /oracle-recommend — 候选池排序推荐

读 candidates.md → 按轨道分组 → 按占比过滤 → 排序 → 输出 top N + 评分细节 + 锚点 + 理由。

## Overview

```
[Phase 0: candidates 存在性检查（缺→引导不报错）]
  ↓
[Phase 1: 解析 candidates]
  ↓
[Phase 2: 通用过滤（已发/已拒/未打分/tier）]
  ↓
[Phase 2.5: Buffer 颜色覆盖（最高优先级）]
  ↓
[Phase 3: 按轨道占比过滤 + 排序 + 选 1 稳 + 1 实验 + 锚点]
  ↓
[Phase 4: 输出]
```

## Constants

- **TOP_N = 5**
- **STRATEGY = stable+experimental** — 推 ≥2 时 1 稳分 + 1 实验性（[cadence-protocol.md](../../shared-references/cadence-protocol.md)）
- **REQUIRE_SCORED = true** — 只推已打分的
- **DUPLICATE_CATEGORY_LOOKBACK** = max(3, cadence_days × 3) 天内已发同类目不推

## Workflow

### Phase 0: 存在性检查

candidates.md 不存在或空 → **不报错**，输出引导：

```
你目前没有候选池。四个建立方式，挑一个：

1. 🌱 [推荐] "找选题" → /oracle-seed（对话式挖你自己的经历，一次一个）
2. 🔥 [日常] "抓热点" → /oracle-trends（多源抓取+打分入池）
3. ✍️ 手动把候选标题贴进 candidates.md，我自动粗打分
4. 📋 受众反馈选题：/oracle-trends 用 audience-feedback 源（从已发作品评论区/私信找追问）

也可以跳过候选池直接给我具体稿子"启动预测"。

> seed = 从你自己身上挖（初始）；trends = 从外部抓（日常补充）
```

### Phase 1: 解析

按 candidate-schema Markdown 格式解析每个 H3 entry（id/title/tier/track/composite/dimension_scores/note）。格式被手改过 → 询问 schema，**不静默忽略不识别条目**。

### Phase 2: 通用过滤

1. 排除已发布（扫 predictions header 的 id 集合）
2. 排除 tier=skip
3. 排除 composite=null（**推没读过的素材是占星**）
4. filter 参数：tier1 / all / safe（排 risky）/ risky（只看风险议题）

### Phase 2.5: Buffer 颜色覆盖（最高优先级）

读 state.shoots + cadence 算颜色：

| 颜色 | 策略 |
|---|---|
| 🔴 红 | **只推 top 1 稳分**，不推实验性（"今天必须拍出来"） |
| 🟠 橙 | 1 稳 + 1 实验，提示优先稳分 |
| 🟢 绿 | 标准 1+1 |
| 🔵 蓝 | **拒绝推荐**："buffer 已 N 条，先发存货+复盘。坚持要拍说'我就要拍'" |
| 灵活模式 | 不覆盖，标准策略 |

### Phase 3: 按轨道占比过滤 + 排序

1. 读 `state.tracks.definitions` 的 mix_ratio
2. 候选按 track 分池（cross 条目进两池；track=null 用 ratio 兜底分配）
3. 各池目标数 = round(TOP_N × 该轨 ratio)
4. **补稀优先**：某轨最近发布占比明显低于 mix_ratio → 该池目标数 +1（从占比高的池借）
5. 各池按 composite 降序取目标数，合并

#### 第 1 条（稳分）

composite 降序 + 排除 risky + 排除近 N 天同类目 → top 1。

#### 第 2 条（实验性）

找：维度组合与最近已发样本**差异最大**（增加校准信息量）/ 含明确 pattern 假设（"新维度 A/B 对照"）/ 用户主动愿试的 risky。composite 不一定 top 但有**信息价值**。没有合适的 → "池里没有明显实验性样本，给你 2 条稳分"。

#### 锚点

每条找 1-2 个 composite 接近的**已发布**同轨作品（从 predictions 读），优先同时长（±20%）。

### Phase 4: 输出

```
🎯 候选池推荐（buffer: 🟢 绿 / cadence: 隔日更 / 占比计划: 破圈40+转化60）

📌 第 1 条 — 稳分（推荐立即做）：
  **[tier1] [9.18] "为你好"高密体系** [破圈轨]
   - 维度：ER=5 HP=5 QL=4 NA=4 AB=5 SR=5 SAT=4
   - rationale：ER+SR 双 5，普适且分享安全
   - 锚点：EP03（composite 9.41，实绩 124w）同走"框架+具象"路线
   - 风险：议题厚重，别连发两篇同款

🧪 第 2 条 — 实验性（验证特定假设）：
  **[tier1] [8.71] 哈哈长度** [破圈轨]
   - 测试目标：候选维度 MS=5 vs EP05 同 ER/HP 但 MS 低 3 → A/B 对照
   - 信息价值：拍这条能强证据/弱推翻下一次 bump

（备选）3. ... [转化轨] / 4. ... / 5. ...

下一步：
- 选 1 稳 + 1 实验 → 各写稿 → "启动预测"
- 只做 1 条 → 选稳分（buffer 越红越该选稳分）
- 都不满意 → "过滤改 all" 或 "抓热点"
```

**每条必有**：维度评分（让用户能挑战打分）+ 锚点（ground 抽象数字）+ rationale（理解推荐逻辑）。**不允许只输出 composite 排序**——那是黑箱。

## Key Rules

1. **不报错给引导**——candidates 缺失是默认状态
2. **不推未打分的**
3. **必带锚点 + rationale**
4. **按占比分池**——混池推荐会让强轨越来越强、弱轨饿死
5. **去重 published**

## Refusals

- 「直接给我 composite 最高的，不用解释」 → 拒绝。展示评分+锚点是发现"打错"的唯一机会
- 「把所有 entry 重新打分」 → 路由 /oracle-score 单条；批量重打是 /oracle-bump 的一部分
- 「按预测桶排不要按 composite」 → 询问理由（bucket 是 composite 离散化；真要按期望值排需乘平均实绩，那是另一个维度）

## Integration

- 上游：oracle-trends 入池
- 下游：用户挑一条 → /oracle-seed 细化或直接写稿 → /oracle-predict（粗 composite 不进 prediction，重新打）
- oracle-status 显示池规模与分轨统计
