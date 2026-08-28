---
name: video-status
description: 视频制作管线只读状态看板。扫描状态文件、交接文件、目录和 B-roll manifest，显示当前阶段、阻塞项、已完成产物和下一步。触发词：视频状态、制作进度、下一步做什么、video status。
allowed-tools: Bash(*), Read, Glob, Grep
---

# /video-status

这是一个无副作用的只读 Skill，不替用户自动推进阶段。

## 检查来源

1. `.video-workflow-state.json`；
2. `video scripts/` 中的交接文件；
3. `Rough/`、`Sub/`、`Polished/`、`Final/` 和 `assets/` 的实际文件；
4. `broll-manifest.md` 及 B-roll slot 的 QA 状态；
5. `approval_pending`。

## 执行脚本

```bash
uv run --project "<合集根>" python "<合集根>/scripts/video-status/status.py" "<视频项目根>/EP001_视频标题"
uv run --project "<合集根>" python "<合集根>/scripts/video-status/status.py" "<视频项目根>/EP001_视频标题" --json
```

脚本只读 state 和实际文件，不自动修改项目。

🔴 **CHECKPOINT：发现 state 与实际文件矛盾、或存在 blocked/awaiting_approval 条目时，先展示矛盾清单并等用户选择修复路由，再结束本次 status——不带着未决矛盾静默退出。**

## 输出内容

```text
视频制作状态
项目：EP001_标题
当前阶段：B-roll 生成 / awaiting_approval

✅ 已完成：分镜、粗剪、字幕校对、剪映 Draft、素材归档、剪映精剪
⏳ 进行中：B-roll-001、B-roll-003
🛑 阻塞：B-roll-002 等待静帧确认
📦 交接文件：Sub/master.srt、broll-segment-plan.md

下一步：确认 B-roll 风格后说“生成通过的 B-roll”
```

## 派生检查

| 检查 | 依据 |
|---|---|
| 分镜是否完成 | `storyboard.md` + `storyboard.json` 均存在且同版本 |
| 粗剪是否完成 | `Rough/edl.json`、`rough_cut_manifest.md` 和预览存在 |
| 字幕是否可交接 | `Sub/caption_corrected.srt` 或 `Sub/master.srt` 存在 |
| 素材是否合规 | manifest 存在，未解决许可证风险为 0 |
| B-roll 是否可生成 | 机会表、母片段设计表和审批状态满足要求 |
| B-roll 是否可装配 | manifest 中通过 QA 的文件与实际文件一致 |
| 成片是否可交付 | `Final/video_final.mp4`、QA 报告和最终时间线 manifest 存在 |

## 失败模式与处理

| 触发条件 | 一线处理 | 仍失败兜底 |
|---|---|---|
| `.video-workflow-state.json` 缺失或损坏 | 只按实际文件报告（此时明确标注「无 state，按文件推断」） | 建议运行 `/video-migrate` 重建 state，本 skill 不代跑 |
| state 与实际文件矛盾（如 state 标 completed 但产物不存在） | 以实际文件为准展示，并把矛盾项列为 🛑 | 路由给 owning 子 skill 核实，不自行改 state |
| 用户给的路径下有多个视频项目 | 列出候选让用户选 | 不猜「最近修改的那个」 |
| `broll-manifest.md` 中 QA 通过条目缺文件 | 该条目标 ❌ 并计入阻塞项 | 路由回 `/b-roll-generate` 重做该条 |

## 禁止

- 不写、不改任何项目文件和 state（本 skill 只读）；
- 不代跑修复命令——修复动作只路由给对应子 Skill；
- 不在多候选项目路径时猜「最近修改的」；
- 不把「state 标了 completed」当完成依据，必须与实际文件交叉核对；
- 不在输出里泄露 API key、Cookie 等敏感配置。

状态不一致时只报告，不自行修复；把修复动作路由给对应子 Skill。
