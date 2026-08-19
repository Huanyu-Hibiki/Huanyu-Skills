---
name: oracle-score
description: 给单篇稿子按其轨道 rubric 打分。**只在控制台输出，不写文件，不预测**。触发词："打分这篇 [path]"/"score this [path]"/"给这稿子打分"/"先打分看看"。oracle-predict 之前的轻量探索动作，可反复打不留痕迹。
argument-hint: <draft-path> [— track: <id>]
allowed-tools: Read, Glob, Grep
---

# /oracle-score — 单稿打分

打分但**不预测**。快速看稿子的 composite，决定是否值得进入正式预测流程。

## Overview

```
[用户：打分这篇 <NNN>_<标题>/scripts/<id>.md]
  ↓
[Step 1: 读 draft + state（识别轨道）+ rubric_notes 该轨节]
  ↓
[Step 2: 解析公式与维度]
  ↓
[Step 3: AI 自己逐维度打分（盲打优先）]
  ↓
[Step 4: 算 composite + 控制台输出 + 推荐下一步]
  ↓
[结束 — 不写任何文件]
```

## Constants

- **OUTPUT_DETAIL = full** — full：含每维度理由；compact：仅分数表（可调用时覆盖）

## Workflow

### Step 1: 前置检查

1. 读 state → 不存在提示先跑 /oracle-init
2. 读 draft → 不存在报错停止
3. **识别轨道**：draft header 的 Track 字段 → 交叉题标明后两轨各打一次
4. 读 `rubric_notes.md` **该轨节**——不存在（cold-start 第 1 篇）→ 从对应 starter（opinion-video-zero / conversion-video）读 v0 等权公式，不写文件不阻塞，控制台加 ⚠️ 提示

### Step 2: 识别公式与维度

从该轨节解析：rubric_version / 维度列表与权重 / 归一化常数 / 每维 0-5 含义。格式与预期不符（用户手改过结构）→ 询问当前公式是哪一行，**不自己猜**。

### Step 3: AI 自己逐维度打分

对每个维度：读定义 → anchor 到 0/3/5 样本对照 → 给**整数**（0-5，不允许 4.5）→ 一行理由（≤30 字，引用稿子具体词/场景）。

**打分速度纪律**：
- 每维 ≤30 秒。超过就是在合理化，不是打分
- **相信第一个整数**
- **盲打优先**——先打分再对比锚点，避免被实绩锚定

输出后用户可挑刺（"AB 给 3 不是 4"），AI 改值重展示。

### Step 4: 算 composite + 输出

```
📊 [draft 短标题] — 打分（轨：<轨名> / rubric: v2）

| 维度 | 分 | 理由 |
|---|---|---|
| ER (情感共鸣) | 5 | "半夜三点翻聊天记录"极端具象 |
| HP (钩子强度) | 5 | 首句直接锁定受众，命中3个钩子方向 |
...

公式：(ER×1.5 + SR×1.5 + HP×1.5 + QL + NA + AB + SAT) / 8.5 × 2.0
composite = **8.24**

📍 粗判桶区间（正式 bucket 判定走 predict）

下一步：
- 写定最终稿准备发布 → "启动预测"
- 想再改 → 改完再打一次（多次打分不留痕迹）
- 想看历史相近样本 → "找 composite 8.0-8.5 的锚点"
```

### Step 5: 绝不做的事

- ❌ 写任何文件（predictions / rubric_notes / candidates）
- ❌ 给 bucket 概率分布（oracle-predict 的活）
- ❌ 提议 rubric 升级（发现异常只在控制台提示）

## Key Rules

1. **整数分**。犹豫 → 选低值 + 备注
2. **盲打优先**。打分前不读 anchors
3. **理由是诊断工具**——复盘时用来找哪个维度判断错了
4. **不写文件**。score 是探索，predict 是承诺
5. **按轨打分**。用错轨道的 rubric = 分数无意义
6. **同稿连打 ≥3 次** → 温和提示"反复打分引入决策疲劳，差不多可以决定了"

## Refusals

- 「打分顺便预测一下」 → 拒绝。predict 必须走 blind check + immutable 日志
- 「把分数写进 rubric_notes 观察段」 → 拒绝。观察必须含"实绩 vs 预测"对比
- 「直接告诉我会不会爆」 → 拒绝。给概率判定要走 predict；score 只输出当前 rubric 的机械计算

## Integration

- oracle-predict 的前置探索：反复 score 不同版本，定稿再 predict
- 无副作用，不更新 state
