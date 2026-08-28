---
generated_by: b-roll-generate
generated_at: <ISO 8601>
source: video scripts/broll-segment-plan.md
schema_version: 0.1
status: active
---

# B-roll Manifest

> 唯一记录“哪些 B-roll 被批准、生成、装配和保留”的清单。每次重渲染前先读取；已批准条目不能静默删除。

| 编号 | 原句 / beat | 精剪时间 | 文件 | 引擎 / 来源 | 版本 | 用户状态 | QA 状态 | 许可证 | 装配时间 | 备注 |
|---|---|---|---|---|---|---|---|---|---|---|
| BROLL-001 | `<原句>` | `00:00:00.000` | `B-roll/BROLL-001_名称/out/final.mp4` | `<Remotion / HyperFrames / 拼贴 / Stock>` | v01 | approved | passed | `<manifest id>` | `00:00-00:04` | | 

## 状态枚举

`proposed` · `approved` · `in_progress` · `awaiting_external_generation` · `generated` · `qa_failed` · `passed` · `deferred` · `removed_by_user` · `superseded`

## Removed / Deferred（不要自动恢复）

| 编号 | 时间 | 决定 | 原因 | 日期 |
|---|---|---|---|---|
| `<BROLL-XXX>` | `<time>` | deferred | `<reason>` | `<date>` |

## 重渲染检查

- [ ] 每个 `approved` / `passed` 条目仍然存在；
- [ ] 新增条目有用户确认；
- [ ] superseded 条目未被误装配；
- [ ] 每个装配点与 `Sub/master.srt` 一致；
- [ ] 已通过 QA 的文件没有被新版本覆盖。
