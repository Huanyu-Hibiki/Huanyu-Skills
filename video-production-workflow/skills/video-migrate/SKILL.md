---
name: video-migrate
description: 视频制作管线 schema 迁移器。升级旧版 `.video-workflow-state.json`、补齐目录和交接文件，迁移前备份并输出报告；不删除用户素材和旧版本。触发词：迁移视频项目、升级制作管线、修复旧项目状态、video migrate。
argument-hint: "[project-path] [--target 0.1]"
allowed-tools: Bash(*), Read, Write, Edit, Glob
---

# /video-migrate

## 原则

- 迁移前先备份 state 和将被改写的派生文件；
- 只执行 `migrations/registry.md` 已登记的迁移；
- 不删除 Raw、Draft、B-roll、旧字幕、旧成片或用户手写说明；
- 迁移失败时恢复 state，不假装升级成功；
- 迁移后重新运行 `video-status` 做一致性检查；
- 迁移和修复是两次独立动作：不在同一次运行里「顺手修复」报告中的问题。

## 当前迁移

当前合集版本为 `schema 0.1`。旧项目通常没有 state 文件，此时执行：

1. 扫描已有 `video scripts/`、`Raw/`、`Rough/`、`Sub/`、`assets/`、`Polished/` 和 `Final/`；
2. 只根据实际文件推断已存在的产物；
3. 不把“目录存在”直接等同于阶段完成，必须检查文件内容；
4. 创建 state 模板并将不确定阶段标为 `blocked` 或 `not_started`；
5. 生成迁移报告，列出需要用户确认的交接问题。

## 输入/输出规格

| 项 | 规格 |
|---|---|
| 输入 | 项目根路径（必填）；`--target 0.1` 指定目标 schema，缺省即当前版本 |
| state 备份 | `.video-workflow-state.json.bak-<yyyyMMdd-HHmmss>`，保留原文件全部内容 |
| 迁移报告 | `Rough/migrations/migration-<yyyyMMdd-HHmmss>.md`，含：推断出的阶段清单（附依据文件路径）、标为 blocked/in_progress 的阶段（附缺失物）、需要用户确认的交接问题 |
| 推断规则（与 migrate.py 一致，纯文件存在性判断） | 证据文件齐全 → `completed`；部分存在 → `in_progress`；全无 → `not_started`；`Raw/` 有任意文件 → `record: in_progress`。**内容级核验（JSON 可解析、SRT 与视频时长一致）不在迁移脚本内**，由迁移后 `video-status` 的一致性检查承担 |

## 失败模式与恢复

| 触发条件 | 一线修复 | 仍失败兜底 |
|---|---|---|
| 旧 state JSON 损坏（解析失败） | 按无 state 处理，从实际文件推断重建 | 把损坏文件改名为 `.corrupt-<timestamp>` 留档，不删除 |
| 迁移脚本中途异常退出 | 从 `.bak-<timestamp>` 恢复 state 后重跑 | 🔴 手动恢复并把失败前的最后操作写入迁移报告，等用户确认后再试 |
| 迁移后 `video-status` 报不一致 | 对照报告逐项核对是推断错误还是文件缺失 | 把 disputed 阶段改回 `blocked`，列进报告的「需用户确认」节 |

## 执行脚本

```bash
uv run --project "<合集根>" python "<合集根>/scripts/video-migrate/migrate.py" "<视频项目根>/EP001_视频标题"
```

迁移脚本会备份旧 state，写入 schema 兼容字段，并把报告放到项目的 `Rough/migrations/`。

## 输出

```text
.video-workflow-state.json.bak-<timestamp>
Rough/migrations/migration-<timestamp>.md
.video-workflow-state.json（升级后）
```
