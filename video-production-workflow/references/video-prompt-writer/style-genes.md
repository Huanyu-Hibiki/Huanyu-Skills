# B-roll 风格基因库

> 服务于 `/b-roll-finder`（选风格）和 `/b-roll-generate`（写风格化 prompt）。前 5 种视觉基因提炼自 MiniMax H3 官方 skills；Kurzgesagt 与数据可视化按通用实践整理。每格基因块可直接拼入 H3 prompt 的 `[Shot 1]` 风格声明。

## 使用规则

1. 每条 B-roll 在 `broll-style-decision.md` 里记录所选风格；同一条视频可混用，但色彩、节奏、字体、颗粒语言统一；
2. 写 AI 视频 prompt 时：视觉基因 → `[Shot 1]` 开头；运动语言 → 动作描述；负向约束 → prompt 末尾或生成工具的 negative 区；
3. 所有风格遵守公共纪律：先静帧后视频、单镜 4-7s、单一主动作、明确 settle 终态、画面文字静帧定稿、默认静音交付。

---

## 1. Vox 纸张拼贴（现有主力）

- **来源**：`paper-collage-explainer-generator` + `vox-director`
- **适合**：科普、观点、历史隐喻、编辑感章节转折
- **视觉基因**（风格签名，英文原样使用）：
  ```text
  flat bold color field, black-and-white halftone photographic cut-outs, selective colored cardstock accents, warm cream keylines, soft paper shadows, fine uncoated-paper grain, premium editorial paper collage, clean refined hand-torn paper edges, subtle fibrous edges, layered paper seams
  ```
- **运动语言**：触感停格组装——纸片 appear → slide/pop in → light bounce → press flat → pause → lock。禁止平滑数字图层移动、全局淡入、快速旋转、混乱飞散；
- **色彩语义**：焦橙/红=紧迫；芥末黄=警示与累积错误；墨绿=认知与重置；深紫=记忆与神秘；青绿=协作流动；玫红=荒诞仪式。钴蓝不作自动默认；
- **负向约束**：可读文字、假 UI、字幕、水印、Logo、牛皮纸做旧底（未批准时）、过脏过皱纸质；
- **音频**：默认保留触感拼贴 SFX（纸片滑动、弹入、压平轻敲、摩擦、脆响）——用户批准才进成片，否则管线去源音。

## 2. 白板手绘风（新）

- **来源**：`handdrawn-live-video-generator`（质感基因）+ 白板解释传统
- **适合**：教学、轻松解释、步骤拆解、"边讲边画"的临场感
- **视觉基因**：
  ```text
  hand-drawn marker illustration on a clean whiteboard, crayon / chalk / colored-pencil / pastel texture, slightly jittery linework, uneven stroke fill, rough brush edges, frame-by-frame redrawn feel, visible stroke build-up
  ```
- **运动语言**：笔画逐步生长（progressive stroke reveal）、图形随讲浮现、简笔箭头/圈注强调；像有人在实时画，不像矢量补间。线条轻微抖动、逐帧重画感是灵魂；
- **负向约束**：
  ```text
  no smooth uniform vector lines, no clean 3D CG, no glossy neon, no photorealism, no perfectly steady strokes, no flat digital gradient fills
  ```
- **H3 提示**：文字和关键图形在静帧定稿；视频只要求笔画自然生长。深色板（黑板/绿板）变体写 `chalk on dark green blackboard`；
- **音频**：可选马克笔书写沙沙声（批准后保留）。

## 3. 3D / CGI 风格（新）

- **来源**：`3d-animation-short-generator`
- **适合**：角色化叙事、产品隐喻、空间/系统想象、情绪爆发镜头
- **视觉基因**（H3 prompt 前缀，官方原文）：
  ```text
  Pixar-inspired 3D cartoon rendering, C4D + Octane look, stylized Q-version proportions, warm SSS skin, designed-with-detail hair, strong character design language, clean motion, on-brand color palette
  ```
- **造型语言**：2.5-3 头身 Q 版比例、夸张几何概括、强剪影；温润次表面散射（耳朵/脸颊/鼻尖微红透光）；毛发块面结构+边缘细发丝；
- **表演语言**：squash-and-stretch、anticipation、overshoot、follow-through、弧线动作、快速但可读的节奏、丰富微表情；
- **负向约束**：写实真人摄影、扁平二次元、塑料玩具皮肤、僵硬解剖姿势、无生命表情；
- **引擎备注**：H3 默认（包装/文字/UI 清晰度强）；高能量动作镜头回退 Seedance 2.0（`cinematic Pixar-quality 3D animation, elastic squash-and-stretch performance`）。角色一致性要求多镜时先锁角色卡。

## 4. 定格动画（新）

- **来源**：`papercraft-stop-motion-explainer`
- **适合**：物件隐喻、过程拆解、分层机制、手工温度、儿童化视角
- **视觉基因**：
  ```text
  handmade papercraft stop-motion, multi-layer cardstock cut-outs with visible paper thickness, matte tactile paper texture with fibers, creases, torn and cut edges, real physical shadows between layers, miniature diorama stage, macro photography feel with slight depth of field
  ```
- **画面层次**（每镜必须）：前景遮挡（纸片叶/帘幕/门框）→ 中景核心对象 → 背景/远景分层视差；背景也要有纸艺机关动效（纸云滑轨、纸门开合），不做静态平面；
- **运动语言**：逐帧手工拨动感——小幅分段移动、短暂停顿、轻微回弹、铰链关节、拉片、滑轨、转盘、翻页、纸片落定；
- **运镜**：缓慢推近、横向平移显视差、固定中景、微距特写、轻微俯视剖面；**禁止**高速飞行、360 环绕、数码故障；
- **转场**：翻页、立体书展开、抽拉标签、纸片遮挡、剖面层分开、纸屑飞散；
- **负向约束**（官方反向提示词，直接用）：
  ```text
  glossy plastic 3D, high-gloss CG render, photorealistic live action, flat vector illustration, cartoon without paper texture, metallic sci-fi surfaces, glass material, cyberpunk neon, digital glitch effects, oil painting brush strokes, real fur or skin pores, no paper fibers, no cut edges, no inter-layer shadows, overly smooth edges, high-speed camera orbits, melting or liquid morphing
  ```
- **音频**：翻纸、剪纸、卡纸滑动、卡扣、弹出、纸偶关节轻响（批准后保留）。

## 5. 数据可视化 / 信息图动画（新）

- **来源**：通用实践（Remotion 为主，AI 版做氛围/概念化数据）
- **适合**：统计、对比、增长、流程清单、抽象数量关系
- **双路由**：
  - **精确数据（有真实数字）→ Remotion/HyperFrames**：数字必须真实可核、图表必须可编辑，不交给 AI 生成（会出假字假数）；
  - **概念化/氛围化数据（无具体数字）→ AI 生成**：表现"数据的感受"而非读数。
- **AI 版视觉基因**：
  ```text
  abstract infographic motion design, clean geometric shapes and data-driven forms, bar-like and node-like abstract elements, smooth professional motion graphics aesthetic, minimal background, coordinated limited palette, subtle grid feel
  ```
- **运动语言**：元素依次点亮、条块生长、节点连线、计数式脉冲；节奏规整、与口播节拍对齐；
- **负向约束**：`no readable text, no numbers, no fake labels, no UI chrome, no watermark`（AI 版画面内不出现可读文字数字——可读数据一律走 Remotion）；
- **红线**：统计、增长、对比的具体数字不进 AI 生成；数据来源和单位在 Remotion 版里标清。

## 6. Kurzgesagt 风格（新）

- **来源**：通用实践（YouTube 科普频道 Kurzgesagt 视觉语言）
- **适合**：宇宙/科学/系统级抽象概念、乐观科普、宏观叙事、"尺度感"段落
- **视觉基因**：
  ```text
  flat 2D vector animation in Kurzgesagt style, bold saturated color palette, simple geometric shapes, anthropomorphic objects and creatures with simple dot eyes, subtle gradients for depth, layered parallax composition, space and nature motifs, clean rounded forms, minimal or no outlines
  ```
- **造型语言**：几何概括的拟人化物体/生物（圆点眼、简洁四肢）、大色块+微渐变、圆润无锐角、层叠视差构图；
- **运动语言**：流畅缓动（ease-in-out 为主）、元素弹入带轻微 overshoot、循环漂浮（呼吸感）、视差层缓慢漂移；与定格的"停顿感"相反，Kurzgesagt 是"丝滑但克制"；
- **色彩**：高饱和但和谐（深蓝底+亮橙/青/紫点缀是经典组合）；每镜限 3-4 主色；
- **负向约束**：`no photorealism, no 3D render, no gritty textures, no complex shading, no sharp angular shapes, no horror or body-horror elements`；
- **语义注意**：乐观科普调性；用于风险/负面话题时降饱和并收敛拟人幽默感，避免轻佻。

---

## 风格选择速查（给 /b-roll-finder）

| 内容责任 | 首选风格 | 备选 |
|---|---|---|
| 历史/文化隐喻、编辑感章节 | Vox 拼贴 | 拼贴+定格 |
| 教学、步骤拆解、轻松解释 | 白板手绘 | Kurzgesagt |
| 角色化叙事、产品拟人、系统想象 | 3D/CGI | Kurzgesagt |
| 物件过程、手工温度、分层机制 | 定格动画 | Vox 拼贴 |
| 精确数据、真实图表 | （不走 AI）Remotion 信息图 | HyperFrames |
| 概念化数据氛围、数量级感受 | 信息图动画（AI 版） | Kurzgesagt |
| 宇宙/宏观/科学系统概念 | Kurzgesagt | 3D/CGI |
| 真实实体、证据、新闻 | 真实素材/Stock（不属于本表 AI 风格） | — |

反同质化检查：连续两期主风格相同时，`/b-roll-finder` 必须在 Phase 4 明确提示并给出差异化建议。
