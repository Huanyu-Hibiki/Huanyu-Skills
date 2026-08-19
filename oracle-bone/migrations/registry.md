# Migration Registry

`LATEST_SCHEMA = "1.0"`

这是 schema 版本演进的**单一来源**。oracle-migrate 按此链表按序应用迁移；oracle-init 写新 state 时硬编码此版本号。

## 版本链

| 版本 | 日期 | BREAKING? | 迁移文件 | 描述 |
|---|---|---|---|---|
| 1.0 | 2026-08-19 | —（初始） | — | oracle-bone 初始 schema：tracks 注册（plan_type + definitions + mix_ratio）+ calibration_samples_by_track 分桶 + shoots 扩展字段 + pending_retros 窗口表 |

## 维护者规则

1. bump schema 时：改本文件 `LATEST_SCHEMA` + 版本链追加一行 + 写 `migrations/<old>-to-<new>.md`（WHAT/WHY/HOW/Manual fallback 四段）
2. 同时改 `skills/oracle-init/SKILL.md` Phase 5 的硬编码版本号
3. CHANGELOG 标 `MINOR` 或 `BREAKING`
4. 详见 [shared-references/migration-protocol.md](../shared-references/migration-protocol.md)
