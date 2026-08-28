# 工作流速查（视频制作管线）

> 本文件由 `/video-init` 复制到单期视频项目根目录。完整规则在本合集根目录的 `SKILL.md` 和 `shared-references/`。

## 一句话流程

```text
终稿
  ↓
/video-plan
  → video scripts/storyboard.md + storyboard.json
  → asset_request_list.md + remotion_candidate_list.md
  ↓
用户按分镜拍摄 / OBS 录制 → Raw/
  ↓
/video-rough-cut
  → Rough/transcripts/*.json + edl.json + preview.mp4
  ↓
/video-caption-correct
  → Sub/caption_corrected.srt
  ↓
/video-jianying-draft
  → Jianying-draft/ + 剪映内部精剪
  ↓
/video-assets
  → assets/ + media_asset_manifest.json
  ↓
/video-fine-cut
  → 剪映内部剪气口、调节节奏
  → Sub/master.srt + Polished/fine_cut.mp4
  ↓
/b-roll-finder
  → broll-opportunity-analysis.md（含 storyboard broll_candidates 对账）+ broll-segment-plan.md
  ↓
/b-roll-generate
  → Polished/B-roll/ + broll-manifest.md
  ↓
/video-polish --preview
  → Polished/preview.mp4 + QA grid
  ↓
用户确认
  ↓
/video-polish --final
  → Final/video_final.mp4 + Final/qa-report.md
```

## 阶段速查

| 阶段 | 触发词 | 输入 | 交接输出 |
|---|---|---|---|
| 初始化 | 初始化视频制作管线 | 项目路径 | state、目录、WORKFLOW、STATUS |
| 分镜规划 | 规划分镜、文稿转分镜 | 终稿 | storyboard、素材请求、动效候选 |
| A-roll 粗剪 | 粗剪、转录、按文稿剪 | Raw、文稿 | transcript、EDL、粗剪预览 |
| 字幕校对 | 校对字幕、修 ASR | 初始字幕、文稿 | caption_corrected.srt、speech_errors |
| 剪映 Draft | 创建剪映草稿 | EDL、字幕、媒体 | Jianying-draft |
| 素材获取 | 下载素材、找音乐 | asset_request_list | assets、许可证 manifest |
| 精剪交接 | `/video-fine-cut` | 剪映 Draft | fine_cut.mp4、master.srt |
| B-roll 策划 | 分析 B-roll | master.srt | 机会表、母片段表、风格决定 |
| B-roll 生成 | 生成 B-roll | 已确认计划 | B-roll 成片、manifest、QA |
| 成片合成 | 合成、输出预览 | fine cut、B-roll、master.srt | preview、Final、QA |

## B-roll 选择原则

- 先判断这句是否值得画面，不为每句添加画面；
- 具体实体优先真实素材，抽象概念才优先自制动效；
- Remotion、HyperFrames、拼贴 AI 都属于 B-roll 生成工具，不接管整条主视频；
- B-roll 默认落在关键词说出后约 `0.2-0.5s`；
- 每次重渲染先读 `Polished/broll-manifest.md`，批准条目不能静默消失。

## 审批闸门

| 闸门 | 需要确认 |
|---|---|
| Gate 1 | 分镜路由、素材需求和动效候选 |
| Gate 2 | 粗剪策略和输出方式 |
| Gate 3 | 外部素材来源、许可和下载范围 |
| Gate 4 | B-roll 机会、密度、风格和素材类型 |
| Gate 5 | B-roll 生成引擎、成本和规格 |
| Gate 6 | 拼贴路线的隐喻、静帧和视频三次确认 | 
| Gate 7 | B-roll 位置、音效、字幕和最终输出 |

## 当前项目目录

```text
项目根：<填写项目绝对路径>
终稿：video scripts/manuscript.md
粗剪：Rough/preview.mp4
精剪：Polished/fine_cut.mp4
最终字幕：Sub/master.srt
最终成片：Final/video_final.mp4
```
