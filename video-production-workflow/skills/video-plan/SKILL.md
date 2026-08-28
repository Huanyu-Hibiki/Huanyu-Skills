---
name: video-plan
description: 前期规划与分镜交接。把完整视频文稿按语义场景转成分镜表、storyboard.json、素材请求、音乐 cue 和动效候选；粗剪后也可根据实际时间码生成 motion_request_list。触发词：规划分镜、文稿转分镜、列素材、制作拍摄计划。
argument-hint: "[manuscript-path] [--mode pre-production|rough-cut-finalization]"
allowed-tools: Bash(*), Read, Write, Edit, Glob, Grep
---

# /video-plan

## 两种模式

| 模式 | 输入 | 输出 | 用途 |
|---|---|---|---|
| `pre-production` | 完整视频文稿 | 分镜表、`storyboard.json`、素材建议、音乐 cue、动效候选 | 指导拍摄、OBS 录制和前期素材准备 |
| `rough-cut-finalization` | `Rough/rough_cut_manifest.md`、`missing_materials.md`、实际时间码 | `motion_request_list.md`、B-roll/动效执行请求 | 根据粗剪后的真实时间线确定真正要做的素材 |

## 前期分镜表

至少输出以下字段：

```markdown
| 镜号 | 时间 | 画面 | 旁白要点 | 字幕/屏幕文字 | 剪辑/声音 | 拍摄形式 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 01 | 0:00-0:08 | 人物特写，直接看镜头 | 核心问题 | 关键词 | 硬切开场，无铺垫 | 实拍 |
```

`拍摄形式`是路由字段，可使用：`实拍`、`OBS 录像`、`Remotion 动效`、`HyperFrames`、`B-roll 动画设计`、`AI 图`、`AI 视频`、`Stock`、`实拍 + Remotion 动效`、`OBS 录像 + Remotion 动效`。

## 规划规则

- 按语义场景分段，不按 `//` 机械切段；
- 一镜一功能，避免一句话塞入多个互不相关的视觉命题；
- 保留用户的 `【画面建议】`，但区分用户意图和最终执行；
- 主要观点、情绪和可信度优先分配给 A-roll；
- 真实工具操作、界面和流程优先规划 OBS；
- 抽象解释、架构、流程、数据再进入 Remotion 或 HyperFrames 候选；
- Stock 和 AI B-roll 用于环境、视觉桥接和不可拍摄概念，不为了“每句有画面”而添加。

## 失败模式与恢复

| 触发条件 | 一线修复 | 仍失败兜底 |
|---|---|---|
| 终稿文件缺失或为空 | 询问用户提供路径；不猜测、不拿旧期文稿顶替 | 🔴 用户给不出终稿就停在本阶段，不产出空分镜 |
| 文稿没有 `//` 停顿标记 | 正常情况：本就按语义分段，不依赖 `//` | 无需兜底；禁止退化为按行机械切 |
| 文稿与实际拍摄/录制严重不符（口播大幅偏离） | 走 `rough-cut-finalization` 模式按实际转录重规划 | 分镜标记 `superseded` 并保留旧版，不覆盖 |
| `storyboard.json` 与 `storyboard.md` 内容冲突 | 以 json 为真相源修正 md | 记录冲突原因，🔴 请用户确认哪版有效 |
| 用户要求跳过分镜直接要素材/B-roll | 拒绝并展示分镜缺失的具体风险（素材无路由依据、B-roll 无对账种子） | 坚持要求时只给 `material_suggestion_doc.md` 草稿，不进入 asset_request_list |

## 必须生成的交接

1. `video scripts/storyboard.md`；
2. `video scripts/storyboard.json`，作为派生文件真相源；**必须包含 `broll_candidates` 数组**（分镜表中所有 B-roll 条目的结构化版本：镜号、旁白原句、视觉命题草稿、路由建议、状态），供 `/b-roll-finder` 强制对账——见 [templates/storyboard.template.md](../../templates/storyboard.template.md) 的字段定义；
3. `video scripts/material_suggestion_doc.md`；
4. `video scripts/remotion_candidate_list.md`；
5. `video scripts/music_cue_sheet.json`；
6. `assets/requests/asset_request_list.md`；
7. `video scripts/feishu_storyboard_records.json`（如项目需要 n8n 同步）。

## 执行说明

本阶段没有独立的“自动写稿脚本”：分镜拆解和 B-roll 路由需要模型读取终稿后生成，输出格式由 `templates/storyboard.template.md` 和 `references/video-plan/output-template.md` 约束。文件落盘由当前 Agent 的写入能力完成；这不是缺少实现，而是该阶段的执行方式。

粗剪后执行第二次规划时，必须丢弃已被实拍、OBS、Stock 或 Filmora 解决的候选，只保留实际缺失且值得制作的请求。

## 禁止

- 不按 `//` 或换行机械切段，只按语义场景分；
- 不把用户的【画面建议】当作最终执行决定，区分意图与执行；
- 不给每句话都分配画面或动效；
- 不在分镜确认前生成 `asset_request_list.md` 触发下载；
- 不覆盖已有 `storyboard.json`——修订走版本递增或 `superseded` 标记；
- 不把抽象关键词直接落成「通用文字卡」类动效候选。

## 结束状态

写入 `approval_pending`，等待用户确认分镜和素材路由；未确认前不启动大批量素材下载。
