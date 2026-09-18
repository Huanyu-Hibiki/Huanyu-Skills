---
name: oracle-learn-from
description: 兼容别名：将旧的账号级对标入口路由到 oracle-study benchmark。本目录不包含独立学习实现。
argument-hint: "<账号或样本> [旧参数保持原样]"
allowed-tools: Read, Skill
---

# 兼容别名：/oracle-learn-from

这是旧入口的薄路由层，不是第二套 skill。收到请求后：

1. 明示“`oracle-learn-from` 已合并为 `oracle-study`”；
2. 保留用户提供的对象与可读参数，转交 `/oracle-study --mode benchmark`；
3. 由 `oracle-study` 负责证据收集、用户确认、迁移与落盘。

不要在此目录实现 benchmark、抓取、评分或写入逻辑。
