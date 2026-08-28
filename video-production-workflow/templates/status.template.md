# 视频制作状态

> 由 `/video-status` 更新。此文件是人类可读看板，真实状态以 `.video-workflow-state.json` 为准。

## 项目

| 字段 | 内容 |
|---|---|
| 项目 | `<project_id>` |
| 标题 | `<title>` |
| 画幅 | `<width>x<height>` |
| FPS | `<fps>` |
| 当前阶段 | `<current_phase>` |
| 最近动作 | `<last_action_at>` |

## 阶段进度

| 阶段 | 状态 | 关键产物 | 阻塞 / 下一步 |
|---|---|---|---|
| init | not_started | 目录、state | |
| plan | not_started | storyboard | |
| record | not_started | Raw | |
| rough_cut | not_started | EDL、preview | |
| caption_correct | not_started | caption_corrected.srt | |
| jianying_draft | not_started | Jianying-draft | |
| assets | not_started | assets、manifest | |
| fine_cut | not_started | fine_cut、master.srt | |
| broll_plan | not_started | opportunity、segment plan | |
| broll_generate | not_started | B-roll、manifest | |
| polish | not_started | Polished/preview | |
| delivery | not_started | Final/video_final.mp4 | |

## B-roll 统计

| 项目 | 数量 |
|---|---:|
| 机会总数 | 0 |
| 用户批准 | 0 |
| 已生成 | 0 |
| 已通过 QA | 0 |
| 延后 / 移除 | 0 |

## 待处理

1. `<最高优先级待办>`
2. `<审批问题>`
3. `<缺失素材或许可证问题>`
