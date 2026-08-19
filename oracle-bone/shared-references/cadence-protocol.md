# Cadence Protocol（节奏协议）

被这些子 skill 引用：`oracle-status`、`oracle-recommend`、`oracle-shoot`、`oracle-publish`、SessionStart hook。

固化"哪天该做什么"——避免用户驱动每一步。让 AI 在会话开场就能回答"我现在该拍 / 该发 / 该复盘"。

---

## 三层节奏

### 日级（每天 / 每次会话开场）

1. SessionStart hook 自动渲染 4-6 行报告：
   - 📦 Buffer 状态（颜色 + 数量）
   - ⏰ 待复盘到期项（按各轨窗口）
   - 🎯 候选池 top 3（粗排，按占比过滤）
   - 📅 上次抓热点时间
   - ⚠️ 关键 to-do
2. 不主动开始任何动作——等用户决定

### 事件级（T+retro 窗口到期）

- 任何已发未复盘 + 时间到 → SessionStart 顶部高亮
- 用户给数据（粘 / URL）→ `/oracle-retro` 自动跑
- 转化类轨道按 [3, 7, 30] 多窗口分阶段回收

### 周级（用户决定的"集中处理日"）

- 抓热点（`/oracle-trends`）刷新候选池
- 检查 rubric bump 触发条件（分轨检查）
- 清理 rubric_notes.md 是否需要清算

---

## Buffer 警戒规则

**Buffer = `state.shoots` 数组长度** = 已拍但未发布的作品数。

`/oracle-shoot` 把作品加进 `state.shoots`，`/oracle-publish` 移除——两个事件分开使 buffer 跟踪准确。

### 颜色阈值（按 `target_publish_cadence_days` 派生）

`buffer_days = buffer_count × target_publish_cadence_days`

| buffer_days | 颜色 | 含义 | 行动 |
|---|---|---|---|
| < 1 | 🔴 **红** | 警戒——下个发布日可能断更 | **今天必须拍**，且只拍稳分（top 1，不冒险） |
| 1-2 | 🟠 橙 | 偏低 | 应该拍 1-2 条 |
| 3-5 | 🟢 绿 | 正常 | 节奏稳定，可以拍可以休 |
| > 5 | 🔵 蓝 | 积压 | **暂停拍摄**，全力发布存货 + 复盘 |

**示例**：
- 用户 cadence = 1（日更），buffer count = 0 → buffer_days = 0 → 🔴
- 用户 cadence = 7（周更），buffer count = 1 → buffer_days = 7 → 🔵（一篇够发七天）
- 用户 cadence = 1，buffer count = 4 → buffer_days = 4 → 🟢

### 灵活节奏（target_publish_cadence_days = null）

用户在 oracle-init 选"灵活/不固定" → buffer 监控**关闭**。SessionStart 报告只显示"已拍未发：N 条"，不显示颜色，不警戒。

---

## 选题策略（`/oracle-recommend` 推 ≥ 2 个时）

每次推荐 2 条时遵循 **1 稳分 + 1 实验性** 原则，并**先按 content-plan 占比过滤**（哪轨稀了补哪轨）：

### 第 1 条（稳分）

- 排序 top 1-3
- 类目与最近 N 条已发**不重复**（N = max(3, target_publish_cadence_days × 3)，避免审美疲劳）
- composite 高 + 议题安全（非 risky）

### 第 2 条（实验性）

- 候选池里能验证某个**待验证假设**的样本（如新维度的 A/B 对照）
- 或验证某个**新 pattern**（script_patterns.md 的 Pattern N）
- composite 不一定 top，但有"信息价值"——复盘后能让 rubric / pattern 库前进

### Buffer 颜色对推荐的覆盖

| Buffer 颜色 | 推荐策略覆盖 |
|---|---|
| 🔴 红 | **只推稳分 top 1**——不推实验性。"今天能拍出来就行" |
| 🟠 橙 | 1 稳 + 1 实验，但建议优先拍稳分 |
| 🟢 绿 | 标准 1+1 |
| 🔵 蓝 | **暂停推荐**——回 "你 buffer 积压了，先发存货 + 复盘" |

**关键约束**（任何颜色都遵守）：
- 同一 category 连发 ≤ 2 条
- 已发过的 candidate（标 done）不推
- 用户主动跳过的 candidate（标 skip）6 个月内不推

---

## 节奏元规则

按优先级（高→低）：

1. **Buffer 优先于评分**：红色警戒时不要因为"等更好的选题"而断更——拍 composite 7.5 的稳分比"等明天的 9.0"安全
2. **复盘优先于新拍**：retro 窗口到期当天**先复盘再考虑拍新的**——否则数据信号丢失，rubric 校准受损
3. **同步优先于积压**：buffer 满（蓝色）时不要再拍，先发掉再说——已拍议题的时效性会衰减
4. **实验性最多 1/天**：每天拍 2 条时至少 1 条是稳分。**不要全实验**——冷启动期实验失败率太高，伤校准节奏

---

## 标准化"今日工作流"模板

### 情况 1：buffer 充足 + 没到复盘窗口

```
SessionStart 报告 → user 决定拍/不拍
├─ 拍 → "推荐选题" → oracle-recommend 按占比推 2 个 →
│       user 选 → /oracle-seed 写 draft (cold-start) 或 user 自己写 →
│       user 改写 → 定稿 → user 拍 → "拍了" → oracle-shoot
└─ 不拍 → 等
```

### 情况 2：buffer 充足 + 到复盘窗口

```
SessionStart 报告含 ⏰ 复盘提醒 → user 给 URL 或粘数据 →
oracle-retro 自动跑 → 写复盘段 → 检查 bump 触发条件（分轨）
├─ 触发 → 提议 /oracle-bump（不强制，用户决定）
└─ 未触发 → 等下个验证样本
```

### 情况 3：buffer 红色警戒

```
🔴 SessionStart 第一行警戒 → user 决定
├─ 拍 → oracle-recommend 只推当前 top 1 稳分 → 立即拍
└─ 接受断更风险 → user 自负，oracle-status 持续提示
```

### 情况 4：buffer 蓝色积压

```
🔵 SessionStart 报告"积压" → user 决定
├─ 发 → "已发布 https://..." → oracle-publish → buffer -1
├─ 复盘 → 见情况 2
└─ 拍新 → oracle-recommend 拒绝："你 buffer 已 N 条，先发掉 ≤3 条再来"
```

### 情况 5：周期性集中处理日（用户主动触发）

```
user 说"抓热点" → oracle-trends → 候选池更新
+ user 说"看看 rubric 是不是该升了" → oracle-status 分轨检查同向偏差累计
+ user 说"看看 rubric_notes 行数" → oracle-status 健康度检查
```

---

## 兜底：流程偏离时

如果某天违反节奏（buffer=0 但用户强行不拍 / 积压 ≥10 但用户继续拍），SessionStart 报告**显式标注**：

```
❌ 你已 N 天没发新内容（最后一次发布：YYYY-MM-DD），
   buffer = 0，你的账号目前处于"事实断更"状态
```

或：

```
❌ 你 buffer 已 N 条但还在新拍，
   过去 N 条里有 N 条已超过 X 天未发——存在时效性流失风险
```

**不会自动尝试补救**——只显式报告，由 user 决定如何回到节奏。

---

## 子 skill 责任表

| Skill | 节奏责任 |
|---|---|
| `/oracle-init` | 问 cadence；写 `target_publish_cadence_days`；装 SessionStart hook |
| `/oracle-shoot` | 把作品加 state.shoots，buffer +1 |
| `/oracle-publish` | 从 state.shoots 移除对应项，buffer -1 |
| `/oracle-status` | 计算 buffer + 颜色，输出报告（分轨） |
| `/oracle-recommend` | 按 buffer 颜色 + 占比 + 选题策略给推荐 |
| `/oracle-retro` | 复盘后更新状态（自动 trigger /oracle-status） |
| SessionStart hook | 调 /oracle-status 渲染 4-6 行报告，写到 STATUS.md |
