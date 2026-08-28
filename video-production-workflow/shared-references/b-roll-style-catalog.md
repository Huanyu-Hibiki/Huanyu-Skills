# B-roll Style Catalog（B-roll 风格目录）

风格目录用于 `/b-roll-finder` 提出候选，不是强制模板。最终风格由用户确认；同一条视频可以混用风格，但需要统一色彩、节奏、字体和颗粒语言。

> **AI 生成风格族**：Vox 拼贴、白板手绘、3D/CGI、定格动画、数据可视化·信息图（概念化）、Kurzgesagt 的完整视觉基因、运动语言、负向约束和 H3 prompt 块见 [../references/video-prompt-writer/style-genes.md](../references/video-prompt-writer/style-genes.md)。`/b-roll-finder` 必须逐条 B-roll 确定风格，不得默认 Vox。

## 真实实拍类

| 风格 | 适合内容 | 生成/获取方式 |
|---|---|---|
| 纪录片观察风 | 工作现场、人物行动、真实过程 | 用户拍摄、Stock、官方视频 |
| 电影化叙事风 | 情绪、转折、空间和时间感 | 用户素材、AI 视频、合规 Stock |
| 新闻报道 / Editorial 风 | 事件、争议、权威信息 | 新闻来源、采访、档案素材 |
| 街头纪实风 | 城市、人物、社会观察 | 用户拍摄、合规 Stock |
| Lifestyle / UGC 手持风 | 日常行为、体验、产品使用 | 用户手机素材、授权 UGC |
| 历史档案 / Archive 风 | 历史、制度、文化背景 | 版权清晰的档案或 AI 风格化重构 |
| 工业 / 实验室 / 工作现场风 | 工程、制造、技术流程 | 现场拍摄、官方素材、Stock |
| 产品广告 / Commercial 风 | 产品能力、结果、功能展示 | 官方产品素材、用户录屏、AI 视频 |
| 桌面俯拍 / 微距材质风 | 文件、工具、手工、材质 | 用户拍摄、AI 视频、Stock |

## 证据和信息类

| 风格 | 适合内容 | 主要注意 |
|---|---|---|
| 新闻截图 / Source Receipt | 当前事件、报道、引用 | 必须保留来源和日期 |
| 网页 / 社交媒体 / 评论截图 | 真实原话、用户反馈、产品页面 | 不伪造截图，不隐藏关键上下文 |
| 屏幕录制 / Screen Recording | 工具和操作流程 | 优先自己的录屏；界面变化需标日期 |
| 软件 UI 演示 | 产品能力、流程和功能 | 真实 UI 优于装饰性模拟 |
| 数据图表 / Data Visualization | 统计、增长、对比 | 数据来源和单位清晰 |
| 地图 / 路线 / 时间线 | 空间、事件顺序、历史过程 | 示意地图要明确标注“示意” |
| 档案文件 / 报纸 / 文献 | 历史和证据链 | 关注版权、可读性和上下文 |
| Before / After | 变化、修复、优化结果 | 前后条件要可比 |

## 动态图形类

| 风格 | 适合内容 | 推荐引擎 |
|---|---|---|
| 极简现代动态图形 | 重点、章节、解释 | HyperFrames / Remotion |
| Premium Motion Design | 品牌、产品、关键结论 | HyperFrames / Remotion |
| Kinetic Typography | 关键词、判断、口播节奏 | HyperFrames |
| Infographic | 数据、清单、流程 | Remotion（精确数据）；概念化氛围版可 AI 生成（画面不出现可读数字） |
| Abstract Geometry | 抽象关系和情绪转折 | HyperFrames / Remotion |
| UI Card / Dashboard | 产品、指标、状态 | HyperFrames / Remotion |
| Isometric / 3D Infographic | 架构、空间、系统 | Remotion / HyperFrames |
| Particle / Fluid / Noise | 氛围和概念过渡 | HyperFrames / AI 视频 |
| Living Canvas / Web-native | 交互、连续流程、动态页面 | HyperFrames |

## 插画和混合媒介类

| 风格 | 适合内容 | 推荐引擎 |
|---|---|---|
| Vox 纸张拼贴 | 科普、观点、历史隐喻 | `b-roll-generate` 的拼贴路线 |
| 半调印刷 / Halftone | 新闻、档案、社会观察 | `b-roll-generate` 的拼贴路线 |
| 撕纸拼贴 / Editorial Magazine | 观点和章节转折 | AI 图 + HyperFrames |
| Newsprint / Zine 朋克 | 争议、反叙事和强观点 | AI 图 + HyperFrames |
| 复古海报 / Poster | 口号、结论、品牌段落 | HyperFrames / AI 图 |
| **白板手绘**（蜡笔/粉笔/马克笔质感，笔画逐步生长） | 教学、轻松解释、步骤拆解 | AI 生成（H3 等），基因见 style-genes.md |
| **3D / CGI**（皮克斯感 Q 版、C4D+Octane 质感） | 角色化叙事、产品拟人、系统想象 | AI 生成（H3 默认，动作镜头 Seedance 回退） |
| **定格动画**（纸艺分层、逐帧手工拨动感） | 物件隐喻、过程拆解、手工温度 | AI 生成 / 拼贴路线 |
| **Kurzgesagt**（扁平矢量、高饱和、拟人几何、丝滑缓动） | 宇宙/科学/宏观系统概念、乐观科普 | AI 生成 + Remotion 辅助 |
| 水彩 / 铅笔 / 墨水 | 文化、历史和情绪 | AI 图 / AI 视频 |
| 漫画分镜 / Storybook | 叙事、案例和想象场景 | AI 图 / AI 视频 |
| 剪纸 / 定格 / 黏土 | 物件、儿童化隐喻、过程 | `b-roll-generate` 的拼贴路线或 AI 视频 |

## 风格化影像类

| 风格 | 适合内容 |
|---|---|
| VHS / 家庭录像 / 胶片颗粒 | 回忆、档案和旧时代 |
| 赛博朋克 / 未来科技 | AI、系统、技术想象 |
| 黑色电影 / Film Noir | 风险、调查、悬疑 |
| 复古电视 / Broadcast | 媒体、新闻、公共叙事 |
| Lo-fi / 梦境 / Surreal | 情绪、隐喻和非现实连接 |
| Analog Horror | 系统失控、警告和不安感，谨慎使用 |
| 蒸汽波 / Retro-futurism | 复古科技和文化评论 |
| 日系生活电影 / 独立电影 | 安静观察、人物和空间 |
| 游戏 / Anime / Pixel / Low-poly | 游戏、虚拟世界、轻松表达 |
| 生成式 AI 超现实 | 不可拍摄的抽象或历史隐喻，必须标明非真实 |

## 节奏和剪辑导向类

| 风格 | 适合内容 |
|---|---|
| 快节奏短视频 / TikTok Cut | 片头、冲突、列表和结果 |
| 新闻快剪 / Image Burst | 证据蒙太奇和时效性内容 |
| Beat-synced | 音乐驱动的情绪和转折 |
| 慢节奏氛围蒙太奇 | 过渡、历史、环境和收束 |
| Chapter-based Explainer | 长视频章节结构 |
| Jump Cut / One-take | 人物风格和紧凑表达 |
| 画中画 / 分屏对比 | 仅在信息关系确实需要时使用 |
| 视觉隐喻 / Assemble-from-empty | 抽象概念、流程和物件关系 |
| Match-cut / Morph | 明确的视觉对应和场景变换 |

## 科普视频优先推荐

1. 纪录片实拍；
2. 新闻证据 / Source Receipt；
3. 屏幕录制 / UI 演示；
4. 数据图表 / 信息图；
5. 电影化 AI B-roll；
6. 纸张拼贴 / Vox；
7. 手绘插画；
8. 3D 等距图形；
9. 桌面实验 / Tabletop；
10. 复古档案 / Archive；
11. 极简动态图形；
12. UGC 手持生活方式风。
