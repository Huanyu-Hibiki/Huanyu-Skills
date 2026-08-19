# Prediction Anatomy（预测日志解剖）

被这些子 skill 引用：`oracle-predict`、`oracle-retro`、`templates/prediction.template.md`。

**所有预测都用统一格式**——7 个必备组件 + 复盘段。Confidence 等级（基于该轨道 `calibration_samples` 派生，见 [state-management.md](state-management.md) 的 confidence 表）作为 header 字段标注，告诉用户这次预测有多可信，**但不改变预测格式本身**。

> **为什么不分 cold-start 简化版 / complete 完整版（旧设计的弃疑）**：
> 把 cold-start 切成简化版是基于"前 5 篇 bucket 数字是 false precision"的担忧。但更好的解决方案是**显示 confidence 等级**——天气预报永远报具体温度，再标置信度，不会因为预报员经验少就不给数字。
> 双版本切换还引入了"第 5 篇突然解锁完整版"的复杂度跃迁——用户体验割裂。统一格式 + 渐进信心标注更平滑。

---

## 7 个必备组件

### 组件 1：File header（文件头）

```markdown
# <标题> — 预测日志

**Article ID**: <12 位 hash>  (sha256 of scripts/<id>.md initial content, 取前 12)
**Title**: <作品完整标题>
**Track**: <轨道 id>   ← state.tracks.definitions 之一（如 reach / convert）；交叉题写 cross:<t1>+<t2>
**Rubric Version**: **v0** | **v1** | **v2** | ...（该轨道节版本）
**预测时间**: 2026-05-04（基于最终稿）
**Script Path**: <NNN>_<标题>/scripts/<date>_<id>_<short>.md
**Script Hash**: <sha256:12 of script content at predict time>
**Target Duration (s)**: 240  (state.typical_duration_seconds 派生)
**Actual Script Length**: 980 字  (从 Script Path 文件读)
**Calibration Samples (at predict time)**: 3   ← 该轨道样本数
**Confidence**: 🟡 偏低 (中枢 ±40%，可作为参考之一)
**Scored By**: claude  ← 或 `claude+user_override`
**User Override**: none  ← 或列出被覆盖字段
**预测时数据状态**: **blind**（未看任何平台实际数据）
**Prediction Basis**: pre_shoot   ← 见下方"Prediction Basis 字段"
```

字段必填规则：
- `Track` 必填——复盘按轨道分桶校准，bump 按轨道独立重打
- `Rubric Version` 必填——将来 v3 时代回看 v2 预测，没有版本号就无法公平对比
- `预测时数据状态` 必填——明确声明 blind 是 immutable 承诺的前提
- `Script Path` 必填——指向 `scripts/<id>.md`（pre-production 草稿）
- `Script Hash` 必填——oracle-shoot 时再 hash 定稿，不一致 → 复盘段加 integrity warning
- `Calibration Samples` + `Confidence` 必填——告诉读者这次预测有多可信。**Confidence 自动派生**自该轨道 calibration_samples（见 state-management.md）
- `Scored By` 必填——告诉读者这次预测是 AI 全自动还是用户介入改过：
  - `claude`：AI 主动打分 + bucket + 概率，用户 review 后接受
  - `claude+user_override`：用户在 review 阶段挑刺改了某些字段
- `User Override` 必填（如有覆盖）——列出哪些字段从 X 改成 Y，附用户给的理由。复盘时这个字段帮诊断：用户的覆盖被实绩验证（用户直觉准）→ rubric 可能漏了什么

---

### 组件 2：输入快照（Input snapshot）

记录**预测时**的稿子状态——尤其是用户的最终改动。

```markdown
## 输入快照

**分数 (vN)**: ER5 / HP5 / QL5 / NA3 / AB5 / SR2 / SAT4 → composite=**8.24**

**用户改写要点 vs AI 草稿（如有）**:
- **开头**：user 砍掉模型名和铺垫
- **砍掉**：[具体段落 / 概念名 / 铺垫]
- **保留**：[关键的金句 / 致谢段 / 主体结构]
- **节奏**：比草稿 [紧 / 松] 约 N%
```

> 如果是用户从零写的（没用 oracle-seed），这一段写"用户原创稿，无 AI 草稿对照"。

---

### 组件 3：预测主体（Prediction）⭐ immutable 段

这是 immutable 段的核心。`hooks/prediction-immutability` 拦截这段往后到下一个 `##` 的所有 Edit。

```markdown
## 预测 v1

**Bucket**: `30-100w`

**内心概率分布**:
- `<5w` → 3%
- `5-30w` → 22%
- **`<headline bucket>` → 55%**（中枢 ~50w）
- `>100w` → 17%
- `>150w` → 3%

**一句话 reason**:
> ER=5+AB=5 普适受众；钩子直接锁定；SR=2 无议题托底是天花板瓶颈；预计 40-60w 中枢。
```

强制要求：
- **Bucket** 必须是预定义的 5 个之一
- **概率分布** 必须加起来 100%——这是逼你诚实的工具
- **中枢** 是该 bucket 内的点估计，便于复盘判断"偏高 / 偏低"
- **一句话 reason** 浓缩到 DB 字段，便于跨样本检索

**关于 cold-start 期的 bucket**：calibration_samples 少 → 概率分布**应该更平**（如 30/30/20/15/5 而非 5/40/45/8/2）。Confidence 低不代表跳过 bucket，而代表对 bucket 该有合适的不确定度。

**交叉题（cross track）**：一条内容跨两轨时，写两份预测段 `## 预测 v1_a`（按轨道 A rubric）和 `## 预测 v1_b`（按轨道 B rubric）+ 综合判断段。复盘时两轨校准池各 +0.5。

---

### 组件 4：推理因素表（Reasoning factors）

每个驱动判断的因素 + 方向 + 置信度 + 说明。

```markdown
## 推理因素

| 因素 | 方向 | 置信度 | 说明 |
|---|---|---|---|
| ER=5 | 强 + | 高 | 极端具象的场景描写 |
| 钩子 | 强 + | 高 | "仅影响 X 的人"一句锁定受众 |
| SR=2 | 强 - | 高 | 无议题托底，纯个人向天花板有限 |
| 数据+金句路线 | 中 ? | 低 | 对算法友好度未验证 |
```

**置信度** 分三档：高（强证据 + 多锚点支持）、中（有理由但样本少）、低（凭直觉）。
- 复盘时如果"低置信度"因素被验证 → 直觉强
- 如果"高置信度"因素被推翻 → rubric 有 bug

---

### 组件 5：锚点对比（Anchor comparison）

找 2-4 个 composite 接近的旧样本（同轨道优先），列出它们的实绩。

```markdown
## 锚点对比

| 对照样本 | composite | 实绩 | 异同 |
|---|---|---|---|
| 样本甲 | 9.41 | ~150w | composite 低 1.17，但路线差异大 |
| 样本乙 | 9.41 | 259w | SR 差 3 分（2 vs 5） |
| 样本丙 | 8.24 | T+8d 11.7w | 同 composite 但 ER 5 vs 3 |
```

锚点的价值：抓出公式抓不到的错误。

**校准样本不够时**（< 2 个 composite 邻近的已发样本）：

```markdown
## 锚点对比

校准池只有 N 个样本，无 composite ±0.5 邻近样本。**锚点对比 N/A**——
注意这次预测的 confidence 标注是 🟡 偏低 / 🔴 极低，bucket 中枢仅供参考。
```

**仍然写出这段**——告诉读者锚点为何缺。不是把段落删掉。

---

### 组件 6：反事实场景（Counterfactual scenarios）

每个可能的 bucket 写一段"如果落在这里，意味着什么"。

```markdown
## 反事实场景

**如果爆 `>X w`**（X% 预期）:
- [验证什么假设]
- [推翻什么假设]
- [可能新增什么 rubric 维度]

**如果落在 `headline bucket`**（X% 预期）:
- [基准线验证什么]

**如果跌到 `<X w`**（X% 预期）:
- [推翻什么核心判断]

**如果 `<<X w`**（X% 预期）:
- [极端场景的可能解释]
```

为什么必填：复盘时**实际落在哪个 bucket** 直接告诉你 rubric 的哪个假设被测试。没有反事实场景，复盘退化为"这次准 / 不准"——没有诊断价值。

---

### 组件 7：关键校准假设（Critical calibration hypothesis）

可选但强烈推荐：把这次预测当成一次实验，明确写下"如果 X 发生，证明 Y"。

```markdown
## 关键校准假设（对比样本丙）

两篇同 composite=8.24，差异：
- 本篇：ER=5 / SR=2
- 样本丙：ER=3 / SR=4

**我押：本篇 > 样本丙（比率 1.5-2x）**

如果反过来 → rubric 里 SR 权重应上调，ER 权重应下调
如果差距 < 1.3x → rubric 基本 OK，差异在噪声范围
```

校准假设是 rubric 升级的种子——单条假设被 ≥3 样本验证 → 进入 bump 候选。

**校准样本不够时**：写"无可对照样本——仍写下我对这次的核心赌注（即使没有锚点）"，然后写一两条这次想测的事。**不要删掉这段**。

---

### 组件 ∞：复盘段（Retrospective）— 仅追加

发布后按轨道 retro 窗口到期时追加。**不修改预测段任何字符**。

```markdown
## 复盘

**复盘时间**: 2026-05-07（发布 T+3d）
**抓取时间**: 2026-05-07 09:30
**数据来源**: manual paste / adapter:<name>

### 实绩数据
- 播放：71.1w（落在 `30-100w` 桶内偏高，相对中枢 50w **+42%**）
- 点赞：2.4w（赞播比 3.38%）
- 分享：1.8w（分播比 2.53%，强）
- 轨道指标：[按该轨 success_metrics 补充——转化轨加咨询数/私信等]

### Top 评论关键词
- 「她不一样」模因爆发：2266 赞独占榜首，全文 12+ 次变体

### 哪些预测被验证 / 推翻
**被验证 ✅**:
- 关键校准假设完全成立：本篇 71.1w / 样本丙 11.7w = 6.07x
- ER=5 主导传播力 → H1 强证据

**被推翻 ❌**:
- 中枢 50w 被超出 +42%
- 我对 SR 的押注反向被推翻：SR 在情感向场景应下调

### 需要写进 rubric_notes.md 的新观察
1. ER 在情感向场景的真实权重应 ≥ ×2.0
2. 议题分享冲动 (TS) 是隐藏维度
```

转化类轨道（retro 窗口 [3, 7, 30]）按窗口多次追加：`### T+3d` / `### T+7d` / `### T+30d` 小节。

---

## 完整结构总览

```
file: <NNN>_<标题>/predictions/YYYY-MM-DD_<id>_<short>.md

# 标题 — 预测日志              ← 组件 1: header（含 confidence + script_hash + Track + Prediction Basis）
（metadata block）

## 输入快照                     ← 组件 2
（scores + 用户改写要点 vs AI 草稿）

## 预测 v1                      ← 组件 3 ⭐ IMMUTABLE 起点
（bucket + 概率 + 中枢 + 一句话 reason）

## 推理因素                     ← 组件 4
（带方向 + 置信度的表）

## 锚点对比                     ← 组件 5（校准池不够时仍写"N/A 段"）

## 反事实场景                   ← 组件 6
（每 bucket 一段"意味着什么"）

## 关键校准假设                 ← 组件 7
（这次预测作为实验的明确赌注）

## 预测 v2 / v3 (appended)      ← (可选) review 改稿后 / 拍后改稿时触发，append 不覆盖
（同 7 组件结构 + 头部含 Diff vs vN-1 摘要）

## 复盘                         ← 仅追加，IMMUTABLE 边界
（实绩 + top 评论 + 验证/推翻 + 新观察；多窗口轨道分 T+Nd 小节）
```

### v1 / v2 / vN 段约定

- **新建文件**：oracle-predict 写 `## 预测 v1`（为 vN 留 schema 一致性）
- **v2 触发条件 A（review 改稿）**：post-draft review（who-for / open-source）改稿后，predict 重判 → `basis=post_review_pre_publish`，append 到 v1 段后、复盘段前
- **v2/v3 触发条件 B（拍后改稿）**：oracle-shoot 检测定稿与预测稿 line-diff ≥ 30%（V2_TRIGGER_THRESHOLD），触发 predict 重判 → `basis=post_shoot_pre_publish`
- **append 而非覆盖**：vN 段插在 `## 复盘` 之前。v1 段**绝不**修改（hook 物理强制）
- **校准用谁**：oracle-retro 读最后一个 `## 预测 vN` 算偏差；v1 留作历史档案
- **diff 学习**：v1 vs v2 的字段差异（如 ER 4→5）就是改稿带来的判分变化，是 rubric 升级证据

### Prediction Basis 字段

prediction header 必含 `Prediction Basis`：
- `pre_shoot`（v1 默认，标准盲预测）
- `post_review_pre_publish`（review skill 改稿后、发布前重判）
- `post_shoot_pre_publish`（拍后改稿、发布前重判——软盲预测）

oracle-retro 用此字段在 score-curve / bump 校准时区分数据线，避免混样。

---

## 子 skill 验收标准

`oracle-predict` 写完一份预测后，必须自检 7 个组件齐全：
- 组件 5 / 7 在校准样本不足时仍写"N/A 段 + 解释"，**不允许直接跳过**
- header 的 `Calibration Samples` + `Confidence` + `Track` 必填——读者一眼看到这次预测多可信、属哪轨

`oracle-retro` 写复盘段时，必须先校验该文件的 7 个组件：
- 缺组件 → 警告"该 prediction 不规范，复盘价值打折"
- 复盘段格式与 confidence 等级**无关**——任何阶段复盘都是同一格式
- diff `Script Hash` 与当前定稿的 hash → 不一致则在复盘段加 `**Script changed between predict and shoot**` 警告
