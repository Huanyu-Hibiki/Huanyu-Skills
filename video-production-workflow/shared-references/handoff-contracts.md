# Handoff Contracts（阶段交接契约）

交接文件不是日志，而是下游可以独立读取的输入契约。每个文件都必须包含来源、版本、生成时间和当前状态。任何下游发现契约缺字段，应暂停并报告，不自行猜测。

## 端到端交接表

| 上游阶段 | 交接文件 | 下游阶段 | 最低要求 |
|---|---|---|---|
| 内容校准 / 用户 | `video scripts/manuscript.md` | `video-plan` | 有完整终稿；保留段落顺序和用户视觉提示 |
| `video-plan` | `storyboard.md`、`storyboard.json` | 用户拍摄、`video-rough-cut` | 每个场景有镜号、脚本、时间估算、画面路由和声音说明 |
| `video-plan` | `storyboard.json` 的 `broll_candidates` 数组 | `b-roll-finder` | 每条有镜号、原句、视觉命题草稿、路由建议和状态；`b-roll-finder` 机会表必须逐条对账（保留/降级/待定），不得静默丢弃 |
| `video-plan`（rough-cut-finalization 模式） | `video scripts/motion_request_list.md` | `b-roll-generate` | 每个动效请求有时间区间、目的、输出规格；`b-roll-generate` Gate 0 将其作为已批准设计提示核对 |
| `video-plan` | `assets/requests/asset_request_list.md` | `video-assets` | 每个外部素材有用途、时长、情绪、比例和许可证要求 |
| 用户拍摄 / OBS | `Raw/*` | `video-rough-cut` | 原始文件可读取；文件名或 `capture_manifest.md` 能映射镜号 |
| `video-rough-cut` | `Rough/takes_decision.json`、`finalKeeps_<source>.json`、`keeps_tightened_<source>.json` | `video-jianying-draft`、`video-caption-correct` | 每句只有一个被选中的 take；EDL 片段必须来自这些 keep 段，不得引用被淘汰 take |
| `video-rough-cut` | `Rough/transcripts/*.json` | `video-caption-correct`、`b-roll-finder` | 词级、verbatim、带 start/end；不可只有 SRT |
| `video-rough-cut` | `Rough/edl.json` | `video-jianying-draft`、剪映 | 每段 source、start、end、target-start、reason；切点不在词内 |
| `video-rough-cut` | `Rough/rough_cut_manifest.md`、`missing_materials.md` | `video-status`、后续精剪 | 记录实际粗剪时间码、已解决项和缺口 |
| `video-caption-correct` | `Sub/caption_corrected.srt`、`Rough/speech_errors.json` | `video-jianying-draft`、剪映 | 字幕时间码来自粗剪时间线；错误修改可追踪；不静默删口播；单条 ≤32 字，进入 Draft 时由 `subtitle_split.py` 拆为 ≤18 显示单位短条 |
| `video-jianying-draft` | `Jianying-draft/`、`Rough/jianying_draft_manifest.md` | 剪映内部精剪 | Draft 可被剪映识别；媒体路径和缓存一致 |
| `video-assets` | `assets/licenses/media_asset_manifest.json` | 所有素材消费者 | 每项第三方素材都有具体来源、许可证和商用判断 |
| 剪映内部精剪 | `Polished/fine_cut.mp4`、`Sub/master.srt` | `b-roll-finder` | SRT 已是精剪输出时间轴；包含完整字幕文本 |
| `b-roll-finder` | `video scripts/broll-opportunity-analysis.md` | 用户确认、`b-roll-generate` | 每个候选有原句、价值判断、素材类型和一句话视觉命题 |
| `b-roll-finder` | `video scripts/broll-segment-plan.md` | `b-roll-generate` | 每个母片段有时间、终态、动作、颜色和风格 |
| `b-roll-finder` | `video scripts/broll-style-decision.md` | `b-roll-generate` | 记录已确认风格、引擎、颜色、成本和需避免的表达 |
| `b-roll-generate` | `Polished/B-roll/<id>/`、`broll-manifest.md` | `video-polish` | 视频/静帧/提示词/许可证/QA 状态齐全 |
| `video-polish` | `Polished/final_timeline_manifest.md`、`Final/qa-report.md` | 用户 / 发布流程 | 所有已批准 B-roll、音效、字幕和最终输出均可追溯 |

## 版本规则

- 修改内容但不改时间轴：递增内容版本，例如 `caption_corrected-v2.srt`。
- 修改剪辑范围或时间轴：必须生成新的 SRT，不得覆盖旧 SRT 后声称时间码不变。
- 修改 B-roll 风格或构图：保留旧版静帧/contact sheet，生成 `v02`。
- Final 文件只有在用户确认后更新；预览写入 `Polished\`。

## 文件头建议

Markdown 交接文件开头使用：

```yaml
source: video scripts/manuscript.md
generated_by: video-plan
generated_at: 2026-08-12T12:00:00+08:00
schema_version: 0.1
status: draft | approved | superseded
```

JSON 交接文件使用同名顶层 `meta` 对象，不把元数据混入场景数组。
