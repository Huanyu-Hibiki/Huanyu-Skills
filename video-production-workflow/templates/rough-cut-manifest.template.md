---
generated_by: video-rough-cut
generated_at: <ISO 8601>
source_project: <project path>
schema_version: 0.1
status: draft
---

# 粗剪交接清单

## 粗剪规格

| 字段 | 内容 |
|---|---|
| 预览文件 | `Rough/preview.mp4` |
| EDL | `Rough/edl.json` |
| 转录引擎 | `<fun-asr / whisper>` |
| 画幅 | `<width>x<height>` |
| FPS | `<fps>` |
| 预计时长 | `<seconds>` |
| 实际时长 | `<seconds>` |
| 字幕状态 | `<not_started / draft / needs_correction>` |

## Take 挑选统计

| 字段 | 内容 |
|---|---|
| 文稿句子数 | `<N>` |
| 检测到 take 总数 | `<M>` |
| 淘汰 take 数 | `<M - matched>` |
| 多 take 句子数 | `<K>` |
| 未匹配句子 | `<idx 列表，需人工确认>` |
| 停顿收紧 | `<移除 X.Xs / 共 N 处>` |

用户已过目 `takes_decision.md`：`<yes / 待确认>`

## 片段状态

| EDL 段 | Source | 起止 | 目标时间 | 场景 / beat | 保留理由 | 状态 |
|---|---|---:|---:|---|---|---|
| 001 | `<source>` | `<start-end>` | `<target-start>` | `<beat>` | `<reason>` | kept |

## 已解决内容

- `<口误、重复、气口或结构问题>`

## 仍需规划的内容

- `<缺少的画面、B-roll、音效、音乐或动效>`

## 给下一阶段的注意事项

- `<字幕校对注意事项>`
- `<剪映精剪时间码注意事项>`
- `<B-roll 候选和不能删的完整解释>`
