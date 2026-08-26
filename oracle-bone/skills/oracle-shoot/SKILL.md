---
name: oracle-shoot
description: 登记一条内容已制作完成（拍摄/录完/写完定稿）。询问实际制作稿与 scripts/<id>.md 是否一致 + buffer +1。与 oracle-publish 配对：拍了进队列，发了出队列。触发词："拍了"/"拍了 X"/"shot"/"shot it"/"已拍 X"/"录完了"/"做完了"。
argument-hint: <scripts-path-or-id>
allowed-tools: Bash(*), Read, Write, Edit, Glob
---

# /oracle-shoot — 登记制作完成 + (改稿则) 触发 v2 预测

把作品从"已写预测、未制作"推进到"已制作、未发布"。这一步：
1. 验证 prediction 已存在（盲预测纪律）
2. 询问"实际制作时用的稿子和 scripts/<id>.md 一致吗？"
3. 算 diff——超过 V2_TRIGGER_THRESHOLD（默认 30%）→ delegate 到 `/oracle-predict — mode: v2`
4. 把作品加进 state.shoots 队列，buffer +1

oracle-shoot 自己**不**写预测内容——预测落盘逻辑全在 oracle-predict，本 skill 只负责检测改稿 + 派发。

为什么单独一个 skill：
- buffer 警戒需要明确区分"拍了" vs "发了"。可以批量拍（一天 5 条），分散发（每天 1 条）
- "实际制作稿" ≠ "pre-shoot 草稿"是常态。diff 显式化 + v2 重判 + 采集"用户改稿 pattern"的入口
- v1 vs v2 的差异本身就是 rubric 升级证据

## Overview

```
[用户：拍了 <NNN>_<标题>/scripts/<id>.md]
  ↓
[Phase 0: 解析路径 + 验证 prediction 已存在]
  ↓
[Phase 1: 读全局 state + 检查重复登记]
  ↓
[Phase 2: 询问稿子一致性（一致 / 改了 / 大改）]
  ↓
[Phase 3: 写定稿 + (b 路径) 算 diff 触发 v2]
  ↓
[Phase 4: append state.shoots]
  ↓
[Phase 5: shoots 队列交叉校验 + 输出 buffer 状态]
```

## Constants

- **REQUIRE_PREDICTION = true** — 制作前必须先有 v1 prediction
- **V2_TRIGGER_THRESHOLD = 0.30** — diff 超过 30%（行级 diff / 原稿行数）→ 默认建议 v2 重判；低于则询问
- **DIFF_METRIC = lines** — `diff -u | grep '^[+-]' | wc -l` / 原文件行数

## Workflow

### Phase 0: 解析 + 验证

1. 解析路径：全路径 / `<NNN>` / id / 短标题简写 → glob `<NNN>_*/scripts/*_<id>_*.md` 匹配
2. 验证 `scripts/<id>.md` 存在 → 不存在报错
3. 验证对应 prediction 存在（同作品 `predictions/<同名>.md`）：
   - 不存在 → **拒绝登记**："先跑 /oracle-predict 写预测——制作完才写预测等于事后看了成品再写判断，违反盲预测原则"

### Phase 1: 读全局 state + 检查重复

1. **必做**：`cat <项目根>/.oracle-state.json` 读全局（协作契约 #7：用户说"另一个会话已登记"→ 先验证再行动）
2. 检查 `shoots[]` 是否已含此 id：
   - 已存在 → 警告"已登记过（X 天前）"+ 显示已有 shot_at / prediction_file / script_consistency。**不重跑**。问用户："要覆盖重登，还是继续走 oracle-publish？"
   - 不存在 → Phase 2

### Phase 2: 确认作品目录 + 询问稿子一致性

1. 确认 `<NNN>_<标题>/` 存在（oracle-seed 应已建）→ 缺失则按 [content-folder-schema.md](../../shared-references/content-folder-schema.md) 补建（不反问用户"要不要补"——缺失就补，一步做完）
2. 🔴 **CHECKPOINT**（三选一决定 v2/redo 路径，不能默认跳过）：询问用户：

```
制作「<title>」的时候，实际用的稿子和 scripts/<id>.md 一致吗？

a) 一致——按草稿做的
b) 改了一些——给我看下实际制作稿，我重新打分一次（v2 预测）
c) 大改了，基本是另一条 → 走 _redo 流程：
   scripts/<id>_redo.md → 重新 oracle-predict → 再 oracle-shoot（原 prediction 留档脱钩）
```

### Phase 3: 写定稿 + diff 判定

**a 路径（一致）**：`cp scripts/<id>.md → <作品目录>/scripts/<id>_final.md`（保留制作时点快照）；`script_consistency = consistent`；进 Phase 4。

> **定稿快照必写**——即使与草稿相同。这是 retro Phase 4b（改稿→流量影响 diff）的基线；缺失会让 pattern 学习系统化跳过。

**b 路径（改了）**：
1. 询问实际制作稿——粘贴文本 / 文件路径 / 转录文件
2. 用户提供 → 写入 `<作品目录>/scripts/<id>_final.md`
3. 用户没保留（即兴）→ 标 `script_lost`，写占位 + 警告"v2 重判跳过——下次建议留稿（哪怕语音转录）"；进 Phase 4
4. 算 diff（**先剥离格式差异**——markdown 加粗/时间戳标题/注释段，只比口播文本实质变化）：
   ```bash
   added=$(diff -u scripts/<id>.md scripts/<id>_final.md | grep -c '^+')
   removed=$(diff -u scripts/<id>.md scripts/<id>_final.md | grep -c '^-')
   diff_pct=$(( (added + removed) * 100 / total_orig ))
   ```
5. **判定 v2 触发**：
   - `diff_pct >= 30` → 默认建议 v2，**主动调用** `/oracle-predict — mode: v2 — prediction-file: <path>`
   - `< 30` → 询问"只改了 N%，要重判吗？默认不（v1 仍有效）"
6. v2 落盘后控制权回到 shoot 进 Phase 4

**c 路径（大改）**：不写定稿，提示走 `_redo` 流程，退出（不进 Phase 4）。

### Phase 4: state 更新

```json
{
  "shoots": [
    ...,
    {
      "work_folder": "<NNN>_<标题>/",
      "prediction_file": "<NNN>_<标题>/predictions/<...>.md",
      "scripts_path": "<NNN>_<标题>/scripts/<id>.md",
      "track": "<轨道 id>",
      "shot_at": "<ISO timestamp>",
      "script_consistency": "consistent | modified | lost",
      "script_diff_pct": <0-100 | null>,
      "v2_prediction_written": <true/false>,
      "script_hash_at_shoot": "<sha256:12 of 定稿>",
      "ad_hoc": false
    }
  ]
}
```

`v2_prediction_written: true` → retro 读 v2 算偏差；false → 沿用 v1。

### Phase 5: shoots 队列交叉校验 + buffer 输出

**校验（硬步骤，不可跳）**：
1. 遍历 state.shoots，对每条检查是否已有对应的 `last_published_*` / 已从队列清过的记录
2. 有已发布残留 → 自动清理 + 警告"发现 N 条已发布作品残留在 shoots 队列，已清理"
3. 用清理后的队列算 buffer

**为什么硬**：buffer 数字直接影响拍摄决策。显示"5 篇待发"但实际只剩 1 条 → 用户对工具的信任崩塌。

输出 buffer + 颜色（[cadence-protocol.md](../../shared-references/cadence-protocol.md)）：

```
✅ 已登记制作：<NNN>_<标题>/
   预测文件：predictions/<...>.md

📦 当前 buffer：3 篇（🟢 绿色，正常）
   按你的 cadence（隔日更）= 6 天 buffer，节奏稳定。

下一步：制作其他候选 / 等下个发布日 / 不动
```

颜色变化 → 高亮提醒（红 = 今天必须拍/发；蓝 = 暂停制作，先发存货）。

## Key Rules

1. **不写 prediction**——拍了 ≠ 发了。预测在 predict 锁，拍只是事件
2. **必先有 prediction**——否则违反盲预测
3. **定稿快照必写**（一致也写）——retro diff 的基线
4. **buffer 实时计算**——state.shoots 是真值
5. **支持批量**——"拍了 X / 拍了 Y / 拍了 Z" 连续登记

## Refusals

- 「拍了 X，但没跑过 oracle-predict」 → 拒绝。v1 必须制作前写。请先 predict 再来
- 「改稿了但直接覆盖 v1 吧，别留 v2」 → 拒绝。append 不覆盖——两段一起留是 rubric 学习的关键证据
- 「我没有作品目录，直接拍的」 → 帮建目录（不反问），登记标 `ad_hoc: true`，提示下次走完整流程

## Integration

- 上游：oracle-predict 写完 → 用户实际制作 → oracle-shoot 登记
- 下游：oracle-publish 发布时从 state.shoots 移除（buffer -1）
- oracle-status 看板 buffer = state.shoots.length；oracle-recommend 按颜色调策略；SessionStart hook 报告第一行
