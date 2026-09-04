# 写作 Pattern 库（script_patterns.md）

> **rubric 教 AI 怎么打分；本文件教 AI 怎么写**。两者解耦，**按轨道分节**（不同轨的写法根本不同，不能混写）。
> oracle-seed 写 draft 前必读；oracle-retro Phase 4b 的改稿 pattern 也写到这里。

---

## 轨道：<轨名>（track: `<slug>`）

### 结构选型 cheat sheet

> 给一个主题，按此表选结构。持续补充。
> **来源（source）与状态（status）双标记**：`source` = self（自己账号复盘沉淀）/ benchmark（对标导入）；`status` = candidate（单样本或未验证）/ verified（≥2 样本复盘确认）。

| Pattern | 一句话 | 适用 | source | status |
|---|---|---|---|---|
| P1 <名> | <描述> | <何时用> | <self / benchmark> | <candidate / verified / 沉淀> |

### 用户改稿历史观察

> retro Phase 4b 沉淀：用户砍了什么/加了什么 + 流量影响。

| 日期 | 作品 | 改动 | 流量影响 | 判断 |
|---|---|---|---|---|

### 新发现的 Pattern（待验证）

> 单样本支持，标 `≥1 样本待验证`；≥2 样本复现才升正式。

### 声音参考（如有 benchmark 声音样本）

<句长 / 口头禅 / 语气词 / 禁用词>

---

## 轨道：<轨名>（track: `<slug>`）

（同上结构）

---

## 对标借鉴（Imported, untested）

> oracle-learn-from 产出的 pattern。**未在自己账号验证**——实拍验证 ≥2 次复盘确认有效后去掉标记升正式。

### Pattern A: <名>（来自 <账号>）
**描述**: ...

## 升降规则

- 新 pattern：单样本 → "待验证"段；≥2 样本 + 复盘确认 → 正式表
- 被推翻：删（git history 是档案）
- pattern 与 rubric 可能交叉（如金句 pattern ↔ QL 维度），但记录在两处——**作用域不同**

## 置信度使用规则（防对标数据污染校准）

- **oracle-seed 选结构**：self / benchmark、candidate / verified 全部可参考——选结构是创作决策，允许借鉴
- **oracle-bump 回追打分与重排序**：pattern 证据**只引用 `source=self 且 status=verified`** 的条目；benchmark 来源或 candidate 状态的条目不作为重打依据——对标账号的规律没在自己的账号验证过，拿它改公式 = 用别人的数据校准自己的尺
- **升级路径**：benchmark-candidate 条目经实拍 ≥2 次复盘确认有效 → 改 source 保持、status 升 verified（"在自己账号验证过的对标写法"仍是 self 经验）
