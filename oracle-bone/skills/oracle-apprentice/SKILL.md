---
name: oracle-apprentice
description: 兼容别名：将旧的单条拆稿入口路由到 oracle-study practice；视觉包装请求转交 video-production-workflow。本目录不包含独立实现。
argument-hint: "<作品或稿件> [--visual 等旧参数保持原样]"
allowed-tools: Read, Skill
---

# 兼容别名：/oracle-apprentice

这是旧入口的薄路由层，不是第二套 skill。收到请求后：

1. 明示“`oracle-apprentice` 已合并为 `oracle-study`”；
2. 普通拆稿/拜师请求转交 `/oracle-study --mode practice`，保留对象与可读参数；
3. `--visual`、“拆包装”“拆视频动效”等请求直接转交 `video-production-workflow`；
4. 由目标 skill 负责确认、验证门、迁移与落盘。

不要在此目录实现拆稿、视觉分析、剪辑计划或成片验收逻辑。
