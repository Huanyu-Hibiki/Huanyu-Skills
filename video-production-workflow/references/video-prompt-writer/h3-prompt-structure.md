# H3 Prompt 结构（B-roll 适配版）

> 提炼自 `MiniMax-H3/skills/h3-prompt-writing`（含 `references/base-en.txt`）。适用于 H3 及结构兼容的视频生成模型。原文为英文结构词，B-roll prompt 正文用英文写，画面内文字保留原语言。

## 1. 五种生成模式

| 模式 | 输入 | 结构 | B-roll 场景 |
|---|---|---|---|
| T2VA | 纯文本 | 直接三字段 | 无参考图的全新概念镜头 |
| I2VA | 首帧图 | 指令行 + 三字段，从首帧向前发展 | 已有静帧/AI 图，让它动起来（最常用） |
| FL2VA | 首帧 + 尾帧 | 对齐指令 + 三字段，描述两帧之间的连续路径 | 有明确开始态和终态的动作（对应工作流的 first/last frame 路线） |
| L2VA | 尾帧图 | 对齐指令 + 三字段，推断合理开头并收敛到尾帧 | 只知道终态的组装/落定型镜头 |
| Ref2VA | 全参考 | 六段结构（subject_definitions/summary/retention_analysis/detailed_description/overall_soundscape/non_diegetic_music） | 风格/主体一致性要求高的多镜参考 |

## 2. 三字段核心结构

```text
integrated_multimodal_description: [Shot 1] ...

overall_soundscape: ...

non_diegetic_music: ...
```

- `integrated_multimodal_description`：主body。沿时间线描述风格、构图、主体、场景、动作、镜头变化、对白和同步声音；
- `overall_soundscape`：1-4 句总结环境声、动作声、非语言人声；
- `non_diegetic_music`：1-3 句描述画外音乐，只写乐器、速度、节奏、动态，不写抽象情绪词。

**B-roll 适配**：默认静音交付 → 两字段写 `N/A`（管线 `--strip-audio` 或后期去除）。仅当用户批准保留触感音效（拼贴 SFX、纸张声）时在 `overall_soundscape` 描述真实动作声；`non_diegetic_music` 对 B-roll 恒为 `N/A`（BGM 由主时间线管理）。

## 3. 指令行写法（关键帧模式）

- **I2VA** 固定句式（必须第一行）：
  `For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.`
- **FL2VA**：`How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark; Picture 2 (from Shot N) aligns with the S.SS-second mark.`（S.SS = 有效时长，两位小数）
- **L2VA**：同上句式，只写尾帧对齐。

指令行后空一行，再接三字段。

## 4. multimodal description 写作规则

1. **[Shot 1] 开头先声明风格和初始构图**。常用风格词：`Cinematic`、`live-action`、`2D-animated`、`3D CG`、`claymation`、`watercolor`、`vintage film`、`paper-collage`、`stop-motion papercraft`（风格基因见 [style-genes.md](style-genes.md)）；
2. **切镜**：后续镜头 `[Shot 2] At 00:03.500, the camera cuts to ...`，时间严格递增且在时长内。B-roll 单镜为主，4-7s，不超 7s；超长拆 wide + detail 两条；
3. **I2VA 叙事链**：first-frame anchor → action onset → continuous development → result/reaction。角色身份、服装、颜色、关键物、空间关系保持一致；
4. **FL2VA 叙事链**（优先单镜）：first-frame state → observable intermediate changes → progressively narrowing differences → last-frame state。不重复两张图的静态描述，写连接路径；
5. **L2VA 叙事链**：plausible preceding state → explicit action path → gradual convergence → last-frame landing。

## 5. 运镜词表：类型 + 幅度 + 速度

| 维度 | 可用表达 |
|---|---|
| 类型 | `Zoom In / Zoom Out`（变焦）、`Push In / Pull Out`（机位前后）、`Pan Left / Pan Right`（水平摇）、`Truck Left / Truck Right`（水平移）、`Tilt Up / Tilt Down`（垂直摇）、`Pedestal Up / Pedestal Down`（垂直移）、`Arc Shot`（环绕）、`Tracking Shot`（跟拍）、`Static Shot`（固定）、`Shake Slightly / Strongly`、`POV`、`Roll Clockwise / Counterclockwise` |
| 幅度 | `with small amplitude` / `with large amplitude` |
| 速度 | `at slow speed` / `at fast speed` |

写成自然动作句，不堆标签：

```text
The camera pushes in with small amplitude at slow speed toward the half-carved "同" character on the wooden slip.
```

中等幅度和正常速度可省略。B-roll 纪律：相邻镜头交替使用安全的 camera move；结论/重点镜头用 `static`。

## 6. 对白、画外音和画面文字

- 说话人用稳定 ID `(S1)` `(S2)`，跨镜不变；首次出现给身份描述；
- 对白格式：`The young woman with a quiet, breathy voice (S1) says: <d>[English] I get off at the next station.</d>`——语言标签 + 用户原话逐字，不翻译不改写；
- 画外音：`says in an off-screen voiceover`，且每个 `<d>` 后注明 `while his lips remain completely closed`；
- **画面内可见文字**（招牌、标签、字幕条）放英文双引号内逐字保留：`A red neon sign reading "营业中" glows above the doorway.`——关键文字在静帧中确定，视频模型只要求保持稳定，不让模型重新生成文字（B-roll 硬规则）。

## 7. 时长和总量约束

- 描述总时长与请求视频长度严格一致（4-15s）；
- B-roll 单 request 目标 3-6s，单镜 ≤7s；
- 提示词具体化：用可看见/可听见的细节，不用 "cinematic"、"beautiful" 这类抽象词（风格词表里的 `Cinematic` 是风格声明，不是质量形容词）。

## 8. 模型选择备注（来自 H3 官方 skill）

- **H3 默认**：强在视觉包装、动效图形、文字/UI 清晰度、指令遵循、性价比（768P 首推，2K 更高）；单片段最长 15s；
- **Seedance 2.0 回退**：强在电影感镜头、复杂运镜、弹性表演（squash-and-stretch、anticipation）；适合高能量动作镜头；
- 模型 ID 会变，付费调用前按 provider 当前 live model list 核验（沿用 b-roll-generate 的现有纪律）。
