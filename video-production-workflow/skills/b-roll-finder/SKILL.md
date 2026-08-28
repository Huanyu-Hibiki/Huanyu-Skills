---
name: b-roll-finder
description: B-roll 机会分析和素材路由。读取剪映内部精剪导出的 SRT，理解完整论点，判断哪里值得插入 B-roll，输出机会分析表、母片段设计表、推荐素材类型、视觉命题、风格和时间锚点。触发词：分析 B-roll、找 B-roll、哪里需要画面、设计 B-roll。
argument-hint: "[project-path] [master-srt-path]"
allowed-tools: Bash(*), Read, Write, Edit, Glob, Grep
---

# /b-roll-finder

## 定位

这是 B-roll 子系统的策划入口，不是一个“搜几个关键词并下载”的工具。它负责收窄选择范围、解释每个候选的意义、提出用户可以确认的路线；最终素材选择和风格取舍保留给用户。

## 输入

- 剪映内部精剪后的 `Sub/master.srt`；
- 完整文稿或 `video scripts/storyboard.json`（可选，用于语义校准）；
- `video scripts/b-roll-taste-profile.md`（如不存在则按 [b-roll-taste-profile.md](../../shared-references/b-roll-taste-profile.md) 建立）；
- 当前项目的品牌设计；
- 已有素材库、许可证清单和用户禁用项。

## Phase 0：读取偏好

首次使用或 `video scripts/b-roll-taste-profile.md` 没有 `Confirmed-by: <name> (<date>)` 时，询问并记录：

1. B-roll 是否默认去除源音；
2. 静态图是否使用轻微 Ken Burns，还是完全静止；
3. 是否显示来源署名；
4. 是否允许生成概念类 Remotion 动效；
5. 是否允许 AI 生成 B-roll，使用什么质量模型。

用户临时说出的禁用项立即生效，并写入项目 profile；例如“不要梗”“不要文字卡”“不要政治素材”。

## Phase 1：完整理解与 storyboard 对账

1. **先对账再分析**：读取 `video scripts/storyboard.json` 的 `broll_candidates`（如有），把它们作为机会表的种子条目；再从 SRT 补充新发现的机会；
2. 机会表必须覆盖每一条 `broll_candidates`，并逐条标注 `保留 / 降级 / 待定` + 理由；降级必须写明原因（如"原句已删""实拍已覆盖"），不得静默丢弃前期规划；
3. 先读完整 SRT，确定视频主题、受众、论点和节奏；
4. 按语义和叙事功能找候选 beat，不平均覆盖每句话；
5. 对每个 beat 先写“这句实际上在说什么”，再决定素材；
6. 使用 `a-roll-b-roll-routing.md` 判断 Receipts、Entity、Concept 或用户素材路线；
7. 对具体实体优先真实素材，对抽象概念才推荐自制动效或 AI 隐喻。

## Phase 2：输出机会分析表

必须生成：

```markdown
| 编号 | 分镜镜号 | 原稿位置与原句 | 是否值得插入B-roll | 推荐素材类型 | 静态终态类型 | 一句话视觉命题 | 是否纳入30秒母片 |
|---|---|---|---|---|---|---|---|
| 001 | 01 | 开场，4-6行：... | 值得 / 可选 / 不建议 | 真实成片 / 概念动效 | 结果展示 | ... | 是 / 否 |
```

`分镜镜号`列关联 `storyboard.json` 的 `broll_candidates.shot_id`；来自 SRT 新发现（分镜未规划）的条目填 `-`。来自 storyboard 的条目还要注明：B-roll 的作用（证明/解释/覆盖/强化）、建议进入词、预期时长、候选风格、素材来源路线、是否需要用户确认。

机会分析表后必须附 **storyboard 对账表**，逐条列 `broll_candidates` 的处理结果，不得静默丢弃：

```markdown
| 镜号 | storyboard 视觉命题 | 对账结果 | 机会表编号 | 理由 |
|---|---|---|---|---|
| 01 | <草稿> | 保留 / 降级 / 待定 | BROLL-001 | <一句话> |
```

## Phase 3：输出母片段设计

```markdown
| 母片段落 | 时间 | 核心内容 | 静态终态类型 | 主要动作事件 | 颜色建议 |
|---|---|---|---|---|---|
| V01 | 00:00-00:04 | ... | 流程中台 | ... | 深电光蓝 `#123B8F` |
```

母片段不是最终剪辑时间线，而是可复用的 B-roll 设计单元。每个单元要有清晰的开始状态、动作顺序、终态和可读时间。

## Phase 4：风格建议与审批

从 [b-roll-style-catalog.md](../../shared-references/b-roll-style-catalog.md) 推荐 1-3 个风格，用 [../../references/video-prompt-writer/style-genes.md](../../references/video-prompt-writer/style-genes.md) 判断每种风格的适用性、成本和语义风险，说明：

- 为什么适合这段文稿；
- 使用真实素材、Remotion、HyperFrames、拼贴 AI 还是混合路线；
- 预计成本、时长和可编辑性；
- 可能出现的语义风险。

**逐条确定风格**：风格决策必须落到每个 BROLL 条目，不是全片一个风格。`broll-style-decision.md` 的机会表增加「风格」列，每条记录：所选风格、引擎路线、颜色、节奏。可用风格族：Vox 拼贴 / 白板手绘 / 3D·CGI / 定格动画 / 数据可视化·信息图 / Kurzgesagt / 真实素材 / Remotion 动效（速查表见 style-genes.md 末节）。

**反同质化**：不得把 Vox 拼贴当默认风格。按内容责任选风格（抽象概念对比→Kurzgesagt/信息图；物件与过程隐喻→定格/白板手绘；角色化叙事→3D/CGI；精确数据→Remotion，不进 AI）。同一视频可混用风格但统一色彩、节奏、字体和颗粒语言。连续两期主风格相同时，必须在决策记录中明确提示用户并给出差异化建议。

将推荐风格、用户逐条选择、生成引擎、颜色、节奏、成本和禁止项写入 `video scripts/broll-style-decision.md`。等待用户确认后，才把 `b-roll` 状态推进到 `b-roll-generate`。

## 失败模式与恢复

| 触发条件 | 一线修复 | 仍失败兜底 |
|---|---|---|
| `storyboard.json` 缺失或无 `broll_candidates` | 降级为纯 SRT 分析；对账表记「本期无分镜候选」并提示下期从 `/video-plan` 补 | 不阻塞分析；禁止虚构镜号 |
| `Sub/master.srt` 不存在或时间轴可疑（时长与 fine_cut 不符） | 🔴 阻塞：路由回 `/video-fine-cut` 重新导出，不用粗剪字幕顶替 | 无兜底——精剪 SRT 是唯一时间真源 |
| 用户否决全部推荐风格 | 回 Phase 4 换风格族重提（最多 2 轮） | 仍否决时请用户点名风格或降密度，记录进 taste profile |
| taste profile 与本期用户口头要求冲突 | 口头要求优先，并把更新写回 profile | 冲突无法调和时 🔴 列差异请用户二选一 |
| 机会表条目过多（> 全片 beat 的 40%） | 主动降密度：只留「必须」和最强「值得」 | 展示密度统计，请用户勾选保留项 |

## 不可妥协

- 不因“画面丰富”而给每句话插 B-roll；
- 不把抽象关键词自动变成通用文字卡；
- 不由 Agent 自动选最终梗或反应素材；
- 不把网站截图数量当作 B-roll 质量；
- 不在未确认计划前批量搜索、下载或调用付费视频模型。

## 执行脚本

本阶段的“语义分析、机会表和风格建议”由模型根据 SRT 执行；脚本负责素材处理和放置验证，位于 `<合集根>/scripts/b-roll-finder/`：

```bash
# 静态图转平滑的子像素微动 B-roll
uv run --project "<合集根>" python "<合集根>/scripts/b-roll-finder/zoom_still.py" \
  "<项目>/assets/image/stock/asset.jpg" \
  "<项目>/Polished/B-roll/BROLL-001/out/final.mp4" 4 \
  --fps 30 --size 1920x1080

# 截取网页证据图（需要 Chrome/CDP）
uv run --project "<合集根>" python "<合集根>/scripts/b-roll-finder/cdp_capture.py" \
  "<URL>" "<项目>/Polished/B-roll/BROLL-001/source/receipt.png"
```

全屏 B-roll 的 beat 渲染入口已归入 `/video-polish`，位于 `<合集根>/scripts/video-polish/render_cutaways.py`；本阶段只负责机会分析、素材处理候选和放置设计。
