# Video Prompt Writer（AI 视频 Prompt 参考库）

> 提炼自 MiniMax H3 官方 skills（`<MiniMax-H3 官方 skills 目录>`），服务于本工作流的 B-roll AI 生成路线。
> 当 `b-roll-generate` 走 AI 视频/图片生成（H3、Seedance、Gemini 图生视频等）时，写 prompt 前必读本目录。

## 文件索引

| 文件 | 用途 | 何时读 |
|---|---|---|
| [h3-prompt-structure.md](h3-prompt-structure.md) | H3 五种生成模式、三字段 prompt 结构、镜头/运镜/对话/文字规则 | 写任何 AI 视频 prompt 之前 |
| [style-genes.md](style-genes.md) | 6 种 B-roll 风格基因：Vox 拼贴 / 白板手绘 / 3D·CGI / 定格动画 / 数据可视化·信息图 / Kurzgesagt | `/b-roll-finder` 选风格时 + `/b-roll-generate` 写风格化 prompt 时 |

## 与工作流的衔接

1. `/b-roll-finder` Phase 4 从 [../../shared-references/b-roll-style-catalog.md](../../shared-references/b-roll-style-catalog.md) 选风格时，用 `style-genes.md` 判断每种风格的适用性、成本和语义风险，**逐条 B-roll 确定风格**，写入 `broll-style-decision.md`；
2. `/b-roll-generate` Gate 3（AI 生成路线）写 prompt 时：
   - 按 `h3-prompt-structure.md` 的三字段结构组织 prompt；
   - 按所选风格在 `style-genes.md` 取视觉基因块、运动语言块和负向约束；
   - B-roll 默认静音——`overall_soundscape` 和 `non_diegetic_music` 按路线写 `N/A`（管线会去源音），仅在用户批准保留触感音效时描述真实动作声；
3. 风格化 AI 路线（3D/CGI、定格、Kurzgesagt、白板手绘、拼贴）都遵守：**先静帧、后视频；单镜 4-7s；单一主动作 + 明确 settle 终态**。

## 风格差异化原则

当前频道历史 B-roll 以 Vox 纸张拼贴为主，同质化严重。新增 5 种风格后：

- 同一条视频内可以混用风格，但需统一色彩、节奏、字体和颗粒语言（沿用 style-catalog 总则）；
- `/b-roll-finder` 推荐风格时**不得把 Vox 当默认**；按内容责任选：抽象概念对比 → Kurzgesagt/信息图；物件与过程隐喻 → 定格/白板手绘；角色化叙事 → 3D/CGI；
- 每期视频的主风格在 `broll-style-decision.md` 里记录，跨期回顾避免连续多期同风格。
