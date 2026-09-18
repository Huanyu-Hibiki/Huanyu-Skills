# 视频口播自动剪辑与剪映草稿适配设计

## 目标

将 `video-production-workflow` 的默认主线从“自动粗剪后必须人工精剪”升级为“自动生成可继续编辑的剪映草稿”，优先服务单人口播/课程视频，兼容有明确锚点的 OBS 录屏插入。

系统应自动完成高置信度的机械剪辑，生成可审计、可回滚的时间线计划、剪映原生草稿及预览视频；表达、节奏和录屏语义不确定之处必须进入显式复核队列，不能静默删改。

## 用户场景

1. 用户提供口播原片和已确认文稿，系统转录、对齐、选择最佳 take、剪除明确重复/口癖并收紧安全停顿，输出可打开的剪映草稿。
2. 用户在剪映内从自动草稿微调节奏、恢复任意自动删除片段，并继续添加 B-roll、音乐和风格效果。
3. 用户提供带章节或文稿锚点的 OBS 录屏时，系统把对应区间放到独立的 `Screen Demo` 轨道；锚点不可靠时只创建待放置提示，不猜测插入位置。
4. 低置信转录、整段重读、多人说话、音乐或情绪性停顿等高风险情况不会被自动破坏，而会在报告中逐项说明并等待人工裁决。

## 技术方案

### 目标流程

```text
Raw 原片 + 确认文稿
  -> video-rough-cut（转录、对齐、take/停顿/重复分析）
  -> video-auto-edit（生成、校验、解释 edit-plan）
  -> video-jianying-draft apply_edit_plan（写剪映草稿）
  -> FFmpeg 预览 + 草稿回读 QA
  -> B-roll 机会判定、三路生成/切片与落位
  -> 人工仅复核 reviewQueue / 在剪映内微调
  -> 装配、成片
```

`video-rough-cut` 继续作为分析与基础决策阶段，保留 `transcribe.py`、`align_to_manuscript.py`、`select_takes.py`、`tighten_pauses.py` 和重复检测。它不再承担下游剪映时间线策略。

新增 `/video-auto-edit` 子 skill 及对应脚本。它只消费已存在的结构化分析产物，负责合成、校验、说明编辑计划，不能重新转录或绕过上游证据。

`video-fine-cut` 从默认必经的人工作业改为可选人工接管阶段。旧项目及明确指定 `--manual` 的新项目继续采用原流程。B-roll 在 A-roll 自动计划稳定后并行启动，最终由同一编辑计划汇总到剪映草稿。

### 编辑计划契约

新增项目级真相源：`Rough/edit-plan.v1.json`。它是中立的、可审计的时间线合同，不是剪映私有格式；FFmpeg 预览与剪映草稿必须由同一份计划派生。

核心字段：

```json
{
  "version": "1",
  "source": "Raw/camera-01.mp4",
  "timeline": [
    {
      "id": "keep-001",
      "op": "keep",
      "sourceStart": 12.4,
      "sourceEnd": 18.75,
      "targetStart": 0,
      "reason": ["manuscript_match", "best_take"],
      "confidence": 0.98,
      "undoGroup": "sentence-001"
    },
    {
      "id": "trim-001",
      "op": "remove",
      "sourceStart": 18.75,
      "sourceEnd": 19.62,
      "reason": ["intra_sentence_pause"],
      "confidence": 0.94,
      "undoGroup": "sentence-001"
    },
    {
      "id": "screen-001",
      "op": "insert_screen_demo",
      "source": "Raw/obs-demo.mp4",
      "sourceStart": 42.0,
      "sourceEnd": 48.5,
      "targetStart": 75.2,
      "anchor": "点击发布按钮",
      "status": "proposed"
    }
  ],
  "reviewQueue": []
}
```

每项操作都必须保留原始时间码、证据来源、置信度和 `undoGroup`；下游禁止通过聊天上下文推断任何时间轴决定。

### 自动决策等级

| 级别 | 策略 | 例子 |
|---|---|---|
| A | 高置信、低语义风险，直接执行 | 句间静音；明确口癖；一句话中断后立即重说 |
| B | 自动执行但必须留回滚信息 | 0.35–1.2 秒句中停顿压缩；语义完整但较差的重复 take |
| C | 不修改主轨，只写入 `reviewQueue` | 整段重读；低置信转录；多人重叠；音乐段；情绪性拉长；不可靠的 OBS 锚点 |

默认策略：

- 句间静音保留 0.18–0.35 秒自然间隔；
- 句中停顿超过 0.35 秒时压缩到约 0.25 秒；低音量、多人声、音乐或情绪特征存在时降级到 C；
- 明确口癖、结巴与“说到一半立即重说”可自动剪除；整句重读仅在候选 take 均高置信时自动选择较优版本；
- 自动删除量超过原片 35%、未匹配文稿超过 5%、或 C 级项目超过 3 项时，不提交自动草稿，只产出诊断报告；
- 录屏仅在文稿锚点与 OBS 章节/用户标记同时成立时自动上轨，否则生成待放置标记卡。

### 句尾保护与全时间线停顿压缩

自动剪辑的最高优先级是**不得截断已表达的内容**。现有“ASR 词尾时间码 + 固定尾部 padding”不能独立证明真实语音已结束，不能作为唯一裁切依据。每个候选切点必须经过如下独立链路：

```text
ASR 词级候选边界
  -> 音频 VAD / 能量检测确认
  -> 文稿句尾保护窗检查
  -> 在稳定静音中吸附边界
  -> 才可写入 edit-plan
```

- 每句最后 3–5 个有效字符必须同时满足：文稿匹配、词级置信度合格、以及实际音频语音活动已结束；
- 若尾部保护窗仍检测到语音活动，切点必须延展到稳定静音后，不能以固定 `0.30s` tail padding 强行截断；
- 语音活动、词级时间码或文稿尾部任一项不确定时，保留整段并进入 `reviewQueue`，绝不剪成不完整句；
- 验收不可使用同一份 ASR 同时做“裁切决定”和“裁切正确性证明”：必须对每个切点前后抽取音频窗口，检测是否在发声中截断；
- 示例回归句为 `当畜五牸，意思就是养母畜。`，验收必须证明裁切点位于最后一个“畜”的尾音结束之后。

停顿处理必须在**最终 A-roll 时间线**统一执行，而非仅在一个 keep 内查相邻 ASR 词：

- 任何最终相邻片段之间或片段内部，超过 `0.35s` 的安全静音均压缩至约 `0.25s`；
- 跨 take/跨 keep 的长间隔与句内停顿使用同一规则，并在 `edit-plan` 中留下压缩前后的时间码；
- 若区域存在语音活动、音乐、多人声、低置信转录或情绪性拉长，降级到 `reviewQueue`，不做盲剪；
- ASR 在静音区产生虚假词时，VAD/能量检查必须优先于文本间隔，避免把真实长静音错误地当成连续口播；
- `auto-cut-report.md` 必须报告检测到、压缩掉、保留和转人工的停顿数与总秒数。

### 剪映草稿适配

扩展现有 `scripts/video-jianying-draft/jianying.py`，新增 `apply_edit_plan` 子命令：

```text
apply_edit_plan
  -> 读取 Rough/edit-plan.v1.json
  -> 写入 A-roll Final / A-roll Recovery / Screen Demo 三组轨道
  -> 导入对齐字幕
  -> 生成 Drafts/auto-cut-report.md
```

- `A-roll Final`：自动选定、可直接播放的主时间线。
- `A-roll Recovery`：自动删掉的原片，按源时间码保留，默认禁用或静音，供人工快速恢复。
- `Screen Demo`：已验证锚点的录屏区间；未验证项仅创建视觉标记，不能伪造已插入状态。

现有的 `load_beats`、字幕拆分、转场/关键帧/滤镜等命令保持兼容，仍由后续 B-roll 或人工工作使用。

### B-roll 生成、落位与风格系统

B-roll 是默认自动主线的一部分，而不是人工精剪后的装饰性可选步骤。系统仅以三条可控的内部路由生成或装配 B-roll：

| 路由 | 适用内容 | 主要产物 | 剪映轨道 |
|---|---|---|---|
| `packaging` | 章节、引语、关键词、数据、流程、转场桥接 | Remotion 或 HyperFrames 参数化包装片段 | `B-roll Packaging` |
| `ai_visual` | 概念隐喻、Vox 风格解释、定格动画、不可拍摄场景 | 图片模型关键帧 + 视频模型或动画编排生成的无声片段 | `B-roll AI Visual` |
| `screen_demo` | 产品操作、网页证据、软件步骤 | 由 OBS/无声录屏按锚点裁切，必要时附放大、标注、遮罩 | `Screen Demo` |

现实证据、产品真实状态或网页事实只能使用 `screen_demo` 的真实录屏；AI 视觉不得替代或伪造证据。录屏仅在文稿锚点与 OBS 章节或用户标记都匹配时自动上轨，否则创建待放置标记。

新增 `B-roll Style System`：

```text
精剪 A-roll 时间线 + 对齐字幕 + 视频风格档
  -> 视觉意图（证明 / 解释 / 隐喻 / 节奏 / 包装）
  -> 镜头语法（构图、相机、转场、动势）
  -> 路由（packaging / ai_visual / screen_demo）
  -> 风格包与参数化模板
  -> B-roll manifest + edit-plan
  -> 剪映草稿、预览和 QA
```

风格包与其主要实现：

| 风格包 | 主视觉与镜头语法 | 优先引擎 |
|---|---|---|
| `documentary_observe` | 真实录屏、局部放大、区域/鼠标引导、克制切换 | 剪映 + Remotion |
| `vox_explainer` | 拼贴、地图/数据/物件、图文分层推进 | 图片/视频模型 + Remotion |
| `stop_motion_craft` | 纸张、实物、撕贴、逐帧移动、纹理 | 图片模型 + 视频模型 |
| `editorial_magazine` | 强构图、图文遮罩、照片裁切、节奏性镜头 | HyperFrames + Remotion |
| `product_cinematic` | UI/产品景别变化、相机推拉、光影/材质、少文字 | Remotion |
| `motion_packaging` | 章节、引语、关键结论、数据爆点、转场桥接 | HyperFrames |

HyperFrames 应提供可复用的 frame/design token、HTML 组合、媒体轨和 seek-safe 动画；Remotion 应提供 props 驱动的独立场景、序列、镜头运动和转场。两者都不是单一“文字卡”模板引擎。实现时可从 `hyperframes-main` 提取 composition/registry 与 design-token 思路，从 `remotion template`、`remotion-main`、`remotion-templates` 提取参数化场景与渲染契约，从 `video-shotcraft` 提取镜头/相机/转场语法，从 `video-talkcraft` 提取人物避让、镜头边界和静帧/时域验收纪律；不复制其完整 UI 或运行时。

每个 B-roll 机会必须生成 `shot brief`，包括视觉意图、主视觉、构图、相机或对象运动、入/出场、时长、避让区、引擎、风格包和验收帧。B-roll manifest 的每项至少含 `anchor`、`start`、`end`、`layer`、`route`、`source/provenance`、`stylePack` 和 `status`。

为防止“PPT 感”，新增机器可检查的多样性与静态风险约束：

- 相邻 B-roll 不可复用同一构图、同一动势或同一文字卡模板；
- 每一镜必须有可见主视觉，且包装镜头必须具有对象或相机运动；
- 单帧文字遵循简短、单焦点、安全边距规则；
- 人物在场时，文字、卡片与其背景均不得进入人脸安全区；
- 每个 B-roll 必抽入点、中点、出点和转场窗口帧；动态镜头额外检查闪烁、冻结、遮挡和接缝；
- 未通过素材/渲染 QA 或无法满足风格包的条目不得写入主 B-roll 轨，只能进入 `reviewQueue`。

## 数据模型

除 `edit-plan.v1.json` 外，新增：

- `Rough/auto-cut-report.md`：操作摘要、删减统计、复核队列与可执行的人工处置说明；
- `Rough/auto-cut-validation.json`：计划结构、文稿覆盖、预览与草稿回读校验的机器可读结果；
- `Rough/auto-cut-preview.mp4`：由同一编辑计划渲染的验收预览。
- `Rough/cut-boundary-report.json`：每个切点的 ASR 候选、VAD/能量结果、句尾保护状态、最终吸附位置与放行结论；
- `Polished/broll-manifest.v1.json`：B-roll 机会、镜头简报、路由、风格包、素材来源、落位和 QA 状态；
- `Polished/broll-style-profile.json`：本期批准的风格包、可用模板、禁用样式和镜头多样性预算。

`reviewQueue` 项目最少应包含 `id`、风险原因、源时间码、建议动作、关联文稿句和原始证据路径。

## 接口设计

建议的命令边界：

```text
video-auto-edit plan <project> [--manual] [--obs-manifest <path>]
video-auto-edit validate <project>
video-jianying-draft apply_edit_plan --draft-id <id> --cache-dir <dir> --plan <path>
video-auto-edit preview <project> --plan <path>
video-auto-edit verify-draft <project> --plan <path> --draft <path>
b-roll-finder plan <project> --style-profile <path>
b-roll-generate render <project> --manifest <path>
```

实现阶段应添加 JSON Schema 或等价的严格验证，至少约束操作类型、数值时间码、路径、置信度范围、`targetStart` 单调性和不重叠区间。

## 错误处理

| 条件 | 行为 |
|---|---|
| 原片、转录或文稿缺失 | 不生成计划；指出缺失交接物 |
| 计划结构非法、源片段越界或目标片段重叠 | 阻断草稿写入，输出验证错误 |
| 低置信/高风险超过阈值 | 不提交草稿，输出诊断与 reviewQueue |
| OBS 锚点不匹配 | 不自动插入录屏，生成待放置标记 |
| 句尾保护窗仍有语音，或 VAD 与 ASR 时间码冲突 | 保留到稳定静音或进入 `reviewQueue`；禁止截断句尾 |
| 跨 keep 长停顿未被识别或静音中存在 ASR 虚假词 | 在全时间线 gap pass 中由 VAD/能量重新判断；不以 ASR 文本连续性跳过 |
| B-roll 风格包、模板或素材不匹配 | 不写入主轨，记录镜头简报和替代路由，转入 `reviewQueue` |
| AI 视觉被要求表现真实证据 | 拒绝 AI 视觉路由，要求真实录屏或明确标为示意 |
| B-roll 呈现静态文字卡、相邻镜头重复或人物避让失败 | 标记 PPT/构图 QA 失败，阻断该条目落位 |
| 剪映草稿写入或回读失败 | 保留计划与预览，明确降级为手工导入；不得宣称草稿已生成 |
| 预览与计划的总时长、片段数不一致 | 视为 QA 失败，阻断自动交接 |

## 测试策略

使用可重复的 fixture 与无 GUI 的计划验证覆盖三类案例：

1. 单人普通口播：自动处理明确重复、口癖和停顿，草稿计划与预览时长一致。
2. 低置信或完整重读口播：不误删，所有高风险项进入 `reviewQueue`。
3. 含 OBS 录屏：带章节标记时生成 `Screen Demo` 操作；无标记时只生成待放置项。
4. 六种 B-roll 风格包：验证路由、镜头简报、模板参数、相邻镜头多样性和首/中/尾帧 QA。
5. 句尾保护：`当畜五牸，意思就是养母畜。` 的最终切点必须在末字尾音后；ASR 提前词尾和低置信尾词均不得导致截断。
6. 停顿压缩：验证句内、跨 keep 的长静音均可压缩；有音乐/多人声/ASR 幻觉的区间必须转复核，不能盲剪。

每类案例测试：

- `edit-plan` Schema 和时间轴不变量；
- 文稿保留覆盖率与删减阈值；
- FFmpeg 预览可探测、时长连续；
- 剪映草稿回读的轨道、片段数、字幕与计划一致；
- B-roll manifest 与剪映的 `B-roll Packaging`、`B-roll AI Visual`、`Screen Demo` 轨道一致；
- 包装片段具有可见主视觉与非静态动势，相邻镜头不触发同构图/同模板风险；
- 每个 A-roll 切点有独立的音频活动检测结果；未稳定静音的切点不允许进入主轨；
- 全时间线停顿报告覆盖片段内和片段间间隔，并能逐项回溯到 `edit-plan` 操作。
- `--manual` 旧路径不变。

## 迁移与兼容性

- 旧项目不迁移，继续使用 `video-rough-cut -> video-fine-cut`；
- 新项目默认启用自动草稿路径，可通过 `--manual` 明确切回旧路径；
- B-roll Finder 优先读取自动计划派生的对齐字幕；人工精剪后生成的 `Sub/master.srt` 仍是最终时间轴的覆盖来源；
- 参考 OpenChatCut 的声明式时间线合同、OpenMontage 的 pipeline/schema 验证、`jianying-editor-skill` 的自动粗剪和 Remotion/HyperFrames 的参数化渲染思想，但不嵌入其 Electron UI、云模型或整套运行时。
