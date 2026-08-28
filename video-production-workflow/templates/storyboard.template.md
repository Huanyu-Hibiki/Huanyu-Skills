---
source: video scripts/manuscript.md
generated_by: video-plan
generated_at: <ISO 8601>
schema_version: 0.1
status: draft
---

# 分镜表

## 使用说明

- `拍摄形式`是素材路由：实拍和 OBS 可以是 A-roll 或 B-roll；Remotion、HyperFrames、AI 图/视频和 B-roll 动画设计默认属于 B-roll。
- 时间是前期估算；实际时间码以粗剪和精剪输出为准。
- 一行只表达一个主要叙事功能。

| 镜号 | 时间 | 画面 | 旁白要点 | 字幕/屏幕文字 | 剪辑/声音 | 拍摄形式 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 01 | 0:00-0:00 | `<画面描述>` | `<旁白核心>` | `<字幕或屏幕文字>` | `<剪辑、音乐、音效>` | `<实拍 / OBS 录像 / Remotion 动效 / HyperFrames / B-roll 动画设计>` |

## 场景补充

| 镜号 | A-roll/B-roll | 素材来源 | 是否需要外部素材 | 是否需要动效 | 许可证 / 版权备注 | 风险 |
|---|---|---|---|---|---|---|
| 01 | A-roll | 用户实拍 | 否 | 否 | | |

## B-roll 候选（结构化交接）

`video-plan` 必须把分镜表中属于 B-roll 的条目抽取为 `storyboard.json` 的 `broll_candidates` 数组（同字段的 JSON 版本），供 `/b-roll-finder` 强制对账。每条：

```json
{
  "shot_id": "01",
  "manuscript_excerpt": "<对应旁白原句>",
  "visual_proposition": "<一句话视觉命题草稿>",
  "route": "Remotion 动效 | HyperFrames | Stock | AI 图 | AI 视频 | B-roll 动画设计 | 用户素材",
  "status": "proposed",
  "note": "<用户【画面建议】或规划理由>"
}
```

`/b-roll-finder` 生成机会表时，每条 `broll_candidates` 必须出现在机会表中并标注：`保留`（升级为正式条目）/ `降级`（判定不值得，写明理由）/ `待定`（时间轴确认后再定）。不得静默丢弃。
