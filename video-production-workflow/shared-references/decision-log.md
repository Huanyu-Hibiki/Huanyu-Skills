# Decision Log（决策日志：跨阶段审计轨迹）

`.video-workflow-state.json` 记录"做到哪了"，决策日志记录"**为什么这么选**"。take 挑选、B-roll 方案、词典沉淀、渲染参数这类选择的理由散落在各阶段产物里，回看时无处可查——本日志是唯一的集中审计轨迹，人工精剪和复盘时是它的第一读者。

## 位置与格式

```text
<项目根>/decision_log.json
```

从 [../templates/decision-log.template.json](../templates/decision-log.template.json) 复制。每条决策：

| 字段 | 要求 |
|---|---|
| `category` | 枚举：`take_selection`（take 挑选）/ `broll_concept`（B-roll 视觉命题与风格）/ `subtitle_lexicon`（词典增改）/ `render_param`（渲染/导出参数变更）/ `promise_change`（交付承诺降级或修改）/ `approval_policy`（预授权记录，如"本期允许静帧兜底"） |
| `subject` | 作用对象（镜号/条目 ID/参数名） |
| `options_considered` | **≥2 个**被考虑过的选项，各带 0-1 分 `score` + `reason`，落选项写 `rejected_because` |
| `decision` / `decided_by` | 结论 + 是用户拍板还是 Agent 待批 |
| `timestamp` | 本地带时区 ISO 8601 |

## 硬规则

1. **append-only**：改决策 = 追加一条同 `(category, subject)` 的新条目（新 id），旧条目永不改写、永不删除——回看能看到完整的决策演化链；
2. **只考虑一个选项 = 没做决策**：`options_considered` 少于 2 条的条目不成立（用户直接指定且无备选时，写明"用户指定，无备选"作为第二项）；
3. **全 1.0 分不可信**：打分是相对判断，全是满分说明没认真比；
4. **降级必须留痕**：`/video-polish` 的交付承诺校验（`check_delivery_promise.py`）判 degraded 后经用户批准的降级，记 `promise_change` 条目——静默降级是 QA 的 CRITICAL 缺陷；
5. **预授权记 `approval_policy`**：用户说"这一期都听你的"只对当次有效；跨门预授权必须落一条 `approval_policy` 条目，后续门仍逐一确认。

## 谁在什么时候写

| 时机 | category | 写入者 |
|---|---|---|
| `/video-plan` 声明交付承诺 | `promise_change`（初始） | video-plan |
| `/video-rough-cut` take 挑选有歧义（`takes_decision.md` 中用户裁决项） | `take_selection` | video-rough-cut |
| `/b-roll-finder` 风格逐条决策（与 `broll-style-decision.md` 并行留痕） | `broll_concept` | b-roll-finder |
| `/video-caption-correct` 词典增改 | `subtitle_lexicon` | video-caption-correct |
| `/video-jianying-draft` / `/video-polish` 渲染参数偏离默认 | `render_param` | 对应阶段 |
| 交付承诺降级获批 / 预授权 | `promise_change` / `approval_policy` | video-polish / 路由器 |
