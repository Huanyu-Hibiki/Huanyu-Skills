# <标题> — 预测日志

> oracle-predict 落盘。7 组件完整规范见 [shared-references/prediction-anatomy.md](../shared-references/prediction-anatomy.md)。
> `## 预测` 段 immutable（hook 强制）——只能往 `## 复盘` 段追加。

---

**Article ID**: <12 位 candidate id（改稿后不变）>
**Title**: <作品完整标题>
**Track**: <轨道 id>
**Rubric Version**: <该轨版本>
**预测时间**: <YYYY-MM-DD>（基于最终稿）
**Script Path**: <NNN>_<标题>/scripts/<date>_<id>_<short>.md
**Script Hash**: <sha256:12>
**Target Duration (s)**: <state 派生>
**Actual Script Length**: <N 字>
**Calibration Samples (at predict time)**: <该轨样本数>
**Confidence**: <按 state-management confidence 表派生>
**Scored By**: claude
**User Override**: none
**预测时数据状态**: blind
**Prediction Basis**: pre_shoot

---

## 输入快照

**分数 (vN)**: <各维分> → composite=**X.XX**

**用户改写要点 vs AI 草稿**:
- （用户原创稿则写"用户原创稿，无 AI 草稿对照"）

## 预测 v1

**Bucket**: `<bucket>`

**内心概率分布**:
- `<bucket1>` → N%
- **`<headline bucket>` → N%**（中枢 ~X）
- `<bucket3>` → N%
- ...（加总必须 100%）

**一句话 reason**:
> <浓缩判断>

## 推理因素

| 因素 | 方向 | 置信度 | 说明 |
|---|---|---|---|

## 锚点对比

> 校准池不够时仍写本段：`校准池只有 N 个样本，无 composite ±0.5 邻近样本。锚点对比 N/A——confidence 为 X，中枢仅供参考。`

| 对照样本 | composite | 实绩 | 异同 |
|---|---|---|---|

## 反事实场景

**如果爆 `>X`**（N% 预期）: 验证/推翻什么假设
**如果落在 `headline`**（N%）: 基准线验证什么
**如果跌到 `<X`**（N%）: 推翻什么核心判断
**如果 `<<X`**（N%）: 极端场景解释

## 关键校准假设

> 无对照样本时写"无可对照样本——仍写下核心赌注"+ 1-2 条想测的事。**不删段**。

**我押**：<本篇 vs 对照 = X 倍>
**如果反过来** → <哪个 rubric 假设被推翻>

## 复盘

（待填——窗口到期后跑 /oracle-retro <作品>）
