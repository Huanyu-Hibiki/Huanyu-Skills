---
name: video-init
description: 视频制作管线首次初始化。检查或确认单期视频项目路径，创建标准目录、状态文件、WORKFLOW.md 和 STATUS.md，不覆盖已有文件。触发词：初始化视频制作管线、创建视频项目、video init。
argument-hint: "[project-path]"
allowed-tools: Bash(*), Read, Write, Edit, Glob
---

# /video-init

## 目标

让一个视频项目从“只有终稿或空目录”进入可追踪的制作状态。初始化只负责脚手架，不自动规划分镜、不下载素材、不转录、不创建剪映草稿。

## 流程

1. 确认项目路径、期数和工作标题。
2. 检查项目根是否已存在 `.video-workflow-state.json`。
3. 已初始化：展示当前状态，只有用户明确要求重置时才继续；重置不删除旧文件，创建备份状态。
4. 半初始化：列出已存在的目录和文件，补齐缺失项，不覆盖已有内容。
5. 创建 [video-folder-schema.md](../../shared-references/video-folder-schema.md) 中的标准目录。
6. 从模板创建 `.video-workflow-state.json`、`WORKFLOW.md`、`STATUS.md`。
7. 如果用户已提供终稿，复制为 `video scripts/manuscript.md`，保留来源说明；不覆盖已有 manuscript。
8. 把 `init` 标为 `completed`，输出下一步 `/video-plan`。

注意：`b-roll-taste-profile.md` 不在 init 阶段创建。它由 `/b-roll-finder` 在真正需要时创建并当面询问用户确认风格，确认前不得用于搜索和生成。

## 执行脚本

```bash
uv run --project "<合集根>" python "<合集根>/scripts/video-init/init_project.py" \
  "<视频项目根>/EP001_视频标题" \
  --title "视频标题" --width 1920 --height 1080 --fps 30 \
  --manuscript "D:/path/to/manuscript.md"
```

脚本会创建目录、复制工作流模板和状态文件。已有文件不覆盖。

## 必须询问

🔴 **CHECKPOINT：以下 5 项全部得到明确答复后才能创建任何文件。用户只给了路径时，逐项补问，不默认填 1920x1080/30fps。**

- 项目路径是否正确；
- 视频标题和期数；
- 画幅（横屏 / 竖屏 / 方形）；
- 典型输出帧率；
- 是否已有 `Raw\` 和终稿。

## 失败模式与恢复

| 触发条件 | 一线修复 | 仍失败兜底 |
|---|---|---|
| 项目路径含空格或中文导致脚本失败 | 所有 CLI 参数加引号重试 | 建议用户把项目目录改为无空格路径后再初始化 |
| `video scripts/manuscript.md` 已存在 | 保留现有文件，展示差异让用户决定 | 不覆盖；新终稿存为 `manuscript-v<N>.md` 并记录来源 |
| state 文件存在但 JSON 损坏 | 按半初始化处理，补齐目录 | 损坏文件改名 `.corrupt-<timestamp>` 留档后重建 |

## 禁止

- 不询问就猜测项目根；
- 覆盖 `Raw\` 或已有 `WORKFLOW.md`；
- 把 API key、Cookie 写入 state；
- 初始化完成后宣称已有粗剪、字幕或素材。
