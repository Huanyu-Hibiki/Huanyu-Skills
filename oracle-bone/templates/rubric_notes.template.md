# 评分校准笔记

> **本文件是 oracle-bone 评分规则进化的载体**，**按轨道分节**。每次复盘实绩 vs 预测后把判断写进对应轨道节；下次 /oracle-score / /oracle-predict 打分前先读本文件对应轨节。
>
> **核心原则**：规律必须可追溯到具体样本。不写"情感共鸣很重要"，要写"XX 这篇 ER=5 被验证，因为评论区 top3 都是 YY 模式"。
>
> 生命周期协议见 [shared-references/observation-lifecycle.md](../shared-references/observation-lifecycle.md)；升级流程见 [bump-validation-protocol.md](../shared-references/bump-validation-protocol.md)。

---

## 轨道 1：<轨名>（track: `<slug>`）

### 版本日志

**当前版本**: `v0`

| 版本 | 生效日期 | 变更类型 | 驱动样本数 |
|---|---|---|---|
| v0 | [INIT-DATE] | 初版占位（cold-start 等权） | 0 |

**升级决策原则**：纯权重微调不 bump；维度定义细化不 bump；新增/删除维度或定义颠覆性改写 → bump（走 /oracle-bump --track <slug>，全量重打 + 跨模型审）。

### 当前评分维度 (0-5)

> init 时从对应 starter-rubric 复制。cold-start 用等权 zero 版；观点类可用已拟合参考版（见 starter-rubrics/）。

| 维度 | 权重 | 含义 | 典型信号 |
|---|---|---|---|

**综合分公式**：

```
composite = ...
```

### 观察记录

> 模板（每次复盘后追加一条）：
>
> ```
> ### YYYY-MM-DD [标题简称] (id) — [一句话定性]
> - 预测：composite=X.XX，bucket=Y
> - 实绩：主指标数据（带 T+Nd 标注）
> - Top 评论关键词：[摘录 + 赞数]
> - 判断：哪个维度被验证 / 推翻？为什么？
> - Rubric 调整：[如有]
> - 详见：[predictions/<file>.md]
> ```

（暂无——从第一次复盘开始累计）

### 重大跨样本观察（≥2 样本支持）

（暂无）

### 规律沉淀区（高置信度）

（暂无——升级 1-2 次后会有内容）

### Benchmark-derived initial signals

> /oracle-learn-from 完成后填入。**仅定性方向，不直接采纳为数值权重**。

（待 learn-from 填入）

### 待验证假设

（暂无）

### 被拒升级 log

（暂无）

### Bucket 方案

> 边界是账号属性不是普适常量。按校准阶段切换：
> - cold-start：比率桶（baseline = 上一篇实绩 × {0.3/1/3/10/30}；第 1 篇用平台通用默认）
> - N≥5：absolute（校准池中位数派生）——跑 `/oracle-bump --bucket-only`
> - N≥10：percentile（永远自洽）
>
> 转化轨：bucket 主指标按 success_metrics（咨询/付费），播放仅作过程指标。

（当前: ratio · baseline: 无）

---

## 轨道 2：<轨名>（track: `<slug>`）

（同上结构——每轨独立版本、独立观察、独立 bump）

---

## 全局备注

- 各轨 rubric 独立升级（/oracle-bump --track <id>），不互相污染
- cross 题（跨两轨）两轨各打一次取均值，复盘时两池各 +0.5
