# Video Folder Schema（视频项目目录标准）

本目录标准是所有子 Skill 的共同约定。一个视频项目只有一个项目根；所有派生文件都必须写入项目根下对应阶段目录。初始化时只创建缺失目录，不覆盖用户已有文件。

## 项目根

```text
D:\work\OPC\videos\{第X期：视频标题}\
```

解析优先级：

1. 用户明确给出的项目路径；
2. 输入文件位于 `D:\work\OPC\videos\...` 下时，使用其最近的项目根；
3. 用户只给出期数和标题时，组合出项目根；
4. 无法判断时先询问，不在当前工作目录猜测创建。

## 标准目录结构

```text
{video-project}/
├── .video-workflow-state.json       # 本期制作状态，受版本 schema 约束
├── WORKFLOW.md                      # 面向用户的速查流程
├── STATUS.md                        # 状态看板，由 video-status 维护
├── video scripts/                   # 文稿、分镜和制作交接文件
│   ├── manuscript.md                # 终稿副本或上游终稿引用
│   ├── storyboard.md                # 给人读的分镜表
│   ├── storyboard.json              # 机器消费的分镜真相源
│   ├── material_suggestion_doc.md   # 素材建议
│   ├── remotion_candidate_list.md   # 拍前候选，不是执行令
│   ├── music_cue_sheet.json         # 音乐/音效情绪和时长需求
│   ├── broll-opportunity-analysis.md
│   ├── broll-segment-plan.md
│   ├── broll-style-decision.md
│   ├── b-roll-taste-profile.md
│   └── motion_request_list.md       # 已确认的动效执行令
├── Raw/                             # 用户原始实拍/OBS，严格只读
├── Rough/                           # 转录、粗剪、EDL 和调试文件
│   ├── transcripts/                 # 缓存的词级 ASR JSON
│   ├── clips_graded/                # 粗剪分段副本
│   ├── animations/                  # 粗剪阶段临时动效 slot
│   ├── verify/                      # 时间线截图、波形和 QA 图
│   ├── edl.json
│   ├── takes_packed.md
│   ├── rough_cut_manifest.md
│   ├── missing_materials.md
│   └── preview.mp4
├── Sub/                             # 字幕各版本
│   ├── draft.srt                    # 粗剪初始字幕
│   ├── caption_corrected.srt        # 文稿校对后字幕
│   └── master.srt                   # 剪映精剪后最终时间轴字幕
├── Jianying-draft/                  # 剪映原生草稿实际归档目录
├── Polished/                        # 精剪和 B-roll 装配中间产物
│   ├── fine_cut.mp4
│   ├── B-roll/                      # 每个 B-roll slot 一个目录
│   ├── broll-manifest.md            # B-roll 的唯一装配清单
│   ├── Remotion/                    # Remotion 工程及输出
│   ├── HyperFrames/                 # HyperFrames 源文件及输出
│   ├── final_timeline_manifest.md
│   └── preview.mp4
├── Final/                           # 只放用户确认过的发布成片
│   ├── video_final.mp4
│   └── qa-report.md
├── assets/                          # 外部/处理后素材，不放未授权下载
│   ├── requests/asset_request_list.md
│   ├── raw/audio/
│   ├── raw/video/
│   ├── raw/image/
│   ├── audio/music/
│   ├── audio/sfx/
│   ├── video/stock/
│   ├── image/stock/
│   ├── licenses/media_asset_manifest.json
│   └── logs/ffmpeg_commands.md
├── prompt/                          # AI 视频、图像、动效和音频提示词
│   ├── video/
│   ├── image/
│   ├── animation/
│   └── audio/
├── Thumb/                           # 封面或缩略图
└── ProjectFolder/                   # Filmora 等项目文件（如需要）
```

## 原始素材规则

- `Raw\` 是证据和输入，不是工作目录。
- 需要转码、裁切、调色或做代理时，输出到 `Rough\` 或 `assets\raw\`。
- 原始文件名尽量与 `storyboard.json` 的镜号范围对应，例如：`实拍【EP001-S01-001到EP001-S04-001】.mp4`。
- 外部下载的原始文件先进入 `assets\raw\`，通过许可证审核和标准化后才能进入消费者目录。

## 剪映草稿映射

剪映 GUI 只识别其设置中的草稿根。推荐让剪映草稿根中的项目名通过 symlink 指向本项目的 `Jianying-draft\`，使项目归档和剪映识别同时成立。

执行 `save_draft` 前必须读取剪映 GUI 的实际“草稿位置”，不得盲用默认 C 盘路径。`video-jianying-draft` 的所有命令使用同一 `Rough\.jianying_cache\`。

## 版本与命名

| 产物 | 命名规则 |
|---|---|
| 分镜 | `storyboard.md` + `storyboard.json`，二者同一版本 |
| 粗剪预览 | `Rough/preview-vN.mp4`，保留通过 QA 的旧版本 |
| B-roll | `BROLL-001_短名称/`，目录内文件带 `v01`、`v02` |
| 动效 | `MotionXX_名称/` 或 `BROLL-XXX_名称/`，不能使用 `temp` 作为唯一名称 |
| 精剪字幕 | `Sub/master.srt`，每次重大时间线变更递增 `master-vN.srt` |
| 成片 | `Final/video_final.mp4`，发布前只允许一个当前确认版本 |
