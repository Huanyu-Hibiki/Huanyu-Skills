---
name: b-roll-generate
description: B-roll 生成编排器。根据已确认的 B-roll 机会表、母片段设计、精剪字幕和风格决策，路由真实素材、Remotion、HyperFrames、拼贴或 AI 生成路线，产出可交给 video-polish 的独立 B-roll、透明素材、静帧、提示词、放置 JSON 和逐条 QA。触发词：生成 B-roll、做 B-roll 动画、生成 Remotion B-roll、生成 HyperFrames B-roll、生成拼贴视频。
argument-hint: "[project-path] [--ids BROLL-001,BROLL-002]"
allowed-tools: Bash(*), Read, Write, Edit, Glob, Grep, Skill
---

# /b-roll-generate

## 定位

这是 B-roll 的生成和交付入口，不是重新做选题、重新分析全文或直接剪主视频。

只执行 `/b-roll-finder` 已经分析、用户已经批准、并且有明确输出规格的条目。每个
B-roll request 是一个独立的可复用素材单元，不把多个条目偷偷拼成完整主视频。

硬边界：

- `/b-roll-finder` 负责机会、母片段、风格和用户审批；本 skill 负责实现与 QA；
- `/video-polish` 负责把通过 QA 的素材放回精剪时间线；
- 不修改 `Raw/`、`Polished/fine_cut.mp4` 或 `Sub/master.srt`；
- 不因为“画面丰富”给每句口播配画面；
- 不用 AI 伪造新闻、文物、研究截图、真实产品 UI、合同、人物或许可证证据；
- 不在用户确认路线和实现计划前批量搜索、下载、生成或消耗付费模型额度。

## 输入

必须存在或能明确定位：

- `video scripts/broll-opportunity-analysis.md`；
- `video scripts/broll-segment-plan.md`，或机会分析文件中的 Phase 3 母片段设计；
- `video scripts/broll-style-decision.md`，且状态已是用户确认状态；
- `video scripts/storyboard.json` 或 `storyboard.md`，用于回看前期路由和已确认的动效；
- `video scripts/motion_request_list.md`（如经过 `video-plan --mode rough-cut-finalization`），作为已批准的动效执行请求核对；
- 精剪后的 `Sub/master.srt`，时间轴以它为唯一时间真源；
- `assets/` 中已经通过许可证检查的素材，和对应的许可证/来源清单；
- 用户批准的条目 ID、输出格式、画幅、FPS、时长和放置方式。

如果 `broll-style-decision.md` 仍是 `pending`、`awaiting_user_confirmation` 或没有
用户确认记录，只能生成实现计划和待确认报告，不能生成视频或调用付费模型。

## 参考资料包

先按当前路线读取对应资料，不要把所有参考库的整片工作流混到一个 B-roll request：

| 资料 | 用途 |
|---|---|
| `../../references/b-roll-generate/remotion-material/motion-request-template.md` | Motion request 的字段契约 |
| `../../references/b-roll-generate/remotion-material/implementation-plan-template.md` | Remotion 写代码前的实现计划契约 |
| `../../references/b-roll-generate/remotion-material/export-formats.md` | MP4、透明 WebM、PNG sequence、ProRes 4444 导出命令 |
| `../../references/b-roll-generate/remotion-scenes/` | 201+ 场景的类别索引、共享颜色/缓动/字体和准确 TSX 源码 |
| `../../references/b-roll-generate/remotion-templates/README.md` | 81 个独立 Remotion 模板的分类和用途 |
| `../../references/b-roll-generate/remotion-templates/templates/` | 具体模板源码；必须读准确文件，不能只凭文件名重写 |
| `../../shared-references/a-roll-b-roll-routing.md` | Receipts / Entity / Concept 路由 |
| `../../shared-references/b-roll-timing-and-qa.md` | 时间锚点、音频和 manifest QA 规则 |
| `../../references/video-prompt-writer/` | AI 视频 prompt 的 H3 结构（三字段/运镜词表/关键帧模式）和 6 种风格基因库；**写任何 AI 视频 prompt 前必读** |
| `<外部参考项目根>\vox-director\references\beat-layer.md` | 拼贴路线的叙事/镜头/运镜约束（可选，见「合集根定位」的软依赖规则） |
| `<外部参考项目根>\vox-director\references\prompt-guide.md` | 拼贴图像 prompt 和运动 prompt 的稳定性结构（可选） |
| `<外部参考项目根>\vox-director\references\models-and-gotchas.md` | Vox/Atlas 路线的模型和 API 陷阱；只在选择该路线时读取（可选） |
| `<外部参考项目根>\video-shotcraft\references\pipeline.md` | Remotion 单镜头实现、静帧验收和确定性渲染原则（可选） |
| `<外部参考项目根>\video-shotcraft\references\aesthetic-rules.md` | 质感、可读性、节奏、音频和技术 QA 判例（可选） |
| `<外部参考项目根>\video-shotcraft\references\final-review.md` | 最终独立审查的输入和报告格式（可选） |

当前合集根目录 = 包含 `scripts/b-roll-generate/` 的目录，即本 SKILL.md 向上两级（`skills/b-roll-generate/` → 合集根）。部署位置因机器而异，**用目录结构特征定位，不硬编码绝对路径**：

```text
<合集根>/                        # 含 SKILL.md、scripts/、skills/、shared-references/
└── scripts/b-roll-generate/     # 执行脚本所在，定位成功的判据
```

外部参考目录（如 `vox-director`、`video-shotcraft`）是**本机增强资料，不是硬依赖**：路径不存在时跳过对应资料并在 `notes.md` 记录 `external-reference-unavailable`，按合集内 `references/` 与本 SKILL.md 的规则继续，不阻塞生成流程。只有选择 Vox/Atlas 路线且 `vox-director` 不可用时，该路线降级为不可选并告知用户。

不要把 `.opencode/skill/...` 参考目录误认为执行脚本根目录。执行前先确认：

```text
<合集根>/scripts/b-roll-generate/
<合集根>/scripts/video-polish/
```

## Gate 0：生成前检查

### 0.1 状态和批准

依次读取：

1. `.video-workflow-state.json`；
2. `broll-opportunity-analysis.md`；
3. `broll-style-decision.md`；
4. `Sub/master.srt`；
5. 目标素材的许可证清单；
6. `video scripts/motion_request_list.md`（如存在，与机会表核对：请求的时间区间和目的应与已批准条目一致，不一致时先报告差异再执行）。

每个 request 必须同时满足：

- 条目存在于机会分析表；
- 有明确的时间、原句、视觉命题、主要动作和终态；
- 条目状态为 `approved`，或 style decision 中有同等明确的用户批准记录；
- 风格、颜色、引擎和输出格式已经确定；
- Remotion 路线有已批准的 `implementation_plan.md`，除非用户明确授权直接实现；
- 需要 AI 时，模型、画幅和质量档位已经明确；
- 需要真实素材时，素材来源和许可证路线已经明确；
- 没有和已批准旧版本静默覆盖的操作。

如果只有“值得”或“推荐”而没有用户批准，停在计划阶段。

### 0.2 时间轴和规格

- 只使用精剪后的 `Sub/master.srt`，不能拿原始录制或旧粗剪时间码代替；
- 进入词通常在关键词后 `+0.2s` 到 `+0.5s`，不确定时宁可稍晚；
- 将秒数转换为帧时使用 `round(time * fps)`，把使用的 FPS 写进 brief 和 manifest；
- 相邻 B-roll 之间不能制造小于 1 秒的无意义人物碎片；
- 读出视频和项目的宽、高、FPS、时长，不能默认把 30fps 套给 60fps 主项目；
- 输出时长必须服从母片设计，不能让模型返回的默认时长改变放置区间。

### 0.3 环境

Remotion 路线检查：

```bash
node --version
npm --version
ffmpeg -version
ffprobe -version
```

Gemini 视频路线检查脚本：

```bash
bash "<合集根>/scripts/b-roll-generate/check_setup.sh"
```

该脚本实际检查 `GEMINI_API_KEY`、ffmpeg/ffprobe、工作流 `.venv` 的 Python 版本
和 `google-genai`，不是 Atlas Cloud 的 `ATLASCLOUD_API_KEY`。

只有 Manim 路线才运行：

```bash
bash "<合集根>/scripts/b-roll-generate/manim-setup.sh"
```

## 路由

| 内容责任 | 首选路线 | 关键规则 |
|---|---|---|
| 具体地点、历史实体、真实产品、人物、事件、证据 | 本地素材 / 合规 Stock / 用户素材 | Receipts / Entity 优先；不能用通用概念图冒充实体 |
| 真实网页、产品 UI、合同或报告 | 用户真实截图/录屏，必要时脱敏 | 复刻既有页面必须使用真实页面；不能手搓伪 UI 或伪截图 |
| 流程、架构、责任链、数据、对比 | Remotion | 一个 request 一个 composition；输出透明叠加或全屏插入 |
| 动态字幕、标题、UI 卡、转场、字幕同步 | HyperFrames | 先读对应 style/house style；执行 lint、validate、inspect |
| 纸张拼贴、半调、编辑风、不可拍摄的概念隐喻 | 拼贴路线 | 先确认隐喻和静帧，再做视频；AI 画面必须标明概念性质 |
| 白板手绘、3D/CGI、定格纸艺、Kurzgesagt、概念化信息图等风格化 AI B-roll | AI 生成路线（H3 等） | 写 prompt 前必读 `references/video-prompt-writer/`：按 h3-prompt-structure 三字段组织，按 style-genes 取所选风格的视觉基因/运动语言/负向约束；风格以 `broll-style-decision.md` 的逐条记录为准，不得默认 Vox |
| 数学或技术推导、公式、算法图 | Manim 或 Remotion | 只在数学/技术动画确实需要时使用，不把 Manim 当默认 B-roll 引擎 |
| 单张静态图的微动 | `zoom_still.py` 或 Remotion Ken Burns | 默认静音、轻微运动；不为微动引入 AI 视频模型 |

真实素材路由需要调用素材获取 skill 时，使用 `video-assets` 或
`media-asset-acquirer`，但本 skill 不因缺素材自动升级为 AI 生成。

## AI 生成模式：vox 拼贴 / 首尾帧

AI 路线的**受控**生成有两种模式（纯文生视频不在此列——构图不受控，仅在用户明确接受时使用）；Gate 3 的 prompt 和资产组织都围绕二者：

| 模式 | 何时用 | 静帧 | 动画 | 硬纪律 |
|---|---|---|---|---|
| **vox 拼贴** | editorial 纸拼贴隐喻、抽象概念、不可拍摄场景 | 一张完成态彩色拼贴静帧（黑白半调剪贴骨架 + 彩色卡纸点色 + 平坦色场） | 空场首帧 + 完成静帧的首尾帧组装（assemble-from-empty） | 同批底色必须轮换（见「拼贴风格多样性」）；一条只讲一个隐喻、3–6 个物件 |
| **首尾帧** | 需要精确控制开头/结尾状态的单镜头，任意视觉风格（不限定拼贴） | 完成态尾帧 + 起始态首帧（可以是空场，也可以是状态 A） | 首尾帧模式生成 | 首帧在前、尾帧在后的顺序不可颠倒；两帧都过静帧 QA 才生成视频 |

两条共用纪律：先静帧确认、后视频生成（对应审批闸门的隐喻/静帧/视频三次确认）；视频模型只负责「从首帧组装到尾帧」，不让它自由发挥新构图或新文字。

## 模型可用性与降级级联

第一次调用付费能力前，按以下顺序探测并锁定本 request 的执行引擎；**降级必须获得用户对「换引擎 + 换计费」的确认**并写入 `notes.md`（`engine=<层级>` 记录实际使用的引擎）：

| 层级 | 引擎 | 探测方式 | 用途 |
|---|---|---|---|
| T1 | 配置的 API（`GEMINI_API_KEY` + Gemini/Veo 模型） | `bash "<合集根>/scripts/b-roll-generate/check_setup.sh"`；模型 ID 按 provider live list 核验 | 静帧 + 视频（`generate_video.py` / `generate_veo_first_last.py`） |
| T2 | ChatGPT Web 端 image2（已登录浏览器会话） | T1 不可用（无 key / 模型下线 / 额度耗尽）时降级 | 生成静帧与空场首帧；prompt 仍按 H3 三字段写好再带入 |
| T3 | Google Flow（如有账号） | 需要视频能力而 T1 不可用，或 T1 只完成了静帧时 | 上传已确认的首尾帧（T1 或 T2 产出），用首尾帧模式生成视频 |

级联规则：

- 探测结果只对当前 request 有效；同批各条目可混用层级，但每条的 `notes.md` 必须记录实际层级；
- T1 与 T2 都不可用时，静帧无法 AI 生成：停在「视觉隐喻 + 静帧 prompt 包」交付并告知用户（用户自带静帧时可继续进 T3）；
- T2/T3 是浏览器端操作：产物必须下载落盘到该 request 的 `source/frames/`（`first-frame.png`、`last-frame.png`）与 `out/final.mp4`，命名与 API 路线一致，不留「只在网页里」的资产；
- T3 不可用时停在「确认静帧 + 动画 prompt 包」交付，明确告知用户视频未生成及原因，不伪造输出；
- 降到 T2/T3 会消耗**另一套付费额度**：降级前必须获得用户对「换引擎 + 换计费」的确认，不只是告知；
- 用户明确点名引擎时跳过级联直接用指定引擎；
- 降级不改变已确认的视觉隐喻和静帧——只换执行引擎，不重开审美确认。

## Remotion 参考库使用规则

### 1. `remotion-material`：请求、计划和导出契约

每个 Remotion request 至少写出：

- Motion Request ID 和关联 B-roll ID；
- 精剪时间区间、建议进入词和放置方式；
- `Material Workspace`、`Remotion Project Path`、`Render Output Path`；
- composition name；
- purpose、format、resolution、FPS、duration、background/alpha；
- 画面文字、颜色、safe area、主要动作和静态终态；
- props、数据来源、素材依赖、许可证 manifest；
- 已读的准确模板/scene 文件、参考实现和任何适配改动；
- 两个以上验收帧、风险和回退路线。

必须先生成 `implementation_plan.md`。默认等待用户确认后才写 Remotion 代码；用户明确说
“直接实现/直接生成”时，仍要把计划先写入工作区并记录“direct implementation approved”。

### 2. `remotion-scenes`：场景库，不渲染 showcase

`remotion-scenes` 约 201 个场景，按 `TextAnimations`、`LayoutAnimations`、
`ListAnimations`、`DemoAnimations`、`TransitionAnimations`、`LiquidAnimations`、
`UIAnimations`、`DataAnimations` 等类别组织。使用规则：

1. 先读类别 `index.tsx`，再读准确的 scene TSX 全文；
2. 复制需要的组件到 B-roll 的 Remotion 工程，不从外部参考目录运行时 import；
3. 共享工具优先复用 `src/common/` 的 `C`、`EASE`、`lerp`、`font`；
4. 不把 `Root.tsx` 中的 `*Showcase` 当成最终素材，它只是浏览全部场景的展示 composition；
5. 参考工程 showcase 默认是 `1280x720 @ 30fps`，必须按 motion request 重新注册目标 composition；
6. 一个 B-roll request 只注册一个目标 composition，除非用户明确要求多个可选版本；
7. 复制后运行该项目自己的 `npm run lint`，并执行 TypeScript 检查/Remotion bundle。

### 3. `remotion-templates`：源码参考，不是无条件即插即用

模板库包含 81 个自包含组件，适合快速搭建单一动效，但不少模板仍有演示占位内容或
框架假设。必须读准确源码并适配，不得只凭文件名重写近似版本。

| 视觉目的 | 可优先检查的模板 | 适配要求 |
|---|---|---|
| 单图缓慢推近/平移 | `ken-burns.tsx`、`image-zoom-reveal.tsx`、`parallax-pan.tsx` | 使用本地素材、明确时长和方向；将 CSS/Next 依赖改成 Remotion 帧驱动 |
| 古今/前后对比 | `split-screen.tsx`、`image-comparison-slider.tsx` | 替换 `Panel A/Panel B`、渐变和占位文案；两侧素材必须是真实批准素材 |
| 档案组装 | `photo-stack.tsx`、`image-carousel.tsx`、`gallery-grid.tsx` | 控制图片数量和主动作，不把相册堆叠当作默认装饰 |
| 流程/步骤/责任链 | `progress-steps.tsx`、`animated-list.tsx`，或 `remotion-scenes/ListAnimations` | 每一步必须来自原句或已批准结构，不凭空增加信息 |
| 引用/证据卡 | `quote-card.tsx` | 只有独立 Remotion 卡片被批准时使用；已有 HyperFrames 卡不重复制作 |
| 章节/转场 | `chapter-title.tsx`、`cross-dissolve.tsx`、`fade-through-black.tsx`、`push-transition.tsx` | 只服务于本 request 的单一转场，不让转场成为无意义 B-roll |
| 纸张/墨水/材质 | `noise-grain.tsx`、`liquid-wave.tsx`、Remotion Scenes 的 `LiquidInkSplash` 等 | 只作为已确认视觉语言中的克制材质，不自动套赛博或泛化科技风 |

已知适配风险：

- `ken-burns.tsx` 使用 CSS `@keyframes`，不能直接当成确定性 Remotion 时间线；应改为
  `useCurrentFrame` + `interpolate`，或验证当前渲染器对该实现的可控性；
- `parallax-pan.tsx` 使用 Next `Image`、外部 URL 和 `infinite alternate`，必须改为本地
  `staticFile`/普通可控媒体，并明确单向运动和 settle 终点；
- `split-screen.tsx`、`image-comparison-slider.tsx`、`photo-stack.tsx`、`quote-card.tsx`
  内含演示文本和固定颜色，必须改成 request props；
- 模板源码中的 CSS `animation`、CSS `transition`、`Math.random()`、远程图片、默认占位
  文案和未确认 logo 都视为需要处理的风险，不得原样带入交付素材；
- 具体 scene/demo 的 easing、时值、遮罩和“已知坑”参数是参数真相。允许改品牌 token、素材、
  文案和布局，但不能无理由降低已调好的动作质量。

### 4. 单镜头设计纪律

吸收 `video-shotcraft` 的镜头规则，但只用于 B-roll 单元：

- 每个 request 只讲一个主要动效；
- 每个主动作有开始状态、动作事件、静态终态和至少 0.5s 的 settle/hold；
- 信息卡或关键结论落定后至少 hold 1s；
- 主体动作弧尽量给足约 3s，不用高速入场掩盖素材和文字不可读；
- 相邻 request 不要重复同一种动效作为主角；
- 不使用无叙事理由的 handheld shake、群发 glint、泛化粒子和赛博装饰；
- 要表现真实产品页面时用真实截图；非复刻的解释图才允许手搓组件；
- 禁止 `Date.now()`、`new Date()`、`Math.random()`；需要随机时使用固定 seed 的 Remotion `random`
  或项目内固定 PRNG，使每次渲染逐帧一致。


在 `Polished/B-roll/<id>_<slug>/implementation_plan.md` 写入：

```md
# Implementation Plan

- Motion Request ID: BROLL-001
- Video Project Folder: <project>
- Material Workspace: Polished/B-roll/BROLL-001_<slug>/
- Remotion Project Path: .../remotion-project/
- Render Output Path: .../out/
- Composition Name: BrollB001
- Purpose: ...
- Format: MP4 insert / ProRes 4444 / transparent WebM / PNG sequence
- Resolution / FPS: 1920x1080, 30fps
- Duration: 4.0s

## Timeline Plan

- 0.0-0.8s: 开始状态/素材进入
- 0.8-2.8s: 唯一主要动作
- 2.8-4.0s: 终态停留和交接

## Layout Plan

- full-frame insert / transparent overlay
- title-safe、字幕安全区、人物脸和产品 UI 避让规则

## Props Design

- sourceAsset
- labels
- accentColor
- motionDirection
- animationSpeed
- showSourceLabel

## Data / Source / License

- source file and checksum
- source URL / author / license / access date
- user approval record

## Library Choices

- exact template or scene path
- exact demo/index path
- copied and adapted files
- new dependencies: none, or reason

## Export and QA Frames

- still frames: entry / action peak / settled / exit
- MP4/alpha format and import target
- risks and fallback
```

## Gate 1：实现计划确认

🔴 **CHECKPOINT：Remotion 路线的 `implementation_plan.md` 写好后必须等用户确认（或用户明说「直接实现」并记录 `direct implementation approved`），才允许进入 Gate 2 写生产代码。付费模型调用前同理——没有明确批准记录就停在计划阶段。**

## Gate 2：Remotion 实现

### 工程结构

每个 request 独立工作区：

```text
Polished/B-roll/BROLL-001_<slug>/
├── brief.md
├── implementation_plan.md
├── style-decision.md
├── remotion-project/
│   ├── package.json
│   ├── src/index.ts
│   ├── src/Root.tsx
│   ├── src/<BrollComponent>.tsx
│   └── public/
├── prompt/
├── source/
├── out/
├── qa/
├── qa.md
└── notes.md
```

不要把 201 场景的 showcase、81 模板的演示页或多个 request 合成一条最终视频。

### 实现规则

- 复制准确参考源码后适配，不 import 外部 references 目录；
- 时间由 `useCurrentFrame`、`useVideoConfig`、`interpolate`、`spring` 和 `Sequence` 控制；
- 所有可变内容通过 props 或 `--props` 进入，不能把项目素材、颜色、文字和时长锁在组件内部；
- 图片、字体、logo、截图全部本地化并记录来源，运行时不依赖远程 URL；
- 文本必须处于 safe area；1080p 中“要读”的主字幕有效字高至少约 56px，辅助文字至少约 32px；
- 默认不在 B-roll 组件内添加音频；如用户批准声音，单独写 audio plan 和来源清单，按时间线集中管理；
- 透明 overlay 不绘制背景、不留下黑色 matte；全屏 insert 才使用背景；
- 任何真实产品页面都用真实截图，任何 mock 数据都要在 brief 中标记为虚构/脱敏；
- 每轮改动后先 `still`，再整片 render；不要把首检交给用户。

### 透明度和格式选择

| 用途 | 首选输出 | 备用 |
|---|---|---|
| 全屏解释片/图像 B-roll | MP4 insert | - |
| 剪映/CapCut 透明叠加 | ProRes 4444 `.mov` | PNG sequence |
| 支持 alpha 的轻量叠加 | transparent WebM | PNG sequence |
| 编辑器 alpha 导入不稳定 | PNG sequence | magenta-key MP4 仅作为最后回退 |

对于剪映/CapCut，ProRes 4444 是优先透明交付格式，即使 Windows 播放器不能预览，也要
用 `ffprobe` 或导入剪映验证，不能以播放器黑底判断失败。

## Gate 3：拼贴和 AI 生成路线

Remotion 不是所有 B-roll 的默认引擎。选择拼贴或 AI 时，先完成以下顺序：

0. 读取 `references/video-prompt-writer/h3-prompt-structure.md` 和所选风格在 `references/video-prompt-writer/style-genes.md` 中的基因块；prompt 按三字段结构写，风格基因进 `[Shot 1]` 开头声明，负向约束随 prompt 提交；B-roll 默认静音，`overall_soundscape`/`non_diegetic_music` 写 `N/A`，仅用户批准触感音效时描述真实动作声；
1. 用户确认视觉隐喻和语义边界；
2. 确认第一帧/静帧/最后一帧或图片输入；
3. 先检查静帧质量，再请求视频生成；
4. 生成 3-6s 的短镜头，单镜不要超过约 7s；超过时拆成 wide + detail，而不是一条长 prompt；
5. 对相邻镜头交替安全的 camera move；结论/重点镜头可使用 `static`；
6. camera move 和 element motion 分开写；元素可以丰富运动，但必须保持平面、刚性、稳定文字；
7. 运动 prompt 使用单一连续动作、低幅度、明确 settle 终点；不要把 snap、slam、quick zoom 等多个动作塞在一镜；
8. 关键文字在静帧中确定，视频模型只要求保持稳定，不让视频模型重新生成文字；
9. 生成结束后立即静音、抽帧、检查时长和画幅，再写 QA。

### 拼贴风格多样性（防审美疲劳）

底色按语意轮换，禁止把任何一种颜色当默认值（包括钴蓝和深电光蓝）：

| 色场 | 语义倾向 | 参考 hex |
|---|---|---|
| 焦橙 / 红 | 时间消耗、劳动、紧迫 | `#C8551B` / `#B3312C` |
| 芥末黄 | 工具、警示、经验漏失 | `#C9A227` |
| 墨绿 | 认知、审美、系统重置 | `#1E4D3B` |
| 深紫 | 规范、沉淀、长期记忆 | `#3B2A6B` |
| 青绿 | 判断、协作、自动执行 | `#14707E` |
| 钴蓝 / 深电光蓝 | 冷静、技术、信息（仅当语义匹配时用） | `#17324D` |

参考 hex 是起点不是约束，可按品牌色微调；实际使用的 hex 必须写入 manifest。

批次纪律：

- 同一视频内相邻两条 B-roll 不同底色；一批 N 条至少覆盖 ⌈N/3⌉ 种色系；
- 统一的是设计语言（半调质感、裁切边、keyline、阴影、颗粒），变化的是底色与点色——「同语言、不同底」；
- 每条的底色 hex 写入 `broll-manifest.md` 的颜色字段；生成下一条前先读 manifest 查最近用色，避免撞色；
- 连续两期视频主色系相同时，在 manifest 顶部标注提醒并给下一期差异化建议。

### Vox / Atlas 和 Gemini 是两条不同路线

不要混用 API key、模型 ID 或脚本：

- 当前合集脚本 `scripts/b-roll-generate/generate_video.py` 使用 `google-genai` 和
  `GEMINI_API_KEY`；实际支持 `--batch`（JSON 作业文件）、`--prompts-file`、`--concurrency`、
  `--aspect-ratio 16:9|9:16`、整数 `3-10s` 的 `--duration`、`--strip-audio`、`--image/--video`
  多值输入和 `--previous-interaction-id` 接续编辑；**没有 `--dry-run` 和首尾帧参数**，
  首尾帧生成用 `generate_veo_first_last.py`；
- `<外部参考项目根>\vox-director` 是 Atlas Cloud 参考 skill，使用它的
  `ATLASCLOUD_API_KEY`、model/provider 和自身脚本契约；仅在用户明确选择 Vox/Atlas 路线时使用；
- Gemini 当前生成脚本默认模型名为 `gemini-omni-flash-preview`，但模型 ID 会变，付费调用前必须
  按当前 provider 的 live model list 或脚本/SDK 文档核验，不把旧默认值当永久契约；
- 没有 key 或模型未确认时，只输出提示词包和作业清单（`--prompts-file` 的内容），不调用 API；
- 本地视频输入需要默认去除源音时使用 `--strip-audio`，但远程 File URI 不能由脚本自动静音；
- 生成 API 的输入视频/图片、模型、画幅和时长全部写入 `notes.md`，不能只留在聊天记录。

Vox 路线写 prompt 前必须读取 `vox-director/references/prompt-guide.md` 和
`beat-layer.md`。图像 prompt 的风格 block、分层 cut-out、平面纸张约束和运动 prompt 的
5-axis 结构不能省略。若使用高级元素级路线，读取 `local-engine.md`，并记录为何没有采用
更便宜的普通 Remotion/静态微动路线。

### first/last frame 路线

如果使用显式起止帧，用 `generate_veo_first_last.py`（必需参数：`--first-frame`、`--last-frame`、
`--prompt-file`、`--output-dir`、`--gcs-uri`；可用 `--dry-run` 预检。**默认 9:16/720p/Veo 3.1 fast**，
横屏项目必须显式传 `--aspect-ratio 16:9 --resolution 1080p`）。尾帧的画幅归一（只是缩放加边）
用 ffmpeg 完成，参数写入 `notes.md`：

```bash
# 尾帧归一（示例：把已确认静帧统一为 1920x1080、指定底色加边）——不是空场首帧，空场首帧走「空场首帧派生」
ffmpeg -y -i "<approved-still>" -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x17324D" "<project>/Polished/B-roll/BROLL-001/source/frames/last-frame.png"

uv run --project "<合集根>" python "<合集根>/scripts/b-roll-generate/generate_veo_first_last.py" \
  --first-frame "<project>/Polished/B-roll/BROLL-001/source/frames/first-frame.png" \
  --last-frame "<project>/Polished/B-roll/BROLL-001/source/frames/last-frame.png" \
  --prompt-file "<project>/Polished/B-roll/BROLL-001/prompt/motion.md" \
  --output-dir "<project>/Polished/B-roll/BROLL-001/out" \
  --gcs-uri "<GCS/云存储 URI>" \
  --aspect-ratio 16:9 --resolution 1080p --dry-run
```

横屏项目必须显式控制宽、高和预期时长，不依赖任何默认值。

**空场首帧派生**（拼贴/组装类镜头的关键步骤）：不要用 ffmpeg 纯色图当首帧——以确认过的完成静帧为参考做图生图「清空」（prompt 方向：移除全部主体、卡片与阴影，仅保留完全相同的底色、纸纹与颗粒），得到的首帧与尾帧底色纹理天然一致，动画不会有底色跳变。T1 用 API 的图片编辑能力；T2 用 ChatGPT Web image2 的参考图编辑。派生帧只做自动 QA（干净空场、无残影、底色一致），**不为它单开用户确认门**；一次不合格重跑，仍不合格退回同底色文生图兜底并在交付说明注明。

## 导出命令

从 Remotion project 根目录执行，输出写入同一 request 的 `../out/`：

```bash
# Studio
npm run dev

# 单帧检查
npx remotion still <COMPOSITION_ID> --frame=<FRAME> --scale=0.5

# 全屏 MP4 insert
npx remotion render <COMPOSITION_ID> ../out/<name>.mp4

# 透明 WebM
npx remotion render <COMPOSITION_ID> ../out/<name>.webm \
  --image-format=png --pixel-format=yuva420p --codec=vp8

# PNG sequence
npx remotion render <COMPOSITION_ID> ../out/<name>-sequence \
  --sequence --image-format=png

# 剪映/CapCut 优先透明格式
npx remotion render <COMPOSITION_ID> ../out/<name>.mov \
  --image-format=png --pixel-format=yuva444p10le \
  --codec=prores --prores-profile=4444
```

如果项目的 Remotion CLI 需要 entrypoint，按该项目 `package.json` 的 script 补上
`src/index.ts`，不要改成运行外部 showcase。

## Gate 4：逐条 QA

每个 request 需要在 `qa/` 保存入场、中点/动作峰值、终态和出场关键帧，并在 `qa.md` 写出证据。

### 视频和画面

- 分辨率、FPS、时长和画幅符合 implementation plan；
- 画面完整，无 letterbox、黑边、错误 crop、半屏残片或透明黑底；
- 关键元素在 safe area 内，人物脸、主字幕和产品 UI 没有被覆盖；
- 文字清晰、对比度足够、没有 3D 缩放糊字；
- 只有一个主要动效，开始状态、动作峰值、终态和 hold 都存在；
- 入点不早于关键词，出点不制造小于 1 秒的人物碎片；
- 无非叙事 handheld shake、群发 glint、随机抖动或不确定性差异；
- 两次渲染的相同 QA 帧内容一致，或差异有明确来源并记录；
- 对真实网页/产品/证据，逐帧核对来源和脱敏状态；
- AI 画面没有假字、伪 logo、错误 UI、伪历史标签、新闻式误导或语义漂移。

### 音频

B-roll 默认静音。用 `ffprobe` 检查没有音频流；如果用户明确批准保留现场声或 SFX：

- 音频来源、许可证、起止时间和音量写入 manifest；
- 不重复 A-roll 台词，不让源音覆盖主口播；
- 音效按真实动作选择，不使用没有叙事理由的游戏式 bleep/notification；
- 时长超过 5s 的音频显式截断，不能拖过动作结束；
- 画面时间线改变后，所有音频钉帧重新对齐。

### 机器检查

至少执行：

```bash
ffprobe -v error -show_streams -show_format -of json "<output>"
ffmpeg -v error -i "<output>" -f null NUL
```

透明输出额外检查 `pix_fmt` 是否为 `yuva...`，并检查 alpha 在透明处不是黑色实底。
拼贴 first/last 路线的静帧比对用 ffmpeg 抽帧后人工/Agent 目检：

```bash
# 在动作起点、中点、终态各抽一帧做比对
ffmpeg -ss <T> -i "<video>" -frames:v 1 "<qa-dir>/frame-<T>.png"
```

HyperFrames 路线额外执行：

```bash
node "<合集根>/scripts/b-roll-generate/animation-map.mjs" \
  "<project>/Polished/B-roll/BROLL-001/source/hyperframes" \
  --out "<project>/Polished/B-roll/BROLL-001/qa/anim-map"

node "<合集根>/scripts/b-roll-generate/contrast-report.mjs" \
  "<project>/Polished/B-roll/BROLL-001/source/hyperframes" \
  --out "<project>/Polished/B-roll/BROLL-001/qa/contrast"
```

`contrast-report.mjs` 是 HyperFrames DOM/像素检查，不要把它冒充成 Remotion 的通用 QA；
Remotion 以 still、render、ffprobe 和人工抽帧为主。

## 输出和交接

每个通过 QA 的 request：

```text
Polished/B-roll/BROLL-001_<slug>/
├── brief.md
├── implementation_plan.md
├── style-decision.md
├── prompt/
│   ├── image.md
│   └── motion.md
├── source/
│   ├── assets/
│   ├── frames/
│   └── remotion-reference/
├── remotion-project/          # Remotion 路线
├── out/
│   ├── preview.mp4
│   ├── final.mp4
│   ├── final.mov              # 若批准透明 ProRes
│   ├── final.webm             # 若批准透明 WebM
│   └── final-sequence/         # 若使用 PNG sequence
├── qa/
│   ├── still-entry.png
│   ├── still-peak.png
│   ├── still-settle.png
│   └── contact-sheet.jpg
├── qa.md
└── notes.md
```

同时写入：

- `<project>/Polished/broll-manifest.md`：编号、原句、时间、文件、路由、版本、来源、许可证、
  用户批准时间、输出规格、音频状态、QA 结果和底色 hex（拼贴/AI 路线必填，用于批次防撞色）；
- `<project>/Polished/broll-placement.json`：供 `video-polish` 使用的机器可读放置表；
- `.video-workflow-state.json`：仅在条目 QA 通过后更新 `generated_count` 和状态。

放置 JSON 使用 `video-polish/render_cutaways.py` 能读的字段：

```json
{
  "beats": [
    {
      "id": "BROLL-001",
      "start": 3.35,
      "end": 11.0,
      "file": "B-roll/BROLL-001_brick/out/final.mp4",
      "kind": "video",
      "source_start": 0
    }
  ]
}
```

`broll-placement.json` 不是主视频时间线。它只声明切入区间和素材路径，实际装配仍由
`/video-polish` 执行。全屏 cutaway 脚本会去除 B-roll 自带音频并保留 base 的 A-roll 音频；透明
overlay 则按剪映/编辑器的 alpha 工作流装配。

## 状态机

```text
finder: recommended
  -> user_approved
  -> implementation_plan_approved
  -> generating
  -> qa
  -> ready_for_polish
```

失败时只把当前条目标为 `needs_revision`，不要重跑已通过的条目。未批准、缺素材、缺许可证、
缺模型或缺 API key 时标记 `awaiting_*`，不伪造输出。

## 禁止

- 未经用户批准调用付费视频/图片模型；
- 把“推荐”当成“approved”；
- 把 Remotion showcase、模板 demo 或外部 skill 目录直接当成最终素材；
- 只按模板文件名重写动画，跳过准确 demo 源码和已知坑；
- 用外部远程图片、Next.js 组件、CSS 不确定动画或未固定随机数生产不可复现素材；
- 把真实页面、合同、新闻、文物、产品界面或研究结果交给 AI 伪造；
- 把所有 B-roll 都路由到同一个引擎；
- 在组件里偷偷添加 BGM/对白/随机音效；
- 覆盖用户确认的旧版本；
- 生成完整主视频来替代 `/video-polish`；
- 未做静帧、ffprobe、解码和来源核验就更新 manifest 为 `ready`。
