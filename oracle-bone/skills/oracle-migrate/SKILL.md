---
name: oracle-migrate
description: 把老用户的 .oracle-state.json 升级到当前 schema_version。读 migrations/registry.md 算迁移链，按顺序应用每步迁移文件。幂等、可断点续跑。触发词："迁移"/"升级 state"/"migrate"/"我的 state 是老版本"/"schema 版本不对"。
argument-hint: "[— from: <version>] [— to: <version>] [— dry-run]"
allowed-tools: Bash(*), Read, Write, Edit, Skill
---

# /oracle-migrate — Schema 版本迁移

把用户 `.oracle-state.json` 从旧 `schema_version` 升级到 LATEST_SCHEMA。

## Overview

```
[Phase 0: 读 state + registry → 确定迁移链]
  ↓
[Phase 1: dry-run 展示计划，等确认]
  ↓
[Phase 2: 备份 → .oracle-state.json.backup-<timestamp>]
  ↓
[Phase 3: 按序应用每步迁移文件的 HOW 段]
  ↓
[Phase 4: 验证（能解析 + 版本正确 + 必填字段齐）]
  ↓
[Phase 5: 报告]
```

## Constants

- **REGISTRY_PATH = `migrations/registry.md`** — 版本链单一来源（LATEST_SCHEMA + 版本链表）
- **DRY_RUN_BY_DEFAULT = true**
- **BACKUP_BEFORE_WRITE = true**（备份保留至下次成功 init / 用户手动清理）
- **STOP_ON_STEP_FAILURE = true** — 失败停在中间版本，不前进不回滚

## Workflow

### Phase 0: 确定迁移链

1. 读 state → `current_version = state.schema_version`
2. 读 registry → `LATEST_SCHEMA`
3. `— to` 覆盖目标；`— from` 强制起点（schema 字段坏了的罕见场景）
4. 状态判断：相等 → "✅ 已是 target，无需迁移"退出；current > target → 报错"无法降级，请手动 cp git 快照或重新 init"；小于 → 从版本链表算 `chain = [(from, to, file), ...]`
5. 某步在链表缺失 → 报错并列出已知版本，让用户检查

### Phase 1: dry-run

```
📋 迁移计划
当前: 1.0 → 目标: 1.1
  [1/1] 1.0 → 1.1（MINOR）
       <一句话描述> · 详见 migrations/1.0-to-1.1.md
⚠️ 备份位置: .oracle-state.json.backup-<timestamp>
继续？yes 执行 / no 退出 / detail 看每步具体改什么
```

### Phase 2: 备份

```bash
cp .oracle-state.json .oracle-state.json.backup-$(date +%s)
```

### Phase 3: 按序应用

对 chain 每步：
1. 读 `migrations/<file>` 的 `## HOW` 段
2. **按段内自然语言步骤逐项执行**——迁移是 AI 读 markdown 跑的，不是脚本
3. 每步完成：更新内存 schema_version = to + **原子写**（.tmp → rename）
4. 失败 → "❌ {file} 第 N 步失败：{error}。已停在 {last_success_version}，修复后重跑会从断点继续" → 退出

### Phase 4: 验证

1. 重新读 state 能解析
2. `schema_version == target`
3. 必填字段非缺失（参照 [state-management.md](../../shared-references/state-management.md) schema）
4. 失败 → "迁移完成但验证失败——查看备份恢复"

### Phase 5: 报告

```
✅ 迁移完成（from → to，N 步）
📦 备份保留：.oracle-state.json.backup-<ts>（确认正常后可手动删）
下一步：跑 /oracle-status 确认看板正常；hooks 重装跑 install.sh --reinstall-hooks <project-dir>
```

## Key Rules

1. **幂等**：已升过的 state 重跑立即退出，不重复应用
2. **不跳版**：多版必须按序，每步独立可恢复；不允许合并 atomic migration
3. **不静默兼容**：未知版本明确报错，不假装能继续
4. **失败停在原地**：断点续跑是设计核心
5. **备份硬约束**：即使 `--dry-run: false` 备份仍执行
6. **只改 state**：不动 predictions / rubric_notes / 作品目录——其他数据归各自 skill
7. **MAJOR/MINOR 透明**：dry-run 必标；MAJOR 额外提示"迁移完不能回退到老 skill 版本"

## Refusals

- 「跳过 dry-run 立刻覆盖」 → 允许（`--dry-run: false`），备份仍强制
- 「state 损坏 schema 字段没了，猜一个版本跑」 → 允许 `--from` 指定，但警告"基于猜测的迁移可能字段错位"
- 「降级到旧版本」 → 拒绝。schema 单向演进
- 「合并多步成一个 atomic」 → 拒绝
- 「在 bump / predict 中途调 migrate」 → 拒绝。避免 in_progress_session 被破坏

## Integration

- 上游：SessionStart hook 检测版本不一致 → 建议跑本 skill；用户 git pull 后看 CHANGELOG 标 BREAKING 主动跑
- 与 oracle-init：init 直接写 LATEST_SCHEMA，不走 migrate
- 与 install.sh --reinstall-hooks 解耦：迁移不重装 hook 脚本（hook 属 skill 包代码，不属于用户 state）
