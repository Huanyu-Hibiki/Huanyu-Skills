---
source: video scripts/manuscript.md
generated_by: video-plan
generated_at: <ISO 8601>
schema_version: 0.2
status: draft
---

# 分镜表

## 使用说明

- `拍摄形式`是素材路由：实拍和 OBS 可以是 A-roll 或 B-roll；Remotion、HyperFrames、AI 图/视频和 B-roll 动画设计默认属于 B-roll。
- 时间是前期估算；实际时间码以粗剪和精剪输出为准。
- 一行只表达一个主要叙事功能。
- **一句话意图**：每镜的「画面」列以一句话意图开头（"这镜让观众明白什么"），动效/素材行的每个动作都要答得出"在配合谁"，答不上就删；
- **素材行要落到盘面**：`场景补充`表中每个外部素材写已登记的请求/来源路径；还没采集的显式写「待采」并登记进文末「未完成 / 未采集清单」，不允许写成"后期再说"或包装成设计决定；
- **动效条目**（拍摄形式含 Remotion / HyperFrames / B-roll 动画设计）必须在「动效导演简报」区补齐简报，并声明覆盖模式。

## 主表

| 镜号 | 时间 | 画面 | 旁白要点 | 字幕/屏幕文字 | 剪辑/声音 | 拍摄形式 | 覆盖模式 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 01 | 0:00-0:00 | `<画面描述>` | `<旁白核心>` | `<字幕或屏幕文字>` | `<剪辑、音乐、音效>` | `<实拍 / OBS 录像 / Remotion 动效 / HyperFrames / B-roll 动画设计>` | `<A-only / B-only / AB-live(B-base-A-PiP / A-base-B-overlay / B-base-A-cutout / AB-split)>` |

覆盖模式说明：A-only=只有人物；B-only=只有素材/动效全屏；AB-live=人物与素材同屏（括号内选具体布局）。实拍/ OBS 的 A-roll 条目可写 A-only 或留空。规则见 [shared-references/motion-brief-standards.md](../shared-references/motion-brief-standards.md) 第 6 节。

## 场景补充

| 镜号 | A-roll/B-roll | 素材来源 | 是否需要外部素材 | 是否需要动效 | 许可证 / 版权备注 | 风险 |
|---|---|---|---|---|---|---|
| 01 | A-roll | 用户实拍 | 否 | 否 | | |

## 动效导演简报（每条动效条目一份）

> `video-plan` 对每条 Remotion / HyperFrames / B-roll 动画设计条目，按 [motion-brief-standards.md](../shared-references/motion-brief-standards.md) 的结构生成简报。先分类输入（目标帧重构 / 概念文案 / 流程数据 / 稿转场景），再写简报。规划阶段不写代码、不渲染。

### MOTION-001（对应镜号 04）

```text
输入分类：<目标帧重构 / 概念文案 / 流程数据 / 稿转场景>
画面理解：<一句话说明这条动画真正表达什么>
核心视觉：<主元素、视觉顺序和最终定格>
推荐动作：<动作之间的因果关系，不罗列动画预设>
主体接力：<本镜主角是谁、谁让位给谁；与相邻镜连成一条接力线，不允许出现无主角或双主角节拍>
趣味钩子：<最有记忆点的一秒，或最有反差的一步；无则写"无">
时间轴：<时间 / 动作 / 镜头焦点 三列表格；短动效按 Establish/主动作/主内容/次级细节/Hold 相位交叠规划>
图层拆分：<必须独立重建或控制的元素清单>
微动与音效：<支持主题的细节；音效标可选或必需，默认 N/A>
负面约束：<不能出现的风格偏差、内容错误和技术伪影>
制作判断：<2D / 2.5D / 3D 及理由；默认 2D>
时长 / 规格：<内容推导优先，缺省标题 4s、概念 4-6s、流程 5-8s；分辨率与 FPS 跟随主项目>
推荐引擎：<Remotion / HyperFrames，理由见 motion-engine-decision.md>
```

## Remotion / HyperFrames 素材组织（规划层约定）

分镜确认后，动效条目进入执行阶段时的**素材与工程组织**按以下约定规划（实际生成由 `/b-roll-generate` 执行）：

```text
Polished/B-roll/MOTION-001_<slug>/     # 每条动效独立工作区
├── brief.md                            # 上面简报的执行版
├── implementation_plan.md              # Remotion 路线必填（Gate 1 确认）
├── remotion-project/                   # Remotion 路线：独立工程
│   ├── src/<Name>.tsx                  # 一个 request 只注册一个 composition
│   └── public/                         # 图片/字体全部本地化
├── source/hyperframes/                 # HyperFrames 路线：HTML 场景
├── prompt/                             # AI 路线：image.md / motion.md
├── out/                                # final.mp4 / final.mov(透明) / final.webm
└── qa/                                 # 三帧静图（入场/峰值/终态）+ 短样片
```

规划分镜时的对应规则：

- **编号**：镜号 → `MOTION-XXX`（或 `BROLL-XXX`），与 `broll_candidates` 的 `shot_id` 对齐；
- **composition 命名**（Remotion）：`BrollM001`（一镜一 composition，不渲染 showcase）；
- **可变内容走参数**：文字、颜色、数据、时长设计为 props/变量，不锁死在组件内；跨视频要复用的模板优先 Remotion；
- **素材依赖**：动效引用的图片/截图/字体在分镜阶段登记进 `asset_request_list`，执行阶段全部本地化到工作区；
- **透明通道**：字幕强调、UI 浮层、叠加类动效默认规划为透明输出（ProRes 4444 / WebM alpha）；全屏解释片默认 MP4 insert。

## 风格档（G0）

> 开工先定皮、再选动作。由 `video-plan` 按全稿判定领域后写成本节，并落盘 `video scripts/style-profile.md`（系列视频从上一期复制后按集扩展，保持跨集一致）。深底主导属于偏离默认的选择，必须写明依据并经用户确认。

```text
领域判定：<讲什么 / 对谁讲 / 什么口吻 → 领域名 + 依据>
底色策略：<浅底默认 / 深底（需确认+依据）；章节间底色交替或轮换规则>
强调色：<唯一 accent；语义色（警示/涨跌/状态）只进图表与语义场景，不换色相只调饱和>
字体气质：<字阶档位与字重两档制；同屏文字层级 ≤3>
材质与卡型：<扁平 / 纸质 / 玻璃 / 线稿……同片同类元素一套皮>
图表语言：<坐标轴、网格、标记的统一画法>
素材气质：<实拍 / 截图 / 线稿陪衬图 / AI 图的配比与统一处理>
能量档：<安静叙述 / 均衡 / 高密度>
不做的事：<本片明确不出现的风格元素清单>
```

## 未完成 / 未采集清单（强制节，不允许缺）

> 本节拦截的失效模式是「未完成被包装成设计原则，进而变成不再被质疑的前提」。内容允许为"无"，节本身不允许缺失；`/b-roll-generate` Gate 0 与装配 QA 会查节在册。

| 事项 | 归档 | 依据 / 阻塞原因 | 试过的兜底 | 处置 |
|---|---|---|---|---|
| `<未采集的素材镜号>` | 待采 | `<为什么没有>` | `<试过哪些替代源>` | `<占位说明 / 降级路线>` |
| `<明确不做的视觉设计>` | 设计决定 | `<为什么不做>` | — | 写入风格档"不做的事" |

## B-roll 候选（结构化交接）

`video-plan` 必须把分镜表中属于 B-roll 的条目抽取为 `storyboard.json` 的 `broll_candidates` 数组（同字段的 JSON 版本），供 `/b-roll-finder` 强制对账。每条：

```json
{
  "shot_id": "01",
  "manuscript_excerpt": "<对应旁白原句>",
  "visual_proposition": "<一句话视觉命题草稿>",
  "route": "Remotion 动效 | HyperFrames | Stock | AI 图 | AI 视频 | B-roll 动画设计 | 用户素材",
  "coverage_mode": "A-only | B-only | AB-live:B-base-A-PiP | AB-live:A-base-B-overlay | AB-live:B-base-A-cutout | AB-live:AB-split",
  "input_class": "target-frame | concept-copy | process-data | script-to-scenes",
  "motion_brief_ref": "MOTION-001",
  "status": "proposed",
  "note": "<用户【画面建议】或规划理由>"
}
```

`/b-roll-finder` 生成机会表时，每条 `broll_candidates` 必须出现在机会表中并标注：`保留`（升级为正式条目）/ `降级`（判定不值得，写明理由）/ `待定`（时间轴确认后再定）。不得静默丢弃。
