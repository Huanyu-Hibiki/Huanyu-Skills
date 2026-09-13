# 动效模板选型与渲染前检查（registry 方法论）

> 方法论吸收自 remotion-templates（1000 模板库）、video-forge、remotion-scenes、HyperFrames 官方 skills 与 Remotion 官方文档（parameterized-rendering / schemas / transparent-videos / prores）。
> **许可证边界**见文末与 [../../shared-references/external-references.md](../../shared-references/external-references.md)——本文档只登记思路与规则，不复制任何外部代码/资产。

## 1. 选型从"三分类推断"升级为"注册表查表"

路由规则（流程/数据→Remotion 等）只做**粗筛**；落到具体 B-roll 条目时，应查机器可读模板注册表精确选型，而不是靠每条重新推断。一个可维护的模板池条目至少包含：

```yaml
id: kinetic-typography-impact        # 模板/场景唯一名
visualRole: keyword-emphasis         # 机器可读视觉角色（证据/实体/概念/强调/标题卡…）
category: typography                 # 大类
tags: [标题卡, 关键词, 转场]
bestUseCases: [观点强调, 章节分隔]
durationRange: [2, 6]                # 秒；时长上下限
textLength: {min: 2, max: 12}        # 文案显示单位上下限（汉字1/ASCII0.5）
pairWith: [lower-thirds, background-loops]   # 官方推荐搭配
defaultProps: { variant: impact, paletteName: deep-blue }
```

- 选型动作 = 「visualRole + 时长 + 文案长度 + 风格闸门」四条件匹配，产出 ≤3 个候选给用户挑；
- 新增模板必须先登记进注册表（含一帧已渲染样图路径），未登记模板不进入候选；
- 同类形态收敛为 **family-engine × variant × palette** 三参数派生（1 个引擎产出 10 个变体），避免模板数随风格线性膨胀。

## 2. Props 契约层：约束在生成端，不在渲染端

每个模板声明字段级约束（Remotion 用 Zod schema，其他引擎等价的校验层）：

- 文案长度 `textLength{min,max}`——超限直接拒绝生成，让 LLM 重写文案，而不是渲染出烂版再返工；
- 时长 `durationRange`、必填槽位 `requiredSlots`、搭配建议 `pairWith`、每个 input 的 `purpose/advice`（例："用目标画幅下最长的真实文案测排版"）；
- 颜色统一走 palette token（`zColor` 类），禁止散落硬编码 hex。

## 3. 时长：内容驱动，默认值退化为 fallback

五相位时间轴的固定默认值（标题 4s、概念 4-6s、流程 5-8s）是**无内容时的假设**。引擎支持元数据函数时（Remotion `calculateMetadata`），由 props 推导 `durationInFrames`：字数/条目数/字幕词数 → 帧数。推导失败或引擎不支持时才回落默认值，并在 notes.md 记录 `duration=derived|default`。

## 4. 渲染前检查层（花钱/长时间渲染之前）

Gate（三帧静图 + 3s 短样片）之前加一道**机械快检**，把"渲完才发现烂版"挡在渲染前：

| 检查 | 做法 | 拦截什么 |
|---|---|---|
| 类型/构建 | `tsc --noEmit`（Remotion）或引擎等价 lint | 属性拼错、props 缺字段 |
| 静默布局错 | HyperFrames `lint/check/doctor`；Remotion 渲首帧 `remotion still --frame=0 --scale=0.5` | 根元素未定尺寸、clip 缺时序属性、黑屏首帧 |
| 三帧样图 | `renderStill`（首/中/尾帧，降分辨率）脚本化出图，交风格闸门 | 风格不符、排版溢出、对齐错误 |

三帧静图 gate 可以完全脚本化（每模板渲首/中两帧的 smoke 是成熟做法），人工只确认风格方向。

## 5. 透明通道 × 渲染环境组合规则

| 场景 | 格式 | 原因 |
|---|---|---|
| 本地单趟渲染 | 透明 WebM（VP8/VP9 + `--image-format=png --pixel-format=yuva420p`） | 体积小，alpha 正常 |
| 云端/分块渲染（Lambda 等） | **ProRes 4444（`--pixel-format=yuva444p10le`）** | 官方已知坑：分块渲染下透明 WebM 在 chunk 边界闪烁（alpha 编码依赖前帧） |
| 剪映/CapCut 导入 | ProRes 4444 .mov | 剪映对 ProRes alpha 兼容最好 |

## 6. 字幕作动效锚点（关键词强调类 B-roll）

词级转录/字幕文件（粗剪 `subtitles_words.json`）可以直接作为 B-roll 相位时间轴的物理锚点：关键词强调的 in/out 绑到对应词的 start/end，而不是人工估算秒数。适用：kinetic typography、下三分之一、数据标注、PiP 类"贴着口播走"的 B-roll（HyperFrames 的 talking-head-recut 工作流即此思路）。实施时用 `pairWith` 或 manifest 字段声明 `anchor: word-idx`，由装配阶段换算。

## 7. 许可证边界（必须遵守）

| 项目 | 许可证 | 边界 |
|---|---|---|
| Remotion 本体及官方 starter | 自定义源可用许可 | 个人/≤3 人营利组织免费（含商用）；更大规模需购买 Company License；**禁止复制/修改 Remotion 代码用于转售或再许可衍生品**。本合集按"个人/OPC 使用"登记 |
| HyperFrames | Apache-2.0 | 可自由使用/修改/再分发，保留版权与许可声明 |
| remotion-scenes / video-forge / video-skills-toolkit | MIT | 可参考/复制，须保留版权声明并登记来源 |
| remotion-templates（1000 模板库） | **无 LICENSE 声明** | ⚠️ 只允许分析思路与机制（registry/变体派生/gate 设计），**禁止复制其代码、模板或资产** |
| video-shotcraft | Apache-2.0 | 可改编，署名登记 |
| video-talkcraft | PolyForm-NC | 只允许分析原理，禁止复制代码/文本/模板 |
