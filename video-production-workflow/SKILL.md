---
name: video-production-workflow
description: 视频制作全流程工作流合集。把终稿文稿、原始拍摄、字幕、剪映草稿、外部素材和 B-roll 生成串成一条可追踪的制作管线，并从真实任务、失败和用户纠正中验证式优化 Skills。触发词：制作视频、视频制作管线、规划分镜、粗剪、字幕校对、生成 B-roll、合成成片、视频状态、优化视频 skill、skillopt。
allowed-tools: Bash(*), Read, Write, Edit, Glob, Grep, Skill
---

# 视频制作管线 / Video Production Workflow

本 Skill 是一组围绕单期视频项目运行的 workflow skill 集合。它不是另一个剪辑软件，也不是把所有工具混在一个黑箱里，而是负责：

- 规定阶段顺序、输入、输出和交接文件；
- 判断当前请求应该进入哪个阶段；
- 维护单期视频的状态和目录；
- 区分 A-roll、B-roll、素材下载和动效生成的责任边界；
- 在剪映、FFmpeg、AI 视频、Remotion 和 HyperFrames 之间做路由；
- 让每个阶段可以暂停、审核、重跑和继续，不因换会话而丢失上下文。

## Python 执行约定

本 Skill 根目录的 `.venv` 是唯一 Python 环境。运行 Python 脚本必须使用 `uv run --project <Skill根目录> python ...`；不得调用系统 Python、Anaconda 或其他虚拟环境。初始化和依赖说明见 [DEPENDENCIES.md](DEPENDENCIES.md)。PyTorch 使用 CUDA 12.6 GPU wheel，不使用 CPU wheel。

## 模型调用约定

对话、分析、规划和校对统一使用当前 Agent 提供的模型，不在 Skill 中配置固定对话模型或供应商级对话密钥。Whisper/Fun-ASR 是本地转录工具；Gemini/Veo 的模型参数只服务于明确的专用图像或视频生成 API，不代表对话模型选择。

## 部署边界

内容校准由 `cheat-on-content` 负责，通常运行在 Hermes 或内容管理环境；本 Skill 负责工作站上的视频制作。两者的衔接物是已经确认的终稿，通常放在：

```text
D:\work\OPC\videos\{第X期：视频标题}\video scripts\
```

本 Skill 不修改上游内容校准的预测、发布和复盘文件。成片完成后，只把 `Final\` 中的成片和必要的制作状态交还上游。

## 核心定义：A-roll 与 B-roll

| 类型 | 定义 | 常见来源 | 主要处理工具 |
|---|---|---|---|
| A-roll | 承担主要叙事、人物表达和连续口播的主体画面 | 实拍口播、采访、主要 OBS 操作 | `video-rough-cut`、剪映、Filmora |
| B-roll | 覆盖、解释、证明或强化 A-roll 的辅助视觉；不要求是“拍摄出来的” | OBS 证据录屏、Stock、网页截图、AI 图/视频、Remotion、HyperFrames、拼贴动画 | `b-roll-finder`、`video-assets`、`b-roll-generate` |

OBS 不是固定的 A-roll 或 B-roll：人物边操作边讲解时是 A-roll；只截取界面、流程和产品证据覆盖口播时是 B-roll。分镜表中的“拍摄形式”是路由字段，不是对素材属性的唯一判断。

## 不可妥协原则

1. **单项目单目录**：每期视频的派生文件只写入该视频目录，不写入 Skill 目录、仓库根目录或 `Raw\`。
2. **Raw 只读**：用户原始实拍和 OBS 文件不可覆盖、重命名、就地转码或写入派生文件。
3. **交接文件是真相源**：下游只消费上游明确产出的契约文件；不凭聊天上下文猜测时间码和状态。
4. **先计划再执行**：破坏性剪辑、付费 AI 视频生成和大规模下载前，先给出策略或计划；用户确认后再执行。
5. **初始转录不等于最终字幕**：粗剪阶段使用词级 ASR 做决策；剪映内部精剪后才生成最终输出时间轴 SRT。
6. **B-roll 表达观点，不机械匹配关键词**：先读完整字幕和上下文，再决定是证据、实体、概念、情绪还是用户提供的文化梗。
7. **生成工具只做 B-roll**：Remotion、HyperFrames 和拼贴 AI 默认输出独立 B-roll，不直接接管整条主视频。
8. **最终交付前必须自检**：检查时间轴、字幕可读性、B-roll 对词、音频边界、画面比例、许可证和已确认素材是否被遗漏。

## 端到端流程

```text
内容校准终稿
  ↓
01 /video-init —— 建项目目录、状态文件和工作流速查
  ↓
02 /video-plan —— 文稿 → 分镜表、素材需求、动效候选
  ↓
用户拍摄 / OBS 录制 —— 素材进入 Raw\
  ↓
03 /video-rough-cut —— Fun-ASR 或 Whisper + 文稿 + FFmpeg → 粗剪与词级转录
  ↓
04 /video-caption-correct —— 根据文稿校对初始字幕和口误
  ↓
05 /video-jianying-draft —— 根据剪辑决策生成剪映原生 Draft
  ↓
  06 /video-assets —— 搜索下载 + 合规转码归档
  ↓
07 /video-fine-cut —— 剪映内部剪气口、精剪、输出 master.srt
  ↓
08 /b-roll-finder —— 精剪 SRT → B-roll 机会表 + 母片段设计表
  ↓
09 /b-roll-generate —— 选择真实素材 / 拼贴 AI / Remotion / HyperFrames 生成 B-roll
  ↓
10 /video-polish —— B-roll、音效、音乐、字幕和 A-roll 装配，反复 QA
  ↓
Final\video_final.mp4
```

## 阶段路由表

| 用户意图 / 触发词 | 子 Skill | 前置条件 | 主要结果 |
|---|---|---|---|
| 初始化、创建视频项目、首次使用 | `/video-init` | 无 | 项目目录、状态文件、`WORKFLOW.md`、`STATUS.md` |
| 看状态、现在做到哪一步、下一步做什么 | `/video-status` | 可选项目目录 | 只读状态看板和下一步建议 |
| 规划分镜、文稿转分镜、列素材 | `/video-plan` | 终稿文稿 | `storyboard.md`、`storyboard.json`、素材和动效候选 |
| 转录、粗剪、剪口播、按文稿剪视频 | `/video-rough-cut` | `Raw\` 原片 | 词级转录、EDL、粗剪预览、粗剪交接文件 |
| 校对字幕、修正 ASR、根据原稿改字幕 | `/video-caption-correct` | 初始转录/字幕 + 文稿 | 校对文本、口误记录、可用于剪映的字幕输入 |
| 创建剪映草稿、导入视频和字幕 | `/video-jianying-draft` | EDL/剪辑决策 + 字幕 | 剪映原生草稿和素材副本 |
| 下载素材、找图片、找视频、找音乐、找音效 | `/video-assets` | `asset_request_list.md` 或明确需求 | 素材文件、转码副本、许可证清单 |
| 剪映内部剪辑、剪气口、导出精剪字幕 | `/video-fine-cut` | 剪映 Draft / Filmora 工程 + 校对字幕 | `Polished/fine_cut.mp4`、`Sub/master.srt` |
| 分析哪里需要 B-roll、设计 B-roll | `/b-roll-finder` | 剪映精剪后的 SRT | B-roll 机会表、母片段设计、风格建议 |
| 生成 B-roll、做 Remotion/HyperFrames/拼贴动画 | `/b-roll-generate` | 已确认的 B-roll 设计 | B-roll 视频、透明素材、静帧和提示词 |
| 调整 B-roll 位置、合成音效、输出成片 | `/video-polish` | 精剪视频 + B-roll + SRT | `Polished\`、`Final\video_final.mp4`、QA 记录 |
| 迁移旧状态、升级 schema、修复项目结构 | `/video-migrate` | 旧版 state 或目录 | 备份、迁移报告、更新后的 state |
| 记录任务教训、复盘协作、优化管线 Skill | `/video-skill-optimize` | 真实任务/对话证据或验证案例 | 本地证据、候选、Gate 结果、经确认的 Skill 更新 |

## 阶段状态

状态统一写入项目根的 `.video-workflow-state.json`。阶段状态只允许使用：

```text
not_started -> in_progress -> awaiting_approval -> completed
                               \-> blocked
```

需要用户选择、审美确认或成本确认时必须进入 `awaiting_approval`，不能假装阶段已经完成。详细读写规则见 [shared-references/state-management.md](shared-references/state-management.md)。

## B-roll 路由

`/b-roll-finder` 先决定“是否值得插入 B-roll”和“应该看什么”，`/b-roll-generate` 再决定“用什么引擎做”。默认决策：

| B-roll 需求 | 首选路由 | 备选路由 |
|---|---|---|
| 真实人物、产品、事件、地点 | 官方/权威视频或用户素材 | `video-assets` + 合规归档 |
| 新闻、引用、数据、网页证据 | 原始页面截图、真实 UI、OBS 录屏 | HyperFrames 复刻展示，但不得伪造证据 |
| 流程、架构、数据、决策树 | Remotion | HyperFrames |
| 标题卡、关键词、字幕强调、UI 浮层、转场 | HyperFrames | Remotion |
| 抽象概念、历史隐喻、不可拍摄场景 | `b-roll-generate` 拼贴路线或 AI 图/视频 | Remotion / HyperFrames |
| 用户明确要求纸拼贴、半调、物件组装 | `b-roll-generate` 拼贴路线 | HyperFrames 分层重做 |
| 需要跨视频复用、props 参数化的模板 | `b-roll-generate` Remotion 路线 | HyperFrames 模板 |
| 用户提供的梗、反应、文化片段 | 用户素材库 | 不由 Agent 擅自搜索和替换 |

## 实现资源与来源映射

可执行实现已经按当前子 Skill 体系统一放入根目录 `scripts/`；旧 Skill 仅作为来源记录，运行时不依赖备份目录：

| 集成阶段 | 来源 Skill |
|---|---|
| 文稿、分镜和交接文档 | `skills/video-plan/SKILL.md` + `templates/`（该阶段为模型生成型，`scripts/video-plan/` 仅存说明） |
| 转录、粗剪、FFmpeg、精剪合成 | `scripts/video-rough-cut/` |
| 字幕转录、口误识别和纠错 | `scripts/video-caption-correct/` |
| 剪映原生 Draft | `scripts/video-jianying-draft/` |
| 下载、许可证、转码和归档 | `scripts/video-assets/` |
| B-roll 机会分析和素材处理 | `scripts/b-roll-finder/` + `skills/b-roll-finder/SKILL.md` |
| 半调纸拼贴 AI B-roll、HyperFrames 检查 | `scripts/b-roll-generate/` |
| Remotion / HyperFrames 技术规则 | `references/b-roll-generate/remotion-best-practices/`、`references/b-roll-generate/hyperframes/` |
| 任务证据、候选 Skill 和验证闸门 | `scripts/video-skill-optimize/` + `skills/video-skill-optimize/SKILL.md` |

注：`video-fine-cut` 的执行主体是用户在剪映/Filmora 内的人工精剪，`scripts/video-fine-cut/` 仅存说明文档；其合成与 QA 脚本位于 `scripts/video-polish/`。

## 目录清单（合集根 = 本 SKILL.md 所在目录）

```text
video-production-workflow/          # 合集根（部署时位于 01-制作管线/ 下）
├── SKILL.md                        # 本文件：路由、原则、阶段顺序
├── README.md / CHANGELOG.md / DEPENDENCIES.md
├── pyproject.toml / uv.lock        # 唯一 Python 环境
├── scripts/                        # 全部可执行实现（按子 skill 分目录）
│   ├── lib/
│   ├── b-roll-finder/
│   ├── b-roll-generate/
│   ├── video-assets/
│   ├── video-caption-correct/
│   ├── video-fine-cut/
│   ├── video-init/
│   ├── video-jianying-draft/       # jianying.py + subtitle_split.py + vendor/
│   ├── video-migrate/
│   ├── video-plan/
│   ├── video-polish/
│   ├── video-rough-cut/            # transcribe/select_takes/tighten_pauses/render 等
│   ├── video-status/
│   └── video-skill-optimize/
├── skills/                         # 各子 skill 的 SKILL.md（路由与规则）
│   ├── video-init/ ├── video-status/ ├── video-plan/
│   ├── video-rough-cut/ ├── video-caption-correct/ ├── video-jianying-draft/
│   ├── video-assets/ ├── video-fine-cut/ ├── b-roll-finder/
│   ├── b-roll-generate/ ├── video-polish/ ├── video-migrate/
│   └── video-skill-optimize/
├── shared-references/              # 跨阶段契约与参考
│   ├── video-folder-schema.md / state-management.md / handoff-contracts.md
│   ├── a-roll-b-roll-routing.md / b-roll-style-catalog.md
│   ├── b-roll-timing-and-qa.md / motion-engine-decision.md
│   ├── b-roll-taste-profile.md / approval-gates.md / skill-optimization.md
├── references/                     # 深度参考资料（按消费者分目录）
│   ├── video-caption-correct/ ├── video-assets/ ├── video-plan/
│   └── b-roll-generate/（hyperframes/ remotion-material/ remotion-best-practices/ …）
├── templates/                      # 交接文件模板（workflow/status/storyboard/broll 系列/motion-request-list 等）
└── migrations/                     # schema 迁移登记
    └── registry.md
```

单期视频项目目录（`D:\work\OPC\videos\{第X期：标题}\`）的结构见 [shared-references/video-folder-schema.md](shared-references/video-folder-schema.md)，与本合集根分开维护。

## 常见拒绝与降级

- 用户要求跳过文稿/分镜直接批量生成大量 B-roll：先拒绝批量生成，要求先完成 B-roll 机会表和风格确认。
- 用户要求覆盖 `Raw\` 原片：拒绝，写处理副本到 `Rough\` 或 `assets\raw\`。
- 用户要求把未经授权的电影、电视剧、付费或 DRM 素材直接放入成片：拒绝并给出合规替代路线。
- 用户要求用网站截图伪造真实证据：拒绝；可以做明确标注为“示意”的视觉解释。
- 用户要求在看到实际数据后修改先前的制作决策：允许追加修订记录，但不覆盖已确认的阶段产物，除非用户明确创建新版本。
- 某个生成引擎失败：只切换该 B-roll 条目的备用路由，不重跑已经通过 QA 的条目。

## 扩展规则

- 新增阶段：在 `skills/` 增加子 Skill，并在本文件路由表、目录清单和交接表登记。
- 新增交接文件：先更新 `shared-references/handoff-contracts.md`，再增加模板。
- 新增 B-roll 引擎：更新 `motion-engine-decision.md`，明确输入、输出、透明通道、时长和 QA 方式。
- 修改项目目录：更新 `video-folder-schema.md` 和 `templates/workflow.template.md`，不要只改某个子 Skill。

## 任务后学习协议

- 用户明确纠正、出现失败/返工、高风险边界误判，或发现可复用成功模式时，路由到 `/video-skill-optimize record`，只保存脱敏后的最小证据。
- 普通单次表现不直接修改生产 Skill；重复信号、用户明确固化要求或高风险单次问题才允许形成候选。
- 所有候选必须经过留出案例严格增益 Gate，并由用户明确确认后才能采纳；不得自动改写 `SKILL.md`。
