# State Management（制作状态读写约定）

`.video-workflow-state.json` 是单期视频制作状态的唯一来源。`STATUS.md` 是面向人阅读的派生看板，不能反过来作为机器状态来源。

## 位置

```text
<video-project>/.video-workflow-state.json
```

不能放到全局 Skill 目录，也不能让多个视频共享一个 state 文件。

## Schema v0.1

```json
{
  "schema_version": "0.1",
  "skill_version": "0.1.0",
  "project_path": "<视频项目根>/EP001_标题",
  "project_id": "EP001_标题",
  "title": "标题",
  "current_phase": "plan",
  "phase_status": {
    "init": "completed",
    "plan": "in_progress",
    "record": "not_started",
    "rough_cut": "not_started",
    "caption_correct": "not_started",
    "jianying_draft": "not_started",
    "assets": "not_started",
    "fine_cut": "not_started",
    "broll_plan": "not_started",
    "broll_generate": "not_started",
    "polish": "not_started",
    "delivery": "not_started"
  },
  "approval_pending": null,
  "artifacts": {},
  "broll": {
    "profile_confirmed": false,
    "opportunity_count": 0,
    "approved_count": 0,
    "generated_count": 0,
    "manifest_path": null
  },
  "last_action_at": "2026-08-12T00:00:00+08:00",
  "initialized_at": "2026-08-12T00:00:00+08:00"
}
```

## 字段职责

| 字段 | 唯一写入者 | 读取者 | 规则 |
|---|---|---|---|
| `schema_version` | `video-init` / `video-migrate` | 所有子 Skill | 不识别的主版本必须阻塞执行 |
| `current_phase` | 当前完成阶段的子 Skill | `video-status`、路由器 | 只能指向实际存在的阶段 |
| `phase_status` | 对应阶段 Skill | 所有 Skill | 不能用 `STATUS.md` 反推并覆盖 |
| `approval_pending` | 触发审批闸门的 Skill | 路由器、`video-status` | 用户未确认前不得继续成本或破坏性操作 |
| `artifacts` | 产出该文件的 Skill | 下游 Skill | 路径必须是项目内相对路径或明确外部只读引用 |
| `broll.*` | `b-roll-finder` / `b-roll-generate` | `video-polish`、`video-status` | 统计值必须能由 manifest 和文件系统复核 |
| `last_action_at` | 每个有副作用的 Skill | `video-status` | 使用本地带时区 ISO 8601 |

## 读协议

1. 先定位项目根，再读取 state。
2. 文件不存在：提示用户运行 `/video-init`，不要静默创建半套状态。
3. JSON 解析失败：停止写入，报告路径和解析错误；不得用空对象覆盖。
4. `schema_version` 低于当前版本：可读时给出迁移提示；字段语义不兼容时阻塞。
5. 所有新增字段读取使用默认值，但必须在下次迁移中补齐。

## 写协议

使用 read-modify-write，先写临时文件，再原子替换：

```text
读取 .video-workflow-state.json
只修改当前 Skill 负责的字段
写入 .video-workflow-state.json.tmp
校验 JSON 可以重新读取
原子替换为 .video-workflow-state.json
再写 STATUS.md 派生看板
```

写入要求：

- JSON 缩进 2 空格；
- `ensure_ascii=false`，保留中文；
- 不把 API key、Cookie、临时绝对路径写入 state；
- 不在同一个操作里静默修改其他阶段的状态；
- 阶段失败写 `blocked` 和明确原因，不写 `completed`。

## 审批状态

```json
{
  "gate": "broll-style",
  "items": ["BROLL-001", "BROLL-003"],
  "question": "请确认风格和是否生成",
  "asked_at": "2026-08-12T12:00:00+08:00"
}
```

用户确认后清空 `approval_pending`，并把对应阶段置为 `in_progress`。用户只确认部分条目时，只推进通过条目，其余保持 `awaiting_approval`。
