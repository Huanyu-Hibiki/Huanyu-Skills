---
name: oracle-cover-analyze
description: 兼容别名：将旧的封面分析入口路由到 oracle-cover analyze 模式。本目录不包含独立实现。
argument-hint: "<参考封面图> [旧参数保持原样]"
allowed-tools: Read, Skill
---

# 兼容别名：/oracle-cover-analyze

这是旧入口的薄路由层，不是第二套封面协议。收到请求后：

1. 明示“`oracle-cover-analyze` 已合并为 `oracle-cover --mode analyze`”；
2. 保留参考图与可读参数，转交 `/oracle-cover --mode analyze`；
3. 由 `oracle-cover` 负责分析确认、版权边界与 `cover-patterns.md` 落盘。

不要在此目录复制封面分析协议，也不要自动生成封面图。
